"""
Rutas FastAPI para Registro de Compras PLE 080000
=================================================

API endpoints para gestión completa del Registro de Compras según
especificaciones oficiales SUNAT PLE 080000.

Funcionalidades incluidas:
- CRUD completo de registros de compras
- Generación de archivos PLE 080000 (32 campos)
- Consultas avanzadas con filtros
- Reportes y agregaciones
- Validaciones de negocio SUNAT
- Exportación de datos

Patrón utilizado: FastAPI + Dependency Injection
Documentación: Swagger UI automática

Autor: Sistema ERP - FASE 3.0
Fecha: Agosto 2025
"""

from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
import io

from ..schemas.compras_schemas import (
    RegistroCompra,
    RegistroCompraCreate,
    RegistroCompraUpdate,
    RegistroCompraResponse,
    RegistroCompraFilter,
    PLEComprasMetadata,
    RegistroCompraResumen,
    ValidationResult,
    PLEFileInfo,
    PLEComprasExportOptions,
)

from ..services.compras_service import ComprasService
from ....core.dependencies import get_database
import logging

# Configurar router
router = APIRouter(
    prefix="/compras",
    tags=["Registro de Compras PLE 080000"],
    responses={
        404: {"description": "Registro no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)

logger = logging.getLogger(__name__)


# Helper function para crear el servicio
def get_compras_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ComprasService:
    """Dependencia para obtener una instancia del servicio de compras"""
    return ComprasService(database=db)


# ===================================
# ENDPOINTS DE CONSULTA
# ===================================


@router.get("/", response_model=List[RegistroCompraResponse])
async def obtener_registros_compras(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    periodo_inicio: Optional[str] = Query(None, description="Período inicio AAAAMM"),
    periodo_fin: Optional[str] = Query(None, description="Período fin AAAAMM"),
    periodo_aaaamm: Optional[str] = Query(None, description="Un solo período AAAAMM"),
    tipo_documento: Optional[str] = Query(None, description="Tipo de comprobante"),
    proveedor_ruc: Optional[str] = Query(None, description="RUC del proveedor"),
    incluir_anulados: bool = Query(False, description="Incluir los comprobantes anulados"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
    service: ComprasService = Depends(get_compras_service)
):
    """
    Registros de compras con filtros opcionales.

    Los filtros son los mismos que en ventas: se acota por **rango de
    periodos**. `periodo_aaaamm` es el atajo para un solo mes.

    La versión anterior construía el filtro con las claves `periodo`,
    `fecha_desde` y `fecha_hasta`, que `listar_registros_compras` no acepta:
    cualquier consulta con filtro moría con TypeError, y sin filtro devolvía
    el histórico entero.
    """
    try:
        if periodo_aaaamm and not (periodo_inicio or periodo_fin):
            periodo_inicio = periodo_fin = periodo_aaaamm

        resultado = await service.listar_registros_compras(
            empresa_id=empresa_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            tipo_comprobante=tipo_documento,
            numero_documento_proveedor=proveedor_ruc,
            incluir_anulados=incluir_anulados,
            pagina=(skip // limit) + 1,
            limite=limit,
        )

        return resultado.get("registros", [])
        
    except Exception as e:
        logger.error(f"Error obteniendo registros de compras: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo registros: {str(e)}"
        )


@router.get("/resumen", response_model=RegistroCompraResumen)
async def obtener_resumen_compras(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período en formato AAAAMM"),
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener resumen de compras para un período específico"""
    try:
        # service ya está inyectado como dependencia
        return await service.obtener_resumen_periodo(empresa_id, periodo_aaaamm)
        
    except ValueError as ve:
        logger.error(f"Error de validación obteniendo resumen: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de validación: {str(ve)}"
        )
    except Exception as e:
        logger.error(f"Error interno obteniendo resumen de compras: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get("/empresa/{empresa_id}")
async def obtener_compras_empresa(
    empresa_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener todos los registros de compras de una empresa"""
    try:
        # service ya está inyectado como dependencia
        return await service.obtener_registros_empresa(empresa_id, skip, limit)
        
    except Exception as e:
        logger.error(f"Error obteniendo compras de empresa {empresa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error obteniendo compras: {str(e)}"
        )


@router.get("/{registro_id}", response_model=RegistroCompraResponse)
async def obtener_registro_compra(
    registro_id: str,
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener un registro de compra específico por ID"""
    try:
        registro = await service.obtener_registro_por_id(registro_id)
        
        if not registro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de compra no encontrado: {registro_id}"
            )
            
        return registro
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo registro {registro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo registro: {str(e)}"
        )


# ===================================
# ENDPOINTS DE CREACIÓN Y MODIFICACIÓN
# ===================================

@router.post("/", response_model=RegistroCompraResponse)
async def crear_registro_compra(
    registro_data: RegistroCompraCreate,
    usuario_id: Optional[str] = Query(None, description="ID del usuario"),
    service: ComprasService = Depends(get_compras_service)
):
    """Crear un nuevo registro de compra"""
    try:
        return await service.crear_registro(registro_data, usuario_id)
        
    except Exception as e:
        logger.error(f"Error creando registro de compra: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creando registro: {str(e)}"
        )


@router.put("/{registro_id}", response_model=RegistroCompraResponse)
async def actualizar_registro_compra(
    registro_id: str,
    registro_update: RegistroCompraUpdate,
    usuario_id: Optional[str] = Query(None, description="ID del usuario"),
    service: ComprasService = Depends(get_compras_service)
):
    """Actualizar un registro de compra existente"""
    try:
        registro_actualizado = await service.actualizar_registro(
            registro_id, registro_update, usuario_id
        )
        
        if not registro_actualizado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de compra no encontrado: {registro_id}"
            )
            
        return registro_actualizado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando registro {registro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error actualizando registro: {str(e)}"
        )


@router.delete("/{registro_id}")
async def eliminar_registro_compra(
    registro_id: str,
    usuario_id: Optional[str] = Query(None, description="ID del usuario"),
    service: ComprasService = Depends(get_compras_service)
):
    """Eliminar un registro de compra"""
    try:
        eliminado = await service.eliminar_registro(registro_id, usuario_id)
        
        if not eliminado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registro de compra no encontrado: {registro_id}"
            )
            
        return {"message": f"Registro de compra {registro_id} eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando registro {registro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error eliminando registro: {str(e)}"
        )


# ===================================
# ENDPOINTS DE VALIDACIÓN Y EXPORT
# ===================================

@router.post("/validar", response_model=ValidationResult)
async def validar_registro_compra(
    registro_data: RegistroCompraCreate,
    service: ComprasService = Depends(get_compras_service)
):
    """Validar un registro de compra antes de guardarlo"""
    try:
        return await service.validar_registro(registro_data)
        
    except Exception as e:
        logger.error(f"Error validando registro de compra: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error validando registro: {str(e)}"
        )


@router.post("/export/ple")
async def exportar_ple_compras(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período en formato AAAAMM"),
    correlativo: str = Query("0001", description="Correlativo del archivo, va en su nombre"),
    incluir_cabecera: bool = Query(True, description="Incluir cabecera en el archivo"),
    service: ComprasService = Depends(get_compras_service)
):
    """
    Exportar el registro de compras al PLE 080000.

    El método se llama `generar_ple_compras` y recibe un objeto de opciones:
    la ruta invocaba un `generar_archivo_ple` que no existe, así que este
    endpoint devolvía un 500 sin llegar a leer un solo comprobante.
    """
    try:
        resultado = await service.generar_ple_compras(
            PLEComprasExportOptions(
                empresa_id=empresa_id,
                periodo_inicio=periodo_aaaamm,
                periodo_fin=periodo_aaaamm,
                correlativo_archivo=correlativo,
                incluir_cabecera=incluir_cabecera,
            )
        )

        if not resultado.contenido_archivo:
            # Un archivo vacío no se descarga: se explica. Es el caso que
            # estuvo pasando desapercibido.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "mensaje": "No se generó ninguna línea para el período",
                    "total_registros": resultado.total_registros,
                    "con_errores": resultado.registros_con_errores,
                    "errores": resultado.errores_encontrados[:10],
                },
            )

        return StreamingResponse(
            io.StringIO(resultado.contenido_archivo),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={resultado.nombre_archivo}",
                "X-Total-Registros": str(resultado.total_registros),
                "X-Registros-Exportados": str(resultado.registros_exportados),
                "X-Registros-Con-Errores": str(resultado.registros_con_errores),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando PLE compras: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando archivo PLE: {str(e)}"
        )


@router.get("/metadata/ple/{empresa_id}/{periodo_aaaamm}", response_model=PLEComprasMetadata)
async def obtener_metadata_ple(
    empresa_id: str,
    periodo_aaaamm: str,
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener metadata para archivo PLE 080000"""
    try:
        return await service.obtener_metadata_ple(empresa_id, periodo_aaaamm)
        
    except Exception as e:
        logger.error(f"Error obteniendo metadata PLE: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error obteniendo metadata: {str(e)}"
        )


# ===================================
# ENDPOINTS ESTADÍSTICOS
# ===================================

@router.get("/estadisticas/empresa/{empresa_id}")
async def obtener_estadisticas_compras(
    empresa_id: str,
    periodo_desde: Optional[str] = Query(None, description="Período inicio AAAAMM"),
    periodo_hasta: Optional[str] = Query(None, description="Período fin AAAAMM"),
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener estadísticas de compras de una empresa"""
    try:
        return await service.obtener_estadisticas_empresa(
            empresa_id, periodo_desde, periodo_hasta
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/proveedores/ranking/{empresa_id}")
async def obtener_ranking_proveedores(
    empresa_id: str,
    periodo_aaaamm: Optional[str] = Query(None, description="Período AAAAMM"),
    top: int = Query(10, ge=1, le=100, description="Top N proveedores"),
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener ranking de proveedores por monto"""
    try:
        return await service.obtener_ranking_proveedores(
            empresa_id, periodo_aaaamm, top
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo ranking proveedores: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error obteniendo ranking: {str(e)}"
        )
