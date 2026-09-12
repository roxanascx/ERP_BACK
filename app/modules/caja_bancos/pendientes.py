"""
Documentos pendientes de pago/cobro para Caja/Bancos.

Cruza Registro de Compras/Ventas con Socios de Negocio —por RUC, ya que hoy no
existe ningún vínculo directo entre esos módulos— y con las aplicaciones de
pago ya registradas, para derivar el saldo pendiente de cada documento sin
tocar `registro_compras`/`registro_ventas` (son módulos PLE/SUNAT ajenos a
este; no se les agrega ningún campo de "saldo").
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from .schemas import DocumentoPendiente, DocumentoTipo

#: Estado SUNAT de un comprobante anulado (ver `EstadoOperacion`/
#: `EstadoOperacionVenta` en los schemas de compras/ventas): no tiene sentido
#: cobrarlo o pagarlo.
ESTADO_ANULADO = "2"


def _fecha_str(valor: Any) -> Optional[str]:
    if valor is None or valor == "":
        return None
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()[:10]
    return str(valor)[:10]


def _dias_vencido(fecha_vencimiento: Optional[str]) -> Optional[int]:
    if not fecha_vencimiento:
        return None
    try:
        venc = datetime.strptime(fecha_vencimiento[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (date.today() - venc).days


class PendientesCajaBancoService:
    """Documentos de Compras/Ventas pendientes de pago/cobro, por socio."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.socios = database["socios_negocio"]
        self.compras = database.registro_compras
        self.ventas = database.registro_ventas
        self.aplicaciones = database["aplicaciones_pago_caja_bancos"]

    def _coleccion(self, tipo: DocumentoTipo):
        return self.compras if tipo == DocumentoTipo.COMPRA else self.ventas

    async def _ruc_del_socio(self, socio_negocio_id: str) -> Optional[str]:
        try:
            oid = ObjectId(socio_negocio_id)
        except InvalidId:
            return None
        socio = await self.socios.find_one({"_id": oid})
        return socio.get("numero_documento") if socio else None

    async def montos_pagados(self, documento_tipo: DocumentoTipo, documento_ids: List[str]) -> Dict[str, float]:
        """`{documento_id: monto_pagado}` para los ids dados."""
        if not documento_ids:
            return {}
        pipeline = [
            {"$match": {"documento_tipo": documento_tipo.value, "documento_id": {"$in": documento_ids}}},
            {"$group": {"_id": "$documento_id", "total": {"$sum": "$monto_aplicado"}}},
        ]
        resultados = await self.aplicaciones.aggregate(pipeline).to_list(length=None)
        return {r["_id"]: r["total"] for r in resultados}

    async def saldo_pendiente(self, documento_tipo: DocumentoTipo, documento_id: str) -> Optional[float]:
        """
        El saldo pendiente de UN documento puntual, o `None` si no existe.

        Se usa para validar una aplicación de pago al vuelo, sin tener que
        recorrer todos los pendientes del socio.
        """
        try:
            oid = ObjectId(documento_id)
        except InvalidId:
            return None
        doc = await self._coleccion(documento_tipo).find_one({"_id": oid})
        if not doc:
            return None
        pagados = await self.montos_pagados(documento_tipo, [documento_id])
        importe_total = float(doc.get("importe_total") or 0)
        return round(importe_total - pagados.get(documento_id, 0.0), 2)

    async def listar_pendientes(
        self,
        empresa_id: str,
        tipo: DocumentoTipo,
        socio_negocio_id: Optional[str] = None,
        incluir_pagados: bool = False,
    ) -> List[DocumentoPendiente]:
        """
        Documentos pendientes de un tipo (COMPRA o VENTA).

        Con `socio_negocio_id`, solo los de ese proveedor/cliente (se cruza
        por RUC). Sin él, **todos** los pendientes de la empresa —para poder
        pagar/cobrar en bloque documentos de varios proveedores o clientes a
        la vez, como en la pantalla de referencia (frmCONDOC01)—, cada uno
        con el nombre de su contraparte para poder identificarlo en la lista.
        """
        campo_documento = "numero_documento_proveedor" if tipo == DocumentoTipo.COMPRA else "numero_documento_cliente"
        campo_razon = "razon_social_proveedor" if tipo == DocumentoTipo.COMPRA else "razon_social_cliente"

        filtro: Dict[str, Any] = {
            "empresa_id": empresa_id,
            "estado_operacion": {"$ne": ESTADO_ANULADO},
        }

        if socio_negocio_id:
            ruc = await self._ruc_del_socio(socio_negocio_id)
            if not ruc:
                return []
            filtro[campo_documento] = ruc

        documentos = await self._coleccion(tipo).find(filtro).to_list(length=None)
        ids = [str(d["_id"]) for d in documentos]
        pagados = await self.montos_pagados(tipo, ids)

        pendientes: List[DocumentoPendiente] = []
        for doc in documentos:
            doc_id = str(doc["_id"])
            importe_total = float(doc.get("importe_total") or 0)
            monto_pagado = float(pagados.get(doc_id, 0.0))
            saldo = round(importe_total - monto_pagado, 2)
            if saldo <= 0.01 and not incluir_pagados:
                continue

            if tipo == DocumentoTipo.COMPRA:
                fecha_doc = _fecha_str(doc.get("fecha_comprobante"))
                moneda = doc.get("moneda")
            else:
                fecha_doc = _fecha_str(doc.get("fecha_emision"))
                moneda = doc.get("codigo_moneda")

            fecha_venc = _fecha_str(doc.get("fecha_vencimiento"))

            pendientes.append(DocumentoPendiente(
                documento_id=doc_id,
                documento_tipo=tipo,
                tipo_comprobante=doc.get("tipo_comprobante"),
                serie=doc.get("serie_comprobante"),
                numero=doc.get("numero_comprobante"),
                fecha_comprobante=fecha_doc,
                fecha_vencimiento=fecha_venc,
                moneda=moneda,
                importe_total=importe_total,
                monto_pagado=monto_pagado,
                saldo_pendiente=saldo,
                dias_vencido=_dias_vencido(fecha_venc),
                contraparte_nombre=doc.get(campo_razon),
                contraparte_documento=doc.get(campo_documento),
            ))

        pendientes.sort(key=lambda p: p.fecha_comprobante or "")
        return pendientes
