"""
Configuración de subdiarios contables.

Mantenimiento del catálogo que clasifica las operaciones por su origen y
determina qué asiento producen. Es la base de la contabilización automática de
las ventas que llegan de SIRE.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ....database import get_database
from ..schemas.schemas_subdiario import SubdiarioCreate, SubdiarioUpdate
from ..services.subdiario_service import (
    SubdiarioDuplicado,
    SubdiarioNoEncontrado,
    SubdiarioService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_subdiario_service(database=Depends(get_database)) -> SubdiarioService:
    return SubdiarioService(database)


@router.get(
    "",
    summary="Listar subdiarios",
    description="Catálogo de subdiarios de la empresa. La primera vez siembra el estándar",
)
async def listar_subdiarios(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    solo_activos: bool = Query(False, description="Excluir los desactivados"),
    tipo: Optional[str] = Query(
        None,
        description="Filtrar por uso: ventas, compras, honorarios, cheque, caja, bancos",
    ),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    """Subdiarios de la empresa, ordenados por código."""
    try:
        subdiarios = await service.listar(empresa_id, solo_activos, tipo)
        return {
            "exitoso": True,
            "empresa_id": empresa_id,
            "total": len(subdiarios),
            "subdiarios": subdiarios,
        }
    except Exception as e:
        logger.exception(f"Error listando subdiarios de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error listando subdiarios: {e}")


@router.get(
    "/diagnostico-compras",
    summary="Qué falta para contabilizar compras",
    description="Subdiarios de compra que aún no tienen sus cuentas completas",
)
async def diagnostico_compras(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    """Espejo del de ventas. La cuenta de gasto es la que suele faltar."""
    try:
        return {"exitoso": True, **await service.diagnostico_compras(empresa_id)}
    except Exception as e:
        logger.exception(f"Error en el diagnóstico de compras de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error en el diagnóstico: {e}")


@router.get(
    "/diagnostico",
    summary="Qué falta para contabilizar ventas",
    description="Subdiarios de venta que aún no tienen sus cuentas completas",
)
async def diagnostico(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    """Estado de la configuración, para avisar antes de intentar contabilizar."""
    try:
        return {"exitoso": True, **await service.diagnostico_ventas(empresa_id)}
    except Exception as e:
        logger.exception(f"Error en el diagnóstico de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error en el diagnóstico: {e}")


@router.get(
    "/{codigo}",
    summary="Obtener un subdiario",
)
async def obtener_subdiario(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    try:
        return {"exitoso": True, "subdiario": await service.obtener(empresa_id, codigo)}
    except SubdiarioNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "",
    summary="Crear un subdiario",
    status_code=201,
)
async def crear_subdiario(
    datos: SubdiarioCreate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None, description="Usuario que lo crea"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    try:
        subdiario = await service.crear(empresa_id, datos, usuario)
        return {
            "exitoso": True,
            "mensaje": f"Subdiario {datos.codigo} creado",
            "subdiario": subdiario,
        }
    except SubdiarioDuplicado as e:
        # 409: la petición es válida pero choca con lo que ya existe.
        raise HTTPException(status_code=409, detail=str(e))


@router.put(
    "/{codigo}",
    summary="Modificar un subdiario",
    description="Actualiza solo los campos enviados",
)
async def actualizar_subdiario(
    codigo: str,
    cambios: SubdiarioUpdate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None, description="Usuario que lo modifica"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    try:
        subdiario = await service.actualizar(empresa_id, codigo, cambios, usuario)
        return {
            "exitoso": True,
            "mensaje": f"Subdiario {codigo} actualizado",
            "subdiario": subdiario,
        }
    except SubdiarioNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{codigo}",
    summary="Eliminar un subdiario",
)
async def eliminar_subdiario(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    try:
        await service.eliminar(empresa_id, codigo)
        return {"exitoso": True, "mensaje": f"Subdiario {codigo} eliminado"}
    except SubdiarioNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/restaurar-catalogo",
    summary="Restaurar los subdiarios estándar que falten",
    description="Añade los del catálogo estándar que no existan. No toca los ya configurados",
)
async def restaurar_catalogo(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: SubdiarioService = Depends(get_subdiario_service),
) -> Dict[str, Any]:
    try:
        creados = await service.restaurar_catalogo(empresa_id)
        return {
            "exitoso": True,
            "creados": creados,
            "mensaje": (
                f"Se añadieron {creados} subdiarios"
                if creados
                else "No faltaba ninguno del catálogo estándar"
            ),
        }
    except Exception as e:
        logger.exception(f"Error restaurando el catálogo de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error restaurando: {e}")
