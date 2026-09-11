"""
Contabilización de las compras: del registro de compras al libro diario.

Segundo paso del puente SIRE → contabilidad por el lado de compras. Espejo de
`contabilizacion_ventas_service`, con las mismas tres garantías: lotes que se
deshacen enteros, nada se contabiliza dos veces, y ningún asiento entra
descuadrado.

El asiento estándar de una compra gravada:

    60/63  Compras o gastos      Debe   total - IGV
    40     IGV crédito fiscal    Debe   IGV
    42     Cuentas por pagar            Haber  total

**Dónde se separa de ventas.** En ventas, el ISC, el IVAP y el ICBPER son
tributos que la empresa cobra y le debe a SUNAT: necesitan cuenta propia, y por
eso un comprobante que los traiga se aparta. En compras es al revés: son
tributos que la empresa **paga** y que no se recuperan, así que forman parte del
costo de la adquisición y entran en la cuenta de gasto. No hay nada que apartar.

De ahí que el gasto se calcule como `total - IGV aplicado` y no sumando bases:
así el asiento cuadra por construcción, lleve el comprobante los tributos que
lleve.

**El caso del subdiario 14** (sin derecho a crédito fiscal): el IGV existe pero
no se puede usar como crédito, así que no va a la cuenta 40 sino al costo. El
asiento queda con dos líneas y el gasto absorbe el total.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.schemas_subdiario import NaturalezaCompra
from .subdiario_service import SubdiarioService

logger = logging.getLogger(__name__)

#: Comprobantes que restan en vez de sumar: la nota de crédito deshace la compra.
TIPOS_QUE_RESTAN = {"07"}

#: Estados de SUNAT que significan que el comprobante no debe contabilizarse.
#: En compras llegan como texto, a diferencia de ventas.
ESTADOS_ANULADOS = {"2", "9"}

#: Naturalezas en las que el IGV **no** va a la cuenta 40. En la primera porque
#: la ley no da derecho a crédito fiscal y en la segunda porque no hay IGV.
SIN_CREDITO_FISCAL = {
    NaturalezaCompra.SIN_DERECHO_CREDITO.value,
    NaturalezaCompra.NO_GRAVADA.value,
}


class ContabilizacionError(Exception):
    """No se puede contabilizar, y el mensaje explica por qué."""


def _fecha_iso(valor: Any) -> str:
    """La fecha del asiento, siempre como texto YYYY-MM-DD."""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor or "")[:10]


def _dec(valor: Any) -> Decimal:
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal("0")


class ContabilizacionComprasService:
    """Genera los asientos del libro diario a partir del registro de compras."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.compras = database.registro_compras
        self.asientos = database["asientos_contables"]
        self.subdiarios = SubdiarioService(database)

    # ------------------------------------------------------------------
    # Selección de lo pendiente
    # ------------------------------------------------------------------

    async def _pendientes(
        self, empresa_id: str, periodo: str, subdiario: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Compras del periodo que todavía no han generado asiento.

        `asiento_numero` es la marca: en cuanto una compra se contabiliza, deja
        de aparecer aquí. Es lo que impide contabilizar dos veces.
        """
        filtro: Dict[str, Any] = {
            "empresa_id": empresa_id,
            "periodo": periodo,
            "asiento_numero": {"$in": [None, ""]},
        }
        if subdiario:
            filtro["subdiario"] = subdiario

        return [doc async for doc in self.compras.find(filtro).sort("fecha_comprobante", 1)]

    @staticmethod
    def _motivo_para_apartar(
        compra: Dict[str, Any], sub: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Por qué este comprobante no se puede contabilizar. None si se puede."""
        if str(compra.get("estado_operacion") or "1").strip() in ESTADOS_ANULADOS:
            return "el comprobante está anulado en SUNAT"

        if sub is None:
            return "no tiene subdiario asignado"

        if not sub.get("listo"):
            faltan = SubdiarioService._que_falta(sub)
            return f"al subdiario {sub['codigo']} le falta {' y '.join(faltan)}"

        if _dec(compra.get("importe_total")) == 0:
            return "el importe total es cero"

        return None

    # ------------------------------------------------------------------
    # Construcción del asiento
    # ------------------------------------------------------------------

    @staticmethod
    def construir_lineas(compra: Dict[str, Any], sub: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Las líneas del asiento de un comprobante de compra.

            60/63  Compras o gastos      Debe   total - IGV
            40     IGV crédito fiscal    Debe   IGV
            42     Cuentas por pagar            Haber  total

        El gasto sale de restar, no de sumar bases: así el ISC, el ICBPER y los
        demás tributos no recuperables quedan dentro del costo —que es donde van
        en una compra— y el asiento cuadra sea cual sea la mezcla de importes.

        Si el subdiario no lleva crédito fiscal, el IGV se queda en el costo y el
        asiento tiene solo dos líneas.

        Una nota de crédito invierte los lados, porque deshace la compra. Se
        detecta por el tipo de comprobante o por un importe negativo, y nunca por
        los dos a la vez: si SUNAT ya manda el importe en negativo, invertir
        además por el tipo lo dejaría como estaba.
        """
        cuentas = sub.get("cuentas") or {}
        total = _dec(compra.get("importe_total"))
        igv = _dec(compra.get("igv"))

        resta = compra.get("tipo_comprobante") in TIPOS_QUE_RESTAN
        if total < 0:
            total, igv = abs(total), abs(igv)
            resta = True

        # El IGV solo se separa del costo si hay derecho a crédito fiscal **y**
        # el subdiario tiene cuenta donde ponerlo. Si falta cualquiera de las
        # dos, se queda en el gasto: es preferible a perderlo o a descuadrar.
        cuenta_igv = cuentas.get("cuenta_igv")
        hay_credito = (
            bool(cuenta_igv)
            and sub.get("naturaleza_compra") not in SIN_CREDITO_FISCAL
        )
        igv_aplicado = igv if hay_credito else Decimal("0")

        gasto = total - igv_aplicado

        # (cuenta, importe, va_al_debe)
        movimientos = [
            (cuentas.get("cuenta_gasto"), gasto, True),
            (cuenta_igv if hay_credito else None, igv_aplicado, True),
            (cuentas.get("cuenta_pago"), total, False),
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
    def _glosa(compra: Dict[str, Any], sub: Dict[str, Any]) -> str:
        """Texto del asiento: quién, con qué documento y por qué subdiario."""
        documento = (
            f"{compra.get('serie_comprobante', '')}-{compra.get('numero_comprobante', '')}"
        )
        proveedor = (compra.get("razon_social_proveedor") or "").strip()[:60]
        return f"{sub['nombre']} {documento} {proveedor}".strip()

    # ------------------------------------------------------------------
    # Previsualización
    # ------------------------------------------------------------------

    async def previsualizar(
        self, empresa_id: str, periodo: str, subdiario: Optional[str] = None
    ) -> Dict[str, Any]:
        """Qué asientos se generarían, y qué comprobantes se quedarían fuera."""
        compras = await self._pendientes(empresa_id, periodo, subdiario)

        contabilizables, apartados = [], []
        total_debe = Decimal("0")

        for compra in compras:
            sub = await self._subdiario_de(empresa_id, compra)
            motivo = self._motivo_para_apartar(compra, sub)

            if motivo:
                apartados.append({
                    "comprobante": (
                        f"{compra.get('serie_comprobante')}-{compra.get('numero_comprobante')}"
                    ),
                    "importe": float(_dec(compra.get("importe_total"))),
                    "motivo": motivo,
                })
                continue

            lineas = self.construir_lineas(compra, sub)
            total_debe += Decimal(str(sum(l["debe"] for l in lineas)))
            contabilizables.append({
                "comprobante": (
                    f"{compra.get('serie_comprobante')}-{compra.get('numero_comprobante')}"
                ),
                "subdiario": sub["codigo"],
                "lineas": lineas,
            })

        return {
            "empresa_id": empresa_id,
            "periodo": periodo,
            "pendientes": len(compras),
            "contabilizables": len(contabilizables),
            "apartados": len(apartados),
            "total_debe": float(total_debe),
            "detalle_apartados": apartados,
            "muestra": contabilizables[:5],
        }

    async def _subdiario_de(
        self, empresa_id: str, compra: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """El subdiario de una compra: el que tiene asignado, o el que le tocaría."""
        codigo = compra.get("subdiario")
        if codigo:
            try:
                return await self.subdiarios.obtener(empresa_id, codigo)
            except Exception:
                return None

        return await self.subdiarios.subdiario_para_compra(empresa_id, {
            "base_gravada": compra.get("base_imponible_gravada"),
            "no_gravada": compra.get("base_imponible_no_gravada"),
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
        Generar los asientos de las compras pendientes del periodo.

        Todo el lote comparte un identificador para poder deshacerlo entero. Los
        comprobantes que no se pueden contabilizar se apartan con su motivo en
        vez de bloquear al resto.
        """
        compras = await self._pendientes(empresa_id, periodo, subdiario)
        if not compras:
            return {
                "lote": None, "asientos": 0, "lineas": 0, "apartados": [],
                "mensaje": "No hay compras pendientes de contabilizar en este periodo",
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

        for compra in compras:
            etiqueta = (
                f"{compra.get('serie_comprobante')}-{compra.get('numero_comprobante')}"
            )

            sub = await self._subdiario_de(empresa_id, compra)
            motivo = self._motivo_para_apartar(compra, sub)
            if motivo:
                apartados.append({"comprobante": etiqueta, "motivo": motivo})
                continue

            lineas = self.construir_lineas(compra, sub)

            # El asiento no entra si no cuadra. Se comprueba aquí, antes de
            # insertar nada, porque un libro descuadrado es mucho peor de
            # arreglar que un comprobante apartado.
            debe = sum(l["debe"] for l in lineas)
            haber = sum(l["haber"] for l in lineas)
            if abs(debe - haber) > 0.01 or len(lineas) < 2:
                apartados.append({
                    "comprobante": etiqueta,
                    "motivo": f"el asiento no cuadra (debe {debe:.2f}, haber {haber:.2f})",
                })
                continue

            numero_asiento = f"{sub['codigo']}-{periodo}-{correlativo}"
            glosa = self._glosa(compra, sub)
            # El registro de compras guarda la fecha como `datetime` para poder
            # filtrar por rango; el asiento la quiere en ISO, como la escribe
            # ventas. Copiarla tal cual hacia que el libro entero devolviera 404.
            fecha = _fecha_iso(compra.get("fecha_comprobante"))

            for linea in lineas:
                documentos.append({
                    "empresaId": empresa_id,
                    "libroId": libro_id,
                    "numeroCorrelativo": str(correlativo).zfill(6),
                    "numeroAsiento": numero_asiento,
                    "fecha": fecha,
                    "glosa": glosa,
                    "codigoLibro": "5.1",
                    # El subdiario es el «libro o registro de origen» que pide el
                    # PLE del Libro Diario.
                    "codigoLibroOrigen": sub["codigo"],
                    "numeroDocumento": etiqueta,
                    "cuentaContable": {
                        "codigo": linea["codigo"],
                        "denominacion": sub["nombre"],
                    },
                    "debe": linea["debe"],
                    "haber": linea["haber"],
                    "lote_contabilizacion": lote,
                    "origen": compra.get("origen") or "SIRE",
                    "usuarioCreacion": usuario,
                    "fechaCreacion": ahora,
                })
                correlativo += 1

            marcas.append((compra["_id"], numero_asiento))

        if documentos:
            await self.asientos.insert_many(documentos)
            await self._actualizar_totales_libro(libro_id)
            for _id, numero in marcas:
                await self.compras.update_one(
                    {"_id": _id},
                    {"$set": {
                        "asiento_numero": numero,
                        "lote_contabilizacion": lote,
                        "contabilizado_en": ahora,
                    }},
                )

        logger.info(
            f"[CONTABILIZACION COMPRAS] {empresa_id}/{periodo} lote {lote}: "
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
        guardado. Se busca por año o por mes y, si no hay ninguno, se crea.

        Compras y ventas del mismo periodo comparten libro a propósito: el libro
        diario es uno solo, y lo que distingue el origen de cada asiento es el
        `codigoLibroOrigen`, que lleva el código del subdiario.
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
        logger.info(f"[CONTABILIZACION COMPRAS] Creado el libro diario {anio} para {empresa_id}")
        return str(resultado.inserted_id)

    async def _actualizar_totales_libro(self, libro_id: Optional[str]) -> None:
        """
        Recalcular el debe y el haber del libro.

        Se inserta el lote entero de golpe, así que hay que recalcular al final o
        el libro mostraría unos totales que no corresponden a sus asientos.
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
            logger.warning(
                f"[CONTABILIZACION COMPRAS] No se pudieron actualizar los totales: {e}"
            )

    async def _siguiente_correlativo(self, empresa_id: str, periodo: str) -> int:
        """
        Desde qué número seguir.

        Se calcula una sola vez y se va incrementando en memoria: pedirlo por
        cada línea sería lento y propenso a chocar. El correlativo es común a
        ventas y compras porque el libro diario también lo es.
        """
        ultimo = await self.asientos.find_one(
            {"empresaId": empresa_id},
            sort=[("numeroCorrelativo", -1)],
        )
        if not ultimo:
            return 1
        try:
            return int(ultimo["numeroCorrelativo"]) + 1
        except (KeyError, TypeError, ValueError):
            return 1

    # ------------------------------------------------------------------
    # Deshacer
    # ------------------------------------------------------------------

    async def deshacer_lote(self, empresa_id: str, lote: str) -> Dict[str, Any]:
        """
        Borrar los asientos de un lote y desmarcar sus compras.

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

        liberadas = await self.compras.update_many(
            {"empresa_id": empresa_id, "lote_contabilizacion": lote},
            {"$unset": {
                "asiento_numero": "",
                "lote_contabilizacion": "",
                "contabilizado_en": "",
            }},
        )

        logger.info(
            f"[CONTABILIZACION COMPRAS] Lote {lote} deshecho: {lineas} lineas "
            f"borradas, {liberadas.modified_count} compras liberadas"
        )

        return {
            "lote": lote,
            "lineas_eliminadas": lineas,
            "compras_liberadas": liberadas.modified_count,
        }

    async def listar_lotes(
        self, empresa_id: str, periodo: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lotes de compras generados, del más reciente al más antiguo."""
        filtro: Dict[str, Any] = {
            "empresa_id": empresa_id,
            "lote_contabilizacion": {"$ne": None},
        }
        if periodo:
            filtro["periodo"] = periodo

        agrupados = await self.compras.aggregate([
            {"$match": filtro},
            {"$group": {
                "_id": "$lote_contabilizacion",
                "periodo": {"$first": "$periodo"},
                "comprobantes": {"$sum": 1},
                "importe": {"$sum": "$importe_total"},
                "fecha": {"$max": "$contabilizado_en"},
            }},
            {"$sort": {"fecha": -1}},
        ]).to_list(length=None)

        return [
            {
                "lote": g["_id"],
                "periodo": g.get("periodo"),
                "comprobantes": g.get("comprobantes", 0),
                "importe": g.get("importe", 0.0),
                "fecha": g.get("fecha").isoformat() if g.get("fecha") else None,
            }
            for g in agrupados
        ]
