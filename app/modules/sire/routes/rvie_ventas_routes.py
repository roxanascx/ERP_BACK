"""
Rutas específicas para Gestión de Ventas RVIE - Según Manual SUNAT v25
Solo endpoints oficiales que existen en el manual
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..services.rvie_ventas_service import RvieVentasService
from ..services.auth_service import SireAuthService
from ..services.api_client import SunatApiClient
from ..services.token_manager import SireTokenManager
from ....database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

async def get_rvie_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> RvieVentasService:
    """Dependency para obtener el servicio RVIE con todas sus dependencias"""
    return RvieVentasService(db)

@router.get(
    "/test-auth/{ruc}",
    summary="Probar autenticación con SUNAT"
)
async def test_auth(
    ruc: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> Dict[str, Any]:
    """Probar la obtención de token usando el servicio oficial"""
    try:
        logger.info(f"🔧 Probando autenticación para RUC: {ruc}")
        
        # Usar el servicio oficial
        api_client = SunatApiClient()
        # ✅ CORREGIDO: Pasar la colección específica, no toda la base de datos
        token_manager = SireTokenManager(
            mongo_collection=db.sire_sessions if db is not None else None
        )
        auth_service = SireAuthService(api_client, token_manager)
        
        # Verificar si hay token válido
        token_valido = await token_manager.get_valid_token(ruc)
        
        if token_valido:
            return {
                "success": True,
                "message": "Token válido existente",
                "ruc": ruc,
                "token_existe": True
            }
        else:
            return {
                "success": False,
                "message": "No hay token válido, requiere autenticación",
                "ruc": ruc,
                "token_existe": False
            }
        
    except Exception as e:
        logger.error(f"❌ Error en test_auth: {e}")
        raise HTTPException(status_code=500, detail=f"Error en autenticación: {str(e)}")

@router.get(
    "/propuesta/{ruc}/{periodo}",
    summary="5.18 Descargar propuesta RVIE (según manual SUNAT)"
)
async def descargar_propuesta(
    ruc: str,
    periodo: str,
    cod_tipo_archivo: int = Query(0, description="0: txt, 1: xls"),
    mto_total_desde: Optional[float] = Query(None),
    mto_total_hasta: Optional[float] = Query(None),
    fec_documento_desde: Optional[str] = Query(None),
    fec_documento_hasta: Optional[str] = Query(None),
    num_ruc_adquiriente: Optional[str] = Query(None),
    num_car_sunat: Optional[str] = Query(None),
    cod_tipo_cdp: Optional[str] = Query(None),
    cod_tipo_inconsistencia: Optional[str] = Query(None),
    rvie_service: RvieVentasService = Depends(get_rvie_service)
) -> Dict[str, Any]:
    """
    Endpoint oficial según manual SUNAT v25 - Sección 5.18
    URL: /v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{perTributario}/exportapropuesta
    """
    try:
        logger.info(f"📄 Descargando propuesta RVIE para RUC {ruc}, periodo {periodo}")
        
        # Llamar al servicio usando el endpoint oficial
        resultado = await rvie_service.descargar_propuesta(
            ruc=ruc,
            periodo=periodo,
            cod_tipo_archivo=cod_tipo_archivo,
            mto_total_desde=mto_total_desde,
            mto_total_hasta=mto_total_hasta,
            fec_documento_desde=fec_documento_desde,
            fec_documento_hasta=fec_documento_hasta,
            num_ruc_adquiriente=num_ruc_adquiriente,
            num_car_sunat=num_car_sunat,
            cod_tipo_cdp=cod_tipo_cdp,
            cod_tipo_inconsistencia=cod_tipo_inconsistencia
        )
        
        return {
            "success": True,
            "data": resultado,
            "mensaje": "Propuesta descargada exitosamente"
        }
        
    except Exception as e:
        logger.error(f"❌ Error descargando propuesta: {e}")
        raise HTTPException(status_code=500, detail=f"Error al descargar propuesta: {str(e)}")

@router.get(
    "/comprobantes/{ruc}/{periodo}",
    summary="Obtener comprobantes de la propuesta - URL que funciona"
)
async def get_comprobantes_ventas(
    ruc: str,
    periodo: str,
    page: int = Query(1, description="Número de página"),
    per_page: int = Query(99, description="Elementos por página"),
    tipo_resumen: Optional[int] = Query(None, description="Tipo de resumen (ignorado por ahora)"),
    rvie_service: RvieVentasService = Depends(get_rvie_service)
) -> Dict[str, Any]:
    """
    Endpoint que usa la URL que funciona en tu script explorador_comprobantes.py
    URL: /v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{periodo}/comprobantes
    """
    try:
        logger.info(f"📊 Obteniendo comprobantes ventas para RUC {ruc}, periodo {periodo}")
        
        # Usar la nueva función que usa el endpoint correcto
        resultado = await rvie_service.obtener_comprobantes(
            ruc=ruc,
            periodo=periodo,
            page=page,
            per_page=per_page
        )
        
        return {
            "success": True,
            "data": resultado,
            "mensaje": "Comprobantes obtenidos exitosamente",
            "meta": {
                "ruc": ruc,
                "periodo": periodo,
                "page": page,
                "per_page": per_page
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo comprobantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ENDPOINTS ELIMINADOS (no existen en manual SUNAT):
# - /actualizar-desde-sunat/ -> No existe en manual SUNAT
# - /resumen-periodo/ -> Funcionalidad incluida en descargar_propuesta oficial
# - /test-connection/ -> No es parte del manual oficial
#
# Solo mantenemos endpoints que existen en el manual oficial SUNAT v25
