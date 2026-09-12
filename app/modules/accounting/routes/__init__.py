# Rutas del módulo de contabilidad

from fastapi import APIRouter
from .mayor_routes import router as mayor_router
from .filtrado_avanzado_routes import router_filtrado
from .diario_routes import router as diario_router
from .ventas_routes import router as ventas_router
from .compras_routes import router as compras_router
from .plan_contable_routes import router as plan_contable_router
from .subdiario_routes import router as subdiario_router
from .centro_costo_routes import router as centro_costo_router
from ..ple_unified_routes import router as ple_unified_router
from .importacion_sire_routes import router as importacion_sire_router
from .importacion_sire_compras_routes import router as importacion_sire_compras_router
from .contabilizacion_routes import router as contabilizacion_router
from .contabilizacion_compras_routes import router as contabilizacion_compras_router

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

# Configuracion de subdiarios: clasifica las operaciones por su origen y
# determina que asiento producen. Es la base de la contabilizacion
# automatica de las ventas que llegan de SIRE.
router.include_router(subdiario_router, prefix="/subdiarios", tags=["Subdiarios"])

# Configuracion de centros de costo: catalogo que, combinado con
# `requiere_centro_costo` del Plan de Cuentas, exige centro de costo al
# grabar un asiento en las cuentas que lo tengan marcado.
router.include_router(centro_costo_router, prefix="/centros-costo", tags=["Centros de Costo"])

# Exportacion PLE unificada. Estaba montada solo en el `routes.py` que el
# paquete eclipsaba, asi que sus endpoints no existian y la exportacion
# del Libro Diario (PLEExportManager en el front) fallaba con 404.
router.include_router(ple_unified_router)

# Puente SIRE -> contabilidad, primer paso: trae los comprobantes de venta
# de SUNAT al registro de ventas. El asiento se genera despues, aparte.
router.include_router(importacion_sire_router,
                      prefix="/ventas/importar-sire", tags=["Ventas SIRE"])

# Lo mismo por el lado de compras. Va aparte porque RCE no devuelve los
# comprobantes al momento: hay que pasar por el ticket del manual.
router.include_router(importacion_sire_compras_router,
                      prefix="/compras/importar-sire", tags=["Compras SIRE"])

# Segundo paso: del registro de ventas al libro diario, por lotes
# reversibles.
router.include_router(contabilizacion_router,
                      prefix="/ventas/contabilizar", tags=["Contabilizacion"])

# Y el segundo paso de compras. El libro diario es el mismo para los dos: lo
# que distingue el origen de cada asiento es su codigoLibroOrigen, que lleva
# el codigo del subdiario.
router.include_router(contabilizacion_compras_router,
                      prefix="/compras/contabilizar", tags=["Contabilizacion"])

__all__ = ["router"]
