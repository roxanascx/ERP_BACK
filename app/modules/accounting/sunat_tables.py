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

    # TABLA 10: TIPO DE COMPROBANTE DE PAGO O DOCUMENTO
    TIPOS_COMPROBANTES_PAGO = {
        "00": "Otros (especificar)",
        "01": "Factura",
        "02": "Recibo por Honorarios",
        "03": "Boleta de Venta",
        "04": "Liquidación de compra",
        "05": "Boleto de compañía de aviación comercial por el servicio de transporte aéreo de pasajeros",
        "06": "Carta de porte aéreo por el servicio de transporte de carga aérea",
        "07": "Nota de crédito",
        "08": "Nota de débito",
        "09": "Guía de remisión - Remitente",
        "10": "Recibo por Arrendamiento",
        "11": "Póliza emitida por las Bolsas de Valores, Bolsas de Productos o Agentes de Intermediación",
        "12": "Ticket o cinta emitido por máquina registradora",
        "13": "Documento emitido por bancos, instituciones financieras, crediticias y de seguros",
        "14": "Recibo por servicios públicos de suministro de energía eléctrica, agua, teléfono",
        "15": "Boleto emitido por las empresas de transporte público urbano de pasajeros",
        "16": "Boleto de viaje emitido por las empresas de transporte público interprovincial",
        "17": "Documento emitido por la Iglesia Católica por el arrendamiento de bienes inmuebles",
        "18": "Documento emitido por las Administradoras Privadas de Fondo de Pensiones",
        "19": "Boleto o entrada por atracciones y espectáculos públicos",
        "20": "Comprobante de Retención",
        "21": "Conocimiento de embarque por el servicio de transporte de carga marítima",
        "22": "Comprobante por Operaciones No Habituales",
        "23": "Pólizas de Adjudicación emitidas con ocasión del remate o adjudicación de bienes",
        "24": "Certificado de pago de regalías emitidas por PERUPETRO S.A",
        "25": "Documento de Atribución",
        "26": "Recibo por el Pago de la Tarifa por Uso de Agua Superficial con fines agrarios",
        "27": "Seguro Complementario de Trabajo de Riesgo",
        "28": "Tarifa Unificada de Uso de Aeropuerto",
        "29": "Documentos emitidos por la COFOPRI en calidad de oferta de venta de terrenos",
        "30": "Documentos emitidos por las empresas que desempeñan el rol adquiriente",
        "31": "Guía de Remisión - Transportista",
        "32": "Documentos emitidos por las empresas recaudadoras de la Garantía de Red Principal",
        "34": "Documento del Operador",
        "35": "Documento del Partícipe",
        "36": "Recibo de Distribución de Gas Natural",
        "37": "Documentos que emitan los concesionarios del servicio de revisiones técnicas",
        "50": "Declaración Única de Aduanas - Importación definitiva",
        "52": "Despacho Simplificado - Importación Simplificada",
        "53": "Declaración de Mensajería o Courier",
        "54": "Liquidación de Cobranza",
        "87": "Nota de Crédito Especial",
        "88": "Nota de Débito Especial",
        "91": "Comprobante de No Domiciliado",
        "96": "Exceso de crédito fiscal por retiro de bienes",
        "97": "Nota de Crédito - No Domiciliado",
        "98": "Nota de Débito - No Domiciliado",
        "99": "Otros -Consolidado de Boletas de Venta"
    }

    # TABLA 11: CÓDIGO DE LA ADUANA
    CODIGOS_ADUANA = {
        "019": "TUMBES",
        "028": "TALARA",
        "046": "PAITA",
        "055": "CHICLAYO",
        "082": "SALAVERRY",
        "091": "CHIMBOTE",
        "118": "MARÍTIMA DEL CALLAO",
        "127": "PISCO",
        "145": "MOLLENDO MATARANI",
        "154": "AREQUIPA",
        "163": "ILO",
        "172": "TACNA",
        "181": "PUNO",
        "190": "CUZCO",
        "217": "PUCALLPA",
        "226": "IQUITOS",
        "235": "AÉREA DEL CALLAO",
        "244": "POSTAL DE LIMA",
        "262": "DESAGUADERO",
        "271": "TARAPOTO",
        "280": "PUERTO MALDONADO",
        "299": "LA TINA",
        "884": "DEPENDENCIA FERROVIARIA TACNA",
        "893": "DEPENDENCIA POSTAL TACNA",
        "910": "DEPENDENCIA POSTAL AREQUIPA",
        "929": "COMPLEJO FRONTERIZO STA ROSA TACNA",
        "938": "TERMINAL TERRESTRE TACNA",
        "947": "AEROPUERTO TACNA",
        "956": "CETICOS TACNA",
        "965": "DEPENDENCIA POSTAL DE SALAVERRY"
    }

    # TABLA 12: TIPO DE OPERACIÓN
    TIPOS_OPERACION = {
        "01": "VENTA",
        "02": "COMPRA",
        "03": "CONSIGNACIÓN RECIBIDA",
        "04": "CONSIGNACIÓN ENTREGADA",
        "05": "DEVOLUCIÓN RECIBIDA",
        "06": "DEVOLUCIÓN ENTREGADA",
        "07": "PROMOCIÓN",
        "08": "PREMIO",
        "09": "DONACIÓN",
        "10": "SALIDA A PRODUCCIÓN",
        "11": "TRANSFERENCIA ENTRE ALMACENES",
        "12": "RETIRO",
        "13": "MERMAS",
        "14": "DESMEDROS",
        "15": "DESTRUCCIÓN",
        "16": "SALDO INICIAL",
        "99": "OTROS (ESPECIFICAR)"
    }

    # ================================
    # MAPEO DE NOMBRES A TABLAS
    # ================================
    
    _TABLAS_DISPONIBLES = {
        "tipos_medio_pago": TIPOS_MEDIO_PAGO,
        "tipos_documento_identidad": TIPOS_DOCUMENTO_IDENTIDAD,
        "entidades_financieras": ENTIDADES_FINANCIERAS,
        "tipos_moneda": TIPOS_MONEDA,
        "tipos_existencia": TIPOS_EXISTENCIA,
        "unidades_medida": UNIDADES_MEDIDA,
        "tipos_intangible": TIPOS_INTANGIBLE,
        "codigos_libros_registros": CODIGOS_LIBROS_REGISTROS,
        "cuentas_contables": CUENTAS_CONTABLES,
        "tipos_comprobantes_pago": TIPOS_COMPROBANTES_PAGO,
        "codigos_aduana": CODIGOS_ADUANA,
        "tipos_operacion": TIPOS_OPERACION
    }

    # ================================
    # MÉTODOS DE UTILIDAD
    # ================================

    @classmethod
    def obtener_tabla(cls, nombre_tabla: str) -> Optional[Dict[str, str]]:
        """Obtener una tabla por su nombre"""
        return cls._TABLAS_DISPONIBLES.get(nombre_tabla)

    @classmethod
    def listar_tablas(cls) -> List[str]:
        """Obtener lista de todas las tablas disponibles"""
        return list(cls._TABLAS_DISPONIBLES.keys())

    @classmethod
    def obtener_descripcion_codigo(cls, nombre_tabla: str, codigo: str) -> Optional[str]:
        """Obtener la descripción de un código específico"""
        tabla = cls.obtener_tabla(nombre_tabla)
        if tabla:
            return tabla.get(codigo)
        return None

    @classmethod
    def validar_codigo(cls, nombre_tabla: str, codigo: str) -> bool:
        """Validar si un código existe en una tabla"""
        tabla = cls.obtener_tabla(nombre_tabla)
        if tabla:
            return codigo in tabla
        return False

    @classmethod
    def buscar_por_descripcion(cls, nombre_tabla: str, termino: str) -> List[Dict[str, str]]:
        """Buscar códigos por descripción parcial"""
        tabla = cls.obtener_tabla(nombre_tabla)
        if not tabla:
            return []
        
        termino_lower = termino.lower()
        resultados = []
        
        for codigo, descripcion in tabla.items():
            if termino_lower in descripcion.lower():
                resultados.append({
                    "codigo": codigo,
                    "descripcion": descripcion
                })
        
        return resultados

    @classmethod
    def obtener_estadisticas(cls) -> Dict[str, int]:
        """Obtener estadísticas de todas las tablas"""
        estadisticas = {
            "total_tablas": len(cls._TABLAS_DISPONIBLES),
            "total_codigos": 0
        }
        
        for nombre, tabla in cls._TABLAS_DISPONIBLES.items():
            cantidad = len(tabla)
            estadisticas[f"codigos_{nombre}"] = cantidad
            estadisticas["total_codigos"] += cantidad
        
        return estadisticas

    # ================================
    # MÉTODOS ESPECÍFICOS POR TABLA
    # ================================

    @classmethod
    def obtener_descripcion_documento(cls, codigo: str) -> str:
        """Obtener descripción de un tipo de documento de identidad"""
        return cls.TIPOS_DOCUMENTO_IDENTIDAD.get(codigo, f"Código {codigo} no encontrado")

    @classmethod
    def obtener_descripcion_comprobante(cls, codigo: str) -> str:
        """Obtener descripción de un tipo de comprobante de pago"""
        return cls.TIPOS_COMPROBANTES_PAGO.get(codigo, f"Código {codigo} no encontrado")

    @classmethod
    def obtener_descripcion_libro(cls, codigo: str) -> str:
        """Obtener descripción de un código de libro o registro"""
        return cls.CODIGOS_LIBROS_REGISTROS.get(codigo, f"Código {codigo} no encontrado")

    @classmethod
    def obtener_descripcion_moneda(cls, codigo: str) -> str:
        """Obtener descripción de un tipo de moneda"""
        return cls.TIPOS_MONEDA.get(codigo, f"Código {codigo} no encontrado")

    @classmethod
    def validar_codigo_documento(cls, codigo: str) -> bool:
        """Validar código de documento de identidad"""
        return codigo in cls.TIPOS_DOCUMENTO_IDENTIDAD

    @classmethod
    def validar_codigo_comprobante(cls, codigo: str) -> bool:
        """Validar código de comprobante de pago"""
        return codigo in cls.TIPOS_COMPROBANTES_PAGO

    @classmethod
    def validar_codigo_libro(cls, codigo: str) -> bool:
        """Validar código de libro o registro"""
        return codigo in cls.CODIGOS_LIBROS_REGISTROS

    @classmethod
    def validar_codigo_moneda(cls, codigo: str) -> bool:
        """Validar código de moneda"""
        return codigo in cls.TIPOS_MONEDA

    @classmethod
    def listar_todos_documentos(cls) -> List[Dict[str, str]]:
        """Listar todos los tipos de documentos de identidad"""
        return [{"codigo": k, "descripcion": v} for k, v in cls.TIPOS_DOCUMENTO_IDENTIDAD.items()]

    @classmethod
    def listar_todos_comprobantes(cls) -> List[Dict[str, str]]:
        """Listar todos los tipos de comprobantes de pago"""
        return [{"codigo": k, "descripcion": v} for k, v in cls.TIPOS_COMPROBANTES_PAGO.items()]

    @classmethod
    def listar_todos_libros(cls) -> List[Dict[str, str]]:
        """Listar todos los códigos de libros y registros"""
        return [{"codigo": k, "descripcion": v} for k, v in cls.CODIGOS_LIBROS_REGISTROS.items()]

    @classmethod
    def listar_todas_monedas(cls) -> List[Dict[str, str]]:
        """Listar todos los tipos de moneda"""
        return [{"codigo": k, "descripcion": v} for k, v in cls.TIPOS_MONEDA.items()]


# ================================
# ENUMS PARA VALIDACIÓN
# ================================

class TipoDocumentoIdentidad(Enum):
    """Enum para tipos de documento de identidad"""
    OTROS = "0"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"


class TipoComprobantePago(Enum):
    """Enum para tipos de comprobante de pago"""
    OTROS = "00"
    FACTURA = "01"
    RECIBO_HONORARIOS = "02"
    BOLETA_VENTA = "03"
    LIQUIDACION_COMPRA = "04"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"


class TipoMoneda(Enum):
    """Enum para tipos de moneda"""
    SOLES = "1"
    DOLARES = "2"
    OTRA = "9"


class TipoOperacion(Enum):
    """Enum para tipos de operación"""
    VENTA = "01"
    COMPRA = "02"
    CONSIGNACION_RECIBIDA = "03"
    CONSIGNACION_ENTREGADA = "04"
    DEVOLUCION_RECIBIDA = "05"
    DEVOLUCION_ENTREGADA = "06"
    OTROS = "99"
