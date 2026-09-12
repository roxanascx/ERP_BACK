"""
Contabilización de ventas: del registro de ventas al libro diario.

Segundo paso del puente SIRE → contabilidad. Trabaja por lotes y cada lote se
puede deshacer entero.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ....database import get_database
from ..services.contabilizacion_ventas_service import (
    ContabilizacionError,
    ContabilizacionVentasService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_contabilizacion_service(database=Depends(get_database)) -> ContabilizacionVentasService:
    return ContabilizacionVentasService(database)


@router.get(
    "/previsualizar",
    summary="Qué asientos se generarian",
    description="Sin escribir nada: cuántos se pueden contabilizar y qué se queda fuera",
)
async def previsualizar(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    subdiario: Optional[str] = Query(None, description="Limitar a un subdiario"),
    service: ContabilizacionVentasService = Depends(get_contabilizacion_service),
) -> Dict[str, Any]:
    """Previsualización. No toca el libro diario."""
    try:
        return {"exitoso": True, **await service.previsualizar(empresa_id, periodo, subdiario)}
    except Exception as e:
        logger.exception(f"Error previsualizando {empresa_id}/{periodo}")
        raise HTTPException(status_code=500, detail=f"Error al previsualizar: {e}")


@router.post(
    "",
    summary="Contabilizar las ventas del periodo",
    description=(
        "Genera un asiento por comprobante, agrupados en un lote que se puede "
        "deshacer. Los que no se pueden contabilizar se apartan con su motivo"
    ),
)
async def contabilizar(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    periodo: str = Query(..., description="Periodo tributario YYYYMM"),
    subdiario: Optional[str] = Query(None, description="Limitar a un subdiario"),
    libro_id: Optional[str] = Query(None, description="Libro diario de destino"),
    usuario: Optional[str] = Query(None, description="Quién contabiliza"),
    service: ContabilizacionVentasService = Depends(get_contabilizacion_service),
) -> Dict[str, Any]:
    """Contabilizar. **Escribe en el libro diario.**"""
    try:
        resultado = await service.contabilizar(
            empresa_id, periodo, subdiario, libro_id, usuario
        )
        return {"exitoso": True, **resultado}
    except Exception as e:
        logger.exception(f"Error contabilizando {empresa_id}/{periodo}")
        raise HTTPException(status_code=500, detail=f"Error al contabilizar: {e}")


@router.get(
    "/lotes",
    summary="Lotes contabilizados",
    description="Para consultarlos y poder deshacerlos",
)
async def listar_lotes(
    empresa_id: str = Query(..., description="RUC de la empresa"),
    periodo: Optional[str] = Query(None, description="Filtrar por periodo"),
    service: ContabilizacionVentasService = Depends(get_contabilizacion_service),
) -> Dict[str, Any]:
    """Lotes generados, del más reciente al más antiguo."""
    try:
        lotes = await service.listar_lotes(empresa_id, periodo)
        return {"exitoso": True, "total": len(lotes), "lotes": lotes}
    except Exception as e:
        logger.exception(f"Error listando lotes de {empresa_id}")
        raise HTTPException(status_code=500, detail=f"Error listando lotes: {e}")


@router.delete(
    "/lotes/{lote}",
    summary="Deshacer un lote",
    description="Borra los asientos del lote y libera sus ventas para volver a contabilizarlas",
)
async def deshacer_lote(
    lote: str,
    empresa_id: str = Query(..., description="RUC de la empresa"),
    service: ContabilizacionVentasService = Depends(get_contabilizacion_service),
) -> Dict[str, Any]:
    """Deshacer. **Borra asientos del libro diario.**"""
    try:
        resultado = await service.deshacer_lote(empresa_id, lote)
        return {
            "exitoso": True,
            "mensaje": (
                f"Lote {lote} deshecho: {resultado['lineas_eliminadas']} lineas "
                f"borradas y {resultado['ventas_liberadas']} ventas liberadas"
            ),
            **resultado,
        }
    except ContabilizacionError as e:
        raise HTTPException(status_code=404, detail=str(e))
