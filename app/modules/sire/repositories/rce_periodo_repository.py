"""
Persistencia del estado de los periodos de un libro SIRE.

Un documento por (ruc, periodo). Compras y Ventas usan colecciones distintas
—`rce_periodos` y `rvie_periodos`— porque un mismo periodo puede estar en fases
diferentes en cada libro.
"""

import logging
from datetime import datetime
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.rce_periodo import EstadoPeriodo, EventoPeriodo, PeriodoRce

logger = logging.getLogger(__name__)


class RcePeriodoRepository:
    """Lectura y escritura del estado de los periodos de un libro."""

    #: Colección por defecto. `RviePeriodoRepository` la cambia.
    COLECCION = "rce_periodos"

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database[self.COLECCION]

    async def obtener(self, ruc: str, periodo: str) -> Optional[PeriodoRce]:
        """El estado guardado del periodo, o None si nunca se operó sobre él."""
        doc = await self.collection.find_one({"ruc": ruc, "periodo": periodo})
        if not doc:
            return None
        doc.pop("_id", None)
        return PeriodoRce(**doc)

    async def obtener_o_crear(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        El estado del periodo, asumiendo PROPUESTA si es la primera vez.

        Un periodo del que no sabemos nada está, por definición, en propuesta:
        es el estado en el que SUNAT lo deja al publicarla.
        """
        existente = await self.obtener(ruc, periodo)
        if existente:
            return existente
        return PeriodoRce(ruc=ruc, periodo=periodo, estado=EstadoPeriodo.PROPUESTA)

    async def registrar_transicion(
        self,
        ruc: str,
        periodo: str,
        nuevo_estado: EstadoPeriodo,
        operacion: str,
        num_ticket: Optional[str] = None,
        detalle: Optional[str] = None,
    ) -> PeriodoRce:
        """
        Guardar el cambio de estado y añadirlo al historial.

        Se llama *después* de que SUNAT confirme la operación: el estado local
        refleja lo que ya pasó, nunca lo que se intentó.
        """
        actual = await self.obtener_o_crear(ruc, periodo)

        evento = EventoPeriodo(
            operacion=operacion,
            estado_anterior=actual.estado,
            estado_nuevo=nuevo_estado,
            num_ticket=num_ticket,
            detalle=detalle,
        )

        actual.estado = nuevo_estado
        actual.num_ticket_ultimo = num_ticket or actual.num_ticket_ultimo
        actual.actualizado_en = datetime.utcnow()
        actual.historial.append(evento)

        await self.collection.update_one(
            {"ruc": ruc, "periodo": periodo},
            {"$set": actual.to_mongo()},
            upsert=True,
        )

        logger.info(
            f"[RCE] {ruc}/{periodo}: {evento.estado_anterior} -> {nuevo_estado} "
            f"por {operacion}" + (f" (ticket {num_ticket})" if num_ticket else "")
        )
        return actual

    async def listar_por_ruc(self, ruc: str, limite: int = 24) -> List[PeriodoRce]:
        """Los periodos sobre los que se ha operado, del más reciente al más antiguo."""
        cursor = self.collection.find({"ruc": ruc}).sort("periodo", -1).limit(limite)
        periodos = []
        async for doc in cursor:
            doc.pop("_id", None)
            periodos.append(PeriodoRce(**doc))
        return periodos


class RviePeriodoRepository(RcePeriodoRepository):
    """El mismo repositorio, sobre la colección de ventas."""

    COLECCION = "rvie_periodos"
