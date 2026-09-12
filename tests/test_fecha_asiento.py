"""
La fecha del asiento contable.

Un bug de este tipo no rompe una fila: rompe **el libro entero**. El endpoint del
libro diario valida todos sus asientos de una vez, así que una sola línea con la
fecha mal tipada hacía que la pantalla devolviera 404 y no se viera ningún
asiento, ni siquiera los correctos.

Pasó de verdad: el registro de compras guarda las fechas como `datetime` para
poder filtrar por rango en Mongo, y la contabilización las copiaba tal cual al
asiento, donde el esquema las declara `str`.

Por eso se arregla en los dos lados: el escritor guarda texto, y el esquema
tolera `datetime` para que el peor caso vuelva a ser una fila rara y no un libro
inaccesible.

Ejecutar:  python -m pytest tests/test_fecha_asiento.py -v
"""

from datetime import date, datetime

import pytest

from app.modules.accounting.accounting_schemas import AsientoContableResponse
from app.modules.accounting.services.contabilizacion_compras_service import _fecha_iso


def asiento(fecha):
    return AsientoContableResponse(
        id="64f123456789012345678901",
        empresaId="20612969125",
        numeroCorrelativo="000001",
        fecha=fecha,
        glosa="REGISTRO COMPRAS F001-1",
        numeroDocumento="F001-1",
        cuentaContable={"codigo": "60111101", "denominacion": "Compras"},
        debe=100.0,
        haber=0.0,
    )


# ---------------------------------------------------------------------------
# 1. El esquema acepta las tres formas y devuelve siempre texto
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada", [
    datetime(2026, 6, 24),
    datetime(2026, 6, 24, 15, 30, 45),
    date(2026, 6, 24),
    "2026-06-24",
])
def test_la_fecha_siempre_sale_como_texto_iso(entrada):
    resultado = asiento(entrada).fecha
    assert resultado == "2026-06-24"
    assert isinstance(resultado, str)


def test_una_fecha_ilegible_sigue_siendo_un_error():
    """
    Normalizar no es tragarse cualquier cosa: un valor que no es una fecha tiene
    que fallar, o acabaria en el PLE que se declara a SUNAT.
    """
    with pytest.raises(Exception):
        asiento("24 de junio")


def test_un_datetime_con_hora_pierde_la_hora_no_el_dia():
    """El asiento es de un dia, no de un instante."""
    assert asiento(datetime(2026, 6, 24, 23, 59, 59)).fecha == "2026-06-24"


# ---------------------------------------------------------------------------
# 2. El escritor de compras normaliza antes de guardar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperada", [
    (datetime(2026, 6, 24), "2026-06-24"),
    (datetime(2026, 6, 24, 15, 30), "2026-06-24"),
    (date(2026, 6, 24), "2026-06-24"),
    ("2026-06-24", "2026-06-24"),
    ("2026-06-24T00:00:00", "2026-06-24"),
])
def test_la_contabilizacion_guarda_la_fecha_en_iso(entrada, esperada):
    assert _fecha_iso(entrada) == esperada


@pytest.mark.parametrize("entrada", [None, ""])
def test_sin_fecha_no_se_inventa_nada(entrada):
    assert _fecha_iso(entrada) == ""
