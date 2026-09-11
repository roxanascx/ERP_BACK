"""
Alta de ventas capturadas a mano.

Dos cosas que se rompieron de verdad y que estos tests fijan:

1. Mongo no sabe codificar `Decimal`, y el esquema de ventas usa `Decimal` en
   los 20 campos de importes. Crear o editar una venta fallaba **siempre** con
   "cannot encode object: Decimal", aunque el 422 nunca llegaba: salía como un
   400 genérico de "error interno".
2. Una venta manual sin subdiario no aparece en el reparto por subdiario, así
   que el usuario no sabe dónde va a caer su asiento hasta que contabiliza.

Ejecutar:  python -m pytest tests/test_ventas_manual.py -v
"""

from decimal import Decimal

from app.modules.accounting.services.ventas_service import VentasService

a_documento = VentasService._a_documento


# ---------------------------------------------------------------------------
# Los importes tienen que salir del Decimal antes de tocar Mongo
# ---------------------------------------------------------------------------

def test_los_decimal_se_convierten_a_float():
    documento = a_documento({"importe_total": Decimal("1180.00"), "igv_ipm": Decimal("180.00")})

    assert documento["importe_total"] == 1180.0
    assert documento["igv_ipm"] == 180.0
    assert all(isinstance(v, float) for v in documento.values())


def test_no_queda_ningun_decimal_suelto():
    """
    El driver aborta la escritura entera si encuentra **un solo** Decimal, así
    que no basta con convertir los campos principales.
    """
    venta = {
        "valor_facturado_exportacion": Decimal("0.00"),
        "base_imponible_gravada": Decimal("1000.00"),
        "descuento_base_imponible": Decimal("0.00"),
        "igv_ipm": Decimal("180.00"),
        "importe_exonerado": Decimal("0.00"),
        "importe_inafecto": Decimal("0.00"),
        "isc": Decimal("0.00"),
        "ivap": Decimal("0.00"),
        "icbper": Decimal("0.00"),
        "tipo_cambio": Decimal("1.000"),
        "importe_total": Decimal("1180.00"),
    }

    for valor in a_documento(venta).values():
        assert not isinstance(valor, Decimal)


def test_lo_que_no_es_decimal_pasa_intacto():
    """Convertir de más rompería las fechas, los enums y los textos."""
    documento = a_documento({
        "razon_social_cliente": "EMPRESA EJEMPLO S.A.C.",
        "serie_comprobante": "F001",
        "estado_operacion": 1,
        "tipo_cambio": Decimal("1.000"),
        "fecha_vencimiento": None,
    })

    assert documento["razon_social_cliente"] == "EMPRESA EJEMPLO S.A.C."
    assert documento["serie_comprobante"] == "F001"
    assert documento["estado_operacion"] == 1
    assert documento["fecha_vencimiento"] is None
    assert documento["tipo_cambio"] == 1.0


def test_el_cero_sobrevive_la_conversion():
    """`Decimal('0.00')` es falsy: una conversión escrita con `or` lo perdería."""
    documento = a_documento({"isc": Decimal("0.00")})

    assert documento["isc"] == 0.0
    assert "isc" in documento


def test_un_importe_negativo_se_conserva():
    """Las notas de crédito llegan con importes en negativo."""
    assert a_documento({"importe_total": Decimal("-500.00")})["importe_total"] == -500.0
