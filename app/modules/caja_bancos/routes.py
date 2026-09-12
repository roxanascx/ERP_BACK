"""
Caja/Bancos (MVP): catálogo de cuentas y sus movimientos, con contabilización
en lotes reversibles. Sin conciliación bancaria (fase posterior).
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ...database import get_database
from .schemas import (
    CuentaCajaBancoCreate,
    CuentaCajaBancoUpdate,
    MovimientoCajaBancoCreate,
)
from .services import (
    CajaBancoDuplicada,
    CajaBancoError,
    CajaBancoNoEncontrada,
    CajaBancoService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_caja_banco_service(database=Depends(get_database)) -> CajaBancoService:
    return CajaBancoService(database)


# ----------------------------------------------------------------------
# Cuentas
# ----------------------------------------------------------------------

@router.get("/cuentas", summary="Listar cuentas de caja y bancos")
async def listar_cuentas(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    solo_activas: bool = Query(False),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        cuentas = await service.listar_cuentas(empresa_id, solo_activas)
        return {"exitoso": True, "empresa_id": empresa_id, "total": len(cuentas), "cuentas": cuentas}
    except Exception as e:
        logger.exception(f"Error listando cuentas de caja/bancos de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error listando cuentas: {e}")


@router.get("/cuentas/{codigo}", summary="Obtener una cuenta de caja/banco")
async def obtener_cuenta(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        return {"exitoso": True, "cuenta": await service.obtener_cuenta(empresa_id, codigo)}
    except CajaBancoNoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cuentas", summary="Crear una cuenta de caja o banco", status_code=201)
async def crear_cuenta(
    datos: CuentaCajaBancoCreate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        cuenta = await service.crear_cuenta(empresa_id, datos, usuario)
        return {"exitoso": True, "mensaje": f"Cuenta {datos.codigo} creada", "cuenta": cuenta}
    except CajaBancoDuplicada as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CajaBancoError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/cuentas/{codigo}", summary="Modificar una cuenta de caja/banco")
async def actualizar_cuenta(
    codigo: str,
    cambios: CuentaCajaBancoUpdate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        cuenta = await service.actualizar_cuenta(empresa_id, codigo, cambios, usuario)
        return {"exitoso": True, "mensaje": f"Cuenta {codigo} actualizada", "cuenta": cuenta}
    except CajaBancoNoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/cuentas/{codigo}", summary="Eliminar una cuenta de caja/banco")
async def eliminar_cuenta(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        await service.eliminar_cuenta(empresa_id, codigo)
        return {"exitoso": True, "mensaje": f"Cuenta {codigo} eliminada"}
    except CajaBancoNoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CajaBancoError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------------------------
# Movimientos
# ----------------------------------------------------------------------

@router.get("/movimientos", summary="Listar movimientos de caja/bancos")
async def listar_movimientos(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    cuenta_caja_banco_id: Optional[str] = Query(None),
    contabilizado: Optional[bool] = Query(None),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        movimientos = await service.listar_movimientos(empresa_id, cuenta_caja_banco_id, contabilizado)
        return {"exitoso": True, "total": len(movimientos), "movimientos": movimientos}
    except Exception as e:
        logger.exception(f"Error listando movimientos de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error listando movimientos: {e}")


@router.post("/movimientos", summary="Registrar un pago o cobro", status_code=201)
async def crear_movimiento(
    datos: MovimientoCajaBancoCreate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        movimiento = await service.crear_movimiento(empresa_id, datos, usuario)
        return {"exitoso": True, "mensaje": "Movimiento registrado", "movimiento": movimiento}
    except CajaBancoNoEncontrada as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CajaBancoError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------------------------
# Contabilización
# ----------------------------------------------------------------------

@router.post("/contabilizar", summary="Generar el asiento de los movimientos pendientes")
async def contabilizar(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    cuenta_caja_banco_id: Optional[str] = Query(None, description="Limitar a una sola cuenta"),
    usuario: Optional[str] = Query(None),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        resultado = await service.contabilizar(empresa_id, cuenta_caja_banco_id, usuario)
        return {"exitoso": True, **resultado}
    except CajaBancoError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deshacer/{lote}", summary="Deshacer un lote de contabilización")
async def deshacer_lote(
    lote: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CajaBancoService = Depends(get_caja_banco_service),
) -> Dict[str, Any]:
    try:
        resultado = await service.deshacer_lote(empresa_id, lote)
        return {"exitoso": True, **resultado}
    except CajaBancoError as e:
        raise HTTPException(status_code=400, detail=str(e))
