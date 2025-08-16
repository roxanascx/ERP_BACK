"""
Rutas de mantenimiento para SIRE
Endpoints para limpieza y gestión de tokens/sesiones
"""

import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from ..services.token_manager import SireTokenManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Instancia global del token manager para mantenimiento
token_manager = SireTokenManager()

@router.post("/cleanup/tokens")
async def cleanup_expired_tokens() -> Dict[str, Any]:
    """
    Limpiar todos los tokens expirados del sistema
    
    Returns:
        Resultado de la limpieza
    """
    try:
        logger.info("🧹 [MAINTENANCE] Iniciando limpieza de tokens expirados")
        
        # Ejecutar limpieza global
        cleaned_count = await token_manager.cleanup_all_expired_tokens()
        
        result = {
            "success": True,
            "message": "Limpieza de tokens completada",
            "tokens_cleaned": cleaned_count
        }
        
        logger.info(f"✅ [MAINTENANCE] Limpieza completada: {cleaned_count} tokens procesados")
        return result
        
    except Exception as e:
        logger.error(f"❌ [MAINTENANCE] Error en limpieza de tokens: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en limpieza de tokens: {str(e)}"
        )

@router.get("/stats/tokens")
async def get_token_stats() -> Dict[str, Any]:
    """
    Obtener estadísticas de tokens activos
    
    Returns:
        Estadísticas del sistema de tokens
    """
    try:
        logger.info("📊 [MAINTENANCE] Obteniendo estadísticas de tokens")
        
        # Contar tokens en cache
        cache_count = len(token_manager.token_cache)
        
        # Obtener estadísticas básicas
        stats = {
            "success": True,
            "cache_tokens": cache_count,
            "message": "Estadísticas obtenidas correctamente"
        }
        
        logger.info(f"📊 [MAINTENANCE] Estadísticas: {cache_count} tokens en cache")
        return stats
        
    except Exception as e:
        logger.error(f"❌ [MAINTENANCE] Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )

@router.post("/cleanup/tokens/{ruc}")
async def cleanup_tokens_for_ruc(ruc: str) -> Dict[str, Any]:
    """
    Limpiar tokens expirados para un RUC específico
    
    Args:
        ruc: RUC del contribuyente
    
    Returns:
        Resultado de la limpieza
    """
    try:
        # Normalizar RUC
        normalized_ruc = ''.join(c for c in str(ruc).strip() if c.isdigit())
        
        if len(normalized_ruc) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RUC inválido: {ruc}"
            )
        
        logger.info(f"🧹 [MAINTENANCE] Limpiando tokens para RUC {normalized_ruc}")
        
        # Ejecutar limpieza específica
        await token_manager._cleanup_expired_tokens(normalized_ruc)
        
        result = {
            "success": True,
            "message": f"Limpieza completada para RUC {normalized_ruc}",
            "ruc": normalized_ruc
        }
        
        logger.info(f"✅ [MAINTENANCE] Limpieza completada para RUC {normalized_ruc}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [MAINTENANCE] Error en limpieza para RUC {ruc}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en limpieza para RUC {ruc}: {str(e)}"
        )
