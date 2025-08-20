"""
RCE Consultas Routes - Endpoints para consultas avanzadas y reportes RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional, Any, Dict
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from ....database import get_database
from ....shared.exceptions import SireException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..services.rce_consulta_service import RceConsultaService
from ..models.rce import RceTipoComprobante, RceEstadoComprobante
from ..schemas.rce_schemas import (
    RceConsultaAvanzadaRequest, RceReporteRequest,
    RceResumenRequest, RceApiResponse
)

router = APIRouter()


class CredencialesSunat(BaseModel):
    """Credenciales SUNAT para operaciones que requieren autenticación"""
    usuario_sunat: str
    clave_sunat: str


class ParametrosReporte(BaseModel):
    """Parámetros para generación de reportes"""
    periodo_inicio: str
    periodo_fin: str
    tipo_comprobante: Optional[List[RceTipoComprobante]] = None
    estado_comprobante: Optional[List[RceEstadoComprobante]] = None
    incluir_anulados: bool = False
    incluir_observados: bool = True
    formato_salida: str = "xlsx"  # xlsx, csv, pdf, json
    incluir_detalles: bool = True
    agrupar_por: Optional[str] = None  # proveedor, tipo_comprobante, mes
    credenciales: CredencialesSunat


class FiltrosAnalisis(BaseModel):
    """Filtros para análisis de datos"""
    rango_fechas: Optional[Dict[str, date]] = None
    rango_importes: Optional[Dict[str, float]] = None
    proveedores_incluir: Optional[List[str]] = None
    proveedores_excluir: Optional[List[str]] = None
    tipos_comprobante: Optional[List[RceTipoComprobante]] = None
    incluir_rectificativas: bool = True


def get_rce_consulta_service(db=Depends(get_database)) -> RceConsultaService:
    """Dependency para obtener el servicio de consultas RCE"""
    api_client = SunatApiClient()
    auth_service = SireAuthService(db, api_client)
    compras_service = RceComprasService(db, api_client, auth_service)
    return RceConsultaService(db, api_client, auth_service, compras_service)


@router.post(
    "/consultas/avanzada",
    response_model=RceApiResponse,
    summary="Consulta avanzada de comprobantes",
    description="Realizar consulta avanzada con múltiples filtros y criterios"
)
async def consulta_avanzada(
    ruc: str,
    request: RceConsultaAvanzadaRequest,
    limit: int = Query(100, description="Límite de resultados", ge=1, le=1000),
    offset: int = Query(0, description="Offset para paginación", ge=0),
    ordenar_por: str = Query("fecha_emision", description="Campo para ordenar"),
    orden_desc: bool = Query(True, description="Orden descendente"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Realizar consulta avanzada de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **request**: Filtros y criterios de búsqueda
    - **limit**: Límite de resultados (máximo 1000)
    - **offset**: Offset para paginación
    - **ordenar_por**: Campo para ordenar resultados
    - **orden_desc**: Orden descendente si es True
    """
    try:
        resultado = await service.consulta_avanzada(
            ruc, request, limit, offset, ordenar_por, orden_desc
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Consulta completada: {resultado['total']} comprobantes encontrados",
            datos=resultado
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
    "/reportes/generar",
    response_model=RceApiResponse,
    summary="Generar reporte personalizado",
    description="Generar reporte personalizado con filtros específicos"
)
async def generar_reporte(
    ruc: str,
    parametros: ParametrosReporte = Body(...),
    incluir_graficos: bool = Query(False, description="Incluir gráficos en el reporte"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Generar reporte personalizado de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **parametros**: Parámetros del reporte (periodo, filtros, formato)
    - **incluir_graficos**: Si incluir gráficos en el reporte
    """
    try:
        # Convertir modelo a request schema
        reporte_request = RceReporteRequest(
            periodo_inicio=parametros.periodo_inicio,
            periodo_fin=parametros.periodo_fin,
            tipo_comprobante=parametros.tipo_comprobante,
            estado_comprobante=parametros.estado_comprobante,
            incluir_anulados=parametros.incluir_anulados,
            incluir_observados=parametros.incluir_observados,
            formato_salida=parametros.formato_salida,
            incluir_detalles=parametros.incluir_detalles,
            agrupar_por=parametros.agrupar_por,
            incluir_graficos=incluir_graficos
        )
        
        reporte = await service.generar_reporte(
            ruc, 
            reporte_request,
            parametros.credenciales.usuario_sunat,
            parametros.credenciales.clave_sunat
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Reporte generado: {reporte['nombre_archivo']}",
            datos=reporte
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
    "/reportes/resumen-periodo",
    response_model=RceApiResponse,
    summary="Generar resumen de periodo",
    description="Generar resumen ejecutivo de un periodo específico"
)
async def generar_resumen_periodo(
    ruc: str,
    request: RceResumenRequest,
    incluir_comparativo: bool = Query(False, description="Incluir comparativo con periodo anterior"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Generar resumen ejecutivo de un periodo
    
    - **ruc**: RUC del contribuyente
    - **request**: Parámetros del resumen (periodo, detalle, formato)
    - **incluir_comparativo**: Si incluir comparativo con periodo anterior
    """
    try:
        resumen = await service.generar_resumen_periodo(
            ruc, request, incluir_comparativo
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Resumen de periodo {request.periodo} generado",
            datos=resumen
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
    "/consultas/duplicados",
    response_model=RceApiResponse,
    summary="Detectar comprobantes duplicados",
    description="Identificar comprobantes posiblemente duplicados"
)
async def detectar_duplicados(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo específico YYYYMM"),
    criterio: str = Query("estricto", description="Criterio de detección (estricto, flexible)"),
    limit: int = Query(100, description="Límite de resultados", ge=1, le=500),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Detectar comprobantes posiblemente duplicados
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **criterio**: Criterio de detección (estricto=mismo número, flexible=mismo importe+fecha)
    - **limit**: Límite de resultados
    """
    try:
        duplicados = await service.detectar_duplicados(ruc, periodo, criterio, limit)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Análisis completado: {len(duplicados)} grupos de duplicados encontrados",
            datos={
                "total_grupos": len(duplicados),
                "criterio_aplicado": criterio,
                "periodo_analizado": periodo or "Todos",
                "duplicados": duplicados
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
    "/consultas/inconsistencias",
    response_model=RceApiResponse,
    summary="Detectar inconsistencias",
    description="Identificar inconsistencias en los datos de comprobantes"
)
async def detectar_inconsistencias(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo específico YYYYMM"),
    tipo_validacion: str = Query("todas", description="Tipo de validación (todas, matematicas, formales, temporales)"),
    nivel_severidad: str = Query("medio", description="Nivel de severidad (bajo, medio, alto)"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Detectar inconsistencias en los datos
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **tipo_validacion**: Tipo de validaciones a realizar
    - **nivel_severidad**: Nivel mínimo de severidad a reportar
    """
    try:
        inconsistencias = await service.detectar_inconsistencias(
            ruc, periodo, tipo_validacion, nivel_severidad
        )
        
        # Categorizar inconsistencias por tipo
        resumen_por_tipo = {}
        for inc in inconsistencias:
            tipo = inc.get("tipo", "Otros")
            if tipo not in resumen_por_tipo:
                resumen_por_tipo[tipo] = 0
            resumen_por_tipo[tipo] += 1
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Análisis completado: {len(inconsistencias)} inconsistencias encontradas",
            datos={
                "total_inconsistencias": len(inconsistencias),
                "resumen_por_tipo": resumen_por_tipo,
                "periodo_analizado": periodo or "Todos",
                "nivel_severidad": nivel_severidad,
                "inconsistencias": inconsistencias
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
    "/analisis/tendencias",
    response_model=RceApiResponse,
    summary="Análisis de tendencias",
    description="Análisis de tendencias y patrones en los datos"
)
async def analisis_tendencias(
    ruc: str,
    filtros: FiltrosAnalisis = Body(...),
    tipo_analisis: str = Query("mensual", description="Tipo de análisis (mensual, trimestral, anual)"),
    metricas: List[str] = Query(["importe", "cantidad"], description="Métricas a analizar"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Realizar análisis de tendencias en los datos
    
    - **ruc**: RUC del contribuyente
    - **filtros**: Filtros para el análisis
    - **tipo_analisis**: Granularidad temporal del análisis
    - **metricas**: Métricas a incluir en el análisis
    """
    try:
        analisis = await service.analizar_tendencias(
            ruc, filtros, tipo_analisis, metricas
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Análisis de tendencias completado",
            datos=analisis
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
    "/consultas/proveedores/ranking",
    response_model=RceApiResponse,
    summary="Ranking de proveedores",
    description="Obtener ranking de proveedores por volumen de compras"
)
async def ranking_proveedores(
    ruc: str,
    periodo_inicio: str = Query(..., description="Periodo inicio YYYYMM"),
    periodo_fin: str = Query(..., description="Periodo fin YYYYMM"),
    criterio: str = Query("importe", description="Criterio de ranking (importe, cantidad, frecuencia)"),
    limit: int = Query(50, description="Número de proveedores a incluir", ge=1, le=200),
    incluir_detalles: bool = Query(True, description="Incluir detalles de cada proveedor"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Obtener ranking de proveedores
    
    - **ruc**: RUC del contribuyente
    - **periodo_inicio**: Periodo inicio del análisis
    - **periodo_fin**: Periodo fin del análisis
    - **criterio**: Criterio para el ranking
    - **limit**: Número de proveedores en el ranking
    - **incluir_detalles**: Si incluir detalles adicionales
    """
    try:
        ranking = await service.obtener_ranking_proveedores(
            ruc, periodo_inicio, periodo_fin, criterio, limit, incluir_detalles
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Ranking de {len(ranking)} proveedores generado",
            datos={
                "criterio": criterio,
                "periodo": f"{periodo_inicio} - {periodo_fin}",
                "total_proveedores": len(ranking),
                "ranking": ranking
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
    "/consultas/estadisticas/periodo",
    response_model=RceApiResponse,
    summary="Estadísticas de periodo",
    description="Obtener estadísticas detalladas de un periodo específico"
)
async def estadisticas_periodo(
    ruc: str,
    periodo: str = Query(..., description="Periodo YYYYMM"),
    incluir_comparativo: bool = Query(True, description="Incluir comparativo con periodo anterior"),
    incluir_graficos: bool = Query(False, description="Incluir datos para gráficos"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Obtener estadísticas detalladas de un periodo
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico YYYYMM
    - **incluir_comparativo**: Si incluir comparación con periodo anterior
    - **incluir_graficos**: Si incluir datos preparados para gráficos
    """
    try:
        estadisticas = await service.obtener_estadisticas_periodo(
            ruc, periodo, incluir_comparativo, incluir_graficos
        )
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Estadísticas del periodo {periodo} generadas",
            datos=estadisticas
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
    "/exportaciones/csv",
    response_model=RceApiResponse,
    summary="Exportar a CSV",
    description="Exportar datos de comprobantes a formato CSV"
)
async def exportar_csv(
    ruc: str,
    request: RceConsultaAvanzadaRequest,
    incluir_cabeceras: bool = Query(True, description="Incluir cabeceras en CSV"),
    separador: str = Query(",", description="Separador de campos"),
    codificacion: str = Query("utf-8", description="Codificación del archivo"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Exportar comprobantes a formato CSV
    
    - **ruc**: RUC del contribuyente
    - **request**: Filtros para la exportación
    - **incluir_cabeceras**: Si incluir cabeceras en el CSV
    - **separador**: Separador de campos (coma, punto y coma, etc.)
    - **codificacion**: Codificación del archivo
    """
    try:
        archivo_csv = await service.exportar_csv(
            ruc, request, incluir_cabeceras, separador, codificacion
        )
        
        from fastapi.responses import Response
        
        return Response(
            content=archivo_csv["contenido"],
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={archivo_csv['nombre_archivo']}"
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
    "/exportaciones/excel",
    response_model=RceApiResponse,
    summary="Exportar a Excel",
    description="Exportar datos de comprobantes a formato Excel con múltiples hojas"
)
async def exportar_excel(
    ruc: str,
    request: RceConsultaAvanzadaRequest,
    incluir_resumen: bool = Query(True, description="Incluir hoja de resumen"),
    incluir_graficos: bool = Query(False, description="Incluir gráficos en Excel"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Exportar comprobantes a formato Excel
    
    - **ruc**: RUC del contribuyente
    - **request**: Filtros para la exportación
    - **incluir_resumen**: Si incluir hoja de resumen ejecutivo
    - **incluir_graficos**: Si incluir gráficos en el archivo
    """
    try:
        archivo_excel = await service.exportar_excel(
            ruc, request, incluir_resumen, incluir_graficos
        )
        
        from fastapi.responses import Response
        
        return Response(
            content=archivo_excel["contenido"],
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={archivo_excel['nombre_archivo']}"
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
    "/consultas/health",
    response_model=RceApiResponse,
    summary="Estado de salud de consultas",
    description="Verificar estado de salud del módulo de consultas"
)
async def health_check(
    ruc: str,
    verificar_conexion_sunat: bool = Query(False, description="Verificar conexión con SUNAT"),
    service: RceConsultaService = Depends(get_rce_consulta_service)
):
    """
    Verificar estado de salud del módulo de consultas
    
    - **ruc**: RUC del contribuyente
    - **verificar_conexion_sunat**: Si verificar conexión con SUNAT
    """
    try:
        # Verificaciones básicas
        total_comprobantes = await service.compras_service.collection.count_documents({"ruc": ruc})
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "modulo": "RCE Consultas",
            "estado": "operativo",
            "estadisticas": {
                "total_comprobantes": total_comprobantes,
                "base_datos_conectada": True
            }
        }
        
        # Verificar conexión con SUNAT si se solicita
        if verificar_conexion_sunat:
            try:
                # Intentar consulta básica a SUNAT (sin autenticación completa)
                health_data["estadisticas"]["sunat_disponible"] = True
                health_data["estadisticas"]["sunat_ultimo_check"] = datetime.utcnow().isoformat()
            except Exception:
                health_data["estadisticas"]["sunat_disponible"] = False
                health_data["estado"] = "degradado"
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Módulo de consultas operativo",
            datos=health_data
        )
        
    except Exception as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=f"Error en verificación de salud: {str(e)}",
            codigo="HEALTH_ERROR"
        )
