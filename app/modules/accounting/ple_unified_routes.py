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
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import io
import logging
from datetime import datetime, date

# Inicializar logger
logger = logging.getLogger(__name__)

from app.modules.accounting.libro_diario_service import LibroDiarioService
from app.modules.accounting.schemas import (
    PLEExportOptions,
    PLEExportResult, 
    PLEValidationResult,
    PLEPreviewResult,
    PLEStatsResult
)

router = APIRouter()

# Logger
logger = logging.getLogger(__name__)

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
    descargar_directo: bool = False  # Nuevo campo para descarga directa
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

@router.post("/ple/generar")
async def generar_ple_unificado(
    request: PLEGeneracionRequest
):
    """
    Endpoint unificado para generar archivos PLE.
    
    Reemplaza tanto endpoints de prueba como de producción
    con una interfaz consistente y completa.
    """
    try:
        logger.info(f"Generando PLE: libro={request.libro_diario_id}, ejercicio={request.ejercicio}, mes={request.mes}")
        
        # Crear service sin dependency injection para evitar problemas de asyncio
        from app.database import get_database
        from app.modules.accounting.libro_diario_repository import LibroDiarioRepository
        
        db = get_database()
        repository = LibroDiarioRepository()
        repository.db = db
        
        # Crear service sin inicializar repository (para evitar crear índices)
        service = LibroDiarioService.__new__(LibroDiarioService)
        service.repository = repository
        
        # Validar que existe el libro diario
        libro = await service.obtener_libro_diario(request.libro_diario_id)
        if not libro:
            raise HTTPException(
                status_code=404, 
                detail=f"Libro diario {request.libro_diario_id} no encontrado"
            )
        
        # Llamar al método correcto del servicio con los parámetros correctos
        resultado_ple = await service.exportar_a_ple(
            libro_id=request.libro_diario_id,
            opciones={
                "ejercicio": request.ejercicio,
                "mes": request.mes
            }
        )
        
        # Verificar si la exportación fue exitosa
        if not resultado_ple.get("exito", False):
            return {
                "success": False,
                "error": resultado_ple.get("error", "Error desconocido en la exportación"),
                "details": "La exportación PLE falló"
            }
        
        # Crear archivo ZIP si se solicita
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                resultado_ple.get("nombre_archivo", "archivo.txt"),
                resultado_ple.get("contenido_txt", "")
            )
        
        tamaño_zip = len(zip_buffer.getvalue())
        
        # Si se solicita descarga directa, devolver el archivo ZIP
        if getattr(request, 'descargar_directo', False):
            zip_buffer.seek(0)
            zip_filename = resultado_ple.get("nombre_archivo", "archivo").replace(".txt", ".zip")
            
            return Response(
                content=zip_buffer.getvalue(),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
            )
        
        return PLEGeneracionResponse(
            success=True,
            archivo_id=request.libro_diario_id,
            archivo_nombre=resultado_ple.get("nombre_archivo", ""),
            mensaje="Archivo PLE generado exitosamente",
            total_registros=resultado_ple.get("total_lineas", 0),
            errores=resultado_ple.get("errores", []),
            advertencias=resultado_ple.get("warnings", []),
            metadata={
                "ejercicio": request.ejercicio,
                "mes": request.mes,
                "fecha_generacion": resultado_ple.get("fecha_generacion", datetime.now().isoformat()),
                "tamaño_txt": resultado_ple.get("tamaño_txt", 0),
                "tamaño_zip": tamaño_zip
            }
        )
        
    except Exception as e:
        import traceback
        error_details = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "libro_diario_id": request.libro_diario_id
        }
        return error_details

@router.post("/ple/validar")
async def validar_ple_unificado(
    request: PLEValidacionRequest
):
    """
    Endpoint unificado para validar datos antes de generar PLE.
    """
    try:
        logger.info(f"Validando PLE: libro={request.libro_diario_id}")
        
        # Crear service sin dependency injection para evitar problemas de asyncio
        from app.database import get_database
        from app.modules.accounting.libro_diario_repository import LibroDiarioRepository
        
        db = get_database()
        repository = LibroDiarioRepository()
        repository.db = db
        
        # Crear service sin inicializar repository (para evitar crear índices)
        service = LibroDiarioService.__new__(LibroDiarioService)
        service.repository = repository
        
        # Obtener resultado de validación del servicio
        resultado = await service.validar_para_ple(libro_id=request.libro_diario_id)
        
        # Devolver resultado directo sin conversión compleja
        return resultado
        
    except Exception as e:
        logger.error(f"Error validando PLE: {str(e)}")
        return {
            "exito": False,
            "libro_id": request.libro_diario_id,
            "valido": False,
            "error": str(e)
        }

# =====================================================
# ENDPOINT: OBTENER CONTEXTO DEL LIBRO DIARIO
# =====================================================

class PLEContextoResponse(BaseModel):
    """Respuesta con contexto automático del libro diario para PLE"""
    libro_diario_id: str
    ejercicio: int
    mes: int
    ruc: str
    razon_social: str
    total_asientos: int
    esta_balanceado: bool
    fecha_inicio: str
    fecha_fin: str

@router.get("/ple/descargar/{libro_diario_id}")
async def descargar_ple_directo(
    libro_diario_id: str,
    ejercicio: int = Query(..., description="Año del período fiscal"),
    mes: int = Query(..., description="Mes del período fiscal (1-12)")
):
    """
    Endpoint para descarga directa del archivo PLE en formato ZIP.
    """
    try:
        logger.info(f"Descarga directa PLE: libro={libro_diario_id}, ejercicio={ejercicio}, mes={mes}")
        
        # Crear service sin dependency injection para evitar problemas de asyncio
        from app.database import get_database
        from app.modules.accounting.libro_diario_repository import LibroDiarioRepository
        
        db = get_database()
        repository = LibroDiarioRepository()
        repository.db = db
        
        # Crear service sin inicializar repository (para evitar crear índices)
        service = LibroDiarioService.__new__(LibroDiarioService)
        service.repository = repository
        
        # Obtener el libro diario
        libro = await service.obtener_libro_diario(libro_diario_id)
        if not libro:
            raise HTTPException(
                status_code=404,
                detail=f"Libro diario {libro_diario_id} no encontrado"
            )
        
        # Exportar a PLE usando los parámetros correctos
        resultado_ple = await service.exportar_a_ple(
            libro_id=libro_diario_id,
            opciones={
                "ejercicio": ejercicio,
                "mes": mes
            }
        )
        
        # Verificar si la exportación fue exitosa
        if not resultado_ple.get("exito", False):
            raise HTTPException(
                status_code=500,
                detail=f"Error en la exportación PLE: {resultado_ple.get('error', 'Error desconocido')}"
            )
        
        # Crear archivo ZIP
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                resultado_ple.get("nombre_archivo", "archivo.txt"),
                resultado_ple.get("contenido_txt", "")
            )
        
        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()
        zip_filename = resultado_ple.get("nombre_archivo", "archivo").replace(".txt", ".zip")
        
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Content-Length": str(len(zip_content))
            }
        )
        
    except Exception as e:
        logger.error(f"Error en descarga directa PLE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en descarga: {str(e)}")
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error en descarga directa de PLE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/ple/contexto/{libro_diario_id}", response_model=PLEContextoResponse)
async def obtener_contexto_libro(libro_diario_id: str):
    """
    Obtiene contexto automático del libro diario para facilitar la generación PLE.
    
    Este endpoint analiza el libro diario y extrae automáticamente:
    - Período (ejercicio y mes) más común de los asientos
    - Información de la empresa (RUC, razón social)
    - Estadísticas del libro (total asientos, balance)
    - Rango de fechas de los asientos
    """
    try:
        service = LibroDiarioService()
        
        # Obtener datos básicos del libro
        libro = await service.obtener_libro_diario(libro_diario_id)
        if not libro:
            raise HTTPException(status_code=404, detail="Libro diario no encontrado")
        
        # Obtener asientos del libro (están en libro.asientos)
        asientos = libro.asientos if hasattr(libro, 'asientos') else []
        
        if not asientos:
            # Si no hay asientos, usar fecha actual como contexto base
            fecha_actual = datetime.now()
            return PLEContextoResponse(
                libro_diario_id=libro_diario_id,
                ejercicio=fecha_actual.year,
                mes=fecha_actual.month,
                ruc=libro.ruc if hasattr(libro, 'ruc') else '',
                razon_social=libro.razonSocial if hasattr(libro, 'razonSocial') else '',
                total_asientos=0,
                esta_balanceado=True,
                fecha_inicio=fecha_actual.strftime('%Y-%m-%d'),
                fecha_fin=fecha_actual.strftime('%Y-%m-%d')
            )
        
        # Analizar período más común en los asientos
        from collections import Counter
        periodos = []
        fechas_asientos = []
        
        for asiento in asientos:
            fecha_asiento = getattr(asiento, 'fecha', None)
            if fecha_asiento:
                if isinstance(fecha_asiento, str):
                    fecha_dt = datetime.strptime(fecha_asiento[:10], '%Y-%m-%d')
                else:
                    fecha_dt = fecha_asiento
                
                fechas_asientos.append(fecha_dt)
                periodos.append((fecha_dt.year, fecha_dt.month))
        
        # Encontrar período más común
        if periodos:
            periodo_mas_comun = Counter(periodos).most_common(1)[0][0]
            ejercicio, mes = periodo_mas_comun
        else:
            fecha_actual = datetime.now()
            ejercicio, mes = fecha_actual.year, fecha_actual.month
        
        # Calcular estadísticas del libro
        total_debe = 0
        total_haber = 0
        
        for asiento in asientos:
            movimientos = getattr(asiento, 'movimientos', [])
            for mov in movimientos:
                total_debe += getattr(mov, 'debe', 0)
                total_haber += getattr(mov, 'haber', 0)
        
        esta_balanceado = abs(total_debe - total_haber) < 0.01
        
        # Rango de fechas
        if fechas_asientos:
            fecha_inicio = min(fechas_asientos).strftime('%Y-%m-%d')
            fecha_fin = max(fechas_asientos).strftime('%Y-%m-%d')
        else:
            fecha_actual = datetime.now()
            fecha_inicio = fecha_fin = fecha_actual.strftime('%Y-%m-%d')
        
        return PLEContextoResponse(
            libro_diario_id=libro_diario_id,
            ejercicio=ejercicio,
            mes=mes,
            ruc=getattr(libro, 'ruc', ''),
            razon_social=getattr(libro, 'razonSocial', ''),
            total_asientos=len(asientos),
            esta_balanceado=esta_balanceado,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo contexto del libro {libro_diario_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo contexto del libro: {str(e)}"
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
