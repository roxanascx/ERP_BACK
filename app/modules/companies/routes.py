from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime

from .services import CompanyService
from .schemas import (
    CompanyCreate, CompanyUpdate, SireConfigRequest, AdditionalCredentialsUpdate,
    CompanyResponse, CompanyDetailResponse, CompanySummaryResponse, 
    CompanyListResponse, SireCredentialsResponse, SireInfoResponse,
    CurrentCompanyResponse, OperationResponse, SireMethod
)

router = APIRouter()

# Dependency injection
def get_company_service() -> CompanyService:
    return CompanyService()

# =========================================
# ENDPOINTS BÁSICOS DE EMPRESAS (CRUD)
# =========================================

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    service: CompanyService = Depends(get_company_service)
):
    """Crear una nueva empresa"""
    try:
        return await service.create_company(company_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    activas_only: bool = Query(False, description="Solo empresas activas"),
    con_sire_only: bool = Query(False, description="Solo empresas con SIRE"),
    service: CompanyService = Depends(get_company_service)
):
    """Listar empresas con filtros opcionales"""
    try:
        print(f"📋 [LIST] Iniciando list_companies - skip:{skip}, limit:{limit}")
        result = await service.list_companies(skip, limit, activas_only, con_sire_only)
        print(f"✅ [LIST] list_companies exitoso - {len(result.companies)} empresas")
        return result
    except Exception as e:
        print(f"❌ [LIST] Error en list_companies: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 [LIST] Traceback completo:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/search", response_model=List[CompanySummaryResponse])
async def search_companies(
    q: str = Query(..., min_length=1, description="Texto de búsqueda (RUC o razón social)"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados"),
    service: CompanyService = Depends(get_company_service)
):
    """Buscar empresas por texto"""
    try:
        return await service.search_companies(q, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{ruc}", response_model=CompanyDetailResponse)
async def get_company(
    ruc: str,
    service: CompanyService = Depends(get_company_service)
):
    """Obtener empresa por RUC"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        company = await service.get_company(ruc)
        if not company:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        return company
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.put("/{ruc}", response_model=CompanyResponse)
async def update_company(
    ruc: str,
    update_data: CompanyUpdate,
    service: CompanyService = Depends(get_company_service)
):
    """Actualizar empresa existente"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        company = await service.update_company(ruc, update_data)
        if not company:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        return company
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.delete("/{ruc}", response_model=OperationResponse)
async def delete_company(
    ruc: str,
    service: CompanyService = Depends(get_company_service)
):
    """Eliminar empresa (soft delete)"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        success = await service.delete_company(ruc)
        if not success:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        
        return OperationResponse(
            success=True,
            message=f"Empresa {ruc} eliminada exitosamente"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# =========================================
# ENDPOINTS DE GESTIÓN MULTI-EMPRESA
# =========================================

@router.post("/{ruc}/select", response_model=OperationResponse)
async def select_current_company(
    ruc: str,
    service: CompanyService = Depends(get_company_service)
):
    """Seleccionar empresa como actual para operaciones"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        success = await service.select_current_company(ruc)
        return OperationResponse(
            success=True,
            message=f"Empresa {ruc} seleccionada como actual"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/current/info", response_model=CurrentCompanyResponse)
async def get_current_company(
    service: CompanyService = Depends(get_company_service)
):
    """Obtener información de la empresa actualmente seleccionada"""
    try:
        return await service.get_current_company()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# =========================================
# ENDPOINTS DE GESTIÓN SIRE
# =========================================

@router.post("/{ruc}/sire", response_model=CompanyDetailResponse)
async def configure_sire(
    ruc: str,
    sire_config: SireConfigRequest,
    service: CompanyService = Depends(get_company_service)
):
    """Configurar credenciales SIRE para una empresa"""
    print(f"🔐 [SIRE CONFIG] RUC recibido: {ruc}")
    print(f"📝 [SIRE CONFIG] Datos recibidos: {sire_config.dict()}")
    print(f"📊 [SIRE CONFIG] Validación RUC - Longitud: {len(ruc)}")
    
    if len(ruc) != 11:
        print(f"❌ [SIRE CONFIG] Error: RUC {ruc} tiene longitud incorrecta: {len(ruc)}")
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        print(f"🚀 [SIRE CONFIG] Llamando a service.configure_sire...")
        sire_result = await service.configure_sire(ruc, sire_config)
        if not sire_result:
            print(f"❌ [SIRE CONFIG] Error: Empresa {ruc} no encontrada")
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        
        # Obtener la empresa completa para devolver al frontend
        print(f"🔄 [SIRE CONFIG] Obteniendo empresa completa...")
        company_detail = await service.get_company(ruc)
        if not company_detail:
            print(f"❌ [SIRE CONFIG] Error: No se pudo obtener empresa completa {ruc}")
            raise HTTPException(status_code=500, detail=f"Error obteniendo empresa actualizada: {ruc}")
            
        print(f"✅ [SIRE CONFIG] SIRE configurado exitosamente para {ruc}")
        return company_detail
    except ValueError as e:
        print(f"❌ [SIRE CONFIG] ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [SIRE CONFIG] Exception inesperada: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{ruc}/sire/credentials", response_model=SireCredentialsResponse)
async def get_sire_credentials(
    ruc: str,
    method: SireMethod = Query(SireMethod.ORIGINAL, description="Método de autenticación SIRE"),
    service: CompanyService = Depends(get_company_service)
):
    """Obtener credenciales SIRE de una empresa"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        credentials = await service.get_sire_credentials(ruc, method)
        if not credentials:
            raise HTTPException(
                status_code=404, 
                detail=f"Empresa {ruc} no tiene credenciales SIRE configuradas"
            )
        return credentials
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{ruc}/sire/info", response_model=SireInfoResponse)
async def get_sire_info(
    ruc: str,
    service: CompanyService = Depends(get_company_service)
):
    """Obtener información de configuración SIRE de una empresa"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        # Primero obtener la empresa
        company = await service.get_company(ruc)
        if not company:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        
        # Crear response con la información SIRE
        return SireInfoResponse(
            ruc=company.ruc,
            razon_social=company.razon_social,
            sire_activo=company.sire_activo,
            tiene_credenciales=company.tiene_sire,
            client_id=company.sire_client_id,
            sunat_usuario=company.sunat_usuario,
            fecha_actualizacion=company.fecha_actualizacion
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.delete("/{ruc}/sire", response_model=SireInfoResponse)
async def disable_sire(
    ruc: str,
    service: CompanyService = Depends(get_company_service)
):
    """Desactivar SIRE para una empresa"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        result = await service.disable_sire(ruc)
        if not result:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# =========================================
# ENDPOINTS DE CREDENCIALES ADICIONALES
# =========================================

@router.put("/{ruc}/credentials", response_model=CompanyDetailResponse)
async def update_additional_credentials(
    ruc: str,
    credentials: AdditionalCredentialsUpdate,
    service: CompanyService = Depends(get_company_service)
):
    """Actualizar credenciales adicionales (bancarias, PDT, PLAME, etc.)"""
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        result = await service.update_additional_credentials(ruc, credentials)
        if not result:
            raise HTTPException(status_code=404, detail=f"Empresa no encontrada: {ruc}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# =========================================
# ENDPOINTS DE CONFIGURACIÓN
# =========================================

@router.post("/current/configure-environment", response_model=OperationResponse)
async def configure_environment_variables(
    method: SireMethod = Query(SireMethod.ORIGINAL, description="Método de configuración SIRE"),
    service: CompanyService = Depends(get_company_service)
):
    """Configurar variables de entorno para la empresa actual"""
    try:
        success = await service.configure_environment_variables(method)
        return OperationResponse(
            success=True,
            message=f"Variables de entorno configuradas para método {method.value}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# =========================================
# ENDPOINT DE SALUD
# =========================================

@router.get("/health/check", response_model=Dict[str, Any])
async def health_check(
    service: CompanyService = Depends(get_company_service)
):
    """Verificar el estado del módulo de empresas"""
    try:
        # Contar empresas totales y con SIRE
        companies_list = await service.list_companies(limit=1)
        current_company = await service.get_current_company()
        
        return {
            "status": "healthy",
            "module": "companies",
            "total_companies": companies_list.total,
            "companies_with_sire": companies_list.total_con_sire,
            "current_company_selected": current_company.empresa_seleccionada,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Módulo de empresas no disponible: {str(e)}"
        )
