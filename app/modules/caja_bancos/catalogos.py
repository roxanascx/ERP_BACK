"""
Catálogos de referencia para Caja/Bancos, transcritos de las tablas SUNAT que
usa el software contable de referencia del usuario (EJB Gestión Contable,
pantalla CONBAN02-Ingreso/Egreso). Listas estáticas, sin lógica: se exponen
tal cual vía API para poblar los `<select>` del formulario de movimiento.

Si algún código o descripción no calza exactamente con la publicación oficial
de SUNAT, es un problema de transcripción de esta lista, no de la lógica que
la usa — se puede corregir aquí sin tocar nada más.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Tipo de Documento (Tabla 10 SUNAT) — usada en libros/registros PLE y en las
# operaciones de tesorería (caja, bancos) para documentos no necesariamente
# tributarios (cheques, transferencias, letras, planillas...).
# ---------------------------------------------------------------------------
TIPOS_DOCUMENTO: List[Dict[str, str]] = [
    {"codigo": "AB", "descripcion": "ABONO BANCARIO"},
    {"codigo": "AF", "descripcion": "DOCUMENTO EMITIDO POR LAS AFP"},
    {"codigo": "AG", "descripcion": "RECIBO DE AGUA - COMISION DE REGANTES"},
    {"codigo": "AP", "descripcion": "APERTURA"},
    {"codigo": "BA", "descripcion": "BOLETO AEREO - TRANSPORTE REGULAR"},
    {"codigo": "BE", "descripcion": "BOLETO DE ENTRADA A ATRACCIONES O ESPECTACULOS"},
    {"codigo": "BF", "descripcion": "BOLETO DE VIAJE ELECTRONICO FERROVIARIO"},
    {"codigo": "BI", "descripcion": "BILLETES DE LOTERIA, RIFAS Y APUESTAS"},
    {"codigo": "BR", "descripcion": "BOLETO AEREO - TRANSPORTE NO REGULAR"},
    {"codigo": "BT", "descripcion": "BOLETO DE VIAJE PROVINCIAL NO ELECTRONICO"},
    {"codigo": "BU", "descripcion": "BOLETO DE VIAJE URBANO TERRESTRE Y FERROVIARIO"},
    {"codigo": "BV", "descripcion": "BOLETA DE VENTA"},
    {"codigo": "CA", "descripcion": "CARTA PORTE AEREO / SERVICIO DE CARGA"},
    {"codigo": "CB", "descripcion": "CARGO BANCARIO"},
    {"codigo": "CD", "descripcion": "CONSTANCIA DE DEPOSITO IVAP - LEY N.° 28211"},
    {"codigo": "CE", "descripcion": "CONOCIMIENTO DE EMBARQUE - TRANSPORTE"},
    {"codigo": "CH", "descripcion": "CHEQUE"},
    {"codigo": "CN", "descripcion": "NOTA DE CREDITO NO DOMICILIADO"},
    {"codigo": "CO", "descripcion": "COMPROBANTE DE OPERACIONES - LEY N.° 29972"},
    {"codigo": "CP", "descripcion": "COMPROBANTE DE PERCEPCION"},
    {"codigo": "CR", "descripcion": "COMPROBANTE DE RETENCION"},
    {"codigo": "CS", "descripcion": "COMPROBANTE DE PAGO SEAE"},
    {"codigo": "DA", "descripcion": "DOCUMENTO DE ATRIBUCION"},
    {"codigo": "DB", "descripcion": "DOCUMENTO DE INSTITUCION FINANCIERA / SEGUROS Y COOPERATIVAS"},
    {"codigo": "DC", "descripcion": "DECLARACION DE MENSAJERIA O COURIER"},
    {"codigo": "DF", "descripcion": "DOCUMENTOS EMITIDOS POR COFOPRI"},
    {"codigo": "DM", "descripcion": "DECLARACION ADUANERA DE MERCANCIAS"},
    {"codigo": "DN", "descripcion": "NOTA DE DEBITO NO DOMICILIADO"},
    {"codigo": "DO", "descripcion": "DOCUMENTO DEL OPERADOR"},
    {"codigo": "DP", "descripcion": "DOCUMENTO DEL PARTICIPE"},
    {"codigo": "DR", "descripcion": "DETRACCION"},
    {"codigo": "DS", "descripcion": "DESPACHO SIMPLIFICADO - IMPORTACION SIMPLIFICADA"},
    {"codigo": "DU", "descripcion": "DOCUMENTOS EMITIDOS POR CENTROS EDUCATIVOS"},
    {"codigo": "DV", "descripcion": "DOCUMENTOS QUE EMITEN LOS CONCESIONARIOS"},
    {"codigo": "EN", "descripcion": "ENTREGA (DEPOSITO)"},
    {"codigo": "ER", "descripcion": "DOCUMENTOS EMITIDOS POR EMPRESAS RECAUDADORAS"},
    {"codigo": "ET", "descripcion": "ETIQUETAS PARA EL PAGO DE LA TUUA"},
    {"codigo": "EX", "descripcion": "EXCESO DE CREDITO FISCAL POR RETIRO DE BIENES"},
    {"codigo": "FP", "descripcion": "FORMULARIO DE DECLARACION - PAGO O BOLETA"},
    {"codigo": "FT", "descripcion": "FACTURA"},
    {"codigo": "GS", "descripcion": "GUIA DE REMISION REMITENTE"},
    {"codigo": "IC", "descripcion": "DOCUMENTO IGLESIA CATOLICA"},
    {"codigo": "IN", "descripcion": "INVOICE NO DOMICILIADO"},
    {"codigo": "JB", "descripcion": "TARJETAS DE CREDITO Y DEBITO EMITIDAS POR BANCOS DEL EXTERIOR"},
    {"codigo": "JE", "descripcion": "TARJETAS DE CREDITO Y DEBITO EMITIDAS POR EMPRESAS NO BANCARIAS"},
    {"codigo": "LC", "descripcion": "LIQUIDACION DE COBRANZA"},
    {"codigo": "LE", "descripcion": "LETRA"},
    {"codigo": "LQ", "descripcion": "LIQUIDACION DE COMPRA"},
    {"codigo": "MP", "descripcion": "MANIFIESTO DE PASAJEROS"},
    {"codigo": "NA", "descripcion": "NOTA DE AJUSTE DE OPERACIONES - LEY N.° 25632"},
    {"codigo": "NB", "descripcion": "NOTA DE DEBITO ESPECIAL"},
    {"codigo": "NC", "descripcion": "NOTA DE CREDITO"},
    {"codigo": "ND", "descripcion": "NOTA DE DEBITO"},
    {"codigo": "NE", "descripcion": "NOTA DE CREDITO ESPECIAL"},
    {"codigo": "NH", "descripcion": "COMPROBANTE POR OPERACIONES NO HABITUALES"},
    {"codigo": "PA", "descripcion": "PAGO ANTICIPADO"},
    {"codigo": "PB", "descripcion": "POLIZA DE BOLSA / AGENTES"},
    {"codigo": "PC", "descripcion": "COMPROBANTE DE PERCEPCION - COMBUSTIBLE"},
    {"codigo": "PF", "descripcion": "POLIZA O DUI FRACCIONADA"},
    {"codigo": "PG", "descripcion": "PAGARE"},
    {"codigo": "PL", "descripcion": "PLANILLA"},
    {"codigo": "PO", "descripcion": "POLIZAS DE ADJUDICACION"},
    {"codigo": "PR", "descripcion": "PRESTAMO"},
    {"codigo": "RA", "descripcion": "RECIBO DE ARRENDAMIENTO"},
    {"codigo": "RC", "descripcion": "RECIBO DE SERVICIOS PUBLICOS"},
    {"codigo": "RD", "descripcion": "RECIBO DE DISTRIBUCION DE GAS NATURAL"},
    {"codigo": "RH", "descripcion": "RECIBO DE HONORARIOS"},
    {"codigo": "RL", "descripcion": "DUA (DECLARACION UNICA DE ADUANAS)"},
    {"codigo": "RP", "descripcion": "CERTIFICADO DE PAGO DE REGALIAS EMITIDA"},
    {"codigo": "ST", "descripcion": "SEGURO COMPLEMENTARIO DE TRABAJO DE RIESGO"},
    {"codigo": "TB", "descripcion": "TRANSFERENCIA BANCARIA O INTERBANCARIA"},
    {"codigo": "TK", "descripcion": "TICKET"},
    {"codigo": "VR", "descripcion": "VARIOS"},
]

# ---------------------------------------------------------------------------
# Medio de Pago — tabla de bancarización (Ley N.° 28194 - ITF).
# ---------------------------------------------------------------------------
MEDIOS_PAGO: List[Dict[str, str]] = [
    {"codigo": "001", "descripcion": "DEPOSITO EN CUENTA"},
    {"codigo": "002", "descripcion": "GIRO"},
    {"codigo": "003", "descripcion": "TRANSFERENCIA DE FONDOS"},
    {"codigo": "004", "descripcion": "ORDEN DE PAGO"},
    {"codigo": "005", "descripcion": "TARJETA DE DEBITO"},
    {"codigo": "006", "descripcion": "TARJETA DE CREDITO EMITIDA EN EL PAIS POR UNA ENTIDAD FINANCIERA"},
    {"codigo": "007", "descripcion": "CHEQUES CON LA CLAUSULA DE NO NEGOCIABLE, INTRANSFERIBLES, \"NO A LA ORDEN\" U OTRO EQUIVALENTE"},
    {"codigo": "008", "descripcion": "EFECTIVO, POR OPERACIONES EN LAS QUE NO EXISTE OBLIGACION DE UTILIZAR MEDIOS DE PAGO"},
    {"codigo": "009", "descripcion": "EFECTIVO, EN LOS DEMAS CASOS"},
    {"codigo": "010", "descripcion": "MEDIOS DE PAGO USADOS EN COMERCIO EXTERIOR"},
    {"codigo": "011", "descripcion": "LETRAS DE CAMBIO"},
    {"codigo": "012", "descripcion": "TARJETA DE CREDITO EMITIDA EN EL EXTERIOR POR UNA ENTIDAD NO DOMICILIADA"},
    {"codigo": "013", "descripcion": "TARJETA DE CREDITO EMITIDA EN EL EXTERIOR POR UNA ENTIDAD FINANCIERA NO DOMICILIADA"},
    {"codigo": "101", "descripcion": "TRANSFERENCIAS - COMERCIO EXTERIOR"},
    {"codigo": "102", "descripcion": "CHEQUES BANCARIOS - COMERCIO EXTERIOR"},
    {"codigo": "103", "descripcion": "ORDEN DE PAGO SIMPLE - COMERCIO EXTERIOR"},
    {"codigo": "104", "descripcion": "ORDEN DE PAGO DOCUMENTARIO - COMERCIO EXTERIOR"},
    {"codigo": "105", "descripcion": "REMESA SIMPLE - COMERCIO EXTERIOR"},
    {"codigo": "106", "descripcion": "REMESA DOCUMENTARIA - COMERCIO EXTERIOR"},
    {"codigo": "107", "descripcion": "CARTA DE CREDITO SIMPLE - COMERCIO EXTERIOR"},
    {"codigo": "108", "descripcion": "CARTA DE CREDITO DOCUMENTARIO - COMERCIO EXTERIOR"},
]

# ---------------------------------------------------------------------------
# Flujo de Efectivo — clasificación del PCGE para el Estado de Flujos de
# Efectivo, usada para etiquetar cada movimiento de caja/banco.
# ---------------------------------------------------------------------------
FLUJOS_EFECTIVO: List[Dict[str, str]] = [
    {"codigo": "001", "descripcion": "APERTURA"},
    {"codigo": "002", "descripcion": "TRANSFERENCIAS ENTRE CUENTAS PROPIAS"},
    {"codigo": "003", "descripcion": "REPOSICION DE FONDOS FIJOS"},
    {"codigo": "100", "descripcion": "COBRANZA A CLIENTES"},
    {"codigo": "110", "descripcion": "COBRANZA POR REGALIAS Y COMISIONES - GIRO DE NEGOCIO"},
    {"codigo": "120", "descripcion": "COBRANZA DE INTERESES Y DIVIDENDOS - GIRO DE NEGOCIO"},
    {"codigo": "140", "descripcion": "OTROS COBROS RELATIVOS A LA ACTIVIDAD DE OPERACION"},
    {"codigo": "150", "descripcion": "PAGOS A PROVEEDORES"},
    {"codigo": "155", "descripcion": "PAGOS DE HONORARIOS"},
    {"codigo": "160", "descripcion": "PAGOS DE REMUNERACIONES Y BENEFICIOS SOCIALES"},
    {"codigo": "170", "descripcion": "PAGOS DE TRIBUTOS"},
    {"codigo": "180", "descripcion": "PAGOS DE INTERESES Y RENDIMIENTOS - GIRO DE NEGOCIO"},
    {"codigo": "190", "descripcion": "OTROS PAGOS RELATIVOS A LA ACTIVIDAD DE OPERACION"},
    {"codigo": "200", "descripcion": "COBRANZA POR VENTA DE VALORES"},
    {"codigo": "210", "descripcion": "COBRANZA DE CAPITAL DE INVERSIONES PERMANENTES"},
    {"codigo": "211", "descripcion": "COBRANZA DE INTERESES Y RENDIMIENTOS DE INVERSIONES"},
    {"codigo": "220", "descripcion": "COBRANZA POR VENTA DE INMUEBLE, MAQUINARIA Y EQUIPO"},
    {"codigo": "230", "descripcion": "COBRANZA POR VENTA DE INTANGIBLES"},
    {"codigo": "240", "descripcion": "OTROS COBROS RELATIVOS A LA ACTIVIDAD DE INVERSION"},
    {"codigo": "250", "descripcion": "PAGOS POR COMPRA DE VALORES E INVERSIONES PERMANENTES"},
    {"codigo": "260", "descripcion": "PAGOS POR COMPRA DE INMUEBLE, MAQUINARIA Y EQUIPO"},
    {"codigo": "270", "descripcion": "PAGOS POR COMPRA Y DESARROLLO DE ACTIVOS INTANGIBLES"},
    {"codigo": "290", "descripcion": "OTROS PAGOS RELATIVOS A LA ACTIVIDAD DE INVERSION"},
    {"codigo": "300", "descripcion": "COBRANZA POR EMISION DE ACCIONES"},
    {"codigo": "310", "descripcion": "COBRANZA POR NUEVOS APORTES"},
    {"codigo": "320", "descripcion": "COBRANZA DE RECURSOS PROVENIENTES DE TITULOS VALORES"},
    {"codigo": "330", "descripcion": "COBRANZA POR PRESTAMOS OBTENIDOS"},
    {"codigo": "340", "descripcion": "OTROS COBROS RELATIVOS A LA ACTIVIDAD DE FINANCIAMIENTO"},
    {"codigo": "350", "descripcion": "PAGOS DE AMORTIZACION O CANCELACION DE VALORES"},
    {"codigo": "360", "descripcion": "PAGOS DE AMORTIZACION DE CAPITAL DE PRESTAMOS OBTENIDOS"},
    {"codigo": "361", "descripcion": "PAGOS DE AMORTIZACION DE INTERESES DE PRESTAMOS OBTENIDOS"},
    {"codigo": "370", "descripcion": "PAGOS DE DIVIDENDOS Y OTRAS DISTRIBUCIONES"},
    {"codigo": "390", "descripcion": "OTROS PAGOS RELATIVOS A LA ACTIVIDAD DE FINANCIAMIENTO"},
]


def _validar_codigo(catalogo: List[Dict[str, str]], codigo: str, nombre_catalogo: str) -> None:
    """Lanza ValueError si `codigo` no pertenece al catálogo dado."""
    if not any(item["codigo"] == codigo for item in catalogo):
        raise ValueError(f"'{codigo}' no es un código válido de {nombre_catalogo}")


def validar_tipo_documento(codigo: str) -> None:
    _validar_codigo(TIPOS_DOCUMENTO, codigo, "Tipo de Documento")


def validar_medio_pago(codigo: str) -> None:
    _validar_codigo(MEDIOS_PAGO, codigo, "Medio de Pago")


def validar_flujo_efectivo(codigo: str) -> None:
    _validar_codigo(FLUJOS_EFECTIVO, codigo, "Flujo de Efectivo")
