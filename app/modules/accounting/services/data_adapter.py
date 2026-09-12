"""
Data Adapter para mapear asientos contables reales a esquemas PLE
Autor: Sistema ERP
Fecha: 2025-08-27
Propósito: Adaptador que convierte datos reales de MongoDB a esquemas PLE Libro Mayor
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from bson import ObjectId

from ..schemas.schemas_mayor import (
    LibroMayorPLE,
    TipoDocumentoIdentidad,
    TipoComprobantePago,
    EstadoOperacion,
    TipoCuentaContable
)


class DataAdapterMayor:
    """
    Adaptador para convertir asientos contables reales a esquemas Libro Mayor PLE
    """
    
    def __init__(self):
        """Inicializar el adaptador con mapeos predefinidos"""
        self._init_mapeos()
    
    def _init_mapeos(self):
        """Inicializar mapeos de códigos SUNAT"""
        # Mapeo de libros contables a códigos SUNAT
        self.mapeo_libros = {
            "5.1": "050100",  # Libro Diario
            "5.2": "050200",  # Libro Mayor
            "8.1": "080100",  # Registro de Compras
            "14.1": "140100"  # Registro de Ventas
        }
        
        # Mapeo de tipos de cuenta por código (primeros dígitos)
        self.mapeo_tipos_cuenta = {
            "1": TipoCuentaContable.ACTIVO,
            "2": TipoCuentaContable.PASIVO,
            "3": TipoCuentaContable.PATRIMONIO,
            "4": TipoCuentaContable.INGRESOS,
            "5": TipoCuentaContable.GASTOS,
            "6": TipoCuentaContable.COSTOS,
            "7": TipoCuentaContable.CUENTAS_CONTINGENTES,
            "8": TipoCuentaContable.CUENTAS_ORDEN,
            "9": TipoCuentaContable.CUENTAS_ANALITICAS
        }
    
    def convertir_asiento_a_libro_mayor(
        self, 
        asiento: Dict[str, Any], 
        empresa_ruc: str,
        periodo: str
    ) -> LibroMayorPLE:
        """
        Convierte un asiento contable real a esquema Libro Mayor PLE
        
        Args:
            asiento: Documento de asiento contable de MongoDB
            empresa_ruc: RUC de la empresa
            periodo: Periodo en formato YYYYMM00
            
        Returns:
            LibroMayorPLE: Objeto validado según esquema SUNAT
        """
        try:
            # Extraer datos del asiento
            fecha_str = asiento.get('fecha', '')
            fecha_obj = self._parsear_fecha(fecha_str)
            
            # Extraer cuenta contable
            cuenta_info = asiento.get('cuentaContable', {})
            codigo_cuenta = cuenta_info.get('codigo', '')
            denominacion_cuenta = cuenta_info.get('denominacion', '')
            
            # Determinar tipo de cuenta
            tipo_cuenta = self._determinar_tipo_cuenta(codigo_cuenta)
            
            # Obtener código de libro
            codigo_libro_original = asiento.get('codigoLibro', '5.2')
            codigo_libro_sunat = self.mapeo_libros.get(codigo_libro_original, '050200')
            
            # Calcular saldo final (debe - haber)
            debe = Decimal(str(asiento.get('debe', 0.0)))
            haber = Decimal(str(asiento.get('haber', 0.0)))
            saldo_final = debe - haber
            
            # Crear objeto Libro Mayor PLE
            libro_mayor = LibroMayorPLE(
                periodo=periodo,
                codigo_unico_operacion=self._generar_cuo(asiento),
                numero_correlativo=asiento.get('numeroCorrelativo', '0001'),
                codigo_cuenta_contable=codigo_cuenta,
                codigo_unidad_operacion='',  # No disponible en datos actuales
                codigo_centro_costos=(asiento.get('centroCosto') or {}).get('codigo', ''),
                tipo_moneda='PEN',           # Asumimos soles por defecto
                tipo_documento_identidad=TipoDocumentoIdentidad.RUC,
                numero_documento_identidad=empresa_ruc,
                tipo_comprobante_pago=TipoComprobantePago.OTROS,  # Por defecto
                numero_serie_comprobante='',
                numero_comprobante_pago=asiento.get('numeroDocumento', ''),
                fecha_contable=fecha_obj,
                fecha_vencimiento=fecha_obj,  # Misma fecha por defecto
                fecha_operacion=fecha_obj,   # Misma fecha por defecto
                glosa_descripcion=asiento.get('glosa', ''),
                glosa_referencial='',
                movimiento_debe=debe,
                movimiento_haber=haber,
                saldo_deudor=saldo_final if saldo_final > 0 else Decimal('0.00'),
                saldo_acreedor=abs(saldo_final) if saldo_final < 0 else Decimal('0.00'),
                datos_estructura='1',  # Contenido del Libro Mayor
                estado_operacion=EstadoOperacion.ANOTACION_VIGENTE
            )
            
            return libro_mayor
            
        except Exception as e:
            raise ValueError(f"Error al convertir asiento a Libro Mayor: {str(e)}")
    
    def _parsear_fecha(self, fecha_str: str) -> date:
        """Parsea string de fecha a objeto date"""
        try:
            if isinstance(fecha_str, str):
                # Formato esperado: YYYY-MM-DD
                return datetime.strptime(fecha_str, '%Y-%m-%d').date()
            elif isinstance(fecha_str, datetime):
                return fecha_str.date()
            else:
                return date.today()
        except:
            return date.today()
    
    def _determinar_tipo_cuenta(self, codigo_cuenta: str) -> TipoCuentaContable:
        """Determina el tipo de cuenta basado en el código"""
        if not codigo_cuenta:
            return TipoCuentaContable.ACTIVO
        
        primer_digito = codigo_cuenta[0]
        return self.mapeo_tipos_cuenta.get(primer_digito, TipoCuentaContable.ACTIVO)
    
    def _generar_cuo(self, asiento: Dict[str, Any]) -> str:
        """Genera Código Único de Operación"""
        # Usar combinación de fecha + número correlativo + ObjectId parcial
        fecha = asiento.get('fecha', '2025-08-27').replace('-', '')
        correlativo = asiento.get('numeroCorrelativo', '0001').replace('-', '')
        
        # Tomar los últimos 6 caracteres del ObjectId como identificador único
        object_id = str(asiento.get('_id', ObjectId()))
        id_suffix = object_id[-6:]
        
        return f"{fecha}{correlativo}{id_suffix}"
    
    def convertir_lista_asientos(
        self, 
        asientos: List[Dict[str, Any]], 
        empresa_ruc: str,
        periodo: str
    ) -> List[LibroMayorPLE]:
        """
        Convierte una lista de asientos contables a lista de Libro Mayor PLE
        
        Args:
            asientos: Lista de documentos de asientos contables
            empresa_ruc: RUC de la empresa
            periodo: Periodo en formato YYYYMM00
            
        Returns:
            List[LibroMayorPLE]: Lista de objetos validados
        """
        resultados = []
        errores = []
        
        for i, asiento in enumerate(asientos):
            try:
                libro_mayor = self.convertir_asiento_a_libro_mayor(asiento, empresa_ruc, periodo)
                resultados.append(libro_mayor)
            except Exception as e:
                errores.append(f"Error en asiento {i+1}: {str(e)}")
        
        if errores:
            print(f"⚠️  Se encontraron {len(errores)} errores durante la conversión:")
            for error in errores:
                print(f"   - {error}")
        
        return resultados
    
    def validar_compatibilidad(self, asientos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valida la compatibilidad de los datos reales con el esquema PLE
        
        Args:
            asientos: Lista de asientos contables
            
        Returns:
            Dict con resultado de validación
        """
        reporte = {
            'total_asientos': len(asientos),
            'campos_requeridos_presentes': 0,
            'campos_opcionales_presentes': 0,
            'errores': [],
            'advertencias': [],
            'compatibilidad': 0.0
        }
        
        campos_requeridos = [
            'fecha', 'cuentaContable', 'debe', 'haber', 
            'numeroCorrelativo', 'glosa'
        ]
        
        campos_opcionales = [
            'numeroDocumento', 'codigoLibro', 'empresaId'
        ]
        
        if not asientos:
            reporte['errores'].append("No hay asientos para validar")
            return reporte
        
        # Validar cada asiento
        for i, asiento in enumerate(asientos):
            # Campos requeridos
            for campo in campos_requeridos:
                if campo in asiento and asiento[campo] is not None:
                    reporte['campos_requeridos_presentes'] += 1
                else:
                    reporte['errores'].append(f"Asiento {i+1}: falta campo '{campo}'")
            
            # Campos opcionales
            for campo in campos_opcionales:
                if campo in asiento and asiento[campo] is not None:
                    reporte['campos_opcionales_presentes'] += 1
            
            # Validaciones específicas
            cuenta = asiento.get('cuentaContable', {})
            if not isinstance(cuenta, dict) or 'codigo' not in cuenta:
                reporte['errores'].append(f"Asiento {i+1}: estructura de cuenta contable inválida")
        
        # Calcular compatibilidad
        total_campos_esperados = len(asientos) * len(campos_requeridos)
        if total_campos_esperados > 0:
            reporte['compatibilidad'] = (reporte['campos_requeridos_presentes'] / total_campos_esperados) * 100
        
        return reporte
