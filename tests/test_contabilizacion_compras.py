"""
Tests de la generación de asientos a partir del registro de compras.

Esto es lo que acaba en el libro diario, así que los tests miran dos cosas: que
el asiento sea el correcto y que **cuadre siempre**. Un asiento descuadrado es
mucho más caro de arreglar que un comprobante apartado.

El caso que más atención lleva es el crédito fiscal. Un IGV que se manda a la
cuenta 40 cuando no da derecho a crédito es un problema tributario, no un
descuadre: el libro sale cuadrado y el error no se ve hasta la fiscalización.

Ejecutar:  python -m pytest tests/test_contabilizacion_compras.py -v
"""

import pytest

from app.modules.accounting.schemas.schemas_subdiario import NaturalezaCompra
from app.modules.accounting.services.contabilizacion_compras_service import (
    ContabilizacionComprasService,
)

construir = ContabilizacionComprasService.construir_lineas
motivo = ContabilizacionComprasService._motivo_para_apartar


def subdiario(codigo="11", naturaleza=NaturalezaCompra.GRAVADA, gasto="60111101",
              igv="40111101", pago="42121101", listo=True):
    return {
        "codigo": codigo,
        "nombre": "REGISTRO COMPRAS",
        "listo": listo,
        "asiento_compras": True,
        "naturaleza_compra": naturaleza.value if naturaleza else None,
        "cuentas": {"cuenta_gasto": gasto, "cuenta_igv": igv, "cuenta_pago": pago},
    }


def compra(**campos):
    base = {
        "tipo_comprobante": "01",
        "serie_comprobante": "F001",
        "numero_comprobante": "100",
        "importe_total": 0,
        "igv": 0,
        "estado_operacion": "1",
    }
    return {**base, **campos}


def totales(lineas):
    return (
        round(sum(l["debe"] for l in lineas), 2),
        round(sum(l["haber"] for l in lineas), 2),
    )


def por_cuenta(lineas):
    return {l["codigo"]: l for l in lineas}


# ---------------------------------------------------------------------------
# 1. El asiento estándar
# ---------------------------------------------------------------------------

def test_compra_gravada_mueve_60_40_y_42():
    """
    Factura gravada de S/ 1.180:
        60  Compras              Debe  1.000
        40  IGV crédito fiscal   Debe    180
        42  Cuentas por pagar          Haber 1.180
    """
    lineas = construir(compra(importe_total=1180, igv=180), subdiario())

    cuentas = por_cuenta(lineas)
    assert cuentas["60111101"]["debe"] == 1000.0
    assert cuentas["40111101"]["debe"] == 180.0
    assert cuentas["42121101"]["haber"] == 1180.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_compra_no_gravada_solo_mueve_60_y_42():
    """Sin IGV no hay nada que llevar a la cuenta 40: una línea en cero ensucia."""
    sub = subdiario(codigo="16", naturaleza=NaturalezaCompra.NO_GRAVADA, igv="")
    lineas = construir(compra(importe_total=500, igv=0), sub)

    assert len(lineas) == 2
    cuentas = por_cuenta(lineas)
    assert cuentas["60111101"]["debe"] == 500.0
    assert cuentas["42121101"]["haber"] == 500.0
    assert "40111101" not in cuentas


# ---------------------------------------------------------------------------
# 2. El crédito fiscal
# ---------------------------------------------------------------------------

def test_sin_derecho_a_credito_el_igv_va_al_costo():
    """
    Subdiario 14. El IGV existe pero no se puede usar como crédito fiscal, así
    que forma parte del costo en vez de ir a la cuenta 40.

        60  Compras              Debe  1.180
        42  Cuentas por pagar          Haber 1.180
    """
    sub = subdiario(codigo="14", naturaleza=NaturalezaCompra.SIN_DERECHO_CREDITO, igv="")
    lineas = construir(compra(importe_total=1180, igv=180), sub)

    cuentas = por_cuenta(lineas)
    assert cuentas["60111101"]["debe"] == 1180.0, "el IGV tiene que quedarse en el costo"
    assert "40111101" not in cuentas
    assert totales(lineas) == (1180.0, 1180.0)


def test_sin_derecho_a_credito_aunque_el_subdiario_tenga_cuenta_de_igv():
    """
    Lo decide la naturaleza, no que haya una cuenta puesta. Si alguien configura
    una cuenta 40 en el subdiario 14, el IGV sigue sin ser crédito fiscal.
    """
    sub = subdiario(codigo="14", naturaleza=NaturalezaCompra.SIN_DERECHO_CREDITO)
    lineas = construir(compra(importe_total=1180, igv=180), sub)

    cuentas = por_cuenta(lineas)
    assert "40111101" not in cuentas, "la naturaleza manda sobre la cuenta configurada"
    assert cuentas["60111101"]["debe"] == 1180.0


def test_una_compra_no_gravada_con_igv_no_se_lo_lleva_a_la_40():
    """Si trae IGV por error, al costo: no se inventa un crédito que no existe."""
    sub = subdiario(codigo="16", naturaleza=NaturalezaCompra.NO_GRAVADA)
    lineas = construir(compra(importe_total=1180, igv=180), sub)

    assert "40111101" not in por_cuenta(lineas)
    assert totales(lineas) == (1180.0, 1180.0)


def test_sin_cuenta_de_igv_configurada_el_impuesto_no_se_pierde():
    """
    Si falta la cuenta, el IGV se queda en el gasto. Descontarlo del costo sin
    ponerlo en ningún sitio descuadraría el asiento por 180 soles.
    """
    lineas = construir(compra(importe_total=1180, igv=180), subdiario(igv=""))

    assert por_cuenta(lineas)["60111101"]["debe"] == 1180.0
    assert totales(lineas) == (1180.0, 1180.0)


# ---------------------------------------------------------------------------
# 3. Los tributos no recuperables van al costo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tributo", ["isc", "icbper", "otros_tributos"])
def test_los_tributos_no_recuperables_entran_en_el_costo(tributo):
    """
    Al revés que en ventas. Ahí son tributos que la empresa cobra y le debe a
    SUNAT, y hacen falta cuentas propias; aquí son tributos que **paga** y no
    recupera, así que forman parte de lo que costó la adquisición.
    """
    c = compra(importe_total=1230, igv=180, **{tributo: 50})
    lineas = construir(c, subdiario())

    cuentas = por_cuenta(lineas)
    assert cuentas["60111101"]["debe"] == 1050.0, "el tributo tiene que estar en el costo"
    assert cuentas["40111101"]["debe"] == 180.0
    assert totales(lineas) == (1230.0, 1230.0)


def test_un_comprobante_con_tributos_no_se_aparta():
    """En ventas sí se apartaba; aquí tienen sitio, así que se contabiliza."""
    c = compra(importe_total=1230, igv=180, isc=50)
    assert motivo(c, subdiario()) is None


# ---------------------------------------------------------------------------
# 4. Notas de crédito
# ---------------------------------------------------------------------------

def test_nota_de_credito_invierte_los_lados():
    """Una nota de crédito deshace la compra: la 42 va al Debe."""
    lineas = construir(
        compra(tipo_comprobante="07", importe_total=1180, igv=180), subdiario()
    )

    cuentas = por_cuenta(lineas)
    assert cuentas["42121101"]["debe"] == 1180.0
    assert cuentas["60111101"]["haber"] == 1000.0
    assert cuentas["40111101"]["haber"] == 180.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_importe_negativo_tambien_invierte():
    lineas = construir(compra(importe_total=-1180, igv=-180), subdiario())
    assert por_cuenta(lineas)["42121101"]["debe"] == 1180.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_nota_de_credito_con_importe_negativo_no_se_invierte_dos_veces():
    """Tipo 07 **y** además importe negativo: invertir por los dos lo dejaría igual."""
    lineas = construir(
        compra(tipo_comprobante="07", importe_total=-1180, igv=-180), subdiario()
    )
    cuentas = por_cuenta(lineas)
    assert cuentas["42121101"]["debe"] == 1180.0, "la 42 debe seguir en el Debe"
    assert cuentas["42121101"]["haber"] == 0.0


# ---------------------------------------------------------------------------
# 5. El asiento cuadra siempre
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("total,igv", [
    (1180, 180), (500, 0), (118, 18), (0.01, 0), (99999.99, 15254.24),
])
def test_el_asiento_siempre_cuadra(total, igv):
    lineas = construir(compra(importe_total=total, igv=igv), subdiario())
    debe, haber = totales(lineas)
    assert abs(debe - haber) < 0.01, f"descuadre con total={total} igv={igv}"


@pytest.mark.parametrize("naturaleza", list(NaturalezaCompra))
def test_cuadra_con_cualquier_naturaleza(naturaleza):
    lineas = construir(
        compra(importe_total=1180, igv=180), subdiario(naturaleza=naturaleza)
    )
    debe, haber = totales(lineas)
    assert abs(debe - haber) < 0.01, f"descuadre con naturaleza {naturaleza.value}"


def test_ninguna_linea_lleva_debe_y_haber_a_la_vez():
    lineas = construir(compra(importe_total=1180, igv=180), subdiario())
    for l in lineas:
        assert not (l["debe"] > 0 and l["haber"] > 0)
        assert l["debe"] > 0 or l["haber"] > 0


def test_sin_cuenta_de_gasto_no_se_inventa_la_linea():
    """Falta la cuenta que el usuario configura: la línea no se genera."""
    lineas = construir(compra(importe_total=1180, igv=180), subdiario(gasto=""))
    assert "60111101" not in por_cuenta(lineas)


# ---------------------------------------------------------------------------
# 6. Lo que NO se debe contabilizar
# ---------------------------------------------------------------------------

def test_un_comprobante_anulado_se_aparta():
    """En compras el estado llega como texto, no como entero."""
    assert "anulado" in motivo(compra(estado_operacion="2", importe_total=100), subdiario())
    assert "anulado" in motivo(compra(estado_operacion="9", importe_total=100), subdiario())


def test_sin_subdiario_se_aparta():
    assert "subdiario" in motivo(compra(importe_total=100), None)


def test_con_el_subdiario_incompleto_se_aparta_diciendo_que_falta():
    sub = subdiario(codigo="11", gasto="", listo=False)
    m = motivo(compra(importe_total=100), sub)
    assert "11" in m and "cuenta de gasto" in m


def test_un_comprobante_en_cero_se_aparta():
    assert "cero" in motivo(compra(importe_total=0), subdiario())


def test_una_compra_normal_no_se_aparta():
    assert motivo(compra(importe_total=1180, igv=180), subdiario()) is None
