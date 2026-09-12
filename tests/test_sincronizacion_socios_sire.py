"""
Tests de sincronización de Socios de Negocio desde comprobantes SIRE.

- Un documento válido sin socio existente se crea.
- Un tipo de documento SUNAT sin equivalente (pasaporte, sin identificar) se
  omite, no revienta.
- Un socio existente con razón social real nunca se pisa con un placeholder.
- Un socio existente con placeholder sí se actualiza si el SIRE trae un dato
  real.
- Un socio que aparece como proveedor y luego como cliente pasa a "ambos".
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from app.modules.socios_negocio.models import SocioNegocioModel
from app.modules.socios_negocio.sincronizacion_sire import (
    PLACEHOLDER_RAZON_SOCIAL,
    SincronizacionSociosSireService,
)


class _FakeSocioRepository:
    def __init__(self):
        self._socios: dict = {}  # numero_documento -> SocioNegocioModel
        self._siguiente_id = 1

    async def get_by_documento(self, empresa_id, numero_documento):
        return self._socios.get(numero_documento)

    async def create(self, socio: SocioNegocioModel) -> str:
        socio.id = str(self._siguiente_id)
        self._siguiente_id += 1
        self._socios[socio.numero_documento] = socio
        return socio.id

    async def update(self, socio_id: str, update_data: dict) -> bool:
        for socio in self._socios.values():
            if socio.id == socio_id:
                for k, v in update_data.items():
                    setattr(socio, k, v)
                return True
        return False


@pytest.fixture
def repo():
    return _FakeSocioRepository()


@pytest.fixture
def service(repo):
    return SincronizacionSociosSireService(repo)


@pytest.mark.asyncio
async def test_crea_socio_nuevo_a_partir_de_un_ruc_valido(service, repo):
    resultado = await service.sincronizar_uno(
        "20123456789", "6", "20600000005", "PROVEEDOR REAL SAC", "proveedor"
    )
    assert resultado == "creado"
    socio = await repo.get_by_documento("20123456789", "20600000005")
    assert socio.razon_social == "PROVEEDOR REAL SAC"
    assert socio.tipo_documento == "RUC"
    assert socio.tipo_socio == "proveedor"


@pytest.mark.asyncio
async def test_omite_tipo_documento_sin_equivalente(service):
    # "7" = pasaporte, sin equivalente en RUC/DNI/CE.
    resultado = await service.sincronizar_uno(
        "20123456789", "7", "AB123456", "CLIENTE EXTRANJERO", "cliente"
    )
    assert resultado == "omitido"


@pytest.mark.asyncio
async def test_omite_documento_sin_identificar():
    servicio = SincronizacionSociosSireService(_FakeSocioRepository())
    resultado = await servicio.sincronizar_uno("20123456789", "0", "-", "SIN IDENTIFICAR", "cliente")
    assert resultado == "omitido"


@pytest.mark.asyncio
async def test_nunca_pisa_una_razon_social_real_con_el_placeholder(service, repo):
    await service.sincronizar_uno("20123456789", "6", "20600000013", "MI PROVEEDOR DE SIEMPRE", "proveedor")

    # El mismo RUC vuelve a aparecer, esta vez sin razón social identificada.
    resultado = await service.sincronizar_uno(
        "20123456789", "6", "20600000013", PLACEHOLDER_RAZON_SOCIAL, "proveedor"
    )

    assert resultado == "omitido"
    socio = await repo.get_by_documento("20123456789", "20600000013")
    assert socio.razon_social == "MI PROVEEDOR DE SIEMPRE"


@pytest.mark.asyncio
async def test_actualiza_razon_social_placeholder_cuando_llega_una_real(service, repo):
    await service.sincronizar_uno("20123456789", "6", "20600000021", PLACEHOLDER_RAZON_SOCIAL, "cliente")

    resultado = await service.sincronizar_uno(
        "20123456789", "6", "20600000021", "AHORA SI IDENTIFICADO SAC", "cliente"
    )

    assert resultado == "actualizado"
    socio = await repo.get_by_documento("20123456789", "20600000021")
    assert socio.razon_social == "AHORA SI IDENTIFICADO SAC"


@pytest.mark.asyncio
async def test_socio_que_aparece_como_proveedor_y_cliente_pasa_a_ambos(service, repo):
    await service.sincronizar_uno("20123456789", "6", "20600000031", "EMPRESA MIXTA SAC", "proveedor")
    resultado = await service.sincronizar_uno(
        "20123456789", "6", "20600000031", "EMPRESA MIXTA SAC", "cliente"
    )

    assert resultado == "actualizado"
    socio = await repo.get_by_documento("20123456789", "20600000031")
    assert socio.tipo_socio == "ambos"


# ---------------------------------------------------------------------------
# Backfill: recorre compras y ventas, sin duplicar por RUC repetido
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class _FakeColeccion:
    def __init__(self, docs):
        self.docs = docs

    def find(self, filtro=None, projection=None):
        return _FakeCursor(self.docs)


class _FakeDB:
    def __init__(self, compras, ventas):
        self.registro_compras = _FakeColeccion(compras)
        self.registro_ventas = _FakeColeccion(ventas)


@pytest.mark.asyncio
async def test_backfill_no_duplica_por_ruc_repetido_en_varias_compras(service):
    compras = [
        {"tipo_documento_proveedor": "6", "numero_documento_proveedor": "20600000005",
         "razon_social_proveedor": "PROVEEDOR X"},
        {"tipo_documento_proveedor": "6", "numero_documento_proveedor": "20600000005",
         "razon_social_proveedor": "PROVEEDOR X"},
    ]
    db = _FakeDB(compras, [])

    resultado = await service.sincronizar_backfill("20123456789", db)

    # El mismo (tipo, numero) se deduplica antes de llamar a sincronizar_uno:
    # la segunda compra ni siquiera se procesa.
    assert resultado["creados"] == 1
    assert resultado["actualizados"] == 0
    assert resultado["omitidos"] == 0


@pytest.mark.asyncio
async def test_backfill_cruza_compras_y_ventas_del_mismo_ruc(service, repo):
    compras = [{"tipo_documento_proveedor": "6", "numero_documento_proveedor": "20600000056",
                "razon_social_proveedor": "EMPRESA CRUZADA SAC"}]
    ventas = [{"tipo_documento_cliente": "6", "numero_documento_cliente": "20600000056",
               "razon_social_cliente": "EMPRESA CRUZADA SAC"}]
    db = _FakeDB(compras, ventas)

    resultado = await service.sincronizar_backfill("20123456789", db)

    assert resultado["creados"] == 1
    assert resultado["actualizados"] == 1
    socio = await repo.get_by_documento("20123456789", "20600000056")
    assert socio.tipo_socio == "ambos"
