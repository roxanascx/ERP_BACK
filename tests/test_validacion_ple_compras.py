"""
PLE 080000 — Registro de Compras.

Este archivo se declara a SUNAT, así que lo que se prueba no es que el código
corra sino que **la línea diga lo que tiene que decir**: 33 campos, en su orden,
con las fechas y los montos en el formato que SUNAT espera.

El módulo estuvo generando un archivo vacío sin avisar, porque `compras_service`
captura la excepción de cada comprobante por separado y sigue. De ahí que varios
tests de aquí comprueben cosas que parecen obvias —que la fecha no salga en
blanco, que el tipo de comprobante no esté vacío—: son exactamente los síntomas
que nadie llegó a ver.

Ejecutar:  python -m pytest tests/test_validacion_ple_compras.py -v
"""

from datetime import date
from decimal import Decimal

import pytest

from app.modules.accounting.ple.ple_formatter_compras import PLEFormatterCompras
from app.modules.accounting.schemas.compras_schemas import (
    RegistroCompraResponse,
    TipoComprobanteCompra,
)

PERIODO = "202408"


def compra(**campos) -> RegistroCompraResponse:
    """Una factura gravada corriente de S/ 1.180."""
    base = {
        "id": "64f123456789012345678901",
        "empresa_id": "20612969125",
        "periodo": PERIODO,
        "fecha_comprobante": date(2024, 8, 15),
        "tipo_comprobante": "01",
        "serie_comprobante": "F001",
        "numero_comprobante": "000123",
        "tipo_documento_proveedor": "6",
        "numero_documento_proveedor": "20123456789",
        "razon_social_proveedor": "PROVEEDOR EJEMPLO S.A.C.",
        "base_imponible_gravada": Decimal("1000.00"),
        "igv": Decimal("180.00"),
        "importe_total": Decimal("1180.00"),
        "moneda": "PEN",
        "tipo_cambio": Decimal("1.000"),
        "clasificacion_bienes_servicios": "1",
        "estado_operacion": "1",
    }
    return RegistroCompraResponse(**{**base, **campos})


def campos_de(registro) -> list:
    """Los campos de la línea PLE, sin el separador final."""
    linea = PLEFormatterCompras().formatear_registro_compra(registro, PERIODO).to_ple_line()
    return linea.rstrip("|").split("|")


# ---------------------------------------------------------------------------
# 1. La estructura de la línea
# ---------------------------------------------------------------------------

def test_la_linea_tiene_los_33_campos_oficiales():
    assert len(campos_de(compra())) == 33


def test_la_linea_termina_en_separador():
    """SUNAT exige el `|` de cierre; sin él rechaza el archivo entero."""
    linea = PLEFormatterCompras().formatear_registro_compra(compra(), PERIODO).to_ple_line()
    assert linea.endswith("|")


def test_el_periodo_va_en_el_primer_campo():
    assert campos_de(compra())[0] == PERIODO


# ---------------------------------------------------------------------------
# 2. Las fechas
# ---------------------------------------------------------------------------

def test_la_fecha_de_emision_sale_en_formato_sunat():
    """
    El esquema declara las fechas como `date` y el formateador solo miraba
    cadenas: el `re.match` lanzaba TypeError, el `except` se lo tragaba y la
    fecha salía **vacía** en todas las líneas del archivo.
    """
    assert campos_de(compra())[3] == "15/08/2024"


def test_la_fecha_de_vencimiento_tambien():
    assert campos_de(compra(fecha_vencimiento=date(2024, 8, 30)))[4] == "30/08/2024"


def test_sin_fecha_de_vencimiento_el_campo_va_vacio():
    """Es opcional: vacío es correcto, pero tiene que seguir ocupando su sitio."""
    campos = campos_de(compra())
    assert campos[4] == ""
    assert len(campos) == 33


def test_la_fecha_de_la_detraccion_sale_formateada():
    assert campos_de(compra(fecha_emision_detraccion=date(2024, 8, 20)))[25] == "20/08/2024"


# ---------------------------------------------------------------------------
# 3. Los códigos, vengan como texto o como Enum
# ---------------------------------------------------------------------------

def test_el_tipo_de_comprobante_sale_del_texto():
    """El esquema lo declara `str`; hacer `.value` sobre él era un AttributeError."""
    assert campos_de(compra())[5] == "01"


def test_el_tipo_de_comprobante_tambien_funciona_como_enum():
    """Hay rutas que todavía construyen el registro con los Enum del módulo."""
    assert campos_de(compra(tipo_comprobante=TipoComprobanteCompra.FACTURA))[5] == "01"


def test_el_tipo_de_documento_del_proveedor():
    assert campos_de(compra())[10] == "6"


def test_el_estado_de_la_operacion():
    assert campos_de(compra())[32] == "1"


# ---------------------------------------------------------------------------
# 4. Los importes
# ---------------------------------------------------------------------------

def test_la_base_y_el_igv_van_con_dos_decimales():
    campos = campos_de(compra())
    assert campos[13] == "1000.00"
    assert campos[14] == "180.00"


def test_el_importe_total():
    assert campos_de(compra())[22] == "1180.00"


def test_los_importes_vacios_van_en_cero_no_en_blanco():
    """Un campo numérico en blanco hace que SUNAT rechace la línea."""
    campos = campos_de(compra())
    for indice in (15, 16, 17, 18, 19, 20, 21):
        assert campos[indice] == "0.00", f"el campo {indice + 1} salió vacío"


def test_la_moneda_sale_del_campo_moneda():
    """El formateador pedía `codigo_moneda`, que no existe en el esquema."""
    assert campos_de(compra())[23] == "PEN"


# ---------------------------------------------------------------------------
# 5. Adquisiciones no gravadas (campo 20)
# ---------------------------------------------------------------------------

def test_las_no_gravadas_se_declaran_en_el_campo_20():
    registro = compra(
        base_imponible_gravada=Decimal("0.00"),
        igv=Decimal("0.00"),
        base_imponible_no_gravada=Decimal("500.00"),
        importe_total=Decimal("500.00"),
    )
    assert campos_de(registro)[19] == "500.00"


def test_el_campo_20_se_completa_con_el_desglose_si_nadie_lo_puso():
    """
    Sin esto, un comprobante cargado con base exonerada declaraba adquisiciones
    no gravadas en cero: el archivo cuadra consigo mismo pero declara de menos.
    """
    registro = compra(
        base_imponible_gravada=Decimal("0.00"),
        igv=Decimal("0.00"),
        base_imponible_exonerada=Decimal("300.00"),
        base_imponible_inafecta=Decimal("200.00"),
        importe_total=Decimal("500.00"),
    )
    assert registro.base_imponible_no_gravada == Decimal("500.00")
    assert campos_de(registro)[19] == "500.00"


def test_un_campo_20_explicito_manda_sobre_el_desglose():
    registro = compra(
        base_imponible_no_gravada=Decimal("700.00"),
        base_imponible_exonerada=Decimal("300.00"),
    )
    assert registro.base_imponible_no_gravada == Decimal("700.00")


# ---------------------------------------------------------------------------
# 6. Importaciones y detracciones
# ---------------------------------------------------------------------------

def test_el_anio_de_la_dua_solo_aparece_si_se_carga():
    """Campo 8: vacío en una compra local, con año en una importación."""
    assert campos_de(compra())[7] == ""
    assert campos_de(compra(anio_emision_dua_dsi="2024"))[7] == "2024"


def test_la_constancia_de_detraccion_llega_al_campo_27():
    assert campos_de(compra(numero_constancia_detraccion="00123456789"))[26] == "00123456789"


# ---------------------------------------------------------------------------
# 7. El archivo
# ---------------------------------------------------------------------------

def test_el_nombre_del_archivo_sigue_la_nomenclatura_sunat():
    nombre = PLEFormatterCompras().generar_nombre_archivo_ple(
        empresa_ruc="20123456789", periodo_aaaamm=PERIODO, correlativo="0001"
    )
    assert nombre.startswith("LE20123456789202408")
    assert "080000" in nombre
    assert nombre.endswith(".txt")


@pytest.mark.parametrize("cuantos", [1, 3])
def test_el_archivo_lleva_una_linea_por_comprobante(cuantos):
    formateador = PLEFormatterCompras()
    lineas = [
        formateador.formatear_registro_compra(compra(numero_comprobante=str(n)), PERIODO)
        for n in range(1, cuantos + 1)
    ]
    contenido = formateador.generar_contenido_archivo_ple(lineas)

    assert len([x for x in contenido.splitlines() if x.strip()]) == cuantos
