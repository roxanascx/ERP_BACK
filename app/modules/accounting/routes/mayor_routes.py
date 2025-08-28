"""
Rutas API para Libro Mayor PLE 050200
=====================================

Endpoints REST para la generación y consulta del Libro Mayor.
Proporciona funcionalidades completas para el manejo del PLE 050200
según especificaciones oficiales SUNAT.

Endpoints disponibles:
- GET /libro-mayor: Consultar Libro Mayor por período
- POST /libro-mayor/generar-ple: Generar archivo PLE 050200
- GET /libro-mayor/resumen: Obtener resumen del período
- GET /libro-mayor/cuenta/{codigo}: Detalle de cuenta específica
- GET /libro-mayor/validar: Validar partida doble y balance

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
import tempfile
import os

from ....database import get_database
from ..services.mayor_service import MayorService
from ..schemas.schemas_mayor import (
    LibroMayorResponse,
    LibroMayorRequest,
    TipoCuentaContable,
    NaturalezaCuenta,
    EstadoCuentaMayor
)
from app.shared.exceptions import AccountingException

logger = logging.getLogger(__name__)

# Crear router para Libro Mayor
router = APIRouter(prefix="/libro-mayor", tags=["Libro Mayor"])


@router.get(
    "/",
    response_model=List[LibroMayorResponse],
    summary="Obtener Libro Mayor",
    description="Obtiene el Libro Mayor para un período específico con todos los saldos y movimientos por cuenta contable."
)
async def obtener_libro_mayor(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_desde: str = Query(..., description="Período inicial (AAAAMM)", regex=r"^\d{6}$"),
    periodo_hasta: str = Query(..., description="Período final (AAAAMM)", regex=r"^\d{6}$"),
    codigo_cuenta_desde: Optional[str] = Query(None, description="Código de cuenta inicial"),
    codigo_cuenta_hasta: Optional[str] = Query(None, description="Código de cuenta final"),
    incluir_cuentas_sin_movimiento: bool = Query(True, description="Incluir cuentas sin movimientos"),
    db=Depends(get_database)
):
    """
    Obtener el Libro Mayor para un período específico
    
    El Libro Mayor muestra los saldos iniciales, movimientos del período
    y saldos finales de todas las cuentas contables.
    
    **Parámetros:**
    - **empresa_id**: Identificador único de la empresa
    - **periodo_desde**: Período inicial en formato AAAAMM (ej: 202408)
    - **periodo_hasta**: Período final en formato AAAAMM
    - **codigo_cuenta_desde**: Código inicial para filtro de cuentas (opcional)
    - **codigo_cuenta_hasta**: Código final para filtro de cuentas (opcional)
    - **incluir_cuentas_sin_movimiento**: Si incluir cuentas sin movimientos
    
    **Respuesta:**
    Lista de cuentas con sus saldos y movimientos del período.
    """
    try:
        service = MayorService(db)
        
        libro_mayor = await service.obtener_libro_mayor(
            empresa_id=empresa_id,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            codigo_cuenta_desde=codigo_cuenta_desde,
            codigo_cuenta_hasta=codigo_cuenta_hasta,
            incluir_cuentas_sin_movimiento=incluir_cuentas_sin_movimiento
        )
        
        logger.info(f"Libro Mayor obtenido: {len(libro_mayor)} cuentas para empresa {empresa_id}")
        
        return libro_mayor
        
    except AccountingException as e:
        logger.error(f"Error de contabilidad obteniendo Libro Mayor: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno obteniendo Libro Mayor: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post(
    "/generar-ple",
    summary="Generar archivo PLE 050200",
    description="Genera el archivo PLE 050200 (Libro Mayor) según especificaciones oficiales SUNAT."
)
async def generar_archivo_ple_mayor(
    empresa_id: str = Query(..., description="ID de la empresa"),
    empresa_ruc: str = Query(..., description="RUC de la empresa", regex=r"^\d{11}$"),
    periodo_aaaamm: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    codigo_cuenta_desde: Optional[str] = Query(None, description="Código de cuenta inicial"),
    codigo_cuenta_hasta: Optional[str] = Query(None, description="Código de cuenta final"),
    correlativo: str = Query("001", description="Correlativo del archivo", regex=r"^\d{3}$"),
    formato_respuesta: str = Query("json", description="Formato de respuesta", regex=r"^(json|file)$"),
    db=Depends(get_database)
):
    """
    Generar archivo PLE 050200 del Libro Mayor
    
    Genera el archivo oficial PLE 050200 según especificaciones SUNAT,
    incluyendo validaciones de partida doble y balance de saldos.
    
    **Parámetros:**
    - **empresa_id**: Identificador único de la empresa
    - **empresa_ruc**: RUC de la empresa (11 dígitos)
    - **periodo_aaaamm**: Período en formato AAAAMM (ej: 202408)
    - **codigo_cuenta_desde**: Filtro inicial de cuentas (opcional)
    - **codigo_cuenta_hasta**: Filtro final de cuentas (opcional)
    - **correlativo**: Correlativo del archivo (001-999)
    - **formato_respuesta**: Formato de respuesta (json o file)
    
    **Respuesta:**
    - Si formato_respuesta = "json": Información detallada del archivo generado
    - Si formato_respuesta = "file": Descarga directa del archivo PLE
    """
    try:
        service = MayorService(db)
        
        resultado = await service.generar_archivo_ple_mayor(
            empresa_id=empresa_id,
            empresa_ruc=empresa_ruc,
            periodo_aaaamm=periodo_aaaamm,
            codigo_cuenta_desde=codigo_cuenta_desde,
            codigo_cuenta_hasta=codigo_cuenta_hasta,
            correlativo=correlativo
        )
        
        logger.info(f"Archivo PLE 050200 generado: {resultado['archivo']['nombre']}")
        
        # Retornar archivo o información según formato solicitado
        if formato_respuesta == "file":
            # Crear archivo temporal y retornar para descarga
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='iso-8859-1') as temp_file:
                temp_file.write(resultado['archivo']['contenido'])
                temp_file_path = temp_file.name
            
            return FileResponse(
                path=temp_file_path,
                filename=resultado['archivo']['nombre'],
                media_type='text/plain',
                background=lambda: os.unlink(temp_file_path)  # Eliminar archivo después de enviar
            )
        else:
            # Retornar información en JSON
            return JSONResponse(content=resultado)
        
    except AccountingException as e:
        logger.error(f"Error de contabilidad generando PLE: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno generando PLE: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/resumen",
    summary="Obtener resumen del período",
    description="Obtiene un resumen estadístico del Libro Mayor para un período específico."
)
async def obtener_resumen_periodo(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    db=Depends(get_database)
):
    """
    Obtener resumen estadístico del período
    
    Proporciona un resumen con totales, balance de partida doble
    y estadísticas por tipo de cuenta contable.
    
    **Parámetros:**
    - **empresa_id**: Identificador único de la empresa
    - **periodo_aaaamm**: Período en formato AAAAMM
    
    **Respuesta:**
    Resumen con totales de movimientos, saldos y validaciones.
    """
    try:
        service = MayorService(db)
        
        resumen = await service.obtener_resumen_periodo(
            empresa_id=empresa_id,
            periodo_aaaamm=periodo_aaaamm
        )
        
        logger.info(f"Resumen del período obtenido para empresa {empresa_id}, período {periodo_aaaamm}")
        
        return resumen
        
    except AccountingException as e:
        logger.error(f"Error de contabilidad obteniendo resumen: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno obteniendo resumen: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/cuenta/{codigo_cuenta}",
    summary="Obtener detalle de cuenta específica",
    description="Obtiene el detalle completo de movimientos de una cuenta específica."
)
async def obtener_detalle_cuenta(
    codigo_cuenta: str = Path(..., description="Código de la cuenta contable"),
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    db=Depends(get_database)
):
    """
    Obtener detalle de una cuenta específica
    
    Muestra todos los movimientos, saldos y estadísticas
    de una cuenta contable específica en un período.
    
    **Parámetros:**
    - **codigo_cuenta**: Código de la cuenta contable
    - **empresa_id**: Identificador único de la empresa
    - **periodo_aaaamm**: Período en formato AAAAMM
    
    **Respuesta:**
    Detalle completo de la cuenta con todos sus movimientos.
    """
    try:
        service = MayorService(db)
        
        # Obtener Libro Mayor filtrado por la cuenta específica
        libro_mayor = await service.obtener_libro_mayor(
            empresa_id=empresa_id,
            periodo_desde=periodo_aaaamm,
            periodo_hasta=periodo_aaaamm,
            codigo_cuenta_desde=codigo_cuenta,
            codigo_cuenta_hasta=codigo_cuenta,
            incluir_cuentas_sin_movimiento=True
        )
        
        if not libro_mayor:
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontró la cuenta {codigo_cuenta} en el período {periodo_aaaamm}"
            )
        
        cuenta_detalle = libro_mayor[0]
        
        # Obtener detalle adicional del repositorio
        from ..repositories.mayor_repository import MayorRepository
        repository = MayorRepository(db)
        
        resumen_movimientos = await repository.obtener_resumen_movimientos_por_cuenta(
            empresa_id=empresa_id,
            periodo=periodo_aaaamm,
            codigo_cuenta=codigo_cuenta
        )
        
        resultado = {
            "cuenta_mayor": cuenta_detalle,
            "resumen_movimientos": resumen_movimientos,
            "periodo": periodo_aaaamm
        }
        
        logger.info(f"Detalle de cuenta {codigo_cuenta} obtenido para empresa {empresa_id}")
        
        return resultado
        
    except HTTPException:
        raise
    except AccountingException as e:
        logger.error(f"Error de contabilidad obteniendo detalle de cuenta: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno obteniendo detalle de cuenta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/validar",
    summary="Validar Libro Mayor",
    description="Realiza validaciones de partida doble y balance de saldos del Libro Mayor."
)
async def validar_libro_mayor(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    db=Depends(get_database)
):
    """
    Validar integridad del Libro Mayor
    
    Realiza validaciones contables importantes:
    - Principio de partida doble (Debe = Haber)
    - Balance de saldos finales
    - Consistencia de datos
    
    **Parámetros:**
    - **empresa_id**: Identificador único de la empresa
    - **periodo_aaaamm**: Período en formato AAAAMM
    
    **Respuesta:**
    Resultado de todas las validaciones con detalles de errores si los hay.
    """
    try:
        service = MayorService(db)
        
        # Obtener datos del Libro Mayor
        libro_mayor = await service.obtener_libro_mayor(
            empresa_id=empresa_id,
            periodo_desde=periodo_aaaamm,
            periodo_hasta=periodo_aaaamm,
            incluir_cuentas_sin_movimiento=True
        )
        
        # Realizar validaciones
        validacion_partida_doble = service.formatter.validar_partida_doble(libro_mayor)
        validacion_balance = service.formatter.validar_balance_saldos(libro_mayor)
        
        # Obtener estadísticas adicionales del repositorio
        from ..repositories.mayor_repository import MayorRepository
        repository = MayorRepository(db)
        
        validacion_periodo = await repository.validar_partida_doble_periodo(
            empresa_id=empresa_id,
            periodo=periodo_aaaamm
        )
        
        estadisticas_periodo = await repository.obtener_estadisticas_periodo(
            empresa_id=empresa_id,
            periodo=periodo_aaaamm
        )
        
        resultado = {
            "periodo": periodo_aaaamm,
            "empresa_id": empresa_id,
            "validaciones": {
                "partida_doble": {
                    "es_valida": validacion_partida_doble[0],
                    "diferencia": str(validacion_partida_doble[1]),
                    "detalles_periodo": validacion_periodo
                },
                "balance_saldos": validacion_balance
            },
            "estadisticas": estadisticas_periodo,
            "resumen": {
                "total_cuentas_analizadas": len(libro_mayor),
                "fecha_validacion": datetime.utcnow().isoformat(),
                "estado_general": "VÁLIDO" if (
                    validacion_partida_doble[0] and 
                    validacion_balance["balance_correcto"]
                ) else "CON_ERRORES"
            }
        }
        
        logger.info(f"Validación del Libro Mayor completada para empresa {empresa_id}, período {periodo_aaaamm}")
        
        return resultado
        
    except AccountingException as e:
        logger.error(f"Error de contabilidad en validación: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno en validación: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/tipos-cuenta",
    summary="Obtener tipos de cuenta",
    description="Lista los tipos de cuenta contable disponibles en el sistema."
)
async def obtener_tipos_cuenta():
    """
    Obtener catálogo de tipos de cuenta contable
    
    Retorna los tipos de cuenta disponibles para clasificación
    según el plan contable general empresarial.
    """
    try:
        tipos = [
            {"codigo": tipo.value, "descripcion": tipo.value.replace("_", " ").title()}
            for tipo in TipoCuentaContable
        ]
        
        return {
            "tipos_cuenta": tipos,
            "naturalezas": [
                {"codigo": nat.value, "descripcion": nat.value.title()}
                for nat in NaturalezaCuenta
            ],
            "estados": [
                {"codigo": est.value, "descripcion": est.value.replace("_", " ").title()}
                for est in EstadoCuentaMayor
            ]
        }
    except Exception as e:
        # Devolver datos hardcodeados temporalmente para debug
        return {
            "tipos_cuenta": [
                {"codigo": "ACTIVO", "descripcion": "Activo"},
                {"codigo": "PASIVO", "descripcion": "Pasivo"},
                {"codigo": "PATRIMONIO", "descripcion": "Patrimonio"},
                {"codigo": "INGRESOS", "descripcion": "Ingresos"},
                {"codigo": "GASTOS", "descripcion": "Gastos"}
            ],
            "naturalezas": [
                {"codigo": "DEUDORA", "descripcion": "Deudora"},
                {"codigo": "ACREEDORA", "descripcion": "Acreedora"}
            ],
            "estados": [
                {"codigo": "ACTIVO", "descripcion": "Activo"},
                {"codigo": "INACTIVO", "descripcion": "Inactivo"}
            ],
            "error": str(e)
        }


# ================================
# NUEVOS ENDPOINTS - DATOS REALES (FASE 2)
# ================================

@router.post(
    "/generar-ple-datos-reales",
    summary="Generar PLE con datos reales",
    description="Genera archivo PLE 050200 usando asientos contables reales de la base de datos."
)
async def generar_ple_libro_mayor_datos_reales(
    empresa_id: str = Query(..., description="ID de la empresa"),
    empresa_ruc: str = Query(..., description="RUC de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período en formato AAAAMM"),
    periodo_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    periodo_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    correlativo: str = Query("001", description="Correlativo del archivo"),
    generar_archivo_fisico: bool = Query(False, description="Si generar archivo físico"),
    db=Depends(get_database)
):
    """
    Generar archivo PLE Libro Mayor usando datos reales
    
    Este endpoint utiliza los asientos contables reales almacenados
    en MongoDB y los convierte al formato PLE 050200 oficial de SUNAT.
    """
    try:
        logger.info(f"Generando PLE Mayor datos reales - Empresa: {empresa_id}, Período: {periodo_aaaamm}")
        
        service = MayorService(db)
        
        # Generar archivo PLE con datos reales
        resultado = await service.generar_archivo_ple_mayor_con_datos_reales(
            empresa_id=empresa_id,
            empresa_ruc=empresa_ruc,
            periodo_aaaamm=periodo_aaaamm,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
            correlativo=correlativo
        )
        
        if not resultado["archivo_generado"]:
            return JSONResponse(
                status_code=204,
                content={
                    "mensaje": resultado["mensaje"],
                    "archivo_generado": False
                }
            )
        
        # Si se solicita archivo físico, generarlo
        if generar_archivo_fisico:
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                delete=False, 
                suffix='.txt',
                encoding='utf-8'
            )
            temp_file.write(resultado["contenido_archivo"])
            temp_file.close()
            
            # Retornar archivo para descarga
            return FileResponse(
                path=temp_file.name,
                filename=resultado["nombre_archivo"],
                media_type='application/octet-stream'
            )
        
        # Retornar información del archivo generado
        return {
            "archivo_generado": True,
            "nombre_archivo": resultado["nombre_archivo"],
            "total_registros": resultado["total_registros"],
            "periodo": resultado["periodo"],
            "empresa_ruc": resultado["empresa_ruc"],
            "validacion": resultado["validacion"],
            "resumen": resultado["resumen"],
            "preview_contenido": resultado["contenido_archivo"][:500] + "..." if len(resultado["contenido_archivo"]) > 500 else resultado["contenido_archivo"]
        }
        
    except Exception as e:
        logger.error(f"Error generando PLE Mayor datos reales: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generando archivo PLE: {str(e)}")


@router.get(
    "/validar-compatibilidad-datos-reales",
    summary="Validar compatibilidad de datos reales",
    description="Valida que los datos reales sean compatibles con el formato PLE Mayor."
)
async def validar_compatibilidad_datos_reales(
    empresa_id: str = Query(..., description="ID de la empresa"),
    db=Depends(get_database)
):
    """
    Validar compatibilidad de datos reales para PLE Mayor
    
    Analiza los asientos contables reales y determina si son
    compatibles con los requerimientos del PLE 050200.
    """
    try:
        logger.info(f"Validando compatibilidad datos reales - Empresa: {empresa_id}")
        
        service = MayorService(db)
        
        # Validar compatibilidad
        reporte = await service.validar_compatibilidad_datos_reales(empresa_id)
        
        return {
            "empresa_id": empresa_id,
            "compatibilidad_porcentaje": reporte["compatibilidad"],
            "total_asientos": reporte["total_asientos"],
            "campos_requeridos_presentes": reporte["campos_requeridos_presentes"],
            "campos_opcionales_presentes": reporte["campos_opcionales_presentes"],
            "errores": reporte["errores"],
            "advertencias": reporte["advertencias"],
            "recomendaciones": reporte["recomendaciones"],
            "fecha_validacion": reporte["fecha_validacion"],
            "apto_para_ple": reporte["compatibilidad"] >= 80.0
        }
        
    except Exception as e:
        logger.error(f"Error validando compatibilidad: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validando compatibilidad: {str(e)}")


@router.get(
    "/asientos-contables-reales",
    summary="Obtener asientos contables reales",
    description="Lista los asientos contables reales disponibles para una empresa."
)
async def obtener_asientos_contables_reales(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    periodo_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    limite: int = Query(50, description="Límite de registros", ge=1, le=1000),
    db=Depends(get_database)
):
    """
    Obtener lista de asientos contables reales
    
    Permite consultar los asientos contables almacenados
    en la base de datos para una empresa específica.
    """
    try:
        logger.info(f"Obteniendo asientos reales - Empresa: {empresa_id}")
        
        service = MayorService(db)
        
        # Obtener asientos contables
        asientos = await service.obtener_asientos_contables_reales(
            empresa_id=empresa_id,
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta
        )
        
        # Limitar resultados
        asientos_limitados = asientos[:limite]
        
        # Preparar respuesta
        asientos_response = []
        for asiento in asientos_limitados:
            asiento_dict = {
                "id": str(asiento.get("_id", "")),
                "numero_correlativo": asiento.get("numeroCorrelativo", ""),
                "fecha": asiento.get("fecha", ""),
                "glosa": asiento.get("glosa", ""),
                "codigo_libro": asiento.get("codigoLibro", ""),
                "numero_documento": asiento.get("numeroDocumento", ""),
                "cuenta_contable": asiento.get("cuentaContable", {}),
                "debe": float(asiento.get("debe", 0.0)),
                "haber": float(asiento.get("haber", 0.0)),
                "empresa_id": asiento.get("empresaId", ""),
                "fecha_creacion": asiento.get("fechaCreacion", "").isoformat() if asiento.get("fechaCreacion") else ""
            }
            asientos_response.append(asiento_dict)
        
        return {
            "asientos": asientos_response,
            "total_encontrados": len(asientos),
            "total_mostrados": len(asientos_limitados),
            "empresa_id": empresa_id,
            "filtros": {
                "periodo_desde": periodo_desde,
                "periodo_hasta": periodo_hasta,
                "limite": limite
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo asientos reales: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo asientos: {str(e)}")


# ================================
# FIN NUEVOS ENDPOINTS
# ================================


# Incluir router en el módulo principal
def include_mayor_routes(app_router):
    """Incluir rutas del Libro Mayor en el router principal"""
    app_router.include_router(router)
    
    # Incluir también las rutas de filtrado avanzado
    from .filtrado_avanzado_routes import add_filtrado_routes
    add_filtrado_routes(app_router)
