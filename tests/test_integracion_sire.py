"""
Tests de integración del módulo SIRE sobre la aplicación completa.

Estos tests no existían porque no podían existir: el cliente de Mongo se ataba
al primer bucle de eventos y la segunda petición de cada proceso moría con
`RuntimeError: Event loop is closed`. Arreglado eso, aquí se comprueba que la
app responde de verdad, no solo que las piezas encajan.

No tocan SUNAT: solo rutas que se resuelven contra el estado local. Sí tocan
MongoDB, así que necesitan la base configurada en el `.env`.

Ejecutar:  python -m pytest tests/test_integracion_sire.py -v
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

RUC = "20612969125"


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_varias_peticiones_en_el_mismo_proceso(cliente):
    """
    La regresión que hacía imposible todo lo demás.

    Con el cliente de Mongo cacheado a un único bucle, la segunda petición
    fallaba siempre. Tres seguidas son prueba suficiente.
    """
    for periodo in ("202607", "202608", "202606"):
        r = cliente.get(
            "/api/v1/sire/rce/ciclo/estado",
            params={"ruc": RUC, "periodo": periodo},
        )
        assert r.status_code == 200, f"{periodo} respondió {r.status_code}: {r.text[:200]}"
        assert r.json()["periodo"] == periodo


def test_estado_inicial_de_un_periodo_es_propuesta(cliente):
    """Un periodo del que no se sabe nada está, por definición, en propuesta."""
    r = cliente.get(
        "/api/v1/sire/rce/ciclo/estado",
        params={"ruc": RUC, "periodo": "209912"},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["estado"] == "PROPUESTA"
    assert cuerpo["operaciones_disponibles"] == ["aceptar la propuesta (5.2)"]


def test_periodo_mal_formado_da_400_y_no_500(cliente):
    """Un error del usuario no puede presentarse como un fallo del servidor."""
    r = cliente.get(
        "/api/v1/sire/rce/ciclo/estado",
        params={"ruc": RUC, "periodo": "2026-07"},
    )
    assert r.status_code == 400
    assert "yyyymm" in r.json()["detail"]


def test_registrar_preliminar_sin_haber_aceptado_da_409(cliente):
    """
    El conflicto de estado tiene que llegar como 409, con las operaciones que
    sí caben, y sin haber llamado a SUNAT.
    """
    r = cliente.post(
        "/api/v1/sire/rce/ciclo/registrar-preliminar",
        params={"ruc": RUC, "periodo": "209912"},
    )
    assert r.status_code == 409
    detalle = r.json()["detail"]
    assert detalle["estado_actual"] == "PROPUESTA"
    assert "aceptar la propuesta (5.2)" in detalle["operaciones_disponibles"]


def test_catalogo_de_cargas_disponibles(cliente):
    """El catálogo de cargas es estático: buena prueba de que el router responde."""
    r = cliente.get("/api/v1/sire/rce/cargas/operaciones")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 6
    servicios = {op["servicio"] for op in cuerpo["operaciones"]}
    assert servicios == {"5.3", "5.5", "5.6", "5.7", "5.8", "5.9"}


def test_carga_desconocida_da_400(cliente):
    r = cliente.post(
        "/api/v1/sire/rce/cargas/inventada",
        params={"ruc": RUC, "periodo": "202607"},
        files={"archivo": ("a.txt", b"contenido", "text/plain")},
    )
    assert r.status_code == 400
    assert "no es una carga conocida" in r.json()["detail"]


def test_los_dos_libros_exponen_el_mismo_contrato(cliente):
    """
    Compras y ventas devuelven la misma forma, que es lo que permite que la
    interfaz use un solo panel para los dos.
    """
    claves = None
    for libro in ("rce", "rvie"):
        r = cliente.get(
            f"/api/v1/sire/{libro}/ciclo/estado",
            params={"ruc": RUC, "periodo": "209912"},
        )
        assert r.status_code == 200, f"{libro}: {r.status_code}"
        if claves is None:
            claves = set(r.json())
        else:
            assert set(r.json()) == claves, "los dos libros deben responder igual"


def test_el_estado_de_compras_y_ventas_es_independiente(cliente):
    """
    Un mismo periodo puede estar en fases distintas en cada libro, así que cada
    uno guarda su estado en su propia colección.
    """
    from app.modules.sire.repositories.rce_periodo_repository import (
        RcePeriodoRepository,
        RviePeriodoRepository,
    )

    assert RcePeriodoRepository.COLECCION != RviePeriodoRepository.COLECCION
