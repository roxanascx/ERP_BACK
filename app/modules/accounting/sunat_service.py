"""
Servicio para las tablas SUNAT
==============================

Lógica de negocio para el manejo de las 12 tablas de códigos SUNAT.
Incluye operaciones de búsqueda, validación, autocompletado y PLE.

Autor: Sistema ERP
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.modules.accounting.sunat_models import TablasSUNATRepository
from app.modules.accounting.sunat_schemas import (
    InicializacionResponse,
    BusquedaCodigoResponse,
    BusquedaDescripcionResponse,
    ValidacionCodigoResponse,
    AutocompleteResponse,
    EstadisticasTablasResponse,
    EstadisticasTablaDetalle,
    ListadoDocumentosResponse,
    ListadoComprobantesResponse,
    ListadoLibrosResponse,
    ListadoMonedasResponse,
    ValidacionMasivaResponse,
    DocumentoIdentidadItem,
    ComprobantePagoItem,
    LibroRegistroItem,
    MonedaItem
)

logger = logging.getLogger(__name__)


class TablasSUNATService:
    """Servicio para manejar todas las operaciones de las tablas SUNAT"""
    
    def __init__(self):
        self.repository = TablasSUNATRepository()
    
    # ================================
    # OPERACIONES GENERALES
    # ================================
    
    async def inicializar_tablas(self) -> InicializacionResponse:
        """Inicializar todas las 12 tablas SUNAT"""
        try:
            resultado = await self.repository.inicializar_tablas()
            
            return InicializacionResponse(
                exitoso=resultado["exitoso"],
                mensaje=resultado["mensaje"],
                total_tablas=resultado["total_tablas"],
                tablas_creadas=resultado.get("tablas_creadas", 0),
                tablas_actualizadas=resultado.get("tablas_actualizadas", 0),
                fecha_inicializacion=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error en inicializar_tablas: {str(e)}")
            return InicializacionResponse(
                exitoso=False,
                mensaje=f"Error al inicializar tablas: {str(e)}",
                total_tablas=0,
                fecha_inicializacion=datetime.utcnow()
            )
    
    async def buscar_codigo(self, tabla: str, codigo: str) -> BusquedaCodigoResponse:
        """Buscar un código específico en una tabla"""
        try:
            resultado = await self.repository.buscar_codigo(tabla, codigo)
            
            return BusquedaCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                descripcion=resultado.get("descripcion"),
                encontrado=resultado.get("encontrado", False)
            )
            
        except Exception as e:
            logger.error(f"Error en buscar_codigo: {str(e)}")
            return BusquedaCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                encontrado=False
            )
    
    async def validar_codigo(self, tabla: str, codigo: str) -> ValidacionCodigoResponse:
        """Validar si un código existe en una tabla"""
        try:
            resultado = await self.repository.validar_codigo(tabla, codigo)
            
            return ValidacionCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                valido=resultado.get("valido", False),
                mensaje=resultado.get("mensaje", "")
            )
            
        except Exception as e:
            logger.error(f"Error en validar_codigo: {str(e)}")
            return ValidacionCodigoResponse(
                tabla=tabla,
                codigo=codigo,
                valido=False,
                mensaje=f"Error en validación: {str(e)}"
            )
    
    async def buscar_por_descripcion(self, tabla: str, descripcion: str) -> BusquedaDescripcionResponse:
        """Buscar códigos por descripción parcial"""
        try:
            resultado = await self.repository.buscar_por_descripcion(tabla, descripcion)
            
            return BusquedaDescripcionResponse(
                tabla=tabla,
                descripcion=descripcion,
                resultados=resultado.get("resultados", []),
                total_encontrados=resultado.get("total_encontrados", 0)
            )
            
        except Exception as e:
            logger.error(f"Error en buscar_por_descripcion: {str(e)}")
            return BusquedaDescripcionResponse(
                tabla=tabla,
                descripcion=descripcion,
                resultados=[],
                total_encontrados=0
            )
    
    async def autocomplete(self, tabla: str, termino: str, limite: int = 10) -> AutocompleteResponse:
        """Autocompletado de códigos por descripción"""
        try:
            resultado = await self.repository.autocomplete(tabla, termino, limite)
            
            return AutocompleteResponse(
                tabla=tabla,
                termino=termino,
                resultados=resultado.get("resultados", []),
                total_encontrados=resultado.get("total_encontrados", 0),
                limite=limite
            )
            
        except Exception as e:
            logger.error(f"Error en autocomplete: {str(e)}")
            return AutocompleteResponse(
                tabla=tabla,
                termino=termino,
                resultados=[],
                total_encontrados=0,
                limite=limite
            )
    
    # ================================
    # LISTADOS ESPECÍFICOS POR TABLA
    # ================================
    
    async def listar_documentos_identidad(self) -> ListadoDocumentosResponse:
        """Listar todos los tipos de documentos de identidad"""
        try:
            resultado = await self.repository.listar_tabla_completa("tipos_documento_identidad")
            items = [DocumentoIdentidadItem(**item) for item in resultado["items"]]
            
            return ListadoDocumentosResponse(
                tabla="tipos_documento_identidad",
                items=items,
                total=resultado["total"]
            )
            
        except Exception as e:
            logger.error(f"Error al listar documentos de identidad: {str(e)}")
            return ListadoDocumentosResponse(tabla="tipos_documento_identidad", items=[], total=0)
    
    async def listar_comprobantes_pago(self) -> ListadoComprobantesResponse:
        """Listar todos los tipos de comprobantes de pago"""
        try:
            resultado = await self.repository.listar_tabla_completa("tipos_comprobantes_pago")
            items = [ComprobantePagoItem(**item) for item in resultado["items"]]
            
            return ListadoComprobantesResponse(
                tabla="tipos_comprobantes_pago",
                items=items,
                total=resultado["total"]
            )
            
        except Exception as e:
            logger.error(f"Error al listar comprobantes de pago: {str(e)}")
            return ListadoComprobantesResponse(tabla="tipos_comprobantes_pago", items=[], total=0)
    
    async def listar_libros_registros(self) -> ListadoLibrosResponse:
        """Listar todos los códigos de libros y registros"""
        try:
            resultado = await self.repository.listar_tabla_completa("codigos_libros_registros")
            items = [LibroRegistroItem(**item) for item in resultado["items"]]
            
            return ListadoLibrosResponse(
                tabla="codigos_libros_registros",
                items=items,
                total=resultado["total"]
            )
            
        except Exception as e:
            logger.error(f"Error al listar libros y registros: {str(e)}")
            return ListadoLibrosResponse(tabla="codigos_libros_registros", items=[], total=0)
    
    async def listar_tipos_moneda(self) -> ListadoMonedasResponse:
        """Listar todos los tipos de moneda"""
        try:
            resultado = await self.repository.listar_tabla_completa("tipos_moneda")
            items = [MonedaItem(**item) for item in resultado["items"]]
            
            return ListadoMonedasResponse(
                tabla="tipos_moneda",
                items=items,
                total=resultado["total"]
            )
            
        except Exception as e:
            logger.error(f"Error al listar tipos de moneda: {str(e)}")
            return ListadoMonedasResponse(tabla="tipos_moneda", items=[], total=0)
    
    # ================================
    # LISTADOS PARA TODAS LAS TABLAS
    # ================================
    
    async def listar_tabla_generica(self, nombre_tabla: str) -> Dict[str, Any]:
        """Listar cualquier tabla de forma genérica"""
        try:
            resultado = await self.repository.listar_tabla_completa(nombre_tabla)
            return resultado
            
        except Exception as e:
            logger.error(f"Error al listar tabla {nombre_tabla}: {str(e)}")
            return {
                "tabla": nombre_tabla,
                "items": [],
                "total": 0,
                "mensaje": f"Error: {str(e)}"
            }
    
    # ================================
    # ESTADÍSTICAS Y SALUD
    # ================================
    
    async def obtener_estadisticas(self) -> EstadisticasTablasResponse:
        """Obtener estadísticas de todas las tablas SUNAT"""
        try:
            resultado = await self.repository.obtener_estadisticas()
            
            tablas_detalle = [
                EstadisticasTablaDetalle(**detalle) 
                for detalle in resultado.get("tablas_detalle", [])
            ]
            
            return EstadisticasTablasResponse(
                total_tablas=resultado.get("total_tablas", 0),
                tablas_activas=resultado.get("tablas_activas", 0),
                tablas_detalle=tablas_detalle,
                fecha_consulta=resultado.get("fecha_consulta", datetime.utcnow())
            )
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return EstadisticasTablasResponse(
                total_tablas=0,
                tablas_activas=0,
                tablas_detalle=[],
                fecha_consulta=datetime.utcnow()
            )
    
    async def verificar_integridad_tablas(self) -> Dict[str, Any]:
        """Verificar la integridad de todas las tablas SUNAT"""
        try:
            return await self.repository.verificar_integridad()
            
        except Exception as e:
            logger.error(f"Error al verificar integridad: {str(e)}")
            return {
                "estado_general": "ERROR",
                "mensaje": f"Error en verificación: {str(e)}",
                "fecha_verificacion": datetime.utcnow()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar el estado de salud del sistema de tablas SUNAT"""
        try:
            return await self.repository.health_check()
            
        except Exception as e:
            logger.error(f"Error en health check: {str(e)}")
            return {
                "status": "ERROR",
                "mensaje": f"Error: {str(e)}",
                "timestamp": datetime.utcnow()
            }
    
    # ================================
    # VALIDACIÓN MASIVA
    # ================================
    
    async def validar_codigos_masivo(self, validaciones: List[Dict[str, str]]) -> ValidacionMasivaResponse:
        """Validar múltiples códigos de una vez"""
        try:
            resultados = []
            
            for validacion in validaciones:
                tabla = validacion.get("tabla")
                codigo = validacion.get("codigo")
                
                if not tabla or not codigo:
                    resultados.append({
                        "tabla": tabla or "",
                        "codigo": codigo or "",
                        "valido": False,
                        "mensaje": "Tabla o código faltante"
                    })
                    continue
                
                resultado_validacion = await self.validar_codigo(tabla, codigo)
                resultados.append({
                    "tabla": resultado_validacion.tabla,
                    "codigo": resultado_validacion.codigo,
                    "valido": resultado_validacion.valido,
                    "mensaje": resultado_validacion.mensaje
                })
            
            total_validos = sum(1 for r in resultados if r["valido"])
            
            return ValidacionMasivaResponse(
                total_validaciones=len(resultados),
                validaciones_exitosas=total_validos,
                validaciones_fallidas=len(resultados) - total_validos,
                resultados=resultados,
                fecha_validacion=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error en validación masiva: {str(e)}")
            return ValidacionMasivaResponse(
                total_validaciones=0,
                validaciones_exitosas=0,
                validaciones_fallidas=0,
                resultados=[],
                fecha_validacion=datetime.utcnow()
            )
    
    # ================================
    # FUNCIONES ESPECÍFICAS PARA PLE
    # ================================
    
    async def obtener_codigos_para_ple(self) -> Dict[str, Dict[str, str]]:
        """Obtener todos los códigos necesarios para generar archivos PLE"""
        try:
            # Tablas críticas para PLE
            tablas_ple = [
                "tipos_documento_identidad",
                "tipos_comprobantes_pago", 
                "codigos_libros_registros",
                "tipos_moneda",
                "tipos_medio_pago",
                "cuentas_contables"
            ]
            
            codigos_ple = {}
            
            for tabla in tablas_ple:
                resultado = await self.repository.listar_tabla_completa(tabla)
                if resultado["total"] > 0:
                    codigos_dict = {
                        item["codigo"]: item["descripcion"] 
                        for item in resultado["items"]
                    }
                    codigos_ple[tabla] = codigos_dict
            
            return codigos_ple
            
        except Exception as e:
            logger.error(f"Error al obtener códigos para PLE: {str(e)}")
            return {}
    
    async def validar_datos_para_ple(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Validar datos específicos para generación de archivos PLE"""
        try:
            validaciones = []
            errores = []
            
            # Mapeo de campos a tablas
            mapeo_campos = {
                "tipoDocumento": "tipos_documento_identidad",
                "tipoComprobante": "tipos_comprobantes_pago",
                "codigoLibro": "codigos_libros_registros", 
                "moneda": "tipos_moneda",
                "mediopago": "tipos_medio_pago"
            }
            
            for campo, tabla in mapeo_campos.items():
                if campo in datos:
                    codigo = datos[campo]
                    validacion = await self.validar_codigo(tabla, str(codigo))
                    
                    validaciones.append({
                        "campo": campo,
                        "codigo": codigo,
                        "tabla": tabla,
                        "valido": validacion.valido,
                        "mensaje": validacion.mensaje
                    })
                    
                    if not validacion.valido:
                        errores.append(f"{campo}: {validacion.mensaje}")
            
            es_valido = len(errores) == 0
            
            return {
                "valido": es_valido,
                "validaciones": validaciones,
                "errores": errores,
                "total_campos_validados": len(validaciones),
                "campos_validos": sum(1 for v in validaciones if v["valido"]),
                "fecha_validacion": datetime.utcnow(),
                "mensaje": "Datos válidos para PLE" if es_valido else f"{len(errores)} errores encontrados"
            }
            
        except Exception as e:
            logger.error(f"Error al validar datos para PLE: {str(e)}")
            return {
                "valido": False,
                "errores": [f"Error en validación: {str(e)}"],
                "mensaje": f"Error: {str(e)}",
                "fecha_validacion": datetime.utcnow()
            }
    
    # ================================
    # UTILIDADES ADICIONALES
    # ================================
    
    async def listar_todas_las_tablas_disponibles(self) -> List[str]:
        """Obtener lista de todas las tablas disponibles"""
        try:
            return await self.repository.obtener_todas_las_tablas()
        except Exception as e:
            logger.error(f"Error al listar tablas disponibles: {str(e)}")
            return []
    
    async def obtener_informacion_tabla(self, nombre_tabla: str) -> Dict[str, Any]:
        """Obtener información detallada de una tabla específica"""
        try:
            return await self.repository.listar_tabla_completa(nombre_tabla)
        except Exception as e:
            logger.error(f"Error al obtener información de tabla {nombre_tabla}: {str(e)}")
            return {
                "tabla": nombre_tabla,
                "mensaje": f"Error: {str(e)}",
                "total": 0
            }
