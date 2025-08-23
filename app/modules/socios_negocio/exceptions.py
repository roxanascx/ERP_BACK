"""
Excepciones específicas del módulo Socios de Negocio
"""

class SocioNegocioException(Exception):
    """Excepción base para el módulo de socios de negocio"""
    pass

class SocioNotFoundException(SocioNegocioException):
    """Excepción cuando no se encuentra un socio"""
    pass

class SocioAlreadyExistsException(SocioNegocioException):
    """Excepción cuando ya existe un socio con el mismo documento"""
    pass

class SocioValidationException(SocioNegocioException):
    """Excepción de validación de datos del socio"""
    pass

class RucConsultaException(SocioNegocioException):
    """Excepción en la consulta de RUC"""
    pass

class SunatServiceException(SocioNegocioException):
    """Excepción del servicio SUNAT"""
    pass
