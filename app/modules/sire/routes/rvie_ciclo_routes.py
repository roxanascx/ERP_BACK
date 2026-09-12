"""
Ciclo de vida del periodo RVIE (ventas).

Expone la secuencia mínima del manual de Ventas v30: aceptar propuesta (5.8) y
registrar preliminar (5.9), más las dos marchas atrás que Ventas separa en
servicios distintos (5.15 para el preliminar no registrado, 5.36 para el ya
registrado, que además necesita el 5.37 para obtener su identificador).

Mismo contrato de respuesta que el ciclo de Compras, para que la interfaz pueda
tratar los dos libros igual.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from ....database import get_database
from ..models.rce_periodo import PeriodoRce
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rvie_ciclo_service import RvieCicloService
from ..utils.errores_http import traducir_error

logger = logging.getLogger(__name__)

router = APIRouter()


def get_ciclo_service(db=Depends(get_database)) -> RvieCicloService:
    """Servicio del ciclo RVIE."""
    from ..services.token_manager import SireTokenManager

    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=db.sire_sessions)
    auth_service = SireAuthService(api_client, token_manager)
    return RvieCicloService(db, api_client, auth_service)


def _respuesta(periodo: PeriodoRce, mensaje: str) -> Dict[str, Any]:
    """Mismo contrato que el ciclo de Compras."""
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
    summary="Periodos habilitados para ventas",
    description="Servicio 5.2: periodos que SUNAT tiene abiertos, con codLibro 140000",
)
async def periodos_habilitados(
    ruc: str = Query(..., description="RUC del contribuyente"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.2 Consultar los periodos habilitados de ventas."""
    try:
        periodos = await service.consultar_periodos_habilitados(ruc)
        return {"exitoso": True, "ruc": ruc, "total": len(periodos), "periodos": periodos}
    except Exception as e:
        raise traducir_error(e, ruc)


@router.get(
    "/estado",
    summary="Estado del periodo de ventas",
    description="Fase del libro de ventas y operaciones admitidas ahora mismo",
)
async def estado_periodo(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    consultar_sunat: bool = Query(
        False,
        description="Añadir lo que SUNAT dice del periodo (una llamada más, servicio 5.2)",
    ),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """Estado local del periodo de ventas y, si se pide, el que reporta SUNAT."""
    try:
        estado = await service.obtener_estado(ruc, periodo)
        respuesta = _respuesta(estado, f"El periodo {periodo} está en {estado.estado.value}")

        if consultar_sunat:
            en_sunat = await service.consultar_estado_en_sunat(ruc, periodo)
            respuesta["estado_sunat"] = en_sunat
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
    summary="Resumen de la propuesta de ventas",
    description="Servicio 5.20: cuántos comprobantes trae el periodo y por qué importe",
)
async def resumen_propuesta(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """Qué contiene la propuesta, para poder verlo antes de aceptarla."""
    try:
        resumen = await service.obtener_resumen_propuesta(ruc, periodo)
        return {"exitoso": True, "ruc": ruc, "periodo": periodo, **resumen}
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.post(
    "/aceptar-propuesta",
    summary="Aceptar la propuesta de ventas",
    description="Servicio 5.8: el libro del periodo pasa a preliminar",
)
async def aceptar_propuesta(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.8 Aceptar la propuesta. Escribe en SUNAT."""
    try:
        estado = await service.aceptar_propuesta(ruc, periodo)
        return _respuesta(estado, f"Propuesta de ventas del periodo {periodo} aceptada")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.post(
    "/registrar-preliminar",
    summary="Registrar el preliminar de ventas",
    description="Servicio 5.9: paso final del ciclo. Puede responder sin ticket",
)
async def registrar_preliminar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.9 Registrar el preliminar. Escribe en SUNAT."""
    try:
        estado = await service.registrar_preliminar(ruc, periodo)
        return _respuesta(estado, f"Preliminar de ventas del periodo {periodo} registrado")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.delete(
    "/preliminar",
    summary="Eliminar el preliminar no registrado",
    description="Servicio 5.15: deshace el reemplazo de la propuesta",
)
async def eliminar_preliminar(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.15 Eliminar el preliminar aún no registrado. Escribe en SUNAT."""
    try:
        estado = await service.eliminar_preliminar(ruc, periodo)
        return _respuesta(estado, f"Preliminar de ventas del periodo {periodo} eliminado")
    except Exception as e:
        raise traducir_error(e, ruc, periodo)


@router.get(
    "/preliminares-registrados",
    summary="Consultar preliminares registrados",
    description="Servicio 5.37: da el identificador que necesita el 5.36",
)
async def preliminares_registrados(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo_ini: str = Query(..., description="Periodo inicial YYYYMM"),
    periodo_fin: str = Query(None, description="Periodo final YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.37 Consultar los preliminares ya registrados."""
    try:
        registros = await service.consultar_preliminares_registrados(
            ruc, periodo_ini, periodo_fin
        )
        return {"exitoso": True, "ruc": ruc, "total": len(registros), "registros": registros}
    except Exception as e:
        raise traducir_error(e, ruc, periodo_ini)


@router.delete(
    "/preliminar-registrado",
    summary="Eliminar el preliminar ya registrado",
    description="Servicio 5.36: busca el identificador con 5.37 y después elimina",
)
async def eliminar_preliminar_registrado(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    service: RvieCicloService = Depends(get_ciclo_service),
) -> Dict[str, Any]:
    """5.36 Eliminar el preliminar registrado. Escribe en SUNAT."""
    try:
        estado = await service.eliminar_preliminar_registrado(ruc, periodo)
        return _respuesta(
            estado, f"Preliminar registrado del periodo {periodo} eliminado"
        )
    except Exception as e:
        raise traducir_error(e, ruc, periodo)
