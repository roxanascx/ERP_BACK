"""
Importación de las compras de SIRE al registro de compras.

Lo que se prueba aquí es la traducción: del TXT que manda SUNAT a un registro de
compra que el PLE 080000 y el asiento contable puedan usar. Es donde se pierde
dinero sin que salte ningún error, porque un importe mal mapeado se guarda tan
callado como uno bien mapeado.

El TXT de las pruebas usa los rótulos de columna reales del manual de Compras.

Ejecutar:  python -m pytest tests/test_importacion_sire_compras.py -v
"""

from decimal import Decimal

import pytest

from app.modules.accounting.services.importacion_sire_compras_service import (
    ImportacionSireComprasService,
    _fecha_iso,
    _tipo_documento,
)
from app.modules.sire.utils.propuesta_rce import parsear_propuesta

traducir = ImportacionSireComprasService.a_registro_compra
clave = ImportacionSireComprasService.clave
cambia = ImportacionSireComprasService._cambia_el_asiento
a_documento = ImportacionSireComprasService._a_documento


CABECERA = "|".join([
    "Periodo", "CAR SUNAT", "Fecha de emisión", "Fecha Vcto/Pago", "Tipo CP/Doc.",
    "Serie del CDP", "Nro CP o Doc. Nro Inicial (Rango)", "Tipo Doc Identidad",
    "Nro Doc Identidad", "Apellidos Nombres/ Razón  Social", "BI Gravado DG",
    "IGV / IPM DG", "Valor Adq. NG", "ISC", "ICBPER", "Otros Trib/ Cargos",
    "Total CP", "Moneda", "Tipo de Cambio",
])


def linea(**campos) -> str:
    base = {
        "Periodo": "202607",
        "CAR SUNAT": "0001",
        "Fecha de emisión": "10/07/2026",
        "Fecha Vcto/Pago": "",
        "Tipo CP/Doc.": "01",
        "Serie del CDP": "F001",
        "Nro CP o Doc. Nro Inicial (Rango)": "555",
        "Tipo Doc Identidad": "6",
        "Nro Doc Identidad": "20602318321",
        "Apellidos Nombres/ Razón  Social": "PROVEEDOR EJEMPLO S.A.C.",
        "BI Gravado DG": "1000.00",
        "IGV / IPM DG": "180.00",
        "Valor Adq. NG": "0.00",
        "ISC": "0.00",
        "ICBPER": "0.00",
        "Otros Trib/ Cargos": "0.00",
        "Total CP": "1180.00",
        "Moneda": "PEN",
        "Tipo de Cambio": "1.000",
    }
    base.update(campos)
    return "|".join(base[c] for c in CABECERA.split("|"))


def propuesta(*lineas) -> str:
    return CABECERA + "\n" + "\n".join(lineas or [linea()])


def comprobante(**campos):
    """Un comprobante ya parseado, listo para traducir."""
    encontrados, _ = parsear_propuesta(propuesta(linea(**campos)), "202607")
    return encontrados[0]


# ---------------------------------------------------------------------------
# 1. Leer el TXT de la propuesta
# ---------------------------------------------------------------------------

def test_el_txt_se_convierte_en_comprobantes():
    encontrados, meta = parsear_propuesta(propuesta(), "202607")

    assert len(encontrados) == 1
    assert not meta["campos_ausentes"], f"columnas no halladas: {meta['campos_ausentes']}"


def test_las_columnas_se_buscan_por_nombre_no_por_posicion():
    """
    El orden de las columnas ha cambiado entre versiones del manual. Buscar por
    posición hacía que los importes acabaran en el campo equivocado.
    """
    columnas = CABECERA.split("|")
    al_reves = "|".join(reversed(columnas))
    fila = "|".join(reversed(linea().split("|")))

    encontrados, _ = parsear_propuesta(al_reves + "\n" + fila, "202607")

    assert encontrados[0]["importe_total"] == 1180.00
    assert encontrados[0]["razon_social_proveedor"] == "PROVEEDOR EJEMPLO S.A.C."


def test_un_archivo_sin_filas_lo_dice_en_vez_de_reventar():
    encontrados, meta = parsear_propuesta(CABECERA, "202607")
    assert encontrados == []
    assert "error" in meta


def test_una_columna_que_falta_deja_ese_campo_en_cero_y_avisa():
    """Si SUNAT renombra una columna, el resto del comprobante se sigue leyendo."""
    sin_igv = CABECERA.replace("IGV / IPM DG", "IGV RENOMBRADO")
    encontrados, meta = parsear_propuesta(sin_igv + "\n" + linea(), "202607")

    assert encontrados[0]["igv"] == 0.0
    assert encontrados[0]["importe_total"] == 1180.00
    assert "igv" in meta["campos_ausentes"]


def test_las_lineas_en_blanco_se_saltan():
    encontrados, _ = parsear_propuesta(propuesta(linea(), "", linea()), "202607")
    assert len(encontrados) == 2


# ---------------------------------------------------------------------------
# 2. Traducir al registro de compra
# ---------------------------------------------------------------------------

def test_los_importes_llegan_completos():
    r = traducir(comprobante(), "202607")

    assert r["base_imponible_gravada"] == Decimal("1000.00")
    assert r["igv"] == Decimal("180.00")
    assert r["importe_total"] == Decimal("1180.00")


def test_el_proveedor_y_el_comprobante_se_identifican():
    r = traducir(comprobante(), "202607")

    assert r["numero_documento_proveedor"] == "20602318321"
    assert r["razon_social_proveedor"] == "PROVEEDOR EJEMPLO S.A.C."
    assert r["serie_comprobante"] == "F001"
    assert r["numero_comprobante"] == "555"
    assert r["tipo_comprobante"] == "01"


def test_la_fecha_pasa_al_formato_que_guarda_contabilidad():
    assert traducir(comprobante(), "202607")["fecha_comprobante"] == "2026-07-10"


def test_sin_fecha_de_vencimiento_queda_en_none_no_en_cadena_vacia():
    """El esquema declara las fechas como `date`: una cadena vacía no valida."""
    assert traducir(comprobante(), "202607")["fecha_vencimiento"] is None


def test_las_no_gravadas_van_al_campo_20_sin_repartirse():
    """
    La propuesta da un solo número («Valor Adq. NG»), igual que lo pide el PLE.
    Repartirlo entre exonerada e inafecta sería inventar un desglose que el
    archivo no trae.
    """
    r = traducir(
        comprobante(**{"BI Gravado DG": "0.00", "IGV / IPM DG": "0.00",
                       "Valor Adq. NG": "500.00", "Total CP": "500.00"}),
        "202607",
    )
    assert r["base_imponible_no_gravada"] == Decimal("500.00")


def test_el_comprobante_queda_marcado_como_venido_del_sire():
    """Es lo que impide que una captura a mano lo pise, y al revés."""
    assert traducir(comprobante(), "202607")["origen"] == "SIRE"


def test_se_conserva_el_car_de_sunat():
    assert traducir(comprobante(), "202607")["car_sunat"] == "0001"


# ---------------------------------------------------------------------------
# 3. El tipo de documento del proveedor
# ---------------------------------------------------------------------------

def test_el_tipo_de_documento_se_respeta_si_viene():
    assert _tipo_documento("6", "20602318321") == "6"


def test_sin_tipo_se_deduce_del_numero():
    """La columna falta en versiones antiguas de la propuesta."""
    assert _tipo_documento("", "20602318321") == "6", "11 dígitos es RUC"
    assert _tipo_documento("", "10426346") == "1", "8 dígitos es DNI"


def test_un_tipo_desconocido_no_se_guarda_tal_cual():
    """Guardar un código fuera de tabla hace que el registro no se pueda leer."""
    assert _tipo_documento("X", "algo") == "0"


def test_sin_nada_queda_como_sin_documento():
    assert _tipo_documento(None, None) == "0"


# ---------------------------------------------------------------------------
# 4. La identidad de un comprobante
# ---------------------------------------------------------------------------

def test_dos_proveedores_pueden_emitir_la_misma_serie_y_numero():
    """
    Por eso el RUC entra en la clave. Sin él, la factura F001-1 de un proveedor
    pisaría la F001-1 de otro al importar.
    """
    uno = traducir(comprobante(**{"Nro Doc Identidad": "20602318321"}), "202607")
    otro = traducir(comprobante(**{"Nro Doc Identidad": "20100066603"}), "202607")

    assert clave(uno) != clave(otro)


def test_el_mismo_comprobante_tiene_la_misma_clave():
    assert clave(traducir(comprobante(), "202607")) == clave(traducir(comprobante(), "202607"))


def test_el_periodo_forma_parte_de_la_identidad():
    uno = traducir(comprobante(), "202607")
    otro = traducir(comprobante(), "202608")
    assert clave(uno) != clave(otro)


# ---------------------------------------------------------------------------
# 5. No pisar lo que ya está contabilizado
# ---------------------------------------------------------------------------

def test_los_mismos_importes_no_cambian_el_asiento():
    r = traducir(comprobante(), "202607")
    assert not cambia(r, r)


def test_cambiar_el_importe_si_cambia_el_asiento():
    antes = traducir(comprobante(), "202607")
    despues = traducir(comprobante(**{"Total CP": "1500.00"}), "202607")
    assert cambia(antes, despues)


def test_cambiar_la_razon_social_no_toca_el_asiento():
    antes = traducir(comprobante(), "202607")
    despues = traducir(
        comprobante(**{"Apellidos Nombres/ Razón  Social": "PROVEEDOR EJEMPLO SAC"}),
        "202607",
    )
    assert not cambia(antes, despues)


def test_una_diferencia_de_medio_centimo_no_cuenta():
    assert not cambia({"importe_total": 1180.0}, {"importe_total": 1180.004, "igv": 0})


def test_un_centimo_completo_si_cuenta():
    assert cambia({"importe_total": 1180.0, "igv": 0}, {"importe_total": 1180.01, "igv": 0})


# ---------------------------------------------------------------------------
# 6. Lo que se guarda en Mongo
# ---------------------------------------------------------------------------

def test_los_decimal_se_convierten_a_float():
    listo = a_documento(traducir(comprobante(), "202607"))
    assert listo["importe_total"] == 1180.0
    assert not isinstance(listo["importe_total"], Decimal)


def test_no_queda_ningun_decimal_suelto():
    """El driver aborta la escritura entera si encuentra uno solo."""
    for valor in a_documento(traducir(comprobante(), "202607")).values():
        assert not isinstance(valor, Decimal)


def test_las_fechas_se_guardan_como_datetime_para_poder_filtrar():
    from datetime import datetime

    listo = a_documento(traducir(comprobante(), "202607"))
    assert isinstance(listo["fecha_comprobante"], datetime)
    assert listo["fecha_comprobante"].strftime("%Y-%m-%d") == "2026-07-10"


def test_una_fecha_ausente_sigue_ausente():
    listo = a_documento(traducir(comprobante(), "202607"))
    assert listo["fecha_vencimiento"] is None


def test_el_cero_sobrevive_la_conversion():
    """`Decimal('0.00')` es falsy: una conversión escrita con `or` lo perdería."""
    listo = a_documento(traducir(comprobante(), "202607"))
    assert listo["isc"] == 0.0
    assert "isc" in listo


# ---------------------------------------------------------------------------
# 7. Fechas sueltas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperada", [
    ("10/07/2026", "2026-07-10"),
    ("2026-07-10", "2026-07-10"),
    ("10-07-2026", "2026-07-10"),
])
def test_los_formatos_de_fecha_que_manda_sunat(entrada, esperada):
    assert _fecha_iso(entrada) == esperada


@pytest.mark.parametrize("entrada", ["", None, "  ", "no es una fecha"])
def test_lo_que_no_es_fecha_no_se_inventa(entrada):
    assert _fecha_iso(entrada) is None
