"""
Estado del ciclo de vida de un periodo RCE.

El manual de Compras describe el periodo como una máquina de estados: SUNAT
publica una propuesta, el contribuyente la acepta (5.2) o la reemplaza (5.3)
—y el libro pasa a preliminar—, y finalmente la registra (5.4). El 5.17 es la
única marcha atrás.

Esto es deliberadamente distinto de `RceEstadoProceso` (models/rce.py), que
describe el estado de *un envío* concreto y mezcla conceptos (`ACEPTADO` y
`PRELIMINAR` son el mismo momento del libro). Aquí solo se modela en qué fase
está el periodo, que es lo que decide qué operaciones se pueden ofrecer.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EstadoPeriodo(str, Enum):
    """Fase en la que está el libro de compras de un periodo."""

    #: SUNAT tiene una propuesta y el contribuyente no ha aceptado nada todavía.
    PROPUESTA = "PROPUESTA"

    #: El libro pasó a preliminar, por 5.2 (aceptar) o 5.3 (reemplazar).
    PRELIMINAR = "PRELIMINAR"

    #: El preliminar quedó registrado con 5.4. Es el estado final del API;
    #: la "Generación" posterior se hace desde el portal web.
    REGISTRADO = "REGISTRADO"


#: Transiciones que el manual permite. Se valida contra esto antes de llamar a
#: SUNAT, para no gastar una petición en algo que va a rechazar.
TRANSICIONES_VALIDAS: Dict[EstadoPeriodo, set] = {
    EstadoPeriodo.PROPUESTA: {EstadoPeriodo.PRELIMINAR},
    # 5.17 con indEliminar=1 deshace el preliminar y devuelve el periodo a
    # propuesta; 5.4 lo lleva a registrado.
    EstadoPeriodo.PRELIMINAR: {EstadoPeriodo.REGISTRADO, EstadoPeriodo.PROPUESTA},
    # Un preliminar ya registrado también se elimina con 5.17.
    EstadoPeriodo.REGISTRADO: {EstadoPeriodo.PROPUESTA},
}


#: Qué operación lleva de un estado a otro, para explicarlo en los errores.
OPERACION_DE_TRANSICION = {
    (EstadoPeriodo.PROPUESTA, EstadoPeriodo.PRELIMINAR): "aceptar la propuesta (5.2)",
    (EstadoPeriodo.PRELIMINAR, EstadoPeriodo.REGISTRADO): "registrar el preliminar (5.4)",
    (EstadoPeriodo.PRELIMINAR, EstadoPeriodo.PROPUESTA): "eliminar el preliminar (5.17)",
    (EstadoPeriodo.REGISTRADO, EstadoPeriodo.PROPUESTA): "eliminar el preliminar (5.17)",
}


def transicion_permitida(desde: EstadoPeriodo, hasta: EstadoPeriodo) -> bool:
    """¿Se puede pasar de `desde` a `hasta`?"""
    return hasta in TRANSICIONES_VALIDAS.get(desde, set())


class EventoPeriodo(BaseModel):
    """Una operación registrada sobre el periodo, para poder auditar el ciclo."""

    operacion: str = Field(..., description="Servicio del manual ejecutado, p. ej. '5.2'")
    estado_anterior: Optional[EstadoPeriodo] = None
    estado_nuevo: EstadoPeriodo
    num_ticket: Optional[str] = Field(None, description="Ticket devuelto por SUNAT")
    detalle: Optional[str] = None
    fecha: datetime = Field(default_factory=datetime.utcnow)


class PeriodoRce(BaseModel):
    """Estado actual del periodo, con su historial de operaciones."""

    ruc: str
    periodo: str = Field(..., description="Periodo tributario en formato yyyymm")
    estado: EstadoPeriodo = EstadoPeriodo.PROPUESTA
    num_ticket_ultimo: Optional[str] = None
    actualizado_en: datetime = Field(default_factory=datetime.utcnow)
    historial: List[EventoPeriodo] = Field(default_factory=list)

    def operaciones_disponibles(self) -> List[str]:
        """
        Operaciones que tienen sentido en el estado actual.

        La UI las usa para habilitar o deshabilitar botones en vez de dejar que
        el usuario descubra por un error de SUNAT que no tocaba.
        """
        return [
            OPERACION_DE_TRANSICION[(self.estado, destino)]
            for destino in TRANSICIONES_VALIDAS.get(self.estado, set())
            if (self.estado, destino) in OPERACION_DE_TRANSICION
        ]

    def to_mongo(self) -> Dict[str, Any]:
        datos = self.model_dump()
        datos["estado"] = self.estado.value
        for evento in datos.get("historial", []):
            for clave in ("estado_anterior", "estado_nuevo"):
                if isinstance(evento.get(clave), EstadoPeriodo):
                    evento[clave] = evento[clave].value
        return datos
