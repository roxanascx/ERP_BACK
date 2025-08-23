"""
Rutas API para el módulo de Socios de Negocio
Incluye integración con servicios SIRE para consultas RUC oficiales
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from app.database import get_database_async
from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import SocioNegocioModel
from .schemas import (
    SocioNegocioCreate, SocioNegocioUpdate, SocioNegocioResponse,
    SocioListResponse, ConsultaRucRequest, ConsultaRucResponse,
    SocioStatsResponse, SocioCreateFromRucRequest
)
from .repositories import SocioNegocioRepository
from .services import SocioNegocioService
from .exceptions import (
    SocioNotFoundException, SocioAlreadyExistsException,
    SocioValidationException, RucConsultaException
)

# ✅ NUEVAS IMPORTACIONES: Servicios SIRE
from ..sire.services.ruc_consulta_service import SireRucConsultaService
from ..sire.services.auth_service import SireAuthService
from ..sire.services.api_client import SunatApiClient
from ..sire.services.token_manager import SireTokenManager
from ..companies.services import CompanyService

router = APIRouter(prefix="/socios-negocio", tags=["Socios de Negocio"])

async def get_sire_ruc_service(db: AsyncIOMotorDatabase = Depends(get_database_async)) -> SireRucConsultaService:
    """Dependency para obtener el servicio SIRE RUC (requerido)"""
    try:
        # Inicializar servicios SIRE
        api_client = SunatApiClient()
        token_manager = SireTokenManager(mongo_collection=db.sire_sessions)  # ✅ CORREGIDO
        auth_service = SireAuthService(api_client, token_manager)
        company_service = CompanyService()
        
        # Crear servicio de consulta RUC
        sire_ruc_service = SireRucConsultaService(
            api_client=api_client,
            auth_service=auth_service,
            token_manager=token_manager,
            company_service=company_service
        )
        
        return sire_ruc_service
        
    except Exception as e:
        # ❌ ERROR CRÍTICO: SIRE es requerido
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Servicio SIRE requerido no disponible: {e}"
        )

async def get_socio_service(
    db: AsyncIOMotorDatabase = Depends(get_database_async),
    sire_ruc_service: SireRucConsultaService = Depends(get_sire_ruc_service)  # ✅ REQUERIDO
) -> SocioNegocioService:
    """Dependency para obtener el servicio de socios con integración SIRE obligatoria"""
    repository = SocioNegocioRepository(db)
    return SocioNegocioService(repository, sire_ruc_service)  # ✅ SIRE obligatorio

# Endpoint de salud del módulo
@router.get(
    "/health",
    summary="Health check del módulo",
    include_in_schema=False
)
async def health_check():
    """Health check básico del módulo de socios de negocio"""
    return {
        "status": "healthy",
        "module": "socios_negocio",
        "version": "1.0.0"
    }

# ✅ ENDPOINT: Verificar disponibilidad de consultas RUC oficiales (obligatorio)
@router.get(
    "/sire-status",
    summary="Verificar disponibilidad de consultas RUC oficiales SIRE"
)
async def verificar_sire_status(
    sire_ruc_service: SireRucConsultaService = Depends(get_sire_ruc_service)
):
    """
    Verifica el estado del servicio SIRE para consultas RUC oficiales
    
    Returns:
        Información sobre disponibilidad y estado de autenticación SIRE
    """
    try:
        status = await sire_ruc_service.verificar_disponibilidad_api()
        return {
            "disponible": status["disponible"],
            "empresa": status.get("empresa"),
            "sesion_activa": status.get("sesion_activa", False),
            "servicios_activos": status.get("servicios_activos", []),
            "token_expira_en": status.get("token_expira_en"),
            "metodos_disponibles": ["SIRE_OAUTH2_OFICIAL"] if status["disponible"] else [],
            "scraping_eliminado": True,
            "solo_api_oficial": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error verificando servicio SIRE: {str(e)}"
        )

@router.post(
    "/",
    response_model=SocioNegocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear socio de negocio"
)
async def create_socio(
    empresa_id: str = Query(..., description="ID de la empresa"),
    socio_data: SocioNegocioCreate = ...,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Crea un nuevo socio de negocio (proveedor, cliente o ambos)
    
    - **empresa_id**: ID de la empresa propietaria
    - **socio_data**: Datos del socio a crear
    
    Valida automáticamente el documento según su tipo (RUC, DNI, CE)
    """
    try:
        return await service.create_socio(empresa_id, socio_data)
    except SocioValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except SocioAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "already_exists", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.get(
    "/{socio_id}",
    response_model=SocioNegocioResponse,
    summary="Obtener socio por ID"
)
async def get_socio(
    socio_id: str,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Obtiene los datos de un socio de negocio por su ID
    
    - **socio_id**: ID único del socio
    """
    try:
        return await service.get_socio(socio_id)
    except SocioNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.put(
    "/{socio_id}",
    response_model=SocioNegocioResponse,
    summary="Actualizar socio"
)
async def update_socio(
    socio_id: str,
    update_data: SocioNegocioUpdate,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Actualiza los datos de un socio de negocio
    
    - **socio_id**: ID único del socio
    - **update_data**: Datos a actualizar (solo campos presentes)
    """
    try:
        return await service.update_socio(socio_id, update_data)
    except SocioNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)}
        )
    except SocioValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.delete(
    "/{socio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar socio"
)
async def delete_socio(
    socio_id: str,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Elimina (desactiva) un socio de negocio
    
    - **socio_id**: ID único del socio
    """
    try:
        await service.delete_socio(socio_id)
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content={"message": "Socio eliminado exitosamente"}
        )
    except SocioNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.get(
    "/",
    response_model=SocioListResponse,
    summary="Listar socios de una empresa"
)
async def list_socios(
    empresa_id: str = Query(..., description="ID de la empresa"),
    tipo_socio: Optional[str] = Query(None, description="Filtrar por tipo (proveedor, cliente, ambos)"),
    tipo_documento: Optional[str] = Query(None, description="Filtrar por tipo de documento"),
    activo: Optional[bool] = Query(True, description="Filtrar por estado activo"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Lista los socios de negocio de una empresa con filtros y paginación
    
    - **empresa_id**: ID de la empresa
    - **tipo_socio**: Opcional, filtrar por proveedor/cliente/ambos
    - **tipo_documento**: Opcional, filtrar por RUC/DNI/CE
    - **activo**: Filtrar por estado activo (default: true)
    - **limit**: Máximo número de resultados (1-100)
    - **offset**: Número de resultados a omitir
    """
    try:
        # Construir filtros
        filters = {}
        if tipo_socio:
            filters['tipo_socio'] = tipo_socio
        if tipo_documento:
            filters['tipo_documento'] = tipo_documento
        if activo is not None:
            filters['activo'] = activo
        
        return await service.list_socios(empresa_id, filters, limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.get(
    "/search/query",
    response_model=SocioListResponse,
    summary="Buscar socios por texto"
)
async def search_socios(
    empresa_id: str = Query(..., description="ID de la empresa"),
    q: str = Query(..., description="Texto a buscar", min_length=2),
    tipo_socio: Optional[str] = Query(None, description="Filtrar por tipo"),
    limit: int = Query(20, ge=1, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Busca socios de negocio por texto en nombre, razón social o documento
    
    - **empresa_id**: ID de la empresa
    - **q**: Texto a buscar (mínimo 2 caracteres)
    - **tipo_socio**: Opcional, filtrar por tipo
    - **limit**: Máximo número de resultados
    - **offset**: Número de resultados a omitir
    """
    try:
        # Construir filtros adicionales
        filters = {}
        if tipo_socio:
            filters['tipo_socio'] = tipo_socio
        
        return await service.search_socios(empresa_id, q, filters, limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.get(
    "/stats/empresa",
    response_model=SocioStatsResponse,
    summary="Estadísticas de socios"
)
async def get_stats(
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Obtiene estadísticas de socios de negocio para una empresa
    
    - **empresa_id**: ID de la empresa
    
    Retorna conteos por tipo de socio, tipo de documento, estado, etc.
    """
    try:
        return await service.get_stats(empresa_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.post(
    "/consulta-ruc",
    response_model=ConsultaRucResponse,
    summary="Consultar RUC en SUNAT"
)
async def consultar_ruc(
    request: ConsultaRucRequest,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Consulta un RUC en el portal de SUNAT para obtener datos actualizados
    
    - **ruc**: RUC de 11 dígitos a consultar
    
    Utiliza web scraping y OCR para obtener información oficial de SUNAT
    """
    try:
        return await service.consultar_ruc(request.ruc)
    except Exception as e:
        # Para consulta RUC, no lanzamos excepción sino que retornamos error en la respuesta
        return ConsultaRucResponse(
            success=False,
            ruc=request.ruc,
            error=f"Error consultando RUC: {str(e)}"
        )

@router.post(
    "/crear-desde-ruc",
    response_model=SocioNegocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear socio desde consulta RUC"
)
async def create_socio_from_ruc(
    request: SocioCreateFromRucRequest,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Crea un socio automáticamente consultando sus datos en SUNAT
    
    - **empresa_id**: ID de la empresa
    - **ruc**: RUC a consultar y crear
    - **tipo_socio**: Tipo de socio (proveedor, cliente, ambos)
    
    Consulta automáticamente SUNAT y crea el socio con los datos oficiales
    """
    try:
        return await service.create_socio_from_ruc(
            request.empresa_id,
            request.ruc,
            request.tipo_socio
        )
    except SocioAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "already_exists", "message": str(e)}
        )
    except RucConsultaException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ruc_consultation_error", "message": str(e)}
        )
    except SocioValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

@router.post(
    "/{socio_id}/sync-sunat",
    response_model=SocioNegocioResponse,
    summary="Sincronizar socio con SUNAT"
)
async def sync_socio_with_sunat(
    socio_id: str,
    background_tasks: BackgroundTasks,
    service: SocioNegocioService = Depends(get_socio_service)
):
    """
    Sincroniza un socio existente con datos actualizados de SUNAT
    
    - **socio_id**: ID único del socio
    
    Solo funciona para socios con RUC. Actualiza automáticamente los datos
    desde SUNAT y marca la fecha de última sincronización.
    """
    try:
        return await service.sync_socio_with_sunat(socio_id)
    except SocioNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)}
        )
    except RucConsultaException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ruc_consultation_error", "message": str(e)}
        )
    except SocioValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "validation_error", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )