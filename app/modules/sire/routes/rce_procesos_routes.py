"""
RCE Procesos Routes - Endpoints para gestión de procesos y tickets RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from ....database import get_database
from ....shared.exceptions import SireException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..services.rce_propuesta_service import RcePropuestaService
from ..services.rce_proceso_service import RceProcesoService
from ..models.rce import RceEstadoProceso
from ..schemas.rce_schemas import (
    RceProcesoEnviarRequest, RceProcesoResponse,
    RceTicketConsultaRequest, RceTicketResponse,
    RceDescargaMasivaRequest, RceApiResponse
)

router = APIRouter()


class CredencialesSunat(BaseModel):
    """Credenciales SUNAT para operaciones que requieren autenticación"""
    usuario_sunat: str
    clave_sunat: str


class CancelacionProceso(BaseModel):
    """Datos para cancelación de proceso"""
    motivo: str
    credenciales: CredencialesSunat


def get_rce_proceso_service(db=Depends(get_database)) -> RceProcesoService:
    """Dependency para obtener el servicio de procesos RCE"""
    api_client = SunatApiClient()
    auth_service = SireAuthService(db, api_client)
    compras_service = RceComprasService(db, api_client, auth_service)
    propuesta_service = RcePropuestaService(db, api_client, auth_service, compras_service)
    return RceProcesoService(db, api_client, auth_service, propuesta_service)


@router.post(
    "/procesos/enviar",
    response_model=RceApiResponse,
    summary="Enviar proceso RCE",
    description="Enviar proceso RCE a SUNAT para procesamiento definitivo"
)
async def enviar_proceso(
    ruc: str,
    request: RceProcesoEnviarRequest,
    credenciales: CredencialesSunat = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Enviar proceso RCE a SUNAT
    
    - **ruc**: RUC del contribuyente
    - **request**: Datos del proceso (periodo, tipo de envío, observaciones)
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        proceso = await service.enviar_proceso(
            ruc, 
            request, 
            credenciales.usuario_sunat, 
            credenciales.clave_sunat
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Proceso del periodo {request.periodo} enviado exitosamente a SUNAT",
            datos=proceso
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/procesos/{periodo}",
    response_model=RceApiResponse,
    summary="Consultar estado de proceso",
    description="Consultar estado de un proceso RCE específico"
)
async def consultar_estado_proceso(
    ruc: str,
    periodo: str,
    ticket_id: Optional[str] = Query(None, description="ID del ticket específico"),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Consultar estado de un proceso RCE
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo del proceso (YYYYMM)
    - **ticket_id**: ID del ticket específico (opcional)
    """
    try:
        proceso = await service.consultar_estado_proceso(ruc, periodo, ticket_id)
        
        if not proceso:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró proceso para el periodo {periodo}",
                codigo="NOT_FOUND"
            )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estado de proceso consultado",
            datos=proceso
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/procesos/{periodo}/cancelar",
    response_model=RceApiResponse,
    summary="Cancelar proceso RCE",
    description="Cancelar un proceso RCE en SUNAT"
)
async def cancelar_proceso(
    ruc: str,
    periodo: str,
    cancelacion: CancelacionProceso = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Cancelar un proceso RCE en SUNAT
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo del proceso (YYYYMM)
    - **cancelacion**: Datos de cancelación (motivo y credenciales SUNAT)
    """
    try:
        proceso = await service.cancelar_proceso(
            ruc, 
            periodo, 
            cancelacion.credenciales.usuario_sunat,
            cancelacion.credenciales.clave_sunat,
            cancelacion.motivo
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Proceso del periodo {periodo} cancelado exitosamente",
            datos=proceso
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/procesos",
    response_model=RceApiResponse,
    summary="Listar procesos RCE",
    description="Listar procesos RCE del contribuyente con filtros"
)
async def listar_procesos(
    ruc: str,
    estado: Optional[RceEstadoProceso] = Query(None, description="Filtrar por estado"),
    periodo_inicio: Optional[str] = Query(None, description="Periodo inicio YYYYMM"),
    periodo_fin: Optional[str] = Query(None, description="Periodo fin YYYYMM"),
    limit: int = Query(50, description="Límite de resultados", ge=1, le=200),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Listar procesos RCE del contribuyente
    
    - **ruc**: RUC del contribuyente
    - **estado**: Filtro por estado (opcional)
    - **periodo_inicio**: Periodo inicio para rango (opcional)
    - **periodo_fin**: Periodo fin para rango (opcional)
    - **limit**: Límite de resultados (máximo 200)
    """
    try:
        procesos = await service.listar_procesos(ruc, estado, periodo_inicio, periodo_fin, limit)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Se encontraron {len(procesos)} procesos",
            datos={
                "total": len(procesos),
                "procesos": procesos
            }
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/tickets/{ticket_id}",
    response_model=RceApiResponse,
    summary="Consultar ticket RCE",
    description="Consultar estado de un ticket RCE específico"
)
async def consultar_ticket(
    ruc: str,
    ticket_id: str,
    credenciales: CredencialesSunat = Body(...),
    actualizar_desde_sunat: bool = Query(True, description="Actualizar estado desde SUNAT"),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Consultar estado de un ticket RCE
    
    - **ruc**: RUC del contribuyente
    - **ticket_id**: ID del ticket
    - **credenciales**: Usuario y clave SUNAT
    - **actualizar_desde_sunat**: Si consultar estado actual en SUNAT
    """
    try:
        ticket = await service.consultar_ticket(
            ruc, 
            ticket_id, 
            credenciales.usuario_sunat,
            credenciales.clave_sunat,
            actualizar_desde_sunat
        )
        
        if not ticket:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró ticket {ticket_id}",
                codigo="NOT_FOUND"
            )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estado de ticket consultado",
            datos=ticket
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/tickets",
    response_model=RceApiResponse,
    summary="Listar tickets activos",
    description="Listar tickets activos (no finalizados) del contribuyente"
)
async def listar_tickets_activos(
    ruc: str,
    limit: int = Query(20, description="Límite de resultados", ge=1, le=100),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Listar tickets activos del contribuyente
    
    - **ruc**: RUC del contribuyente
    - **limit**: Límite de resultados (máximo 100)
    """
    try:
        tickets = await service.listar_tickets_activos(ruc, limit)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Se encontraron {len(tickets)} tickets activos",
            datos={
                "total": len(tickets),
                "tickets": tickets
            }
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/descarga-masiva",
    response_model=RceApiResponse,
    summary="Solicitar descarga masiva",
    description="Solicitar descarga masiva de comprobantes RCE"
)
async def solicitar_descarga_masiva(
    ruc: str,
    request: RceDescargaMasivaRequest,
    credenciales: CredencialesSunat = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Solicitar descarga masiva de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **request**: Parámetros de descarga masiva (periodos, filtros, formato)
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        ticket = await service.solicitar_descarga_masiva(
            ruc, 
            request, 
            credenciales.usuario_sunat,
            credenciales.clave_sunat
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Descarga masiva solicitada para periodos {request.periodo_inicio} a {request.periodo_fin}",
            datos=ticket
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/descarga-masiva/{ticket_id}/estado",
    response_model=RceApiResponse,
    summary="Consultar estado de descarga masiva",
    description="Consultar estado de una descarga masiva por ticket"
)
async def consultar_estado_descarga_masiva(
    ruc: str,
    ticket_id: str,
    credenciales: CredencialesSunat = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Consultar estado de descarga masiva
    
    - **ruc**: RUC del contribuyente
    - **ticket_id**: ID del ticket de descarga masiva
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        # Consultar estado del ticket
        ticket = await service.consultar_ticket(
            ruc, 
            ticket_id, 
            credenciales.usuario_sunat,
            credenciales.clave_sunat,
            True  # Siempre actualizar desde SUNAT para descargas
        )
        
        if not ticket:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró ticket de descarga {ticket_id}",
                codigo="NOT_FOUND"
            )
        
        # Información específica para descargas masivas
        respuesta_descarga = {
            "ticket_id": ticket.ticket_id,
            "estado": ticket.estado,
            "porcentaje_avance": ticket.porcentaje_avance,
            "resultados_disponibles": ticket.resultados_disponibles,
            "archivos_disponibles": ticket.archivos_disponibles,
            "url_descarga": ticket.url_descarga,
            "fecha_vencimiento": ticket.fecha_vencimiento,
            "mensaje": ticket.mensaje_usuario
        }
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estado de descarga masiva consultado",
            datos=respuesta_descarga
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/descargar-archivo",
    summary="Descargar archivo RCE",
    description="Descargar archivo generado por SUNAT (propuestas, reportes, etc.)"
)
async def descargar_archivo(
    ruc: str,
    ticket_id: str,
    nombre_archivo: str,
    credenciales: CredencialesSunat = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Descargar archivo generado por SUNAT
    
    - **ruc**: RUC del contribuyente
    - **ticket_id**: ID del ticket
    - **nombre_archivo**: Nombre del archivo a descargar
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        # Autenticar con SUNAT
        token = await service.auth_service.obtener_token_valido(
            ruc, 
            credenciales.usuario_sunat, 
            credenciales.clave_sunat
        )
        
        # Preparar parámetros de descarga
        params = {
            "ruc": ruc,
            "ticket": ticket_id,
            "archivo": nombre_archivo
        }
        
        # Descargar archivo desde SUNAT
        contenido_archivo = await service.api_client.rce_archivo_descargar(token.access_token, params)
        
        # Determinar tipo de contenido basado en extensión
        content_type = "application/octet-stream"
        if nombre_archivo.endswith('.txt'):
            content_type = "text/plain"
        elif nombre_archivo.endswith('.xlsx'):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif nombre_archivo.endswith('.pdf'):
            content_type = "application/pdf"
        elif nombre_archivo.endswith('.zip'):
            content_type = "application/zip"
        
        from fastapi.responses import Response
        
        return Response(
            content=contenido_archivo,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/procesos/estadisticas",
    response_model=RceApiResponse,
    summary="Estadísticas de procesos",
    description="Obtener estadísticas de procesos RCE del contribuyente"
)
async def obtener_estadisticas_procesos(
    ruc: str,
    año: Optional[int] = Query(None, description="Año para estadísticas anuales"),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Obtener estadísticas de procesos RCE
    
    - **ruc**: RUC del contribuyente
    - **año**: Año para estadísticas anuales (opcional)
    """
    try:
        filtros = {"ruc": ruc}
        
        if año:
            filtros["periodo"] = {"$regex": f"^{año}"}
        
        # Pipeline de agregación para estadísticas
        pipeline_estados = [
            {"$match": filtros},
            {"$group": {
                "_id": "$estado",
                "cantidad": {"$sum": 1},
                "comprobantes_total": {"$sum": "$comprobantes_enviados"},
                "importe_total": {"$sum": "$total_importe_enviado"}
            }}
        ]
        
        pipeline_mensuales = [
            {"$match": filtros},
            {"$group": {
                "_id": "$periodo",
                "cantidad_procesos": {"$sum": 1},
                "comprobantes": {"$sum": "$comprobantes_enviados"},
                "importe": {"$sum": "$total_importe_enviado"},
                "exitosos": {
                    "$sum": {
                        "$cond": ["$exitoso", 1, 0]
                    }
                }
            }},
            {"$sort": {"_id": 1}}
        ]
        
        estadisticas_estados = await service.collection_procesos.aggregate(pipeline_estados).to_list(length=None)
        estadisticas_mensuales = await service.collection_procesos.aggregate(pipeline_mensuales).to_list(length=None)
        
        # Procesar resultados
        resumen = {
            "por_estado": {
                item["_id"]: {
                    "cantidad_procesos": item["cantidad"],
                    "comprobantes_total": item["comprobantes_total"],
                    "importe_total": float(item["importe_total"])
                }
                for item in estadisticas_estados
            },
            "por_periodo": [
                {
                    "periodo": item["_id"],
                    "cantidad_procesos": item["cantidad_procesos"],
                    "comprobantes": item["comprobantes"],
                    "importe": float(item["importe"]),
                    "tasa_exito": (item["exitosos"] / item["cantidad_procesos"] * 100) if item["cantidad_procesos"] > 0 else 0
                }
                for item in estadisticas_mensuales
            ],
            "totales": {
                "procesos_total": sum(item["cantidad"] for item in estadisticas_estados),
                "comprobantes_total": sum(item["comprobantes_total"] for item in estadisticas_estados),
                "importe_total": sum(item["importe_total"] for item in estadisticas_estados)
            }
        }
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estadísticas de procesos generadas",
            datos=resumen
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/tickets/{ticket_id}/actualizar",
    response_model=RceApiResponse,
    summary="Actualizar estado de ticket",
    description="Forzar actualización del estado de un ticket desde SUNAT"
)
async def actualizar_estado_ticket(
    ruc: str,
    ticket_id: str,
    credenciales: CredencialesSunat = Body(...),
    service: RceProcesoService = Depends(get_rce_proceso_service)
):
    """
    Forzar actualización del estado de un ticket desde SUNAT
    
    - **ruc**: RUC del contribuyente
    - **ticket_id**: ID del ticket
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        ticket_antes = await service.consultar_ticket(
            ruc, ticket_id, credenciales.usuario_sunat, credenciales.clave_sunat, False
        )
        
        ticket_despues = await service.consultar_ticket(
            ruc, ticket_id, credenciales.usuario_sunat, credenciales.clave_sunat, True
        )
        
        if not ticket_despues:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró ticket {ticket_id}",
                codigo="NOT_FOUND"
            )
        
        cambio_estado = (
            ticket_antes and ticket_antes.estado != ticket_despues.estado
        ) if ticket_antes else True
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estado de ticket actualizado desde SUNAT",
            datos={
                "ticket": ticket_despues,
                "estado_cambio": cambio_estado,
                "estado_anterior": ticket_antes.estado if ticket_antes else None,
                "estado_actual": ticket_despues.estado
            }
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
