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

from .repositories import CajaBancoRepository
from .schemas import (
    CuentaCajaBancoCreate,
    CuentaCajaBancoUpdate,
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


class CajaBancoService:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.repo = CajaBancoRepository(database)
        self.plan_contable_repo = AccountingRepository()
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

        return await self.repo.crear_movimiento(empresa_id, datos.model_dump(mode="json"), usuario)

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
        ultimo = await self.asientos.find_one(
            {"empresaId": empresa_id}, sort=[("numeroCorrelativo", -1)]
        )
        if not ultimo:
            return 1
        try:
            return int(ultimo["numeroCorrelativo"]) + 1
        except (KeyError, TypeError, ValueError):
            return 1

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
        deshacerlo entero, igual que la contabilización de ventas/compras.
        """
        pendientes = await self.repo.listar_movimientos(
            empresa_id, cuenta_caja_banco_id, contabilizado=False
        )
        if not pendientes:
            return {
                "lote": None, "asientos": 0, "lineas": 0,
                "mensaje": "No hay movimientos pendientes de contabilizar",
            }

        lote = f"CB{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:6]}"
        correlativo = await self._siguiente_correlativo(empresa_id)
        ahora = datetime.utcnow()

        documentos: List[Dict[str, Any]] = []
        marcas: List[tuple] = []
        libros_afectados: set = set()

        for mov in pendientes:
            cuenta = await self.repo.obtener_cuenta_por_id(empresa_id, mov["cuenta_caja_banco_id"])
            if not cuenta:
                continue

            periodo = mov["fecha"][:7].replace("-", "")
            libro_id = await self._libro_del_periodo(empresa_id, periodo)
            libros_afectados.add(libro_id)

            numero_asiento = f"CB-{periodo}-{correlativo}"
            documento_ref = mov.get("documento_referencia") or numero_asiento
            monto = mov["monto"]
            es_ingreso = mov["tipo"] == TipoMovimientoCajaBanco.INGRESO.value

            linea_caja = {
                "debe": monto if es_ingreso else 0.0,
                "haber": 0.0 if es_ingreso else monto,
                "cuentaContable": cuenta["cuenta_contable"],
            }
            linea_contra = {
                "debe": 0.0 if es_ingreso else monto,
                "haber": monto if es_ingreso else 0.0,
                "cuentaContable": mov["contra_cuenta"],
            }

            for linea in (linea_caja, linea_contra):
                documentos.append({
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

            marcas.append((mov["id"], numero_asiento))

        if not documentos:
            return {
                "lote": None, "asientos": 0, "lineas": 0,
                "mensaje": "Ningún movimiento pendiente tiene una cuenta de caja/banco válida",
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
            f"{len(marcas)} movimientos, {len(documentos)} líneas"
        )

        return {
            "lote": lote,
            "asientos": len(marcas),
            "lineas": len(documentos),
            "mensaje": f"Se contabilizaron {len(marcas)} movimientos",
        }

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
