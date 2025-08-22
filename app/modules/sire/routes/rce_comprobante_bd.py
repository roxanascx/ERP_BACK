"""
Rutas API para gestión de comprobantes RCE en base de datos - OPTIMIZADO
Endpoints RESTful para CRUD de comprobantes con cache inteligente
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from ..services.rce_comprobante_bd_service import RceComprobanteBDService
from ..models.rce_comprobante_bd import (
    RceComprobanteBDCreate,
    RceComprobanteBDResponse,
    RceGuardarResponse,
    RceEstadisticasBD
)
from ....core.dependencies import get_database
from ....shared.exceptions import SireException

router = APIRouter(prefix="/bd", tags=["RCE Base de Datos"])


async def get_rce_comprobante_service() -> RceComprobanteBDService:
    """Dependencia para obtener el servicio de comprobantes BD"""
    from ..repositories.rce_comprobante_bd_repository import RceComprobanteBDRepository
    from ..services.rce_compras_service import RceComprasService
    from ..services.api_client import SunatApiClient
    from ..services.auth_service import SireAuthService
    from ..services.token_manager import SireTokenManager
    from ....database import get_database_connection
    
    # Obtener la conexión directa a la base de datos
    db = await get_database_connection()
    
    # Crear instancias de dependencias
    api_client = SunatApiClient()
    token_manager = SireTokenManager(db)
    auth_service = SireAuthService(api_client, token_manager)
    
    # Crear instancias con la base de datos real
    repository = RceComprobanteBDRepository(db)
    rce_service = RceComprasService(db, api_client, auth_service)
    
    return RceComprobanteBDService(repository, rce_service)


@router.get(
    "/{ruc}/comprobantes",
    response_model=dict,
    summary="Consultar comprobantes almacenados",
    description="Obtener comprobantes guardados con filtros y paginación"
)
async def consultar_comprobantes(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Período YYYYMM"),
    ruc_proveedor: Optional[str] = Query(None, description="RUC del proveedor"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta YYYY-MM-DD"),
    estado: Optional[str] = Query(None, description="Estado del comprobante"),
    pagina: int = Query(1, ge=1, description="Número de página"),
    por_pagina: int = Query(50, ge=1, le=2000, description="Comprobantes por página"),
    service: RceComprobanteBDService = Depends(get_rce_comprobante_service)
):
    """Consultar comprobantes con filtros"""
    try:
        resultado = await service.consultar_comprobantes(
            ruc=ruc,
            periodo=periodo,
            ruc_proveedor=ruc_proveedor,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=estado,
            pagina=pagina,
            por_pagina=por_pagina
        )
        return resultado
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/{ruc}/comprobantes/guardar",
    response_model=RceGuardarResponse,
    summary="Guardar comprobantes (OPTIMIZADO)",
    description="Guardar comprobantes evitando consultas duplicadas a SUNAT"
)
async def guardar_comprobantes(
    ruc: str,
    request_data: dict,
    service: RceComprobanteBDService = Depends(get_rce_comprobante_service)
):
    """
    Endpoint OPTIMIZADO para guardar comprobantes
    
    Flujo:
    1. Si se envían comprobantes en el body → Usar esos (desde cache/vista)
    2. Si no hay comprobantes → Verificar si ya existen en BD
    3. Solo si no existen → Consultar SUNAT
    """
    try:
        periodo = request_data.get('periodo')
        comprobantes = request_data.get('comprobantes')
        
        if not periodo:
            raise HTTPException(status_code=400, detail="El campo 'periodo' es requerido")
        
        # CASO 1: Guardar desde cache/vista (SIN consulta a SUNAT)
        if comprobantes:
            resultado = await service.guardar_comprobantes_desde_cache(
                ruc, periodo, comprobantes
            )
            resultado.mensaje = f"✅ Guardado desde cache/vista: {resultado.mensaje}"
            return resultado
        
        # CASO 2: Verificar si ya existen en BD
        existe = await service.verificar_datos_existentes(ruc, periodo)
        if existe:
            return RceGuardarResponse(
                exitoso=True,
                mensaje="✅ Los datos ya existen en la base de datos (consulta evitada)",
                total_procesados=0,
                total_nuevos=0,
                total_actualizados=0,
                total_errores=0
            )
        
        # CASO 3: Solo si no existen, consultar SUNAT
        comprobantes_sunat = await service.rce_service.obtener_comprobantes_detallados(ruc, periodo)
        
        if not comprobantes_sunat.exitoso:
            raise HTTPException(
                status_code=400, 
                detail=f"Error obteniendo datos de SUNAT: {comprobantes_sunat.mensaje}"
            )
        
        resultado = await service.guardar_comprobantes_desde_sunat(
            ruc, periodo, comprobantes_sunat.comprobantes
        )
        resultado.mensaje = f"✅ Nueva consulta SUNAT necesaria: {resultado.mensaje}"
        return resultado
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/{ruc}/estadisticas",
    response_model=RceEstadisticasBD,
    summary="Estadísticas de comprobantes",
    description="Obtener estadísticas de comprobantes almacenados"
)
async def obtener_estadisticas(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Período específico YYYYMM"),
    service: RceComprobanteBDService = Depends(get_rce_comprobante_service)
):
    """Obtener estadísticas de comprobantes guardados"""
    try:
        estadisticas = await service.obtener_estadisticas(ruc, periodo)
        return estadisticas
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")