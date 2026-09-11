"""
Importación de ventas de SIRE al registro de ventas.

Primer paso del puente SIRE → contabilidad. Solo crea registros de venta; el
asiento del libro diario se genera después, en un paso aparte.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ....database import get_database
from ...sire.services.api_client import SunatApiClient
from ...sire.services.auth_service import SireAuthService
from ...sire.utils.errores_http import traducir_error
from ..services.importacion_sire_service import ImportacionSireService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_importacion_service(database=Depends(get_database)) -> ImportacionSireService:
    from ...sire.services.token_manager import SireTokenManager

    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=database.sire_sessions)
    auth_service = SireAuthService(api_client, token_manager)
    return ImportacionSireService(database, api_client, auth_service)


@router.get(
    "/previsualizar",
    summary="Qué traeria la importacion",
    description="Consulta SUNAT y dice qué se crearia, sin escribir nada",
)
async def previsualizar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: ImportacionSireService = Depends(get_importacion_service),
) -> Dict[str, Any]:
    """Previsualización de la importación: nada se escribe."""
    try:
        return {"exitoso": True, **await service.previsualizar(ruc, periodo)}
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.post(
    "",
    summary="Importar las ventas del periodo",
    description=(
        "Trae los comprobantes de SUNAT al registro de ventas, cada uno con su "
        "subdiario. Es idempotente: reimportar actualiza en vez de duplicar"
    ),
)
async def importar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    sobrescribir_manuales: bool = Query(
        False,
        description=(
            "Pisar tambien los comprobantes capturados a mano. Por defecto se "
            "respetan y solo se informan"
        ),
    ),
    service: ImportacionSireService = Depends(get_importacion_service),
) -> Dict[str, Any]:
    """Importar. Escribe en el registro de ventas, no en el libro diario."""
    try:
        resultado = await service.importar(ruc, periodo, sobrescribir_manuales)
        return {
            "exitoso": True,
            "mensaje": (
                f"{resultado['creados']} creados y "
                f"{resultado['actualizados']} actualizados del periodo {periodo}"
            ),
            **resultado,
        }
    except Exception as e:
        raise traducir_error(e, ruc, periodo)
