"""
Configuración de centros de costo.

Mantenimiento del catálogo que, combinado con `requiere_centro_costo` en el
Plan de Cuentas, determina qué asientos exigen centro de costo.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ....database import get_database
from ..schemas.schemas_centro_costo import CentroCostoCreate, CentroCostoUpdate
from ..services.centro_costo_service import (
    CentroCostoDuplicado,
    CentroCostoNoEncontrado,
    CentroCostoService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_centro_costo_service(database=Depends(get_database)) -> CentroCostoService:
    return CentroCostoService(database)


@router.get(
    "",
    summary="Listar centros de costo",
    description="Catálogo de centros de costo de la empresa. La primera vez siembra el estándar",
)
async def listar_centros_costo(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    solo_activos: bool = Query(False, description="Excluir los desactivados"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        centros = await service.listar(empresa_id, solo_activos)
        return {
            "exitoso": True,
            "empresa_id": empresa_id,
            "total": len(centros),
            "centros_costo": centros,
        }
    except Exception as e:
        logger.exception(f"Error listando centros de costo de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error listando centros de costo: {e}")


@router.get(
    "/{codigo}",
    summary="Obtener un centro de costo",
)
async def obtener_centro_costo(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        return {"exitoso": True, "centro_costo": await service.obtener(empresa_id, codigo)}
    except CentroCostoNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "",
    summary="Crear un centro de costo",
    status_code=201,
)
async def crear_centro_costo(
    datos: CentroCostoCreate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None, description="Usuario que lo crea"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        centro_costo = await service.crear(empresa_id, datos, usuario)
        return {
            "exitoso": True,
            "mensaje": f"Centro de costo {datos.codigo} creado",
            "centro_costo": centro_costo,
        }
    except CentroCostoDuplicado as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put(
    "/{codigo}",
    summary="Modificar un centro de costo",
    description="Actualiza solo los campos enviados",
)
async def actualizar_centro_costo(
    codigo: str,
    cambios: CentroCostoUpdate,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    usuario: Optional[str] = Query(None, description="Usuario que lo modifica"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        centro_costo = await service.actualizar(empresa_id, codigo, cambios, usuario)
        return {
            "exitoso": True,
            "mensaje": f"Centro de costo {codigo} actualizado",
            "centro_costo": centro_costo,
        }
    except CentroCostoNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{codigo}",
    summary="Eliminar un centro de costo",
)
async def eliminar_centro_costo(
    codigo: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        await service.eliminar(empresa_id, codigo)
        return {"exitoso": True, "mensaje": f"Centro de costo {codigo} eliminado"}
    except CentroCostoNoEncontrado as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/restaurar-catalogo",
    summary="Restaurar los centros de costo estándar que falten",
    description="Añade los del catálogo estándar que no existan. No toca los ya configurados",
)
async def restaurar_catalogo(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: CentroCostoService = Depends(get_centro_costo_service),
) -> Dict[str, Any]:
    try:
        creados = await service.restaurar_catalogo(empresa_id)
        return {
            "exitoso": True,
            "creados": creados,
            "mensaje": (
                f"Se añadieron {creados} centros de costo"
                if creados
                else "No faltaba ninguno del catálogo estándar"
            ),
        }
    except Exception as e:
        logger.exception(f"Error restaurando el catálogo de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error restaurando: {e}")
