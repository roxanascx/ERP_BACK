"""
Servicio de negocio para tablas SUNAT
====================================

Lógica de negocio para el manejo de las tablas de códigos SUNAT
necesarias para la generación de archivos PLE.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.modules.accounting.sunat_models import TablasSUNATRepository
from app.modules.accounting.sunat_schemas import (
    TablaSUNATResponse,
    BusquedaCodigoResponse,
    BusquedaDescripcionResponse,
    ValidacionCodigoResponse,
    EstadisticasTablasResponse,
    ListadoDocumentosResponse,
    ListadoComprobantesResponse,
    ListadoLibrosResponse,
    ListadoMonedasResponse,
    InicializacionTablasSUNATResponse,
    AutocompleteResponse,
    AutocompleteItem,
    DocumentoIdentidadItem,
    ComprobantePagoItem,
    LibroRegistroItem,
    MonedaItem
)

logger = logging.getLogger(__name__)


class TablasSUNATService:
    """Servicio de lógica de negocio para tablas SUNAT"""
    
    def __init__(self):
        self.repository = TablasSUNATRepository()
    
    # ================================
    # OPERACIONES DE INICIALIZACIÓN
    # ================================
    
    async def inicializar_tablas(self, forzar_reinicio: bool = False) -> InicializacionTablasSUNATResponse:
        """Inicializar todas las tablas SUNAT"""
        try:
            # Si se fuerza el reinicio, eliminar tablas existentes
            if forzar_reinicio:
                # TODO: Implementar eliminación de tablas existentes
                pass
            
            # Inicializar tablas
            exitoso = await self.repository.inicializar_todas_las_tablas()
            
            if exitoso:
                # Obtener estadísticas post-inicialización
                stats = await self.repository.obtener_estadisticas_tablas()
                
                return InicializacionTablasSUNATResponse(
                    exitoso=True,
                    mensaje="Tablas SUNAT inicializadas correctamente",
                    tablas_inicializadas=[
                        "tipos_documento_identidad",
                        "codigos_libros_registros",
                        "tipos_comprobantes_pago", 
                        "entidades_financieras",
                        "tipos_moneda",
                        "tipos_existencias",
                        "unidades_medida",
                        "tipos_intangibles",
                        "tipos_operacion_inventario"
                    ],
                    total_tablas=stats.get("tablas_activas", 0),
                    fecha_inicializacion=datetime.utcnow()
                )
            else:
                return InicializacionTablasSUNATResponse(
                    exitoso=False,
                    mensaje="Error al inicializar las tablas SUNAT",
                    tablas_inicializadas=[],
                    total_tablas=0,
                    errores=["Error desconocido en la inicialización"],
                    fecha_inicializacion=datetime.utcnow()
                )
                
        except Exception as e:
            logger.error(f"Error en inicialización de tablas: {str(e)}")
            return InicializacionTablasSUNATResponse(
                exitoso=False,
                mensaje=f"Error al inicializar tablas: {str(e)}",
                tablas_inicializadas=[],
                total_tablas=0,
                errores=[str(e)],
                fecha_inicializacion=datetime.utcnow()
            )
    
    # ================================
    # OPERACIONES DE CONSULTA
    # ================================
    
    async def buscar_codigo(self, tabla: str, codigo: str) -> BusquedaCodigoResponse:
        """Buscar un código específico en una tabla"""
        try:
            descripcion = await self.repository.obtener_descripcion_documento(codigo) if tabla == "tipos_documento_identidad" \
                         else await self.repository.obtener_descripcion_comprobante(codigo) if tabla == "tipos_comprobantes_pago" \
                         else await self.repository.obtener_descripcion_libro(codigo) if tabla == "codigos_libros_registros" \
                         else await self.repository.model.buscar_codigo(tabla, codigo)
            
            return BusquedaCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                descripcion=descripcion,
                encontrado=descripcion is not None
            )
            
        except Exception as e:
            logger.error(f"Error al buscar código {codigo} en tabla {tabla}: {str(e)}")
            return BusquedaCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                descripcion=None,
                encontrado=False
            )
    
    async def buscar_por_descripcion(self, tabla: str, descripcion: str) -> BusquedaDescripcionResponse:
        """Buscar códigos por descripción parcial"""
        try:
            resultados = await self.repository.model.buscar_por_descripcion(tabla, descripcion)
            
            return BusquedaDescripcionResponse(
                tabla=tabla,
                descripcion_buscada=descripcion,
                resultados=resultados,
                total_encontrados=len(resultados)
            )
            
        except Exception as e:
            logger.error(f"Error en búsqueda por descripción en tabla {tabla}: {str(e)}")
            return BusquedaDescripcionResponse(
                tabla=tabla,
                descripcion_buscada=descripcion,
                resultados=[],
                total_encontrados=0
            )
    
    async def validar_codigo(self, tabla: str, codigo: str) -> ValidacionCodigoResponse:
        """Validar si un código es válido en una tabla"""
        try:
            if tabla == "tipos_documento_identidad":
                valido = await self.repository.validar_documento_identidad(codigo)
                descripcion = await self.repository.obtener_descripcion_documento(codigo) if valido else None
            elif tabla == "tipos_comprobantes_pago":
                valido = await self.repository.validar_comprobante_pago(codigo)
                descripcion = await self.repository.obtener_descripcion_comprobante(codigo) if valido else None
            elif tabla == "codigos_libros_registros":
                valido = await self.repository.validar_codigo_libro(codigo)
                descripcion = await self.repository.obtener_descripcion_libro(codigo) if valido else None
            else:
                valido = await self.repository.model.validar_codigo(tabla, codigo)
                descripcion = await self.repository.model.buscar_codigo(tabla, codigo) if valido else None
            
            mensaje = "Código válido" if valido else f"Código '{codigo}' no encontrado en tabla '{tabla}'"
            
            return ValidacionCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                valido=valido,
                descripcion=descripcion,
                mensaje=mensaje
            )
            
        except Exception as e:
            logger.error(f"Error al validar código {codigo} en tabla {tabla}: {str(e)}")
            return ValidacionCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                valido=False,
                descripcion=None,
                mensaje=f"Error en validación: {str(e)}"
            )
    
    # ================================
    # OPERACIONES DE LISTADO
    # ================================
    
    async def listar_documentos_identidad(self) -> ListadoDocumentosResponse:
        """Listar todos los tipos de documento de identidad"""
        try:
            datos = await self.repository.obtener_tipos_documento_identidad()
            
            items = [
                DocumentoIdentidadItem(codigo=codigo, descripcion=descripcion)
                for codigo, descripcion in datos.items()
            ]
            
            return ListadoDocumentosResponse(
                items=items,
                total=len(items)
            )
            
        except Exception as e:
            logger.error(f"Error al listar documentos de identidad: {str(e)}")
            return ListadoDocumentosResponse(items=[], total=0)
    
    async def listar_comprobantes_pago(self) -> ListadoComprobantesResponse:
        """Listar todos los tipos de comprobantes de pago"""
        try:
            datos = await self.repository.obtener_tipos_comprobantes_pago()
            
            items = [
                ComprobantePagoItem(codigo=codigo, descripcion=descripcion)
                for codigo, descripcion in datos.items()
            ]
            
            return ListadoComprobantesResponse(
                items=items,
                total=len(items)
            )
            
        except Exception as e:
            logger.error(f"Error al listar comprobantes de pago: {str(e)}")
            return ListadoComprobantesResponse(items=[], total=0)
    
    async def listar_libros_registros(self) -> ListadoLibrosResponse:
        """Listar todos los códigos de libros y registros"""
        try:
            datos = await self.repository.obtener_codigos_libros_registros()
            
            items = [
                LibroRegistroItem(codigo=codigo, descripcion=descripcion)
                for codigo, descripcion in datos.items()
            ]
            
            return ListadoLibrosResponse(
                items=items,
                total=len(items)
            )
            
        except Exception as e:
            logger.error(f"Error al listar libros y registros: {str(e)}")
            return ListadoLibrosResponse(items=[], total=0)
    
    async def listar_tipos_moneda(self) -> ListadoMonedasResponse:
        """Listar todos los tipos de moneda"""
        try:
            datos = await self.repository.obtener_tipos_moneda()
            
            items = [
                MonedaItem(codigo=codigo, descripcion=descripcion)
                for codigo, descripcion in datos.items()
            ]
            
            return ListadoMonedasResponse(
                items=items,
                total=len(items)
            )
            
        except Exception as e:
            logger.error(f"Error al listar tipos de moneda: {str(e)}")
            return ListadoMonedasResponse(items=[], total=0)
    
    # ================================
    # OPERACIONES DE AUTOCOMPLETADO
    # ================================
    
    async def autocomplete(self, tabla: str, termino: str, limite: int = 10) -> AutocompleteResponse:
        """Autocompletado para búsquedas en tablas"""
        try:
            # Buscar por descripción parcial
            resultados_descripcion = await self.repository.model.buscar_por_descripcion(tabla, termino)
            
            # Convertir a items de autocompletado
            items = []
            termino_lower = termino.lower()
            
            for resultado in resultados_descripcion[:limite]:
                # Determinar qué parte coincide
                descripcion = resultado["descripcion"].lower()
                if termino_lower in descripcion:
                    inicio = descripcion.find(termino_lower)
                    coincidencia = resultado["descripcion"][inicio:inicio+len(termino)]
                else:
                    coincidencia = termino
                
                items.append(AutocompleteItem(
                    codigo=resultado["codigo"],
                    descripcion=resultado["descripcion"],
                    coincidencia=coincidencia
                ))
            
            return AutocompleteResponse(
                tabla=tabla,
                termino=termino,
                resultados=items,
                total_encontrados=len(resultados_descripcion),
                limite_aplicado=limite
            )
            
        except Exception as e:
            logger.error(f"Error en autocompletado para tabla {tabla}: {str(e)}")
            return AutocompleteResponse(
                tabla=tabla,
                termino=termino,
                resultados=[],
                total_encontrados=0,
                limite_aplicado=limite
            )
    
    # ================================
    # OPERACIONES DE ESTADÍSTICAS
    # ================================
    
    async def obtener_estadisticas(self) -> EstadisticasTablasResponse:
        """Obtener estadísticas de las tablas SUNAT"""
        try:
            stats = await self.repository.obtener_estadisticas_tablas()
            
            # Convertir a formato de respuesta
            return EstadisticasTablasResponse(**stats)
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return EstadisticasTablasResponse(
                total_tablas=0,
                tablas_activas=0,
                tablas_detalle=[],
                fecha_consulta=datetime.utcnow()
            )
    
    # ================================
    # OPERACIONES DE UTILIDAD
    # ================================
    
    async def verificar_integridad_tablas(self) -> Dict[str, Any]:
        """Verificar la integridad de todas las tablas"""
        try:
            integridad = {
                "tablas_verificadas": [],
                "errores": [],
                "warnings": [],
                "estado_general": "OK"
            }
            
            # Lista de tablas críticas
            tablas_criticas = [
                "tipos_documento_identidad",
                "tipos_comprobantes_pago",
                "codigos_libros_registros"
            ]
            
            for tabla in tablas_criticas:
                try:
                    datos = await self.repository.model.obtener_datos_tabla(tabla)
                    if datos:
                        integridad["tablas_verificadas"].append({
                            "tabla": tabla,
                            "total_codigos": len(datos),
                            "estado": "OK"
                        })
                    else:
                        integridad["errores"].append(f"Tabla {tabla} no encontrada o vacía")
                        integridad["estado_general"] = "ERROR"
                        
                except Exception as e:
                    integridad["errores"].append(f"Error al verificar tabla {tabla}: {str(e)}")
                    integridad["estado_general"] = "ERROR"
            
            # Verificar códigos críticos específicos
            verificaciones_criticas = [
                ("tipos_documento_identidad", "6", "RUC"),
                ("tipos_comprobantes_pago", "01", "FACTURA"),
                ("codigos_libros_registros", "05", "LIBRO DIARIO")
            ]
            
            for tabla, codigo, descripcion_esperada in verificaciones_criticas:
                try:
                    descripcion = await self.repository.model.buscar_codigo(tabla, codigo)
                    if not descripcion:
                        integridad["errores"].append(f"Código crítico {codigo} no encontrado en {tabla}")
                        integridad["estado_general"] = "ERROR"
                    elif descripcion_esperada.lower() not in descripcion.lower():
                        integridad["warnings"].append(f"Descripción inesperada para código {codigo} en {tabla}")
                        
                except Exception as e:
                    integridad["errores"].append(f"Error al verificar código {codigo} en {tabla}: {str(e)}")
            
            return integridad
            
        except Exception as e:
            logger.error(f"Error en verificación de integridad: {str(e)}")
            return {
                "tablas_verificadas": [],
                "errores": [f"Error general: {str(e)}"],
                "warnings": [],
                "estado_general": "ERROR"
            }
    
    # ================================
    # OPERACIONES ESPECÍFICAS PARA PLE
    # ================================
    
    async def obtener_codigos_para_ple(self) -> Dict[str, Dict[str, str]]:
        """Obtener todas las tablas necesarias para generación de PLE"""
        try:
            resultado = {}
            
            # Tablas críticas para PLE
            tablas_ple = [
                "tipos_documento_identidad",
                "tipos_comprobantes_pago", 
                "codigos_libros_registros",
                "tipos_moneda"
            ]
            
            for tabla in tablas_ple:
                datos = await self.repository.model.obtener_datos_tabla(tabla)
                if datos:
                    resultado[tabla] = datos
                else:
                    logger.warning(f"Tabla {tabla} no disponible para PLE")
                    resultado[tabla] = {}
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al obtener códigos para PLE: {str(e)}")
            return {}
    
    async def validar_datos_para_ple(self, datos_asiento: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos de un asiento para generación de PLE"""
        try:
            validacion = {
                "valido": True,
                "errores": [],
                "warnings": []
            }
            
            # Validar código de cuenta contable (si está presente)
            if "codigoCuenta" in datos_asiento:
                # TODO: Validar contra plan contable
                pass
            
            # Validar tipo de comprobante (si está presente)
            if "tipoComprobante" in datos_asiento:
                valido = await self.repository.validar_comprobante_pago(datos_asiento["tipoComprobante"])
                if not valido:
                    validacion["errores"].append(f"Tipo de comprobante inválido: {datos_asiento['tipoComprobante']}")
                    validacion["valido"] = False
            
            # Validar tipo de documento (si está presente)
            if "tipoDocumento" in datos_asiento:
                valido = await self.repository.validar_documento_identidad(datos_asiento["tipoDocumento"])
                if not valido:
                    validacion["errores"].append(f"Tipo de documento inválido: {datos_asiento['tipoDocumento']}")
                    validacion["valido"] = False
            
            return validacion
            
        except Exception as e:
            logger.error(f"Error en validación para PLE: {str(e)}")
            return {
                "valido": False,
                "errores": [f"Error en validación: {str(e)}"],
                "warnings": []
            }
