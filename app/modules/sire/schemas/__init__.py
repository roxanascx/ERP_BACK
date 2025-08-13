"""
Inicializador de schemas SIRE
"""

from .auth_schemas import (
    SireAuthRequest,
    SireAuthResponse,
    SireLogoutRequest,
    SireLogoutResponse,
    SireStatusRequest,
    SireStatusResponse,
    SireValidateTokenRequest,
    SireValidateTokenResponse,
    SireErrorResponse
)

__all__ = [
    "SireAuthRequest",
    "SireAuthResponse",
    "SireLogoutRequest",
    "SireLogoutResponse",
    "SireStatusRequest",
    "SireStatusResponse",
    "SireValidateTokenRequest",
    "SireValidateTokenResponse",
    "SireErrorResponse"
]
