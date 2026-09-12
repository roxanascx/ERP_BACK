"""
Tests de la generación de asientos a partir del registro de ventas.

Esto es lo que acaba en el libro diario, así que los tests miran dos cosas: que
el asiento sea el correcto y que **cuadre siempre**. Un asiento descuadrado es
mucho más caro de arreglar que un comprobante apartado, de ahí que haya tantas
pruebas de lo que NO se debe contabilizar.

Ejecutar:  python -m pytest tests/test_contabilizacion_ventas.py -v
"""

import pytest

from app.modules.accounting.services.contabilizacion_ventas_service import (
    ContabilizacionVentasService,
)

construir = ContabilizacionVentasService.construir_lineas
motivo = ContabilizacionVentasService._motivo_para_apartar


def subdiario(codigo="05", cobro="121101", ingreso="701101", igv="401111", listo=True):
    return {
        "codigo": codigo,
        "nombre": "REGISTRO VENTAS",
        "listo": listo,
        "asiento_ventas": True,
        "cuentas": {"cuenta_cobro": cobro, "cuenta_ingreso": ingreso, "cuenta_igv": igv},
    }


def venta(**campos):
    base = {
        "tipo_comprobante": "01",
        "serie_comprobante": "E001",
        "numero_comprobante": "5",
        "importe_total": 0,
        "igv_ipm": 0,
        "estado_operacion": 1,
    }
    return {**base, **campos}


def totales(lineas):
    return (
        round(sum(l["debe"] for l in lineas), 2),
        round(sum(l["haber"] for l in lineas), 2),
    )


# ---------------------------------------------------------------------------
# 1. Los dos asientos que definió el usuario
# ---------------------------------------------------------------------------

def test_venta_gravada_mueve_12_40_y_70():
    """
    Factura gravada de S/ 1.180:
        12  Cuentas por cobrar   Debe  1.180
        40  IGV por pagar              Haber  180
        70  Ventas                     Haber 1.000
    """
    lineas = construir(venta(importe_total=1180, igv_ipm=180), subdiario())

    por_cuenta = {l["codigo"]: l for l in lineas}
    assert por_cuenta["121101"]["debe"] == 1180.0
    assert por_cuenta["401111"]["haber"] == 180.0
    assert por_cuenta["701101"]["haber"] == 1000.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_venta_exonerada_solo_mueve_12_y_70():
    """
    El caso real del usuario. Una operación exonerada de S/ 1.000 no traslada
    IGV, así que la cuenta 40 **no debe aparecer**: una línea en cero
    ensuciaría el libro.
    """
    sub = subdiario(codigo="06", igv="")
    lineas = construir(venta(importe_total=1000, igv_ipm=0), sub)

    assert len(lineas) == 2
    por_cuenta = {l["codigo"]: l for l in lineas}
    assert por_cuenta["121101"]["debe"] == 1000.0
    assert por_cuenta["701101"]["haber"] == 1000.0
    assert "401111" not in por_cuenta
    assert totales(lineas) == (1000.0, 1000.0)


def test_el_caso_real_de_julio():
    """La factura exonerada de S/ 1.800 del periodo 202607."""
    lineas = construir(
        venta(importe_total=1800, igv_ipm=0), subdiario(codigo="06", igv="")
    )
    assert totales(lineas) == (1800.0, 1800.0)


# ---------------------------------------------------------------------------
# 2. Notas de crédito: invierten una sola vez
# ---------------------------------------------------------------------------

def test_nota_de_credito_invierte_los_lados():
    """Una nota de crédito deshace la venta: 12 va al Haber."""
    lineas = construir(
        venta(tipo_comprobante="07", importe_total=1180, igv_ipm=180), subdiario()
    )

    por_cuenta = {l["codigo"]: l for l in lineas}
    assert por_cuenta["121101"]["haber"] == 1180.0
    assert por_cuenta["701101"]["debe"] == 1000.0
    assert por_cuenta["401111"]["debe"] == 180.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_importe_negativo_tambien_invierte():
    """Si SUNAT manda el importe firmado, el efecto debe ser el mismo."""
    lineas = construir(venta(importe_total=-1180, igv_ipm=-180), subdiario())
    por_cuenta = {l["codigo"]: l for l in lineas}
    assert por_cuenta["121101"]["haber"] == 1180.0
    assert totales(lineas) == (1180.0, 1180.0)


def test_nota_de_credito_con_importe_negativo_no_se_invierte_dos_veces():
    """
    El caso que se escapa: tipo 07 **y** además importe negativo. Invertir por
    los dos motivos dejaria el asiento como una venta normal.
    """
    lineas = construir(
        venta(tipo_comprobante="07", importe_total=-1180, igv_ipm=-180), subdiario()
    )
    por_cuenta = {l["codigo"]: l for l in lineas}
    assert por_cuenta["121101"]["haber"] == 1180.0, "la 12 debe seguir en el Haber"
    assert por_cuenta["121101"]["debe"] == 0.0


# ---------------------------------------------------------------------------
# 3. El asiento cuadra siempre
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("total,igv", [
    (1180, 180), (1000, 0), (118, 18), (0.01, 0), (99999.99, 15254.24),
])
def test_el_asiento_siempre_cuadra(total, igv):
    lineas = construir(venta(importe_total=total, igv_ipm=igv), subdiario())
    debe, haber = totales(lineas)
    assert abs(debe - haber) < 0.01, f"descuadre con total={total} igv={igv}"


def test_ninguna_linea_lleva_debe_y_haber_a_la_vez():
    """El esquema del asiento lo prohíbe, así que hay que respetarlo aquí."""
    lineas = construir(venta(importe_total=1180, igv_ipm=180), subdiario())
    for l in lineas:
        assert not (l["debe"] > 0 and l["haber"] > 0)
        assert l["debe"] > 0 or l["haber"] > 0


def test_sin_cuenta_configurada_no_se_inventa_la_linea():
    """Si falta la cuenta de ingreso, esa línea no se genera (y el asiento no cuadrará)."""
    lineas = construir(venta(importe_total=1000), subdiario(ingreso="", igv=""))
    assert [l["codigo"] for l in lineas] == ["121101"]


# ---------------------------------------------------------------------------
# 4. Lo que NO se debe contabilizar
# ---------------------------------------------------------------------------

def test_un_comprobante_anulado_se_aparta():
    assert "anulado" in motivo(venta(estado_operacion=8, importe_total=100), subdiario())
    assert "anulado" in motivo(venta(estado_operacion=9, importe_total=100), subdiario())


def test_sin_subdiario_se_aparta():
    assert "subdiario" in motivo(venta(importe_total=100), None)


def test_con_el_subdiario_incompleto_se_aparta_diciendo_que_falta():
    sub = subdiario(codigo="06", ingreso="", igv="")
    sub["listo"] = False
    sub["naturaleza"] = "EXONERADA"
    m = motivo(venta(importe_total=100), sub)
    assert "06" in m and "cuenta de ingreso" in m


def test_los_tributos_sin_cuenta_apartan_el_comprobante():
    """
    ISC, IVAP, ICBPER y otros tributos no tienen cuenta en el subdiario.
    Meterlos en la cuenta de ventas seria imputarlos mal, asi que el
    comprobante se aparta con el motivo a la vista.
    """
    for tributo in ("isc", "ivap", "icbper", "otros_tributos_cargos"):
        v = venta(importe_total=1000, **{tributo: 50})
        m = motivo(v, subdiario())
        assert m and tributo in m, f"{tributo} deberia apartar el comprobante"


def test_un_comprobante_en_cero_se_aparta():
    assert "cero" in motivo(venta(importe_total=0), subdiario())


def test_una_venta_normal_no_se_aparta():
    assert motivo(venta(importe_total=1180, igv_ipm=180), subdiario()) is None
