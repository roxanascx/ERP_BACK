"""
Rutas API para configuración del sistema
========================================

Endpoints para gestión de configuraciones y tiempo
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse

from .services import SystemConfigService, TimeConfigService, SystemStatusService
from .schemas import (
    # System Config
    SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse, SystemConfigQuery,
    SystemConfigListResponse,
    
    # Time Config
    TimeConfigUpdate, TimeConfigResponse,
    
    # System Status
    SystemStatus
)

# Router principal
router = APIRouter()

# Dependency para servicios
async def get_config_service() -> SystemConfigService:
    return SystemConfigService()

async def get_time_service() -> TimeConfigService:
    return TimeConfigService()

async def get_status_service() -> SystemStatusService:
    return SystemStatusService()


# ===========================================
# RUTAS PARA CONFIGURACIONES DEL SISTEMA
# ===========================================

@router.post("/configs", response_model=SystemConfigResponse, status_code=201)
async def create_system_config(
    config_data: SystemConfigCreate,
    service: SystemConfigService = Depends(get_config_service)
):
    """Crea una nueva configuración del sistema"""
    try:
        config = await service.create_config(config_data)
        return SystemConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/configs", response_model=SystemConfigListResponse)
async def list_system_configs(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    config_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    is_system: Optional[bool] = Query(None, description="Filtrar por configuraciones del sistema"),
    search: Optional[str] = Query(None, description="Buscar en clave o descripción"),
    page: int = Query(1, ge=1, description="Página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
    service: SystemConfigService = Depends(get_config_service)
):
    """Lista configuraciones del sistema con filtros"""
    try:
        query = SystemConfigQuery(
            category=category,
            config_type=config_type,
            is_active=is_active,
            is_system=is_system,
            search=search
        )
        
        configs, total = await service.list_configs(query, page, size)
        config_responses = [SystemConfigResponse.model_validate(config) for config in configs]
        
        return SystemConfigListResponse(
            configs=config_responses,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/configs/{config_key}", response_model=SystemConfigResponse)
async def get_system_config(
    config_key: str = Path(..., description="Clave de la configuración"),
    service: SystemConfigService = Depends(get_config_service)
):
    """Obtiene una configuración específica por su clave"""
    try:
        config = await service.get_config_by_key(config_key)
        if not config:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
        
        return SystemConfigResponse.model_validate(config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/configs/{config_id}", response_model=SystemConfigResponse)
async def update_system_config(
    config_id: str = Path(..., description="ID de la configuración"),
    updates: SystemConfigUpdate = ...,
    service: SystemConfigService = Depends(get_config_service)
):
    """Actualiza una configuración del sistema"""
    try:
        config = await service.update_config(config_id, updates)
        if not config:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
        
        return SystemConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/configs/{config_id}", status_code=204)
async def delete_system_config(
    config_id: str = Path(..., description="ID de la configuración"),
    service: SystemConfigService = Depends(get_config_service)
):
    """Elimina una configuración del sistema"""
    try:
        deleted = await service.delete_config(config_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/configs/initialize", status_code=201)
async def initialize_default_configs(
    service: SystemConfigService = Depends(get_config_service)
):
    """Inicializa las configuraciones por defecto del sistema"""
    try:
        await service.initialize_default_configs()
        return {"message": "Configuraciones por defecto inicializadas correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ===========================================
# RUTAS PARA CONFIGURACIÓN DE TIEMPO
# ===========================================

@router.get("/time-config", response_model=TimeConfigResponse)
async def get_time_config(
    service: TimeConfigService = Depends(get_time_service)
):
    """Obtiene la configuración de tiempo actual"""
    try:
        config = await service.get_time_config()
        return TimeConfigResponse.model_validate(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/time-config", response_model=TimeConfigResponse)
async def update_time_config(
    updates: TimeConfigUpdate,
    service: TimeConfigService = Depends(get_time_service)
):
    """Actualiza la configuración de tiempo"""
    try:
        config = await service.update_time_config(updates)
        return TimeConfigResponse.model_validate(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/time/current-peru")
async def get_current_peru_time(
    service: TimeConfigService = Depends(get_time_service)
):
    """Obtiene la fecha y hora actual en zona horaria de Perú"""
    try:
        current_time = await service.get_current_peru_time()
        return {
            "current_time": current_time,
            "timezone": "America/Lima",
            "formatted": current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/time/business-hours")
async def check_business_hours(
    service: TimeConfigService = Depends(get_time_service)
):
    """Verifica si estamos en horario laboral"""
    try:
        is_business_hours = await service.is_business_hours()
        current_time = await service.get_current_peru_time()
        
        return {
            "is_business_hours": is_business_hours,
            "current_time": current_time,
            "message": "En horario laboral" if is_business_hours else "Fuera de horario laboral"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ===========================================
# RUTAS PARA ESTADO DEL SISTEMA
# ===========================================

@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    service: SystemStatusService = Depends(get_status_service)
):
    """Obtiene el estado general del sistema de configuración"""
    try:
        status = await service.get_system_status()
        return SystemStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check para el módulo de configuración del sistema"""
    try:
        from .utils import PeruTimeUtils
        current_time = PeruTimeUtils.now_peru()
        
        return {
            "status": "healthy",
            "module": "system_config",
            "current_time_peru": current_time,
            "timezone": "America/Lima",
            "services": {
                "config_service": "operational",
                "time_service": "operational",
                "status_service": "operational"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "module": "system_config",
                "error": str(e)
            }
        )
