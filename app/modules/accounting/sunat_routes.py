"""
Rutas API para tablas SUNAT - Versión Completa
=============================================

Endpoints REST para el manejo de las 12 tablas de códigos SUNAT
necesarias para la generación de archivos PLE y procesos contables.

Incluye:
- Inicialización de tablas
- Búsqueda y validación de códigos
- Listados específicos por tabla
- Autocompletado
- Validación masiva
- Estadísticas y salud del sistema
- Funciones específicas para PLE

Autor: Sistema ERP
Fecha: Agosto 2025
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import Optional, List, Dict, Any
import logging

from app.modules.accounting.sunat_service import TablasSUNATService
from app.modules.accounting.sunat_schemas import (
    # Respuestas básicas
    InicializacionResponse,
    BusquedaCodigoResponse,
    BusquedaDescripcionResponse,
    ValidacionCodigoResponse,
    AutocompleteResponse,
    EstadisticasTablasResponse,
    ValidacionMasivaResponse,
    
    # Listados específicos
    ListadoDocumentosResponse,
    ListadoComprobantesResponse,
    ListadoLibrosResponse,
    ListadoMonedasResponse,
    
    # Requests
    BusquedaCodigoRequest,
    BusquedaDescripcionRequest,
    ValidacionCodigoRequest,
    AutocompleteRequest,
    ValidacionMasivaRequest
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

@router.post("/inicializar", response_model=InicializacionResponse)
async def inicializar_tablas_sunat(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> InicializacionResponse:
    """
    Inicializar todas las 12 tablas SUNAT con sus códigos oficiales.
    
    Crea o actualiza las siguientes tablas:
    1. Tipos de Documento de Identidad
    2. Tipos de Comprobantes de Pago  
    3. Códigos de Libros y Registros
    4. Tipos de Moneda
    5. Tipos de Medio de Pago
    6. Cuentas Contables
    7. Códigos de País
    8. Tipos de Documento
    9. Estados del Contribuyente
    10. Condición del Domicilio
    11. Tipos de Operación
    12. Clasificación de Bienes y Servicios
    """
    try:
        logger.info("Iniciando inicialización de tablas SUNAT")
        resultado = await service.inicializar_tablas()
        
        if resultado.exitoso:
            logger.info(f"Tablas SUNAT inicializadas exitosamente: {resultado.total_tablas} tablas")
        else:
            logger.error(f"Error en inicialización: {resultado.mensaje}")
            
        return resultado
        
    except Exception as e:
        logger.error(f"Error en endpoint inicializar_tablas_sunat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al inicializar tablas SUNAT: {str(e)}"
        )


# ================================
# ENDPOINTS DE BÚSQUEDA Y VALIDACIÓN
# ================================

@router.get("/buscar/codigo", response_model=BusquedaCodigoResponse)
async def buscar_codigo(
    tabla: str = Query(..., description="Nombre de la tabla SUNAT"),
    codigo: str = Query(..., description="Código a buscar"),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> BusquedaCodigoResponse:
    """
    Buscar un código específico en una tabla SUNAT.
    
    Permite buscar códigos en cualquiera de las 12 tablas disponibles.
    Retorna la descripción del código si existe.
    """
    try:
        resultado = await service.buscar_codigo(tabla, codigo)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al buscar código {codigo} en tabla {tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar código: {str(e)}"
        )


@router.get("/validar/codigo", response_model=ValidacionCodigoResponse)
async def validar_codigo(
    tabla: str = Query(..., description="Nombre de la tabla SUNAT"),
    codigo: str = Query(..., description="Código a validar"),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ValidacionCodigoResponse:
    """
    Validar si un código existe en una tabla SUNAT.
    
    Retorna True/False según la existencia del código,
    junto con un mensaje descriptivo.
    """
    try:
        resultado = await service.validar_codigo(tabla, codigo)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al validar código {codigo} en tabla {tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar código: {str(e)}"
        )


@router.get("/buscar/descripcion", response_model=BusquedaDescripcionResponse)
async def buscar_por_descripcion(
    tabla: str = Query(..., description="Nombre de la tabla SUNAT"),
    descripcion: str = Query(..., description="Descripción parcial a buscar"),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> BusquedaDescripcionResponse:
    """
    Buscar códigos por descripción parcial.
    
    Permite encontrar códigos cuando solo se conoce parte
    de la descripción. Útil para interfaces de usuario.
    """
    try:
        resultado = await service.buscar_por_descripcion(tabla, descripcion)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al buscar por descripción '{descripcion}' en tabla {tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar por descripción: {str(e)}"
        )


@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete(
    tabla: str = Query(..., description="Nombre de la tabla SUNAT"),
    termino: str = Query(..., description="Término para autocompletado"),
    limite: int = Query(10, description="Número máximo de resultados"),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> AutocompleteResponse:
    """
    Autocompletado de códigos por descripción.
    
    Ideal para implementar funcionalidad de autocompletado
    en formularios y campos de entrada.
    """
    try:
        resultado = await service.autocomplete(tabla, termino, limite)
        return resultado
        
    except Exception as e:
        logger.error(f"Error en autocomplete para '{termino}' en tabla {tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en autocompletado: {str(e)}"
        )


# ================================
# ENDPOINTS DE LISTADOS ESPECÍFICOS
# ================================

@router.get("/listados/documentos-identidad", response_model=ListadoDocumentosResponse)
async def listar_documentos_identidad(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ListadoDocumentosResponse:
    """
    Listar todos los tipos de documentos de identidad válidos según SUNAT.
    
    Incluye DNI, RUC, Carnet de Extranjería, etc.
    """
    try:
        resultado = await service.listar_documentos_identidad()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar documentos de identidad: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener documentos de identidad: {str(e)}"
        )


@router.get("/listados/comprobantes-pago", response_model=ListadoComprobantesResponse)
async def listar_comprobantes_pago(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ListadoComprobantesResponse:
    """
    Listar todos los tipos de comprobantes de pago válidos según SUNAT.
    
    Incluye Facturas, Boletas, Notas de Crédito, etc.
    """
    try:
        resultado = await service.listar_comprobantes_pago()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar comprobantes de pago: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener comprobantes de pago: {str(e)}"
        )


@router.get("/listados/libros-registros", response_model=ListadoLibrosResponse)
async def listar_libros_registros(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ListadoLibrosResponse:
    """
    Listar todos los códigos de libros y registros según SUNAT.
    
    Incluye Libro Diario, Libro Mayor, Registro de Compras, etc.
    """
    try:
        resultado = await service.listar_libros_registros()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar libros y registros: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener libros y registros: {str(e)}"
        )


@router.get("/listados/tipos-moneda", response_model=ListadoMonedasResponse)
async def listar_tipos_moneda(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ListadoMonedasResponse:
    """
    Listar todos los tipos de moneda válidos según SUNAT.
    
    Incluye PEN (Soles), USD (Dólares), EUR (Euros), etc.
    """
    try:
        resultado = await service.listar_tipos_moneda()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar tipos de moneda: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener tipos de moneda: {str(e)}"
        )


# ================================
# ENDPOINTS GENÉRICOS
# ================================

@router.get("/listar/{nombre_tabla}")
async def listar_tabla_generica(
    nombre_tabla: str,
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Listar cualquier tabla SUNAT de forma genérica.
    
    Permite acceder a cualquiera de las 12 tablas disponibles:
    - tipos_documento_identidad
    - tipos_comprobantes_pago
    - codigos_libros_registros
    - tipos_moneda
    - tipos_medio_pago
    - cuentas_contables
    - codigos_pais
    - tipos_documento
    - estados_contribuyente
    - condicion_domicilio
    - tipos_operacion
    - clasificacion_bienes_servicios
    """
    try:
        resultado = await service.listar_tabla_generica(nombre_tabla)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al listar tabla {nombre_tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener tabla {nombre_tabla}: {str(e)}"
        )


@router.get("/tablas-disponibles")
async def listar_tablas_disponibles(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Obtener lista de todas las tablas SUNAT disponibles.
    
    Retorna los nombres de las 12 tablas que se pueden consultar.
    """
    try:
        tablas = await service.listar_todas_las_tablas_disponibles()
        return {
            "tablas_disponibles": tablas,
            "total": len(tablas),
            "mensaje": "Tablas SUNAT disponibles para consulta"
        }
        
    except Exception as e:
        logger.error(f"Error al listar tablas disponibles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener tablas disponibles: {str(e)}"
        )


# ================================
# ENDPOINTS DE VALIDACIÓN MASIVA
# ================================

@router.post("/validar/masivo", response_model=ValidacionMasivaResponse)
async def validar_codigos_masivo(
    validaciones: List[Dict[str, str]] = Body(
        ...,
        description="Lista de validaciones con formato [{'tabla': 'nombre_tabla', 'codigo': 'codigo'}]"
    ),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> ValidacionMasivaResponse:
    """
    Validar múltiples códigos de diferentes tablas en una sola operación.
    
    Útil para validar datos en lote antes de procesar archivos
    o realizar operaciones masivas.
    
    Formato del request body:
    [
        {"tabla": "tipos_documento_identidad", "codigo": "1"},
        {"tabla": "tipos_comprobantes_pago", "codigo": "01"},
        {"tabla": "tipos_moneda", "codigo": "PEN"}
    ]
    """
    try:
        resultado = await service.validar_codigos_masivo(validaciones)
        return resultado
        
    except Exception as e:
        logger.error(f"Error en validación masiva: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en validación masiva: {str(e)}"
        )


# ================================
# ENDPOINTS DE ESTADÍSTICAS Y SALUD
# ================================

@router.get("/estadisticas", response_model=EstadisticasTablasResponse)
async def obtener_estadisticas_tablas(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> EstadisticasTablasResponse:
    """
    Obtener estadísticas generales de todas las tablas SUNAT.
    
    Incluye:
    - Total de tablas disponibles
    - Cantidad de registros por tabla
    - Estado de cada tabla
    - Fecha de última actualización
    """
    try:
        resultado = await service.obtener_estadisticas()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


@router.get("/salud/verificar-integridad")
async def verificar_integridad_tablas(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Verificar la integridad de todas las tablas SUNAT.
    
    Realiza comprobaciones de:
    - Existencia de todas las tablas
    - Consistencia de datos
    - Detección de problemas
    """
    try:
        resultado = await service.verificar_integridad_tablas()
        return resultado
        
    except Exception as e:
        logger.error(f"Error al verificar integridad: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar integridad: {str(e)}"
        )


@router.get("/salud/health-check")
async def health_check(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Verificar el estado de salud del sistema de tablas SUNAT.
    
    Endpoint básico para monitoreo y verificación de disponibilidad.
    """
    try:
        resultado = await service.health_check()
        return resultado
        
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en health check: {str(e)}"
        )


# ================================
# ENDPOINTS ESPECÍFICOS PARA PLE
# ================================

@router.get("/ple/codigos-necesarios")
async def obtener_codigos_para_ple(
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Obtener todos los códigos SUNAT necesarios para generar archivos PLE.
    
    Retorna un diccionario con las tablas más importantes para
    la generación de archivos del Programa de Libros Electrónicos.
    """
    try:
        resultado = await service.obtener_codigos_para_ple()
        return {
            "codigos_ple": resultado,
            "total_tablas": len(resultado),
            "mensaje": "Códigos SUNAT para generación de PLE"
        }
        
    except Exception as e:
        logger.error(f"Error al obtener códigos para PLE: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener códigos para PLE: {str(e)}"
        )


@router.post("/ple/validar-datos")
async def validar_datos_para_ple(
    datos: Dict[str, Any] = Body(
        ...,
        description="Datos a validar para generación de archivos PLE"
    ),
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Validar datos específicos para la generación de archivos PLE.
    
    Verifica que los códigos utilizados en los datos correspondan
    a valores válidos según las tablas SUNAT.
    
    Campos típicos a validar:
    - tipoDocumento (tipos_documento_identidad)
    - tipoComprobante (tipos_comprobantes_pago)
    - codigoLibro (codigos_libros_registros)
    - moneda (tipos_moneda)
    - mediopago (tipos_medio_pago)
    """
    try:
        resultado = await service.validar_datos_para_ple(datos)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al validar datos para PLE: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar datos para PLE: {str(e)}"
        )


# ================================
# ENDPOINTS DE INFORMACIÓN
# ================================

@router.get("/informacion/{nombre_tabla}")
async def obtener_informacion_tabla(
    nombre_tabla: str,
    service: TablasSUNATService = Depends(get_tablas_service)
) -> Dict[str, Any]:
    """
    Obtener información detallada de una tabla específica.
    
    Incluye metadatos, estadísticas y descripción de la tabla.
    """
    try:
        resultado = await service.obtener_informacion_tabla(nombre_tabla)
        return resultado
        
    except Exception as e:
        logger.error(f"Error al obtener información de tabla {nombre_tabla}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información de tabla: {str(e)}"
        )
