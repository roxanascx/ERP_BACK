"""
Contabilización de las ventas: del registro de ventas al libro diario.

Segundo paso del puente SIRE → contabilidad. Genera un asiento por comprobante,
con las cuentas que define su subdiario.

Tres cosas lo hacen seguro, que es lo que faltaba para poder automatizarlo:

  - **Se agrupa en lotes.** Cada contabilización lleva un identificador, y el
    lote entero se puede deshacer.
  - **No se contabiliza dos veces.** Una venta que ya generó asiento queda
    marcada y se salta.
  - **Nada entra descuadrado.** El asiento se valida antes de insertarse, no
    después; y un comprobante con tributos sin cuenta configurada se aparta en
    vez de imputarse donde no va.

El asiento sigue la estructura estándar: cuentas por cobrar (12) al Debe por el
total, IGV (40) al Haber cuando lo hay, e ingresos (70) al Haber por el resto.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..plan_contable_repository import AccountingRepository
from ..schemas.schemas_subdiario import NaturalezaVenta
from .asientos_automaticos import lineas_automaticas_por_destino
from .subdiario_service import SubdiarioService

logger = logging.getLogger(__name__)

#: Comprobantes que restan en vez de sumar: la nota de crédito deshace una venta.
TIPOS_QUE_RESTAN = {"07"}

#: Estados de SUNAT que significan que el comprobante no debe contabilizarse.
ESTADOS_ANULADOS = {8, 9}

#: Tributos que el asiento no sabe imputar todavía porque no hay cuenta para
#: ellos en el subdiario. Si alguno viene con importe, el comprobante se aparta.
TRIBUTOS_SIN_CUENTA = ("isc", "ivap", "icbper", "otros_tributos_cargos")


class ContabilizacionError(Exception):
    """No se puede contabilizar, y el mensaje explica por qué."""


def _dec(valor: Any) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal("0")


class ContabilizacionVentasService:
    """Genera los asientos del libro diario a partir del registro de ventas."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.ventas = database.registro_ventas
        self.asientos = database["asientos_contables"]
        self.subdiarios = SubdiarioService(database)
        self.plan_contable_repo = AccountingRepository()

    # ------------------------------------------------------------------
    # Selección de lo pendiente
    # ------------------------------------------------------------------

    async def _pendientes(
        self, empresa_id: str, periodo: str, subdiario: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ventas del periodo que todavía no han generado asiento.

        `asiento_numero` es la marca: en cuanto una venta se contabiliza, deja
        de aparecer aquí. Es lo que impide contabilizar dos veces.
        """
        filtro: Dict[str, Any] = {
            "empresa_id": empresa_id,
            "periodo": periodo,
            "asiento_numero": {"$in": [None, ""]},
        }
        if subdiario:
            filtro["subdiario"] = subdiario

        return [doc async for doc in self.ventas.find(filtro).sort("fecha_emision", 1)]

    @staticmethod
    def _motivo_para_apartar(venta: Dict[str, Any], sub: Optional[Dict[str, Any]]) -> Optional[str]:
        """Por qué este comprobante no se puede contabilizar. None si se puede."""
        if int(venta.get("estado_operacion") or 1) in ESTADOS_ANULADOS:
            return "el comprobante está anulado en SUNAT"

        if sub is None:
            return "no tiene subdiario asignado"

        if not sub.get("listo"):
            faltan = SubdiarioService._que_falta(sub)
            return f"al subdiario {sub['codigo']} le falta {' y '.join(faltan)}"

        con_tributos = [t for t in TRIBUTOS_SIN_CUENTA if _dec(venta.get(t)) != 0]
        if con_tributos:
            return (
                f"lleva {', '.join(con_tributos)} y no hay cuenta configurada para "
                f"esos tributos: imputarlos a ventas sería incorrecto"
            )

        if _dec(venta.get("importe_total")) == 0:
            return "el importe total es cero"

        return None

    # ------------------------------------------------------------------
    # Construcción del asiento
    # ------------------------------------------------------------------

    @staticmethod
    def construir_lineas(venta: Dict[str, Any], sub: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Las líneas del asiento de un comprobante.

        Estructura estándar de una venta:
            12  Cuentas por cobrar    Debe   total
            40  IGV por pagar               Haber   igv
            70  Ventas                      Haber   total - igv

        Una nota de crédito invierte los lados, porque deshace la venta. Se
        detecta por el tipo de comprobante o por un importe negativo, y nunca
        por los dos a la vez: si SUNAT ya manda el importe en negativo, invertir
        además por el tipo lo dejaría como estaba.
        """
        cuentas = sub.get("cuentas") or {}
        total = _dec(venta.get("importe_total"))
        igv = _dec(venta.get("igv_ipm"))

        # Una nota de crédito resta, y hay dos formas de saberlo: por el tipo de
        # comprobante o porque SUNAT ya manda el importe en negativo. Las dos
        # convergen en lo mismo —trabajar en positivo e invertir los lados una
        # sola vez—, así que un comprobante que cumpla las dos no se invierte
        # dos veces y queda como estaba.
        resta = venta.get("tipo_comprobante") in TIPOS_QUE_RESTAN
        if total < 0:
            total, igv = abs(total), abs(igv)
            resta = True

        ingreso = total - igv

        # (cuenta, importe, va_al_debe)
        movimientos = [
            (cuentas.get("cuenta_cobro"), total, True),
            (cuentas.get("cuenta_igv"), igv, False),
            (cuentas.get("cuenta_ingreso"), ingreso, False),
        ]

        lineas = []
        for cuenta, importe, al_debe in movimientos:
            if not cuenta or importe == 0:
                continue
            if resta:
                al_debe = not al_debe
            lineas.append({
                "codigo": cuenta,
                "debe": float(importe) if al_debe else 0.0,
                "haber": 0.0 if al_debe else float(importe),
            })

        return lineas

    @staticmethod
    def _glosa(venta: Dict[str, Any], sub: Dict[str, Any]) -> str:
        """Texto del asiento: quién, con qué documento y por qué subdiario."""
        documento = f"{venta.get('serie_comprobante', '')}-{venta.get('numero_comprobante', '')}"
        cliente = (venta.get("razon_social_cliente") or "").strip()[:60]
        return f"{sub['nombre']} {documento} {cliente}".strip()

    # ------------------------------------------------------------------
    # Previsualización
    # ------------------------------------------------------------------

    async def previsualizar(
        self, empresa_id: str, periodo: str, subdiario: Optional[str] = None
    ) -> Dict[str, Any]:
        """Qué asientos se generarían, y qué comprobantes se quedarían fuera."""
        ventas = await self._pendientes(empresa_id, periodo, subdiario)

        contabilizables, apartados = [], []
        total_debe = Decimal("0")

        for venta in ventas:
            sub = await self._subdiario_de(empresa_id, venta)
            motivo = self._motivo_para_apartar(venta, sub)

            if motivo:
                apartados.append({
                    "comprobante": f"{venta.get('serie_comprobante')}-{venta.get('numero_comprobante')}",
                    "importe": float(_dec(venta.get("importe_total"))),
                    "motivo": motivo,
                })
                continue

            lineas = self.construir_lineas(venta, sub)
            total_debe += Decimal(str(sum(l["debe"] for l in lineas)))
            contabilizables.append({
                "comprobante": f"{venta.get('serie_comprobante')}-{venta.get('numero_comprobante')}",
                "subdiario": sub["codigo"],
                "lineas": lineas,
            })

        return {
            "empresa_id": empresa_id,
            "periodo": periodo,
            "pendientes": len(ventas),
            "contabilizables": len(contabilizables),
            "apartados": len(apartados),
            "total_debe": float(total_debe),
            "detalle_apartados": apartados,
            "muestra": contabilizables[:5],
        }

    async def _subdiario_de(
        self, empresa_id: str, venta: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """El subdiario de una venta: el que tiene asignado, o el que le tocaría."""
        codigo = venta.get("subdiario")
        if codigo:
            try:
                return await self.subdiarios.obtener(empresa_id, codigo)
            except Exception:
                return None

        return await self.subdiarios.subdiario_para_venta(empresa_id, {
            "exportacion": venta.get("valor_facturado_exportacion"),
            "base_gravada": venta.get("base_imponible_gravada"),
            "exonerado": venta.get("importe_exonerado"),
            "inafecto": venta.get("importe_inafecto"),
        })

    # ------------------------------------------------------------------
    # Contabilización
    # ------------------------------------------------------------------

    async def contabilizar(
        self,
        empresa_id: str,
        periodo: str,
        subdiario: Optional[str] = None,
        libro_id: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generar los asientos de las ventas pendientes del periodo.

        Todo el lote comparte un identificador para poder deshacerlo entero.
        Los comprobantes que no se pueden contabilizar se apartan con su motivo
        en vez de bloquear al resto.
        """
        ventas = await self._pendientes(empresa_id, periodo, subdiario)
        if not ventas:
            return {
                "lote": None, "asientos": 0, "lineas": 0, "apartados": [],
                "mensaje": "No hay ventas pendientes de contabilizar en este periodo",
            }

        # Sin libro, el asiento no se ve en ninguna pantalla aunque se guarde.
        if not libro_id:
            libro_id = await self.libro_del_periodo(empresa_id, periodo)

        lote = f"L{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:6]}"
        correlativo = await self._siguiente_correlativo(empresa_id, periodo)
        ahora = datetime.utcnow()

        documentos: List[Dict[str, Any]] = []
        marcas: List[tuple] = []
        apartados: List[Dict[str, Any]] = []

        for venta in ventas:
            sub = await self._subdiario_de(empresa_id, venta)
            motivo = self._motivo_para_apartar(venta, sub)
            if motivo:
                apartados.append({
                    "comprobante": f"{venta.get('serie_comprobante')}-{venta.get('numero_comprobante')}",
                    "motivo": motivo,
                })
                continue

            lineas = self.construir_lineas(venta, sub)

            # El asiento no entra si no cuadra. Se comprueba aquí, antes de
            # insertar nada, porque un libro descuadrado es mucho peor de
            # arreglar que un comprobante apartado.
            debe = sum(l["debe"] for l in lineas)
            haber = sum(l["haber"] for l in lineas)
            if abs(debe - haber) > 0.01 or len(lineas) < 2:
                apartados.append({
                    "comprobante": f"{venta.get('serie_comprobante')}-{venta.get('numero_comprobante')}",
                    "motivo": f"el asiento no cuadra (debe {debe:.2f}, haber {haber:.2f})",
                })
                continue

            numero_asiento = f"{sub['codigo']}-{periodo}-{correlativo}"
            documento = f"{venta.get('serie_comprobante', '')}-{venta.get('numero_comprobante', '')}"
            glosa = self._glosa(venta, sub)

            for linea in lineas:
                documentos.append({
                    "empresaId": empresa_id,
                    "libroId": libro_id,
                    "numeroCorrelativo": str(correlativo).zfill(6),
                    "numeroAsiento": numero_asiento,
                    "fecha": venta.get("fecha_emision"),
                    "glosa": glosa,
                    "codigoLibro": "5.1",
                    # El subdiario es el «libro o registro de origen» que pide el
                    # PLE del Libro Diario. El campo existía y nadie lo llenaba.
                    "codigoLibroOrigen": sub["codigo"],
                    "numeroDocumento": documento,
                    "cuentaContable": {
                        "codigo": linea["codigo"],
                        "denominacion": sub["nombre"],
                    },
                    "debe": linea["debe"],
                    "haber": linea["haber"],
                    "lote_contabilizacion": lote,
                    "origen": "SIRE",
                    "usuarioCreacion": usuario,
                    "fechaCreacion": ahora,
                })
                correlativo += 1

                # Cuentas autogeneradas (cargo/abono) del Plan de Cuentas: ver
                # el mismo bloque en `contabilizacion_compras_service.py`. Un
                # fallo aquí no debe apartar el comprobante entero.
                try:
                    monto = linea["debe"] or linea["haber"] or 0
                    auto_lineas = await lineas_automaticas_por_destino(
                        self.plan_contable_repo, linea["codigo"], monto
                    )
                except Exception as e:
                    logger.error(
                        f"[AUTO_DESTINO] No se pudieron calcular las líneas "
                        f"automáticas de {linea['codigo']} ({documento}): {e}"
                    )
                    auto_lineas = []

                for auto in auto_lineas:
                    documentos.append({
                        "empresaId": empresa_id,
                        "libroId": libro_id,
                        "numeroCorrelativo": str(correlativo).zfill(6),
                        "numeroAsiento": numero_asiento,
                        "fecha": venta.get("fecha_emision"),
                        "glosa": f"{glosa} (auto: destino de {linea['codigo']})",
                        "codigoLibro": "5.1",
                        "codigoLibroOrigen": None,
                        "numeroDocumento": documento,
                        "cuentaContable": auto["cuentaContable"],
                        "debe": auto["debe"],
                        "haber": auto["haber"],
                        "lote_contabilizacion": lote,
                        "origen": "AUTO_DESTINO",
                        "usuarioCreacion": usuario,
                        "fechaCreacion": ahora,
                    })
                    correlativo += 1

            marcas.append((venta["_id"], numero_asiento))

        if documentos:
            await self.asientos.insert_many(documentos)
            await self._actualizar_totales_libro(libro_id)
            for _id, numero in marcas:
                await self.ventas.update_one(
                    {"_id": _id},
                    {"$set": {
                        "asiento_numero": numero,
                        "lote_contabilizacion": lote,
                        "contabilizado_en": ahora,
                    }},
                )

        logger.info(
            f"[CONTABILIZACION] {empresa_id}/{periodo} lote {lote}: "
            f"{len(marcas)} asientos, {len(documentos)} lineas, {len(apartados)} apartados"
        )

        return {
            "lote": lote if documentos else None,
            "asientos": len(marcas),
            "lineas": len(documentos),
            "apartados": apartados,
            "mensaje": (
                f"{len(marcas)} asientos generados en el lote {lote}"
                if documentos else "No se pudo contabilizar ningún comprobante"
            ),
        }

    async def libro_del_periodo(self, empresa_id: str, periodo: str) -> str:
        """
        El libro diario al que pertenecen los asientos del periodo.

        Es obligatorio: los asientos se leen con `find({"libroId": ...})`, así
        que uno sin libro no aparece en ninguna pantalla aunque esté bien
        guardado. Se busca por año o por mes —el esquema admite «2026»,
        «202607» y «2026-07»— y, si no hay ninguno, se crea.
        """
        anio = periodo[:4]
        libros = self.db["libros_diario"]

        libro = await libros.find_one({
            "empresaId": empresa_id,
            "periodo": {"$in": [anio, periodo, f"{anio}-{periodo[4:]}"]},
        })
        if libro:
            return str(libro["_id"])

        empresa = await self.db.companies.find_one({"ruc": empresa_id}) or {}
        resultado = await libros.insert_one({
            "empresaId": empresa_id,
            "ruc": empresa.get("ruc", empresa_id),
            "razonSocial": empresa.get("razon_social", ""),
            "descripcion": f"LIBRO DIARIO {anio}",
            "periodo": anio,
            "estado": "BORRADOR",
            "moneda": "PEN",
            "tipoLibro": "5.1",
            "totalDebe": 0.0,
            "totalHaber": 0.0,
            "fechaCreacion": datetime.utcnow(),
            "usuarioCreacion": "sistema",
        })
        logger.info(f"[CONTABILIZACION] Creado el libro diario {anio} para {empresa_id}")
        return str(resultado.inserted_id)

    async def _actualizar_totales_libro(self, libro_id: Optional[str]) -> None:
        """
        Recalcular el debe y el haber del libro.

        Lo hace el repositorio cuando se agrega un asiento de uno en uno; aquí
        se inserta el lote entero de golpe, así que hay que recalcular al final
        o el libro mostraría unos totales que no corresponden a sus asientos.
        """
        if not libro_id:
            return

        from bson import ObjectId

        totales = await self.asientos.aggregate([
            {"$match": {"libroId": libro_id}},
            {"$group": {
                "_id": None,
                "debe": {"$sum": "$debe"},
                "haber": {"$sum": "$haber"},
            }},
        ]).to_list(1)

        debe = totales[0]["debe"] if totales else 0.0
        haber = totales[0]["haber"] if totales else 0.0

        try:
            await self.db["libros_diario"].update_one(
                {"_id": ObjectId(libro_id)},
                {"$set": {
                    "totalDebe": debe,
                    "totalHaber": haber,
                    "fechaModificacion": datetime.utcnow(),
                }},
            )
        except Exception as e:  # un libro_id ilegible no debe tumbar el lote
            logger.warning(f"[CONTABILIZACION] No se pudieron actualizar los totales: {e}")

    async def _siguiente_correlativo(self, empresa_id: str, periodo: str) -> int:
        """
        Desde qué número seguir.

        Se calcula una sola vez y se va incrementando en memoria: pedirlo por
        cada línea sería lento y, con el índice único por empresa, propenso a
        chocar.

        `numeroCorrelativo` mezcla formatos entre orígenes ("000021" de SIRE,
        "0001-1" del Libro Diario manual): ordenar por el campo como texto
        compara lexicográficamente, así que un `find_one(sort=...)` puede
        devolver un valor con guión, fallar al convertirlo a `int` y caer
        siempre a 1 -chocando con el índice único en cuanto ese "1" ya
        existe-. Se filtra a los puramente numéricos y se comparan como
        número, no como texto.
        """
        resultado = await self.asientos.aggregate([
            {"$match": {"empresaId": empresa_id, "numeroCorrelativo": {"$regex": r"^\d+$"}}},
            {"$addFields": {"_num": {"$toInt": "$numeroCorrelativo"}}},
            {"$sort": {"_num": -1}},
            {"$limit": 1},
        ]).to_list(1)
        return (resultado[0]["_num"] + 1) if resultado else 1

    # ------------------------------------------------------------------
    # Deshacer
    # ------------------------------------------------------------------

    async def deshacer_lote(self, empresa_id: str, lote: str) -> Dict[str, Any]:
        """
        Borrar los asientos de un lote y desmarcar sus ventas.

        Es la red de seguridad de todo el proceso: sin ella, un mapeo de cuentas
        equivocado dejaría decenas de asientos que habría que borrar a mano.
        """
        filtro = {"empresaId": empresa_id, "lote_contabilizacion": lote}

        lineas = await self.asientos.count_documents(filtro)
        if lineas == 0:
            raise ContabilizacionError(
                f"No hay ningún asiento del lote {lote} en esta empresa"
            )

        libros_afectados = await self.asientos.distinct("libroId", filtro)

        await self.asientos.delete_many(filtro)

        for libro in libros_afectados:
            await self._actualizar_totales_libro(libro)

        resultado = await self.ventas.update_many(
            {"empresa_id": empresa_id, "lote_contabilizacion": lote},
            {"$unset": {
                "asiento_numero": "",
                "lote_contabilizacion": "",
                "contabilizado_en": "",
            }},
        )

        logger.info(
            f"[CONTABILIZACION] Lote {lote} deshecho: {lineas} lineas, "
            f"{resultado.modified_count} ventas liberadas"
        )

        return {
            "lote": lote,
            "lineas_eliminadas": lineas,
            "ventas_liberadas": resultado.modified_count,
        }

    async def listar_lotes(self, empresa_id: str, periodo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lotes contabilizados, para poder consultarlos y deshacerlos."""
        filtro: Dict[str, Any] = {"empresa_id": empresa_id, "lote_contabilizacion": {"$ne": None}}
        if periodo:
            filtro["periodo"] = periodo

        pipeline = [
            {"$match": filtro},
            {"$group": {
                "_id": "$lote_contabilizacion",
                "periodo": {"$first": "$periodo"},
                "comprobantes": {"$sum": 1},
                "importe": {"$sum": "$importe_total"},
                "fecha": {"$first": "$contabilizado_en"},
            }},
            {"$sort": {"fecha": -1}},
        ]

        return [
            {
                "lote": d["_id"],
                "periodo": d.get("periodo"),
                "comprobantes": d.get("comprobantes", 0),
                "importe": d.get("importe", 0),
                "fecha": d["fecha"].isoformat() if d.get("fecha") else None,
            }
            async for d in self.ventas.aggregate(pipeline)
        ]
