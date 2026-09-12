"""
El bloque «datos reales» del Libro Mayor.

Estos tests fijan dos defectos que no eran casos límite: hacían que la
funcionalidad **no pudiera funcionar nunca**, y aun así nadie lo notó porque los
tests que debían cubrirla miraban una base de datos vacía.

1. Cuatro métodos estaban escritos como síncronos contra Motor, que es un driver
   asíncrono. El síntoma visible era `list(cursor)` sobre un `AsyncIOMotorCursor`.

2. El filtro avanzado metía objetos `date` en la consulta a Mongo. Falla dos
   veces: el driver no sabe codificar `date` —solo `datetime`— y, aunque lo
   codificara, comparar un objeto contra un campo de texto no casaría nunca,
   porque los asientos guardan la fecha como ISO.

Ejecutar:  python -m pytest tests/test_mayor_datos_reales.py -v
"""

import inspect
from datetime import date, datetime

import pytest

from app.modules.accounting.services.filtrado_avanzado_service import (
    FiltroAvanzado,
    ServiceFiltradoAvanzadoMayor,
    _fecha_iso,
)
from app.modules.accounting.services.mayor_service import MayorService


class _ClienteFalso(dict):
    """
    Un cliente que solo sirve para construir el servicio.

    `__init__` resuelve `client[db_name]` nada mas nacer, y estos tests solo
    miran como arma la consulta: no hace falta una base de verdad.
    """

    def __getitem__(self, _):
        return self

    def __getattr__(self, _):
        return self


def solo_codigo(fuente: str) -> str:
    """
    El código de una función, sin comentarios ni docstring.

    Hace falta porque los comentarios de estos métodos nombran el defecto que
    arreglan: buscar el patrón en el texto crudo daría un falso positivo.
    """
    sin_comentarios = "\n".join(
        linea for linea in fuente.splitlines() if not linea.strip().startswith("#")
    )

    for marca in ('"""', "'''"):
        partes = sin_comentarios.split(marca)
        if len(partes) >= 3:
            sin_comentarios = partes[0] + "".join(partes[2:])

    return sin_comentarios


# ---------------------------------------------------------------------------
# 1. Los métodos que tocan la base son asíncronos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nombre", [
    "obtener_asientos_contables_reales",
    "convertir_asientos_a_libro_mayor_ple",
    "generar_archivo_ple_mayor_con_datos_reales",
    "validar_compatibilidad_datos_reales",
])
def test_los_metodos_de_datos_reales_son_asincronos(nombre):
    """
    Motor solo se puede usar desde código asíncrono. Declarados como `def`,
    estos cuatro métodos no devolvían nada nunca: reventaban al recorrer el
    cursor, y las rutas —que sí hacían `await`— propagaban el error como un 500.
    """
    metodo = getattr(MayorService, nombre)
    assert inspect.iscoroutinefunction(metodo), (
        f"{nombre} tiene que ser async: usa Motor por dentro"
    )


def test_la_lectura_de_asientos_no_recorre_el_cursor_a_mano():
    """
    `list(cursor)` sobre un cursor de Motor lanza
    "AsyncIOMotorCursor object is not iterable". Hay que usar `to_list`.
    """
    codigo = solo_codigo(
        inspect.getsource(MayorService.obtener_asientos_contables_reales)
    )

    assert "to_list" in codigo
    assert "list(cursor)" not in codigo


# ---------------------------------------------------------------------------
# 2. Las fechas del filtro avanzado
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperada", [
    (date(2026, 6, 1), "2026-06-01"),
    (datetime(2026, 6, 1), "2026-06-01"),
    (datetime(2026, 6, 1, 23, 59), "2026-06-01"),
    ("2026-06-01", "2026-06-01"),
    ("2026-06-01T00:00:00", "2026-06-01"),
])
def test_la_fecha_del_filtro_se_vuelve_texto_iso(entrada, esperada):
    """Es el formato en el que los asientos guardan `fecha`."""
    assert _fecha_iso(entrada) == esperada


def test_la_consulta_no_lleva_objetos_date():
    """
    Mongo no sabe codificar `date` y aborta la consulta entera con
    "cannot encode object: datetime.date". Antes iba tal cual.
    """
    servicio = ServiceFiltradoAvanzadoMayor(_ClienteFalso(), "cualquiera")
    filtro = FiltroAvanzado(
        empresa_id="20612969125",
        fecha_desde=date(2026, 6, 1),
        fecha_hasta=date(2026, 6, 30),
    )

    query = servicio._construir_query_mongodb(filtro)

    assert query["fecha"] == {"$gte": "2026-06-01", "$lte": "2026-06-30"}
    for limite in query["fecha"].values():
        assert isinstance(limite, str), "un date aqui rompe la consulta"


def test_sin_fechas_no_se_filtra_por_fecha():
    """Un filtro vacío no debe acotar nada de más."""
    servicio = ServiceFiltradoAvanzadoMayor(_ClienteFalso(), "cualquiera")
    query = servicio._construir_query_mongodb(FiltroAvanzado(empresa_id="20612969125"))

    assert "fecha" not in query
