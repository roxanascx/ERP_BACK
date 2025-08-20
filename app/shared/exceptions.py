from fastapi import HTTPException, status

# Excepciones personalizadas para el ERP

class ERPException(HTTPException):
    """Excepción base para el ERP"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class AccountingException(ERPException):
    """Excepciones específicas de contabilidad"""
    pass

class InsufficientFundsException(AccountingException):
    """Cuando no hay fondos suficientes"""
    def __init__(self, detail: str = "Fondos insuficientes"):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)

class InvalidAccountException(AccountingException):
    """Cuando una cuenta contable no es válida"""
    def __init__(self, account_code: str):
        super().__init__(f"Cuenta contable no válida: {account_code}", status.HTTP_404_NOT_FOUND)

class UnbalancedEntryException(AccountingException):
    """Cuando un asiento contable no está balanceado"""
    def __init__(self, detail: str = "El asiento contable no está balanceado (debe = haber)"):
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)

class CustomerException(ERPException):
    """Excepciones específicas de clientes"""
    pass

class CustomerNotFound(CustomerException):
    """Cuando un cliente no existe"""
    def __init__(self, customer_id: str):
        super().__init__(f"Cliente no encontrado: {customer_id}", status.HTTP_404_NOT_FOUND)

class DuplicateCustomerException(CustomerException):
    """Cuando se intenta crear un cliente duplicado"""
    def __init__(self, detail: str = "Cliente ya existe"):
        super().__init__(detail, status.HTTP_409_CONFLICT)

class UserException(ERPException):
    """Excepciones específicas de usuarios"""
    pass

class UserNotFound(UserException):
    """Cuando un usuario no existe"""
    def __init__(self, user_id: str):
        super().__init__(f"Usuario no encontrado: {user_id}", status.HTTP_404_NOT_FOUND)

class InvalidCredentialsException(UserException):
    """Cuando las credenciales son incorrectas"""
    def __init__(self):
        super().__init__("Credenciales incorrectas", status.HTTP_401_UNAUTHORIZED)

class InsufficientPermissionsException(UserException):
    """Cuando el usuario no tiene permisos suficientes"""
    def __init__(self):
        super().__init__("Permisos insuficientes", status.HTTP_403_FORBIDDEN)

# Excepciones específicas de SIRE
class SireException(ERPException):
    """Excepción base para SIRE"""
    pass

class SireValidationException(SireException):
    """Excepciones de validación SIRE"""
    def __init__(self, detail: str, field: str = None):
        if field:
            detail = f"Error en campo '{field}': {detail}"
        super().__init__(detail, status.HTTP_400_BAD_REQUEST)

class SireAuthException(SireException):
    """Excepciones de autenticación SIRE"""
    def __init__(self, detail: str = "Error de autenticación SIRE"):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)

class SireApiException(SireException):
    """Excepciones de API SIRE"""
    def __init__(self, detail: str, status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE):
        super().__init__(detail, status_code)

class SireConnectionException(SireException):
    """Excepciones de conexión SIRE"""
    def __init__(self, detail: str = "Error de conexión con SIRE"):
        super().__init__(detail, status.HTTP_503_SERVICE_UNAVAILABLE)

class SireTimeoutException(SireException):
    """Excepciones de timeout SIRE"""
    def __init__(self, detail: str = "Timeout en consulta SIRE"):
        super().__init__(detail, status.HTTP_504_GATEWAY_TIMEOUT)

class SireNotFound(SireException):
    """Cuando un recurso SIRE no existe"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} no encontrado: {identifier}", status.HTTP_404_NOT_FOUND)

class SireRateLimitException(SireException):
    """Cuando se excede el límite de consultas SIRE"""
    def __init__(self, detail: str = "Límite de consultas SIRE excedido"):
        super().__init__(detail, status.HTTP_429_TOO_MANY_REQUESTS)
