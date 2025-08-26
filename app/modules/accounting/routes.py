"""
Rutas del módulo Contabilidad

Este archivo contiene rutas iniciales y puntos de extensión para:
- Plan Contable
- Libro Diario
- Registro de Compras
- Registro de Ventas
- Libro de Activos Fijos

Las rutas son esqueleto; la lógica se implementará en services.py y repositories.py
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Any, Optional, List, Dict
import io

from app.modules.accounting.services import AccountingService
from app.modules.accounting.libro_diario_service import LibroDiarioService
from app.modules.accounting.schemas import (
    CuentaContableCreate, 
    CuentaContableResponse,
    ValidationResult,
    ImportResult,
    PlanContableInfo,
    SwitchPlanRequest,
    ImportFileRequest,
    # Schemas de Libro Diario
    LibroDiarioCreate,
    LibroDiarioUpdate,
    LibroDiarioResponse,
    LibroDiarioCreateV2,
    LibroDiarioResponseV2,
    AsientoContableCreate,
    AsientoContableUpdate,
    AsientoContableResponse,
    AsientoContableCreateV2,
    AsientoContableResponseV2,
    FiltrosLibroDiario,
    ResumenLibroDiario,
    ExportOptions,
    CuentaContableLookup,
    # Schemas PLE
    PLEExportOptions,
    PLEExportResult,
    PLEValidationResult,
    PLEPreviewResult,
    PLEStatsResult,
    PLEReportResult
)
from app.modules.accounting.import_service import PlanContableImportService
from app.modules.accounting.sunat_routes import router as sunat_router

router = APIRouter(tags=["Accounting"])

# Incluir rutas de tablas SUNAT
router.include_router(sunat_router)


@router.get("/ping", summary="Health ping del módulo accounting")
async def ping() -> Any:
    return {"status": "ok", "module": "accounting"}


@router.get("/plan/estructura", summary="Obtener estructura jerárquica del plan contable")
async def get_plan_estructura(service: AccountingService = Depends(AccountingService)):
    return await service.get_plan_estructura()


@router.get("/plan/cuentas", summary="Listar cuentas del plan contable con filtros")
async def list_cuentas(
    activos: bool = Query(True, description="Filtrar solo cuentas activas"),
    clase_contable: Optional[int] = Query(None, description="Filtrar por clase contable (1-9)"),
    nivel: Optional[int] = Query(None, description="Filtrar por nivel jerárquico (1-8)"),
    busqueda: Optional[str] = Query(None, description="Buscar por código o descripción"),
    limit: Optional[int] = Query(None, description="Límite de resultados"),
    empresa_id: Optional[str] = Query(None, description="ID de la empresa"),
    tipo_plan: Optional[str] = Query("estandar", description="Tipo de plan contable"),
    service: AccountingService = Depends(AccountingService)
):
    """
    Obtener cuentas del plan contable con filtros optimizados.
    
    - **activos**: Si True, solo devuelve cuentas activas
    - **clase_contable**: Filtrar por clase (1-9)
    - **nivel**: Filtrar por nivel jerárquico (1-8)
    - **busqueda**: Búsqueda de texto en código o descripción
    - **limit**: Límite de resultados para paginación
    - **empresa_id**: ID de la empresa
    - **tipo_plan**: Tipo de plan contable (estandar/personalizado)
    """
    return await service.list_cuentas_filtradas(
        activos_solo=activos,
        clase_contable=clase_contable,
        nivel=nivel,
        busqueda=busqueda,
        limit=limit,
        empresa_id=empresa_id,
        tipo_plan=tipo_plan
    )


@router.get("/plan/cuentas/buscar", summary="Búsqueda rápida de cuentas")
async def buscar_cuentas(
    q: str = Query(..., description="Término de búsqueda"),
    activos: bool = Query(True, description="Solo cuentas activas"),
    limit: int = Query(50, description="Límite de resultados"),
    empresa_id: Optional[str] = Query(None, description="ID de la empresa"),
    tipo_plan: Optional[str] = Query("estandar", description="Tipo de plan contable"),
    service: AccountingService = Depends(AccountingService)
):
    """
    Búsqueda rápida y eficiente de cuentas por código o descripción.
    Optimizada para autocompletado y búsquedas en tiempo real.
    """
    return await service.buscar_cuentas_rapido(q, activos, limit, empresa_id, tipo_plan)


@router.get("/plan/cuentas/{codigo}", summary="Obtener cuenta por código")
async def get_cuenta(codigo: str, service: AccountingService = Depends(AccountingService)):
    cuenta = await service.plan_service.get_cuenta(codigo)
    if not cuenta:
        raise HTTPException(status_code=404, detail=f"Cuenta {codigo} no encontrada")
    return cuenta


@router.post("/plan/cuentas", summary="Crear cuenta contable")
async def create_cuenta(payload: CuentaContableCreate, service: AccountingService = Depends(AccountingService)) -> CuentaContableResponse:
    try:
        return await service.plan_service.crear_cuenta(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/plan/cuentas/{codigo}", summary="Actualizar cuenta contable")
async def update_cuenta(codigo: str, payload: dict, service: AccountingService = Depends(AccountingService)):
    try:
        result = await service.plan_service.actualizar_cuenta(codigo, payload)
        if not result:
            raise HTTPException(status_code=404, detail=f"Cuenta {codigo} no encontrada")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/plan/cuentas/{codigo}", summary="Eliminar cuenta contable (soft delete)")
async def delete_cuenta(codigo: str, service: AccountingService = Depends(AccountingService)):
    try:
        result = await service.plan_service.eliminar_cuenta(codigo)
        if not result:
            raise HTTPException(status_code=404, detail=f"Cuenta {codigo} no encontrada o no se pudo eliminar")
        return {"message": f"Cuenta {codigo} eliminada correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plan/estadisticas", summary="Obtener estadísticas del plan contable")
async def get_estadisticas(service: AccountingService = Depends(AccountingService)):
    return await service.plan_service.obtener_estadisticas()


# ==========================================
# NUEVAS RUTAS PARA PLANES PERSONALIZADOS
# ==========================================

@router.get("/plan/template", summary="Descargar plantilla de plan contable en TXT")
async def download_template():
    """
    Descarga una plantilla de ejemplo en formato TXT para crear un plan contable personalizado.
    La plantilla incluye instrucciones y ejemplos del formato requerido.
    """
    import_service = PlanContableImportService()
    template_content = import_service.generar_plantilla_txt()
    
    # Crear archivo para descarga
    file_like = io.StringIO(template_content)
    
    return StreamingResponse(
        io.BytesIO(template_content.encode('utf-8')),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=plantilla_plan_contable.txt"}
    )


@router.get("/plan/template-excel", summary="Descargar plantilla de plan contable en Excel")
async def download_template_excel():
    """
    Descarga una plantilla de ejemplo en formato Excel (.xlsx) para crear un plan contable personalizado.
    La plantilla incluye instrucciones detalladas, ejemplos y validaciones del formato requerido.
    """
    import_service = PlanContableImportService()
    excel_data = import_service.generar_plantilla_excel()
    
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_plan_contable.xlsx"}
    )


@router.post("/plan/validate", summary="Validar archivo de plan contable")
async def validate_plan_file(
    empresa_id: str = Form(...),
    file: UploadFile = File(...)
) -> ValidationResult:
    """
    Valida un archivo de plan contable sin importarlo.
    Útil para verificar el formato antes de la importación real.
    Soporta archivos .txt y .xlsx
    """
    allowed_extensions = ['.txt', '.xlsx']
    file_extension = None
    
    for ext in allowed_extensions:
        if file.filename.endswith(ext):
            file_extension = ext
            break
    
    if not file_extension:
        raise HTTPException(
            status_code=400, 
            detail="Solo se permiten archivos .txt o .xlsx"
        )
    
    import_service = PlanContableImportService()
    
    try:
        content = await file.read()
        
        if file_extension == '.txt':
            try:
                content_str = content.decode('utf-8')
                validation_result = import_service.validar_formato_archivo(content_str)
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="El archivo TXT debe estar codificado en UTF-8")
                
        elif file_extension == '.xlsx':
            validation_result = import_service.validar_formato_excel(content)
        
        return validation_result
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error procesando archivo: {str(e)}"
        )
    
    return validation_result


@router.post("/plan/import", summary="Importar plan contable personalizado")
async def import_plan_personalizado(
    empresa_id: str = Form(...),
    file: UploadFile = File(...)
) -> ImportResult:
    """
    Importa un plan contable personalizado desde un archivo TXT o Excel.
    
    - **empresa_id**: ID de la empresa para la cual se importa el plan
    - **file**: Archivo TXT o Excel (.xlsx) con el plan contable en el formato requerido
    
    Formatos soportados:
    - TXT: CODIGO[ESPACIOS]DESCRIPCION
    - Excel: Columnas CODIGO, DESCRIPCION, TIPO, NIVEL
    """
    allowed_extensions = ['.txt', '.xlsx']
    file_extension = None
    
    for ext in allowed_extensions:
        if file.filename.endswith(ext):
            file_extension = ext
            break
    
    if not file_extension:
        raise HTTPException(
            status_code=400, 
            detail="Solo se permiten archivos .txt o .xlsx"
        )
    
    import_service = PlanContableImportService()
    
    try:
        content = await file.read()
        
        if file_extension == '.txt':
            try:
                content_str = content.decode('utf-8')
                result = await import_service.importar_plan_personalizado(
                    empresa_id=empresa_id,
                    archivo_content=content_str,
                    filename=file.filename
                )
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="El archivo TXT debe estar codificado en UTF-8")
                
        elif file_extension == '.xlsx':
            result = await import_service.importar_plan_excel(
                empresa_id=empresa_id,
                excel_data=content,
                filename=file.filename
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la importación: {str(e)}")


@router.get("/plan/tipos/{empresa_id}", summary="Listar tipos de plan disponibles")
async def get_tipos_plan(empresa_id: str, service: AccountingService = Depends(AccountingService)) -> List[PlanContableInfo]:
    """
    Obtiene información sobre los tipos de plan contable disponibles para una empresa.
    
    - **empresa_id**: ID de la empresa
    
    Retorna información sobre el plan estándar y personalizado (si existe).
    """
    try:
        info = await service.plan_service.repo.get_plan_info(empresa_id)
        
        planes = []
        
        # Plan estándar
        if info["estandar"]["disponible"]:
            planes.append(PlanContableInfo(
                tipo="estandar",
                nombre="Plan Contable Estándar",
                descripcion="Plan contable general empresarial peruano",
                total_cuentas=info["estandar"]["total_cuentas"],
                activo=True  # Por defecto, el estándar está activo si no hay personalizado
            ))
        
        # Plan personalizado
        if info["personalizado"]["disponible"]:
            personalizado_info = info["personalizado"]["info"]
            planes.append(PlanContableInfo(
                tipo="personalizado",
                nombre="Plan Contable Personalizado",
                descripcion=f"Plan importado desde {personalizado_info.get('archivo_origen', 'archivo personalizado')}",
                total_cuentas=info["personalizado"]["total_cuentas"],
                fecha_creacion=personalizado_info.get("fecha_creacion"),
                archivo_origen=personalizado_info.get("archivo_origen"),
                activo=False
            ))
        
        return planes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo información de planes: {str(e)}")


@router.post("/plan/switch", summary="Cambiar tipo de plan activo")
async def switch_plan_tipo(
    request: SwitchPlanRequest,
    service: AccountingService = Depends(AccountingService)
):
    """
    Cambia el tipo de plan contable activo para una empresa.
    
    - **tipo_plan**: "estandar" o "personalizado"
    - **empresa_id**: ID de la empresa
    
    Esta operación afecta qué plan se utiliza en las consultas de la empresa.
    """
    if request.tipo_plan not in ["estandar", "personalizado"]:
        raise HTTPException(
            status_code=400, 
            detail="tipo_plan debe ser 'estandar' o 'personalizado'"
        )
    
    try:
        # Verificar que el plan solicitado existe
        info = await service.plan_service.repo.get_plan_info(request.empresa_id)
        
        if request.tipo_plan == "personalizado" and not info["personalizado"]["disponible"]:
            raise HTTPException(
                status_code=400,
                detail="No existe un plan personalizado para esta empresa"
            )
        
        if request.tipo_plan == "estandar" and not info["estandar"]["disponible"]:
            raise HTTPException(
                status_code=400,
                detail="No existe un plan estándar disponible"
            )
        
        # Marcar como activo (esto se puede implementar con una tabla de configuración)
        success = await service.plan_service.repo.set_plan_activo(
            request.empresa_id, 
            request.tipo_plan
        )
        
        if success:
            return {
                "message": f"Plan '{request.tipo_plan}' activado correctamente",
                "empresa_id": request.empresa_id,
                "tipo_plan_activo": request.tipo_plan
            }
        else:
            raise HTTPException(status_code=500, detail="Error activando el plan")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cambiando tipo de plan: {str(e)}")


@router.delete("/plan/personalizado/{empresa_id}", summary="Eliminar plan personalizado")
async def delete_plan_personalizado(
    empresa_id: str,
    service: AccountingService = Depends(AccountingService)
):
    """
    Elimina el plan contable personalizado de una empresa.
    Esto restaura el uso del plan estándar.
    
    - **empresa_id**: ID de la empresa
    """
    try:
        # Verificar que existe plan personalizado
        info = await service.plan_service.repo.get_plan_info(empresa_id)
        
        if not info["personalizado"]["disponible"]:
            raise HTTPException(
                status_code=404,
                detail="No existe un plan personalizado para esta empresa"
            )
        
        # Eliminar plan personalizado
        result = await service.plan_service.repo.delete_plan_personalizado(empresa_id)
        
        if result.deleted_count > 0:
            return {
                "message": "Plan personalizado eliminado correctamente",
                "cuentas_eliminadas": result.deleted_count,
                "empresa_id": empresa_id
            }
        else:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el plan")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando plan personalizado: {str(e)}")


# ================================
# RUTAS PARA LIBRO DIARIO
# ================================

@router.post("/libro-diario/", response_model=LibroDiarioResponse)
async def crear_libro_diario(
    libro_data: LibroDiarioCreateV2,
    usuario_id: Optional[str] = None
):
    """Crear un nuevo libro diario"""
    try:
        service = LibroDiarioService()
        return await service.crear_libro_diario_v2(libro_data, usuario_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/libro-diario/resumen", response_model=ResumenLibroDiario)
async def obtener_resumen_libro_diario(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo: Optional[str] = Query(None, description="Período específico")
):
    """Obtener resumen estadístico del libro diario"""
    try:
        service = LibroDiarioService()
        return await service.obtener_resumen(empresa_id, periodo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/libro-diario/{libro_id}", response_model=LibroDiarioResponse)
async def obtener_libro_diario(libro_id: str):
    """Obtener un libro diario por ID"""
    try:
        service = LibroDiarioService()
        libro = await service.obtener_libro_diario(libro_id)
        if not libro:
            raise HTTPException(status_code=404, detail="Libro diario no encontrado")
        return libro
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/libro-diario/{libro_id}", response_model=LibroDiarioResponse)
async def actualizar_libro_diario(
    libro_id: str,
    libro_data: LibroDiarioUpdate,
    usuario_id: Optional[str] = None
):
    """Actualizar un libro diario"""
    try:
        service = LibroDiarioService()
        libro = await service.actualizar_libro_diario(libro_id, libro_data, usuario_id)
        if not libro:
            raise HTTPException(status_code=404, detail="Libro diario no encontrado")
        return libro
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/libro-diario/{libro_id}")
async def eliminar_libro_diario(libro_id: str):
    """Eliminar un libro diario"""
    try:
        service = LibroDiarioService()
        resultado = await service.eliminar_libro_diario(libro_id)
        if not resultado:
            raise HTTPException(status_code=404, detail="Libro diario no encontrado")
        return {"message": "Libro diario eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/libro-diario/empresa/{empresa_id}", response_model=List[LibroDiarioResponse])
async def listar_libros_por_empresa(
    empresa_id: str,
    periodo: Optional[str] = Query(None, description="Período en formato YYYY o YYYY-MM"),
    fecha_desde: Optional[str] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    estado: Optional[str] = Query(None, description="Estado del libro"),
    busqueda: Optional[str] = Query(None, description="Búsqueda en descripción"),
    cuenta_contable: Optional[str] = Query(None, description="Código de cuenta contable")
):
    """Listar libros diario de una empresa con filtros"""
    try:
        # Construir filtros
        filtros = FiltrosLibroDiario(
            empresaId=empresa_id,
            periodo=periodo,
            fechaDesde=fecha_desde,
            fechaHasta=fecha_hasta,
            estado=estado,
            busqueda=busqueda,
            cuentaContable=cuenta_contable
        )
        
        service = LibroDiarioService()
        return await service.listar_libros_por_empresa_v2(empresa_id, filtros)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# RUTAS PARA ASIENTOS CONTABLES
# ================================

@router.post("/libro-diario/{libro_id}/asientos", response_model=AsientoContableResponse)
async def agregar_asiento(
    libro_id: str,
    asiento_data: AsientoContableCreate,
    usuario_id: Optional[str] = None
):
    """Agregar un asiento contable a un libro"""
    try:
        service = LibroDiarioService()
        return await service.agregar_asiento(libro_id, asiento_data, usuario_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/libro-diario/{libro_id}/asientos/{asiento_id}", response_model=AsientoContableResponse)
async def actualizar_asiento(
    libro_id: str,
    asiento_id: str,
    asiento_data: AsientoContableUpdate,
    usuario_id: Optional[str] = None
):
    """Actualizar un asiento contable"""
    try:
        service = LibroDiarioService()
        asiento = await service.actualizar_asiento(libro_id, asiento_id, asiento_data, usuario_id)
        if not asiento:
            raise HTTPException(status_code=404, detail="Asiento no encontrado")
        return asiento
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/libro-diario/{libro_id}/asientos/{asiento_id}")
async def eliminar_asiento(libro_id: str, asiento_id: str):
    """Eliminar un asiento contable"""
    try:
        service = LibroDiarioService()
        resultado = await service.eliminar_asiento(libro_id, asiento_id)
        if not resultado:
            raise HTTPException(status_code=404, detail="Asiento no encontrado")
        return {"message": "Asiento eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# RUTAS DE VALIDACIÓN Y UTILIDADES
# ================================

@router.post("/libro-diario/{libro_id}/validar", response_model=ValidationResult)
async def validar_libro_diario(libro_id: str):
    """Validar un libro diario completo"""
    try:
        service = LibroDiarioService()
        return await service.validar_libro_diario(libro_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/libro-diario/validar-asiento", response_model=ValidationResult)
async def validar_asiento(asiento: AsientoContableCreate):
    """Validar un asiento contable individualmente"""
    try:
        service = LibroDiarioService()
        await service._validar_asiento(asiento)
        return ValidationResult(isValid=True, errors=[], warnings=[])
    except ValueError as e:
        return ValidationResult(isValid=False, errors=[str(e)], warnings=[])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/libro-diario/siguiente-correlativo")
async def obtener_siguiente_correlativo(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo: str = Query(..., description="Período en formato YYYY-MM")
):
    """Obtener el siguiente número correlativo disponible"""
    try:
        service = LibroDiarioService()
        correlativo = await service.obtener_siguiente_correlativo(empresa_id, periodo)
        return {"numeroCorrelativo": correlativo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/cuentas/buscar", response_model=List[CuentaContableLookup])
async def buscar_cuentas_contables(
    q: str = Query(..., description="Término de búsqueda"),
    empresa_id: str = Query(..., description="ID de la empresa"),
    activos: bool = Query(True, description="Solo cuentas activas"),
    limit: int = Query(10, description="Límite de resultados")
):
    """Buscar cuentas contables para autocompletado"""
    try:
        service = LibroDiarioService()
        cuentas = await service.buscar_cuentas_contables(q, empresa_id, limit)
        return cuentas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# RUTAS DE EXPORTACIÓN
# ================================

@router.post("/libro-diario/{libro_id}/export")
async def exportar_libro_diario(
    libro_id: str,
    opciones: ExportOptions
):
    """Exportar libro diario en el formato especificado"""
    try:
        service = LibroDiarioService()
        data = await service.exportar_libro_diario(libro_id, opciones)
        
        # Determinar content type según formato
        content_types = {
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
            "txt": "text/plain"
        }
        
        filename_extensions = {
            "excel": "xlsx",
            "pdf": "pdf", 
            "txt": "txt"
        }
        
        filename = f"libro-diario.{filename_extensions[opciones.formato]}"
        
        return StreamingResponse(
            io.BytesIO(data),
            media_type=content_types[opciones.formato],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/libro-diario/reporte/{empresa_id}")
async def generar_reporte_empresa(
    empresa_id: str,
    request_data: Dict[str, Any]
):
    """Generar reporte consolidado por empresa"""
    try:
        filtros_data = request_data.get("filtros", {})
        formato = request_data.get("formato", "excel")
        
        # Construir filtros
        filtros = FiltrosLibroDiario(**filtros_data)
        
        service = LibroDiarioService()
        data = await service.generar_reporte_empresa(empresa_id, filtros, formato)
        
        # Determinar content type
        content_types = {
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf"
        }
        
        filename_extensions = {
            "excel": "xlsx",
            "pdf": "pdf"
        }
        
        filename = f"reporte-libro-diario.{filename_extensions[formato]}"
        
        return StreamingResponse(
            io.BytesIO(data),
            media_type=content_types[formato],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================
# ENDPOINTS PLE (PROGRAMA DE LIBROS ELECTRÓNICOS)
# =====================================

@router.post("/libros-diario/{libro_id}/export-ple")
async def exportar_libro_diario_ple(
    libro_id: str,
    opciones: Optional[Dict[str, Any]] = None
):
    """
    Exportar libro diario a formato PLE para SUNAT.
    
    Genera archivo TXT (y opcionalmente ZIP) según especificaciones SUNAT
    para el Programa de Libros Electrónicos (PLE).
    """
    try:
        service = LibroDiarioService()
        resultado = await service.exportar_a_ple(libro_id, opciones)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error en exportación PLE"))
        
        # Importar schemas PLE
        from app.modules.accounting.schemas import PLEExportResult
        
        return PLEExportResult(**resultado)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/libros-diario/{libro_id}/validate-ple")
async def validar_libro_diario_ple(libro_id: str):
    """
    Validar libro diario para exportación PLE.
    
    Realiza validaciones básicas y validaciones específicas SUNAT
    para verificar que el libro esté listo para exportar a PLE.
    """
    try:
        service = LibroDiarioService()
        resultado = await service.validar_para_ple(libro_id)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error en validación PLE"))
        
        # Importar schemas PLE
        from app.modules.accounting.schemas import PLEValidationResult
        
        return PLEValidationResult(**resultado)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/libros-diario/{libro_id}/preview-ple")
async def preview_archivo_ple(
    libro_id: str,
    max_lineas: int = Query(10, ge=1, le=100, description="Número máximo de líneas a mostrar")
):
    """
    Generar vista previa del archivo PLE.
    
    Muestra las primeras líneas del archivo PLE que se generaría,
    sin crear el archivo completo. Útil para verificar formato.
    """
    try:
        service = LibroDiarioService()
        resultado = await service.preview_ple(libro_id, max_lineas)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error en preview PLE"))
        
        # Importar schemas PLE
        from app.modules.accounting.schemas import PLEPreviewResult
        
        return PLEPreviewResult(**resultado)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/libros-diario/{libro_id}/stats-ple")
async def estadisticas_ple(libro_id: str):
    """
    Obtener estadísticas del libro diario para PLE.
    
    Proporciona información estadística sobre el libro diario
    relevante para la exportación PLE (totales, cuentas, estimaciones).
    """
    try:
        service = LibroDiarioService()
        resultado = await service.obtener_estadisticas_ple(libro_id)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error obteniendo estadísticas PLE"))
        
        # Importar schemas PLE
        from app.modules.accounting.schemas import PLEStatsResult
        
        return PLEStatsResult(**resultado)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/libros-diario/{libro_id}/report-ple")
async def generar_reporte_validacion_ple(libro_id: str):
    """
    Generar reporte detallado de validación PLE.
    
    Produce un reporte completo en texto con todas las validaciones,
    errores, warnings y recomendaciones para la exportación PLE.
    """
    try:
        service = LibroDiarioService()
        resultado = await service.generar_reporte_validacion(libro_id)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error generando reporte PLE"))
        
        # Importar schemas PLE
        from app.modules.accounting.schemas import PLEReportResult
        
        return PLEReportResult(**resultado)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/libros-diario/{libro_id}/download-ple")
async def descargar_archivo_ple(
    libro_id: str,
    formato: str = Query("zip", regex="^(txt|zip)$", description="Formato del archivo a descargar"),
    opciones: Optional[Dict[str, Any]] = None
):
    """
    Descargar archivo PLE generado.
    
    Genera y descarga el archivo PLE en el formato especificado.
    Útil para descargar directamente desde el navegador.
    """
    try:
        service = LibroDiarioService()
        
        # Configurar opciones basadas en el formato solicitado
        opciones_descarga = opciones or {}
        opciones_descarga["generar_zip"] = (formato == "zip")
        
        resultado = await service.exportar_a_ple(libro_id, opciones_descarga)
        
        if not resultado["exito"]:
            raise HTTPException(status_code=400, detail=resultado.get("error", "Error generando archivo PLE"))
        
        # Preparar descarga
        if formato == "zip" and resultado.get("contenido_zip"):
            content = resultado["contenido_zip"]
            media_type = "application/zip"
            filename = resultado["nombre_archivo"].replace(".TXT", ".zip")
        else:
            content = resultado["contenido_txt"].encode('utf-8')
            media_type = "text/plain"
            filename = resultado["nombre_archivo"]
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/libros-diario/{libro_id}/validate-and-export-ple")
async def validar_y_exportar_ple(
    libro_id: str,
    opciones: Optional[Dict[str, Any]] = None,
    forzar_exportacion: bool = Query(False, description="Forzar exportación aún con warnings")
):
    """
    Validar y exportar libro diario a PLE en una sola operación.
    
    Primero valida el libro diario y luego, si es válido (o si se fuerza),
    genera el archivo PLE. Optimizado para procesos automatizados.
    """
    try:
        service = LibroDiarioService()
        
        # 1. Validar primero
        resultado_validacion = await service.validar_para_ple(libro_id)
        
        if not resultado_validacion["exito"]:
            raise HTTPException(status_code=400, detail=resultado_validacion.get("error", "Error en validación"))
        
        # 2. Determinar si proceder con exportación
        valido = resultado_validacion["valido"]
        tiene_errores_criticos = any(
            e["critico"] for e in resultado_validacion["validacion_sunat"]["errores"]
        )
        
        puede_exportar = valido or (forzar_exportacion and not tiene_errores_criticos)
        
        if not puede_exportar:
            return {
                "exito": False,
                "validacion": resultado_validacion,
                "exportacion": None,
                "mensaje": "No se puede exportar debido a errores críticos. Use forzar_exportacion=true para ignorar warnings."
            }
        
        # 3. Proceder con exportación
        resultado_exportacion = await service.exportar_a_ple(libro_id, opciones)
        
        return {
            "exito": True,
            "validacion": resultado_validacion,
            "exportacion": resultado_exportacion,
            "mensaje": "Validación y exportación completadas exitosamente"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
