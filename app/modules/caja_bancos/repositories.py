"""
Persistencia de cuentas y movimientos de Caja/Bancos.

Un documento por (empresa, código) en `cuentas_caja_banco`, y un documento por
movimiento en `movimientos_caja_banco`. El saldo de una cuenta no se guarda:
se calcula sumando sus movimientos sobre el saldo inicial (`calcular_saldo`),
para no duplicar estado con la fuente real.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class CajaBancoRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.cuentas = database["cuentas_caja_banco"]
        self.movimientos = database["movimientos_caja_banco"]
        self.aplicaciones = database["aplicaciones_pago_caja_bancos"]

    async def asegurar_indices(self) -> None:
        try:
            await self.cuentas.create_index(
                [("empresa_id", 1), ("codigo", 1)],
                unique=True,
                name="idx_empresa_codigo_cuenta_caja_banco",
            )
            await self.movimientos.create_index(
                [("empresa_id", 1), ("cuenta_caja_banco_id", 1)],
                name="idx_empresa_cuenta_movimiento_caja_banco",
            )
            await self.movimientos.create_index(
                [("empresa_id", 1), ("lote_contabilizacion", 1)],
                name="idx_empresa_lote_movimiento_caja_banco",
            )
            await self.aplicaciones.create_index(
                [("documento_tipo", 1), ("documento_id", 1)],
                name="idx_documento_aplicacion_pago",
            )
        except Exception as e:  # pragma: no cover - depende del estado de Mongo
            logger.warning(f"No se pudo crear índices de caja/bancos: {e}")

    # ------------------------------------------------------------------
    # Cuentas
    # ------------------------------------------------------------------

    async def listar_cuentas(
        self, empresa_id: str, solo_activas: bool = False
    ) -> List[Dict[str, Any]]:
        filtro: Dict[str, Any] = {"empresa_id": empresa_id}
        if solo_activas:
            filtro["activa"] = True
        cursor = self.cuentas.find(filtro).sort("codigo", 1)
        return [self._limpiar(d) async for d in cursor]

    async def obtener_cuenta(self, empresa_id: str, codigo: str) -> Optional[Dict[str, Any]]:
        doc = await self.cuentas.find_one({"empresa_id": empresa_id, "codigo": codigo})
        return self._limpiar(doc) if doc else None

    async def obtener_cuenta_por_id(
        self, empresa_id: str, cuenta_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(cuenta_id)
        except InvalidId:
            return None
        doc = await self.cuentas.find_one({"empresa_id": empresa_id, "_id": oid})
        return self._limpiar(doc) if doc else None

    async def crear_cuenta(
        self, empresa_id: str, datos: Dict[str, Any], usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        documento = {
            **datos,
            "empresa_id": empresa_id,
            "creado_en": datetime.utcnow(),
            "creado_por": usuario,
            "modificado_en": None,
            "modificado_por": None,
        }
        resultado = await self.cuentas.insert_one(documento)
        documento["_id"] = resultado.inserted_id
        return self._limpiar(documento)

    async def actualizar_cuenta(
        self,
        empresa_id: str,
        codigo: str,
        cambios: Dict[str, Any],
        usuario: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not cambios:
            return await self.obtener_cuenta(empresa_id, codigo)

        doc = await self.cuentas.find_one_and_update(
            {"empresa_id": empresa_id, "codigo": codigo},
            {"$set": {**cambios, "modificado_en": datetime.utcnow(), "modificado_por": usuario}},
            return_document=True,
        )
        return self._limpiar(doc) if doc else None

    async def eliminar_cuenta(self, empresa_id: str, codigo: str) -> bool:
        resultado = await self.cuentas.delete_one({"empresa_id": empresa_id, "codigo": codigo})
        return resultado.deleted_count > 0

    async def tiene_movimientos(self, empresa_id: str, cuenta_id: str) -> bool:
        return (
            await self.movimientos.count_documents(
                {"empresa_id": empresa_id, "cuenta_caja_banco_id": cuenta_id}
            )
            > 0
        )

    async def calcular_saldo(
        self, empresa_id: str, cuenta_id: str, saldo_inicial: float
    ) -> float:
        pipeline = [
            {"$match": {"empresa_id": empresa_id, "cuenta_caja_banco_id": cuenta_id}},
            {"$group": {"_id": "$tipo", "total": {"$sum": "$monto"}}},
        ]
        resultados = await self.movimientos.aggregate(pipeline).to_list(length=None)
        ingresos = next((r["total"] for r in resultados if r["_id"] == "INGRESO"), 0.0)
        egresos = next((r["total"] for r in resultados if r["_id"] == "EGRESO"), 0.0)
        return round(saldo_inicial + ingresos - egresos, 2)

    # ------------------------------------------------------------------
    # Movimientos
    # ------------------------------------------------------------------

    async def listar_movimientos(
        self,
        empresa_id: str,
        cuenta_caja_banco_id: Optional[str] = None,
        contabilizado: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        filtro: Dict[str, Any] = {"empresa_id": empresa_id}
        if cuenta_caja_banco_id:
            filtro["cuenta_caja_banco_id"] = cuenta_caja_banco_id
        if contabilizado is not None:
            filtro["contabilizado"] = contabilizado
        cursor = self.movimientos.find(filtro).sort("fecha", 1)
        return [self._limpiar(d) async for d in cursor]

    async def obtener_movimiento_por_id(
        self, empresa_id: str, movimiento_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(movimiento_id)
        except InvalidId:
            return None
        doc = await self.movimientos.find_one({"empresa_id": empresa_id, "_id": oid})
        return self._limpiar(doc) if doc else None

    async def crear_movimiento(
        self, empresa_id: str, datos: Dict[str, Any], usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        documento = {
            **datos,
            "empresa_id": empresa_id,
            "contabilizado": False,
            "lote_contabilizacion": None,
            "numeroAsiento": None,
            "creado_en": datetime.utcnow(),
            "creado_por": usuario,
        }
        resultado = await self.movimientos.insert_one(documento)
        documento["_id"] = resultado.inserted_id
        return self._limpiar(documento)

    async def crear_aplicaciones(
        self,
        empresa_id: str,
        movimiento_caja_banco_id: str,
        documentos_aplicados: List[Dict[str, Any]],
    ) -> None:
        """
        Una fila por documento cancelado por este movimiento. El saldo
        pendiente de cada documento se deriva sumando estas filas (ver
        `pendientes.PendientesCajaBancoService`); nunca se escribe un campo
        "saldo" en `registro_compras`/`registro_ventas`.
        """
        if not documentos_aplicados:
            return
        ahora = datetime.utcnow()
        await self.aplicaciones.insert_many([
            {
                "empresa_id": empresa_id,
                "movimiento_caja_banco_id": movimiento_caja_banco_id,
                "documento_tipo": doc["documento_tipo"],
                "documento_id": doc["documento_id"],
                "monto_aplicado": doc["monto"],
                "fecha_aplicacion": ahora,
            }
            for doc in documentos_aplicados
        ])

    async def eliminar_movimiento(self, empresa_id: str, movimiento_id: str) -> bool:
        try:
            oid = ObjectId(movimiento_id)
        except InvalidId:
            return False
        resultado = await self.movimientos.delete_one(
            {"empresa_id": empresa_id, "_id": oid, "contabilizado": False}
        )
        return resultado.deleted_count > 0

    @staticmethod
    def _limpiar(doc: Dict[str, Any]) -> Dict[str, Any]:
        salida = dict(doc)
        _id = salida.pop("_id", None)
        salida["id"] = str(_id) if _id is not None else salida.get("codigo", "")
        return salida
