"""
Ciclo de vida del periodo RCE.

Expone la secuencia mínima del manual (§3.1) —aceptar propuesta y registrar
preliminar— más la consulta de periodos habilitados y la marcha atrás.

Son las primeras rutas del módulo que **escriben** en SUNAT. Todas validan la
transición contra el estado local antes de llamar, y devuelven el estado
resultante para que la UI sepa qué ofrecer a continuación.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query

from ....database import get_database
from ..models.rce_periodo import PeriodoRce
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_ciclo_service import RceCicloService
from ..utils.errores_http import traducir_error

logger = logging.getLogger(__name__)

router = APIRouter()


def get_ciclo_service(db=Depends(get_database)) -> RceCicloService:
    """Servicio del ciclo RCE."""
    from ..services.token_manager import SireTokenManager

    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=db.sire_sessions)
    auth_service = SireAuthService(api_client, token_manager)
    return RceCicloService(db, api_client, auth_service)


def _respuesta(periodo: PeriodoRce, mensaje: str) -> Dict[str, Any]:
    """Forma única de respuesta: qué pasó y qué se puede hacer ahora."""
    return {
        "exitoso": True,
        "mensaje": mensaje,
        "ruc": periodo.ruc,
        "periodo": periodo.periodo,
        "estado": periodo.estado.value,
        "num_ticket": periodo.num_ticket_ultimo,
        "operaciones_disponibles": periodo.operaciones_disponibles(),
        "actualizado_en": periodo.actualizado_en.isoformat(),
    }


@router.get(
    "/periodos",
    summary="Periodos habilitados en SUNAT",
    description="Servicio 5.33: periodos que SUNAT tiene abiertos para el contribuyente",
)
async def periodos_habilitados(
    ruc: str = Query(..., description="RUC del contribuyente"),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.33 Consultar los periodos habilitados."""
    try:
        periodos = await service.consultar_periodos_habilitados(ruc)
        return {
            "exitoso": True,
            "ruc": ruc,
            "total": len(periodos),
            "periodos": periodos,
        }
    except Exception as e:
        raise traducir_error(e, ruc, "-")


@router.get(
    "/estado",
    summary="Estado del periodo",
    description="Fase del libro de compras y operaciones admitidas ahora mismo",
)
async def estado_periodo(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    consultar_sunat: bool = Query(
        False,
        description="Añadir lo que SUNAT dice del periodo (una llamada más, servicio 5.33)",
    ),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """Estado local del periodo y, si se pide, el que reporta SUNAT."""
    try:
        estado = await service.obtener_estado(ruc, periodo)
        respuesta = _respuesta(estado, f"El periodo {periodo} está en {estado.estado.value}")

        if consultar_sunat:
            en_sunat = await service.consultar_estado_en_sunat(ruc, periodo)
            respuesta["estado_sunat"] = en_sunat
            # El estado local solo sabe de lo hecho desde aquí. Si alguien operó
            # en el portal web, la diferencia se ve aquí antes de tocar nada.
            respuesta["coincide_con_sunat"] = (
                None if en_sunat is None
                else (en_sunat.get("desEstado") == "No Presentado")
                     == (estado.estado.value == "PROPUESTA")
            )

        return respuesta
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.get(
    "/resumen",
    summary="Resumen de la propuesta",
    description="Servicio 5.35: cuántos comprobantes trae el periodo y por qué importe",
)
async def resumen_propuesta(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """Qué contiene la propuesta, para poder verlo antes de aceptarla."""
    try:
        resumen = await service.obtener_resumen_propuesta(ruc, periodo)
        return {"exitoso": True, "ruc": ruc, "periodo": periodo, **resumen}
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.get(
    "/estados",
    summary="Historial de periodos operados",
    description="Periodos del contribuyente sobre los que ya se ha ejecutado alguna operación",
)
async def listar_estados(
    ruc: str = Query(..., description="RUC del contribuyente"),
    limite: int = Query(24, ge=1, le=120),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """Estados guardados, del periodo más reciente al más antiguo."""
    try:
        periodos = await service.listar_estados(ruc, limite)
        return {
            "exitoso": True,
            "ruc": ruc,
            "total": len(periodos),
            "periodos": [
                {
                    "periodo": p.periodo,
                    "estado": p.estado.value,
                    "num_ticket": p.num_ticket_ultimo,
                    "actualizado_en": p.actualizado_en.isoformat(),
                    "operaciones_disponibles": p.operaciones_disponibles(),
                }
                for p in periodos
            ],
        }
    except Exception as e:
        raise traducir_error(e, ruc, "-")


@router.post(
    "/aceptar-propuesta",
    summary="Aceptar la propuesta de SUNAT",
    description="Servicio 5.2: el libro del periodo pasa a preliminar",
)
async def aceptar_propuesta(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.2 Aceptar la propuesta. Escribe en SUNAT."""
    try:
        estado = await service.aceptar_propuesta(ruc, periodo)
        return _respuesta(estado, f"Propuesta del periodo {periodo} aceptada")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.post(
    "/registrar-preliminar",
    summary="Registrar el preliminar",
    description="Servicio 5.4: paso final del ciclo por API. Solo se deshace con 5.17",
)
async def registrar_preliminar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.4 Registrar el preliminar. Escribe en SUNAT."""
    try:
        estado = await service.registrar_preliminar(ruc, periodo)
        return _respuesta(estado, f"Preliminar del periodo {periodo} registrado")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.delete(
    "/preliminar",
    summary="Eliminar el preliminar",
    description="Servicio 5.17: marcha atrás del 5.2 y del 5.4",
)
async def eliminar_preliminar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    solo_no_domiciliados: bool = Query(
        False, description="Eliminar únicamente la parte de no domiciliados"
    ),
    service: RceCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.17 Eliminar el preliminar. Escribe en SUNAT."""
    try:
        estado = await service.eliminar_preliminar(ruc, periodo, solo_no_domiciliados)
        alcance = "no domiciliados del " if solo_no_domiciliados else ""
        return _respuesta(estado, f"Preliminar {alcance}periodo {periodo} eliminado")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)
