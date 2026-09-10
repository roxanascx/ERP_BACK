# Rutas del módulo de contabilidad

from fastapi import APIRouter
from .mayor_routes import router as mayor_router
from .filtrado_avanzado_routes import router_filtrado
from .diario_routes import router as diario_router
from .ventas_routes import router as ventas_router
from .compras_routes import router as compras_router
from .plan_contable_routes import router as plan_contable_router

# Crear router principal del módulo accounting SIN prefijo
# porque ya se agrega en core/router.py
router = APIRouter(tags=["Contabilidad"])

# Incluir rutas específicas
router.include_router(plan_contable_router)  # Plan Contable
router.include_router(mayor_router)      # Libro Mayor PLE 050200
router.include_router(router_filtrado)  # Filtrado Avanzado
router.include_router(diario_router)    # Libro Diario PLE 050100
router.include_router(ventas_router)    # Registro Ventas PLE 140000
router.include_router(compras_router)   # Registro Compras PLE 080000

__all__ = ["router"]
