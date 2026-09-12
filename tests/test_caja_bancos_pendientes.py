"""
Tests de "documentos pendientes de pago/cobro" para Caja/Bancos:
- `PendientesCajaBancoService.listar_pendientes` deriva el saldo cruzando
  Registro de Compras/Ventas (por RUC del socio) con las aplicaciones de pago
  ya registradas, sin tocar esos módulos.
- `CajaBancoService.crear_movimiento` valida que no se sobre-aplique un pago.
- `CajaBancoService.contabilizar` fusiona en una sola línea los documentos
  aplicados que comparten la misma cuenta contable real.
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from bson import ObjectId

from app.modules.caja_bancos.pendientes import PendientesCajaBancoService
from app.modules.caja_bancos.schemas import (
    DocumentoAplicadoCreate,
    DocumentoTipo,
    MovimientoCajaBancoCreate,
)
from app.modules.caja_bancos.services import CajaBancoError, CajaBancoService


def _coincide(doc, filtro):
    for k, v in filtro.items():
        if isinstance(v, dict) and "$ne" in v:
            if doc.get(k) == v["$ne"]:
                return False
        elif isinstance(v, dict) and "$in" in v:
            if doc.get(k) not in v["$in"]:
                return False
        elif isinstance(v, dict) and "$gt" in v:
            if not (doc.get(k, 0) > v["$gt"]):
                return False
        elif isinstance(v, dict) and "$regex" in v:
            # Ningún test de este archivo depende del contenido exacto del
            # regex: el filtrado "solo numéricos" para el correlativo se
            # hace aparte, dentro de `aggregate`.
            continue
        else:
            if doc.get(k) != v:
                return False
    return True


class _Cursor:
    """Sustituto de un cursor de Motor: encadena `.sort()` e itera async,
    y también soporta `.to_list()` (los distintos servicios usan una u otra)."""

    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def to_list(self, length=None):
        async def _inner():
            return list(self._docs)
        return _inner()

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find(self, filtro=None):
        filtro = filtro or {}
        return _Cursor([d for d in self.docs if _coincide(d, filtro)])

    async def find_one(self, filtro=None, sort=None):
        filtro = filtro or {}
        for d in self.docs:
            if _coincide(d, filtro):
                return d
        return None

    async def insert_one(self, doc):
        doc = {**doc, "_id": doc.get("_id", ObjectId())}
        self.docs.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})

    async def insert_many(self, docs):
        for doc in docs:
            doc.setdefault("_id", ObjectId())
            self.docs.append(doc)
        return type("Result", (), {"inserted_ids": [d["_id"] for d in docs]})

    async def update_one(self, filtro, update):
        for d in self.docs:
            if _coincide(d, filtro):
                d.update(update.get("$set", {}))
                for campo in update.get("$unset", {}):
                    d.pop(campo, None)
                return type("Result", (), {"modified_count": 1})
        return type("Result", (), {"modified_count": 0})

    def aggregate(self, pipeline):
        match = pipeline[0].get("$match", {})
        filtrados = [d for d in self.docs if _coincide(d, match)]

        segunda_etapa = pipeline[1] if len(pipeline) > 1 else {}

        if "$addFields" in segunda_etapa and "_num" in segunda_etapa["$addFields"]:
            # Pipeline de `_siguiente_correlativo`: solo correlativos puramente
            # numéricos (el `$match` ya trae el `$regex`, que `_coincide`
            # ignora a propósito), el máximo como número.
            numericos = [
                d for d in filtrados
                if str(d.get("numeroCorrelativo", "")).isdigit()
            ]
            if not numericos:
                return _Cursor([])
            maximo = max(int(d["numeroCorrelativo"]) for d in numericos)
            return _Cursor([{"_num": maximo}])

        grupo = segunda_etapa.get("$group")
        if grupo and grupo["_id"] == "$documento_id":
            agregados: dict = {}
            for d in filtrados:
                agregados[d["documento_id"]] = agregados.get(d["documento_id"], 0.0) + d["monto_aplicado"]
            return _Cursor([{"_id": k, "total": v} for k, v in agregados.items()])
        # Pipeline de totales de libro: suma debe/haber de todo lo filtrado.
        debe = sum(d.get("debe", 0) for d in filtrados)
        haber = sum(d.get("haber", 0) for d in filtrados)
        return _Cursor([{"debe": debe, "haber": haber}])


class _FakeDB:
    """Cualquier nombre de colección (por atributo o por índice) resuelve a
    un `_FakeCollection` propio, creado la primera vez que se pide."""

    def __init__(self):
        object.__setattr__(self, "_colecciones", {})

    def _get(self, nombre):
        return self._colecciones.setdefault(nombre, _FakeCollection([]))

    def __getitem__(self, nombre):
        return self._get(nombre)

    def __getattr__(self, nombre):
        return self._get(nombre)


class _SinCargoAbono:
    """Plan de cuentas falso: ninguna cuenta tiene cargo/abono configurado."""

    async def list_cuentas(self, filtros=None, limit=None):
        return []


def _servicio(db: _FakeDB) -> CajaBancoService:
    service = CajaBancoService(db)
    service.plan_contable_repo = _SinCargoAbono()
    return service


# ---------------------------------------------------------------------------
# listar_pendientes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_listar_pendientes_descarta_lo_ya_pagado_y_calcula_saldo():
    socio_id = str(ObjectId())
    ruc = "20500000001"
    compra_pagada, compra_parcial, compra_sin_pagos = ObjectId(), ObjectId(), ObjectId()

    db = _FakeDB()
    db["socios_negocio"].docs.append({"_id": ObjectId(socio_id), "numero_documento": ruc})
    db.registro_compras.docs.extend([
        {
            "_id": compra_pagada, "empresa_id": "20123456789",
            "numero_documento_proveedor": ruc, "estado_operacion": "1",
            "importe_total": 100.0, "serie_comprobante": "F001", "numero_comprobante": "1",
            "fecha_comprobante": "2026-08-01", "fecha_vencimiento": "2026-08-31", "moneda": "PEN",
            "tipo_comprobante": "01",
        },
        {
            "_id": compra_parcial, "empresa_id": "20123456789",
            "numero_documento_proveedor": ruc, "estado_operacion": "1",
            "importe_total": 500.0, "serie_comprobante": "F001", "numero_comprobante": "2",
            "fecha_comprobante": "2026-08-05", "fecha_vencimiento": "2026-09-05", "moneda": "PEN",
            "tipo_comprobante": "01",
        },
        {
            "_id": compra_sin_pagos, "empresa_id": "20123456789",
            "numero_documento_proveedor": ruc, "estado_operacion": "1",
            "importe_total": 200.0, "serie_comprobante": "F001", "numero_comprobante": "3",
            "fecha_comprobante": "2026-08-10", "fecha_vencimiento": "2026-09-10", "moneda": "PEN",
            "tipo_comprobante": "01",
        },
    ])
    db["aplicaciones_pago_caja_bancos"].docs.extend([
        {"documento_tipo": "COMPRA", "documento_id": str(compra_pagada), "monto_aplicado": 100.0},
        {"documento_tipo": "COMPRA", "documento_id": str(compra_parcial), "monto_aplicado": 150.0},
    ])

    service = PendientesCajaBancoService(db)
    pendientes = await service.listar_pendientes("20123456789", DocumentoTipo.COMPRA, socio_id)

    assert len(pendientes) == 2
    por_id = {p.documento_id: p for p in pendientes}
    assert str(compra_pagada) not in por_id
    assert por_id[str(compra_parcial)].saldo_pendiente == 350.0
    assert por_id[str(compra_sin_pagos)].saldo_pendiente == 200.0


@pytest.mark.asyncio
async def test_listar_pendientes_sin_socio_devuelve_todos_con_contraparte():
    """Sin `socio_negocio_id`: todos los pendientes de la empresa, de
    cualquier proveedor, cada uno con el nombre de su contraparte -para
    poder pagar en bloque documentos de varios proveedores a la vez."""
    compra_a, compra_b = ObjectId(), ObjectId()
    db = _FakeDB()
    db.registro_compras.docs.extend([
        {
            "_id": compra_a, "empresa_id": "20123456789",
            "numero_documento_proveedor": "20500000001",
            "razon_social_proveedor": "PROVEEDOR A", "estado_operacion": "1",
            "importe_total": 100.0, "serie_comprobante": "F001", "numero_comprobante": "1",
            "fecha_comprobante": "2026-08-01", "moneda": "PEN", "tipo_comprobante": "01",
        },
        {
            "_id": compra_b, "empresa_id": "20123456789",
            "numero_documento_proveedor": "20500000099",
            "razon_social_proveedor": "PROVEEDOR B", "estado_operacion": "1",
            "importe_total": 200.0, "serie_comprobante": "F002", "numero_comprobante": "1",
            "fecha_comprobante": "2026-08-02", "moneda": "PEN", "tipo_comprobante": "01",
        },
    ])

    service = PendientesCajaBancoService(db)
    pendientes = await service.listar_pendientes("20123456789", DocumentoTipo.COMPRA)

    assert len(pendientes) == 2
    por_id = {p.documento_id: p for p in pendientes}
    assert por_id[str(compra_a)].contraparte_nombre == "PROVEEDOR A"
    assert por_id[str(compra_a)].contraparte_documento == "20500000001"
    assert por_id[str(compra_b)].contraparte_nombre == "PROVEEDOR B"


# ---------------------------------------------------------------------------
# crear_movimiento: no se puede sobre-aplicar un pago
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_movimiento_rechaza_sobre_aplicacion():
    compra_id = ObjectId()
    db = _FakeDB()
    db.registro_compras.docs.append({
        "_id": compra_id, "empresa_id": "20123456789",
        "numero_documento_proveedor": "20500000001", "estado_operacion": "1",
        "importe_total": 100.0, "serie_comprobante": "F001", "numero_comprobante": "1",
        "fecha_comprobante": "2026-08-01", "moneda": "PEN", "tipo_comprobante": "01",
    })
    db["cuentas_caja_banco"].docs.append({
        "_id": ObjectId(), "empresa_id": "20123456789", "codigo": "CAJA-01",
        "activa": True, "cuenta_contable": {"codigo": "101101", "denominacion": "Caja"},
    })
    cuenta_id = str(db["cuentas_caja_banco"].docs[0]["_id"])

    service = _servicio(db)

    datos = MovimientoCajaBancoCreate(
        cuenta_caja_banco_id=cuenta_id,
        fecha="2026-09-12",
        tipo="EGRESO",
        monto=150.0,
        glosa="Pago factura",
        tipo_documento="FT",
        medio_pago="009",
        flujo_efectivo="150",
        documentos_aplicados=[
            DocumentoAplicadoCreate(documento_tipo="COMPRA", documento_id=str(compra_id), monto=150.0)
        ],
    )

    with pytest.raises(CajaBancoError, match="saldo pendiente"):
        await service.crear_movimiento("20123456789", datos)


@pytest.mark.asyncio
async def test_crear_movimiento_exige_contra_cuenta_si_sobra_remanente():
    compra_id = ObjectId()
    db = _FakeDB()
    db.registro_compras.docs.append({
        "_id": compra_id, "empresa_id": "20123456789",
        "numero_documento_proveedor": "20500000001", "estado_operacion": "1",
        "importe_total": 100.0, "serie_comprobante": "F001", "numero_comprobante": "1",
        "fecha_comprobante": "2026-08-01", "moneda": "PEN", "tipo_comprobante": "01",
    })
    db["cuentas_caja_banco"].docs.append({
        "_id": ObjectId(), "empresa_id": "20123456789", "codigo": "CAJA-01",
        "activa": True, "cuenta_contable": {"codigo": "101101", "denominacion": "Caja"},
    })
    cuenta_id = str(db["cuentas_caja_banco"].docs[0]["_id"])
    service = _servicio(db)

    datos = MovimientoCajaBancoCreate(
        cuenta_caja_banco_id=cuenta_id,
        fecha="2026-09-12",
        tipo="EGRESO",
        monto=150.0,  # 100 se aplican a la factura, sobran 50 sin destino
        glosa="Pago factura + adelanto",
        tipo_documento="FT",
        medio_pago="009",
        flujo_efectivo="150",
        documentos_aplicados=[
            DocumentoAplicadoCreate(documento_tipo="COMPRA", documento_id=str(compra_id), monto=100.0)
        ],
    )

    with pytest.raises(CajaBancoError, match="contra-cuenta"):
        await service.crear_movimiento("20123456789", datos)


# ---------------------------------------------------------------------------
# contabilizar(): fusiona documentos que comparten la misma cuenta CxP real
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_contabilizar_fusiona_documentos_de_la_misma_cuenta():
    ruc_proveedor = "20500000001"
    compra_1, compra_2 = ObjectId(), ObjectId()

    db = _FakeDB()
    db.registro_compras.docs.extend([
        {
            "_id": compra_1, "empresa_id": "20123456789",
            "numero_documento_proveedor": ruc_proveedor, "estado_operacion": "1",
            "importe_total": 300.0, "serie_comprobante": "F001", "numero_comprobante": "1",
            "fecha_comprobante": "2026-08-01", "moneda": "PEN", "tipo_comprobante": "01",
        },
        {
            "_id": compra_2, "empresa_id": "20123456789",
            "numero_documento_proveedor": ruc_proveedor, "estado_operacion": "1",
            "importe_total": 200.0, "serie_comprobante": "F001", "numero_comprobante": "2",
            "fecha_comprobante": "2026-08-02", "moneda": "PEN", "tipo_comprobante": "01",
        },
    ])
    # Ambas compras se contabilizaron contra la misma cuenta 421101.
    db["asientos_contables"].docs.extend([
        {
            "empresaId": "20123456789", "numeroDocumento": "F001-1",
            "cuentaContable": {"codigo": "421101", "denominacion": "Facturas por pagar"},
            "debe": 0.0, "haber": 300.0,
        },
        {
            "empresaId": "20123456789", "numeroDocumento": "F001-2",
            "cuentaContable": {"codigo": "421101", "denominacion": "Facturas por pagar"},
            "debe": 0.0, "haber": 200.0,
        },
    ])
    db["cuentas_caja_banco"].docs.append({
        "_id": ObjectId(), "empresa_id": "20123456789", "codigo": "CAJA-01",
        "activa": True, "cuenta_contable": {"codigo": "101101", "denominacion": "Caja"},
    })
    cuenta_id = str(db["cuentas_caja_banco"].docs[0]["_id"])
    db.companies.docs.append({"ruc": "20123456789", "razon_social": "Test SAC"})

    service = _servicio(db)

    datos = MovimientoCajaBancoCreate(
        cuenta_caja_banco_id=cuenta_id,
        fecha="2026-09-12",
        tipo="EGRESO",
        monto=500.0,
        glosa="Pago de dos facturas del mismo proveedor",
        tipo_documento="FT",
        medio_pago="009",
        flujo_efectivo="150",
        documentos_aplicados=[
            DocumentoAplicadoCreate(documento_tipo="COMPRA", documento_id=str(compra_1), monto=300.0),
            DocumentoAplicadoCreate(documento_tipo="COMPRA", documento_id=str(compra_2), monto=200.0),
        ],
    )
    await service.crear_movimiento("20123456789", datos)

    resultado = await service.contabilizar("20123456789")

    # 1 linea de caja + 1 linea fusionada de la cuenta 421101 (no 3).
    assert resultado["lineas"] == 2

    generadas = [d for d in db["asientos_contables"].docs if d.get("origen") == "CAJA_BANCOS"]
    assert len(generadas) == 2
    linea_cxp = next(d for d in generadas if d["cuentaContable"]["codigo"] == "421101")
    assert linea_cxp["debe"] == 500.0
    linea_caja = next(d for d in generadas if d["cuentaContable"]["codigo"] == "101101")
    assert linea_caja["haber"] == 500.0


# ---------------------------------------------------------------------------
# Regresión: un movimiento sin documentos aplicados ni contra-cuenta se
# aparta en vez de tumbar la contabilización de todo el lote.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_contabilizar_aparta_movimiento_sin_documentos_ni_contracuenta_y_sigue_con_los_demas():
    """
    Reproduce el bug real: un movimiento quedó guardado con
    `documentos_aplicados: []` y `contra_cuenta: None` (dato incompleto, por
    ejemplo de antes de que el frontend exigiera la contra-cuenta). Antes esto
    tumbaba con un error sin controlar (`None["codigo"]`) TODA la
    contabilización, incluidos los demás movimientos que sí estaban bien.
    """
    db = _FakeDB()
    db["cuentas_caja_banco"].docs.append({
        "_id": ObjectId(), "empresa_id": "20123456789", "codigo": "CAJA-01",
        "activa": True, "cuenta_contable": {"codigo": "101101", "denominacion": "Caja"},
    })
    cuenta_id = str(db["cuentas_caja_banco"].docs[0]["_id"])
    db.companies.docs.append({"ruc": "20123456789", "razon_social": "Test SAC"})

    service = _servicio(db)

    # Movimiento roto: se inserta directo (bypass de crear_movimiento, que ya
    # no permite este estado) para simular el dato incompleto real.
    await db["movimientos_caja_banco"].insert_one({
        "empresa_id": "20123456789",
        "cuenta_caja_banco_id": cuenta_id,
        "fecha": "2026-09-12",
        "tipo": "INGRESO",
        "monto": 3600.0,
        "glosa": "dfsfsd",
        "documentos_aplicados": [],
        "contra_cuenta": None,
        "contabilizado": False,
    })

    # Movimiento bueno: sin documentos aplicados pero con su contra-cuenta.
    datos_bueno = MovimientoCajaBancoCreate(
        cuenta_caja_banco_id=cuenta_id,
        fecha="2026-09-12",
        tipo="INGRESO",
        monto=100.0,
        glosa="Cobro varios",
        tipo_documento="FT",
        medio_pago="009",
        flujo_efectivo="100",
        contra_cuenta={"codigo": "701101", "denominacion": "Ventas"},
    )
    await service.crear_movimiento("20123456789", datos_bueno)

    resultado = await service.contabilizar("20123456789")

    assert resultado["asientos"] == 1
    assert len(resultado["apartados"]) == 1
    assert "documentos aplicados" in resultado["apartados"][0]["motivo"]

    generadas = [d for d in db["asientos_contables"].docs if d.get("origen") == "CAJA_BANCOS"]
    assert len(generadas) == 2
    assert any(d["cuentaContable"]["codigo"] == "701101" for d in generadas)
