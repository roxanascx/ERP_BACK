from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .services import CompanyService
from .schemas import (
    CompanyCreate, CompanyUpdate, SireConfigRequest, AdditionalCredentialsUpdate,
    CompanyResponse, CompanyDetailResponse, CompanySummaryResponse, 
    CompanyListResponse, SireCredentialsResponse, SireInfoResponse,
    CurrentCompanyResponse, OperationResponse, SireMethod
)

# Importaciones para auto-autenticación SIRE
from ..sire.services.auth_service import SireAuthService
from ..sire.services.api_client import SunatApiClient
from ..sire.services.token_manager import SireTokenManager
from ..sire.models.auth import SireCredentials
from ...database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection
def get_company_service() -> CompanyService:
    return CompanyService()

# =========================================
# FUNCIONES AUXILIARES PARA AUTO-AUTENTICACIÓN SIRE
# =========================================

async def auto_authenticate_sire_if_needed(ruc: str, company_service: CompanyService) -> Optional[str]:
    """
    Auto-autentica una empresa con SIRE si tiene credenciales configuradas
    
    Args:
        ruc: RUC de la empresa
        company_service: Servicio de empresas
    
    Returns:
        str: Session ID si la autenticación fue exitosa, None si no
    """
    try:
        logger.info(f"🔐 [AUTO-AUTH] Verificando auto-autenticación SIRE para RUC {ruc}")
        
        # Obtener empresa y verificar configuración SIRE
        company = await company_service.get_company(ruc)
        
        if not company:
            logger.info(f"ℹ️ [AUTO-AUTH] RUC {ruc}: Empresa no encontrada")
            return None
            
        logger.info(f"🔍 [AUTO-AUTH] RUC {ruc}: Empresa encontrada - sire_activo={company.sire_activo}")
        
        if not company.sire_activo:
            logger.info(f"ℹ️ [AUTO-AUTH] RUC {ruc}: SIRE no está activo")
            return None
        
        # Verificar que tenga credenciales completas
        credentials_check = {
            "sunat_usuario": company.sunat_usuario,
            "sunat_clave": company.sunat_clave, 
            "sire_client_id": company.sire_client_id,
            "sire_client_secret": company.sire_client_secret
        }
        
        logger.info(f"🔍 [AUTO-AUTH] RUC {ruc}: Verificando credenciales...")
        for field, value in credentials_check.items():
            has_value = bool(value and str(value).strip())
            logger.info(f"   {field}: {'✅' if has_value else '❌'} ({len(str(value)) if value else 0} chars)")
        
        missing_fields = [field for field, value in credentials_check.items() if not (value and str(value).strip())]
        
        if missing_fields:
            logger.warning(f"⚠️ [AUTO-AUTH] RUC {ruc}: Credenciales faltantes: {', '.join(missing_fields)}")
            return None
        
        # Crear servicios SIRE
        database = get_database()
        token_manager = SireTokenManager(mongo_collection=database.sire_sessions if database is not None else None)
        
        # Verificar si ya existe una sesión válida
        existing_token = await token_manager.get_valid_token(ruc)
        if existing_token:
            logger.info(f"✅ [AUTO-AUTH] RUC {ruc}: Sesión válida existente encontrada")
            return "existing_session"
        
        # Crear credenciales y autenticar
        credentials = SireCredentials(
            ruc=ruc,
            sunat_usuario=company.sunat_usuario,
            sunat_clave=company.sunat_clave,
            client_id=company.sire_client_id,
            client_secret=company.sire_client_secret
        )
        
        api_client = SunatApiClient()
        auth_service = SireAuthService(api_client, token_manager)
        
        logger.info(f"🚀 [AUTO-AUTH] RUC {ruc}: Iniciando autenticación automática...")
        
        auth_response = await auth_service.authenticate(credentials)
        
        logger.info(f"✅ [AUTO-AUTH] RUC {ruc}: Autenticación exitosa - Session ID: {auth_response.session_id}")
        
        return auth_response.session_id
        
    except Exception as e:
        logger.error(f"❌ [AUTO-AUTH] RUC {ruc}: Error en auto-autenticación: {e}")
        # No propagamos el error para no afectar la selección de empresa
        return None

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
        # print(f"📋 [LIST] Iniciando list_companies - skip:{skip}, limit:{limit}")
        result = await service.list_companies(skip, limit, activas_only, con_sire_only)
        # print(f"✅ [LIST] list_companies exitoso - {len(result.companies)} empresas")
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
    """
    Seleccionar empresa como actual para operaciones
    
    ✨ NUEVA FUNCIONALIDAD: Auto-autenticación SIRE automática
    - Si la empresa tiene SIRE configurado, se autentica automáticamente
    - No afecta la selección si falla la autenticación SIRE
    """
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos")
    
    try:
        logger.info(f"🏢 [SELECT] Seleccionando empresa RUC: {ruc}")
        
        # 1. Seleccionar empresa como actual (funcionalidad original)
        success = await service.select_current_company(ruc)
        
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo seleccionar la empresa")
        
        # 2. 🚀 NUEVA FUNCIONALIDAD: Auto-autenticación SIRE
        sire_session_id = await auto_authenticate_sire_if_needed(ruc, service)
        
        # 3. Construir respuesta con información de autenticación SIRE
        message = f"Empresa {ruc} seleccionada como actual"
        
        if sire_session_id:
            if sire_session_id == "existing_session":
                message += " | SIRE: Sesión existente válida ✅"
            else:
                message += f" | SIRE: Autenticado automáticamente ✅ (Session: {sire_session_id[:20]}...)"
        else:
            message += " | SIRE: No configurado o sin credenciales ⚠️"
        
        logger.info(f"✅ [SELECT] {message}")
        
        return OperationResponse(
            success=True,
            message=message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ [SELECT] Error seleccionando empresa {ruc}: {e}")
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
