"""
Tests del motor de cuentas autogeneradas (cargo/abono).

Cuando se postea un asiento contra una cuenta con `cuenta_cargo_destino` /
`cuenta_abono_destino` configurados en el Plan de Cuentas, deben generarse
además las líneas espejo por el mismo importe, bajo el mismo `numeroAsiento`.
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from app.modules.accounting.accounting_schemas import AsientoContableCreate
from app.modules.accounting.libro_diario_service import LibroDiarioService
from app.modules.accounting.services.asientos_automaticos import (
    lineas_automaticas_por_destino,
)


class _PlanContableConDestino:
    """601 tiene cargo=201 y abono=611; el resto de cuentas no tiene nada."""

    def __init__(self, cuentas=None):
        self._cuentas = cuentas or {
            "601101": {
                "codigo": "601101",
                "cuenta_cargo_destino": {"codigo": "201111", "denominacion": "Mercaderias-Costo"},
                "cuenta_abono_destino": {"codigo": "611101", "denominacion": "Mercaderias"},
            },
            "101101": {"codigo": "101101"},
        }

    async def list_cuentas(self, filtros=None, limit=None):
        filtros = filtros or {}
        cuenta = self._cuentas.get(filtros.get("codigo"))
        return [cuenta] if cuenta else []


class _RepoQueRegistraInserts:
    """Repositorio falso de Libro Diario: guarda cada documento insertado."""

    def __init__(self):
        self.insertados = []
        self._correlativo = 0

    async def agregar_asiento(self, libro_id, asiento_data):
        documento = {**asiento_data, "id": f"id-{len(self.insertados) + 1}", "libroId": libro_id}
        self.insertados.append(documento)
        return documento

    async def obtener_siguiente_correlativo(self, empresa_id, periodo):
        self._correlativo += 1
        return str(self._correlativo).zfill(6)


# ---------------------------------------------------------------------------
# Función pura: qué líneas corresponde generar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lineas_automaticas_cuenta_con_cargo_y_abono():
    repo = _PlanContableConDestino()
    lineas = await lineas_automaticas_por_destino(repo, "601101", 1000.0)

    assert len(lineas) == 2
    assert lineas[0] == {"cuentaContable": {"codigo": "201111", "denominacion": "Mercaderias-Costo"}, "debe": 1000.0, "haber": 0.0}
    assert lineas[1] == {"cuentaContable": {"codigo": "611101", "denominacion": "Mercaderias"}, "debe": 0.0, "haber": 1000.0}


@pytest.mark.asyncio
async def test_lineas_automaticas_cuenta_sin_destino():
    repo = _PlanContableConDestino()
    assert await lineas_automaticas_por_destino(repo, "101101", 500.0) == []


@pytest.mark.asyncio
async def test_lineas_automaticas_monto_cero_no_genera_nada():
    repo = _PlanContableConDestino()
    assert await lineas_automaticas_por_destino(repo, "601101", 0.0) == []


# ---------------------------------------------------------------------------
# Integración con LibroDiarioService.agregar_asiento
# ---------------------------------------------------------------------------

def _servicio_con_fakes():
    service = LibroDiarioService.__new__(LibroDiarioService)
    service.repository = _RepoQueRegistraInserts()
    service.plan_contable_repo = _PlanContableConDestino()
    return service


@pytest.mark.asyncio
async def test_agregar_asiento_genera_lineas_espejo():
    service = _servicio_con_fakes()

    asiento_creado = {
        "id": "id-original",
        "empresaId": "20123456789",
        "numeroCorrelativo": "000001",
        "numeroAsiento": "0001",
        "fecha": "2026-09-12",
        "glosa": "Compra de mercaderias",
        "codigoLibro": "5.1",
        "numeroDocumento": "F001-1",
        "cuentaContable": {"codigo": "601101", "denominacion": "Mercaderias"},
        "debe": 1000.0,
        "haber": 0.0,
    }

    await service._generar_lineas_automaticas("libro-1", asiento_creado, usuario_id="tester")

    generadas = service.repository.insertados
    assert len(generadas) == 2

    cargo = next(l for l in generadas if l["cuentaContable"]["codigo"] == "201111")
    abono = next(l for l in generadas if l["cuentaContable"]["codigo"] == "611101")

    assert cargo["debe"] == 1000.0 and cargo["haber"] == 0.0
    assert abono["debe"] == 0.0 and abono["haber"] == 1000.0

    # Ambas comparten el numeroAsiento del original, para quedar agrupadas.
    assert cargo["numeroAsiento"] == "0001"
    assert abono["numeroAsiento"] == "0001"

    # Correlativos distintos entre sí (índice único empresa+correlativo).
    assert cargo["numeroCorrelativo"] != abono["numeroCorrelativo"]

    assert cargo["origen"] == "AUTO_DESTINO"
    assert "destino de 601101" in cargo["glosa"]


@pytest.mark.asyncio
async def test_agregar_asiento_sin_destino_no_genera_nada():
    service = _servicio_con_fakes()

    asiento_creado = {
        "empresaId": "20123456789",
        "fecha": "2026-09-12",
        "cuentaContable": {"codigo": "101101", "denominacion": "Caja"},
        "debe": 500.0,
        "haber": 0.0,
    }

    await service._generar_lineas_automaticas("libro-1", asiento_creado)

    assert service.repository.insertados == []


@pytest.mark.asyncio
async def test_correlativo_se_deriva_del_original_no_del_contador_compartido():
    """
    Regresión: el frontend manda numeroCorrelativo con formato "0001-1", no
    numérico puro. `obtener_siguiente_correlativo` no sabe interpretarlo y
    siempre caía a "000001", chocando con el índice único en la segunda
    línea. El correlativo de las líneas espejo ahora se deriva del original.
    """
    service = _servicio_con_fakes()

    asiento_creado = {
        "id": "id-original",
        "empresaId": "20123456789",
        "numeroCorrelativo": "0001-1",
        "numeroAsiento": "0001",
        "fecha": "2026-09-12",
        "glosa": "Compra de mercaderias",
        "cuentaContable": {"codigo": "601101", "denominacion": "Mercaderias"},
        "debe": 1000.0,
        "haber": 0.0,
    }

    await service._generar_lineas_automaticas("libro-1", asiento_creado)

    correlativos = {l["numeroCorrelativo"] for l in service.repository.insertados}
    assert correlativos == {"0001-1-auto1", "0001-1-auto2"}


class _RepoQueFallaEnLaSegundaLinea(_RepoQueRegistraInserts):
    """
    Simula el índice único de Mongo chocando en la segunda línea espejo
    (abono): la original y la de cargo (índices 0 y 1) se insertan bien.
    """

    async def agregar_asiento(self, libro_id, asiento_data):
        if len(self.insertados) == 2:
            raise Exception("El número correlativo ya existe para esta empresa")
        return await super().agregar_asiento(libro_id, asiento_data)


@pytest.mark.asyncio
async def test_agregar_asiento_no_falla_si_las_lineas_automaticas_fallan():
    """
    El asiento que pidió el usuario ya quedó guardado cuando se generan las
    líneas automáticas: si esa parte falla, no debe tumbar la respuesta ni
    hacer creer que el asiento original no se creó.
    """
    service = LibroDiarioService.__new__(LibroDiarioService)
    service.repository = _RepoQueFallaEnLaSegundaLinea()
    service.plan_contable_repo = _PlanContableConDestino()

    asiento_data = AsientoContableCreate(
        numeroCorrelativo="0001-1",
        numeroAsiento="0001",
        fecha="2026-09-12",
        glosa="Compra de mercaderias",
        numeroDocumento="F001-1",
        cuentaContable={"codigo": "601101", "denominacion": "Mercaderias"},
        debe=1000.0,
        haber=0.0,
        empresaId="20123456789",
    )

    respuesta = await service.agregar_asiento("libro-1", asiento_data, usuario_id="tester")

    assert respuesta.cuentaContable["codigo"] == "601101"
    # La primera línea espejo (cargo) sí se alcanzó a insertar antes del fallo.
    assert len(service.repository.insertados) == 2
