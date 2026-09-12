"""
Catálogo estándar de subdiarios.

Son los códigos que usa la práctica contable peruana. Se siembran la primera vez
que una empresa entra en la configuración, para que nadie tenga que teclear
cuarenta filas antes de poder trabajar.

**Las cuentas**: se rellenan solo las que ya están en uso en este ERP
(`121101` cuentas por cobrar, `401111` IGV por pagar, `701101` ventas gravadas,
`42121101` facturas por pagar, `40111101` IGV crédito fiscal).

Las que dependen de cada empresa se dejan **vacías a propósito**: la cuenta de
ingreso de exoneradas, inafectas y exportaciones (cada empresa usa su subcuenta
del 70) y **todas las cuentas de gasto de compras** (60 mercaderías, 63
servicios... depende de qué compra sea). Adivinarlas produciría asientos
silenciosamente mal imputados. La pantalla las marca como pendientes y el
subdiario no se puede contabilizar hasta completarlas.
"""

from typing import Any, Dict, List

from ..schemas.schemas_subdiario import NaturalezaCompra, NaturalezaVenta

#: Cuentas ya en uso en el ERP, seguras como valor de partida.
CUENTA_POR_COBRAR = "121101"
CUENTA_IGV = "401111"
CUENTA_VENTAS_GRAVADAS = "701101"

#: Compras. La 42 y la 40 son las mismas para todas las empresas; la de
#: gasto no, porque depende de qué se compró.
CUENTA_POR_PAGAR = "42121101"
CUENTA_IGV_CREDITO = "40111101"


def _venta(codigo: str, nombre: str, naturaleza: NaturalezaVenta,
           cuenta_ingreso: str = "", con_igv: bool = False) -> Dict[str, Any]:
    return {
        "codigo": codigo,
        "nombre": nombre,
        "detalle": nombre,
        "asiento_ventas": True,
        "naturaleza": naturaleza.value,
        "cuentas": {
            "cuenta_cobro": CUENTA_POR_COBRAR,
            "cuenta_ingreso": cuenta_ingreso,
            "cuenta_igv": CUENTA_IGV if con_igv else "",
        },
    }


def _compra(codigo: str, nombre: str, naturaleza: NaturalezaCompra,
            con_igv: bool = True) -> Dict[str, Any]:
    """
    Subdiario de compra. Espejo de `_venta`.

    La cuenta de gasto va vacía siempre: es la que cambia de una empresa a
    otra y de un tipo de compra a otro.
    """
    return {
        "codigo": codigo,
        "nombre": nombre,
        "detalle": nombre,
        "asiento_compras": True,
        "naturaleza_compra": naturaleza.value,
        "cuentas": {
            "cuenta_gasto": "",
            "cuenta_pago": CUENTA_POR_PAGAR,
            "cuenta_igv": CUENTA_IGV_CREDITO if con_igv else "",
        },
    }


def _simple(codigo: str, nombre: str, **marcas: Any) -> Dict[str, Any]:
    return {"codigo": codigo, "nombre": nombre, "detalle": nombre, **marcas}


#: Catálogo por defecto. El orden es el del código, como en la pantalla.
CATALOGO_ESTANDAR: List[Dict[str, Any]] = [
    _simple("00", "ASIENTO DE INICIO (APERTURA)"),
    _simple("01", "CAJA EFECTIVO", asiento_caja=True, modo_caja="A"),
    _simple("02", "COBRANZA FACTURACION AL CONTADO"),
    _simple("03", "PLANILLA DE COBRANZA"),

    # --- Ventas: los que alimentan la contabilización automática ---
    _venta("04", "REGISTRO VENTAS - EXPORTACIONES", NaturalezaVenta.EXPORTACION),
    _venta("05", "REGISTRO VENTAS - GRAVADAS", NaturalezaVenta.GRAVADA,
           cuenta_ingreso=CUENTA_VENTAS_GRAVADAS, con_igv=True),
    _venta("06", "REGISTRO VENTAS - EXONERADAS", NaturalezaVenta.EXONERADA),
    _venta("07", "REGISTRO VENTAS - INAFECTAS", NaturalezaVenta.INAFECTA),
    _venta("08", "REGISTRO VENTAS - MIXTO", NaturalezaVenta.MIXTO,
           cuenta_ingreso=CUENTA_VENTAS_GRAVADAS, con_igv=True),
    _venta("09", "REGISTRO VENTAS - GRAVADAS IGV 10%", NaturalezaVenta.GRAVADA_IGV_10,
           cuenta_ingreso=CUENTA_VENTAS_GRAVADAS, con_igv=True),

    _simple("10", "DETRACCIONES POR COBRAR"),

    # --- Compras ---
    _compra("11", "REGISTRO COMPRAS LOCALES - VTAS GRAVADAS", NaturalezaCompra.GRAVADA),
    _compra("12", "REGISTRO COMPRAS IMPORTACIONES - VTAS GRAVADAS",
            NaturalezaCompra.IMPORTACION),
    # Destino mixto (prorrata del credito fiscal): lo decide el usuario segun
    # a que ventas se destino la compra, no se puede deducir de los importes.
    _compra("13", "REGISTRO COMPRAS - VTAS GRAV. Y NO GRAVA.",
            NaturalezaCompra.GRAVADA_Y_NO_GRAVADA),
    # Sin derecho a crédito: el IGV existe pero no va a la cuenta 40, se
    # suma al gasto. De ahí que no lleve cuenta de IGV.
    _compra("14", "REGISTRO COMPRAS - SIN DERECHO CREDITO",
            NaturalezaCompra.SIN_DERECHO_CREDITO, con_igv=False),
    _simple("15", "REGISTRO DE HONORARIOS", asiento_honorarios=True),
    _compra("16", "REGISTRO COMPRAS - NO GRAVADAS",
            NaturalezaCompra.NO_GRAVADA, con_igv=False),
    _compra("17", "REGISTRO COMPRAS - MIXTO", NaturalezaCompra.MIXTA),
    _compra("18", "REGISTRO COMPRAS - GRAVADAS IGV 10%",
            NaturalezaCompra.GRAVADA_IGV_10),

    _simple("19", "FACTURAS DEL EXTERIOR"),
    _simple("20", "PROVISION IGV NO DOMICILIADOS"),

    # --- Tesorería ---
    _simple("21", "BANCOS - INGRESOS", asiento_bancos=True, modo_bancos="I"),
    _simple("22", "BANCOS - EGRESOS VARIOS", asiento_bancos=True, modo_bancos="E"),
    _simple("23", "BANCOS - CHEQUES", asiento_cheque=True),
    _simple("24", "RETENCIONES"),
    _simple("25", "LETRAS POR PAGAR"),
    _simple("26", "PERCEPCIONES"),
    _simple("27", "RENDICION DE CUENTA"),
    _simple("29", "DESPACHOS"),
    _simple("30", "MOVIMIENTOS DE ALMACEN"),
    _simple("31", "PROVISIONES VARIAS"),
    _simple("32", "COSTO DE PRODUCCION"),
    _simple("33", "COSTO DE VENTAS"),
    _simple("34", "CONSUMO DE MATERIALES / MP"),
    _simple("35", "PLANILLA DE SUELDOS Y SALARIOS"),
    _simple("36", "COSTO DE ENAJENACION"),
    _simple("37", "BAJA DE ACTIVO FIJO"),
    _simple("39", "DEPRECIACION Y AMORTIZACION"),
    _simple("40", "APLICACIONES VARIAS", asiento_canje_aplicacion=True),
    _simple("41", "CANJE DE LETRAS POR COBRAR"),
    _simple("42", "MOVIMIENTO DE LETRAS POR COBRAR"),
    _simple("43", "FONDOS EN GARANTIA"),
    _simple("44", "DIARIO"),
    _simple("45", "FACTORING"),
    _simple("55", "REGULARIZACION AUT. DIF CAMBIO"),
    _simple("56", "AJUSTE AUT. POR DIF. CAMBIO-NIC 21"),
    _simple("59", "AJUSTE POR INFLACION"),
]


#: Cómo se deduce el subdiario de venta a partir de los importes del comprobante.
#: El orden importa: se evalúa de arriba abajo y gana la primera que encaje.
#: Código estándar de cada naturaleza de compra, para caer de pie cuando la
#: empresa no tiene un subdiario marcado con esa naturaleza.
NATURALEZA_COMPRA_POR_SUBDIARIO = {
    NaturalezaCompra.GRAVADA: "11",
    NaturalezaCompra.IMPORTACION: "12",
    NaturalezaCompra.SIN_DERECHO_CREDITO: "14",
    NaturalezaCompra.NO_GRAVADA: "16",
    NaturalezaCompra.MIXTA: "17",
    NaturalezaCompra.GRAVADA_IGV_10: "18",
}

NATURALEZA_POR_SUBDIARIO = {
    NaturalezaVenta.EXPORTACION: "04",
    NaturalezaVenta.GRAVADA: "05",
    NaturalezaVenta.EXONERADA: "06",
    NaturalezaVenta.INAFECTA: "07",
    NaturalezaVenta.MIXTO: "08",
    NaturalezaVenta.GRAVADA_IGV_10: "09",
}
