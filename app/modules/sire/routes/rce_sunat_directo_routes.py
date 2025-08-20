"""
Rutas DIRECTAS a SUNAT para RCE - Usando URLs verificadas
Estas rutas llaman directamente a SUNAT API usando las mismas URLs que funcionan en los scripts
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
    "/test-sunat",
    summary="Test directo SUNAT",
    description="Endpoint de prueba para verificar conexión directa con SUNAT"
)
async def test_sunat():
    """Test simple"""
    return {"message": "Endpoint directo SUNAT funcionando", "status": "ok"}


@router.get(
    "/sunat/propuestas",
    response_model=RceApiResponse,
    summary="Consultar propuestas SUNAT directo",
    description="Consultar propuestas RCE directamente desde SUNAT usando URLs verificadas"
)
async def consultar_propuestas_sunat_directo(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: Optional[str] = Query(None, description="Período en formato YYYYMM"),
    token_manager: SireTokenManager = Depends(lambda: SireTokenManager())
):
    """
    Consulta propuestas RCE DIRECTAMENTE desde SUNAT
    Usa las mismas URLs que los scripts que funcionan
    """
    logger.info(f"🔍 [SUNAT Directo] Consultando propuestas para RUC: {ruc}, Período: {periodo}")
    
    try:
        # 1. Obtener token válido
        logger.info("🔑 [SUNAT Directo] Obteniendo token SUNAT...")
        token_data = await token_manager.get_valid_token(ruc)
        if not token_data:
            raise HTTPException(
                status_code=401, 
                detail="No se pudo obtener token SUNAT válido"
            )
        
        # 2. Preparar headers (igual que en el script que funciona)
        headers = {
            "Authorization": f"Bearer {token_data['access_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 3. URL CORRECTA copiada del script que funciona
        if periodo:
            # Para exportar propuesta específica (igual que descarga_directa_v27.py)
            url = f"https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rce/propuesta/web/propuesta/{periodo}/exportacioncomprobantepropuesta"
            params = {
                'codTipoArchivo': '0',  # TXT
                'codOrigenEnvio': '2'   # Servicio Web
            }
            logger.info(f"📤 [SUNAT Directo] Generando propuesta para período {periodo}")
        else:
            # Para consultar tickets (igual que test_api_v27.py)
            url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"
            params = {
                'perIni': '202507',
                'perFin': '202507', 
                'page': 1,
                'perPage': 20,
                'codLibro': '080000',
                'codOrigenEnvio': '2'
            }
            logger.info(f"🎫 [SUNAT Directo] Consultando tickets RCE")
            
        logger.info(f"🌐 [SUNAT Directo] URL: {url}")
        logger.info(f"🌐 [SUNAT Directo] Params: {params}")
        logger.info(f"🌐 [SUNAT Directo] Headers: {dict(headers)}")
        
        # 4. Hacer llamada a SUNAT (igual que en los scripts)
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("📡 [SUNAT Directo] Realizando petición a SUNAT...")
            response = await client.get(url, headers=headers, params=params)
            
            logger.info(f"📥 [SUNAT Directo] Status: {response.status_code}")
            logger.info(f"📥 [SUNAT Directo] Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ [SUNAT Directo] Respuesta exitosa: {data}")
                
                return RceApiResponse(
                    exitoso=True,
                    mensaje="Propuestas RCE obtenidas exitosamente desde SUNAT",
                    datos=data
                )
            else:
                error_text = response.text
                logger.error(f"❌ [SUNAT Directo] Error {response.status_code}: {error_text}")
                
                return RceApiResponse(
                    exitoso=False,
                    mensaje=f"Error SUNAT {response.status_code}: {error_text}",
                    datos=None
                )
                
    except Exception as e:
        logger.error(f"💥 [SUNAT Directo] Error inesperado: {str(e)}")
        logger.error(f"💥 [SUNAT Directo] Tipo: {type(e).__name__}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.get(
    "/sunat/tickets",
    response_model=RceApiResponse,
    summary="Consultar tickets SUNAT directo",
    description="Consultar tickets RCE directamente desde SUNAT usando URLs verificadas"
)
async def consultar_tickets_sunat_directo(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo_ini: str = Query("202507", description="Período inicial YYYYMM"),
    periodo_fin: str = Query("202507", description="Período final YYYYMM"),
    page: int = Query(1, description="Página", ge=1),
    per_page: int = Query(20, description="Registros por página", ge=1, le=100),
    token_manager: SireTokenManager = Depends(lambda: SireTokenManager())
):
    """
    Consulta tickets RCE DIRECTAMENTE desde SUNAT
    Usa la misma URL que test_api_v27.py que funciona
    """
    logger.info(f"🎫 [SUNAT Tickets] Consultando tickets para RUC: {ruc}, Períodos: {periodo_ini}-{periodo_fin}")
    
    try:
        # 1. Obtener token válido
        logger.info("🔑 [SUNAT Tickets] Obteniendo token SUNAT...")
        token_data = await token_manager.get_valid_token(ruc)
        if not token_data:
            raise HTTPException(
                status_code=401, 
                detail="No se pudo obtener token SUNAT válido"
            )
        
        # 2. Preparar headers
        headers = {
            "Authorization": f"Bearer {token_data['access_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 3. URL CORRECTA del script test_api_v27.py que funciona
        url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"
        
        # 4. Parámetros CORRECTOS del script que funciona
        params = {
            'perIni': periodo_ini,
            'perFin': periodo_fin,
            'page': page,
            'perPage': per_page,
            'codLibro': '080000',
            'codOrigenEnvio': '2'
        }
            
        logger.info(f"🌐 [SUNAT Tickets] URL: {url}")
        logger.info(f"🌐 [SUNAT Tickets] Params: {params}")
        
        # 5. Hacer llamada a SUNAT
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info("📡 [SUNAT Tickets] Realizando petición a SUNAT...")
            response = await client.get(url, headers=headers, params=params)
            
            logger.info(f"📥 [SUNAT Tickets] Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ [SUNAT Tickets] Respuesta exitosa con {len(data.get('registros', []))} registros")
                
                return RceApiResponse(
                    exitoso=True,
                    mensaje="Tickets RCE obtenidos exitosamente desde SUNAT",
                    datos=data
                )
            else:
                error_text = response.text
                logger.error(f"❌ [SUNAT Tickets] Error {response.status_code}: {error_text}")
                
                return RceApiResponse(
                    exitoso=False,
                    mensaje=f"Error SUNAT {response.status_code}: {error_text}",
                    datos=None
                )
                
    except Exception as e:
        logger.error(f"💥 [SUNAT Tickets] Error inesperado: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )
