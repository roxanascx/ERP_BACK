"""
RCE Propuestas Routes - Endpoints para gestión de propuestas RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from ....database import get_database
from ....shared.exceptions import SireException, SireValidationException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..services.rce_propuesta_service import RcePropuestaService
from ..models.rce import RceEstadoProceso
from ..services import sunat_endpoints as sunat_ep
from ..services.sunat_endpoints import CodLibro, CodOrigenEnvio, CodTipoArchivo, CodTipoResumen
from ..utils.exceptions import SireApiException, SireAuthException, SunatValidationException
from ..schemas.rce_schemas import (
    RcePropuestaGenerarRequest, RcePropuestaResponse,
    RceApiResponse
)

router = APIRouter()


class CredencialesSunat(BaseModel):
    """Credenciales SUNAT para operaciones que requieren autenticación"""
    usuario_sunat: str
    clave_sunat: str


def get_rce_propuesta_service(db=Depends(get_database)) -> RcePropuestaService:
    """Dependency para obtener el servicio de propuestas RCE"""
    from ..services.token_manager import SireTokenManager
    
    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=db.sire_sessions)  # Usar misma colección que RVIE
    auth_service = SireAuthService(api_client, token_manager)
    compras_service = RceComprasService(db, api_client, auth_service)
    return RcePropuestaService(db, api_client, auth_service, compras_service)


@router.post(
    "/propuestas",
    response_model=RceApiResponse,
    summary="Generar propuesta RCE",
    description="Generar una nueva propuesta RCE a partir de comprobantes"
)
async def generar_propuesta(
    ruc: str,
    request: RcePropuestaGenerarRequest,
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Generar una nueva propuesta RCE
    
    - **ruc**: RUC del contribuyente
    - **request**: Datos para generar la propuesta (periodo y comprobantes)
    """
    try:
        propuesta = await service.generar_propuesta(ruc, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Propuesta generada exitosamente para el periodo {request.periodo}",
            datos=propuesta
        )
        
    except SireValidationException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="VALIDATION_ERROR"
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
    "/propuestas/{periodo}/enviar",
    response_model=RceApiResponse,
    summary="Enviar propuesta a SUNAT",
    description="Enviar propuesta RCE a SUNAT para su procesamiento"
)
async def enviar_propuesta_sunat(
    ruc: str,
    periodo: str,
    credenciales: CredencialesSunat = Body(...),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Enviar propuesta RCE a SUNAT
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        propuesta = await service.enviar_propuesta_sunat(
            ruc, 
            periodo, 
            credenciales.usuario_sunat, 
            credenciales.clave_sunat
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Propuesta del periodo {periodo} enviada exitosamente a SUNAT",
            datos=propuesta
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
    "/propuestas/{periodo}",
    response_model=RceApiResponse,
    summary="Consultar propuesta RCE",
    description="Consultar una propuesta RCE específica"
)
async def consultar_propuesta(
    ruc: str,
    periodo: str,
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Consultar una propuesta RCE específica
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    """
    try:
        propuesta = await service.consultar_propuesta(ruc, periodo)
        
        if not propuesta:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró propuesta para el periodo {periodo}",
                codigo="NOT_FOUND"
            )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Propuesta encontrada",
            datos=propuesta
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put(
    "/propuestas/{periodo}",
    response_model=RceApiResponse,
    summary="Actualizar propuesta RCE",
    description="Actualizar una propuesta RCE existente (solo en estado PROPUESTA o ERROR)"
)
async def actualizar_propuesta(
    ruc: str,
    periodo: str,
    request: RcePropuestaGenerarRequest,
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Actualizar una propuesta RCE existente
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    - **request**: Nuevos datos de la propuesta
    """
    try:
        propuesta = await service.actualizar_propuesta(ruc, periodo, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Propuesta del periodo {periodo} actualizada exitosamente",
            datos=propuesta
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete(
    "/propuestas/{periodo}",
    response_model=RceApiResponse,
    summary="Eliminar propuesta RCE",
    description="Eliminar una propuesta RCE (solo si no ha sido enviada a SUNAT)"
)
async def eliminar_propuesta(
    ruc: str,
    periodo: str,
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Eliminar una propuesta RCE
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    """
    try:
        eliminado = await service.eliminar_propuesta(ruc, periodo)
        
        if eliminado:
            return RceApiResponse(
                exitoso=True,
                mensaje=f"Propuesta del periodo {periodo} eliminada exitosamente"
            )
        else:
            return RceApiResponse(
                exitoso=False,
                mensaje="No se pudo eliminar la propuesta",
                codigo="DELETE_ERROR"
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
    "/test",
    summary="Test endpoint RCE",
    description="Endpoint simple para probar que las rutas RCE funcionan"
)
async def test_rce_propuestas():
    """Test simple"""
    return {"message": "RCE Propuestas endpoint funcionando", "status": "ok"}


@router.get(
    "/propuestas",
    response_model=RceApiResponse,
    summary="Listar propuestas RCE",
    description="Listar propuestas RCE del contribuyente con filtros"
)
async def listar_propuestas(
    ruc: str,
    estado: Optional[RceEstadoProceso] = Query(None, description="Filtrar por estado"),
    año: Optional[int] = Query(None, description="Filtrar por año"),
    limit: int = Query(50, description="Límite de resultados", ge=1, le=200),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Listar propuestas RCE del contribuyente
    
    - **ruc**: RUC del contribuyente
    - **estado**: Filtro por estado (opcional)
    - **año**: Filtro por año (opcional)
    - **limit**: Límite de resultados (máximo 200)
    """
    try:
        propuestas = await service.listar_propuestas(ruc, estado, año, limit)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Se encontraron {len(propuestas)} propuestas",
            datos={
                "total": len(propuestas),
                "propuestas": propuestas
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
    "/propuestas/{periodo}/resumen",
    response_model=RceApiResponse,
    summary="Resumen de propuesta RCE",
    description="Obtener resumen consolidado de una propuesta RCE"
)
async def obtener_resumen_propuesta(
    ruc: str,
    periodo: str,
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Obtener resumen consolidado de una propuesta RCE
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    """
    try:
        propuesta = await service.consultar_propuesta(ruc, periodo)
        
        if not propuesta:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró propuesta para el periodo {periodo}",
                codigo="NOT_FOUND"
            )
        
        # Generar resumen detallado
        resumen = {
            "ruc": propuesta.ruc,
            "periodo": propuesta.periodo,
            "estado": propuesta.estado,
            "fecha_generacion": propuesta.fecha_generacion,
            "estadisticas": {
                "total_comprobantes": propuesta.cantidad_comprobantes,
                "total_importe": float(propuesta.total_importe),
                "total_igv": float(propuesta.total_igv),
                "total_credito_fiscal": float(propuesta.total_credito_fiscal)
            },
            "porcentajes": {
                "credito_fiscal_sobre_igv": (
                    float(propuesta.total_credito_fiscal) / float(propuesta.total_igv) * 100
                    if propuesta.total_igv > 0 else 0
                ),
                "igv_sobre_total": (
                    float(propuesta.total_igv) / float(propuesta.total_importe) * 100
                    if propuesta.total_importe > 0 else 0
                )
            },
            "control": {
                "ticket_id": propuesta.ticket_id,
                "numero_orden": propuesta.numero_orden,
                "fecha_aceptacion": propuesta.fecha_aceptacion,
                "archivos_disponibles": propuesta.archivos_disponibles
            },
            "observaciones": propuesta.observaciones_sunat
        }
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Resumen de propuesta generado",
            datos=resumen
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/propuestas/{periodo}/regenerar",
    response_model=RceApiResponse,
    summary="Regenerar propuesta RCE",
    description="Regenerar una propuesta RCE con los comprobantes actuales del periodo"
)
async def regenerar_propuesta(
    ruc: str,
    periodo: str,
    validar_duplicados: bool = Query(True, description="Validar comprobantes duplicados"),
    formato_salida: str = Query("TXT", description="Formato de salida: TXT, EXCEL"),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Regenerar propuesta RCE con comprobantes actuales del periodo
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    - **validar_duplicados**: Validar comprobantes duplicados
    - **formato_salida**: Formato de salida (TXT, EXCEL)
    """
    try:
        # Obtener comprobantes del periodo
        from ..schemas.rce_schemas import RceConsultaRequest
        from ..services.rce_compras_service import RceComprasService
        
        # Crear servicio de comprobantes
        api_client = SunatApiClient()
        auth_service = SireAuthService(service.db, api_client)
        compras_service = RceComprasService(service.db, api_client, auth_service)
        
        # Consultar comprobantes del periodo
        consulta_request = RceConsultaRequest(
            ruc=ruc,
            periodo=periodo,
            registros_por_pagina=10000  # Obtener todos los comprobantes
        )
        
        comprobantes_response = await compras_service.consultar_comprobantes(ruc, consulta_request)
        
        if not comprobantes_response.comprobantes:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontraron comprobantes para el periodo {periodo}",
                codigo="NO_COMPROBANTES"
            )
        
        # Convertir a request format
        from ..schemas.rce_schemas import RceComprobanteCreateRequest, RcePropuestaGenerarRequest
        
        comprobantes_request = []
        for comp in comprobantes_response.comprobantes:
            comp_request = RceComprobanteCreateRequest(
                periodo=comp.periodo,
                correlativo=comp.correlativo,
                fecha_emision=comp.fecha_emision,
                fecha_vencimiento=comp.fecha_vencimiento,
                tipo_comprobante=comp.tipo_comprobante,
                serie=comp.serie,
                numero=comp.numero,
                tipo_documento_proveedor=comp.tipo_documento_proveedor,
                numero_documento_proveedor=comp.numero_documento_proveedor,
                razon_social_proveedor=comp.razon_social_proveedor,
                moneda=comp.moneda,
                tipo_cambio=comp.tipo_cambio,
                base_imponible_operaciones_gravadas=comp.base_imponible_operaciones_gravadas,
                igv=comp.igv,
                importe_total=comp.importe_total,
                sustenta_credito_fiscal=comp.sustenta_credito_fiscal,
                observaciones=comp.observaciones
            )
            comprobantes_request.append(comp_request)
        
        # Crear request de propuesta
        propuesta_request = RcePropuestaGenerarRequest(
            ruc=ruc,
            periodo=periodo,
            comprobantes=comprobantes_request,
            validar_duplicados=validar_duplicados,
            formato_salida=formato_salida
        )
        
        # Verificar si existe propuesta y actualizarla o crear nueva
        propuesta_existente = await service.consultar_propuesta(ruc, periodo)
        
        if propuesta_existente:
            propuesta = await service.actualizar_propuesta(ruc, periodo, propuesta_request)
            mensaje = f"Propuesta del periodo {periodo} regenerada exitosamente"
        else:
            propuesta = await service.generar_propuesta(ruc, propuesta_request)
            mensaje = f"Propuesta del periodo {periodo} generada exitosamente"
        
        return RceApiResponse(
            exitoso=True,
            mensaje=mensaje,
            datos=propuesta
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
    "/propuestas/{periodo}/estado-sunat",
    response_model=RceApiResponse,
    summary="Consultar estado en SUNAT",
    description="Consultar estado actual de la propuesta en SUNAT"
)
async def consultar_estado_sunat(
    ruc: str,
    periodo: str,
    credenciales: CredencialesSunat = Body(...),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Consultar estado actual de la propuesta en SUNAT
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo de la propuesta (YYYYMM)
    - **credenciales**: Usuario y clave SUNAT
    """
    try:
        # Obtener propuesta local
        propuesta = await service.consultar_propuesta(ruc, periodo)
        
        if not propuesta:
            return RceApiResponse(
                exitoso=False,
                mensaje=f"No se encontró propuesta local para el periodo {periodo}",
                codigo="NOT_FOUND"
            )
        
        if not propuesta.ticket_id:
            return RceApiResponse(
                exitoso=False,
                mensaje="La propuesta no tiene ticket asociado. No ha sido enviada a SUNAT.",
                codigo="NO_TICKET"
            )
        
        # Consultar estado en SUNAT
        token = await service.auth_service.obtener_token_valido(
            ruc, 
            credenciales.usuario_sunat, 
            credenciales.clave_sunat
        )
        
        params = {
            "ruc": ruc,
            "periodo": periodo,
            "ticket": propuesta.ticket_id
        }
        
        respuesta_sunat = await service.api_client.rce_propuesta_consultar(token.access_token, params)
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estado consultado en SUNAT",
            datos={
                "estado_local": propuesta.estado,
                "estado_sunat": respuesta_sunat.get("estado"),
                "ticket_id": propuesta.ticket_id,
                "numero_orden": propuesta.numero_orden,
                "respuesta_sunat": respuesta_sunat,
                "sincronizado": propuesta.estado == respuesta_sunat.get("estado")
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


# ========================================
# CONSULTAS DIRECTAS A SUNAT
# ========================================
# Estos tres endpoints devuelven el ticket en el momento, sin esperar a que
# SUNAT termine: la UI consulta el estado después con /sunat/tickets. Por eso
# no usan `ejecutar_operacion_con_ticket`, que sí espera al resultado.


@router.get(
    "/sunat/propuestas",
    summary="Generar ticket de propuesta en SUNAT",
    description="Servicio 5.34: solicita la exportación de la propuesta y devuelve el numTicket"
)
async def generar_ticket_propuesta_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    periodo: str = Query(..., description="Período tributario YYYYMM"),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """5.34 Solicitar la propuesta del periodo. Devuelve el ticket para seguirla."""
    try:
        token = await service.auth_service.obtener_token_valido(ruc)

        params = {
            "codTipoArchivo": CodTipoArchivo.TXT,
            "codOrigenEnvio": CodOrigenEnvio.SERVICIO_API,
        }
        url = sunat_ep.descargar_propuesta(periodo)
        datos = await service.api_client.get_json(url, token, params=params)

        return {
            "exitoso": True,
            "mensaje": "Ticket generado exitosamente",
            "datos": datos,
            "ticket_id": datos.get("numTicket"),
            "url_usada": url,
            "parametros": params,
        }

    except SunatValidationException as e:
        return {"exitoso": False, "mensaje": str(e), "errores": e.errors}
    except SireAuthException as e:
        raise HTTPException(
            status_code=401,
            detail=f"No se pudo autenticar con SUNAT para el RUC {ruc}: {e}"
        )
    except SireApiException as e:
        return {"exitoso": False, "mensaje": f"Error de SUNAT: {e}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.get(
    "/sunat/tickets",
    summary="Consultar tickets en SUNAT",
    description="Servicio 5.31: estado de los tickets del contribuyente en un rango de periodos"
)
async def consultar_tickets_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    periodo_ini: str = Query(..., description="Período inicial YYYYMM"),
    periodo_fin: str = Query(..., description="Período final YYYYMM"),
    page: int = Query(1, description="Número de página"),
    per_page: int = Query(20, description="Elementos por página"),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """5.31 Consultar el estado de los tickets del RUC."""
    try:
        token = await service.auth_service.obtener_token_valido(ruc)

        params = {
            "perIni": periodo_ini,
            "perFin": periodo_fin,
            "page": page,
            "perPage": per_page,
            "codLibro": CodLibro.RCE,
            "codOrigenEnvio": CodOrigenEnvio.SERVICIO_API,
        }
        url = sunat_ep.consultar_estado_tickets()
        datos = await service.api_client.get_json(url, token, params=params)

        return {
            "exitoso": True,
            "mensaje": "Tickets consultados exitosamente",
            "datos": datos,
            "total_registros": datos.get("paginacion", {}).get("totalRegistros", 0),
            "url_usada": url,
            "parametros": params,
        }

    except SunatValidationException as e:
        return {"exitoso": False, "mensaje": str(e), "errores": e.errors}
    except SireAuthException as e:
        raise HTTPException(
            status_code=401,
            detail=f"No se pudo autenticar con SUNAT para el RUC {ruc}: {e}"
        )
    except SireApiException as e:
        return {"exitoso": False, "mensaje": f"Error de SUNAT: {e}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.get(
    "/sunat/resumen",
    summary="Consultar resumen del periodo en SUNAT",
    description="Servicio 5.35: descarga directa del resumen, sin pasar por ticket"
)
async def consultar_resumen_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    per_tributario: str = Query(..., description="Período tributario YYYYMM", pattern=r"^\d{6}$"),
    cod_tipo_resumen: str = Query(
        CodTipoResumen.PROPUESTA,
        description="1 propuesta, 2 preliminar, 3 incluidos/excluidos, 4 registro, "
                    "5 preliminar registrado, 6 ajustes posteriores, 7 no domiciliados",
    ),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """5.35 Descargar el resumen del periodo."""
    try:
        token = await service.auth_service.obtener_token_valido(ruc)

        contenido = await service.api_client.descargar_resumen(
            token,
            per_tributario=per_tributario,
            cod_tipo_resumen=cod_tipo_resumen,
            cod_tipo_archivo=CodTipoArchivo.TXT,
        )

        return {
            "exitoso": True,
            "mensaje": "Resumen obtenido correctamente",
            "ruc": ruc,
            "periodo": per_tributario,
            "cod_tipo_resumen": cod_tipo_resumen,
            "contenido_completo": contenido,
            "total_lineas": len(contenido.strip().splitlines()),
        }

    except SunatValidationException as e:
        return {"exitoso": False, "mensaje": str(e), "errores": e.errors}
    except SireAuthException as e:
        raise HTTPException(
            status_code=401,
            detail=f"No se pudo autenticar con SUNAT para el RUC {ruc}: {e}"
        )
    except SireApiException as e:
        return {"exitoso": False, "mensaje": f"Error de SUNAT: {e}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")
