"""
Integración: `CajaBancoService.contabilizar()` también debe disparar las
cuentas autogeneradas (cargo/abono) del Plan de Cuentas cuando la cuenta de
caja/banco o la contra-cuenta del movimiento las tengan configuradas.
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from bson import ObjectId

from app.modules.caja_bancos.services import CajaBancoService


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def to_list(self, n=None):
        async def _inner():
            return self._docs[:n] if n else self._docs
        return _inner()


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.inserted = []

    async def find_one(self, filtro=None, sort=None):
        candidatos = self.docs + self.inserted
        return candidatos[-1] if candidatos else None

    async def insert_one(self, doc):
        doc = {**doc, "_id": ObjectId()}
        self.inserted.append(doc)
        return type("Result", (), {"inserted_id": doc["_id"]})

    async def insert_many(self, docs):
        self.inserted.extend(docs)
        return type("Result", (), {"inserted_ids": list(range(len(docs)))})

    async def update_one(self, filtro, update):
        return type("Result", (), {"modified_count": 1})

    def aggregate(self, pipeline):
        segunda_etapa = pipeline[1] if len(pipeline) > 1 else {}
        if "$addFields" in segunda_etapa and "_num" in segunda_etapa["$addFields"]:
            # Pipeline de `_siguiente_correlativo`: ninguno de estos tests
            # pre-siembra un numeroCorrelativo numerico, asi que siempre
            # arranca en 1 (resultado vacio).
            candidatos = self.docs + self.inserted
            numericos = [d for d in candidatos if str(d.get("numeroCorrelativo", "")).isdigit()]
            if not numericos:
                return _Cursor([])
            return _Cursor([{"_num": max(int(d["numeroCorrelativo"]) for d in numericos)}])

        debe = sum(d.get("debe", 0) for d in self.inserted)
        haber = sum(d.get("haber", 0) for d in self.inserted)
        return _Cursor([{"debe": debe, "haber": haber}])


class _FakeDB:
    def __init__(self):
        self.companies = _FakeCollection([{"ruc": "20123456789", "razon_social": "Test SAC"}])


class _RepoCajaBancoFalso:
    """Sustituto de `CajaBancoRepository`: solo lo que usa `contabilizar()`."""

    def __init__(self, cuentas, movimientos_pendientes):
        self._cuentas = {c["id"]: c for c in cuentas}
        self._pendientes = list(movimientos_pendientes)
        self.movimientos = _FakeCollection([])

    async def listar_movimientos(self, empresa_id, cuenta_caja_banco_id=None, contabilizado=None):
        if contabilizado is False:
            return self._pendientes
        return []

    async def obtener_cuenta_por_id(self, empresa_id, cuenta_id):
        return self._cuentas.get(cuenta_id)


class _PlanContableConDestinoEnLaContraCuenta:
    """La contra-cuenta 601101 (un gasto) tiene cargo=201111 / abono=611101."""

    async def list_cuentas(self, filtros=None, limit=None):
        filtros = filtros or {}
        if filtros.get("codigo") == "601101":
            return [{
                "codigo": "601101",
                "cuenta_cargo_destino": {"codigo": "201111", "denominacion": "Mercaderias-Costo"},
                "cuenta_abono_destino": {"codigo": "611101", "denominacion": "Mercaderias"},
            }]
        return []


def _servicio_con_fakes(cuentas, movimientos):
    service = CajaBancoService.__new__(CajaBancoService)
    service.db = _FakeDB()
    service.repo = _RepoCajaBancoFalso(cuentas, movimientos)
    service.plan_contable_repo = _PlanContableConDestinoEnLaContraCuenta()
    service.asientos = _FakeCollection([])
    service.libros = _FakeCollection([])
    return service


@pytest.mark.asyncio
async def test_contabilizar_caja_bancos_genera_lineas_automaticas_de_la_contracuenta():
    """
    Un pago en efectivo (egreso) contra un gasto (601101, que sí tiene
    destino configurado) debe generar, además de las 2 líneas normales
    (caja / gasto), las 2 líneas espejo del destino de la contra-cuenta.
    """
    cuenta_caja = {
        "id": "cuenta-caja-1",
        "codigo": "CAJA-01",
        "cuenta_contable": {"codigo": "101101", "denominacion": "Caja principal"},
    }
    movimiento = {
        "id": str(ObjectId()),
        "cuenta_caja_banco_id": "cuenta-caja-1",
        "fecha": "2026-09-12",
        "tipo": "EGRESO",
        "monto": 300.0,
        "glosa": "Pago de gasto en efectivo",
        "contra_cuenta": {"codigo": "601101", "denominacion": "Gastos varios"},
        "centro_costo": None,
    }

    service = _servicio_con_fakes([cuenta_caja], [movimiento])

    resultado = await service.contabilizar("20123456789")

    assert resultado["asientos"] == 1
    # 2 lineas del movimiento (caja/contra-cuenta) + 2 lineas espejo del destino.
    assert resultado["lineas"] == 4

    generadas = service.asientos.inserted
    codigos = sorted((d["cuentaContable"]["codigo"], d["debe"], d["haber"]) for d in generadas)
    assert codigos == sorted([
        ("101101", 0.0, 300.0),   # caja, egreso -> haber
        ("601101", 300.0, 0.0),   # contra-cuenta (gasto), egreso -> debe
        ("201111", 300.0, 0.0),   # auto cargo
        ("611101", 0.0, 300.0),   # auto abono
    ])

    numeros_asiento = {d["numeroAsiento"] for d in generadas}
    assert len(numeros_asiento) == 1
    correlativos = [d["numeroCorrelativo"] for d in generadas]
    assert len(correlativos) == len(set(correlativos))

    auto = [d for d in generadas if d["origen"] == "AUTO_DESTINO"]
    assert len(auto) == 2


@pytest.mark.asyncio
async def test_contabilizar_caja_bancos_sin_destino_no_genera_extra():
    """Ni la cuenta de caja ni la contra-cuenta tienen destino: solo 2 lineas."""
    cuenta_caja = {
        "id": "cuenta-caja-1",
        "codigo": "CAJA-01",
        "cuenta_contable": {"codigo": "101101", "denominacion": "Caja principal"},
    }
    movimiento = {
        "id": str(ObjectId()),
        "cuenta_caja_banco_id": "cuenta-caja-1",
        "fecha": "2026-09-12",
        "tipo": "INGRESO",
        "monto": 150.0,
        "glosa": "Cobro varios",
        "contra_cuenta": {"codigo": "701101", "denominacion": "Ventas"},
        "centro_costo": None,
    }

    service = _servicio_con_fakes([cuenta_caja], [movimiento])

    resultado = await service.contabilizar("20123456789")

    assert resultado["lineas"] == 2
    assert all(d["origen"] != "AUTO_DESTINO" for d in service.asientos.inserted)
