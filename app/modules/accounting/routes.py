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
from typing import Any, Optional, List
import io

from app.modules.accounting.services import AccountingService
from app.modules.accounting.schemas import (
    CuentaContableCreate, 
    CuentaContableResponse,
    ValidationResult,
    ImportResult,
    PlanContableInfo,
    SwitchPlanRequest,
    ImportFileRequest
)
from app.modules.accounting.import_service import PlanContableImportService

router = APIRouter(prefix="/accounting", tags=["Accounting"])


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
