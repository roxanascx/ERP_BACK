"""
RCE Propuestas Routes - Endpoints para gestión de propuestas RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
import httpx

from ....database import get_database
from ....shared.exceptions import SireException, SireValidationException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..services.rce_propuesta_service import RcePropuestaService
from ..models.rce import RceEstadoProceso
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
# 🔥 ENDPOINTS DIRECTOS - IGUAL A TUS SCRIPTS
# ========================================

import httpx

@router.get(
    "/sunat/propuestas",
    summary="🚀 SUNAT DIRECTO - Generar ticket propuesta",
    description="Genera ticket de propuesta usando API SUNAT directamente (igual a tu script)"
)
async def generar_ticket_propuesta_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    periodo: str = Query(..., description="Período tributario YYYYMM")
):
    """Genera ticket de propuesta usando la misma lógica que tu script test_api_v27.py"""
    
    # CREDENCIALES HARDCODEADAS - IGUALES A TU SCRIPT
    usuario = "THENTHIP"
    clave_sol = "enteatell"
    client_id = "aa3f9b5c-7013-4ded-a63a-5ee658ce3530"
    client_secret = "MOIzbzE3lAj/W5EkokXEbA=="
    
    try:
        # PASO 1: OBTENER TOKEN - IGUAL A TU SCRIPT
        token_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
        token_data = {
            'grant_type': 'password',
            'scope': 'https://api-sire.sunat.gob.pe',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': f"{ruc}{usuario}",
            'password': clave_sol
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(token_url, data=token_data, headers=token_headers)
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Error obteniendo token: {token_response.status_code} - {token_response.text}"
                )
            
            token = token_response.json()['access_token']
            
            # PASO 2: GENERAR TICKET - URL EXACTA DE TU SCRIPT
            propuesta_url = f"https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rce/propuesta/web/propuesta/{periodo}/exportacioncomprobantepropuesta"
            
            propuesta_params = {
                'codTipoArchivo': '0',  # TXT
                'codOrigenEnvio': '2'   # Servicio Web
            }
            
            propuesta_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            propuesta_response = await client.get(
                propuesta_url, 
                headers=propuesta_headers, 
                params=propuesta_params
            )
            
            if propuesta_response.status_code == 200:
                data = propuesta_response.json()
                return {
                    "exitoso": True,
                    "mensaje": "Ticket generado exitosamente",
                    "datos": data,
                    "ticket_id": data.get('numTicket'),
                    "url_usada": propuesta_url,
                    "parametros": propuesta_params
                }
            else:
                return {
                    "exitoso": False,
                    "mensaje": f"Error de SUNAT: {propuesta_response.status_code}",
                    "detalle": propuesta_response.text,
                    "url_usada": propuesta_url
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get(
    "/sunat/tickets",
    summary="🎫 SUNAT DIRECTO - Consultar tickets",
    description="Consulta tickets usando API SUNAT directamente (igual a tu script)"
)
async def consultar_tickets_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    periodo_ini: str = Query(..., description="Período inicial YYYYMM"),
    periodo_fin: str = Query(..., description="Período final YYYYMM"),
    page: int = Query(1, description="Número de página"),
    per_page: int = Query(20, description="Elementos por página")
):
    """Consulta tickets usando la misma lógica que tu script test_api_v27.py"""
    
    # CREDENCIALES HARDCODEADAS - IGUALES A TU SCRIPT
    usuario = "THENTHIP"
    clave_sol = "enteatell"
    client_id = "aa3f9b5c-7013-4ded-a63a-5ee658ce3530"
    client_secret = "MOIzbzE3lAj/W5EkokXEbA=="
    
    try:
        # PASO 1: OBTENER TOKEN - IGUAL A TU SCRIPT
        token_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
        token_data = {
            'grant_type': 'password',
            'scope': 'https://api-sire.sunat.gob.pe',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': f"{ruc}{usuario}",
            'password': clave_sol
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(token_url, data=token_data, headers=token_headers)
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Error obteniendo token: {token_response.status_code} - {token_response.text}"
                )
            
            token = token_response.json()['access_token']
            
            # PASO 2: CONSULTAR TICKETS - URL EXACTA DE TU SCRIPT
            tickets_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"
            
            tickets_params = {
                'perIni': periodo_ini,
                'perFin': periodo_fin,
                'page': page,
                'perPage': per_page,
                'codLibro': '080000',
                'codOrigenEnvio': '2'
            }
            
            tickets_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            tickets_response = await client.get(
                tickets_url, 
                headers=tickets_headers, 
                params=tickets_params
            )
            
            if tickets_response.status_code == 200:
                data = tickets_response.json()
                return {
                    "exitoso": True,
                    "mensaje": "Tickets consultados exitosamente",
                    "datos": data,
                    "total_registros": data.get('paginacion', {}).get('totalRegistros', 0),
                    "url_usada": tickets_url,
                    "parametros": tickets_params
                }
            else:
                return {
                    "exitoso": False,
                    "mensaje": f"Error de SUNAT: {tickets_response.status_code}",
                    "detalle": tickets_response.text,
                    "url_usada": tickets_url
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get(
    "/sunat/resumen",
    summary="Consulta directa de resumen SUNAT",
    description="Consulta directa al endpoint de resumen de SUNAT SIRE v27 - descarga archivos de período completo"
)
async def consultar_resumen_sunat_directo(
    ruc: str = Query(..., description="RUC de la empresa"),
    per_tributario: str = Query(..., description="Período tributario (AAAAMMDD)", regex=r"^\d{6}$"),
    opcion: str = Query("1", description="Opción de consulta (1=General, 2=Detalle, 3=Errores)"),
    service: RcePropuestaService = Depends(get_rce_propuesta_service)
):
    """
    Consulta directa al endpoint de resumen de SUNAT para RCE
    """
    try:
        # Obtener token vigente usando token_manager (ahora con la colección correcta)
        token = await service.auth_service.token_manager.get_valid_token(ruc)
        if not token:
            raise HTTPException(status_code=401, detail="No se pudo obtener token SUNAT")

        # Parámetros exactos del script
        resumen_params = {
            'numRuc': ruc,
            'perTributario': per_tributario,
            'opcion': opcion
        }
        
        # URL exacta del script 
        resumen_url = 'https://api-sire.sunat.gob.pe/v1/contribuyente/gem/rce/resumenPeriodo'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resumen_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            resumen_response = await client.get(
                resumen_url, 
                headers=resumen_headers, 
                params=resumen_params
            )
            
            if resumen_response.status_code == 200:
                data = resumen_response.json()
                return {
                    "exitoso": True,
                    "mensaje": "Resumen consultado exitosamente",
                    "datos": data,
                    "url_usada": resumen_url,
                    "parametros": resumen_params
                }
            else:
                return {
                    "exitoso": False,
                    "mensaje": f"Error de SUNAT: {resumen_response.status_code}",
                    "detalle": resumen_response.text,
                    "url_usada": resumen_url
                }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
