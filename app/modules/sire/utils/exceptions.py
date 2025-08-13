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
