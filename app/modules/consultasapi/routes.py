"""
Rutas API para consultas de documentos
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
import logging

from .schemas import RucConsultaRequest, DniConsultaRequest, ConsultaEstadoResponse
from .models import RucConsultaResponse, DniConsultaResponse
from .services import SunatService, ReniecService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consultas", tags=["Consultas de Documentos"])

# Instancias de servicios
sunat_service = SunatService()
reniec_service = ReniecService()

@router.get(
    "/estado",
    response_model=ConsultaEstadoResponse,
    summary="Estado de los servicios de consulta"
)
async def get_estado_servicios():
    """
    Obtiene el estado actual de los servicios de consulta SUNAT y RENIEC
    
    Returns:
        Estado de disponibilidad de cada servicio
    """
    try:
        # Verificar estado de servicios
        estado_sunat = await sunat_service.verificar_estado_servicio()
        estado_reniec = await reniec_service.verificar_estado_servicio()
        
        return ConsultaEstadoResponse(
            servicio_sunat=estado_sunat.get("disponible", False),
            servicio_reniec=estado_reniec.get("disponible", False),
            apis_disponibles={
                "sunat": {
                    "principal": 1,
                    "backup": estado_sunat.get("apis_backup", 0),
                    "total": estado_sunat.get("apis_backup", 0) + 1
                },
                "reniec": {
                    "disponibles": estado_reniec.get("apis_disponibles", 0),
                    "endpoints": estado_reniec.get("endpoints", [])
                }
            },
            version="1.0.0",
            endpoints_activos=[
                "/consultas/ruc",
                "/consultas/dni", 
                "/consultas/estado"
            ]
        )
    except Exception as e:
        logger.error(f"Error obteniendo estado de servicios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )

@router.post(
    "/ruc",
    response_model=RucConsultaResponse,
    summary="Consultar RUC en SUNAT"
)
async def consultar_ruc(request: RucConsultaRequest):
    """
    Consulta información de una empresa por su RUC en SUNAT
    
    - **ruc**: RUC de 11 dígitos de la empresa a consultar
    
    Utiliza múltiples APIs para garantizar disponibilidad:
    - API principal: apis.net.pe
    - APIs de respaldo: apisperu.com, sunat.gob.pe
    """
    try:
        logger.info(f"Consultando RUC: {request.ruc}")
        resultado = await sunat_service.consultar_ruc(request.ruc)
        
        if not resultado.success:
            # No lanzar excepción, retornar la respuesta con error
            logger.warning(f"Consulta RUC falló: {resultado.message}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error en consulta RUC {request.ruc}: {e}")
        return RucConsultaResponse(
            success=False,
            message=f"Error interno en consulta: {str(e)}",
            data=None
        )

@router.post(
    "/dni",
    response_model=DniConsultaResponse,
    summary="Consultar DNI en RENIEC"
)
async def consultar_dni(request: DniConsultaRequest):
    """
    Consulta información de una persona por su DNI en RENIEC
    
    - **dni**: DNI de 8 dígitos de la persona a consultar
    
    Utiliza múltiples APIs RENIEC para garantizar disponibilidad.
    """
    try:
        logger.info(f"Consultando DNI: {request.dni}")
        resultado = await reniec_service.consultar_dni(request.dni)
        
        if not resultado.success:
            logger.warning(f"Consulta DNI falló: {resultado.message}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error en consulta DNI {request.dni}: {e}")
        return DniConsultaResponse(
            success=False,
            message=f"Error interno en consulta: {str(e)}",
            data=None
        )

@router.get(
    "/health",
    summary="Health check del módulo",
    include_in_schema=False
)
async def health_check():
    """Health check básico del módulo de consultas"""
    return {
        "status": "healthy",
        "module": "consultasapi",
        "version": "1.0.0",
        "servicios": ["sunat", "reniec"]
    }
