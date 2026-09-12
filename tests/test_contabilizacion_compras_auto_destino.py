"""
Integración: la contabilización de compras (puente SIRE -> Libro Diario)
también debe disparar las cuentas autogeneradas (cargo/abono) del Plan de
Cuentas para las líneas que las tengan configuradas.

Usa fakes en memoria de las colecciones de Mongo que toca
`ContabilizacionComprasService.contabilizar()`, para probar el flujo
completo sin una base de datos real.
"""
import sys
import os
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from app.modules.accounting.services.contabilizacion_compras_service import (
    ContabilizacionComprasService,
)


class _Cursor:
    """Cursor falso: soporta `.sort(...)` encadenado e iteración async."""

    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _FakeCollection:
    """Sustituto mínimo de una colección de Motor, en memoria."""

    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.inserted = []
        self.updates = []

    def find(self, filtro=None):
        return _Cursor(self.docs)

    async def find_one(self, filtro=None, sort=None):
        candidatos = list(self.docs) + self.inserted
        return candidatos[-1] if candidatos else None

    async def insert_many(self, docs):
        self.inserted.extend(docs)
        return type("Result", (), {"inserted_ids": list(range(len(docs)))})

    async def insert_one(self, doc):
        doc = {**doc, "_id": "libro-nuevo"}
        self.inserted.append(doc)
        return type("Result", (), {"inserted_id": "libro-nuevo"})

    async def update_one(self, filtro, update):
        self.updates.append((filtro, update))
        return type("Result", (), {"modified_count": 1})

    def aggregate(self, pipeline):
        segunda_etapa = pipeline[1] if len(pipeline) > 1 else {}
        if "$addFields" in segunda_etapa and "_num" in segunda_etapa["$addFields"]:
            # Pipeline de `_siguiente_correlativo`: este test no pre-siembra
            # ningun numeroCorrelativo numerico, asi que siempre arranca en 1.
            candidatos = self.docs + self.inserted
            numericos = [d for d in candidatos if str(d.get("numeroCorrelativo", "")).isdigit()]
            if not numericos:
                return _Cursor([])
            return _Cursor([{"_num": max(int(d["numeroCorrelativo"]) for d in numericos)}])

        total_debe = sum(d.get("debe", 0) for d in self.inserted)
        total_haber = sum(d.get("haber", 0) for d in self.inserted)
        return _Cursor([{"debe": total_debe, "haber": total_haber}])


# `aggregate(...)` en el servicio real hace `.to_list(1)`; el cursor falso
# necesita ese método también.
def _to_list(self, n=None):
    async def _inner():
        return self._docs[: n] if n else self._docs
    return _inner()


_Cursor.to_list = _to_list


class _FakeDB:
    """Sustituto de `AsyncIOMotorDatabase`: solo lo que toca este servicio."""

    def __init__(self):
        self.companies = _FakeCollection([{"ruc": "20123456789", "razon_social": "Test SAC"}])
        self._colecciones = {"libros_diario": _FakeCollection([])}

    def __getitem__(self, nombre):
        return self._colecciones.setdefault(nombre, _FakeCollection([]))


class _SubdiarioFalso:
    """Un único subdiario de compras, listo para contabilizar, sin IGV."""

    SUBDIARIO = {
        "codigo": "11",
        "nombre": "REGISTRO COMPRAS LOCALES",
        "listo": True,
        "naturaleza_compra": "NO_GRAVADA",
        "cuentas": {"cuenta_gasto": "601101", "cuenta_pago": "421101"},
    }

    async def obtener(self, empresa_id, codigo):
        return self.SUBDIARIO

    async def subdiario_para_compra(self, empresa_id, importes):
        return self.SUBDIARIO


class _PlanContableConDestino:
    """601101 tiene cargo=201111 y abono=611101; 421101 no tiene nada."""

    async def list_cuentas(self, filtros=None, limit=None):
        filtros = filtros or {}
        if filtros.get("codigo") == "601101":
            return [{
                "codigo": "601101",
                "cuenta_cargo_destino": {"codigo": "201111", "denominacion": "Mercaderias-Costo"},
                "cuenta_abono_destino": {"codigo": "611101", "denominacion": "Mercaderias"},
            }]
        return []


def _servicio_con_fakes(compras_pendientes):
    service = ContabilizacionComprasService.__new__(ContabilizacionComprasService)
    service.db = _FakeDB()
    service.compras = _FakeCollection(compras_pendientes)
    service.asientos = _FakeCollection([])
    service.subdiarios = _SubdiarioFalso()
    service.plan_contable_repo = _PlanContableConDestino()
    return service


@pytest.mark.asyncio
async def test_contabilizar_compras_genera_lineas_automaticas():
    compra = {
        "_id": "compra-1",
        "empresa_id": "20123456789",
        "periodo": "202609",
        "subdiario": "11",
        "serie_comprobante": "F001",
        "numero_comprobante": "123",
        "razon_social_proveedor": "Proveedor SAC",
        "fecha_comprobante": datetime(2026, 9, 12),
        "importe_total": 1000.0,
        "igv": 0.0,
        "base_imponible_no_gravada": 1000.0,
        "estado_operacion": "1",
        "asiento_numero": None,
    }

    service = _servicio_con_fakes([compra])

    resultado = await service.contabilizar("20123456789", "202609")

    assert resultado["asientos"] == 1
    # 2 lineas del comprobante (gasto/pago) + 2 lineas espejo del destino.
    assert resultado["lineas"] == 4

    generadas = service.asientos.inserted
    codigos = sorted((d["cuentaContable"]["codigo"], d["debe"], d["haber"]) for d in generadas)
    assert codigos == sorted([
        ("601101", 1000.0, 0.0),
        ("421101", 0.0, 1000.0),
        ("201111", 1000.0, 0.0),
        ("611101", 0.0, 1000.0),
    ])

    # Las 4 lineas comparten numeroAsiento y no chocan en numeroCorrelativo.
    numeros_asiento = {d["numeroAsiento"] for d in generadas}
    assert len(numeros_asiento) == 1
    correlativos = [d["numeroCorrelativo"] for d in generadas]
    assert len(correlativos) == len(set(correlativos))

    auto = [d for d in generadas if d["origen"] == "AUTO_DESTINO"]
    assert len(auto) == 2
    assert all(d["cuentaContable"]["codigo"] in ("201111", "611101") for d in auto)


@pytest.mark.asyncio
async def test_contabilizar_compras_sin_destino_no_genera_extra():
    """Un comprobante cuya cuenta de gasto NO tiene destino configurado
    genera solo sus 2 lineas normales."""
    compra = {
        "_id": "compra-2",
        "empresa_id": "20123456789",
        "periodo": "202609",
        "subdiario": "11",
        "serie_comprobante": "F001",
        "numero_comprobante": "999",
        "razon_social_proveedor": "Otro Proveedor",
        "fecha_comprobante": datetime(2026, 9, 12),
        "importe_total": 500.0,
        "igv": 0.0,
        "base_imponible_no_gravada": 500.0,
        "estado_operacion": "1",
        "asiento_numero": None,
    }

    service = _servicio_con_fakes([compra])
    service.subdiarios.SUBDIARIO = {
        **_SubdiarioFalso.SUBDIARIO,
        "cuentas": {"cuenta_gasto": "639999", "cuenta_pago": "421101"},
    }

    resultado = await service.contabilizar("20123456789", "202609")

    assert resultado["lineas"] == 2
    assert all(d["origen"] != "AUTO_DESTINO" for d in service.asientos.inserted)
