"""
Inicializador de modelos SIRE
"""

from .auth import (
    SireCredentials,
    SireTokenData,
    SireSession,
    SireAuthResponse,
    SireAuthError
)

from .rce_comprobante_bd import (
    RceComprobanteBD,
    RceComprobanteBDCreate,
    RceComprobanteBDResponse,
    RceGuardarResponse,
    RceEstadisticasBD
)

from .rvie import (
    RvieEstadoProceso,
    RvieTipoComprobante,
    RvieComprobante,
    RviePropuesta,
    RvieInconsistencia,
    RvieProcesoResult,
    RvieResumen
)

from .rce import (
    RceEstadoProceso,
    RceEstadoComprobante,
    RceTipoComprobante,
    RceComprobante,
    RcePropuesta,
    RceInconsistencia,
    RceResumenConsolidado,
    RceProcesoResult,
    RceResumen
)

from .responses import (
    SireOperationStatus,
    TicketStatus,
    SireApiResponse,
    TicketResponse,
    FileDownloadResponse,
    SireStatusResponse,
    ValidationError,
    SireErrorResponse,
    SirePaginatedResponse
)

__all__ = [
    # Auth models
    "SireCredentials",
    "SireTokenData", 
    "SireSession",
    "SireAuthResponse",
    "SireAuthError",
    
    # RVIE models
    "RvieEstadoProceso",
    "RvieTipoComprobante",
    "RvieComprobante",
    "RviePropuesta",
    "RvieInconsistencia",
    "RvieProcesoResult",
    "RvieResumen",
    
    # RCE models
    "RceEstadoProceso",
    "RceTipoComprobante",
    "RceComprobante",
    "RcePropuesta",
    "RceInconsistencia",
    "RceResumenConsolidado",
    "RceProcesoResult",
    "RceResumen",
    
    # Response models
    "SireOperationStatus",
    "TicketStatus",
    "SireApiResponse",
    "TicketResponse",
    "FileDownloadResponse",
    "SireStatusResponse",
    "ValidationError",
    "SireErrorResponse",
    "SirePaginatedResponse"
]
