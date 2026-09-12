"""
Excepciones personalizadas para el módulo SIRE
"""

from typing import Optional, Dict, Any


class SireException(Exception):
    """Excepción base para el módulo SIRE"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SireAuthException(SireException):
    """Excepción de autenticación SIRE"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        super().__init__(message, details)


class SireApiException(SireException):
    """Excepción de API SUNAT"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message, response_data)


class SireTimeoutException(SireException):
    """Excepción de timeout en requests"""
    pass


class SireValidationException(SireException):
    """Excepción de validación de datos"""
    
    def __init__(self, message: str, field: str, value: Any = None, details: Optional[Dict[str, Any]] = None):
        self.field = field
        self.value = value
        super().__init__(message, details)


class SireTokenException(SireException):
    """Excepción relacionada con tokens"""
    pass


class SireFileException(SireException):
    """Excepción de manejo de archivos"""
    
    def __init__(self, message: str, filename: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.filename = filename
        super().__init__(message, details)


class SireConfigurationException(SireException):
    """Excepción de configuración SIRE"""
    pass


class SireBusinessException(SireException):
    """Excepción de reglas de negocio SIRE"""
    
    def __init__(self, message: str, business_rule: str, details: Optional[Dict[str, Any]] = None):
        self.business_rule = business_rule
        super().__init__(message, details)

class SunatValidationException(SireApiException):
    """
    Error 422 de SUNAT: la petición se entendió pero no pasó las validaciones.

    SUNAT responde con la forma:
        {"cod": "422", "msg": "...", "errors": [{"cod": "1001", "msg": "..."}]}

    La lista `errors` es la parte útil (1001 RUC no enviado, 1006 periodo mal
    formado, 1161 codLibro no permitido, y una fila por cada error del archivo
    en las cargas masivas). Antes se perdía dentro de un str(e); aquí se
    conserva entera para poder mostrarla al usuario tal cual.
    """

    def __init__(
        self,
        message: str,
        errors: Optional[list] = None,
        cod: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ):
        self.errors = errors or []
        self.cod = cod
        super().__init__(message, status_code=422, response_data=response_data)

    def __str__(self) -> str:
        if not self.errors:
            return self.message
        detalle = "; ".join(
            f"{e.get('cod', '?')}: {e.get('msg', '')}" for e in self.errors[:5]
        )
        if len(self.errors) > 5:
            detalle += f" (y {len(self.errors) - 5} más)"
        return f"{self.message} — {detalle}"
