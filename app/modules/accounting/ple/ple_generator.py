"""
PLEGenerator - Generador de Archivos PLE
========================================

Generador de archivos PLE en formato SUNAT para Libro Diario.
Integrado con PLEAnalyzer y PLEFormatter para generar archivos
100% conformes con las especificaciones de SUNAT.

Funcionalidades principales:
- Generación de archivos TXT según formato SUNAT
- Nomenclatura automática de archivos
- Formateo de campos con precisión requerida
- Compresión ZIP automática
- Validación previa a la generación

Especificaciones SUNAT:
- Formato: Libro Diario 5.1
- Separador: |
- Codificación: UTF-8
- Compresión: ZIP obligatoria

Autor: Sistema ERP
Fecha: Agosto 2025
"""

import os
import re
import logging
import zipfile
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, date
from io import StringIO, BytesIO
from dataclasses import dataclass

from .ple_analyzer import PLEDataAnalyzer, PLEAnalysisResult
from .ple_formatter import PLEFormatter, PLELineFormat

logger = logging.getLogger(__name__)


@dataclass
class PLEOptions:
    """Opciones para la generación de archivos PLE"""
    incluir_asientos_cero: bool = True
    validar_antes_generar: bool = True
    generar_zip: bool = True
    incluir_metadatos: bool = True
    formato_fecha: str = "DD/MM/YYYY"
    precision_montos: int = 2
    validar_con_sunat: bool = True
    # Nuevas opciones para validación SUNAT
    validar_plan_contable: bool = True
    validar_tipos_documento: bool = True
    enriquecer_con_sunat: bool = True
    permitir_cuentas_personalizadas: bool = True
    fallar_en_errores_criticos: bool = True
    incluir_reporte_validacion: bool = True
    

@dataclass
class PLEArchivo:
    """Resultado de la generación de archivo PLE"""
    nombre_archivo: str
    contenido_txt: str
    contenido_zip: Optional[bytes]
    tamaño_txt: int
    tamaño_zip: Optional[int]
    total_lineas: int
    resumen_validacion: Dict[str, Any]
    metadatos: Dict[str, Any]
    fecha_generacion: datetime
    errores: List[str]
    warnings: List[str]
    # Nuevos campos para validación SUNAT
    validacion_sunat: Optional[Dict[str, Any]] = None
    datos_enriquecidos: bool = False
    reporte_validacion: Optional[str] = None


@dataclass
class PLEMetadata:
    """Metadatos del archivo PLE generado"""
    empresa_ruc: str
    periodo: str
    codigo_libro: str = "5"  # Libro Diario
    formato: str = "1"       # Simplificado
    moneda: str = "00"       # Soles
    operacion: str = "1"     # Cierre mensual
    contenido: str = "1"     # Con información
    total_asientos: int = 0
    total_debe: str = "0.00"
    total_haber: str = "0.00"


class PLEGenerator:
    """
    Generador de archivos PLE para Libro Diario.
    
    Utiliza PLEAnalyzer para validación previa y PLEFormatter 
    para formateo correcto de todos los campos según normativa SUNAT.
    """
    
    def __init__(self):
        """Inicializar el generador con sus dependencias"""
        self.analyzer = PLEDataAnalyzer()
        self.formatter = PLEFormatter()
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # MÉTODO PRINCIPAL DE GENERACIÓN
    # ================================
    
    async def generar_libro_diario_ple(
        self, 
        libro_data: Dict[str, Any],
        empresa_ruc: str,
        periodo: Union[date, str],
        opciones: Optional[PLEOptions] = None
    ) -> PLEArchivo:
        """
        Generar archivo PLE completo para Libro Diario.
        
        Args:
            libro_data: Datos del libro diario con asientos
            empresa_ruc: RUC de la empresa (11 dígitos)
            periodo: Período del libro (fecha o string AAAAMMDD)
            opciones: Opciones de generación
            
        Returns:
            PLEArchivo: Archivo PLE generado con todos los metadatos
        """
        if opciones is None:
            opciones = PLEOptions()
        
        errores = []
        warnings = []
        
        try:
            self.logger.info(f"Iniciando generación PLE para RUC {empresa_ruc}, período {periodo}")
            
            # 1. Validación previa de datos (básica y SUNAT)
            validacion_sunat = None
            if opciones.validar_antes_generar:
                resultado_analisis, validacion_sunat = await self._validar_datos_previos(libro_data, opciones)
                if not resultado_analisis.valido:
                    errores.extend(resultado_analisis.errores)
                    if errores:  # Si hay errores críticos, detener
                        return self._crear_archivo_error(errores, warnings, validacion_sunat)
                warnings.extend(resultado_analisis.warnings)
            
            # 2. Enriquecer datos con SUNAT si está habilitado
            datos_libro_final = libro_data
            datos_enriquecidos = False
            if opciones.enriquecer_con_sunat and opciones.validar_con_sunat:
                try:
                    from .ple_sunat_validator import PLESUNATValidator
                    
                    validator = PLESUNATValidator()
                    datos_libro_final = await validator.enriquecer_datos_libro_diario(libro_data)
                    datos_enriquecidos = True
                    self.logger.info("Datos enriquecidos con información SUNAT")
                    
                except Exception as e:
                    self.logger.warning(f"No se pudieron enriquecer los datos con SUNAT: {str(e)}")
                    warnings.append(f"Enriquecimiento SUNAT falló: {str(e)}")
            
            # 3. Preparar metadatos
            metadatos = self._crear_metadatos(empresa_ruc, periodo, datos_libro_final)
            
            # 4. Generar nombre del archivo
            nombre_archivo = self.generar_nombre_archivo(empresa_ruc, periodo)
            
            # 5. Generar contenido TXT
            contenido_txt, estadisticas = await self._generar_contenido_txt(
                datos_libro_final, metadatos, opciones
            )
            
            # 6. Generar ZIP si es requerido
            contenido_zip = None
            tamaño_zip = None
            if opciones.generar_zip:
                contenido_zip = self._crear_archivo_zip(nombre_archivo, contenido_txt)
                tamaño_zip = len(contenido_zip)
            
            # 7. Crear resumen de validación
            resumen_validacion = self._crear_resumen_validacion(estadisticas, opciones)
            
            # 8. Generar reporte de validación si está habilitado
            reporte_validacion = None
            if opciones.incluir_reporte_validacion and validacion_sunat:
                reporte_validacion = self._generar_reporte_validacion(validacion_sunat, estadisticas)
            
            resultado = PLEArchivo(
                nombre_archivo=nombre_archivo,
                contenido_txt=contenido_txt,
                contenido_zip=contenido_zip,
                tamaño_txt=len(contenido_txt.encode('utf-8')),
                tamaño_zip=tamaño_zip,
                total_lineas=estadisticas.get('total_lineas', 0),
                resumen_validacion=resumen_validacion,
                metadatos=metadatos.__dict__,
                fecha_generacion=datetime.utcnow(),
                errores=errores,
                warnings=warnings,
                validacion_sunat=validacion_sunat,
                datos_enriquecidos=datos_enriquecidos,
                reporte_validacion=reporte_validacion
            )
            
            self.logger.info(f"Archivo PLE generado exitosamente: {nombre_archivo}")
            return resultado
            
        except Exception as e:
            error_msg = f"Error crítico en generación PLE: {str(e)}"
            self.logger.error(error_msg)
            errores.append(error_msg)
            return self._crear_archivo_error(errores, warnings)
    
    # ================================
    # GENERACIÓN DE NOMBRES DE ARCHIVO
    # ================================
    
    def generar_nombre_archivo(self, empresa_ruc: str, periodo: Union[date, str]) -> str:
        """
        Generar nombre de archivo según nomenclatura SUNAT.
        
        Formato: LE[RUC][AAAAMMDD][AAAA][MM][00][5][1][00][1][1].TXT
        
        Args:
            empresa_ruc: RUC de la empresa (11 dígitos)
            periodo: Período del reporte
            
        Returns:
            str: Nombre de archivo formateado
        """
        try:
            # Limpiar y validar RUC
            ruc_limpio = re.sub(r'[^0-9]', '', str(empresa_ruc))
            if len(ruc_limpio) != 11:
                raise ValueError(f"RUC debe tener 11 dígitos: {empresa_ruc}")
            
            # Convertir período a fecha si es string
            if isinstance(periodo, str):
                if len(periodo) == 8:  # AAAAMMDD
                    fecha_periodo = datetime.strptime(periodo, "%Y%m%d").date()
                else:
                    raise ValueError(f"Formato de período inválido: {periodo}")
            elif isinstance(periodo, datetime):
                fecha_periodo = periodo.date()
            elif isinstance(periodo, date):
                fecha_periodo = periodo
            else:
                raise ValueError(f"Tipo de período no soportado: {type(periodo)}")
            
            # Componentes del nombre
            prefijo = "LE"
            ruc = ruc_limpio
            fecha_reporte = fecha_periodo.strftime("%Y%m%d")
            año_mes = fecha_periodo.strftime("%Y%m")
            oportunidad = "00"  # Normal
            codigo_libro = "5"   # Libro Diario
            formato = "1"        # Simplificado
            moneda = "00"        # Soles
            operacion = "1"      # Cierre mensual
            contenido = "1"      # Con información
            extension = ".TXT"
            
            nombre = f"{prefijo}{ruc}{fecha_reporte}{año_mes}{oportunidad}{codigo_libro}{formato}{moneda}{operacion}{contenido}{extension}"
            
            return nombre
            
        except Exception as e:
            self.logger.error(f"Error al generar nombre de archivo: {str(e)}")
            # Nombre de fallback
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"LIBRO_DIARIO_PLE_{timestamp}.TXT"
    
    # ================================
    # GENERACIÓN DE CONTENIDO
    # ================================
    
    async def _generar_contenido_txt(
        self, 
        libro_data: Dict[str, Any], 
        metadatos: PLEMetadata,
        opciones: PLEOptions
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generar el contenido TXT del archivo PLE.
        
        Args:
            libro_data: Datos del libro diario
            metadatos: Metadatos del archivo
            opciones: Opciones de generación
            
        Returns:
            Tuple[str, Dict]: Contenido TXT y estadísticas
        """
        lineas_ple = []
        estadisticas = {
            'total_lineas': 0,
            'total_asientos': 0,
            'total_movimientos': 0,
            'asientos_con_errores': 0,
            'lineas_omitidas': 0
        }
        
        try:
            # Extraer asientos del libro diario
            asientos = libro_data.get('asientos', [])
            if not asientos:
                self.logger.warning("No se encontraron asientos en el libro diario")
                return "", estadisticas
            
            estadisticas['total_asientos'] = len(asientos)
            
            # Procesar cada asiento
            for i, asiento in enumerate(asientos):
                try:
                    lineas_asiento = await self._procesar_asiento_para_ple(
                        asiento, metadatos, opciones, i + 1
                    )
                    
                    # Filtrar líneas según opciones
                    if opciones.incluir_asientos_cero:
                        lineas_ple.extend(lineas_asiento)
                    else:
                        # Solo incluir líneas con movimientos > 0
                        lineas_filtradas = [
                            linea for linea in lineas_asiento 
                            if self._tiene_movimiento_significativo(linea)
                        ]
                        lineas_ple.extend(lineas_filtradas)
                        estadisticas['lineas_omitidas'] += len(lineas_asiento) - len(lineas_filtradas)
                    
                    estadisticas['total_movimientos'] += len(lineas_asiento)
                    
                except Exception as e:
                    self.logger.error(f"Error procesando asiento {i+1}: {str(e)}")
                    estadisticas['asientos_con_errores'] += 1
                    continue
            
            estadisticas['total_lineas'] = len(lineas_ple)
            
            # Convertir líneas a texto
            contenido_txt = '\n'.join(lineas_ple)
            
            # Agregar línea final vacía si es requerida
            if contenido_txt and not contenido_txt.endswith('\n'):
                contenido_txt += '\n'
            
            return contenido_txt, estadisticas
            
        except Exception as e:
            self.logger.error(f"Error generando contenido TXT: {str(e)}")
            return "", estadisticas
    
    async def _procesar_asiento_para_ple(
        self, 
        asiento: Dict[str, Any], 
        metadatos: PLEMetadata,
        opciones: PLEOptions,
        numero_asiento: int
    ) -> List[str]:
        """
        Procesar un asiento contable para convertirlo a líneas PLE.
        
        Args:
            asiento: Datos del asiento contable
            metadatos: Metadatos del archivo PLE
            opciones: Opciones de generación
            numero_asiento: Número correlativo del asiento
            
        Returns:
            List[str]: Lista de líneas PLE para el asiento
        """
        lineas = []
        
        try:
            # Extraer datos básicos del asiento
            fecha_operacion = asiento.get('fecha', '')
            glosa = asiento.get('glosa', '')
            numero_correlativo = asiento.get('numero_asiento', numero_asiento)
            movimientos = asiento.get('movimientos', [])
            
            if not movimientos:
                self.logger.warning(f"Asiento {numero_asiento} sin movimientos")
                return lineas
            
            # Procesar cada movimiento del asiento
            for movimiento in movimientos:
                datos_movimiento = {
                    'periodo': metadatos.periodo,
                    'numero_correlativo': numero_correlativo,
                    'codigo_cuenta': movimiento.get('cuenta_contable', ''),
                    'codigo_cuenta_desagregada': movimiento.get('cuenta_desagregada', ''),
                    'fecha_operacion': fecha_operacion,
                    'glosa': glosa,
                    'debe': movimiento.get('debe', 0),
                    'haber': movimiento.get('haber', 0),
                    'dato_estructurado': movimiento.get('dato_estructurado', '')
                }
                
                # Formatear la línea usando PLEFormatter
                linea_formateada = self.formatter.formatear_linea_ple(datos_movimiento)
                lineas.append(linea_formateada.to_line())
            
            return lineas
            
        except Exception as e:
            self.logger.error(f"Error procesando asiento {numero_asiento}: {str(e)}")
            return lineas
    
    # ================================
    # COMPRESIÓN ZIP
    # ================================
    
    def _crear_archivo_zip(self, nombre_archivo: str, contenido_txt: str) -> bytes:
        """
        Crear archivo ZIP con el contenido TXT.
        
        Args:
            nombre_archivo: Nombre del archivo TXT
            contenido_txt: Contenido del archivo TXT
            
        Returns:
            bytes: Contenido del archivo ZIP
        """
        try:
            # Crear ZIP en memoria
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Agregar archivo TXT al ZIP
                zip_file.writestr(nombre_archivo, contenido_txt.encode('utf-8'))
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error creando archivo ZIP: {str(e)}")
            return b""
    
    # ================================
    # MÉTODOS AUXILIARES
    # ================================
    
    async def _validar_datos_previos(
        self, 
        libro_data: Dict[str, Any], 
        opciones: PLEOptions
    ) -> Tuple[PLEAnalysisResult, Optional[Dict[str, Any]]]:
        """
        Validar datos antes de generar el archivo.
        Incluye validación básica y validación SUNAT según configuración.
        
        Returns:
            Tuple[PLEAnalysisResult, Optional[validacion_sunat]]
        """
        # 1. Validación básica con PLEDataAnalyzer
        resultado_basico = await self.analyzer.analizar_libro_diario(libro_data)
        
        # 2. Validación SUNAT si está habilitada
        validacion_sunat = None
        if opciones.validar_con_sunat:
            try:
                from .ple_sunat_validator import PLESUNATValidator
                
                validator = PLESUNATValidator()
                opciones_sunat = {
                    "validar_plan_contable": opciones.validar_plan_contable,
                    "validar_tipos_documento": opciones.validar_tipos_documento,
                    "permitir_cuentas_personalizadas": opciones.permitir_cuentas_personalizadas
                }
                
                resultado_sunat = await validator.validar_libro_diario_completo(
                    libro_data, opciones_sunat
                )
                
                # Consolidar errores y warnings
                if resultado_sunat.errores:
                    # Convertir errores SUNAT a formato PLEAnalysisResult
                    for error_sunat in resultado_sunat.errores:
                        if error_sunat.critico and opciones.fallar_en_errores_criticos:
                            resultado_basico.errores.append(f"SUNAT: {error_sunat.mensaje}")
                        else:
                            resultado_basico.warnings.append(f"SUNAT: {error_sunat.mensaje}")
                
                if resultado_sunat.warnings:
                    for warning_sunat in resultado_sunat.warnings:
                        resultado_basico.warnings.append(f"SUNAT: {warning_sunat.mensaje}")
                
                # Actualizar validez si hay errores críticos SUNAT
                errores_criticos_sunat = [e for e in resultado_sunat.errores if e.critico]
                if errores_criticos_sunat and opciones.fallar_en_errores_criticos:
                    resultado_basico.valido = False
                
                validacion_sunat = {
                    "realizada": True,
                    "valida": resultado_sunat.valido,
                    "total_errores": len(resultado_sunat.errores),
                    "total_warnings": len(resultado_sunat.warnings),
                    "datos_enriquecidos": len(resultado_sunat.datos_enriquecidos),
                    "estadisticas": resultado_sunat.estadisticas,
                    "tiempo_validacion": resultado_sunat.tiempo_validacion
                }
                
                self.logger.info(
                    f"Validación SUNAT completada: {len(resultado_sunat.errores)} errores, "
                    f"{len(resultado_sunat.warnings)} warnings, "
                    f"{len(resultado_sunat.datos_enriquecidos)} datos enriquecidos"
                )
                
            except Exception as e:
                self.logger.error(f"Error en validación SUNAT: {str(e)}")
                resultado_basico.warnings.append(f"No se pudo realizar validación SUNAT: {str(e)}")
                validacion_sunat = {
                    "realizada": False,
                    "error": str(e)
                }
        
        return resultado_basico, validacion_sunat
    
    def _crear_metadatos(self, empresa_ruc: str, periodo: Union[date, str], libro_data: Dict[str, Any]) -> PLEMetadata:
        """Crear metadatos del archivo PLE"""
        # Convertir período a string si es fecha
        if isinstance(periodo, (date, datetime)):
            periodo_str = periodo.strftime("%Y%m%d")
        else:
            periodo_str = str(periodo)
        
        return PLEMetadata(
            empresa_ruc=empresa_ruc,
            periodo=periodo_str,
            total_asientos=len(libro_data.get('asientos', []))
        )
    
    def _crear_resumen_validacion(self, estadisticas: Dict[str, Any], opciones: PLEOptions) -> Dict[str, Any]:
        """Crear resumen de validación"""
        return {
            'opciones_aplicadas': opciones.__dict__,
            'estadisticas': estadisticas,
            'validaciones_realizadas': [
                'formato_campos',
                'longitud_maxima',
                'caracteres_especiales',
                'balanceo_asientos' if opciones.validar_antes_generar else 'no_validado'
            ]
        }
    
    def _crear_archivo_error(
        self, 
        errores: List[str], 
        warnings: List[str],
        validacion_sunat: Optional[Dict[str, Any]] = None
    ) -> PLEArchivo:
        """Crear archivo PLE con errores"""
        return PLEArchivo(
            nombre_archivo="ERROR_PLE.TXT",
            contenido_txt="",
            contenido_zip=None,
            tamaño_txt=0,
            tamaño_zip=None,
            total_lineas=0,
            resumen_validacion={},
            metadatos={},
            fecha_generacion=datetime.utcnow(),
            errores=errores,
            warnings=warnings,
            validacion_sunat=validacion_sunat,
            datos_enriquecidos=False,
            reporte_validacion=None
        )
    
    def _generar_reporte_validacion(
        self, 
        validacion_sunat: Dict[str, Any], 
        estadisticas: Dict[str, Any]
    ) -> str:
        """Generar reporte detallado de validación"""
        
        reporte = []
        reporte.append("REPORTE DE VALIDACIÓN PLE - LIBRO DIARIO")
        reporte.append("=" * 50)
        reporte.append(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        reporte.append("")
        
        # Información de validación SUNAT
        if validacion_sunat and validacion_sunat.get("realizada", False):
            reporte.append("📋 VALIDACIÓN SUNAT")
            reporte.append("-" * 20)
            reporte.append(f"Estado: {'✅ VÁLIDO' if validacion_sunat.get('valida', False) else '❌ CON ERRORES'}")
            reporte.append(f"Total errores: {validacion_sunat.get('total_errores', 0)}")
            reporte.append(f"Total warnings: {validacion_sunat.get('total_warnings', 0)}")
            reporte.append(f"Datos enriquecidos: {validacion_sunat.get('datos_enriquecidos', 0)}")
            reporte.append(f"Tiempo de validación: {validacion_sunat.get('tiempo_validacion', 0):.2f}s")
            reporte.append("")
            
            # Estadísticas SUNAT
            if "estadisticas" in validacion_sunat:
                stats = validacion_sunat["estadisticas"]
                reporte.append("📊 ESTADÍSTICAS SUNAT")
                reporte.append("-" * 20)
                reporte.append(f"Porcentaje validado: {stats.get('porcentaje_validado', 0):.1f}%")
                reporte.append(f"Cuentas validadas: {stats.get('cuentas_validadas', 0)}")
                reporte.append(f"Errores críticos: {stats.get('errores_criticos', 0)}")
                reporte.append("")
        
        # Estadísticas generales
        reporte.append("📈 ESTADÍSTICAS GENERALES")
        reporte.append("-" * 20)
        reporte.append(f"Total líneas generadas: {estadisticas.get('total_lineas', 0)}")
        reporte.append(f"Total asientos procesados: {estadisticas.get('total_asientos', 0)}")
        reporte.append("")
        
        # Resumen final
        reporte.append("🏁 RESUMEN")
        reporte.append("-" * 10)
        if validacion_sunat and validacion_sunat.get("valida", False):
            reporte.append("✅ El archivo PLE cumple con las validaciones SUNAT")
        else:
            reporte.append("⚠️  El archivo PLE tiene observaciones que revisar")
        
        return "\n".join(reporte)
    
    def _tiene_movimiento_significativo(self, linea: str) -> bool:
        """Verificar si una línea tiene movimientos significativos (> 0)"""
        try:
            campos = linea.split('|')
            if len(campos) >= 8:
                debe = float(campos[6]) if campos[6] else 0.0
                haber = float(campos[7]) if campos[7] else 0.0
                return debe > 0.01 or haber > 0.01
            return False
        except:
            return True  # En caso de duda, incluir la línea
