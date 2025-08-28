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
    PLEFileInfo
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
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: Optional[str] = Query(None, description="Período en formato AAAAMM"),
    fecha_desde: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    tipo_documento: Optional[str] = Query(None, description="Tipo de documento"),
    proveedor_ruc: Optional[str] = Query(None, description="RUC del proveedor"),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
    service: ComprasService = Depends(get_compras_service)
):
    """Obtener registros de compras con filtros opcionales"""
    try:
        # Preparar filtros para el servicio
        filtros = {
            "empresa_id": empresa_id,
            "incluir_anulados": False,
            "pagina": (skip // limit) + 1,
            "limite": limit
        }
        
        # Agregar filtros opcionales si están presentes
        if periodo_aaaamm:
            filtros["periodo"] = periodo_aaaamm
        if fecha_desde:
            filtros["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filtros["fecha_hasta"] = fecha_hasta
        if tipo_documento:
            filtros["tipo_comprobante"] = tipo_documento
        if proveedor_ruc:
            filtros["numero_documento_proveedor"] = proveedor_ruc
        
        # Llamar al servicio con filtros completos
        resultado = await service.listar_registros_compras(**filtros)
        
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
    formato: str = Query("txt", description="Formato de exportación (txt|excel)"),
    incluir_cabecera: bool = Query(True, description="Incluir cabecera en el archivo"),
    service: ComprasService = Depends(get_compras_service)
):
    """Exportar registros de compras en formato PLE 080000"""
    try:
        if formato.lower() == "excel":
            archivo_bytes, filename = await service.exportar_excel_ple(
                empresa_id, periodo_aaaamm, incluir_cabecera
            )
            
            return StreamingResponse(
                io.BytesIO(archivo_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # Formato TXT por defecto
            contenido_txt, filename = await service.generar_archivo_ple(
                empresa_id, periodo_aaaamm, incluir_cabecera
            )
            
            return StreamingResponse(
                io.StringIO(contenido_txt),
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
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
