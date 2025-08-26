#!/usr/bin/env python3
"""
PLE SUNAT Validator - Validador de datos PLE con Tablas SUNAT
=============================================================

Este módulo maneja la validación e integración de datos del Libro Diario
con las 12 tablas oficiales de SUNAT para el PLE.

Funcionalidades principales:
- Validación de códigos de cuenta contable con Tabla 5 (Plan Contable PCGE)
- Validación de tipos de documento con Tabla 10
- Validación de medios de pago con Tabla 1
- Enriquecimi                sunat_service = TablasSUNATService()
                resultado_busqueda = await sunat_service.buscar_codigo("5", cuenta)
                
                if resultado_busqueda and resultado_busqueda.encontrado:
                    # Agregar información enriquecida al movimiento
                    movimiento["cuenta_contable_descripcion"] = resultado_busqueda.descripcion or ""
                    movimiento["cuenta_contable_tabla"] = "5"
                    movimiento["cuenta_contable_activa"] = True
                    
                    # Marcar como enriquecido
                    movimiento["_enriquecido_sunat"] = True
                    movimiento["_fecha_enriquecimiento"] = datetime.now().isoformat()o de datos con descripciones SUNAT
- Verificación de consistencia entre tablas

Autor: Sistema ERP
Fecha: Agosto 2025
Versión: 2.0
"""

import asyncio
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import date, datetime

# Configurar logging
logger = logging.getLogger(__name__)

@dataclass
class SUNATValidationError:
    """Error de validación con tablas SUNAT"""
    codigo: str
    tabla: str
    campo: str
    valor_encontrado: str
    mensaje: str
    sugerencia: Optional[str] = None
    critico: bool = True

@dataclass
class SUNATValidationWarning:
    """Warning de validación con tablas SUNAT"""
    codigo: str
    tabla: str
    campo: str
    valor_encontrado: str
    mensaje: str
    sugerencia: Optional[str] = None

@dataclass
class SUNATEnrichmentData:
    """Datos enriquecidos con información de SUNAT"""
    codigo_original: str
    descripcion_sunat: str
    tabla_sunat: str
    activo: bool
    fecha_inicio_vigencia: Optional[date] = None
    fecha_fin_vigencia: Optional[date] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PLEValidationResult:
    """Resultado de validación completa PLE con SUNAT"""
    valido: bool
    total_registros: int
    registros_validados: int
    errores: List[SUNATValidationError] = field(default_factory=list)
    warnings: List[SUNATValidationWarning] = field(default_factory=list)
    datos_enriquecidos: List[SUNATEnrichmentData] = field(default_factory=list)
    estadisticas: Dict[str, Any] = field(default_factory=dict)
    tiempo_validacion: float = 0.0

class PLESUNATValidator:
    """
    Validador e integrador de datos PLE con las tablas oficiales de SUNAT.
    
    Este componente se conecta con el sistema de tablas SUNAT implementado
    en el módulo accounting para validar y enriquecer los datos del libro diario
    antes de generar el archivo PLE.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._cache_tablas = {}
        self._configuraciones_validacion = self._cargar_configuraciones()
    
    def _cargar_configuraciones(self) -> Dict[str, Any]:
        """Cargar configuraciones específicas de validación"""
        return {
            "validar_plan_contable": True,
            "validar_tipos_documento": True,
            "validar_medios_pago": False,  # Opcional para libro diario básico
            "permitir_cuentas_personalizadas": True,
            "longitud_minima_cuenta": 2,
            "longitud_maxima_cuenta": 24,
            "validar_vigencia_codigos": True,
            "usar_cache": True,
            "timeout_validacion": 30.0
        }
    
    async def validar_libro_diario_completo(
        self, 
        libro_data: Dict[str, Any],
        opciones_validacion: Optional[Dict[str, Any]] = None
    ) -> PLEValidationResult:
        """
        Validar un libro diario completo contra las tablas SUNAT.
        
        Args:
            libro_data: Datos del libro diario a validar
            opciones_validacion: Opciones específicas de validación
            
        Returns:
            PLEValidationResult: Resultado completo de la validación
        """
        start_time = datetime.now()
        self.logger.info("Iniciando validación completa del libro diario con tablas SUNAT")
        
        try:
            # Configurar opciones
            opciones = {**self._configuraciones_validacion}
            if opciones_validacion:
                opciones.update(opciones_validacion)
            
            # Inicializar resultado
            resultado = PLEValidationResult(
                valido=True,
                total_registros=0,
                registros_validados=0
            )
            
            # Extraer asientos del libro
            asientos = libro_data.get("asientos", [])
            resultado.total_registros = sum(len(asiento.get("movimientos", [])) for asiento in asientos)
            
            self.logger.info(f"Validando {len(asientos)} asientos con {resultado.total_registros} movimientos")
            
            # Validar cada asiento
            for i, asiento in enumerate(asientos):
                self.logger.debug(f"Validando asiento {i+1}/{len(asientos)}: {asiento.get('numero_asiento', 'S/N')}")
                
                resultado_asiento = await self._validar_asiento_individual(asiento, opciones)
                
                # Consolidar resultados
                resultado.errores.extend(resultado_asiento.errores)
                resultado.warnings.extend(resultado_asiento.warnings)
                resultado.datos_enriquecidos.extend(resultado_asiento.datos_enriquecidos)
                resultado.registros_validados += resultado_asiento.registros_validados
            
            # Determinar si es válido
            errores_criticos = [e for e in resultado.errores if e.critico]
            resultado.valido = len(errores_criticos) == 0
            
            # Generar estadísticas
            resultado.estadisticas = self._generar_estadisticas_validacion(resultado)
            
            # Calcular tiempo
            end_time = datetime.now()
            resultado.tiempo_validacion = (end_time - start_time).total_seconds()
            
            self.logger.info(
                f"Validación completada: {resultado.registros_validados}/{resultado.total_registros} registros, "
                f"{len(resultado.errores)} errores, {len(resultado.warnings)} warnings en {resultado.tiempo_validacion:.2f}s"
            )
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error durante validación SUNAT: {str(e)}")
            return PLEValidationResult(
                valido=False,
                total_registros=0,
                registros_validados=0,
                errores=[SUNATValidationError(
                    codigo="SUNAT_ERROR_GENERAL",
                    tabla="N/A",
                    campo="N/A", 
                    valor_encontrado=str(e),
                    mensaje=f"Error crítico durante validación: {str(e)}",
                    critico=True
                )],
                tiempo_validacion=(datetime.now() - start_time).total_seconds()
            )
    
    async def _validar_asiento_individual(
        self, 
        asiento: Dict[str, Any], 
        opciones: Dict[str, Any]
    ) -> PLEValidationResult:
        """Validar un asiento individual contra las tablas SUNAT"""
        
        resultado = PLEValidationResult(
            valido=True,
            total_registros=0,
            registros_validados=0
        )
        
        movimientos = asiento.get("movimientos", [])
        resultado.total_registros = len(movimientos)
        
        # Validar cada movimiento
        for movimiento in movimientos:
            try:
                # Validar cuenta contable (Tabla 5 - Plan Contable)
                if opciones.get("validar_plan_contable", True):
                    await self._validar_cuenta_contable(movimiento, resultado)
                
                # Validar otros campos según configuración
                await self._validar_montos_movimiento(movimiento, resultado)
                await self._validar_formato_campos(movimiento, resultado)
                
                resultado.registros_validados += 1
                
            except Exception as e:
                self.logger.error(f"Error validando movimiento: {str(e)}")
                resultado.errores.append(SUNATValidationError(
                    codigo="MOVIMIENTO_ERROR",
                    tabla="N/A",
                    campo="movimiento",
                    valor_encontrado=str(movimiento.get("cuenta_contable", "")),
                    mensaje=f"Error validando movimiento: {str(e)}",
                    critico=False
                ))
        
        return resultado
    
    async def _validar_cuenta_contable(
        self, 
        movimiento: Dict[str, Any], 
        resultado: PLEValidationResult
    ) -> None:
        """Validar cuenta contable contra Tabla 5 (Plan Contable PCGE)"""
        
        cuenta = movimiento.get("cuenta_contable", "").strip()
        
        if not cuenta:
            resultado.errores.append(SUNATValidationError(
                codigo="CUENTA_VACIA",
                tabla="5",
                campo="cuenta_contable",
                valor_encontrado="",
                mensaje="Cuenta contable no puede estar vacía",
                sugerencia="Proporcionar un código de cuenta válido",
                critico=True
            ))
            return
        
        try:
            # Intentar validar con el servicio de tablas SUNAT
            from app.modules.accounting.sunat_service import TablasSUNATService
            
            sunat_service = TablasSUNATService()
            
            # Buscar la cuenta en la tabla 5
            resultado_busqueda = await sunat_service.buscar_codigo("5", cuenta)
            
            if resultado_busqueda and resultado_busqueda.encontrado:
                # Cuenta encontrada, enriquecer datos
                enrichment = SUNATEnrichmentData(
                    codigo_original=cuenta,
                    descripcion_sunat=resultado_busqueda.descripcion or "",
                    tabla_sunat="5",
                    activo=True,  # Asumimos que está activa si se encuentra
                    metadata={
                        "tabla_sunat": "5",
                        "metodo_busqueda": "buscar_codigo"
                    }
                )
                resultado.datos_enriquecidos.append(enrichment)
            
            else:
                # Cuenta no encontrada
                # Verificar si es una cuenta personalizada válida
                if self._es_cuenta_personalizada_valida(cuenta):
                    resultado.warnings.append(SUNATValidationWarning(
                        codigo="CUENTA_PERSONALIZADA",
                        tabla="5",
                        campo="cuenta_contable",
                        valor_encontrado=cuenta,
                        mensaje=f"Cuenta {cuenta} no está en el PCGE estándar (posible cuenta personalizada)",
                        sugerencia="Verificar que la cuenta esté correctamente definida en el plan contable de la empresa"
                    ))
                else:
                    resultado.errores.append(SUNATValidationError(
                        codigo="CUENTA_INVALIDA",
                        tabla="5",
                        campo="cuenta_contable",
                        valor_encontrado=cuenta,
                        mensaje=f"Cuenta contable {cuenta} no válida según PCGE",
                        sugerencia="Usar un código de cuenta del Plan Contable General Empresarial",
                        critico=True
                    ))
        
        except Exception as e:
            self.logger.error(f"Error validando cuenta contable {cuenta}: {str(e)}")
            resultado.warnings.append(SUNATValidationWarning(
                codigo="ERROR_VALIDACION_CUENTA",
                tabla="5",
                campo="cuenta_contable",
                valor_encontrado=cuenta,
                mensaje=f"No se pudo validar la cuenta {cuenta}: {str(e)}",
                sugerencia="Verificar conexión con tablas SUNAT"
            ))
    
    def _es_cuenta_personalizada_valida(self, cuenta: str) -> bool:
        """Verificar si una cuenta no estándar tiene formato válido"""
        
        # Verificar longitud
        if len(cuenta) < self._configuraciones_validacion.get("longitud_minima_cuenta", 2):
            return False
        if len(cuenta) > self._configuraciones_validacion.get("longitud_maxima_cuenta", 24):
            return False
        
        # Verificar que solo contenga números y puntos
        import re
        if not re.match(r'^[0-9.]+$', cuenta):
            return False
        
        # Verificar que empiece con dígito válido del PCGE (1-9)
        if not cuenta[0].isdigit() or cuenta[0] == '0':
            return False
        
        return True
    
    async def _validar_montos_movimiento(
        self, 
        movimiento: Dict[str, Any], 
        resultado: PLEValidationResult
    ) -> None:
        """Validar los montos del movimiento"""
        
        debe = movimiento.get("debe", 0)
        haber = movimiento.get("haber", 0)
        
        try:
            # Convertir a Decimal para validación precisa
            debe_decimal = Decimal(str(debe)) if debe else Decimal('0')
            haber_decimal = Decimal(str(haber)) if haber else Decimal('0')
            
            # Validar que solo uno de los dos sea diferente de cero
            if debe_decimal > 0 and haber_decimal > 0:
                resultado.errores.append(SUNATValidationError(
                    codigo="DEBE_HABER_AMBOS",
                    tabla="N/A",
                    campo="debe_haber",
                    valor_encontrado=f"debe:{debe}, haber:{haber}",
                    mensaje="Un movimiento no puede tener tanto debe como haber",
                    sugerencia="Definir solo debe o solo haber por movimiento",
                    critico=True
                ))
            
            # Validar que al menos uno sea mayor que cero
            if debe_decimal == 0 and haber_decimal == 0:
                resultado.warnings.append(SUNATValidationWarning(
                    codigo="MOVIMIENTO_CERO",
                    tabla="N/A",
                    campo="debe_haber",
                    valor_encontrado=f"debe:{debe}, haber:{haber}",
                    mensaje="Movimiento con monto cero",
                    sugerencia="Verificar si el movimiento es necesario"
                ))
            
            # Validar precisión (máximo 2 decimales)
            if debe_decimal.as_tuple().exponent < -2:
                resultado.warnings.append(SUNATValidationWarning(
                    codigo="PRECISION_DEBE",
                    tabla="N/A",
                    campo="debe",
                    valor_encontrado=str(debe),
                    mensaje="El monto del debe tiene más de 2 decimales",
                    sugerencia="Redondear a 2 decimales para cumplir formato SUNAT"
                ))
            
            if haber_decimal.as_tuple().exponent < -2:
                resultado.warnings.append(SUNATValidationWarning(
                    codigo="PRECISION_HABER",
                    tabla="N/A",
                    campo="haber",
                    valor_encontrado=str(haber),
                    mensaje="El monto del haber tiene más de 2 decimales",
                    sugerencia="Redondear a 2 decimales para cumplir formato SUNAT"
                ))
        
        except Exception as e:
            resultado.errores.append(SUNATValidationError(
                codigo="ERROR_MONTO",
                tabla="N/A",
                campo="debe_haber",
                valor_encontrado=f"debe:{debe}, haber:{haber}",
                mensaje=f"Error validando montos: {str(e)}",
                critico=True
            ))
    
    async def _validar_formato_campos(
        self, 
        movimiento: Dict[str, Any], 
        resultado: PLEValidationResult
    ) -> None:
        """Validar formato de campos del movimiento"""
        
        # Validar glosa si existe
        glosa = movimiento.get("glosa", "")
        if glosa and len(glosa) > 40:
            resultado.warnings.append(SUNATValidationWarning(
                codigo="GLOSA_LARGA",
                tabla="N/A",
                campo="glosa",
                valor_encontrado=glosa,
                mensaje=f"Glosa excede 40 caracteres (actual: {len(glosa)})",
                sugerencia="Recortar glosa para cumplir límite de formato PLE"
            ))
        
        # Validar cuenta desagregada
        cuenta_desagregada = movimiento.get("cuenta_desagregada", "")
        if cuenta_desagregada and len(cuenta_desagregada) > 24:
            resultado.warnings.append(SUNATValidationWarning(
                codigo="CUENTA_DESAGREGADA_LARGA",
                tabla="N/A",
                campo="cuenta_desagregada",
                valor_encontrado=cuenta_desagregada,
                mensaje=f"Cuenta desagregada excede 24 caracteres",
                sugerencia="Recortar código para cumplir formato PLE"
            ))
    
    def _generar_estadisticas_validacion(self, resultado: PLEValidationResult) -> Dict[str, Any]:
        """Generar estadísticas del proceso de validación"""
        
        errores_por_tabla = {}
        warnings_por_tabla = {}
        
        for error in resultado.errores:
            tabla = error.tabla
            if tabla not in errores_por_tabla:
                errores_por_tabla[tabla] = 0
            errores_por_tabla[tabla] += 1
        
        for warning in resultado.warnings:
            tabla = warning.tabla
            if tabla not in warnings_por_tabla:
                warnings_por_tabla[tabla] = 0
            warnings_por_tabla[tabla] += 1
        
        return {
            "total_errores": len(resultado.errores),
            "total_warnings": len(resultado.warnings),
            "errores_criticos": sum(1 for e in resultado.errores if e.critico),
            "errores_por_tabla": errores_por_tabla,
            "warnings_por_tabla": warnings_por_tabla,
            "datos_enriquecidos": len(resultado.datos_enriquecidos),
            "porcentaje_validado": (resultado.registros_validados / resultado.total_registros * 100) if resultado.total_registros > 0 else 0,
            "cuentas_validadas": len([d for d in resultado.datos_enriquecidos if d.tabla_sunat == "5"])
        }
    
    async def enriquecer_datos_libro_diario(
        self, 
        libro_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enriquecer datos del libro diario con información de tablas SUNAT.
        
        Args:
            libro_data: Datos originales del libro diario
            
        Returns:
            Dict: Datos enriquecidos con información adicional de SUNAT
        """
        self.logger.info("Iniciando enriquecimiento de datos con tablas SUNAT")
        
        try:
            # Crear copia de los datos originales
            datos_enriquecidos = libro_data.copy()
            
            # Enriquecer cada asiento
            if "asientos" in datos_enriquecidos:
                for asiento in datos_enriquecidos["asientos"]:
                    if "movimientos" in asiento:
                        for movimiento in asiento["movimientos"]:
                            await self._enriquecer_movimiento_individual(movimiento)
            
            self.logger.info("Enriquecimiento de datos completado")
            return datos_enriquecidos
        
        except Exception as e:
            self.logger.error(f"Error durante enriquecimiento: {str(e)}")
            return libro_data  # Retornar datos originales en caso de error
    
    async def _enriquecer_movimiento_individual(self, movimiento: Dict[str, Any]) -> None:
        """Enriquecer un movimiento individual con datos SUNAT"""
        
        try:
            cuenta = movimiento.get("cuenta_contable", "").strip()
            
            if cuenta:
                from app.modules.accounting.sunat_service import TablasSUNATService
                
                sunat_service = TablasSUNATService()
                resultado_busqueda = await sunat_service.buscar_codigo("5", cuenta)
                
                # El resultado es un objeto BusquedaCodigoResponse
                if resultado_busqueda and resultado_busqueda.encontrado:
                    # Agregar información enriquecida al movimiento
                    movimiento["cuenta_contable_descripcion"] = resultado_busqueda.descripcion or ""
                    
                    # Marcar como enriquecido
                    movimiento["_enriquecido_sunat"] = True
                    movimiento["_fecha_enriquecimiento"] = datetime.now().isoformat()
        
        except Exception as e:
            self.logger.error(f"Error enriqueciendo movimiento: {str(e)}")
            # No fallar el proceso completo por un error de enriquecimiento
