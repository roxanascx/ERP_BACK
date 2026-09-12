"""
Servicio de Caja/Bancos.

Mantenimiento del catálogo de cuentas y movimientos, más la contabilización:
generar el asiento de cada pago/cobro pendiente en un lote reversible, igual
que `contabilizacion_ventas_service.py` hace para las ventas de SIRE.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.modules.accounting.plan_contable_repository import AccountingRepository
from app.modules.accounting.services.asientos_automaticos import lineas_automaticas_por_destino
from app.modules.accounting.services.catalogo_subdiarios import (
    CUENTA_POR_COBRAR,
    CUENTA_POR_PAGAR,
)

from .catalogos import validar_flujo_efectivo, validar_medio_pago, validar_tipo_documento
from .pendientes import PendientesCajaBancoService
from .repositories import CajaBancoRepository
from .schemas import (
    CuentaCajaBancoCreate,
    CuentaCajaBancoUpdate,
    DocumentoTipo,
    MovimientoCajaBancoCreate,
    TipoCuentaCajaBanco,
    TipoMovimientoCajaBanco,
)

logger = logging.getLogger(__name__)


class CajaBancoNoEncontrada(Exception):
    """La cuenta o el movimiento pedido no existe para esa empresa."""


class CajaBancoDuplicada(Exception):
    """Ya hay una cuenta de caja/banco con ese código en la empresa."""


class CajaBancoError(Exception):
    """Error de negocio (cuenta contable inválida, sin pendientes, etc.)."""


class _MovimientoInvalido(Exception):
    """
    Un movimiento pendiente no tiene datos suficientes para generar su
    asiento (cuenta borrada, o sin documentos aplicados ni contra-cuenta).

    Se usa solo dentro de `contabilizar()`: en vez de tumbar el lote entero
    con un error sin controlar, ese movimiento se aparta y el resto sigue.
    """


class CajaBancoService:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.repo = CajaBancoRepository(database)
        self.plan_contable_repo = AccountingRepository()
        self.pendientes_service = PendientesCajaBancoService(database)
        self.asientos = database["asientos_contables"]
        self.libros = database["libros_diario"]

    # ------------------------------------------------------------------
    # Cuentas
    # ------------------------------------------------------------------

    async def listar_cuentas(
        self, empresa_id: str, solo_activas: bool = False
    ) -> List[Dict[str, Any]]:
        await self.repo.asegurar_indices()
        cuentas = await self.repo.listar_cuentas(empresa_id, solo_activas)
        for cuenta in cuentas:
            cuenta["saldo_actual"] = await self.repo.calcular_saldo(
                empresa_id, cuenta["id"], cuenta.get("saldo_inicial", 0.0)
            )
        return cuentas

    async def obtener_cuenta(self, empresa_id: str, codigo: str) -> Dict[str, Any]:
        doc = await self.repo.obtener_cuenta(empresa_id, codigo)
        if not doc:
            raise CajaBancoNoEncontrada(
                f"No existe la cuenta {codigo} en la empresa {empresa_id}"
            )
        doc["saldo_actual"] = await self.repo.calcular_saldo(
            empresa_id, doc["id"], doc.get("saldo_inicial", 0.0)
        )
        return doc

    async def _validar_cuenta_contable(self, tipo: TipoCuentaCajaBanco, codigo: str) -> None:
        """
        La cuenta contable debe existir y estar marcada para este tipo.

        Es la regla que enlaza este módulo con el Plan de Cuentas (Fase 1):
        una caja solo puede apuntar a una cuenta `es_cuenta_caja`, y un banco a
        una `es_cuenta_bancaria`. Sin esto, cualquier cuenta serviría y el
        Libro Mayor de caja/bancos mezclaría cuentas que no son efectivo.
        """
        cuentas = await self.plan_contable_repo.list_cuentas({"codigo": codigo}, limit=1)
        if not cuentas:
            raise CajaBancoError(f"La cuenta contable {codigo} no existe en el Plan de Cuentas")

        cuenta = cuentas[0]
        campo = "es_cuenta_caja" if tipo == TipoCuentaCajaBanco.CAJA else "es_cuenta_bancaria"
        if not cuenta.get(campo):
            etiqueta = "cuenta de caja" if tipo == TipoCuentaCajaBanco.CAJA else "cuenta bancaria"
            raise CajaBancoError(
                f"La cuenta {codigo} no está marcada como {etiqueta} en el Plan de Cuentas"
            )

    async def crear_cuenta(
        self, empresa_id: str, datos: CuentaCajaBancoCreate, usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        await self.repo.asegurar_indices()

        if await self.repo.obtener_cuenta(empresa_id, datos.codigo):
            raise CajaBancoDuplicada(f"Ya existe la cuenta {datos.codigo} en esta empresa")

        await self._validar_cuenta_contable(datos.tipo, datos.cuenta_contable["codigo"])

        doc = await self.repo.crear_cuenta(empresa_id, datos.model_dump(mode="json"), usuario)
        doc["saldo_actual"] = doc.get("saldo_inicial", 0.0)
        return doc

    async def actualizar_cuenta(
        self,
        empresa_id: str,
        codigo: str,
        cambios: CuentaCajaBancoUpdate,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        datos = cambios.model_dump(mode="json", exclude_unset=True)
        doc = await self.repo.actualizar_cuenta(empresa_id, codigo, datos, usuario)
        if not doc:
            raise CajaBancoNoEncontrada(f"No existe la cuenta {codigo} en la empresa {empresa_id}")
        doc["saldo_actual"] = await self.repo.calcular_saldo(
            empresa_id, doc["id"], doc.get("saldo_inicial", 0.0)
        )
        return doc

    async def eliminar_cuenta(self, empresa_id: str, codigo: str) -> bool:
        cuenta = await self.repo.obtener_cuenta(empresa_id, codigo)
        if not cuenta:
            raise CajaBancoNoEncontrada(f"No existe la cuenta {codigo} en la empresa {empresa_id}")
        if await self.repo.tiene_movimientos(empresa_id, cuenta["id"]):
            raise CajaBancoError(
                f"No se puede eliminar {codigo}: tiene movimientos registrados"
            )
        return await self.repo.eliminar_cuenta(empresa_id, codigo)

    # ------------------------------------------------------------------
    # Movimientos
    # ------------------------------------------------------------------

    async def listar_movimientos(
        self,
        empresa_id: str,
        cuenta_caja_banco_id: Optional[str] = None,
        contabilizado: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        return await self.repo.listar_movimientos(empresa_id, cuenta_caja_banco_id, contabilizado)

    async def listar_pendientes(
        self, empresa_id: str, tipo: DocumentoTipo, socio_negocio_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        pendientes = await self.pendientes_service.listar_pendientes(
            empresa_id, tipo, socio_negocio_id=socio_negocio_id
        )
        return [p.model_dump(mode="json") for p in pendientes]

    async def crear_movimiento(
        self, empresa_id: str, datos: MovimientoCajaBancoCreate, usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        cuenta = await self.repo.obtener_cuenta_por_id(empresa_id, datos.cuenta_caja_banco_id)
        if not cuenta:
            raise CajaBancoNoEncontrada(
                f"No existe la cuenta de caja/banco {datos.cuenta_caja_banco_id}"
            )
        if not cuenta.get("activa", True):
            raise CajaBancoError(f"La cuenta {cuenta['codigo']} está inactiva")

        try:
            validar_tipo_documento(datos.tipo_documento)
            validar_medio_pago(datos.medio_pago)
            validar_flujo_efectivo(datos.flujo_efectivo)
        except ValueError as e:
            raise CajaBancoError(str(e))

        total_aplicado = round(sum(d.monto for d in datos.documentos_aplicados), 2)
        if total_aplicado > datos.monto + 0.01:
            raise CajaBancoError(
                "La suma de los documentos aplicados no puede superar el monto del movimiento"
            )
        remanente = round(datos.monto - total_aplicado, 2)
        if remanente > 0.01 and not datos.contra_cuenta:
            raise CajaBancoError(
                "Falta la contra-cuenta para la parte del importe que no se aplicó a ningún documento"
            )

        # Cada documento debe ser un pendiente real, con saldo suficiente:
        # evita sobre-aplicar un pago (dos cajeros cobrando la misma factura
        # a la vez, o un monto tecleado a mano por encima de lo que se debe).
        for doc_aplicado in datos.documentos_aplicados:
            saldo = await self.pendientes_service.saldo_pendiente(
                doc_aplicado.documento_tipo, doc_aplicado.documento_id
            )
            if saldo is None:
                raise CajaBancoError(f"El documento {doc_aplicado.documento_id} no existe")
            if doc_aplicado.monto > saldo + 0.01:
                raise CajaBancoError(
                    f"El documento {doc_aplicado.documento_id} tiene un saldo pendiente de "
                    f"{saldo:.2f}, menor al monto que se le quiere aplicar ({doc_aplicado.monto:.2f})"
                )

        movimiento = await self.repo.crear_movimiento(empresa_id, datos.model_dump(mode="json"), usuario)
        await self.repo.crear_aplicaciones(
            empresa_id,
            movimiento["id"],
            [d.model_dump(mode="json") for d in datos.documentos_aplicados],
        )
        return movimiento

    # ------------------------------------------------------------------
    # Contabilización: del movimiento al asiento, en lote reversible
    # ------------------------------------------------------------------

    async def _libro_del_periodo(self, empresa_id: str, periodo: str) -> str:
        """Igual que `ContabilizacionVentasService.libro_del_periodo`: sin
        libro, el asiento no aparece en ninguna pantalla aunque se guarde."""
        anio = periodo[:4]
        libro = await self.libros.find_one({
            "empresaId": empresa_id,
            "periodo": {"$in": [anio, periodo, f"{anio}-{periodo[4:]}"]},
        })
        if libro:
            return str(libro["_id"])

        empresa = await self.db.companies.find_one({"ruc": empresa_id}) or {}
        resultado = await self.libros.insert_one({
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
        })
        return str(resultado.inserted_id)

    async def _siguiente_correlativo(self, empresa_id: str) -> int:
        """
        El correlativo más alto YA USADO por esta empresa, más uno.

        `numeroCorrelativo` mezcla formatos entre orígenes: "000021" (SIRE),
        "0001-1" (Libro Diario manual), "0001-1-auto1" (cargo/abono
        automático). Ordenar por el campo como texto compara
        lexicográficamente -"0001-1" sale "mayor" que "000021"- así que un
        `find_one(sort=...)` puede devolver un valor con guión, fallar al
        convertirlo a `int` y caer siempre a 1, chocando con el índice único
        (empresaId, numeroCorrelativo) en cuanto ese "1" ya existe. Se filtra
        a los puramente numéricos y se comparan como número, no como texto.
        """
        resultado = await self.asientos.aggregate([
            {"$match": {"empresaId": empresa_id, "numeroCorrelativo": {"$regex": r"^\d+$"}}},
            {"$addFields": {"_num": {"$toInt": "$numeroCorrelativo"}}},
            {"$sort": {"_num": -1}},
            {"$limit": 1},
        ]).to_list(1)
        return (resultado[0]["_num"] + 1) if resultado else 1

    async def _actualizar_totales_libro(self, libro_id: Optional[str]) -> None:
        if not libro_id:
            return
        totales = await self.asientos.aggregate([
            {"$match": {"libroId": libro_id}},
            {"$group": {"_id": None, "debe": {"$sum": "$debe"}, "haber": {"$sum": "$haber"}}},
        ]).to_list(1)
        debe = totales[0]["debe"] if totales else 0.0
        haber = totales[0]["haber"] if totales else 0.0
        try:
            await self.libros.update_one(
                {"_id": ObjectId(libro_id)},
                {"$set": {"totalDebe": debe, "totalHaber": haber}},
            )
        except Exception as e:  # pragma: no cover
            logger.warning(f"No se pudo actualizar totales del libro {libro_id}: {e}")

    async def _cuenta_del_documento(
        self, empresa_id: str, documento_tipo: str, documento_id: str
    ) -> Dict[str, str]:
        """
        La cuenta contable real con la que se contabilizó ese documento (la
        línea 42.../12... de su asiento original), no una inventada: se busca
        en `asientos_contables` la línea de esa compra/venta (por su
        serie-número) del lado que corresponde -haber en compras, debe en
        ventas, que es donde queda la cuenta por pagar/cobrar-.

        Si el documento nunca se contabilizó (dato inconsistente: no debería
        poder generar un pendiente con saldo real), se usa la cuenta por
        defecto del subdiario estándar como respaldo, para que el asiento de
        todos modos tenga a dónde ir.
        """
        coleccion = self.pendientes_service.compras if documento_tipo == "COMPRA" else self.pendientes_service.ventas
        try:
            doc = await coleccion.find_one({"_id": ObjectId(documento_id)})
        except Exception:
            doc = None

        if doc:
            etiqueta = f"{doc.get('serie_comprobante', '')}-{doc.get('numero_comprobante', '')}"
            lado = "haber" if documento_tipo == "COMPRA" else "debe"
            linea = await self.asientos.find_one({
                "empresaId": empresa_id,
                "numeroDocumento": etiqueta,
                lado: {"$gt": 0},
            })
            if linea and linea.get("cuentaContable"):
                return linea["cuentaContable"]

        codigo = CUENTA_POR_PAGAR if documento_tipo == "COMPRA" else CUENTA_POR_COBRAR
        nombre = (
            "Cuentas por pagar comerciales - Terceros"
            if documento_tipo == "COMPRA"
            else "Cuentas por cobrar comerciales - Terceros"
        )
        return {"codigo": codigo, "denominacion": nombre}

    async def contabilizar(
        self,
        empresa_id: str,
        cuenta_caja_banco_id: Optional[str] = None,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generar el asiento de cada movimiento pendiente.

        Un ingreso carga la cuenta de caja/banco y abona la contra-cuenta; un
        egreso es al revés. Todo el lote comparte un identificador para poder
        deshacerlo entero, igual que la contabilización de ventas/compras. Un
        movimiento a medio configurar se aparta (ver `_construir_lineas`) en
        vez de tumbar con un error sin controlar la contabilización de todo
        el lote, incluidos los demás movimientos que sí estaban bien.
        """
        pendientes = await self.repo.listar_movimientos(
            empresa_id, cuenta_caja_banco_id, contabilizado=False
        )
        if not pendientes:
            return {
                "lote": None, "asientos": 0, "lineas": 0, "apartados": [],
                "mensaje": "No hay movimientos pendientes de contabilizar",
            }

        lote = f"CB{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:6]}"
        correlativo = await self._siguiente_correlativo(empresa_id)
        ahora = datetime.utcnow()

        documentos: List[Dict[str, Any]] = []
        marcas: List[tuple] = []
        libros_afectados: set = set()
        apartados: List[Dict[str, Any]] = []

        for mov in pendientes:
            try:
                lineas, correlativo, numero_asiento, libro_id = await self._construir_lineas(
                    mov, empresa_id, lote, ahora, correlativo, usuario
                )
            except _MovimientoInvalido as e:
                apartados.append({"movimiento": mov["id"], "motivo": str(e)})
                logger.warning(f"[CAJA_BANCOS] Movimiento {mov['id']} apartado: {e}")
                continue

            documentos.extend(lineas)
            libros_afectados.add(libro_id)
            marcas.append((mov["id"], numero_asiento))

        if not documentos:
            return {
                "lote": None, "asientos": 0, "lineas": 0, "apartados": apartados,
                "mensaje": (
                    "Ningún movimiento pendiente se pudo contabilizar"
                    if apartados
                    else "Ningún movimiento pendiente tiene una cuenta de caja/banco válida"
                ),
            }

        await self.asientos.insert_many(documentos)
        for libro_id in libros_afectados:
            await self._actualizar_totales_libro(libro_id)

        for movimiento_id, numero_asiento in marcas:
            await self.repo.movimientos.update_one(
                {"_id": ObjectId(movimiento_id)},
                {"$set": {
                    "contabilizado": True,
                    "lote_contabilizacion": lote,
                    "numeroAsiento": numero_asiento,
                }},
            )

        logger.info(
            f"[CAJA_BANCOS] {empresa_id} lote {lote}: "
            f"{len(marcas)} movimientos, {len(documentos)} líneas, {len(apartados)} apartados"
        )

        return {
            "lote": lote,
            "asientos": len(marcas),
            "lineas": len(documentos),
            "apartados": apartados,
            "mensaje": f"Se contabilizaron {len(marcas)} movimientos",
        }

    async def _construir_lineas(
        self,
        mov: Dict[str, Any],
        empresa_id: str,
        lote: str,
        ahora: datetime,
        correlativo: int,
        usuario: Optional[str],
    ) -> "tuple[List[Dict[str, Any]], int, str, str]":
        """
        Arma las líneas de asiento de UN movimiento.

        Devuelve `(lineas, siguiente_correlativo, numeroAsiento, libroId)`.
        Lanza `_MovimientoInvalido` si el movimiento no tiene a dónde
        contabilizarse (cuenta de caja/banco borrada, o sin documentos
        aplicados ni contra-cuenta): antes esto producía un error sin
        controlar (`None["codigo"]`) que tumbaba la contabilización completa
        del lote en vez de apartar solo ese movimiento.
        """
        cuenta = await self.repo.obtener_cuenta_por_id(empresa_id, mov["cuenta_caja_banco_id"])
        if not cuenta:
            raise _MovimientoInvalido("la cuenta de caja/banco ya no existe")

        periodo = mov["fecha"][:7].replace("-", "")
        libro_id = await self._libro_del_periodo(empresa_id, periodo)

        numero_asiento = f"CB-{periodo}-{correlativo}"
        documento_ref = mov.get("documento_referencia") or numero_asiento
        monto = mov["monto"]
        es_ingreso = mov["tipo"] == TipoMovimientoCajaBanco.INGRESO.value

        linea_caja = {
            "debe": monto if es_ingreso else 0.0,
            "haber": 0.0 if es_ingreso else monto,
            "cuentaContable": cuenta["cuenta_contable"],
        }

        # La contrapartida: una línea por cada cuenta CxP/CxR real de los
        # documentos que este movimiento cancela (fusionando los que
        # comparten cuenta), más una línea final por lo que no se aplicó a
        # ningún documento (contra_cuenta, si sobró algo por aplicar).
        documentos_aplicados = mov.get("documentos_aplicados") or []
        lineas_contra: List[Dict[str, Any]] = []

        if documentos_aplicados:
            acumulado_por_cuenta: Dict[str, Dict[str, Any]] = {}
            for doc_aplicado in documentos_aplicados:
                cuenta_doc = await self._cuenta_del_documento(
                    empresa_id, doc_aplicado["documento_tipo"], doc_aplicado["documento_id"]
                )
                entrada = acumulado_por_cuenta.setdefault(
                    cuenta_doc["codigo"], {"cuentaContable": cuenta_doc, "monto": 0.0}
                )
                entrada["monto"] += doc_aplicado["monto"]

            for acumulado in acumulado_por_cuenta.values():
                m = acumulado["monto"]
                lineas_contra.append({
                    "cuentaContable": acumulado["cuentaContable"],
                    "debe": 0.0 if es_ingreso else m,
                    "haber": m if es_ingreso else 0.0,
                })

            remanente = round(monto - sum(d["monto"] for d in documentos_aplicados), 2)
            if remanente > 0.01:
                contra_cuenta = mov.get("contra_cuenta")
                if not contra_cuenta or not contra_cuenta.get("codigo"):
                    raise _MovimientoInvalido(
                        f"sobran {remanente:.2f} sin aplicar a ningún documento y no tiene contra-cuenta"
                    )
                lineas_contra.append({
                    "cuentaContable": contra_cuenta,
                    "debe": 0.0 if es_ingreso else remanente,
                    "haber": remanente if es_ingreso else 0.0,
                })
        else:
            contra_cuenta = mov.get("contra_cuenta")
            if not contra_cuenta or not contra_cuenta.get("codigo"):
                raise _MovimientoInvalido("no tiene documentos aplicados ni contra-cuenta")
            lineas_contra.append({
                "cuentaContable": contra_cuenta,
                "debe": 0.0 if es_ingreso else monto,
                "haber": monto if es_ingreso else 0.0,
            })

        lineas: List[Dict[str, Any]] = []
        for linea in (linea_caja, *lineas_contra):
            lineas.append({
                "empresaId": empresa_id,
                "libroId": libro_id,
                "numeroCorrelativo": str(correlativo).zfill(6),
                "numeroAsiento": numero_asiento,
                "fecha": mov["fecha"],
                "glosa": mov["glosa"],
                "codigoLibro": "5.1",
                "codigoLibroOrigen": "CB",
                "numeroDocumento": documento_ref,
                "cuentaContable": linea["cuentaContable"],
                "centroCosto": mov.get("centro_costo"),
                "debe": linea["debe"],
                "haber": linea["haber"],
                "lote_contabilizacion": lote,
                "origen": "CAJA_BANCOS",
                "usuarioCreacion": usuario,
                "fechaCreacion": ahora,
            })
            correlativo += 1

            # Cuentas autogeneradas (cargo/abono) del Plan de Cuentas: mismo
            # motor que Compras/Ventas/Libro Diario. Un fallo aquí no debe
            # apartar el movimiento entero.
            try:
                monto_linea = linea["debe"] or linea["haber"] or 0
                auto_lineas = await lineas_automaticas_por_destino(
                    self.plan_contable_repo, linea["cuentaContable"]["codigo"], monto_linea
                )
            except Exception as e:
                logger.error(
                    f"[AUTO_DESTINO] No se pudieron calcular las líneas automáticas de "
                    f"{linea['cuentaContable'].get('codigo')} (movimiento {mov['id']}): {e}"
                )
                auto_lineas = []

            for auto in auto_lineas:
                lineas.append({
                    "empresaId": empresa_id,
                    "libroId": libro_id,
                    "numeroCorrelativo": str(correlativo).zfill(6),
                    "numeroAsiento": numero_asiento,
                    "fecha": mov["fecha"],
                    "glosa": f"{mov['glosa']} (auto: destino de {linea['cuentaContable']['codigo']})",
                    "codigoLibro": "5.1",
                    "codigoLibroOrigen": None,
                    "numeroDocumento": documento_ref,
                    "cuentaContable": auto["cuentaContable"],
                    "centroCosto": mov.get("centro_costo"),
                    "debe": auto["debe"],
                    "haber": auto["haber"],
                    "lote_contabilizacion": lote,
                    "origen": "AUTO_DESTINO",
                    "usuarioCreacion": usuario,
                    "fechaCreacion": ahora,
                })
                correlativo += 1

        return lineas, correlativo, numero_asiento, libro_id

    async def deshacer_lote(self, empresa_id: str, lote: str) -> Dict[str, Any]:
        filtro = {"empresaId": empresa_id, "lote_contabilizacion": lote}

        lineas = await self.asientos.count_documents(filtro)
        if lineas == 0:
            raise CajaBancoError(f"No hay ningún asiento del lote {lote} en esta empresa")

        libros_afectados = await self.asientos.distinct("libroId", filtro)
        await self.asientos.delete_many(filtro)
        for libro_id in libros_afectados:
            await self._actualizar_totales_libro(libro_id)

        resultado = await self.repo.movimientos.update_many(
            {"empresa_id": empresa_id, "lote_contabilizacion": lote},
            {"$set": {"contabilizado": False},
             "$unset": {"lote_contabilizacion": "", "numeroAsiento": ""}},
        )

        return {
            "lote": lote,
            "lineas_eliminadas": lineas,
            "movimientos_liberados": resultado.modified_count,
        }
