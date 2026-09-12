"""
Tests de Caja/Bancos: la cuenta contable enlazada debe existir y estar
marcada para el tipo correcto (es_cuenta_caja / es_cuenta_bancaria).
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from app.modules.caja_bancos.services import CajaBancoError, CajaBancoService
from app.modules.caja_bancos.schemas import TipoCuentaCajaBanco


class _RepoConPlanDeCuentas:
    def __init__(self, cuentas):
        self._cuentas = {c["codigo"]: c for c in cuentas}

    async def list_cuentas(self, filtros=None, limit=None):
        filtros = filtros or {}
        codigo = filtros.get("codigo")
        cuenta = self._cuentas.get(codigo)
        return [cuenta] if cuenta else []


def _servicio_con_plan(cuentas):
    """Construye el servicio sin tocar Mongo: solo se prueba la validacion."""
    service = CajaBancoService.__new__(CajaBancoService)
    service.plan_contable_repo = _RepoConPlanDeCuentas(cuentas)
    return service


@pytest.mark.asyncio
async def test_rechaza_cuenta_contable_inexistente():
    service = _servicio_con_plan([])
    with pytest.raises(CajaBancoError, match="no existe"):
        await service._validar_cuenta_contable(TipoCuentaCajaBanco.CAJA, "101101")


@pytest.mark.asyncio
async def test_rechaza_cuenta_no_marcada_como_caja():
    service = _servicio_con_plan([{"codigo": "101101", "es_cuenta_caja": False}])
    with pytest.raises(CajaBancoError, match="cuenta de caja"):
        await service._validar_cuenta_contable(TipoCuentaCajaBanco.CAJA, "101101")


@pytest.mark.asyncio
async def test_rechaza_cuenta_no_marcada_como_bancaria():
    service = _servicio_con_plan([{"codigo": "104101", "es_cuenta_bancaria": False}])
    with pytest.raises(CajaBancoError, match="cuenta bancaria"):
        await service._validar_cuenta_contable(TipoCuentaCajaBanco.BANCO, "104101")


@pytest.mark.asyncio
async def test_acepta_cuenta_marcada_correctamente():
    service = _servicio_con_plan([{"codigo": "101101", "es_cuenta_caja": True}])
    await service._validar_cuenta_contable(TipoCuentaCajaBanco.CAJA, "101101")
