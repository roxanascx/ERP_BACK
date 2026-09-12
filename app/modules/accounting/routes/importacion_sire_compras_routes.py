"""
Importación de compras de SIRE al registro de compras.

Primer paso del puente SIRE → contabilidad por el lado de compras. Solo crea
registros; el asiento del libro diario se genera después, en un paso aparte.

A diferencia de ventas, estos dos endpoints **tardan**: RCE no devuelve los
comprobantes al momento, hay que pedirle a SUNAT que genere la propuesta, esperar
su ticket y descargar el archivo.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from ....database import get_database
from ...sire.services.api_client import SunatApiClient
from ...sire.services.auth_service import SireAuthService
from ...sire.utils.errores_http import traducir_error
from ..services.importacion_sire_compras_service import ImportacionSireComprasService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_importacion_compras_service(
    database=Depends(get_database),
) -> ImportacionSireComprasService:
    from ...sire.services.token_manager import SireTokenManager

    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=database.sire_sessions)
    auth_service = SireAuthService(api_client, token_manager)
    return ImportacionSireComprasService(database, api_client, auth_service)


@router.get(
    "/previsualizar",
    summary="Qué traeria la importacion de compras",
    description=(
        "Descarga la propuesta de SUNAT y dice qué se crearia, sin escribir nada. "
        "Tarda: hay que esperar a que SUNAT genere el archivo"
    ),
)
async def previsualizar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: ImportacionSireComprasService = Depends(get_importacion_compras_service),
) -> Dict[str, Any]:
    """Previsualización de la importación: nada se escribe."""
    try:
        return {"exitoso": True, **await service.previsualizar(ruc, periodo)}
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.post(
    "",
    summary="Importar las compras del periodo",
    description=(
        "Trae los comprobantes de la propuesta al registro de compras, cada uno "
        "con su subdiario. Es idempotente: reimportar actualiza en vez de duplicar"
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
    service: ImportacionSireComprasService = Depends(get_importacion_compras_service),
) -> Dict[str, Any]:
    """Importar. Escribe en el registro de compras, no en el libro diario."""
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
