"""
Rutas API para tablas SUNAT
==========================

Endpoints REST para el manejo de las tablas de códigos SUNAT
necesarias para la generación de archivos PLE.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging

from app.modules.accounting.sunat_service import TablasSUNATService
from app.modules.accounting.sunat_schemas import (
    TablaSUNATResponse,
    BusquedaCodigoRequest,
    BusquedaCodigoResponse,
    BusquedaDescripcionRequest, 
    BusquedaDescripcionResponse,
    ValidacionCodigoRequest,
    ValidacionCodigoResponse,
    EstadisticasTablasResponse,
    ListadoDocumentosResponse,
    ListadoComprobantesResponse,
    ListadoLibrosResponse,
    ListadoMonedasResponse,
    InicializacionTablasSUNATRequest,
    InicializacionTablasSUNATResponse,
    AutocompleteRequest,
    AutocompleteResponse
)

logger = logging.getLogger(__name__)

# Router para las rutas de tablas SUNAT
router = APIRouter(prefix="/tablas-sunat", tags=["Tablas SUNAT"])


def get_tablas_service() -> TablasSUNATService:
    """Dependency para obtener el servicio de tablas SUNAT"""
    return TablasSUNATService()


# ================================
# ENDPOINTS DE INICIALIZACIÓN
# ================================

@router.post("/inicializar", response_model=InicializacionTablasSUNATResponse)
async def inicializar_tablas_sunat(
    request: InicializacionTablasSUNATRequest,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Inicializar todas las tablas SUNAT en la base de datos
    
    - **forzar_reinicio**: Si es True, elimina y vuelve a crear las tablas
    - **tablas_especificas**: Lista de tablas específicas a inicializar (opcional)
    """
    try:
        response = await service.inicializar_tablas(request.forzar_reinicio)
        
        if not response.exitoso:
            raise HTTPException(
                status_code=500,
                detail=f"Error al inicializar tablas: {response.mensaje}"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error en endpoint inicializar_tablas_sunat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/verificar-integridad")
async def verificar_integridad_tablas(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Verificar la integridad de todas las tablas SUNAT
    
    Retorna información sobre el estado de las tablas y posibles errores.
    """
    try:
        resultado = await service.verificar_integridad_tablas()
        return resultado
        
    except Exception as e:
        logger.error(f"Error en verificación de integridad: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar integridad: {str(e)}"
        )


# ================================
# ENDPOINTS DE CONSULTA
# ================================

@router.post("/buscar-codigo", response_model=BusquedaCodigoResponse)
async def buscar_codigo_en_tabla(
    request: BusquedaCodigoRequest,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Buscar un código específico en una tabla SUNAT
    
    - **tabla**: Nombre de la tabla donde buscar
    - **codigo**: Código a buscar
    """
    try:
        response = await service.buscar_codigo(request.tabla, request.codigo)
        return response
        
    except Exception as e:
        logger.error(f"Error en búsqueda de código: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda: {str(e)}"
        )


@router.get("/buscar-codigo/{tabla}/{codigo}", response_model=BusquedaCodigoResponse)
async def buscar_codigo_get(
    tabla: str,
    codigo: str,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Buscar un código específico en una tabla SUNAT (método GET)
    
    - **tabla**: Nombre de la tabla donde buscar
    - **codigo**: Código a buscar
    """
    try:
        response = await service.buscar_codigo(tabla, codigo)
        return response
        
    except Exception as e:
        logger.error(f"Error en búsqueda de código GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda: {str(e)}"
        )


@router.post("/buscar-descripcion", response_model=BusquedaDescripcionResponse)
async def buscar_por_descripcion(
    request: BusquedaDescripcionRequest,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Buscar códigos por descripción parcial en una tabla SUNAT
    
    - **tabla**: Nombre de la tabla donde buscar
    - **descripcion**: Texto parcial a buscar en las descripciones
    """
    try:
        response = await service.buscar_por_descripcion(request.tabla, request.descripcion)
        return response
        
    except Exception as e:
        logger.error(f"Error en búsqueda por descripción: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda: {str(e)}"
        )


@router.get("/buscar-descripcion/{tabla}")
async def buscar_descripcion_get(
    tabla: str,
    descripcion: str = Query(..., min_length=3, description="Descripción parcial a buscar"),
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Buscar códigos por descripción parcial (método GET)
    
    - **tabla**: Nombre de la tabla donde buscar
    - **descripcion**: Texto parcial a buscar en las descripciones (mínimo 3 caracteres)
    """
    try:
        response = await service.buscar_por_descripcion(tabla, descripcion)
        return response
        
    except Exception as e:
        logger.error(f"Error en búsqueda por descripción GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en búsqueda: {str(e)}"
        )


# ================================
# ENDPOINTS DE VALIDACIÓN
# ================================

@router.post("/validar-codigo", response_model=ValidacionCodigoResponse)
async def validar_codigo_en_tabla(
    request: ValidacionCodigoRequest,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Validar si un código es válido en una tabla SUNAT
    
    - **tabla**: Nombre de la tabla donde validar
    - **codigo**: Código a validar
    """
    try:
        response = await service.validar_codigo(request.tabla, request.codigo)
        return response
        
    except Exception as e:
        logger.error(f"Error en validación de código: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en validación: {str(e)}"
        )


@router.get("/validar-codigo/{tabla}/{codigo}", response_model=ValidacionCodigoResponse)
async def validar_codigo_get(
    tabla: str,
    codigo: str,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Validar si un código es válido en una tabla SUNAT (método GET)
    
    - **tabla**: Nombre de la tabla donde validar
    - **codigo**: Código a validar
    """
    try:
        response = await service.validar_codigo(tabla, codigo)
        return response
        
    except Exception as e:
        logger.error(f"Error en validación de código GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en validación: {str(e)}"
        )


# ================================
# ENDPOINTS DE LISTADO COMPLETO
# ================================

@router.get("/documentos-identidad", response_model=ListadoDocumentosResponse)
async def listar_documentos_identidad(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Listar todos los tipos de documento de identidad
    
    Retorna la lista completa de códigos y descripciones de documentos de identidad
    según la tabla 2 de SUNAT.
    """
    try:
        response = await service.listar_documentos_identidad()
        return response
        
    except Exception as e:
        logger.error(f"Error al listar documentos de identidad: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener documentos: {str(e)}"
        )


@router.get("/comprobantes-pago", response_model=ListadoComprobantesResponse)
async def listar_comprobantes_pago(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Listar todos los tipos de comprobantes de pago
    
    Retorna la lista completa de códigos y descripciones de comprobantes de pago
    según la tabla 10 de SUNAT.
    """
    try:
        response = await service.listar_comprobantes_pago()
        return response
        
    except Exception as e:
        logger.error(f"Error al listar comprobantes de pago: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener comprobantes: {str(e)}"
        )


@router.get("/libros-registros", response_model=ListadoLibrosResponse)
async def listar_libros_registros(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Listar todos los códigos de libros y registros
    
    Retorna la lista completa de códigos y descripciones de libros y registros
    según la tabla 8 de SUNAT.
    """
    try:
        response = await service.listar_libros_registros()
        return response
        
    except Exception as e:
        logger.error(f"Error al listar libros y registros: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener libros: {str(e)}"
        )


@router.get("/tipos-moneda", response_model=ListadoMonedasResponse)
async def listar_tipos_moneda(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Listar todos los tipos de moneda
    
    Retorna la lista completa de códigos y descripciones de monedas
    según la tabla 4 de SUNAT.
    """
    try:
        response = await service.listar_tipos_moneda()
        return response
        
    except Exception as e:
        logger.error(f"Error al listar tipos de moneda: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener monedas: {str(e)}"
        )


# ================================
# ENDPOINTS DE AUTOCOMPLETADO
# ================================

@router.post("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_tabla(
    request: AutocompleteRequest,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Autocompletado para búsquedas en tablas SUNAT
    
    - **tabla**: Nombre de la tabla donde buscar
    - **termino**: Término de búsqueda
    - **limite**: Número máximo de resultados (default: 10)
    """
    try:
        response = await service.autocomplete(request.tabla, request.termino, request.limite)
        return response
        
    except Exception as e:
        logger.error(f"Error en autocompletado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en autocompletado: {str(e)}"
        )


@router.get("/autocomplete/{tabla}")
async def autocomplete_get(
    tabla: str,
    termino: str = Query(..., min_length=1, description="Término de búsqueda"),
    limite: int = Query(10, ge=1, le=50, description="Límite de resultados"),
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Autocompletado para búsquedas en tablas SUNAT (método GET)
    
    - **tabla**: Nombre de la tabla donde buscar
    - **termino**: Término de búsqueda (mínimo 1 carácter)
    - **limite**: Número máximo de resultados (1-50, default: 10)
    """
    try:
        response = await service.autocomplete(tabla, termino, limite)
        return response
        
    except Exception as e:
        logger.error(f"Error en autocompletado GET: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en autocompletado: {str(e)}"
        )


# ================================
# ENDPOINTS DE ESTADÍSTICAS
# ================================

@router.get("/estadisticas", response_model=EstadisticasTablasResponse)
async def obtener_estadisticas_tablas(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Obtener estadísticas de las tablas SUNAT
    
    Retorna información estadística sobre el estado de las tablas:
    - Total de tablas
    - Tablas activas
    - Detalle por tabla (número de códigos, fecha de actualización)
    """
    try:
        response = await service.obtener_estadisticas()
        return response
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


# ================================
# ENDPOINTS ESPECÍFICOS PARA PLE
# ================================

@router.get("/codigos-ple")
async def obtener_codigos_para_ple(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Obtener todas las tablas necesarias para la generación de archivos PLE
    
    Retorna un objeto con todas las tablas de códigos requeridas para
    generar correctamente los archivos del Programa de Libros Electrónicos.
    """
    try:
        codigos = await service.obtener_codigos_para_ple()
        
        if not codigos:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron tablas para generación de PLE"
            )
        
        return {
            "mensaje": "Códigos SUNAT para PLE obtenidos correctamente",
            "tablas": codigos,
            "total_tablas": len(codigos)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener códigos para PLE: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener códigos para PLE: {str(e)}"
        )


@router.post("/validar-para-ple")
async def validar_datos_para_ple(
    datos_asiento: dict,
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Validar datos de un asiento contable para generación de PLE
    
    Valida que los códigos utilizados en un asiento contable sean válidos
    según las tablas SUNAT para la correcta generación de archivos PLE.
    """
    try:
        validacion = await service.validar_datos_para_ple(datos_asiento)
        
        return {
            "mensaje": "Validación completada",
            "resultado": validacion,
            "datos_validados": datos_asiento
        }
        
    except Exception as e:
        logger.error(f"Error en validación para PLE: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en validación: {str(e)}"
        )


# ================================
# ENDPOINTS DE UTILIDAD
# ================================

@router.get("/tablas-disponibles")
async def listar_tablas_disponibles(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Listar todas las tablas disponibles en el sistema
    
    Retorna una lista con información básica de todas las tablas SUNAT
    disponibles en el sistema.
    """
    try:
        tablas = await service.repository.listar_todas_las_tablas()
        
        return {
            "mensaje": "Tablas disponibles obtenidas correctamente",
            "tablas": tablas,
            "total": len(tablas)
        }
        
    except Exception as e:
        logger.error(f"Error al listar tablas disponibles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener tablas: {str(e)}"
        )


@router.get("/health")
async def health_check(
    service: TablasSUNATService = Depends(get_tablas_service)
):
    """
    Health check para el módulo de tablas SUNAT
    
    Verifica que el módulo esté funcionando correctamente y que las
    tablas críticas estén disponibles.
    """
    try:
        # Verificar tablas críticas
        tablas_criticas = ["tipos_documento_identidad", "tipos_comprobantes_pago", "codigos_libros_registros"]
        estado = {
            "status": "healthy",
            "tablas_criticas": {},
            "timestamp": "2025-08-26T00:00:00Z"
        }
        
        for tabla in tablas_criticas:
            try:
                datos = await service.repository.model.obtener_datos_tabla(tabla)
                estado["tablas_criticas"][tabla] = {
                    "disponible": datos is not None,
                    "total_codigos": len(datos) if datos else 0
                }
            except Exception:
                estado["tablas_criticas"][tabla] = {
                    "disponible": False,
                    "total_codigos": 0
                }
                estado["status"] = "degraded"
        
        return estado
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-08-26T00:00:00Z"
        }
