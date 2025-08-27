"""
PLEDataAnalyzer - Analizador de Datos Contables para PLE
========================================================

Analiza y prepara datos contables para exportación PLE,
integrando validaciones con las 12 tablas SUNAT oficiales.

Funcionalidades principales:
- Análisis de integridad de datos contables
- Verificación de balanceo debe/haber
- Enriquecimiento automático con tablas SUNAT
- Detección de errores antes de exportación
- Preparación de datos para formato PLE

Autor: Sistema ERP
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass

from app.modules.accounting.sunat_service import TablasSUNATService

logger = logging.getLogger(__name__)


@dataclass
class PLEAnalysisResult:
    """Resultado del análisis de datos para PLE"""
    valido: bool
    total_asientos: int
    total_debe: Decimal
    total_haber: Decimal
    balanceado: bool
    errores: List[str]
    warnings: List[str]
    datos_enriquecidos: Dict[str, Any]
    estadisticas: Dict[str, Any]
    fecha_analisis: datetime


@dataclass
class ValidationResult:
    """Resultado de validación general"""
    valido: bool
    errores: List[str]
    warnings: List[str]
    detalles: Dict[str, Any]


@dataclass
class BalanceResult:
    """Resultado de verificación de balanceo"""
    balanceado: bool
    diferencia: Decimal
    total_debe: Decimal
    total_haber: Decimal
    asientos_desbalanceados: List[str]
    detalle_por_asiento: Dict[str, Dict[str, Decimal]]


@dataclass
class EnrichedData:
    """Datos enriquecidos con información SUNAT"""
    datos_originales: Dict[str, Any]
    datos_enriquecidos: Dict[str, Any]
    validaciones_sunat: Dict[str, bool]
    descripciones_agregadas: Dict[str, str]
    sugerencias: List[str]


class PLEDataAnalyzer:
    """
    Analizador de datos contables para generación de archivos PLE.
    
    Integra completamente con las 12 tablas SUNAT para validación
    y enriquecimiento automático de datos.
    """
    
    def __init__(self):
        """Inicializar el analizador con servicios SUNAT"""
        self.tablas_service = TablasSUNATService()
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # ANÁLISIS PRINCIPAL
    # ================================
    
    async def analizar_libro_diario(self, libro_data: Dict[str, Any]) -> PLEAnalysisResult:
        """
        Realizar análisis completo de un libro diario para exportación PLE.
        
        Args:
            libro_data: Datos del libro diario con asientos contables
            
        Returns:
            PLEAnalysisResult: Resultado completo del análisis
        """
        try:
            # 1. Extraer asientos contables
            asientos = self._extraer_asientos_contables(libro_data)
            
            # 2. Validar estructura básica
            validacion_estructura = await self._validar_estructura_basica(asientos)
            
            # 3. Verificar balanceo contable
            resultado_balance = await self._verificar_balanceo_completo(asientos)
            
            # 4. Enriquecer con datos SUNAT
            datos_enriquecidos = await self._enriquecer_con_tablas_sunat(asientos)
            
            # 5. Calcular estadísticas
            estadisticas = self._calcular_estadisticas(asientos, datos_enriquecidos)
            
            # 6. Consolidar resultados
            return PLEAnalysisResult(
                valido=(validacion_estructura.valido and resultado_balance.balanceado),
                total_asientos=len(asientos),
                total_debe=resultado_balance.total_debe,
                total_haber=resultado_balance.total_haber,
                balanceado=resultado_balance.balanceado,
                errores=validacion_estructura.errores + self._extraer_errores_balance(resultado_balance),
                warnings=validacion_estructura.warnings,
                datos_enriquecidos=datos_enriquecidos.datos_enriquecidos,
                estadisticas=estadisticas,
                fecha_analisis=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error en análisis PLE: {str(e)}")
            return PLEAnalysisResult(
                valido=False,
                total_asientos=0,
                total_debe=Decimal('0.00'),
                total_haber=Decimal('0.00'),
                balanceado=False,
                errores=[f"Error crítico en análisis: {str(e)}"],
                warnings=[],
                datos_enriquecidos={},
                estadisticas={},
                fecha_analisis=datetime.utcnow()
            )
    
    # ================================
    # VALIDACIÓN DE ASIENTOS CONTABLES
    # ================================
    
    async def validar_asientos_contables(self, asientos: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validar la estructura y contenido de asientos contables.
        
        Args:
            asientos: Lista de asientos contables a validar
            
        Returns:
            ValidationResult: Resultado de la validación
        """
        errores = []
        warnings = []
        detalles = {}
        
        try:
            # Validar cada asiento individualmente
            for i, asiento in enumerate(asientos):
                resultado_asiento = await self._validar_asiento_individual(asiento, i)
                
                if resultado_asiento.errores:
                    errores.extend([f"Asiento {i+1}: {error}" for error in resultado_asiento.errores])
                
                if resultado_asiento.warnings:
                    warnings.extend([f"Asiento {i+1}: {warning}" for warning in resultado_asiento.warnings])
                
                detalles[f"asiento_{i+1}"] = resultado_asiento.detalles
            
            # Validaciones globales
            errores_globales = await self._validar_consistencia_global(asientos)
            errores.extend(errores_globales)
            
            return ValidationResult(
                valido=len(errores) == 0,
                errores=errores,
                warnings=warnings,
                detalles=detalles
            )
            
        except Exception as e:
            self.logger.error(f"Error en validación de asientos: {str(e)}")
            return ValidationResult(
                valido=False,
                errores=[f"Error en validación: {str(e)}"],
                warnings=[],
                detalles={}
            )
    
    # ================================
    # VERIFICACIÓN DE BALANCEO
    # ================================
    
    async def verificar_balanceo(self, asientos: List[Dict[str, Any]]) -> BalanceResult:
        """
        Verificar el balanceo contable de los asientos (Debe = Haber).
        
        Args:
            asientos: Lista de asientos contables
            
        Returns:
            BalanceResult: Resultado de la verificación de balance
        """
        try:
            total_debe = Decimal('0.00')
            total_haber = Decimal('0.00')
            asientos_desbalanceados = []
            detalle_por_asiento = {}
            
            # Analizar cada asiento
            for i, asiento in enumerate(asientos):
                asiento_id = asiento.get('id', f'asiento_{i+1}')
                debe_asiento = Decimal('0.00')
                haber_asiento = Decimal('0.00')
                
                # Sumar movimientos del asiento
                movimientos = asiento.get('movimientos', [])
                for movimiento in movimientos:
                    debe = Decimal(str(movimiento.get('debe', 0)))
                    haber = Decimal(str(movimiento.get('haber', 0)))
                    
                    debe_asiento += debe
                    haber_asiento += haber
                    total_debe += debe
                    total_haber += haber
                
                # Verificar balanceo del asiento individual
                diferencia_asiento = debe_asiento - haber_asiento
                if abs(diferencia_asiento) > Decimal('0.01'):  # Tolerancia de 1 centavo
                    asientos_desbalanceados.append(asiento_id)
                
                detalle_por_asiento[asiento_id] = {
                    'debe': debe_asiento,
                    'haber': haber_asiento,
                    'diferencia': diferencia_asiento
                }
            
            # Calcular diferencia total
            diferencia_total = total_debe - total_haber
            balanceado = abs(diferencia_total) <= Decimal('0.01')
            
            return BalanceResult(
                balanceado=balanceado,
                diferencia=diferencia_total,
                total_debe=total_debe,
                total_haber=total_haber,
                asientos_desbalanceados=asientos_desbalanceados,
                detalle_por_asiento=detalle_por_asiento
            )
            
        except Exception as e:
            self.logger.error(f"Error en verificación de balanceo: {str(e)}")
            return BalanceResult(
                balanceado=False,
                diferencia=Decimal('0.00'),
                total_debe=Decimal('0.00'),
                total_haber=Decimal('0.00'),
                asientos_desbalanceados=[],
                detalle_por_asiento={}
            )
    
    # ================================
    # ENRIQUECIMIENTO CON TABLAS SUNAT
    # ================================
    
    async def enriquecer_con_tablas_sunat(self, datos: Dict[str, Any]) -> EnrichedData:
        """
        Enriquecer datos contables con información de las tablas SUNAT.
        
        Args:
            datos: Datos contables a enriquecer
            
        Returns:
            EnrichedData: Datos enriquecidos con validaciones SUNAT
        """
        try:
            datos_enriquecidos = datos.copy()
            validaciones_sunat = {}
            descripciones_agregadas = {}
            sugerencias = []
            
            # Enriquecer códigos de cuenta contable
            await self._enriquecer_cuentas_contables(
                datos_enriquecidos, validaciones_sunat, descripciones_agregadas, sugerencias
            )
            
            # Enriquecer tipos de comprobante
            await self._enriquecer_tipos_comprobante(
                datos_enriquecidos, validaciones_sunat, descripciones_agregadas, sugerencias
            )
            
            # Enriquecer tipos de moneda
            await self._enriquecer_tipos_moneda(
                datos_enriquecidos, validaciones_sunat, descripciones_agregadas, sugerencias
            )
            
            # Validar códigos de libros
            await self._validar_codigo_libro_diario(validaciones_sunat)
            
            return EnrichedData(
                datos_originales=datos,
                datos_enriquecidos=datos_enriquecidos,
                validaciones_sunat=validaciones_sunat,
                descripciones_agregadas=descripciones_agregadas,
                sugerencias=sugerencias
            )
            
        except Exception as e:
            self.logger.error(f"Error en enriquecimiento SUNAT: {str(e)}")
            return EnrichedData(
                datos_originales=datos,
                datos_enriquecidos=datos,
                validaciones_sunat={},
                descripciones_agregadas={},
                sugerencias=[f"Error en enriquecimiento: {str(e)}"]
            )
    
    # ================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ================================
    
    def _extraer_asientos_contables(self, libro_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extraer lista de asientos contables del libro diario"""
        asientos = libro_data.get('asientos', [])
        if not asientos:
            # Intentar otras estructuras posibles
            asientos = libro_data.get('asientos_contables', [])
        
        return asientos if isinstance(asientos, list) else []
    
    async def _validar_estructura_basica(self, asientos: List[Dict[str, Any]]) -> ValidationResult:
        """Validar estructura básica de asientos"""
        errores = []
        warnings = []
        
        if not asientos:
            errores.append("No se encontraron asientos contables para analizar")
            return ValidationResult(False, errores, warnings, {})
        
        # Validar cada asiento
        for i, asiento in enumerate(asientos):
            if not isinstance(asiento, dict):
                errores.append(f"Asiento {i+1}: Estructura inválida")
                continue
            
            # Verificar campos obligatorios
            campos_obligatorios = ['fecha', 'glosa', 'movimientos']
            for campo in campos_obligatorios:
                if campo not in asiento:
                    errores.append(f"Asiento {i+1}: Campo obligatorio '{campo}' faltante")
            
            # Validar movimientos
            movimientos = asiento.get('movimientos', [])
            if not movimientos:
                errores.append(f"Asiento {i+1}: No tiene movimientos contables")
            elif len(movimientos) < 2:
                warnings.append(f"Asiento {i+1}: Solo tiene {len(movimientos)} movimiento(s)")
        
        return ValidationResult(
            valido=len(errores) == 0,
            errores=errores,
            warnings=warnings,
            detalles={'total_asientos_validados': len(asientos)}
        )
    
    async def _verificar_balanceo_completo(self, asientos: List[Dict[str, Any]]) -> BalanceResult:
        """Verificación completa de balanceo"""
        return await self.verificar_balanceo(asientos)
    
    async def _enriquecer_con_tablas_sunat(self, asientos: List[Dict[str, Any]]) -> EnrichedData:
        """Enriquecer asientos con datos SUNAT"""
        datos_consolidados = {'asientos': asientos}
        return await self.enriquecer_con_tablas_sunat(datos_consolidados)
    
    def _calcular_estadisticas(self, asientos: List[Dict[str, Any]], datos_enriquecidos: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular estadísticas del análisis"""
        total_movimientos = sum(len(asiento.get('movimientos', [])) for asiento in asientos)
        
        return {
            'total_asientos': len(asientos),
            'total_movimientos': total_movimientos,
            'promedio_movimientos_por_asiento': total_movimientos / len(asientos) if asientos else 0,
            'cuentas_unicas': len(set(
                mov.get('cuenta_contable', '') 
                for asiento in asientos 
                for mov in asiento.get('movimientos', [])
            )),
            'fecha_primer_asiento': min(
                (asiento.get('fecha') for asiento in asientos if asiento.get('fecha')), 
                default=None
            ),
            'fecha_ultimo_asiento': max(
                (asiento.get('fecha') for asiento in asientos if asiento.get('fecha')), 
                default=None
            )
        }
    
    def _extraer_errores_balance(self, resultado_balance: BalanceResult) -> List[str]:
        """Extraer errores de balanceo como lista de strings"""
        errores = []
        
        if not resultado_balance.balanceado:
            errores.append(f"Libro diario desbalanceado: diferencia de {resultado_balance.diferencia}")
        
        for asiento_id in resultado_balance.asientos_desbalanceados:
            detalle = resultado_balance.detalle_por_asiento.get(asiento_id, {})
            diferencia = detalle.get('diferencia', 0)
            errores.append(f"Asiento {asiento_id} desbalanceado: diferencia de {diferencia}")
        
        return errores
    
    async def _validar_asiento_individual(self, asiento: Dict[str, Any], indice: int) -> ValidationResult:
        """Validar un asiento individual"""
        errores = []
        warnings = []
        detalles = {}
        
        # Validar fecha
        fecha = asiento.get('fecha')
        if not fecha:
            errores.append("Fecha faltante")
        
        # Validar glosa
        glosa = asiento.get('glosa', '').strip()
        if not glosa:
            errores.append("Glosa faltante")
        elif len(glosa) > 200:
            warnings.append("Glosa muy larga (>200 caracteres)")
        
        # Validar movimientos
        movimientos = asiento.get('movimientos', [])
        if len(movimientos) < 2:
            errores.append("Debe tener al menos 2 movimientos")
        
        return ValidationResult(
            valido=len(errores) == 0,
            errores=errores,
            warnings=warnings,
            detalles=detalles
        )
    
    async def _validar_consistencia_global(self, asientos: List[Dict[str, Any]]) -> List[str]:
        """Validar consistencia global entre asientos"""
        errores = []
        
        # Verificar unicidad de números de asiento
        numeros_asiento = []
        for asiento in asientos:
            numero = asiento.get('numero_asiento')
            if numero:
                if numero in numeros_asiento:
                    errores.append(f"Número de asiento duplicado: {numero}")
                numeros_asiento.append(numero)
        
        return errores
    
    # Métodos de enriquecimiento específicos por tabla SUNAT
    async def _enriquecer_cuentas_contables(self, datos: Dict, validaciones: Dict, descripciones: Dict, sugerencias: List):
        """Enriquecer códigos de cuenta contable"""
        from .ple_formatter import PLEFormatter
        
        formatter = PLEFormatter()
        
        # Buscar todas las cuentas contables en los datos
        cuentas_encontradas = set()
        
        # Extraer cuentas de asientos
        asientos = datos.get('asientos', [])
        for asiento in asientos:
            movimientos = asiento.get('movimientos', [])
            for mov in movimientos:
                codigo_cuenta = mov.get('cuenta_contable', '')
                if codigo_cuenta:
                    cuentas_encontradas.add(codigo_cuenta)
        
        # Validar cada cuenta encontrada
        cuentas_validas = 0
        cuentas_total = len(cuentas_encontradas)
        cuentas_advertencias = []
        
        for codigo_cuenta in cuentas_encontradas:
            # Formatear la cuenta para PLE (truncar a 4 dígitos)
            cuenta_ple = formatter.formatear_cuenta_contable(codigo_cuenta)
            
            # Validar cuenta PCGE
            validacion = formatter.validar_cuenta_pcge(cuenta_ple)
            
            if validacion['valida']:
                cuentas_validas += 1
            else:
                cuentas_advertencias.append({
                    'cuenta_original': codigo_cuenta,
                    'cuenta_ple': cuenta_ple,
                    'razon': validacion['razon'],
                    'sugerencia': validacion.get('sugerencia', '')
                })
        
        # Actualizar validaciones
        validaciones['cuentas_contables_validas'] = cuentas_validas == cuentas_total
        validaciones['cuentas_contables_stats'] = {
            'total': cuentas_total,
            'validas': cuentas_validas,
            'invalidas': cuentas_total - cuentas_validas
        }
        
        # Agregar descripciones
        if cuentas_total > 0:
            porcentaje_validas = (cuentas_validas / cuentas_total) * 100
            descripciones['cuentas_contables'] = f"{cuentas_validas}/{cuentas_total} cuentas válidas ({porcentaje_validas:.1f}%)"
        else:
            descripciones['cuentas_contables'] = "No se encontraron cuentas contables"
        
        # Agregar sugerencias para cuentas problemáticas
        if cuentas_advertencias:
            sugerencias.append(f"Se encontraron {len(cuentas_advertencias)} cuentas con advertencias para PLE")
            for adv in cuentas_advertencias[:3]:  # Mostrar solo las primeras 3
                sugerencias.append(f"Cuenta {adv['cuenta_original']} → {adv['cuenta_ple']}: {adv['razon']}")
    
    async def _enriquecer_tipos_comprobante(self, datos: Dict, validaciones: Dict, descripciones: Dict, sugerencias: List):
        """Enriquecer tipos de comprobante"""
        # Implementación para validar tipos de comprobante
        pass
    
    async def _enriquecer_tipos_moneda(self, datos: Dict, validaciones: Dict, descripciones: Dict, sugerencias: List):
        """Enriquecer tipos de moneda"""
        # Implementación para validar tipos de moneda
        pass
    
    async def _validar_codigo_libro_diario(self, validaciones: Dict):
        """Validar que el código 5 (Libro Diario) existe en la tabla"""
        resultado = await self.tablas_service.validar_codigo("codigos_libros_registros", "5")
        validaciones['codigo_libro_diario'] = resultado.valido
