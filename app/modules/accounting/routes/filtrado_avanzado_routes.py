"""
Endpoints de Filtrado Avanzado - Libro Mayor PLE 050200
======================================================

Endpoints REST especializados para filtrado avanzado del Libro Mayor
con múltiples criterios, ordenamiento, agrupación y paginación.

Endpoints implementados:
- POST /filtrado-avanzado: Filtros complejos con criterios múltiples
- GET /buscar-cuentas: Búsqueda de cuentas por patrones
- GET /estadisticas-filtradas: Estadísticas con filtros aplicados
- GET /agrupaciones: Agrupaciones personalizables

Autor: Sistema ERP - FASE 3.2
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field

from ....database import get_database
from ..services.filtrado_avanzado_service import (
    ServiceFiltradoAvanzadoMayor,
    FiltroAvanzado,
    ResultadoFiltrado,
    TipoOrdenamiento,
    CampoOrdenamiento,
    TipoAgrupacion
)
from ..schemas.schemas_mayor import TipoCuentaContable
from app.shared.exceptions import AccountingException

logger = logging.getLogger(__name__)

# Crear router para filtrado avanzado sin prefijo adicional
router_filtrado = APIRouter(tags=["Filtrado Avanzado Libro Mayor"])


# ========================================
# SCHEMAS DE REQUEST/RESPONSE
# ========================================

class FiltroAvanzadoRequest(BaseModel):
    """Schema para request de filtro avanzado"""
    
    # Filtros básicos
    empresa_id: str = Field(..., description="ID de la empresa")
    empresa_ruc: Optional[str] = Field(None, description="RUC de la empresa")
    periodo_desde: Optional[str] = Field(None, description="Período inicial AAAAMM")
    periodo_hasta: Optional[str] = Field(None, description="Período final AAAAMM")
    
    # Filtros de cuenta contable
    codigo_cuenta: Optional[str] = Field(None, description="Código de cuenta específico")
    codigos_cuenta: Optional[List[str]] = Field(None, description="Lista de códigos de cuenta")
    patron_codigo_cuenta: Optional[str] = Field(None, description="Patrón regex para código de cuenta")
    tipo_cuenta: Optional[TipoCuentaContable] = Field(None, description="Tipo de cuenta contable")
    nivel_cuenta: Optional[int] = Field(None, ge=1, le=10, description="Nivel de cuenta (1-10)")
    
    # Filtros de texto
    buscar_texto: Optional[str] = Field(None, description="Búsqueda en descripción")
    buscar_texto_glosa: Optional[str] = Field(None, description="Búsqueda en glosa")
    
    # Filtros de rangos numéricos
    saldo_deudor_min: Optional[Decimal] = Field(None, description="Saldo deudor mínimo")
    saldo_deudor_max: Optional[Decimal] = Field(None, description="Saldo deudor máximo")
    saldo_acreedor_min: Optional[Decimal] = Field(None, description="Saldo acreedor mínimo")
    saldo_acreedor_max: Optional[Decimal] = Field(None, description="Saldo acreedor máximo")
    movimiento_debe_min: Optional[Decimal] = Field(None, description="Movimiento debe mínimo")
    movimiento_debe_max: Optional[Decimal] = Field(None, description="Movimiento debe máximo")
    movimiento_haber_min: Optional[Decimal] = Field(None, description="Movimiento haber mínimo")
    movimiento_haber_max: Optional[Decimal] = Field(None, description="Movimiento haber máximo")
    
    # Filtros de fechas
    fecha_desde: Optional[date] = Field(None, description="Fecha desde")
    fecha_hasta: Optional[date] = Field(None, description="Fecha hasta")
    incluir_saldos_cero: bool = Field(True, description="Incluir cuentas con saldo cero")
    solo_con_movimientos: bool = Field(False, description="Solo cuentas con movimientos")
    
    # Opciones de resultado
    ordenar_por: CampoOrdenamiento = Field(CampoOrdenamiento.CODIGO_CUENTA, description="Campo para ordenar")
    tipo_orden: TipoOrdenamiento = Field(TipoOrdenamiento.ASCENDENTE, description="Tipo de ordenamiento")
    agrupar_por: Optional[TipoAgrupacion] = Field(None, description="Tipo de agrupación")
    limite: Optional[int] = Field(None, ge=1, le=1000, description="Límite de registros")
    offset: Optional[int] = Field(None, ge=0, description="Offset para paginación")
    
    # Opciones de formato
    incluir_totales: bool = Field(True, description="Incluir totales calculados")
    incluir_estadisticas: bool = Field(False, description="Incluir estadísticas detalladas")


class BusquedaCuentasRequest(BaseModel):
    """Schema para búsqueda de cuentas"""
    
    empresa_id: str = Field(..., description="ID de la empresa")
    patron_busqueda: str = Field(..., min_length=1, description="Patrón de búsqueda")
    buscar_en_codigo: bool = Field(True, description="Buscar en código de cuenta")
    buscar_en_descripcion: bool = Field(True, description="Buscar en descripción")
    limite: int = Field(20, ge=1, le=100, description="Límite de resultados")


class EstadisticasFiltradas(BaseModel):
    """Schema para estadísticas filtradas"""
    
    total_cuentas: int
    total_saldo_deudor: Decimal
    total_saldo_acreedor: Decimal
    total_movimiento_debe: Decimal
    total_movimiento_haber: Decimal
    diferencia_balance: Decimal
    cuentas_con_saldo_deudor: int
    cuentas_con_saldo_acreedor: int
    porcentaje_balance: float


# ========================================
# ENDPOINTS
# ========================================

@router_filtrado.post(
    "/filtrado-avanzado/aplicar",
    response_model=Dict[str, Any],
    summary="Aplicar filtro avanzado",
    description="Aplicar filtros avanzados al Libro Mayor con múltiples criterios de búsqueda"
)
async def aplicar_filtro_avanzado(
    filtro_request: FiltroAvanzadoRequest,
    db=Depends(get_database)
):
    """Aplicar filtro avanzado al Libro Mayor"""
    try:
        logger.info(f"Aplicando filtro avanzado - Empresa: {filtro_request.empresa_id}")
        
        # Crear servicio de filtrado
        service_filtrado = ServiceFiltradoAvanzadoMayor(db.client, db.name)
        
        # Convertir request a FiltroAvanzado
        filtro = FiltroAvanzado(
            empresa_id=filtro_request.empresa_id,
            empresa_ruc=filtro_request.empresa_ruc,
            periodo_desde=filtro_request.periodo_desde,
            periodo_hasta=filtro_request.periodo_hasta,
            codigo_cuenta=filtro_request.codigo_cuenta,
            codigos_cuenta=filtro_request.codigos_cuenta,
            patron_codigo_cuenta=filtro_request.patron_codigo_cuenta,
            tipo_cuenta=filtro_request.tipo_cuenta,
            nivel_cuenta=filtro_request.nivel_cuenta,
            buscar_texto=filtro_request.buscar_texto,
            buscar_texto_glosa=filtro_request.buscar_texto_glosa,
            saldo_deudor_min=filtro_request.saldo_deudor_min,
            saldo_deudor_max=filtro_request.saldo_deudor_max,
            saldo_acreedor_min=filtro_request.saldo_acreedor_min,
            saldo_acreedor_max=filtro_request.saldo_acreedor_max,
            movimiento_debe_min=filtro_request.movimiento_debe_min,
            movimiento_debe_max=filtro_request.movimiento_debe_max,
            movimiento_haber_min=filtro_request.movimiento_haber_min,
            movimiento_haber_max=filtro_request.movimiento_haber_max,
            fecha_desde=filtro_request.fecha_desde,
            fecha_hasta=filtro_request.fecha_hasta,
            incluir_saldos_cero=filtro_request.incluir_saldos_cero,
            solo_con_movimientos=filtro_request.solo_con_movimientos,
            ordenar_por=filtro_request.ordenar_por,
            tipo_orden=filtro_request.tipo_orden,
            agrupar_por=filtro_request.agrupar_por,
            limite=filtro_request.limite,
            offset=filtro_request.offset,
            incluir_totales=filtro_request.incluir_totales,
            incluir_estadisticas=filtro_request.incluir_estadisticas
        )
        
        # Aplicar filtro
        resultado = await service_filtrado.aplicar_filtro_avanzado(filtro)
        
        # Preparar respuesta
        response = {
            "exito": True,
            "mensaje": f"Filtro aplicado: {resultado.total_registros} registros encontrados",
            "total_registros": resultado.total_registros,
            "registros": [
                {
                    "codigo_cuenta": registro.codigo_cuenta_contable,
                    "descripcion_cuenta": registro.descripcion_cuenta,
                    "periodo_desde": registro.periodo_desde.isoformat() if registro.periodo_desde else None,
                    "periodo_hasta": registro.periodo_hasta.isoformat() if registro.periodo_hasta else None,
                    "saldo_deudor_inicial": float(registro.saldo_deudor_inicial),
                    "saldo_acreedor_inicial": float(registro.saldo_acreedor_inicial),
                    "movimiento_debe": float(registro.movimiento_debe),
                    "movimiento_haber": float(registro.movimiento_haber),
                    "saldo_final_deudor": float(registro.saldo_final_deudor),
                    "saldo_final_acreedor": float(registro.saldo_final_acreedor),
                    "estado": registro.estado.value if hasattr(registro.estado, 'value') else str(registro.estado)
                }
                for registro in resultado.registros
            ]
        }
        
        # Agregar totales si están incluidos
        if filtro_request.incluir_totales:
            response["totales"] = {
                "total_saldo_deudor": float(resultado.total_saldo_deudor),
                "total_saldo_acreedor": float(resultado.total_saldo_acreedor),
                "total_movimiento_debe": float(resultado.total_movimiento_debe),
                "total_movimiento_haber": float(resultado.total_movimiento_haber),
                "diferencia_balance": float(abs(resultado.total_movimiento_debe - resultado.total_movimiento_haber))
            }
        
        # Agregar paginación si aplica
        if resultado.total_paginas:
            response["paginacion"] = {
                "total_paginas": resultado.total_paginas,
                "pagina_actual": resultado.pagina_actual,
                "limite": filtro_request.limite,
                "offset": filtro_request.offset
            }
        
        # Agregar estadísticas si están incluidas
        if resultado.estadisticas:
            response["estadisticas"] = resultado.estadisticas
        
        # Agregar agrupaciones si están incluidas
        if resultado.agrupaciones:
            response["agrupaciones"] = resultado.agrupaciones
        
        logger.info(f"Filtro aplicado exitosamente: {resultado.total_registros} registros")
        
        return response
        
    except AccountingException as e:
        logger.error(f"Error en filtro avanzado: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno en filtro avanzado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router_filtrado.post(
    "/filtrado-avanzado/buscar-cuentas",
    response_model=Dict[str, Any],
    summary="Buscar cuentas contables",
    description="Buscar cuentas contables por patrón en código o descripción"
)
async def buscar_cuentas_contables(
    busqueda_request: BusquedaCuentasRequest,
    db=Depends(get_database)
):
    """Buscar cuentas contables por patrón"""
    try:
        logger.info(f"Buscando cuentas - Patrón: {busqueda_request.patron_busqueda}")
        
        # Crear servicio de filtrado
        service_filtrado = ServiceFiltradoAvanzadoMayor(db.client, db.name)
        
        # Construir filtro para búsqueda
        filtro = FiltroAvanzado(
            empresa_id=busqueda_request.empresa_id,
            limite=busqueda_request.limite
        )
        
        # Configurar búsqueda según opciones
        if busqueda_request.buscar_en_codigo and busqueda_request.buscar_en_descripcion:
            # Buscar en ambos campos - esto requeriría lógica especial
            filtro.patron_codigo_cuenta = busqueda_request.patron_busqueda
            filtro.buscar_texto = busqueda_request.patron_busqueda
        elif busqueda_request.buscar_en_codigo:
            filtro.patron_codigo_cuenta = busqueda_request.patron_busqueda
        elif busqueda_request.buscar_en_descripcion:
            filtro.buscar_texto = busqueda_request.patron_busqueda
        
        # Aplicar filtro
        resultado = await service_filtrado.aplicar_filtro_avanzado(filtro)
        
        # Preparar respuesta
        cuentas_encontradas = [
            {
                "codigo_cuenta": registro.codigo_cuenta_contable,
                "descripcion_cuenta": registro.descripcion_cuenta,
                "saldo_final_deudor": float(registro.saldo_final_deudor),
                "saldo_final_acreedor": float(registro.saldo_final_acreedor),
                "tiene_movimientos": registro.movimiento_debe > 0 or registro.movimiento_haber > 0
            }
            for registro in resultado.registros
        ]
        
        response = {
            "exito": True,
            "patron_busqueda": busqueda_request.patron_busqueda,
            "total_encontradas": len(cuentas_encontradas),
            "cuentas": cuentas_encontradas
        }
        
        logger.info(f"Búsqueda completada: {len(cuentas_encontradas)} cuentas encontradas")
        
        return response
        
    except Exception as e:
        logger.error(f"Error en búsqueda de cuentas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router_filtrado.get(
    "/filtrado-avanzado/estadisticas",
    response_model=Dict[str, Any],
    summary="Obtener estadísticas filtradas",
    description="Obtener estadísticas del Libro Mayor con filtros aplicados"
)
async def obtener_estadisticas_filtradas(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_desde: Optional[str] = Query(None, description="Período inicial AAAAMM"),
    periodo_hasta: Optional[str] = Query(None, description="Período final AAAAMM"),
    tipo_cuenta: Optional[TipoCuentaContable] = Query(None, description="Tipo de cuenta"),
    incluir_saldos_cero: bool = Query(True, description="Incluir cuentas con saldo cero"),
    db=Depends(get_database)
):
    """Obtener estadísticas filtradas del Libro Mayor"""
    try:
        logger.info(f"Obteniendo estadísticas filtradas - Empresa: {empresa_id}")
        
        # Crear servicio de filtrado
        service_filtrado = ServiceFiltradoAvanzadoMayor(db.client, db.name)
        
        # Crear filtro para estadísticas
        filtro = FiltroAvanzado(
            empresa_id=empresa_id,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            tipo_cuenta=tipo_cuenta,
            incluir_saldos_cero=incluir_saldos_cero,
            incluir_estadisticas=True,
            incluir_totales=True
        )
        
        # Aplicar filtro
        resultado = await service_filtrado.aplicar_filtro_avanzado(filtro)
        
        # Calcular estadísticas adicionales
        diferencia_balance = abs(resultado.total_movimiento_debe - resultado.total_movimiento_haber)
        porcentaje_balance = 0.0
        if resultado.total_movimiento_debe > 0:
            porcentaje_balance = float((diferencia_balance / resultado.total_movimiento_debe) * 100)
        
        response = {
            "exito": True,
            "empresa_id": empresa_id,
            "periodo_desde": periodo_desde,
            "periodo_hasta": periodo_hasta,
            "estadisticas": {
                "total_cuentas": resultado.total_registros,
                "total_saldo_deudor": float(resultado.total_saldo_deudor),
                "total_saldo_acreedor": float(resultado.total_saldo_acreedor),
                "total_movimiento_debe": float(resultado.total_movimiento_debe),
                "total_movimiento_haber": float(resultado.total_movimiento_haber),
                "diferencia_balance": float(diferencia_balance),
                "porcentaje_diferencia": porcentaje_balance,
                "cuentas_con_saldo_deudor": len([r for r in resultado.registros if r.saldo_final_deudor > 0]),
                "cuentas_con_saldo_acreedor": len([r for r in resultado.registros if r.saldo_final_acreedor > 0]),
                "balance_correcto": diferencia_balance <= Decimal('0.01')
            }
        }
        
        # Agregar estadísticas avanzadas si están disponibles
        if resultado.estadisticas:
            response["estadisticas_avanzadas"] = resultado.estadisticas
        
        logger.info(f"Estadísticas calculadas para {resultado.total_registros} cuentas")
        
        return response
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router_filtrado.get(
    "/filtrado-avanzado/agrupaciones/{tipo_agrupacion}",
    response_model=Dict[str, Any],
    summary="Obtener agrupaciones",
    description="Obtener agrupaciones del Libro Mayor por diferentes criterios"
)
async def obtener_agrupaciones(
    tipo_agrupacion: TipoAgrupacion,
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_desde: Optional[str] = Query(None, description="Período inicial AAAAMM"),
    periodo_hasta: Optional[str] = Query(None, description="Período final AAAAMM"),
    db=Depends(get_database)
):
    """Obtener agrupaciones del Libro Mayor"""
    try:
        logger.info(f"Obteniendo agrupaciones {tipo_agrupacion.value} - Empresa: {empresa_id}")
        
        # Crear servicio de filtrado
        service_filtrado = ServiceFiltradoAvanzadoMayor(db.client, db.name)
        
        # Crear filtro para agrupaciones
        filtro = FiltroAvanzado(
            empresa_id=empresa_id,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            agrupar_por=tipo_agrupacion,
            incluir_totales=True
        )
        
        # Aplicar filtro
        resultado = await service_filtrado.aplicar_filtro_avanzado(filtro)
        
        response = {
            "exito": True,
            "tipo_agrupacion": tipo_agrupacion.value,
            "empresa_id": empresa_id,
            "total_registros": resultado.total_registros,
            "agrupaciones": resultado.agrupaciones or {},
            "totales_generales": {
                "total_movimiento_debe": float(resultado.total_movimiento_debe),
                "total_movimiento_haber": float(resultado.total_movimiento_haber),
                "total_saldo_deudor": float(resultado.total_saldo_deudor),
                "total_saldo_acreedor": float(resultado.total_saldo_acreedor)
            }
        }
        
        logger.info(f"Agrupaciones calculadas: {len(resultado.agrupaciones or {})} grupos")
        
        return response
        
    except Exception as e:
        logger.error(f"Error obteniendo agrupaciones: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# Agregar el router de filtrado avanzado al router principal del módulo accounting
def add_filtrado_routes(main_router: APIRouter):
    """Agregar rutas de filtrado avanzado al router principal"""
    main_router.include_router(router_filtrado)
