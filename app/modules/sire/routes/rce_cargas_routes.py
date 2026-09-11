"""
Cargas de archivos al RCE (servicios 5.3 y 5.5–5.9).

Suben un `.txt` a SUNAT por tus.io. El endpoint zipea el archivo, monta la
metadata que exige el manual y devuelve el `numTicket` con el que seguir el
proceso en `/sire/rce/propuestas/sunat/tickets`.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Query, UploadFile

from ....database import get_database
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_carga_service import OPERACIONES, RceCargaService
from ..utils.errores_http import traducir_error

logger = logging.getLogger(__name__)

router = APIRouter()


def get_carga_service(db=Depends(get_database)) -> RceCargaService:
    """Servicio de cargas RCE."""
    from ..services.token_manager import SireTokenManager

    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=db.sire_sessions)
    auth_service = SireAuthService(api_client, token_manager)
    return RceCargaService(db, api_client, auth_service)


@router.get(
    "/operaciones",
    summary="Cargas disponibles",
    description="Qué se puede subir, con el servicio del manual y el estado que exige",
)
async def listar_operaciones() -> Dict[str, Any]:
    """Catálogo de cargas, para que la UI sepa qué ofrecer en cada estado."""
    return {
        "exitoso": True,
        "total": len(OPERACIONES),
        "operaciones": [
            {
                "clave": clave,
                "servicio": op.servicio,
                "nombre": op.nombre,
                "cod_proceso": op.cod_proceso,
                "estado_requerido": op.estado_requerido.value,
                "estado_resultante": op.estado_resultante.value if op.estado_resultante else None,
            }
            for clave, op in sorted(OPERACIONES.items(), key=lambda kv: kv[1].servicio)
        ],
    }


@router.post(
    "/{operacion}",
    summary="Subir un archivo al RCE",
    description=(
        "Sube un .txt a SUNAT por tus.io. La operación decide el codProceso y el "
        "destino. Devuelve el numTicket del proceso"
    ),
)
async def cargar_archivo(
    operacion: str,
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    archivo: UploadFile = File(..., description="Archivo .txt con el formato de SUNAT"),
    service: RceCargaService = Depends(get_carga_service),
) -> Dict[str, Any]:
    """Subir un archivo. Escribe en SUNAT."""
    try:
        contenido = await archivo.read()

        resultado = await service.cargar(
            ruc=ruc,
            periodo=periodo,
            clave_operacion=operacion,
            nombre_archivo=archivo.filename or f"{ruc}{periodo}.txt",
            contenido=contenido,
        )

        return {
            "exitoso": True,
            "mensaje": (
                f"{resultado.operacion.nombre} ({resultado.operacion.servicio}): "
                f"archivo enviado a SUNAT"
            ),
            "ruc": ruc,
            "periodo": periodo,
            "servicio": resultado.operacion.servicio,
            "num_ticket": resultado.num_ticket,
            "bytes_enviados": resultado.bytes_enviados,
            "estado": resultado.periodo.estado.value,
            "operaciones_disponibles": resultado.periodo.operaciones_disponibles(),
        }

    except Exception as e:
        raise traducir_error(e, ruc, periodo)
