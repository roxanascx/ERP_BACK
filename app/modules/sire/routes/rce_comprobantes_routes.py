"""
RCE Comprobantes Routes - Endpoints para gestión de comprobantes RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import io

from ....database import get_database
from ....shared.exceptions import SireException, SireValidationException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..schemas.rce_schemas import (
    RceComprobanteCreateRequest, RceComprobanteResponse,
    RceConsultaRequest, RceConsultaResponse,
    RceApiResponse, RceErrorResponse
)

router = APIRouter()


def get_rce_compras_service(db=Depends(get_database)) -> RceComprasService:
    """Dependency para obtener el servicio de comprobantes RCE"""
    api_client = SunatApiClient()
    auth_service = SireAuthService(db, api_client)
    return RceComprasService(db, api_client, auth_service)


@router.post(
    "/comprobantes",
    response_model=RceApiResponse,
    summary="Crear comprobante RCE",
    description="Crear un nuevo comprobante de compra RCE"
)
async def crear_comprobante(
    ruc: str,
    request: RceComprobanteCreateRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Crear un nuevo comprobante RCE
    
    - **ruc**: RUC del contribuyente
    - **request**: Datos del comprobante a crear
    """
    try:
        comprobante = await service.crear_comprobante(ruc, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante creado exitosamente",
            datos=comprobante
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


@router.put(
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Actualizar comprobante RCE",
    description="Actualizar un comprobante RCE existente"
)
async def actualizar_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    request: RceComprobanteCreateRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Actualizar un comprobante RCE existente
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    - **request**: Nuevos datos del comprobante
    """
    try:
        comprobante = await service.actualizar_comprobante(ruc, correlativo, periodo, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante actualizado exitosamente",
            datos=comprobante
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
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Obtener comprobante RCE",
    description="Obtener un comprobante RCE específico"
)
async def obtener_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener un comprobante RCE específico
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    """
    try:
        comprobante = await service.obtener_comprobante(ruc, correlativo, periodo)
        
        if not comprobante:
            return RceApiResponse(
                exitoso=False,
                mensaje="Comprobante no encontrado",
                codigo="NOT_FOUND"
            )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante encontrado",
            datos=comprobante
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
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Eliminar comprobante RCE",
    description="Eliminar un comprobante RCE"
)
async def eliminar_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Eliminar un comprobante RCE
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    """
    try:
        eliminado = await service.eliminar_comprobante(ruc, correlativo, periodo)
        
        return RceApiResponse(
            exitoso=eliminado,
            mensaje="Comprobante eliminado exitosamente" if eliminado else "No se pudo eliminar el comprobante"
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
    "/comprobantes/consultar",
    response_model=RceConsultaResponse,
    summary="Consultar comprobantes RCE",
    description="Consultar comprobantes RCE con filtros y paginación"
)
async def consultar_comprobantes(
    ruc: str,
    request: RceConsultaRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Consultar comprobantes RCE con filtros avanzados
    
    - **ruc**: RUC del contribuyente
    - **request**: Filtros de consulta y parámetros de paginación
    """
    try:
        resultado = await service.consultar_comprobantes(ruc, request)
        return resultado
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/comprobantes/validar-lote",
    response_model=RceApiResponse,
    summary="Validar lote de comprobantes",
    description="Validar un lote de comprobantes RCE y devolver válidos e inconsistencias"
)
async def validar_lote_comprobantes(
    ruc: str,
    comprobantes: List[RceComprobanteCreateRequest],
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Validar un lote de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **comprobantes**: Lista de comprobantes a validar
    """
    try:
        comprobantes_validos, inconsistencias = await service.validar_comprobantes_lote(ruc, comprobantes)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Validación completada: {len(comprobantes_validos)} válidos, {len(inconsistencias)} inconsistencias",
            datos={
                "comprobantes_validos": len(comprobantes_validos),
                "total_comprobantes": len(comprobantes),
                "inconsistencias": [inc.dict() for inc in inconsistencias],
                "comprobantes_validos_detalle": [comp.dict() for comp in comprobantes_validos]
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
    "/comprobantes/exportar/csv",
    summary="Exportar comprobantes a CSV",
    description="Exportar comprobantes RCE a formato CSV"
)
async def exportar_comprobantes_csv(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo YYYYMM"),
    periodo_inicio: Optional[str] = Query(None, description="Periodo inicio YYYYMM"),
    periodo_fin: Optional[str] = Query(None, description="Periodo fin YYYYMM"),
    tipo_comprobante: Optional[List[str]] = Query(None, description="Tipos de comprobante"),
    solo_con_credito_fiscal: Optional[bool] = Query(None, description="Solo con crédito fiscal"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Exportar comprobantes RCE a formato CSV
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **periodo_inicio**: Periodo inicio para rango (opcional)
    - **periodo_fin**: Periodo fin para rango (opcional)
    - **tipo_comprobante**: Filtrar por tipos de comprobante (opcional)
    - **solo_con_credito_fiscal**: Solo comprobantes con crédito fiscal (opcional)
    """
    try:
        # Importar desde consulta service para evitar dependencia circular
        from ..services.rce_consulta_service import RceConsultaService
        from ..models.rce import RceTipoComprobante
        
        # Crear servicio de consulta
        api_client = SunatApiClient()
        auth_service = SireAuthService(service.db, api_client)
        consulta_service = RceConsultaService(service.db, api_client, auth_service, service)
        
        # Preparar request de consulta
        tipos_enum = None
        if tipo_comprobante:
            tipos_enum = [RceTipoComprobante(tc) for tc in tipo_comprobante]
        
        consulta_request = RceConsultaRequest(
            ruc=ruc,
            periodo=periodo,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            tipo_comprobante=tipos_enum,
            solo_con_credito_fiscal=solo_con_credito_fiscal,
            registros_por_pagina=10000  # Exportar hasta 10k registros
        )
        
        # Generar CSV
        csv_content = await consulta_service.exportar_comprobantes_csv(ruc, consulta_request)
        
        # Crear respuesta de descarga
        return StreamingResponse(
            io.BytesIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=comprobantes_rce_{ruc}_{periodo or 'varios'}.csv"
            }
        )
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/comprobantes/estadisticas",
    response_model=RceApiResponse,
    summary="Estadísticas de comprobantes",
    description="Obtener estadísticas generales de comprobantes RCE"
)
async def obtener_estadisticas_comprobantes(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo YYYYMM"),
    año: Optional[int] = Query(None, description="Año para estadísticas anuales"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener estadísticas de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **año**: Año para estadísticas anuales (opcional)
    """
    try:
        filtros = {"numero_documento_adquiriente": ruc}
        
        if periodo:
            filtros["periodo"] = periodo
        elif año:
            filtros["periodo"] = {"$regex": f"^{año}"}
        
        # Pipeline de agregación para estadísticas
        pipeline = [
            {"$match": filtros},
            {"$group": {
                "_id": {
                    "tipo_comprobante": "$tipo_comprobante",
                    "sustenta_credito_fiscal": "$sustenta_credito_fiscal"
                },
                "cantidad": {"$sum": 1},
                "total_importe": {"$sum": "$importe_total"},
                "total_igv": {"$sum": "$igv"},
                "promedio_importe": {"$avg": "$importe_total"}
            }}
        ]
        
        estadisticas = await service.collection.aggregate(pipeline).to_list(length=None)
        
        # Procesar estadísticas
        resumen = {
            "total_comprobantes": 0,
            "total_importe": 0,
            "total_igv": 0,
            "total_credito_fiscal": 0,
            "por_tipo": {},
            "con_credito_fiscal": 0,
            "sin_credito_fiscal": 0
        }
        
        for stat in estadisticas:
            tipo = stat["_id"]["tipo_comprobante"]
            con_credito = stat["_id"]["sustenta_credito_fiscal"]
            
            resumen["total_comprobantes"] += stat["cantidad"]
            resumen["total_importe"] += stat["total_importe"]
            resumen["total_igv"] += stat["total_igv"]
            
            if con_credito:
                resumen["total_credito_fiscal"] += stat["total_igv"]
                resumen["con_credito_fiscal"] += stat["cantidad"]
            else:
                resumen["sin_credito_fiscal"] += stat["cantidad"]
            
            if tipo not in resumen["por_tipo"]:
                resumen["por_tipo"][tipo] = {
                    "cantidad": 0,
                    "total_importe": 0,
                    "total_igv": 0,
                    "credito_fiscal": 0
                }
            
            resumen["por_tipo"][tipo]["cantidad"] += stat["cantidad"]
            resumen["por_tipo"][tipo]["total_importe"] += stat["total_importe"]
            resumen["por_tipo"][tipo]["total_igv"] += stat["total_igv"]
            
            if con_credito:
                resumen["por_tipo"][tipo]["credito_fiscal"] += stat["total_igv"]
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estadísticas generadas exitosamente",
            datos=resumen
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# Endpoint para verificar salud del módulo RCE
@router.get(
    "/health",
    response_model=RceApiResponse,
    summary="Verificar salud del módulo RCE",
    description="Verificar que el módulo RCE esté funcionando correctamente"
)
async def health_check(
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Verificar salud del módulo RCE
    """
    try:
        # Verificar conexión a base de datos
        await service.db.command("ping")
        
        # Verificar API de SUNAT
        api_disponible = await service.api_client.health_check()
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Módulo RCE funcionando correctamente",
            datos={
                "base_datos": "OK",
                "api_sunat": "OK" if api_disponible else "NO_DISPONIBLE",
                "timestamp": str(service.db.command("serverStatus")["localTime"])
            }
        )
        
    except Exception as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=f"Error en módulo RCE: {str(e)}",
            codigo="HEALTH_ERROR"
        )
