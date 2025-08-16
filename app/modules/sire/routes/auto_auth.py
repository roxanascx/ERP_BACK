"""
Endpoint para autenticación automática de todos los RUCs con SIRE activo
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import logging
from datetime import datetime

from ..services.auth_service import SireAuthService
from ..services.credentials_manager import SireCredentialsManager
from ..schemas.auth_schemas import SireAuthResponse, SireErrorResponse
from ...companies.services import CompanyService
from ....database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_auth_service() -> SireAuthService:
    """Obtener instancia del servicio de autenticación"""
    from ..services.token_manager import SireTokenManager
    from ..services.api_client import SunatApiClient
    
    database = get_database()
    token_manager = SireTokenManager(
        mongo_collection=database.sire_sessions if database is not None else None
    )
    api_client = SunatApiClient()
    return SireAuthService(token_manager, api_client)

async def get_company_service() -> CompanyService:
    """Obtener instancia del servicio de empresas"""
    database = get_database()
    return CompanyService(database)

@router.post("/auto-authenticate")
async def auto_authenticate_all_rucs(
    auth_service: SireAuthService = Depends(get_auth_service),
    company_service: CompanyService = Depends(get_company_service)
) -> Dict[str, Any]:
    """
    Autenticar automáticamente todos los RUCs con SIRE activo
    
    Returns:
        Resultado de autenticación para cada RUC
    """
    try:
        logger.info("🔐 [AUTO-AUTH] Iniciando autenticación automática de todos los RUCs")
        
        # 1. Obtener todas las empresas con SIRE activo
        companies = await company_service.list_companies()
        sire_companies = [
            company for company in companies.companies 
            if getattr(company, 'sire_activo', False)
        ]
        
        logger.info(f"📊 [AUTO-AUTH] Encontradas {len(sire_companies)} empresas con SIRE activo")
        
        # 2. Resultados de autenticación
        auth_results = {
            "successful": [],
            "failed": [],
            "already_authenticated": [],
            "total_companies": len(sire_companies),
            "summary": {}
        }
        
        # 3. Autenticar cada empresa
        credentials_manager = SireCredentialsManager()
        
        for company in sire_companies:
            ruc = company.ruc
            try:
                logger.info(f"🔑 [AUTO-AUTH] Procesando RUC {ruc}")
                
                # Verificar si ya está autenticado
                existing_token = await auth_service.token_manager.get_valid_token(ruc)
                if existing_token:
                    logger.info(f"✅ [AUTO-AUTH] RUC {ruc} ya está autenticado")
                    auth_results["already_authenticated"].append({
                        "ruc": ruc,
                        "razon_social": getattr(company, 'razon_social', 'N/A'),
                        "message": "Ya está autenticado"
                    })
                    continue
                
                # Obtener credenciales
                credentials = await credentials_manager.get_credentials(ruc)
                if not credentials:
                    logger.warning(f"⚠️ [AUTO-AUTH] No se encontraron credenciales para RUC {ruc}")
                    auth_results["failed"].append({
                        "ruc": ruc,
                        "razon_social": getattr(company, 'razon_social', 'N/A'),
                        "error": "Credenciales no encontradas"
                    })
                    continue
                
                # Intentar autenticación
                auth_response = await auth_service.authenticate(credentials)
                
                logger.info(f"✅ [AUTO-AUTH] Autenticación exitosa para RUC {ruc}")
                auth_results["successful"].append({
                    "ruc": ruc,
                    "razon_social": getattr(company, 'razon_social', 'N/A'),
                    "session_id": auth_response.session_id,
                    "expires_in": auth_response.expires_in
                })
                
            except Exception as e:
                logger.error(f"❌ [AUTO-AUTH] Error autenticando RUC {ruc}: {e}")
                auth_results["failed"].append({
                    "ruc": ruc,
                    "razon_social": getattr(company, 'razon_social', 'N/A'),
                    "error": str(e)
                })
        
        # 4. Crear resumen
        auth_results["summary"] = {
            "successful_count": len(auth_results["successful"]),
            "failed_count": len(auth_results["failed"]),
            "already_authenticated_count": len(auth_results["already_authenticated"]),
            "total_processed": len(sire_companies),
            "success_rate": round(
                (len(auth_results["successful"]) + len(auth_results["already_authenticated"])) / 
                len(sire_companies) * 100, 2
            ) if sire_companies else 0
        }
        
        logger.info(f"📊 [AUTO-AUTH] Resumen: {auth_results['summary']}")
        
        return {
            "success": True,
            "message": "Autenticación automática completada",
            "timestamp": datetime.utcnow().isoformat(),
            "results": auth_results
        }
        
    except Exception as e:
        logger.error(f"❌ [AUTO-AUTH] Error en autenticación automática: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en autenticación automática: {str(e)}"
        )

@router.post("/authenticate/{ruc}")
async def authenticate_single_ruc(
    ruc: str,
    auth_service: SireAuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    Autenticar un RUC específico automáticamente
    
    Args:
        ruc: RUC a autenticar
        
    Returns:
        Resultado de autenticación
    """
    try:
        logger.info(f"🔐 [AUTO-AUTH] Autenticando RUC específico: {ruc}")
        
        # Normalizar RUC
        normalized_ruc = ''.join(c for c in str(ruc).strip() if c.isdigit())
        if len(normalized_ruc) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RUC inválido: {ruc}"
            )
        
        # Verificar si ya está autenticado
        existing_token = await auth_service.token_manager.get_valid_token(normalized_ruc)
        if existing_token:
            return {
                "success": True,
                "message": f"RUC {normalized_ruc} ya está autenticado",
                "ruc": normalized_ruc,
                "already_authenticated": True
            }
        
        # Obtener credenciales
        credentials_manager = SireCredentialsManager()
        credentials = await credentials_manager.get_credentials(normalized_ruc)
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credenciales no encontradas para RUC {normalized_ruc}"
            )
        
        # Autenticar
        auth_response = await auth_service.authenticate(credentials)
        
        return {
            "success": True,
            "message": f"Autenticación exitosa para RUC {normalized_ruc}",
            "ruc": normalized_ruc,
            "session_id": auth_response.session_id,
            "expires_in": auth_response.expires_in,
            "authenticated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTO-AUTH] Error autenticando RUC {ruc}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error autenticando RUC {ruc}: {str(e)}"
        )
