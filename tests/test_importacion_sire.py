"""
Tests de la importación de ventas de SIRE al registro de ventas.

Lo crítico aquí es el **mapeo**: cada importe de SUNAT tiene que caer en su campo
del PLE 140000. Un campo mal mapeado no da error, produce una declaración
incorrecta. Por eso el test principal usa un comprobante real, con los nombres
tal como los devuelve SUNAT.

Ejecutar:  python -m pytest tests/test_importacion_sire.py -v
"""

from decimal import Decimal

import pytest

from app.modules.accounting.services.importacion_sire_service import (
    ImportacionSireService,
    _fecha_iso,
)

traducir = ImportacionSireService.a_registro_venta

#: Comprobante tal como lo devolvió SUNAT para el periodo 202607 del RUC de
#: pruebas. Se conserva entero, con sus nombres originales, para que el test
#: falle si SUNAT renombra algo.
COMPROBANTE_REAL = {
    "id": "6a6cef64b15a15e430dba458",
    "numRuc": "20612969125",
    "nomRazonSocial": "SCUTI COMPANY SOCIEDAD ANONIMA CERRADA",
    "perPeriodoTributario": "202607",
    "codCar": "2061296912501E0010000000005",
    "codTipoCDP": "01",
    "numSerieCDP": "E001",
    "numCDP": "5",
    "fecEmision": "31/07/2026",
    "codTipoDocIdentidad": "6",
    "numDocIdentidad": "10426346082",
    "nomRazonSocialCliente": "CUTIPA MOLLEHUANCA ROXANA",
    "mtoValFactExpo": 0.0,
    "mtoBIGravada": 0.0,
    "mtoDsctoBI": 0.0,
    "mtoIGV": 0.0,
    "mtoDsctoIGV": 0.0,
    "mtoExonerado": 1800.0,
    "mtoInafecto": 0.0,
    "mtoISC": 0.0,
    "mtoBIIvap": 0.0,
    "mtoIvap": 0.0,
    "mtoIcbp": 0.0,
    "mtoOtrosTrib": 0.0,
    "mtoTotalCP": 1800.0,
    "codMoneda": "PEN",
    "mtoTipoCambio": 1,
    "codEstadoComprobante": "1",
    "desEstadoComprobante": "ACTIVO",
    "indTipoOperacion": "0101",
}


# ---------------------------------------------------------------------------
# 1. El mapeo, campo por campo
# ---------------------------------------------------------------------------

def test_datos_del_cliente_y_del_comprobante():
    r = traducir(COMPROBANTE_REAL, "202607")

    assert r["tipo_documento_cliente"] == "6"          # RUC
    assert r["numero_documento_cliente"] == "10426346082"
    assert r["razon_social_cliente"] == "CUTIPA MOLLEHUANCA ROXANA"
    assert r["tipo_comprobante"] == "01"               # Factura
    assert r["serie_comprobante"] == "E001"
    assert r["numero_comprobante"] == "5"


def test_todos_los_importes_del_ple_llegan_a_su_campo():
    """
    Los doce importes del PLE 140000. Si alguno se quedara en cero por un
    nombre mal escrito, la declaración saldría mal sin ningún aviso.
    """
    r = traducir(COMPROBANTE_REAL, "202607")

    esperado = {
        "valor_facturado_exportacion": "mtoValFactExpo",
        "base_imponible_gravada": "mtoBIGravada",
        "descuento_base_imponible": "mtoDsctoBI",
        "igv_ipm": "mtoIGV",
        "descuento_igv_ipm": "mtoDsctoIGV",
        "importe_exonerado": "mtoExonerado",
        "importe_inafecto": "mtoInafecto",
        "isc": "mtoISC",
        "base_imponible_ivap": "mtoBIIvap",
        "ivap": "mtoIvap",
        "icbper": "mtoIcbp",
        "otros_tributos_cargos": "mtoOtrosTrib",
        "importe_total": "mtoTotalCP",
    }

    for campo, origen in esperado.items():
        assert r[campo] == Decimal(str(COMPROBANTE_REAL[origen])), (
            f"{campo} deberia venir de {origen}"
        )


def test_el_exonerado_no_se_confunde_con_la_base_gravada():
    """El caso real: una factura exonerada tiene base gravada e IGV en cero."""
    r = traducir(COMPROBANTE_REAL, "202607")
    assert r["importe_exonerado"] == Decimal("1800.0")
    assert r["base_imponible_gravada"] == Decimal("0")
    assert r["igv_ipm"] == Decimal("0")
    assert r["importe_total"] == Decimal("1800.0")


def test_los_importes_son_decimal_no_float():
    """En contabilidad, un float redondea donde no debe."""
    r = traducir(COMPROBANTE_REAL, "202607")
    assert isinstance(r["importe_total"], Decimal)
    assert isinstance(r["igv_ipm"], Decimal)


def test_trazabilidad_hacia_sunat():
    """Sin el CAR no se puede reconciliar un registro con su origen."""
    r = traducir(COMPROBANTE_REAL, "202607")
    assert r["origen"] == "SIRE"
    assert r["car_sunat"] == "2061296912501E0010000000005"
    assert r["id_sunat"] == "6a6cef64b15a15e430dba458"
    assert r["periodo"] == "202607"


def test_estado_y_moneda():
    r = traducir(COMPROBANTE_REAL, "202607")
    assert r["estado_operacion"] == 1      # VIGENTE
    assert r["codigo_moneda"] == "PEN"
    assert r["tipo_cambio"] == Decimal("1")


# ---------------------------------------------------------------------------
# 2. Fechas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperada", [
    ("31/07/2026", "2026-07-31"),   # el formato de SUNAT
    ("2026-07-31", "2026-07-31"),   # ya en ISO
    ("31-07-2026", "2026-07-31"),
])
def test_la_fecha_se_pasa_a_iso(entrada, esperada):
    assert _fecha_iso(entrada) == esperada


def test_una_fecha_ilegible_se_conserva_tal_cual():
    """Mejor guardar lo que vino que inventarse una fecha plausible."""
    assert _fecha_iso("no es una fecha") == "no es una fecha"
    assert _fecha_iso(None) == ""


# ---------------------------------------------------------------------------
# 3. Casos que rompen si no se contemplan
# ---------------------------------------------------------------------------

def test_boleta_sin_documento_de_cliente():
    """Las boletas al publico suelen venir sin identificar."""
    boleta = {
        **COMPROBANTE_REAL,
        "codTipoCDP": "03",
        "codTipoDocIdentidad": None,
        "numDocIdentidad": None,
        "nomRazonSocialCliente": None,
    }
    r = traducir(boleta, "202607")

    assert r["tipo_comprobante"] == "03"
    assert r["tipo_documento_cliente"] == "0"          # Sin documento
    assert r["numero_documento_cliente"] == "-"
    assert r["razon_social_cliente"] == "SIN IDENTIFICAR"


def test_importes_ausentes_cuentan_como_cero():
    """SUNAT omite campos en algunos comprobantes."""
    r = traducir({"codTipoCDP": "01", "numCDP": "1"}, "202607")
    assert r["importe_total"] == Decimal("0")
    assert r["isc"] == Decimal("0")


def test_importes_en_texto():
    r = traducir({**COMPROBANTE_REAL, "mtoTotalCP": "1800.50"}, "202607")
    assert r["importe_total"] == Decimal("1800.50")


def test_comprobante_anulado_conserva_su_estado():
    r = traducir({**COMPROBANTE_REAL, "codEstadoComprobante": "8"}, "202607")
    assert r["estado_operacion"] == 8     # ANULADO


# ---------------------------------------------------------------------------
# 4. Identidad: es lo que hace idempotente la importacion
# ---------------------------------------------------------------------------

def test_la_clave_identifica_el_comprobante_dentro_del_periodo():
    r = traducir(COMPROBANTE_REAL, "202607")
    assert ImportacionSireService.clave(r) == ("01", "E001", "5", "202607")


def test_dos_comprobantes_distintos_tienen_claves_distintas():
    a = traducir(COMPROBANTE_REAL, "202607")
    b = traducir({**COMPROBANTE_REAL, "numCDP": "6"}, "202607")
    assert ImportacionSireService.clave(a) != ImportacionSireService.clave(b)


def test_el_mismo_numero_en_otro_periodo_es_otro_comprobante():
    a = traducir(COMPROBANTE_REAL, "202607")
    b = traducir(COMPROBANTE_REAL, "202608")
    assert ImportacionSireService.clave(a) != ImportacionSireService.clave(b)
