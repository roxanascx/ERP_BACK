"""
PLE Unified Routes - Rutas OFICIALES para el módulo PLE
========================================================

Este archivo contiene TODAS las rutas PLE para producción.
REEMPLAZA completamente a ple_test_routes.py que fue eliminado
para evitar duplicaciones y conflictos.

Endpoints disponibles:
- POST /ple/generar - Generar archivo PLE
- POST /ple/validar - Validar datos PLE  
- GET /ple/archivos - Listar archivos generados
- GET /ple/preview/{id} - Vista previa de archivo
- DELETE /ple/archivos/{id} - Eliminar archivo
- GET /ple/descargar/{id} - Descargar archivo
- GET /ple/configuracion - Obtener configuración
- GET /ple/estadisticas - Estadísticas del módulo
- GET /ple/healthcheck - Health check

Autor: Sistema ERP  
Fecha: Agosto 2025
Versión: 3.0 - PRODUCCIÓN UNIFICADA
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import io
from datetime import datetime, date

from app.modules.accounting.libro_diario_service import LibroDiarioService
from app.modules.accounting.schemas import (
    PLEExportOptions,
    PLEExportResult, 
    PLEValidationResult,
    PLEPreviewResult,
    PLEStatsResult
)

router = APIRouter()

# =====================================================
# SCHEMAS UNIFICADOS
# =====================================================

class PLEGeneracionRequest(BaseModel):
    """Request unificado para generación PLE"""
    libro_diario_id: str
    ejercicio: int
    mes: int
    validar_antes_generar: bool = True
    incluir_metadatos: bool = True
    generar_zip: bool = True
    directorio_salida: Optional[str] = None
    observaciones: Optional[str] = ""

class PLEGeneracionResponse(BaseModel):
    """Response unificado para generación PLE"""
    success: bool
    archivo_id: str
    archivo_nombre: str
    mensaje: str
    total_registros: int
    errores: List[str] = []
    advertencias: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

class PLEValidacionRequest(BaseModel):
    """Request para validación PLE"""
    libro_diario_id: str
    validar_estructura: bool = True
    validar_balanceo: bool = True
    validar_sunat: bool = True

class PLEArchivoInfo(BaseModel):
    """Información de archivo PLE generado"""
    id: str
    nombre_archivo: str
    ejercicio: int
    mes: int
    fecha_generacion: str
    estado: str = "generado"
    tamano_archivo: int
    total_registros: int
    ruc_empresa: str
    razon_social: str
    observaciones: Optional[str] = ""
    errores: List[str] = []

# =====================================================
# ENDPOINTS UNIFICADOS - PLE
# =====================================================

@router.post("/ple/generar", response_model=PLEGeneracionResponse)
async def generar_ple_unificado(
    request: PLEGeneracionRequest,
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para generar archivos PLE.
    
    Reemplaza tanto endpoints de prueba como de producción
    con una interfaz consistente y completa.
    """
    try:
        # Validar que existe el libro diario
        libro = await service.obtener_libro_por_id(request.libro_diario_id)
        if not libro:
            raise HTTPException(
                status_code=404, 
                detail=f"Libro diario {request.libro_diario_id} no encontrado"
            )
        
        # Opciones de exportación
        opciones = PLEExportOptions(
            validar_antes_generar=request.validar_antes_generar,
            incluir_metadatos=request.incluir_metadatos,
            generar_zip=request.generar_zip,
            formato="SUNAT_V3",
            directorio_salida=request.directorio_salida
        )
        
        # Generar archivo PLE
        resultado = await service.exportar_a_ple_v3(
            libro_id=request.libro_diario_id,
            opciones=opciones
        )
        
        return PLEGeneracionResponse(
            success=True,
            archivo_id=resultado.archivo_id,
            archivo_nombre=resultado.nombre_archivo,
            mensaje="Archivo PLE generado exitosamente",
            total_registros=resultado.total_lineas,
            errores=resultado.errores,
            advertencias=resultado.advertencias,
            metadata={
                "ejercicio": request.ejercicio,
                "mes": request.mes,
                "fecha_generacion": datetime.now().isoformat(),
                "tamaño_txt": resultado.tamaño_txt,
                "tamaño_zip": resultado.tamaño_zip
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando PLE: {str(e)}"
        )

@router.post("/ple/validar", response_model=PLEValidationResult)
async def validar_ple_unificado(
    request: PLEValidacionRequest,
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para validar datos antes de generar PLE.
    """
    try:
        resultado = await service.validar_para_ple(
            libro_id=request.libro_diario_id,
            validar_estructura=request.validar_estructura,
            validar_balanceo=request.validar_balanceo,
            validar_sunat=request.validar_sunat
        )
        
        return resultado
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando PLE: {str(e)}"
        )

@router.get("/ple/archivos", response_model=List[PLEArchivoInfo])
async def obtener_archivos_ple_unificado(
    empresa_id: Optional[str] = Query(None),
    ejercicio: Optional[int] = Query(None),
    mes: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para obtener lista de archivos PLE generados.
    """
    try:
        filtros = {
            "empresa_id": empresa_id,
            "ejercicio": ejercicio,
            "mes": mes,
            "limit": limit,
            "offset": offset
        }
        
        archivos = await service.obtener_archivos_ple(filtros)
        
        return [
            PLEArchivoInfo(
                id=archivo["_id"],
                nombre_archivo=archivo["nombre_archivo"],
                ejercicio=archivo["ejercicio"],
                mes=archivo["mes"],
                fecha_generacion=archivo["fecha_generacion"].isoformat(),
                estado=archivo.get("estado", "generado"),
                tamano_archivo=archivo.get("tamano_archivo", 0),
                total_registros=archivo.get("total_registros", 0),
                ruc_empresa=archivo.get("ruc_empresa", ""),
                razon_social=archivo.get("razon_social", ""),
                observaciones=archivo.get("observaciones", ""),
                errores=archivo.get("errores", [])
            )
            for archivo in archivos
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo archivos PLE: {str(e)}"
        )

@router.get("/ple/preview/{archivo_id}")
async def obtener_preview_ple_unificado(
    archivo_id: str,
    max_lineas: int = Query(10, ge=1, le=100),
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para obtener preview de archivo PLE.
    """
    try:
        preview = await service.obtener_preview_ple(archivo_id, max_lineas)
        return preview
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo preview PLE: {str(e)}"
        )

@router.delete("/ple/archivos/{archivo_id}")
async def eliminar_archivo_ple_unificado(
    archivo_id: str,
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para eliminar archivo PLE.
    """
    try:
        resultado = await service.eliminar_archivo_ple(archivo_id)
        
        return {
            "success": True,
            "message": f"Archivo {archivo_id} eliminado exitosamente"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando archivo PLE: {str(e)}"
        )

@router.get("/ple/descargar/{archivo_id}")
async def descargar_archivo_ple_unificado(
    archivo_id: str,
    formato: str = Query("zip", regex="^(txt|zip)$"),
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Endpoint unificado para descargar archivo PLE.
    """
    try:
        archivo_data = await service.obtener_archivo_ple_para_descarga(
            archivo_id, 
            formato
        )
        
        media_type = "application/zip" if formato == "zip" else "text/plain"
        
        return StreamingResponse(
            io.BytesIO(archivo_data["contenido"]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={archivo_data['nombre_archivo']}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando archivo PLE: {str(e)}"
        )

# =====================================================
# ENDPOINTS DE CONFIGURACIÓN Y ESTADÍSTICAS
# =====================================================

@router.get("/ple/configuracion")
async def obtener_configuracion_ple():
    """
    Obtener configuración actual del módulo PLE.
    """
    return {
        "formatos_soportados": ["SUNAT_V3", "SUNAT_5.1"],
        "validaciones_disponibles": ["estructura", "balanceo", "sunat"],
        "tipos_exportacion": ["TXT", "ZIP"],
        "versiones_ple": ["5.1", "6.0"],
        "configuracion_default": {
            "validar_antes_generar": True,
            "incluir_metadatos": True,
            "generar_zip": True,
            "formato": "SUNAT_V3"
        }
    }

@router.get("/ple/estadisticas")
async def obtener_estadisticas_ple(
    empresa_id: Optional[str] = Query(None),
    ejercicio: Optional[int] = Query(None),
    service: LibroDiarioService = Depends(LibroDiarioService)
):
    """
    Obtener estadísticas del módulo PLE.
    """
    try:
        stats = await service.obtener_estadisticas_ple(empresa_id, ejercicio)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas PLE: {str(e)}"
        )

@router.get("/ple/healthcheck")
async def healthcheck_ple():
    """
    Health check del módulo PLE unificado.
    """
    return {
        "status": "ok",
        "module": "PLE_Unified",
        "version": "3.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints_disponibles": [
            "POST /ple/generar",
            "POST /ple/validar", 
            "GET /ple/archivos",
            "GET /ple/preview/{id}",
            "DELETE /ple/archivos/{id}",
            "GET /ple/descargar/{id}"
        ]
    }
