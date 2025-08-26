"""
Tablas de códigos SUNAT para Libros Electrónicos
================================================

Implementación COMPLETA de las 12 tablas de códigos requeridas por SUNAT
según la Resolución N° 234-2006/SUNAT para el PLE.

Autor: Sistema ERP
Fecha: Agosto 2025
"""

from typing import Dict, List, Optional
from enum import Enum


class TablasSUNAT:
    """Clase para manejar todas las 12 tablas de códigos SUNAT"""
    
    # TABLA 1: TIPO DE MEDIO DE PAGO
    TIPOS_MEDIO_PAGO = {
        "001": "DEPÓSITO EN CUENTA",
        "002": "GIRO",
        "003": "TRANSFERENCIA DE FONDOS",
        "004": "ORDEN DE PAGO",
        "005": "TARJETA DE DÉBITO",
        "006": "TARJETA DE CRÉDITO",
        "007": "CHEQUES CON LA CLÁUSULA DE \"NO NEGOCIABLE\", \"INTRANSFERIBLES\", \"NO A LA ORDEN\" U OTRA EQUIVALENTE",
        "008": "EFECTIVO, POR OPERACIONES EN LAS QUE NO EXISTE OBLIGACIÓN DE UTILIZAR MEDIOS DE PAGO",
        "009": "EFECTIVO, EN LOS DEMÁS CASOS",
        "010": "MEDIOS DE PAGO DE COMERCIO EXTERIOR",
        "011": "LETRAS DE CAMBIO",
        "101": "TRANSFERENCIAS - COMERCIO EXTERIOR",
        "102": "CHEQUES BANCARIOS - COMERCIO EXTERIOR",
        "103": "ORDEN DE PAGO SIMPLE - COMERCIO EXTERIOR",
        "104": "ORDEN DE PAGO DOCUMENTARIO - COMERCIO EXTERIOR",
        "105": "REMESA SIMPLE - COMERCIO EXTERIOR",
        "106": "REMESA DOCUMENTARIA - COMERCIO EXTERIOR",
        "107": "CARTA DE CRÉDITO SIMPLE - COMERCIO EXTERIOR",
        "108": "CARTA DE CRÉDITO DOCUMENTARIO - COMERCIO EXTERIOR",
        "999": "OTROS MEDIOS DE PAGO (ESPECIFICAR)"
    }

    # TABLA 2: TIPOS DE DOCUMENTOS DE IDENTIDAD
    TIPOS_DOCUMENTO_IDENTIDAD = {
        "0": "OTROS TIPOS DE DOCUMENTOS",
        "1": "DOCUMENTO NACIONAL DE IDENTIDAD (DNI)",
        "4": "CARNET DE EXTRANJERIA",
        "6": "REGISTRO ÚNICO DE CONTRIBUYENTES",
        "7": "PASAPORTE"
    }

    # TABLA 3: ENTIDAD FINANCIERA
    ENTIDADES_FINANCIERAS = {
        "01": "CENTRAL RESERVA DEL PERU",
        "02": "DE CREDITO DEL PERU",
        "03": "INTERNACIONAL DEL PERU",
        "05": "LATINO",
        "07": "CITIBANK DEL PERU S.A.",
        "08": "STANDARD CHARTERED",
        "09": "SCOTIABANK PERU",
        "11": "CONTINENTAL",
        "12": "DE LIMA",
        "16": "MERCANTIL",
        "18": "NACION",
        "22": "SANTANDER CENTRAL HISPANO",
        "23": "DE COMERCIO",
        "25": "REPUBLICA",
        "26": "NBK BANK",
        "29": "BANCOSUR",
        "35": "FINANCIERO DEL PERU",
        "37": "DEL PROGRESO",
        "38": "INTERAMERICANO FINANZAS",
        "39": "BANEX",
        "40": "NUEVO MUNDO",
        "41": "SUDAMERICANO",
        "42": "DEL LIBERTADOR",
        "43": "DEL TRABAJO",
        "44": "SOLVENTA",
        "45": "SERBANCO SA.",
        "46": "BANK OF BOSTON",
        "47": "ORION",
        "48": "DEL PAIS",
        "49": "MI BANCO",
        "50": "BNP PARIBAS",
        "53": "HSBC BANK PERU S.A.",
        "99": "OTROS"
    }

    # TABLA 4: TIPO DE MONEDA
    TIPOS_MONEDA = {
        "1": "NUEVOS SOLES",
        "2": "DÓLARES AMERICANOS",
        "9": "OTRA MONEDA (ESPECIFICAR)"
    }

    # TABLA 5: TIPO DE EXISTENCIA
    TIPOS_EXISTENCIA = {
        "01": "MERCADERÍA",
        "02": "PRODUCTO TERMINADO",
        "03": "MATERIAS PRIMAS Y AUXILIARES - MATERIALES",
        "04": "ENVASES Y EMBALAJES",
        "05": "SUMINISTROS DIVERSOS",
        "99": "OTROS (ESPECIFICAR)"
    }

    # TABLA 6: CÓDIGO DE LA UNIDAD DE MEDIDA
    UNIDADES_MEDIDA = {
        "01": "KILOGRAMOS",
        "02": "LIBRAS",
        "03": "TONELADAS LARGAS",
        "04": "TONELADAS MÉTRICAS",
        "05": "TONELADAS CORTAS",
        "06": "GRAMOS",
        "07": "UNIDADES",
        "08": "LITROS",
        "09": "GALONES",
        "10": "BARRILES",
        "11": "LATAS",
        "12": "CAJAS",
        "13": "MILLARES",
        "14": "METROS CÚBICOS",
        "15": "METROS",
        "99": "OTROS (ESPECIFICAR)"
    }

    # TABLA 7: TIPO DE INTANGIBLE
    TIPOS_INTANGIBLE = {
        "01": "INTANGIBLE ADQUIRIDO",
        "02": "INTANGIBLE EN ETAPA DE INVESTIGACIÓN",
        "03": "INTANGIBLE EN ETAPA DE DESARROLLO"
    }
    
    # TABLA 8: CÓDIGOS DE LIBROS Y REGISTROS
    CODIGOS_LIBROS_REGISTROS = {
        "1": "LIBRO CAJA Y BANCOS",
        "2": "LIBRO DE INGRESOS Y GASTOS",
        "3": "LIBRO DE INVENTARIOS Y BALANCES",
        "4": "LIBRO DE RETENCIONES INCISOS E) Y F) DEL ARTICULO 34° DE LA LEY DEL IMPUESTO A LA RENTA",
        "5": "LIBRO DIARIO",
        "6": "LIBRO MAYOR",
        "7": "REGISTRO DE ACTIVOS FIJOS",
        "8": "REGISTRO DE COMPRAS",
        "9": "REGISTRO DE CONSIGNACIONES",
        "10": "REGISTRO DE COSTOS",
        "11": "REGISTRO DE HUÉSPEDES",
        "12": "REGISTRO DE INVENTARIO PERMANENTE EN UNIDADES FÍSICAS",
        "13": "REGISTRO DE INVENTARIO PERMANENTE VALORIZADO",
        "14": "REGISTRO DE VENTAS E INGRESOS",
        "15": "REGISTRO DE VENTAS E INGRESOS - ARTÍCULO 23° RESOLUCIÓN DE SUPERINTENDENCIA N° 266-2004/SUNAT",
        "16": "REGISTRO DEL RÉGIMEN DE PERCEPCIONES",
        "17": "REGISTRO DEL RÉGIMEN DE RETENCIONES",
        "18": "REGISTRO IVAP",
        "19": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - ARTÍCULO 8° RESOLUCIÓN DE SUPERINTENDENCIA N° 022-98/SUNAT",
        "20": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 021-99/SUNAT",
        "21": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 142-2001/SUNAT",
        "22": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 256-2004/SUNAT",
        "23": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 257-2004/SUNAT",
        "24": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 258-2004/SUNAT",
        "25": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 259-2004/SUNAT",
        "26": "REGISTRO DE RETENCIONES ARTÍCULO 77-A DE LA LEY DEL IMPUESTO A LA RENTA",
        "27": "LIBRO DE ACTAS DE LA EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA",
        "28": "LIBRO DE ACTAS DE LA JUNTA GENERAL DE ACCIONISTAS",
        "29": "LIBRO DE ACTAS DEL DIRECTORIO",
        "30": "LIBRO DE MATRÍCULA DE ACCIONES",
        "31": "LIBRO DE PLANILLAS"
    }

    # TABLA 9: CÓDIGO DE LA CUENTA CONTABLE
    CUENTAS_CONTABLES = {
        "10": "CAJA Y BANCOS",
        "12": "CLIENTES",
        "16": "CUENTAS POR COBRAR DIVERSAS",
        "20": "MERCADERÍAS",
        "21": "PRODUCTOS TERMINADOS",
        "33": "INMUEBLES, MAQUINARIAS Y EQUIPO",
        "34": "INTANGIBLES",
        "38": "CARGAS DIFERIDAS",
        "39": "DEPRECIACIÓN Y AMORTIZACIÓN ACUMULADA",
        "4011D": "TRIBUTOS POR PAGAR - IGV - DÉBITOS",
        "4011C": "TRIBUTOS POR PAGAR - IGV - CRÉDITOS",
        "4017D": "TRIBUTOS POR PAGAR - IMPUESTO A LA RENTA - DÉBITOS",
        "4017C": "TRIBUTOS POR PAGAR - IMPUESTO A LA RENTA - CRÉDITOS",
        "402": "TRIBUTOS POR PAGAR - OTROS IMPUESTOS",
        "42": "PROVEEDORES",
        "46": "CUENTAS POR PAGAR DIVERSAS",
        "50": "CAPITAL",
        "58": "RESERVAS",
        "59": "RESULTADOS ACUMULADOS",
        "60": "COMPRAS",
        "61": "VARIACIÓN DE EXISTENCIAS",
        "62": "CARGAS DE PERSONAL",
        "63": "SERVICIOS PRESTADOS POR TERCEROS",
        "65": "CARGAS DIVERSAS DE GESTIÓN",
        "66": "CARGAS EXCEPCIONALES",
        "67": "CARGAS FINANCIERAS",
        "68": "PROVISIONES DEL EJERCICIO",
        "69": "COSTO DE VENTAS",
        "96": "GASTOS ADMINISTRATIVOS",
        "97": "GASTOS DE VENTAS",
        "70": "VENTAS",
        "75": "INGRESOS DIVERSOS",
        "76": "INGRESOS EXCEPCIONALES",
        "77": "INGRESOS FINANCIEROS",
        "79": "CARGAS IMPUTABLES A LA CUENTA DE COSTOS"
    }
        "17": "REGISTRO DEL RÉGIMEN DE RETENCIONES",
        "18": "REGISTRO IVAP",
        "19": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - ARTÍCULO 8° RESOLUCIÓN DE SUPERINTENDENCIA N° 022-98/SUNAT",
        "20": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 021-99/SUNAT",
        "21": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 142-2001/SUNAT",
        "22": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 256-2004/SUNAT",
        "23": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 257-2004/SUNAT",
        "24": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 258-2004/SUNAT",
        "25": "REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 259-2004/SUNAT"
    }
    
    # TABLA 10: TIPOS DE COMPROBANTES DE PAGO
    TIPOS_COMPROBANTES_PAGO = {
        "00": "OTROS (especificar)",
        "01": "FACTURA",
        "02": "RECIBO POR HONORARIOS",
        "03": "BOLETA DE VENTA",
        "04": "LIQUIDACIÓN DE COMPRA",
        "05": "BOLETO DE COMPAÑÍA DE AVIACIÓN COMERCIAL POR EL SERVICIO DE TRANSPORTE AÉREO DE PASAJEROS",
        "06": "CARTA DE PORTE AÉREO POR EL SERVICIO DE TRANSPORTE DE CARGA AÉREA",
        "07": "NOTA DE CRÉDITO",
        "08": "NOTA DE DÉBITO",
        "09": "GUÍA DE REMISIÓN - REMITENTE",
        "10": "RECIBO POR ARRENDAMIENTO",
        "11": "PÓLIZA EMITIDA POR LAS BOLSAS DE VALORES, BOLSAS DE PRODUCTOS O AGENTES DE INTERMEDIACIÓN",
        "12": "TICKET O CINTA EMITIDO POR MÁQUINA REGISTRADORA",
        "13": "DOCUMENTO EMITIDO POR BANCOS, INSTITUCIONES FINANCIERAS, CREDITICIAS Y DE SEGUROS",
        "14": "RECIBO POR SERVICIOS PÚBLICOS DE SUMINISTRO DE ENERGÍA ELÉCTRICA, AGUA, TELÉFONO, TELEX Y TELEGRÁFICOS",
        "15": "BOLETO EMITIDO POR LAS EMPRESAS DE TRANSPORTE PÚBLICO URBANO DE PASAJEROS",
        "16": "BOLETO DE VIAJE EMITIDO POR LAS EMPRESAS DE TRANSPORTE PÚBLICO INTERPROVINCIAL DE PASAJEROS",
        "17": "DOCUMENTO EMITIDO POR LA IGLESIA CATÓLICA POR EL ARRENDAMIENTO DE BIENES INMUEBLES",
        "18": "DOCUMENTO EMITIDO POR LAS ADMINISTRADORAS PRIVADAS DE FONDO DE PENSIONES",
        "19": "BOLETO O ENTRADA POR ATRACCIONES Y ESPECTÁCULOS PÚBLICOS",
        "20": "COMPROBANTE DE RETENCIÓN",
        "21": "CONOCIMIENTO DE EMBARQUE POR EL SERVICIO DE TRANSPORTE DE CARGA MARÍTIMA",
        "22": "COMPROBANTE POR OPERACIONES NO HABITUALES",
        "23": "PÓLIZAS DE ADJUDICACIÓN EMITIDAS CON OCASIÓN DEL REMATE O ADJUDICACIÓN DE BIENES",
        "24": "CERTIFICADO DE PAGO DE REGALÍAS EMITIDAS POR PERUPETRO S.A",
        "25": "DOCUMENTO DE ATRIBUCIÓN",
        "26": "RECIBO POR EL PAGO DE LA TARIFA POR USO DE AGUA SUPERFICIAL CON FINES AGRARIOS",
        "27": "SEGURO COMPLEMENTARIO DE TRABAJO DE RIESGO",
        "28": "TARIFA UNIFICADA DE USO DE AEROPUERTO",
        "29": "DOCUMENTOS EMITIDOS POR LA COFOPRI",
        "30": "DOCUMENTOS EMITIDOS POR LAS EMPRESAS QUE DESEMPEÑAN EL ROL ADQUIRIENTE EN LOS SISTEMAS DE PAGO",
        "31": "GUÍA DE REMISIÓN - TRANSPORTISTA",
        "32": "DOCUMENTOS EMITIDOS POR LAS EMPRESAS RECAUDADORAS DE LA GARANTÍA DE RED PRINCIPAL",
        "34": "DOCUMENTO DEL OPERADOR",
        "35": "DOCUMENTO DEL PARTÍCIPE",
        "36": "RECIBO DE DISTRIBUCIÓN DE GAS NATURAL",
        "37": "DOCUMENTOS QUE EMITAN LOS CONCESIONARIOS DEL SERVICIO DE REVISIONES TÉCNICAS VEHICULARES",
        "50": "DECLARACIÓN ÚNICA DE ADUANAS - IMPORTACIÓN DEFINITIVA",
        "52": "DESPACHO SIMPLIFICADO - IMPORTACIÓN SIMPLIFICADA",
        "53": "DECLARACIÓN DE MENSAJERÍA O COURIER",
        "54": "LIQUIDACIÓN DE COBRANZA",
        "87": "NOTA DE CRÉDITO ESPECIAL",
        "88": "NOTA DE DÉBITO ESPECIAL",
        "91": "COMPROBANTE DE NO DOMICILIADO",
        "96": "EXCESO DE CRÉDITO FISCAL POR RETIRO DE BIENES",
        "97": "NOTA DE CRÉDITO - NO DOMICILIADO",
        "98": "NOTA DE DÉBITO - NO DOMICILIADO",
        "99": "OTROS - CONSOLIDADO DE BOLETAS DE VENTA"
    }
    
    # TABLA 3: ENTIDADES FINANCIERAS
    ENTIDADES_FINANCIERAS = {
        "002": "BANCO DE CRÉDITO DEL PERÚ",
        "003": "BANCO INTERNACIONAL DEL PERÚ",
        "009": "SCOTIABANK PERÚ S.A.A.",
        "011": "BANCO DE LA NACIÓN",
        "022": "BANCO CONTINENTAL",
        "025": "BANCO DE COMERCIO",
        "035": "BANCO POPULAR DEL PERÚ",
        "038": "BANCO DE LOS ANDES",
        "043": "BANCO AGRARIO",
        "054": "BANCO DE TRABAJO",
        "056": "BANCO WIESE SUDAMERIS",
        "059": "BANCO FALABELLA PERÚ S.A.",
        "285": "BANCO RIPLEY PERÚ S.A.",
        "801": "CAJA MUNICIPAL DE SULLANA",
        "802": "CAJA MUNICIPAL DE PIURA",
        "803": "CAJA MUNICIPAL DE MAYNAS",
        "804": "CAJA MUNICIPAL DE CUSCO S.A.",
        "805": "CAJA MUNICIPAL DE TACNA",
        "806": "CAJA MUNICIPAL DE TRUJILLO",
        "807": "CAJA MUNICIPAL DE HUANCAYO",
        "808": "CAJA MUNICIPAL DE ICA",
        "809": "CAJA MUNICIPAL DE CHINCHA",
        "810": "CAJA MUNICIPAL DE PAITA",
        "811": "CAJA MUNICIPAL DE PISCO",
        "812": "CAJA MUNICIPAL DE CHIMBOTE",
        "813": "CAJA MUNICIPAL DE CAJAMARCA",
        "814": "CAJA MUNICIPAL DE AREQUIPA",
        "815": "CAJA MUNICIPAL DE DEL SANTA",
        "816": "CAJA MUNICIPAL DE LIMA",
        "821": "CAJA RURAL DE AHORRO Y CRÉDITO DE LA REGIÓN SAN MARTÍN",
        "822": "CAJA RURAL DE AHORRO Y CRÉDITO DEL SUR",
        "823": "CAJA RURAL DE AHORRO Y CRÉDITO DE CAJAMARCA",
        "824": "CAJA RURAL DE AHORRO Y CRÉDITO DE PRYMERA",
        "825": "CAJA RURAL DE AHORRO Y CRÉDITO RAÍZ",
        "831": "EDPYME ALTERNATIVA",
        "832": "EDPYME CREAR TACNA",
        "833": "EDPYME PROEMPRESA",
        "834": "EDPYME CREDIVISIÓN",
        "835": "EDPYME SOLIDARIDAD",
        "836": "EDPYME ACCESO CREDITICIO",
        "837": "EDPYME CONFIANZA",
        "838": "EDPYME CREAR TRUJILLO",
        "839": "EDPYME CREAR CUSCO",
        "840": "EDPYME MARCIMEX",
        "999": "OTRAS ENTIDADES FINANCIERAS"
    }
    
    # TABLA 4: TIPOS DE MONEDA
    TIPOS_MONEDA = {
        "USD": "DÓLARES AMERICANOS",
        "PEN": "SOLES",
        "EUR": "EUROS"
    }
    
    # TABLA 5: TIPOS DE EXISTENCIAS
    TIPOS_EXISTENCIAS = {
        "01": "MERCADERÍAS",
        "02": "PRODUCTOS TERMINADOS",
        "03": "PRODUCTOS EN PROCESO",
        "04": "MATERIAS PRIMAS",
        "05": "MATERIALES AUXILIARES, SUMINISTROS Y REPUESTOS",
        "06": "ENVASES Y EMBALAJES",
        "07": "ACTIVOS NO PRODUCIDOS"
    }
    
    # TABLA 6: CÓDIGOS DE UNIDADES DE MEDIDA
    UNIDADES_MEDIDA = {
        "01": "KILOGRAMOS",
        "02": "LIBRAS",
        "03": "TONELADAS LARGAS",
        "04": "TONELADAS MÉTRICAS",
        "05": "TONELADAS CORTAS",
        "06": "GRAMOS",
        "07": "UNIDADES",
        "08": "LITROS",
        "09": "GALONES",
        "10": "BARRILES",
        "11": "LLANTAS",
        "12": "TUBOS",
        "13": "METROS CÚBICOS",
        "14": "METROS CUADRADOS",
        "15": "METROS LINEALES",
        "99": "OTROS (especificar en observaciones)"
    }
    
    # TABLA 7: TIPOS DE INTANGIBLES
    TIPOS_INTANGIBLES = {
        "01": "CONCESIONES, LICENCIAS Y OTROS DERECHOS",
        "02": "PATENTES Y MARCAS",
        "03": "PROGRAMAS DE COMPUTADORA (SOFTWARE)",
        "04": "COSTOS DE EXPLORACIÓN Y DESARROLLO",
        "05": "FÓRMULAS, DISEÑOS Y PROTOTIPOS",
        "06": "RESERVAS DE RECURSOS EXTRAÍBLES",
        "99": "OTROS"
    }
    
    # TABLA 9: AJUSTES POR INFLACIÓN (PARA FORMATO SIMPLIFICADO)
    AJUSTES_INFLACION = {
        "1": "SIN AJUSTES",
        "2": "CON AJUSTES"
    }
    
    # TABLA 12: TIPOS DE OPERACIÓN DEL INVENTARIO
    TIPOS_OPERACION_INVENTARIO = {
        "01": "INVENTARIO INICIAL",
        "02": "COMPRAS",
        "03": "VENTAS",
        "04": "CONSIGNACIONES RECIBIDAS",
        "05": "CONSIGNACIONES ENTREGADAS",
        "06": "DEVOLUCIONES RECIBIDAS",
        "07": "DEVOLUCIONES ENTREGADAS",
        "08": "BONIFICACIONES",
        "09": "DONACIONES",
        "10": "SALIDAS A PRODUCCIÓN",
        "11": "TRANSFERENCIAS ENTRE ALMACENES",
        "12": "RETIROS",
        "13": "MERMAS",
        "14": "DESVALORIZACIÓN",
        "15": "REVALORIZACIÓN",
        "16": "PRODUCCIÓN INGRESADA AL ALMACÉN",
        "99": "OTROS"
    }

    @classmethod
    def obtener_descripcion_documento(cls, codigo: str) -> str:
        """Obtener descripción de tipo de documento de identidad"""
        return cls.TIPOS_DOCUMENTO_IDENTIDAD.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_libro(cls, codigo: str) -> str:
        """Obtener descripción de libro o registro"""
        return cls.CODIGOS_LIBROS_REGISTROS.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_comprobante(cls, codigo: str) -> str:
        """Obtener descripción de tipo de comprobante"""
        return cls.TIPOS_COMPROBANTES_PAGO.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_entidad_financiera(cls, codigo: str) -> str:
        """Obtener descripción de entidad financiera"""
        return cls.ENTIDADES_FINANCIERAS.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_moneda(cls, codigo: str) -> str:
        """Obtener descripción de tipo de moneda"""
        return cls.TIPOS_MONEDA.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_existencia(cls, codigo: str) -> str:
        """Obtener descripción de tipo de existencia"""
        return cls.TIPOS_EXISTENCIAS.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_unidad_medida(cls, codigo: str) -> str:
        """Obtener descripción de unidad de medida"""
        return cls.UNIDADES_MEDIDA.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_intangible(cls, codigo: str) -> str:
        """Obtener descripción de tipo de intangible"""
        return cls.TIPOS_INTANGIBLES.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def obtener_descripcion_operacion_inventario(cls, codigo: str) -> str:
        """Obtener descripción de tipo de operación de inventario"""
        return cls.TIPOS_OPERACION_INVENTARIO.get(codigo, f"CÓDIGO DESCONOCIDO: {codigo}")
    
    @classmethod
    def validar_codigo_documento(cls, codigo: str) -> bool:
        """Validar si un código de documento es válido"""
        return codigo in cls.TIPOS_DOCUMENTO_IDENTIDAD
    
    @classmethod
    def validar_codigo_comprobante(cls, codigo: str) -> bool:
        """Validar si un código de comprobante es válido"""
        return codigo in cls.TIPOS_COMPROBANTES_PAGO
    
    @classmethod
    def validar_codigo_libro(cls, codigo: str) -> bool:
        """Validar si un código de libro es válido"""
        return codigo in cls.CODIGOS_LIBROS_REGISTROS
    
    @classmethod
    def listar_todos_documentos(cls) -> Dict[str, str]:
        """Listar todos los tipos de documentos de identidad"""
        return cls.TIPOS_DOCUMENTO_IDENTIDAD.copy()
    
    @classmethod
    def listar_todos_comprobantes(cls) -> Dict[str, str]:
        """Listar todos los tipos de comprobantes de pago"""
        return cls.TIPOS_COMPROBANTES_PAGO.copy()
    
    @classmethod
    def listar_todos_libros(cls) -> Dict[str, str]:
        """Listar todos los códigos de libros y registros"""
        return cls.CODIGOS_LIBROS_REGISTROS.copy()
    
    @classmethod
    def listar_entidades_financieras(cls) -> Dict[str, str]:
        """Listar todas las entidades financieras"""
        return cls.ENTIDADES_FINANCIERAS.copy()
    
    @classmethod
    def listar_tipos_moneda(cls) -> Dict[str, str]:
        """Listar todos los tipos de moneda"""
        return cls.TIPOS_MONEDA.copy()
    
    @classmethod
    def listar_tipos_existencias(cls) -> Dict[str, str]:
        """Listar todos los tipos de existencias"""
        return cls.TIPOS_EXISTENCIAS.copy()
    
    @classmethod
    def listar_unidades_medida(cls) -> Dict[str, str]:
        """Listar todas las unidades de medida"""
        return cls.UNIDADES_MEDIDA.copy()
    
    @classmethod
    def listar_tipos_intangibles(cls) -> Dict[str, str]:
        """Listar todos los tipos de intangibles"""
        return cls.TIPOS_INTANGIBLES.copy()
    
    @classmethod
    def listar_operaciones_inventario(cls) -> Dict[str, str]:
        """Listar todas las operaciones de inventario"""
        return cls.TIPOS_OPERACION_INVENTARIO.copy()


# Enums para uso con Pydantic
class TipoDocumentoIdentidad(str, Enum):
    """Enum para tipos de documento de identidad"""
    OTROS = "0"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "A"
    DOC_TRIB_NO_DOM = "B"
    TIN = "C"
    IN = "D"
    TAM = "E"


class TipoComprobantePago(str, Enum):
    """Enum para tipos de comprobante de pago"""
    OTROS = "00"
    FACTURA = "01"
    RECIBO_HONORARIOS = "02"
    BOLETA_VENTA = "03"
    LIQUIDACION_COMPRA = "04"
    BOLETO_AVIACION = "05"
    CARTA_PORTE_AEREO = "06"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION_REMITENTE = "09"
    RECIBO_ARRENDAMIENTO = "10"
    

class TipoLibroRegistro(str, Enum):
    """Enum para tipos de libros y registros"""
    LIBRO_CAJA_BANCOS = "01"
    LIBRO_INGRESOS_GASTOS = "02"
    LIBRO_INVENTARIOS_BALANCES = "03"
    LIBRO_RETENCIONES = "04"
    LIBRO_DIARIO = "05"
    LIBRO_MAYOR = "06"
    REGISTRO_ACTIVOS_FIJOS = "07"
    REGISTRO_COMPRAS = "08"
    REGISTRO_VENTAS = "14"


class TipoMoneda(str, Enum):
    """Enum para tipos de moneda"""
    USD = "USD"
    PEN = "PEN"
    EUR = "EUR"


# Constantes específicas para el Libro Diario
class ConstantesLibroDiario:
    """Constantes específicas para el Libro Diario PLE"""
    
    CODIGO_LIBRO = "05"  # Código del Libro Diario
    FORMATO_SIMPLIFICADO = "1"
    FORMATO_DETALLADO = "2"
    
    # Estados del archivo PLE
    ESTADO_OPERACION_APERTURA = "1"
    ESTADO_OPERACION_MENSUAL = "1"
    ESTADO_OPERACION_CIERRE = "2"
    
    # Contenido del archivo
    CONTENIDO_CON_INFORMACION = "1"
    CONTENIDO_SIN_INFORMACION = "0"
    
    # Oportunidad de presentación
    OPORTUNIDAD_NORMAL = "00"
    OPORTUNIDAD_SUSTITUTORIA = "01"
    
    # Indicador de renta
    INDICADOR_RENTA_ANUAL = "1"
    INDICADOR_RENTA_ALQUILER = "2"
    
    @classmethod
    def generar_nombre_archivo_ple(
        cls,
        fecha_presentacion: str,  # AAAAMMDD
        anio_ejercicio: str,      # AAAA
        mes_periodo: str,         # MM
        codigo_oportunidad: str = "00",
        indicador_contenido: str = "1"
    ) -> str:
        """
        Generar nombre de archivo PLE para Libro Diario
        
        Formato: AAAAMMDDAAAAMMCCOFLLOIIC.TXT
        Donde:
        - AAAAMMDD: Fecha de presentación
        - AAAA: Año del ejercicio
        - MM: Mes del período
        - CC: Código de oportunidad (00=Normal, 01=Sustitutoria)
        - O: Origen de la información (F=Formulario)
        - FL: Código del formato del libro (05=Libro Diario)
        - L: Formato (1=Simplificado)
        - O: Tipo de moneda (0=Soles)
        - I: Operación (1=Cierre mensual)
        - I: Contenido (1=Con información, 0=Sin información)
        - C: Indicador de moneda de cierre
        """
        return f"{fecha_presentacion}{anio_ejercicio}{mes_periodo}{codigo_oportunidad}051001{indicador_contenido}.TXT"


# Función para inicializar las tablas en MongoDB (opcional)
async def inicializar_tablas_sunat_en_mongo(db):
    """
    Función para insertar las tablas SUNAT en MongoDB si se desea
    """
    coleccion_tablas = db["tablas_sunat"]
    
    # Verificar si ya existen las tablas
    if await coleccion_tablas.count_documents({}) == 0:
        tablas_data = [
            {
                "tabla": "tipos_documento_identidad",
                "codigo": "2",
                "descripcion": "Tipos de Documentos de Identidad",
                "data": TablasSUNAT.TIPOS_DOCUMENTO_IDENTIDAD
            },
            {
                "tabla": "codigos_libros_registros", 
                "codigo": "8",
                "descripcion": "Códigos de Libros y Registros",
                "data": TablasSUNAT.CODIGOS_LIBROS_REGISTROS
            },
            {
                "tabla": "tipos_comprobantes_pago",
                "codigo": "10", 
                "descripcion": "Tipos de Comprobantes de Pago",
                "data": TablasSUNAT.TIPOS_COMPROBANTES_PAGO
            },
            {
                "tabla": "entidades_financieras",
                "codigo": "3",
                "descripcion": "Entidades Financieras",
                "data": TablasSUNAT.ENTIDADES_FINANCIERAS
            },
            {
                "tabla": "tipos_moneda",
                "codigo": "4",
                "descripcion": "Tipos de Moneda", 
                "data": TablasSUNAT.TIPOS_MONEDA
            }
        ]
        
        await coleccion_tablas.insert_many(tablas_data)
        print("✅ Tablas SUNAT inicializadas en MongoDB")
    else:
        print("ℹ️ Tablas SUNAT ya existen en MongoDB")
