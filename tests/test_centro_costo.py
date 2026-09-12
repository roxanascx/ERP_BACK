"""
Tests de Centro de Costos: validaciones del Plan de Cuentas y del asiento.
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from app.modules.accounting.plan_contable_services import (
    _calcular_nivel_y_clase,
    _validar_flags_cuenta,
)
from app.modules.accounting.accounting_schemas import AsientoContableCreate
from app.modules.accounting.libro_diario_service import LibroDiarioService


def test_calcular_nivel_y_clase_por_longitud_de_codigo():
    assert _calcular_nivel_y_clase("1") == (1, 1)
    assert _calcular_nivel_y_clase("10") == (2, 1)
    assert _calcular_nivel_y_clase("101") == (3, 1)
    assert _calcular_nivel_y_clase("1011") == (4, 1)
    assert _calcular_nivel_y_clase("70111101") == (8, 7)


def test_requiere_centro_costo_exige_acepta_movimiento():
    with pytest.raises(ValueError):
        _validar_flags_cuenta({
            "acepta_movimiento": False,
            "requiere_centro_costo": True,
            "clase_contable": 1,
        })


def test_es_cuenta_bancaria_exige_clase_1():
    with pytest.raises(ValueError):
        _validar_flags_cuenta({
            "acepta_movimiento": True,
            "es_cuenta_bancaria": True,
            "clase_contable": 6,
        })


def test_flags_validos_no_lanzan():
    _validar_flags_cuenta({
        "acepta_movimiento": True,
        "requiere_centro_costo": True,
        "es_cuenta_bancaria": True,
        "clase_contable": 1,
    })


class _RepoConCuentaQueExigeCentroCosto:
    """Mock minimo: una sola cuenta, marcada `requiere_centro_costo`."""

    async def list_cuentas(self, filtros=None, limit=None):
        filtros = filtros or {}
        if filtros.get("codigo") == "659999":
            return [{"codigo": "659999", "requiere_centro_costo": True}]
        return []


@pytest.mark.asyncio
async def test_validar_asiento_rechaza_sin_centro_costo():
    service = LibroDiarioService()
    service.plan_contable_repo = _RepoConCuentaQueExigeCentroCosto()

    asiento = AsientoContableCreate(
        numeroCorrelativo="0001-1",
        fecha="2026-09-01",
        glosa="Gasto sin centro de costo",
        numeroDocumento="F001-1",
        cuentaContable={"codigo": "659999", "denominacion": "Otros gastos"},
        debe=100.0,
        haber=0.0,
    )

    with pytest.raises(ValueError, match="exige centro de costo"):
        await service._validar_asiento(asiento)


@pytest.mark.asyncio
async def test_validar_asiento_acepta_con_centro_costo():
    service = LibroDiarioService()
    service.plan_contable_repo = _RepoConCuentaQueExigeCentroCosto()

    asiento = AsientoContableCreate(
        numeroCorrelativo="0001-1",
        fecha="2026-09-01",
        glosa="Gasto con centro de costo",
        numeroDocumento="F001-1",
        cuentaContable={"codigo": "659999", "denominacion": "Otros gastos"},
        debe=100.0,
        haber=0.0,
        centroCosto={"codigo": "200", "nombre": "ADMINISTRACION"},
    )

    await service._validar_asiento(asiento)


@pytest.mark.asyncio
async def test_validar_asiento_no_exige_centro_costo_si_cuenta_no_lo_marca():
    service = LibroDiarioService()
    service.plan_contable_repo = _RepoConCuentaQueExigeCentroCosto()

    asiento = AsientoContableCreate(
        numeroCorrelativo="0001-1",
        fecha="2026-09-01",
        glosa="Cuenta sin la marca",
        numeroDocumento="F001-1",
        cuentaContable={"codigo": "101101", "denominacion": "Caja principal"},
        debe=100.0,
        haber=0.0,
    )

    await service._validar_asiento(asiento)
