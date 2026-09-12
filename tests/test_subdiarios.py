"""
Tests del catálogo de subdiarios.

Lo que más importa aquí es la **clasificación automática**: es la regla que
decide, a partir de los importes de un comprobante de SIRE, en qué subdiario
cae y por tanto qué asiento se va a generar. Si se equivoca, el error llega al
libro diario.

Ejecutar:  python -m pytest tests/test_subdiarios.py -v
"""

import pytest

from app.modules.accounting.schemas.schemas_subdiario import (
    CuentasSubdiario,
    NaturalezaVenta,
    SubdiarioBase,
)
from app.modules.accounting.services.catalogo_subdiarios import (
    CATALOGO_ESTANDAR,
    NATURALEZA_POR_SUBDIARIO,
)
from app.modules.accounting.services.subdiario_service import SubdiarioService

deducir = SubdiarioService.deducir_naturaleza


# ---------------------------------------------------------------------------
# 1. Clasificación por importes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("descripcion,importes,esperada", [
    ("solo gravada",
     {"base_gravada": 1000, "igv": 180}, NaturalezaVenta.GRAVADA),

    ("solo exonerada — el caso real de julio",
     {"exonerado": 1800}, NaturalezaVenta.EXONERADA),

    ("solo inafecta",
     {"inafecto": 500}, NaturalezaVenta.INAFECTA),

    ("exportación",
     {"exportacion": 5000}, NaturalezaVenta.EXPORTACION),

    ("gravada y exonerada a la vez",
     {"base_gravada": 1000, "igv": 180, "exonerado": 500}, NaturalezaVenta.MIXTO),

    ("exportación y gravada",
     {"exportacion": 200, "base_gravada": 100}, NaturalezaVenta.MIXTO),

    ("las tres",
     {"base_gravada": 1, "exonerado": 1, "inafecto": 1}, NaturalezaVenta.MIXTO),
])
def test_naturaleza_deducida_de_los_importes(descripcion, importes, esperada):
    assert deducir(importes) == esperada, descripcion


def test_importes_en_texto_y_nulos_no_rompen():
    """SUNAT manda los importes como texto y a veces vacíos."""
    assert deducir({"exonerado": "1800.00", "base_gravada": ""}) == NaturalezaVenta.EXONERADA
    assert deducir({"base_gravada": None, "exonerado": "0"}) == NaturalezaVenta.GRAVADA


def test_comprobante_en_cero_cae_en_gravada():
    """
    Un comprobante sin ninguna base (anulado, por ejemplo) se clasifica como
    gravado: deja el asiento en cero, que es visible y corregible, en vez de
    quedarse sin subdiario y bloquear la importación.
    """
    assert deducir({}) == NaturalezaVenta.GRAVADA
    assert deducir({"base_gravada": 0, "exonerado": 0}) == NaturalezaVenta.GRAVADA


# ---------------------------------------------------------------------------
# 2. Cuándo un subdiario se puede usar
# ---------------------------------------------------------------------------

def _subdiario(naturaleza, cobro="121101", ingreso="701101", igv="401111"):
    return SubdiarioBase(
        codigo="05", nombre="X", asiento_ventas=True, naturaleza=naturaleza,
        cuentas=CuentasSubdiario(
            cuenta_cobro=cobro, cuenta_ingreso=ingreso, cuenta_igv=igv
        ),
    )


def test_gravada_necesita_las_tres_cuentas():
    """12, 70 y 40: sin la de IGV el asiento saldría descuadrado."""
    assert _subdiario(NaturalezaVenta.GRAVADA).listo_para_contabilizar()
    assert not _subdiario(NaturalezaVenta.GRAVADA, igv="").listo_para_contabilizar()


def test_exonerada_e_inafecta_solo_necesitan_12_y_70():
    """No trasladan IGV, así que exigir la cuenta 40 las bloquearía sin motivo."""
    for naturaleza in (NaturalezaVenta.EXONERADA, NaturalezaVenta.INAFECTA):
        assert _subdiario(naturaleza, igv="").listo_para_contabilizar(), naturaleza


def test_sin_cuenta_de_ingreso_no_esta_listo():
    assert not _subdiario(NaturalezaVenta.EXONERADA, ingreso="", igv="").listo_para_contabilizar()


def test_un_subdiario_que_no_es_de_ventas_nunca_esta_listo():
    s = _subdiario(NaturalezaVenta.GRAVADA)
    s.asiento_ventas = False
    assert not s.listo_para_contabilizar()


def test_un_subdiario_puede_servir_a_varios_tipos():
    """Las casillas son independientes, como en la pantalla de mantenimiento."""
    s = SubdiarioBase(codigo="44", nombre="DIARIO", asiento_caja=True, asiento_bancos=True)
    assert sorted(s.tipos_de_asiento()) == ["Bancos", "Caja"]


def test_codigo_debe_ser_numerico_de_dos_digitos():
    with pytest.raises(ValueError):
        SubdiarioBase(codigo="A5", nombre="X")


# ---------------------------------------------------------------------------
# 3. El catálogo estándar
# ---------------------------------------------------------------------------

def test_el_catalogo_no_repite_codigos():
    codigos = [s["codigo"] for s in CATALOGO_ESTANDAR]
    assert len(codigos) == len(set(codigos))


def test_hay_un_subdiario_de_venta_por_cada_naturaleza():
    """Si faltara uno, los comprobantes de esa naturaleza no se podrían clasificar."""
    naturalezas = {
        s.get("naturaleza") for s in CATALOGO_ESTANDAR if s.get("asiento_ventas")
    }
    assert naturalezas == {n.value for n in NaturalezaVenta}


def test_los_codigos_de_venta_son_los_del_04_al_09():
    de_venta = sorted(s["codigo"] for s in CATALOGO_ESTANDAR if s.get("asiento_ventas"))
    assert de_venta == ["04", "05", "06", "07", "08", "09"]


def test_el_mapa_de_naturalezas_apunta_a_subdiarios_que_existen():
    codigos = {s["codigo"] for s in CATALOGO_ESTANDAR}
    for naturaleza, codigo in NATURALEZA_POR_SUBDIARIO.items():
        assert codigo in codigos, f"{naturaleza} apunta al {codigo}, que no está en el catálogo"


def test_las_cuentas_sembradas_son_las_que_el_erp_ya_usa():
    """
    Solo se siembran cuentas que ya están en uso (121101, 401111, 701101). Las
    de exoneradas, inafectas y exportaciones se dejan vacías **a propósito**:
    inventarlas produciría asientos mal imputados sin que nadie se entere.
    """
    por_codigo = {s["codigo"]: s for s in CATALOGO_ESTANDAR}

    assert por_codigo["05"]["cuentas"]["cuenta_ingreso"] == "701101"
    assert por_codigo["05"]["cuentas"]["cuenta_igv"] == "401111"

    for codigo in ("04", "06", "07"):
        assert por_codigo[codigo]["cuentas"]["cuenta_ingreso"] == "", (
            f"El subdiario {codigo} no debe traer una cuenta de ingreso inventada"
        )
        assert por_codigo[codigo]["cuentas"]["cuenta_cobro"] == "121101"

    # Exoneradas e inafectas no llevan IGV
    for codigo in ("06", "07"):
        assert por_codigo[codigo]["cuentas"]["cuenta_igv"] == ""


def test_el_catalogo_cubre_compras_y_tesoreria():
    """No es solo de ventas: el mantenimiento sirve a todo el plan de trabajo."""
    compras = [s for s in CATALOGO_ESTANDAR if s.get("asiento_compras")]
    assert len(compras) >= 6
    assert any(s.get("asiento_bancos") for s in CATALOGO_ESTANDAR)
    assert any(s.get("asiento_honorarios") for s in CATALOGO_ESTANDAR)
