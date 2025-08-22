"""
Rutas API para gestión de comprobantes RVIE (Ventas) en base de datos
Endpoints para CRUD y consultas de datos guardados localmente
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from ....core.dependencies import get_database
from ..services.rvie_comprobante_bd_service import RvieComprobanteBDService
from ..models.rvie_comprobante_bd import RvieComprobanteBDResponse, RvieEstadisticas
from ....shared.exceptions import SireException, SireValidationException

router = APIRouter(tags=["RVIE - Base de Datos"])


@router.get("/{ruc}/comprobantes", response_model=Dict[str, Any])
async def consultar_comprobantes(
    ruc: str,
    periodo: str = Query(..., description="Período YYYYMM"),
    skip: int = Query(0, ge=0, description="Registros a saltar para paginación"),
    por_pagina: int = Query(50, ge=1, le=2000, description="Comprobantes por página"),
    tipo_documento: Optional[str] = Query(None, description="Filtrar por tipo de documento"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    cliente_ruc: Optional[str] = Query(None, description="Filtrar por RUC del cliente"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    monto_min: Optional[float] = Query(None, description="Monto mínimo"),
    monto_max: Optional[float] = Query(None, description="Monto máximo"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Consultar comprobantes RVIE guardados en base de datos
    
    Permite filtrar y paginar los comprobantes de ventas almacenados localmente.
    """
    try:
        service = RvieComprobanteBDService(db)
        
        # Construir filtros
        filtros = {}
        if tipo_documento:
            filtros["tipo_documento"] = tipo_documento
        if estado:
            filtros["estado"] = estado
        if cliente_ruc:
            filtros["cliente_ruc"] = cliente_ruc
        if fecha_desde:
            filtros["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filtros["fecha_hasta"] = fecha_hasta
        if monto_min is not None:
            filtros["monto_min"] = monto_min
        if monto_max is not None:
            filtros["monto_max"] = monto_max
        
        resultado = await service.consultar_comprobantes(
            ruc, periodo, skip, por_pagina, filtros
        )
        
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{ruc}/estadisticas", response_model=Dict[str, Any])
async def obtener_estadisticas(
    ruc: str,
    periodo: str = Query(..., description="Período YYYYMM"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener estadísticas de comprobantes RVIE guardados
    
    Retorna resúmenes y totales de los comprobantes de ventas en base de datos.
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.obtener_estadisticas(ruc, periodo)
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{ruc}/estado", response_model=Dict[str, Any])
async def verificar_estado_bd(
    ruc: str,
    periodo: str = Query(..., description="Período YYYYMM"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verificar el estado de la base de datos para un RUC y período
    
    Útil para determinar si hay datos guardados antes de mostrar la interfaz.
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.verificar_estado_bd(ruc, periodo)
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/{ruc}/comprobantes/{comprobante_id}", response_model=Dict[str, Any])
async def obtener_comprobante(
    ruc: str,
    comprobante_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Obtener un comprobante específico por ID
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.obtener_comprobante(comprobante_id)
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/{ruc}/comprobantes/{comprobante_id}", response_model=Dict[str, Any])
async def eliminar_comprobante(
    ruc: str,
    comprobante_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Eliminar un comprobante específico de la base de datos
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.eliminar_comprobante(comprobante_id)
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/{ruc}/periodo/{periodo}", response_model=Dict[str, Any])
async def limpiar_periodo(
    ruc: str,
    periodo: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Limpiar todos los comprobantes de un período específico
    
    ⚠️ Esta operación elimina TODOS los comprobantes del período indicado.
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.limpiar_periodo(ruc, periodo)
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/{ruc}/guardar-desde-sunat", response_model=Dict[str, Any])
async def guardar_comprobantes_desde_sunat(
    ruc: str,
    comprobantes: List[Dict[str, Any]], 
    periodo: str = Query(..., description="Período YYYYMM"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Guardar comprobantes desde datos obtenidos de SUNAT
    
    Este endpoint se usa internamente después de una consulta exitosa a SUNAT.
    """
    try:
        service = RvieComprobanteBDService(db)
        resultado = await service.guardar_comprobantes_desde_consulta(
            ruc, periodo, comprobantes
        )
        return resultado
        
    except SireValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
