"""
Rutas para consultar resumen RCE
Endpoint específico para resumen de período RCE
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
import httpx
import logging

from ..services.token_manager import SireTokenManager
from ..schemas.rce_schemas import RceApiResponse

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/test-resumen",
    summary="Test endpoint RCE Resumen",
    description="Endpoint simple para probar que las rutas RCE Resumen funcionan"
)
async def test_rce_resumen():
    """Test simple"""
    return {"message": "RCE Resumen endpoint funcionando", "status": "ok"}


@router.get(
    "/resumen",
    response_model=RceApiResponse,
    summary="Consultar resumen RCE",
    description="Consultar resumen del período RCE del contribuyente"
)
async def consultar_resumen_rce(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: Optional[str] = Query(None, description="Período en formato YYYYMM"),
    token_manager: SireTokenManager = Depends(lambda: SireTokenManager())
):
    """
    Consulta el resumen RCE para un período específico
    """
    logger.info(f"🔍 [RCE Resumen] Consultando resumen para RUC: {ruc}, Período: {periodo}")
    
    try:
        # 1. Obtener token válido
        logger.info("🔑 [RCE Resumen] Obteniendo token SUNAT...")
        token_data = await token_manager.get_valid_token(ruc)
        if not token_data:
            raise HTTPException(
                status_code=401, 
                detail="No se pudo obtener token SUNAT válido"
            )
        
        # 2. Preparar headers y URL
        headers = {
            "Authorization": f"Bearer {token_data['access_token']}",
            "Content-Type": "application/json"
        }
        
        # URL del endpoint SUNAT v27 para resumen
        # Nota: Ajustar según documentación SUNAT para resumen
        base_url = "https://api-cpe.sunat.gob.pe/v1/contribuyente/contribuyentes"
        url = f"{base_url}/{ruc}/libroselectronicos/rce/resumen"
        
        # 3. Preparar parámetros
        params = {}
        if periodo:
            params['periodo'] = periodo
            
        logger.info(f"🌐 [RCE Resumen] URL: {url}")
        logger.info(f"🌐 [RCE Resumen] Params: {params}")
        logger.info(f"🌐 [RCE Resumen] Headers: {dict(headers)}")
        
        # 4. Hacer llamada a SUNAT
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("📡 [RCE Resumen] Realizando petición a SUNAT...")
            response = await client.get(url, headers=headers, params=params)
            
            logger.info(f"📥 [RCE Resumen] Status: {response.status_code}")
            logger.info(f"📥 [RCE Resumen] Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ [RCE Resumen] Respuesta exitosa: {data}")
                
                return RceApiResponse(
                    exitoso=True,
                    mensaje="Resumen RCE obtenido exitosamente",
                    datos=data
                )
            else:
                error_text = response.text
                logger.error(f"❌ [RCE Resumen] Error {response.status_code}: {error_text}")
                
                return RceApiResponse(
                    exitoso=False,
                    mensaje=f"Error SUNAT {response.status_code}: {error_text}",
                    datos=None
                )
                
    except Exception as e:
        logger.error(f"💥 [RCE Resumen] Error inesperado: {str(e)}")
        logger.error(f"💥 [RCE Resumen] Tipo: {type(e).__name__}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )
