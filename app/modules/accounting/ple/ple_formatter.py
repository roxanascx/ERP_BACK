"""
PLEFormatter - Formateador de Datos para PLE
===========================================

Formateo específico de datos contables para cumplir con las
especificaciones exactas del formato PLE de SUNAT.

Funcionalidades principales:
- Formateo de fechas a DD/MM/AAAA
- Formateo de montos con 2 decimales
- Escape de caracteres especiales
- Validación de longitudes de campo
- Formateo de códigos según normativa SUNAT

Especificaciones técnicas:
- Separador de campos: |
- Codificación: UTF-8
- Formato de números: #.##
- Formato de fechas: DD/MM/AAAA

Autor: Sistema ERP
Fecha: Agosto 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FormatValidationResult:
    """Resultado de validación de formateo"""
    valido: bool
    errores: List[str]
    warnings: List[str]
    campo_formateado: Optional[str]
    longitud_final: int


@dataclass
class PLELineFormat:
    """Estructura de una línea formateada para PLE"""
    periodo: str
    numero_correlativo: str
    codigo_cuenta: str
    codigo_cuenta_desagregada: str
    fecha_operacion: str
    glosa: str
    movimiento_debe: str
    movimiento_haber: str
    dato_estructurado: str
    
    def to_line(self) -> str:
        """Convertir a línea de texto separada por |"""
        return "|".join([
            self.periodo,
            self.numero_correlativo,
            self.codigo_cuenta,
            self.codigo_cuenta_desagregada,
            self.fecha_operacion,
            self.glosa,
            self.movimiento_debe,
            self.movimiento_haber,
            self.dato_estructurado
        ])


class PLEFormatter:
    """
    Formateador específico de datos para archivos PLE.
    
    Maneja todos los aspectos de formateo requeridos por SUNAT:
    - Fechas, montos, códigos y texto
    - Validación de longitudes
    - Escape de caracteres especiales
    - Precisión numérica
    """
    
    # Constantes de formateo según normativa SUNAT
    SEPARADOR_CAMPOS = "|"
    PRECISION_MONTOS = 2
    FORMATO_FECHA_PLE = "%d/%m/%Y"
    FORMATO_PERIODO = "%Y%m%d"
    
    # Longitudes máximas de campos
    MAX_LONGITUD_CORRELATIVO = 40
    MAX_LONGITUD_CUENTA = 24
    MAX_LONGITUD_GLOSA = 200
    MAX_LONGITUD_DATO_ESTRUCTURADO = 500
    
    def __init__(self):
        """Inicializar el formateador"""
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # FORMATEO DE FECHAS
    # ================================
    
    def formatear_periodo(self, fecha: Union[date, datetime, str]) -> str:
        """
        Formatear período en formato AAAAMMDD.
        
        Args:
            fecha: Fecha a formatear (date, datetime o string)
            
        Returns:
            str: Período en formato AAAAMMDD (ej: 20250831)
        """
        try:
            if isinstance(fecha, str):
                # Intentar parsear diferentes formatos de fecha
                fecha_obj = self._parsear_fecha_string(fecha)
            elif isinstance(fecha, datetime):
                fecha_obj = fecha.date()
            elif isinstance(fecha, date):
                fecha_obj = fecha
            else:
                raise ValueError(f"Tipo de fecha no soportado: {type(fecha)}")
            
            return fecha_obj.strftime(self.FORMATO_PERIODO)
            
        except Exception as e:
            self.logger.error(f"Error al formatear período: {str(e)}")
            return ""
    
    def formatear_fecha_operacion(self, fecha: Union[date, datetime, str]) -> str:
        """
        Formatear fecha de operación en formato DD/MM/AAAA.
        
        Args:
            fecha: Fecha a formatear
            
        Returns:
            str: Fecha en formato DD/MM/AAAA (ej: 31/08/2025)
        """
        try:
            if isinstance(fecha, str):
                fecha_obj = self._parsear_fecha_string(fecha)
            elif isinstance(fecha, datetime):
                fecha_obj = fecha.date()
            elif isinstance(fecha, date):
                fecha_obj = fecha
            else:
                raise ValueError(f"Tipo de fecha no soportado: {type(fecha)}")
            
            return fecha_obj.strftime(self.FORMATO_FECHA_PLE)
            
        except Exception as e:
            self.logger.error(f"Error al formatear fecha de operación: {str(e)}")
            return ""
    
    # ================================
    # FORMATEO DE MONTOS
    # ================================
    
    def formatear_monto(self, valor: Union[float, Decimal, int, str]) -> str:
        """
        Formatear monto con precisión de 2 decimales.
        
        Args:
            valor: Valor numérico a formatear
            
        Returns:
            str: Monto formateado (ej: 1250.75)
        """
        try:
            if isinstance(valor, str):
                # Limpiar el string de caracteres no numéricos excepto punto y coma
                valor_limpio = re.sub(r'[^\d.,-]', '', valor)
                valor_limpio = valor_limpio.replace(',', '.')
                decimal_valor = Decimal(valor_limpio)
            elif isinstance(valor, (int, float)):
                decimal_valor = Decimal(str(valor))
            elif isinstance(valor, Decimal):
                decimal_valor = valor
            else:
                decimal_valor = Decimal('0.00')
            
            # Redondear a 2 decimales
            valor_redondeado = decimal_valor.quantize(
                Decimal('0.01'), 
                rounding=ROUND_HALF_UP
            )
            
            # Formatear como string sin separadores de miles
            return f"{valor_redondeado:.2f}"
            
        except Exception as e:
            self.logger.error(f"Error al formatear monto '{valor}': {str(e)}")
            return "0.00"
    
    # ================================
    # FORMATEO DE CÓDIGOS
    # ================================
    
    def formatear_cuenta_contable(self, codigo: str) -> str:
        """
        Formatear código de cuenta contable para PLE.
        
        SOLUCIÓN PARA PLE SUNAT:
        - Las cuentas pueden tener más de 4 dígitos en el sistema interno
        - SUNAT requiere máximo 4 dígitos según PCGE
        - Se trunca a 4 dígitos para cumplir normativa sin afectar contabilidad
        
        Ejemplos:
        - 11121101 → 1112 (trunca a nivel 4)
        - 40111102 → 4011 (trunca a nivel 4)  
        - 70111101 → 7011 (trunca a nivel 4)
        - 101 → 101 (mantiene si es menor a 4)
        
        Args:
            codigo: Código de cuenta a formatear
            
        Returns:
            str: Código formateado para PLE (máximo 4 dígitos)
        """
        try:
            if not codigo:
                return ""
            
            # Limpiar espacios y convertir a string
            codigo_limpio = str(codigo).strip()
            
            # Eliminar caracteres no numéricos para PLE
            codigo_numerico = re.sub(r'[^0-9]', '', codigo_limpio)
            
            if not codigo_numerico:
                self.logger.warning(f"Código de cuenta sin dígitos válidos: {codigo}")
                return ""
            
            # NORMALIZACIÓN PARA PLE SUNAT:
            # Truncar a máximo 4 dígitos según PCGE
            if len(codigo_numerico) > 4:
                codigo_ple = codigo_numerico[:4]
                self.logger.debug(f"Cuenta normalizada para PLE: {codigo} → {codigo_ple}")
            else:
                codigo_ple = codigo_numerico
            
            # Validar que el código resultante sea válido
            if not codigo_ple or len(codigo_ple) == 0:
                self.logger.error(f"Código de cuenta inválido después de normalización: {codigo}")
                return ""
            
            return codigo_ple
            
        except Exception as e:
            self.logger.error(f"Error al formatear código de cuenta '{codigo}': {str(e)}")
            return ""

    def validar_cuenta_pcge(self, codigo_cuenta: str) -> Dict[str, Any]:
        """
        Validar si una cuenta normalizada cumple con el PCGE para PLE.
        
        Esta función valida que las cuentas truncadas a 4 dígitos
        correspondan a cuentas válidas del Plan Contable General Empresarial.
        
        Args:
            codigo_cuenta: Código de cuenta normalizado (máximo 4 dígitos)
            
        Returns:
            dict: Resultado de validación con información detallada
        """
        try:
            if not codigo_cuenta:
                return {
                    'valida': False,
                    'razon': 'Código de cuenta vacío',
                    'sugerencia': 'Proporcionar un código de cuenta válido'
                }
            
            # Validar que sea numérico
            if not codigo_cuenta.isdigit():
                return {
                    'valida': False,
                    'razon': f'El código debe ser numérico: {codigo_cuenta}',
                    'sugerencia': 'Usar solo dígitos en el código de cuenta'
                }
            
            # Validar longitud (máximo 4 dígitos para PLE)
            if len(codigo_cuenta) > 4:
                return {
                    'valida': False,
                    'razon': f'Código muy largo para PLE: {codigo_cuenta} ({len(codigo_cuenta)} dígitos)',
                    'sugerencia': 'Truncar a 4 dígitos máximo'
                }
            
            # Validar estructura básica del PCGE
            primer_digito = codigo_cuenta[0]
            
            # Clasificación por primer dígito según PCGE
            clasificaciones_pcge = {
                '1': 'Activo',
                '2': 'Pasivo', 
                '3': 'Patrimonio',
                '4': 'Ingresos',
                '5': 'Gastos',
                '6': 'Gastos por naturaleza',
                '7': 'Ingresos',
                '8': 'Saldos intermediarios',
                '9': 'Cuentas analíticas'
            }
            
            if primer_digito not in clasificaciones_pcge:
                return {
                    'valida': False,
                    'razon': f'Primer dígito inválido: {primer_digito}',
                    'sugerencia': f'Debe empezar con: {", ".join(clasificaciones_pcge.keys())}'
                }
            
            # Para cuentas de 2+ dígitos, validar estructuras comunes
            if len(codigo_cuenta) >= 2:
                # Validar algunos patrones conocidos del PCGE
                cuenta_2_digitos = codigo_cuenta[:2]
                
                # Patrones válidos conocidos (lista básica - se puede expandir)
                patrones_validos = {
                    '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',  # Activos
                    '20', '21', '22', '23', '24', '25', '26', '27', '28', '29',  # Pasivos
                    '30', '31', '32', '33', '34', '35', '36', '37', '38', '39',  # Patrimonio
                    '40', '41', '42', '43', '44', '45', '46', '47', '48', '49',  # Ingresos
                    '50', '51', '52', '53', '54', '55', '56', '57', '58', '59',  # Gastos
                    '60', '61', '62', '63', '64', '65', '66', '67', '68', '69',  # Gastos por naturaleza
                    '70', '71', '72', '73', '74', '75', '76', '77', '78', '79'   # Ingresos
                }
                
                # Por ahora, aceptar todos los patrones (validación básica)
                # En producción se puede integrar con tablas SUNAT oficiales
                
            return {
                'valida': True,
                'razon': f'Cuenta válida para PLE: {codigo_cuenta}',
                'clasificacion': clasificaciones_pcge.get(primer_digito, 'Desconocida'),
                'sugerencia': None
            }
            
        except Exception as e:
            self.logger.error(f"Error validando cuenta PCGE '{codigo_cuenta}': {str(e)}")
            return {
                'valida': False,
                'razon': f'Error en validación: {str(e)}',
                'sugerencia': 'Revisar formato del código de cuenta'
            }

    def formatear_numero_correlativo(self, numero: Union[str, int]) -> str:
        """
        Formatear número correlativo del asiento (CUO).
        
        Args:
            numero: Número correlativo a formatear
            
        Returns:
            str: Número correlativo formateado
        """
        try:
            if not numero:
                return ""
            
            # Convertir a string y limpiar
            numero_str = str(numero).strip()
            
            # Validar longitud máxima
            if len(numero_str) > self.MAX_LONGITUD_CORRELATIVO:
                self.logger.warning(f"Número correlativo muy largo: {numero_str}")
                numero_str = numero_str[:self.MAX_LONGITUD_CORRELATIVO]
            
            # Validar caracteres alfanuméricos
            if not re.match(r'^[A-Za-z0-9\-_]+$', numero_str):
                # Limpiar caracteres no permitidos
                numero_str = re.sub(r'[^A-Za-z0-9\-_]', '', numero_str)
            
            return numero_str.upper()
            
        except Exception as e:
            self.logger.error(f"Error al formatear número correlativo '{numero}': {str(e)}")
            return ""
    
    # ================================
    # FORMATEO DE TEXTO
    # ================================
    
    def formatear_glosa(self, glosa: str) -> str:
        """
        Formatear glosa o descripción de operación.
        
        Args:
            glosa: Texto de la glosa a formatear
            
        Returns:
            str: Glosa formateada y validada
        """
        try:
            if not glosa:
                return ""
            
            # Limpiar y normalizar
            glosa_limpia = str(glosa).strip()
            
            # Escapar caracteres especiales
            glosa_escapada = self.escapar_caracteres_especiales(glosa_limpia)
            
            # Validar longitud máxima
            if len(glosa_escapada) > self.MAX_LONGITUD_GLOSA:
                self.logger.warning(f"Glosa muy larga, truncando: {glosa_escapada[:50]}...")
                glosa_escapada = glosa_escapada[:self.MAX_LONGITUD_GLOSA]
            
            return glosa_escapada
            
        except Exception as e:
            self.logger.error(f"Error al formatear glosa: {str(e)}")
            return ""
    
    def escapar_caracteres_especiales(self, texto: str) -> str:
        """
        Escapar caracteres especiales para formato PLE.
        
        Args:
            texto: Texto a procesar
            
        Returns:
            str: Texto con caracteres escapados
        """
        if not texto:
            return ""
        
        # Reemplazar caracteres problemáticos
        replacements = {
            '|': ' ',  # Separador de campos
            '\n': ' ',  # Saltos de línea
            '\r': ' ',  # Retornos de carro
            '\t': ' ',  # Tabulaciones
            '"': "'",   # Comillas dobles por simples
            '\\': '/',  # Backslashes
        }
        
        texto_limpio = texto
        for char_original, char_reemplazo in replacements.items():
            texto_limpio = texto_limpio.replace(char_original, char_reemplazo)
        
        # Limpiar espacios múltiples
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
        
        return texto_limpio
    
    # ================================
    # VALIDACIÓN DE LONGITUDES
    # ================================
    
    def validar_longitud_campos(self, datos: Dict[str, str]) -> FormatValidationResult:
        """
        Validar longitudes de todos los campos según especificaciones SUNAT.
        
        Args:
            datos: Diccionario con los campos a validar
            
        Returns:
            FormatValidationResult: Resultado de la validación
        """
        errores = []
        warnings = []
        
        # Definir límites por campo
        limites = {
            'numero_correlativo': self.MAX_LONGITUD_CORRELATIVO,
            'codigo_cuenta': self.MAX_LONGITUD_CUENTA,
            'glosa': self.MAX_LONGITUD_GLOSA,
            'dato_estructurado': self.MAX_LONGITUD_DATO_ESTRUCTURADO
        }
        
        # Validar cada campo
        for campo, valor in datos.items():
            if campo in limites and valor:
                longitud_actual = len(str(valor))
                limite = limites[campo]
                
                if longitud_actual > limite:
                    errores.append(f"Campo '{campo}' excede longitud máxima: {longitud_actual} > {limite}")
                elif longitud_actual > limite * 0.9:  # Warning al 90% del límite
                    warnings.append(f"Campo '{campo}' cerca del límite: {longitud_actual}/{limite}")
        
        return FormatValidationResult(
            valido=len(errores) == 0,
            errores=errores,
            warnings=warnings,
            campo_formateado=None,
            longitud_final=0
        )
    
    # ================================
    # FORMATEO COMPLETO DE LÍNEA PLE
    # ================================
    
    def formatear_linea_ple(self, datos_movimiento: Dict[str, Any]) -> PLELineFormat:
        """
        Formatear una línea completa para archivo PLE.
        
        Args:
            datos_movimiento: Datos del movimiento contable
            
        Returns:
            PLELineFormat: Línea formateada para PLE
        """
        try:
            return PLELineFormat(
                periodo=self.formatear_periodo(datos_movimiento.get('periodo', '')),
                numero_correlativo=self.formatear_numero_correlativo(
                    datos_movimiento.get('numero_correlativo', '')
                ),
                codigo_cuenta=self.formatear_cuenta_contable(
                    datos_movimiento.get('codigo_cuenta', '')
                ),
                codigo_cuenta_desagregada=self.formatear_cuenta_contable(
                    datos_movimiento.get('codigo_cuenta_desagregada', '')
                ),
                fecha_operacion=self.formatear_fecha_operacion(
                    datos_movimiento.get('fecha_operacion', '')
                ),
                glosa=self.formatear_glosa(
                    datos_movimiento.get('glosa', '')
                ),
                movimiento_debe=self.formatear_monto(
                    datos_movimiento.get('debe', 0)
                ),
                movimiento_haber=self.formatear_monto(
                    datos_movimiento.get('haber', 0)
                ),
                dato_estructurado=self.escapar_caracteres_especiales(
                    datos_movimiento.get('dato_estructurado', '')
                )
            )
            
        except Exception as e:
            self.logger.error(f"Error al formatear línea PLE: {str(e)}")
            # Retornar línea vacía en caso de error
            return PLELineFormat(
                periodo="", numero_correlativo="", codigo_cuenta="",
                codigo_cuenta_desagregada="", fecha_operacion="", glosa="",
                movimiento_debe="0.00", movimiento_haber="0.00", dato_estructurado=""
            )
    
    # ================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ================================
    
    def _parsear_fecha_string(self, fecha_str: str) -> date:
        """
        Parsear string de fecha en diferentes formatos.
        
        Args:
            fecha_str: String de fecha a parsear
            
        Returns:
            date: Objeto date parseado
        """
        formatos_posibles = [
            "%Y-%m-%d",      # 2025-08-31
            "%d/%m/%Y",      # 31/08/2025
            "%d-%m-%Y",      # 31-08-2025
            "%Y/%m/%d",      # 2025/08/31
            "%Y%m%d",        # 20250831
        ]
        
        for formato in formatos_posibles:
            try:
                return datetime.strptime(fecha_str.strip(), formato).date()
            except ValueError:
                continue
        
        raise ValueError(f"No se pudo parsear la fecha: {fecha_str}")
    
    # ================================
    # UTILIDADES DE VALIDACIÓN
    # ================================
    
    def validar_formato_numero_ple(self, numero_str: str) -> bool:
        """Validar que un número esté en formato válido para PLE"""
        try:
            # Verificar que sea un número válido con máximo 2 decimales
            partes = numero_str.split('.')
            if len(partes) > 2:
                return False
            if len(partes) == 2 and len(partes[1]) > 2:
                return False
            
            # Verificar que se pueda convertir a Decimal
            Decimal(numero_str)
            return True
        except:
            return False
    
    def validar_formato_fecha_ple(self, fecha_str: str) -> bool:
        """Validar que una fecha esté en formato DD/MM/AAAA"""
        try:
            datetime.strptime(fecha_str, self.FORMATO_FECHA_PLE)
            return True
        except ValueError:
            return False
