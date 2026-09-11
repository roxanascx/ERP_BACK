"""
Traducción de las excepciones del módulo SIRE a respuestas HTTP.

Se comparte entre los routers del ciclo y de las cargas para que un mismo fallo
se vea igual venga de donde venga.
"""

import logging

from fastapi import HTTPException

from .exceptions import (
    SireApiException,
    SireAuthException,
    SireBusinessException,
    SireValidationException,
    SunatValidationException,
)

logger = logging.getLogger(__name__)


def traducir_error(e: Exception, ruc: str, periodo: str = "-") -> HTTPException:
    """
    Convertir una excepción del módulo en la respuesta HTTP que le corresponde.

    El reparto de códigos importa: un 409 dice «la petición está bien pero
    choca con el estado del periodo», que es muy distinto de un 422, donde
    SUNAT enumera qué hay mal en los datos.
    """
    if isinstance(e, SireAuthException):
        return HTTPException(
            status_code=401,
            detail=f"No se pudo autenticar con SUNAT para el RUC {ruc}: {e}",
        )

    if isinstance(e, SireValidationException):
        return HTTPException(status_code=400, detail=str(e))

    if isinstance(e, SireBusinessException):
        return HTTPException(
            status_code=409,
            detail={"mensaje": str(e), **(e.details or {})},
        )

    if isinstance(e, SunatValidationException):
        # La lista de errores viaja entera: es lo que el usuario debe corregir.
        return HTTPException(
            status_code=422,
            detail={"mensaje": str(e), "errores": e.errors},
        )

    if isinstance(e, SireApiException):
        return HTTPException(status_code=502, detail=f"Error de SUNAT: {e}")

    logger.exception(f"Error inesperado en SIRE para {ruc}/{periodo}")
    return HTTPException(status_code=500, detail=f"Error inesperado: {e}")
