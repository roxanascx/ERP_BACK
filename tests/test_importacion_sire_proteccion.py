"""
Lo que la reimportación NO debe pisar.

Reimportar un periodo es normal: SUNAT corrige datos y el usuario vuelve a
traerlos. El problema aparece cuando el comprobante ya generó su asiento: si se
actualiza el importe en la venta pero el asiento del libro se queda con el
viejo, la venta y el libro se contradicen y nada avisa. Por eso esos casos se
bloquean y se reportan.

Ejecutar:  python -m pytest tests/test_importacion_sire_proteccion.py -v
"""

from app.modules.accounting.services.importacion_sire_service import (
    ImportacionSireService,
)

ya_contabilizado = ImportacionSireService._ya_contabilizado
cambia = ImportacionSireService._cambia_el_asiento


def venta(**campos):
    base = {"importe_total": 1180.0, "igv_ipm": 180.0, "estado_operacion": 1}
    return {**base, **campos}


# ---------------------------------------------------------------------------
# Reconocer un comprobante ya contabilizado
# ---------------------------------------------------------------------------

def test_sin_lote_no_esta_contabilizado():
    assert not ya_contabilizado(venta())
    assert not ya_contabilizado(None)
    assert not ya_contabilizado(venta(lote_contabilizacion=None))


def test_con_lote_si_esta_contabilizado():
    assert ya_contabilizado(venta(lote_contabilizacion="L20260911-97b429"))


# ---------------------------------------------------------------------------
# Qué cambio afecta al asiento y cuál no
# ---------------------------------------------------------------------------

def test_los_mismos_importes_no_cambian_el_asiento():
    assert not cambia(venta(), venta())


def test_cambiar_el_nombre_del_cliente_no_toca_el_asiento():
    """Los datos descriptivos sí se pueden actualizar sin deshacer nada."""
    previo = venta(razon_social="CUTIPA ROXANA")
    nuevo = venta(razon_social="CUTIPA MOLLEHUANCA ROXANA")
    assert not cambia(previo, nuevo)


def test_cambiar_el_importe_si_cambia_el_asiento():
    assert cambia(venta(importe_total=1180.0), venta(importe_total=1500.0))


def test_cambiar_solo_el_igv_tambien_cambia_el_asiento():
    """El IGV parte el asiento entre la 40 y la 70, así que importa."""
    assert cambia(venta(igv_ipm=180.0), venta(igv_ipm=0.0))


def test_anular_el_comprobante_cambia_el_asiento():
    """Pasar a anulado debe obligar a rehacer: ese asiento ya no debería existir."""
    assert cambia(venta(estado_operacion=1), venta(estado_operacion=9))


def test_una_diferencia_de_medio_centimo_no_cuenta():
    """Tolerancia de céntimo: el float no debe disparar bloqueos falsos."""
    assert not cambia(venta(importe_total=1180.0), venta(importe_total=1180.004))


def test_un_centimo_completo_si_cuenta():
    assert cambia(venta(importe_total=1180.0), venta(importe_total=1180.01))


def test_los_campos_faltantes_valen_cero():
    """Un registro viejo sin igv_ipm no debe reventar la comparación."""
    assert not cambia({"importe_total": 1000.0}, venta(importe_total=1000.0, igv_ipm=0))
