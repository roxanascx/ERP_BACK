"""
Servicio de centros de costo.

Mantenimiento del catálogo. La regla de negocio real —qué cuentas exigen
centro de costo— vive en el Plan de Cuentas (`requiere_centro_costo`) y se
aplica al grabar un asiento en `libro_diario_service._validar_asiento`.
"""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..repositories.centro_costo_repository import CentroCostoRepository
from ..schemas.schemas_centro_costo import CentroCostoCreate, CentroCostoUpdate

logger = logging.getLogger(__name__)

#: Catálogo estándar sembrado la primera vez, calcado del ejemplo de
#: referencia (CONTRA1): las cuatro áreas típicas de una empresa peruana.
CATALOGO_ESTANDAR: List[Dict[str, Any]] = [
    {"codigo": "100", "nombre": "PRODUCCION", "descripcion": "Costos de producción"},
    {"codigo": "200", "nombre": "ADMINISTRACION", "descripcion": "Gastos administrativos"},
    {"codigo": "300", "nombre": "VENTAS", "descripcion": "Gastos de ventas y distribución"},
    {"codigo": "400", "nombre": "FINANCIERO", "descripcion": "Gastos financieros"},
]


class CentroCostoNoEncontrado(Exception):
    """El centro de costo pedido no existe para esa empresa."""


class CentroCostoDuplicado(Exception):
    """Ya hay un centro de costo con ese código en la empresa."""


class CentroCostoService:
    """Mantenimiento del catálogo de centros de costo."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.repo = CentroCostoRepository(database)

    async def listar(
        self,
        empresa_id: str,
        solo_activos: bool = False,
        sembrar_si_vacio: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Centros de costo de la empresa.

        La primera vez se siembra el catálogo estándar, igual que Subdiarios:
        entrar y encontrarlo vacío obligaría a teclear las áreas típicas antes
        de poder marcar una sola cuenta como "requiere centro de costo".
        """
        await self.repo.asegurar_indices()

        if sembrar_si_vacio and await self.repo.contar(empresa_id) == 0:
            creados = await self.repo.sembrar(empresa_id, CATALOGO_ESTANDAR)
            logger.info(f"[CENTROS_COSTO] Sembrados {creados} centros de costo para {empresa_id}")

        return await self.repo.listar(empresa_id, solo_activos)

    async def obtener(self, empresa_id: str, codigo: str) -> Dict[str, Any]:
        doc = await self.repo.obtener(empresa_id, codigo)
        if not doc:
            raise CentroCostoNoEncontrado(
                f"No existe el centro de costo {codigo} en la empresa {empresa_id}"
            )
        return doc

    async def crear(
        self, empresa_id: str, datos: CentroCostoCreate, usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        await self.repo.asegurar_indices()

        if await self.repo.obtener(empresa_id, datos.codigo):
            raise CentroCostoDuplicado(
                f"Ya existe el centro de costo {datos.codigo} en esta empresa"
            )

        return await self.repo.crear(empresa_id, datos.model_dump(mode="json"), usuario)

    async def actualizar(
        self,
        empresa_id: str,
        codigo: str,
        cambios: CentroCostoUpdate,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        datos = cambios.model_dump(mode="json", exclude_unset=True)

        doc = await self.repo.actualizar(empresa_id, codigo, datos, usuario)
        if not doc:
            raise CentroCostoNoEncontrado(
                f"No existe el centro de costo {codigo} en la empresa {empresa_id}"
            )
        return doc

    async def eliminar(self, empresa_id: str, codigo: str) -> bool:
        if not await self.repo.eliminar(empresa_id, codigo):
            raise CentroCostoNoEncontrado(
                f"No existe el centro de costo {codigo} en la empresa {empresa_id}"
            )
        return True

    async def restaurar_catalogo(self, empresa_id: str) -> int:
        await self.repo.asegurar_indices()
        return await self.repo.sembrar(empresa_id, CATALOGO_ESTANDAR)
