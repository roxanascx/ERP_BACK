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
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Any, Optional

from app.modules.accounting.services import AccountingService
from app.modules.accounting.schemas import CuentaContableCreate, CuentaContableResponse

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
    service: AccountingService = Depends(AccountingService)
):
    """
    Obtener cuentas del plan contable con filtros optimizados.
    
    - **activos**: Si True, solo devuelve cuentas activas
    - **clase_contable**: Filtrar por clase (1-9)
    - **nivel**: Filtrar por nivel jerárquico (1-8)
    - **busqueda**: Búsqueda de texto en código o descripción
    - **limit**: Límite de resultados para paginación
    """
    return await service.list_cuentas_filtradas(
        activos_solo=activos,
        clase_contable=clase_contable,
        nivel=nivel,
        busqueda=busqueda,
        limit=limit
    )


@router.get("/plan/cuentas/buscar", summary="Búsqueda rápida de cuentas")
async def buscar_cuentas(
    q: str = Query(..., description="Término de búsqueda"),
    activos: bool = Query(True, description="Solo cuentas activas"),
    limit: int = Query(50, description="Límite de resultados"),
    service: AccountingService = Depends(AccountingService)
):
    """
    Búsqueda rápida y eficiente de cuentas por código o descripción.
    Optimizada para autocompletado y búsquedas en tiempo real.
    """
    return await service.buscar_cuentas_rapido(q, activos, limit)


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
