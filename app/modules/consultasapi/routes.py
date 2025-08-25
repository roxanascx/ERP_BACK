"""
Rutas API para consultas de documentos y tipos de cambio
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from typing import Dict, Any, Optional
from datetime import date, timedelta
import logging

from .schemas import (
    RucConsultaRequest, DniConsultaRequest, ConsultaEstadoResponse,
    # Schemas de tipos de cambio
    ExchangeRateRequest, ExchangeRateResponse, ExchangeRateListResponse,
    ExchangeRateQuery, ActualizarTiposCambioRequest, ActualizarTiposCambioResponse
)
from .models import RucConsultaResponse, DniConsultaResponse
from .services import SunatService, ReniecService, ExchangeRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consultas", tags=["Consultas de Documentos"])

# Instancias de servicios
sunat_service = SunatService()
reniec_service = ReniecService()
exchange_rate_service = ExchangeRateService()

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
        "version": "1.1.0",
        "servicios": ["sunat", "reniec", "tipos_cambio"]
    }


# ===========================================
# RUTAS PARA TIPOS DE CAMBIO
# ===========================================

@router.get(
    "/tipos-cambio",
    response_model=ExchangeRateListResponse,
    summary="Listar tipos de cambio con filtros"
)
async def listar_tipos_cambio(
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    moneda_origen: Optional[str] = Query(None, description="Código moneda origen (ej: USD)"),
    moneda_destino: Optional[str] = Query(None, description="Código moneda destino (ej: PEN)"),
    fuente: Optional[str] = Query(None, description="Fuente de datos (ej: eApiPeru)"),
    es_oficial: Optional[bool] = Query(None, description="Solo tipos de cambio oficiales"),
    es_activo: Optional[bool] = Query(True, description="Solo tipos de cambio activos"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página")
):
    """
    Lista tipos de cambio con filtros y paginación
    
    - **fecha_desde/fecha_hasta**: Rango de fechas
    - **moneda_origen/moneda_destino**: Filtrar por par de monedas
    - **fuente**: Filtrar por fuente de datos
    - **es_oficial**: Solo tipos de cambio oficiales
    - **es_activo**: Solo registros activos
    """
    try:
        query = ExchangeRateQuery(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            moneda_origen=moneda_origen,
            moneda_destino=moneda_destino,
            fuente=fuente,
            es_oficial=es_oficial,
            es_activo=es_activo
        )
        
        tipos_cambio, total = await exchange_rate_service.repository.list_exchange_rates(
            query, page, size
        )
        
        total_pages = (total + size - 1) // size
        
        return ExchangeRateListResponse(
            tipos_cambio=[ExchangeRateResponse.model_validate(tc) for tc in tipos_cambio],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error listando tipos de cambio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/tipos-cambio/actual",
    response_model=ExchangeRateResponse,
    summary="Obtener tipo de cambio actual"
)
async def obtener_tipo_cambio_actual(
    moneda_origen: str = Query("USD", description="Código moneda origen"),
    moneda_destino: str = Query("PEN", description="Código moneda destino")
):
    """
    Obtiene el tipo de cambio más actual disponible
    
    Si no existe para hoy, intenta consultarlo de la API externa.
    Si aún no está disponible, retorna el más reciente.
    """
    try:
        tipo_cambio = await exchange_rate_service.get_tipo_cambio_actual(
            moneda_origen, moneda_destino
        )
        
        if not tipo_cambio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró tipo de cambio para {moneda_origen} -> {moneda_destino}"
            )
        
        return ExchangeRateResponse.model_validate(tipo_cambio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tipo de cambio actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/tipos-cambio/estado",
    summary="Estado del servicio de tipos de cambio"
)
async def estado_tipos_cambio():
    """
    Obtiene el estado actual del servicio de tipos de cambio
    
    Incluye disponibilidad de API externa y estadísticas de base de datos
    """
    try:
        estado = await exchange_rate_service.verificar_estado_servicio()
        return estado
        
    except Exception as e:
        logger.error(f"Error verificando estado de tipos de cambio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/tipos-cambio/{fecha}",
    response_model=ExchangeRateResponse,
    summary="Obtener tipo de cambio por fecha"
)
async def obtener_tipo_cambio_por_fecha(
    fecha: date = Path(..., description="Fecha en formato YYYY-MM-DD"),
    moneda_origen: str = Query("USD", description="Código moneda origen"),
    moneda_destino: str = Query("PEN", description="Código moneda destino")
):
    """
    Obtiene el tipo de cambio para una fecha específica
    
    Si no existe en la base de datos, intenta consultarlo de la API externa
    """
    try:
        # Validar que no sea fecha futura
        if fecha > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede consultar tipo de cambio de fechas futuras"
            )
        
        # Buscar en base de datos
        tipo_cambio = await exchange_rate_service.repository.get_exchange_rate_by_date(
            fecha, moneda_origen, moneda_destino
        )
        
        # Si no existe, intentar consultar de API externa
        if not tipo_cambio:
            logger.info(f"Tipo de cambio para {fecha} no existe, consultando API externa")
            resultado = await exchange_rate_service.actualizar_tipo_cambio_dia(fecha)
            
            if resultado["success"] and resultado["data"]:
                tipo_cambio = resultado["data"]
        
        if not tipo_cambio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró tipo de cambio para {fecha}"
            )
        
        return ExchangeRateResponse.model_validate(tipo_cambio)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo tipo de cambio para {fecha}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.post(
    "/tipos-cambio/actualizar",
    response_model=ActualizarTiposCambioResponse,
    summary="Actualizar tipos de cambio manualmente"
)
async def actualizar_tipos_cambio(
    request: ActualizarTiposCambioRequest
):
    """
    Actualiza tipos de cambio manualmente para un rango de fechas
    
    - **fecha_desde/fecha_hasta**: Rango de fechas a actualizar
    - **forzar_actualizacion**: Si actualizar registros existentes
    """
    try:
        fecha_desde = request.fecha_desde or date.today()
        fecha_hasta = request.fecha_hasta or date.today()
        
        # Validar rango de fechas
        if fecha_hasta < fecha_desde:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecha_hasta debe ser mayor o igual a fecha_desde"
            )
        
        # Validar que no sean fechas muy futuras
        if fecha_desde > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden actualizar fechas futuras"
            )
        
        # Limitar rango máximo (ej: 90 días)
        dias_diferencia = (fecha_hasta - fecha_desde).days
        if dias_diferencia > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rango de fechas no puede ser mayor a 90 días"
            )
        
        resultado = await exchange_rate_service.poblar_datos_historicos(
            fecha_desde, fecha_hasta, request.forzar_actualizacion
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando tipos de cambio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.post(
    "/tipos-cambio/poblar-historicos",
    response_model=ActualizarTiposCambioResponse,
    summary="Poblar datos históricos de tipos de cambio"
)
async def poblar_datos_historicos(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    forzar_actualizacion: bool = Query(False, description="Forzar actualización de existentes")
):
    """
    Pobla datos históricos de tipos de cambio desde la API externa
    
    Útil para cargar datos masivos como el script de agosto que demostró 100% éxito
    """
    try:
        # Validaciones
        if fecha_fin < fecha_inicio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fecha_fin debe ser mayor o igual a fecha_inicio"
            )
        
        if fecha_inicio > date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden poblar fechas futuras"
            )
        
        # Limitar rango para evitar sobrecarga
        dias_diferencia = (fecha_fin - fecha_inicio).days
        if dias_diferencia > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rango de fechas no puede ser mayor a 365 días"
            )
        
        logger.info(f"Iniciando población histórica desde {fecha_inicio} hasta {fecha_fin}")
        
        resultado = await exchange_rate_service.poblar_datos_historicos(
            fecha_inicio, fecha_fin, forzar_actualizacion
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error poblando datos históricos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get(
    "/tipos-cambio/estado",
    summary="Estado del servicio de tipos de cambio"
)
async def estado_tipos_cambio():
    """
    Obtiene el estado actual del servicio de tipos de cambio
    
    Incluye disponibilidad de API externa y estadísticas de base de datos
    """
    try:
        estado = await exchange_rate_service.verificar_estado_servicio()
        return estado
        
    except Exception as e:
        logger.error(f"Error verificando estado de tipos de cambio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )
