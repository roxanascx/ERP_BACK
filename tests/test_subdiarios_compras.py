"""
El lado de compras de los subdiarios.

El asiento de compra es el espejo del de venta, pero tiene dos casos que no
existen en ventas y que son los que pueden imputar mal el crédito fiscal:

- **Sin derecho a crédito** (subdiario 14): el IGV existe pero no va a la cuenta
  40, se suma al gasto.
- **Destino mixto** (subdiario 13): la compra se aplicó a ventas gravadas y no
  gravadas a la vez. Es una decisión del usuario, no se lee en el comprobante.

Ninguno de los dos se puede deducir de los importes, así que estos tests fijan
sobre todo que la deducción automática **no los invente**.

Ejecutar:  python -m pytest tests/test_subdiarios_compras.py -v
"""

import pytest

from app.modules.accounting.schemas.schemas_subdiario import (
    NaturalezaCompra,
    SubdiarioBase,
)
from app.modules.accounting.services.catalogo_subdiarios import CATALOGO_ESTANDAR
from app.modules.accounting.services.subdiario_service import SubdiarioService

deducir = SubdiarioService.deducir_naturaleza_compra


def subdiario(codigo="11", naturaleza=NaturalezaCompra.GRAVADA,
              gasto="60111101", igv="40111101", pago="42121101"):
    return SubdiarioBase(
        codigo=codigo,
        nombre="REGISTRO COMPRAS",
        asiento_compras=True,
        naturaleza_compra=naturaleza,
        cuentas={"cuenta_gasto": gasto, "cuenta_igv": igv, "cuenta_pago": pago},
    )


# ---------------------------------------------------------------------------
# 1. Deducir la naturaleza de los importes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("importes,esperada", [
    ({"base_gravada": 1000, "no_gravada": 0}, NaturalezaCompra.GRAVADA),
    ({"base_gravada": 0, "no_gravada": 500}, NaturalezaCompra.NO_GRAVADA),
    ({"base_gravada": 1000, "no_gravada": 500}, NaturalezaCompra.MIXTA),
])
def test_la_naturaleza_sale_de_los_importes(importes, esperada):
    assert deducir(importes) == esperada


def test_un_comprobante_en_cero_se_trata_como_gravado():
    """Deja el asiento en cero, que se ve y se corrige. Igual que en ventas."""
    assert deducir({"base_gravada": 0, "no_gravada": 0}) == NaturalezaCompra.GRAVADA


def test_los_campos_ausentes_no_rompen_la_deduccion():
    assert deducir({}) == NaturalezaCompra.GRAVADA


def test_los_importes_en_texto_tambien_valen():
    """SUNAT manda los importes como texto en el TXT de la propuesta."""
    assert deducir({"base_gravada": "0", "no_gravada": "500.00"}) == NaturalezaCompra.NO_GRAVADA


# ---------------------------------------------------------------------------
# 2. Lo que la deducción NO debe inventar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("importes", [
    {"base_gravada": 1000, "no_gravada": 0},
    {"base_gravada": 0, "no_gravada": 500},
    {"base_gravada": 1000, "no_gravada": 500},
    {},
])
def test_nunca_deduce_las_naturalezas_que_decide_el_usuario(importes):
    """
    Importación, destino mixto y sin-derecho-a-crédito dependen de algo que el
    comprobante no dice. Deducirlas imputaría mal el crédito fiscal.
    """
    assert deducir(importes) not in (
        NaturalezaCompra.IMPORTACION,
        NaturalezaCompra.GRAVADA_Y_NO_GRAVADA,
        NaturalezaCompra.SIN_DERECHO_CREDITO,
    )


# ---------------------------------------------------------------------------
# 3. Cuándo un subdiario de compra está listo
# ---------------------------------------------------------------------------

def test_con_las_tres_cuentas_esta_listo():
    assert subdiario().listo_para_contabilizar_compras()


def test_sin_cuenta_de_gasto_no_esta_listo():
    """Es la que el usuario tiene que poner: el catálogo la deja vacía."""
    assert not subdiario(gasto="").listo_para_contabilizar_compras()


def test_sin_cuenta_por_pagar_no_esta_listo():
    assert not subdiario(pago="").listo_para_contabilizar_compras()


def test_una_gravada_sin_cuenta_de_igv_no_esta_lista():
    assert not subdiario(igv="").listo_para_contabilizar_compras()


def test_sin_derecho_a_credito_no_necesita_cuenta_de_igv():
    """
    El IGV se suma al gasto, así que exigir la cuenta 40 sería pedir una cuenta
    que el asiento nunca va a usar.
    """
    sub = subdiario(codigo="14", naturaleza=NaturalezaCompra.SIN_DERECHO_CREDITO, igv="")
    assert sub.listo_para_contabilizar_compras()


def test_una_compra_no_gravada_tampoco_necesita_la_cuenta_de_igv():
    sub = subdiario(codigo="16", naturaleza=NaturalezaCompra.NO_GRAVADA, igv="")
    assert sub.listo_para_contabilizar_compras()


def test_un_subdiario_de_venta_no_pasa_por_la_puerta_de_compras():
    """Las marcas son independientes: no se puede contabilizar lo que no es."""
    venta = SubdiarioBase(
        codigo="05",
        nombre="REGISTRO VENTAS",
        asiento_ventas=True,
        cuentas={"cuenta_cobro": "121101", "cuenta_ingreso": "701101"},
    )
    assert not venta.listo_para_contabilizar_compras()


# ---------------------------------------------------------------------------
# 4. El catálogo sembrado
# ---------------------------------------------------------------------------

def test_cada_naturaleza_de_compra_apunta_a_un_solo_subdiario():
    """
    Si dos subdiarios comparten naturaleza, la búsqueda devuelve el primero por
    código y los comprobantes caen en el equivocado. Pasó con el 13 y el 17.
    """
    por_naturaleza = {}
    for d in CATALOGO_ESTANDAR:
        if d.get("asiento_compras"):
            por_naturaleza.setdefault(d["naturaleza_compra"], []).append(d["codigo"])

    repetidas = {k: v for k, v in por_naturaleza.items() if len(v) > 1}
    assert not repetidas, f"naturalezas con más de un subdiario: {repetidas}"


def test_el_catalogo_no_adivina_la_cuenta_de_gasto():
    """
    Depende de qué se compró (60 mercaderías, 63 servicios...). Rellenarla
    produciría asientos mal imputados sin que nadie lo note.
    """
    for d in CATALOGO_ESTANDAR:
        if d.get("asiento_compras"):
            assert not d["cuentas"]["cuenta_gasto"], f"el subdiario {d['codigo']} la trae puesta"


def test_el_14_y_el_16_se_siembran_sin_cuenta_de_igv():
    for d in CATALOGO_ESTANDAR:
        if d["codigo"] in ("14", "16"):
            assert not d["cuentas"]["cuenta_igv"], f"el subdiario {d['codigo']} no lleva IGV"
