"""
Rutas del Libro Diario PLE 050100
=================================

Endpoints para la gestión del Libro Diario según especificaciones SUNAT.

Funcionalidades:
- Consultar Libro Diario por período
- Crear y gestionar asientos contables
- Validar partida doble
- Exportar formato PLE 050100
- Generar reportes y estadísticas

Autor: Sistema ERP
Fecha: Agosto 2025
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.modules.accounting.libro_diario_service import LibroDiarioService

# Importar desde el archivo accounting_schemas.py a través del directorio schemas/
from app.modules.accounting.schemas import (
    LibroDiarioCreate,
    LibroDiarioUpdate,
    LibroDiarioResponse,
    LibroDiarioCreateV2,
    LibroDiarioResponseV2,
    AsientoContableCreate,
    AsientoContableUpdate,
    AsientoContableResponse,
    AsientoContableCreateV2,
    AsientoContableResponseV2,
    FiltrosLibroDiario,
    ResumenLibroDiario,
    ValidationResult,
    ExportOptions
)

# Configurar router con prefijo específico
router = APIRouter(prefix="/libro-diario", tags=["Libro Diario"])

# Logger
logger = logging.getLogger(__name__)


# ===================================
# ENDPOINTS DE CONSULTA
# ===================================

@router.get("/resumen", response_model=ResumenLibroDiario)
async def obtener_resumen_libro_diario(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período en formato AAAAMM"),
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Obtener resumen del Libro Diario para un período específico"""
    try:
        service = LibroDiarioService()
        return await service.obtener_resumen_libro_diario(
            empresa_id=empresa_id,
            periodo_aaaamm=periodo_aaaamm,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error obteniendo resumen Libro Diario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error obteniendo resumen Libro Diario: {str(e)}"
        )


@router.get("/empresa/{empresa_id}", response_model=List[LibroDiarioResponse])
async def obtener_libros_diario_empresa(
    empresa_id: str,
    periodo_desde: Optional[str] = Query(None, description="Período desde (AAAAMM)"),
    periodo_hasta: Optional[str] = Query(None, description="Período hasta (AAAAMM)"),
    estado: Optional[str] = Query(None, description="Estado del libro"),
    limit: int = Query(50, ge=1, le=1000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """Obtener todos los libros diario de una empresa"""
    try:
        service = LibroDiarioService()
        
        filtros = FiltrosLibroDiario(
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            estado=estado
        )
        
        return await service.obtener_libros_diario_empresa(
            empresa_id=empresa_id,
            filtros=filtros,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error obteniendo libros diario de empresa {empresa_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error obteniendo libros diario: {str(e)}"
        )


@router.get("/siguiente-correlativo")
async def obtener_siguiente_correlativo(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo: str = Query(..., description="Período AAAAMM")
):
    """Obtener el siguiente número correlativo para un asiento"""
    try:
        service = LibroDiarioService()
        correlativo = await service.obtener_siguiente_correlativo(
            empresa_id=empresa_id,
            periodo=periodo
        )
        return {
            "empresa_id": empresa_id,
            "periodo": periodo,
            "siguiente_correlativo": correlativo
        }
    except Exception as e:
        logger.error(f"Error obteniendo siguiente correlativo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error obteniendo correlativo: {str(e)}"
        )


@router.get("/{libro_id}", response_model=LibroDiarioResponse)
async def obtener_libro_diario_por_id(
    libro_id: str,
    incluir_asientos: bool = Query(True, description="Incluir asientos contables")
):
    """Obtener un libro diario específico por ID"""
    try:
        service = LibroDiarioService()
        return await service.obtener_libro_diario_por_id(
            libro_id=libro_id,
            incluir_asientos=incluir_asientos
        )
    except Exception as e:
        logger.error(f"Error obteniendo libro diario {libro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"404: Libro diario no encontrado: {str(e)}"
        )


# ===================================
# ENDPOINTS DE CREACIÓN Y MODIFICACIÓN
# ===================================

@router.post("/", response_model=LibroDiarioResponse)
async def crear_libro_diario(
    libro_data: LibroDiarioCreateV2,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Crear un nuevo libro diario"""
    try:
        service = LibroDiarioService()
        return await service.crear_libro_diario_v2(libro_data, usuario_id)
    except Exception as e:
        logger.error(f"Error creando libro diario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error creando libro diario: {str(e)}"
        )


@router.put("/{libro_id}", response_model=LibroDiarioResponse)
async def actualizar_libro_diario(
    libro_id: str,
    libro_data: LibroDiarioUpdate,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Actualizar un libro diario existente"""
    try:
        service = LibroDiarioService()
        return await service.actualizar_libro_diario(
            libro_id=libro_id,
            libro_data=libro_data,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error actualizando libro diario {libro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error actualizando libro diario: {str(e)}"
        )


@router.delete("/{libro_id}")
async def eliminar_libro_diario(
    libro_id: str,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Eliminar un libro diario"""
    try:
        service = LibroDiarioService()
        resultado = await service.eliminar_libro_diario(
            libro_id=libro_id,
            usuario_id=usuario_id
        )
        return {
            "success": True,
            "message": f"Libro diario {libro_id} eliminado correctamente",
            "deleted_count": resultado
        }
    except Exception as e:
        logger.error(f"Error eliminando libro diario {libro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error eliminando libro diario: {str(e)}"
        )


# ===================================
# ENDPOINTS DE ASIENTOS CONTABLES
# ===================================

@router.post("/{libro_id}/asientos", response_model=AsientoContableResponse)
async def crear_asiento_contable(
    libro_id: str,
    asiento_data: AsientoContableCreateV2,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Crear un nuevo asiento contable en el libro diario"""
    try:
        service = LibroDiarioService()
        return await service.crear_asiento_contable_v2(
            libro_id=libro_id,
            asiento_data=asiento_data,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error creando asiento contable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error creando asiento contable: {str(e)}"
        )


@router.put("/{libro_id}/asientos/{asiento_id}", response_model=AsientoContableResponse)
async def actualizar_asiento_contable(
    libro_id: str,
    asiento_id: str,
    asiento_data: AsientoContableUpdate,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Actualizar un asiento contable existente"""
    try:
        service = LibroDiarioService()
        return await service.actualizar_asiento_contable(
            libro_id=libro_id,
            asiento_id=asiento_id,
            asiento_data=asiento_data,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error actualizando asiento contable {asiento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error actualizando asiento contable: {str(e)}"
        )


@router.delete("/{libro_id}/asientos/{asiento_id}")
async def eliminar_asiento_contable(
    libro_id: str,
    asiento_id: str,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Eliminar un asiento contable"""
    try:
        service = LibroDiarioService()
        resultado = await service.eliminar_asiento_contable(
            libro_id=libro_id,
            asiento_id=asiento_id,
            usuario_id=usuario_id
        )
        return {
            "success": True,
            "message": f"Asiento contable {asiento_id} eliminado correctamente",
            "deleted_count": resultado
        }
    except Exception as e:
        logger.error(f"Error eliminando asiento contable {asiento_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error eliminando asiento contable: {str(e)}"
        )


# ===================================
# ENDPOINTS DE VALIDACIÓN
# ===================================

@router.post("/{libro_id}/validar", response_model=ValidationResult)
async def validar_libro_diario(
    libro_id: str,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Validar un libro diario completo"""
    try:
        service = LibroDiarioService()
        return await service.validar_libro_diario(
            libro_id=libro_id,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error validando libro diario {libro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error validando libro diario: {str(e)}"
        )


@router.post("/validar-asiento", response_model=ValidationResult)
async def validar_asiento_contable(
    asiento_data: AsientoContableCreateV2,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Validar un asiento contable antes de guardarlo"""
    try:
        service = LibroDiarioService()
        return await service.validar_asiento_contable_v2(
            asiento_data=asiento_data,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error validando asiento contable: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error validando asiento: {str(e)}"
        )


# ===================================
# ENDPOINTS DE EXPORTACIÓN
# ===================================

@router.post("/{libro_id}/export")
async def exportar_libro_diario(
    libro_id: str,
    options: ExportOptions,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Exportar libro diario en diferentes formatos"""
    try:
        service = LibroDiarioService()
        return await service.exportar_libro_diario(
            libro_id=libro_id,
            options=options,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error exportando libro diario {libro_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error exportando libro diario: {str(e)}"
        )


@router.post("/reporte/{empresa_id}")
async def generar_reporte_libro_diario(
    empresa_id: str,
    filtros: FiltrosLibroDiario,
    usuario_id: Optional[str] = Query(None, description="ID del usuario")
):
    """Generar reporte del libro diario para una empresa"""
    try:
        service = LibroDiarioService()
        return await service.generar_reporte_libro_diario(
            empresa_id=empresa_id,
            filtros=filtros,
            usuario_id=usuario_id
        )
    except Exception as e:
        logger.error(f"Error generando reporte libro diario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"400: Error generando reporte: {str(e)}"
        )


# ===================================
# ENDPOINT DE HEALTH CHECK
# ===================================

@router.get("/health")
async def health_check():
    """Health check del módulo Libro Diario"""
    return {
        "status": "ok",
        "module": "libro_diario",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ===================================
# FUNCIÓN PARA REGISTRAR RUTAS
# ===================================

def register_routes(app_router: APIRouter):
    """Registrar las rutas del Libro Diario en el router principal"""
    app_router.include_router(router)
    logger.info("Rutas del Libro Diario registradas correctamente")


if __name__ == "__main__":
    # Para desarrollo y testing
    print("Rutas del Libro Diario definidas:")
    for route in router.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = list(route.methods)
            print(f"  {methods[0] if methods else 'GET'} {route.path}")
