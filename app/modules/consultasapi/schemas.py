"""
Esquemas de request y response para las consultas API
"""

from typing import Optional
from pydantic import BaseModel, Field, validator

class RucConsultaRequest(BaseModel):
    """Request para consulta de RUC"""
    ruc: str = Field(..., description="RUC de 11 dígitos", min_length=11, max_length=11)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo números')
        if len(v) != 11:
            raise ValueError('RUC debe tener exactamente 11 dígitos')
        # Validar que empiece con 10, 15, 17, 20
        if not v.startswith(('10', '15', '17', '20')):
            raise ValueError('RUC debe empezar con 10, 15, 17 o 20')
        return v

class DniConsultaRequest(BaseModel):
    """Request para consulta de DNI"""
    dni: str = Field(..., description="DNI de 8 dígitos", min_length=8, max_length=8)
    
    @validator('dni')
    def validate_dni(cls, v):
        if not v.isdigit():
            raise ValueError('DNI debe contener solo números')
        if len(v) != 8:
            raise ValueError('DNI debe tener exactamente 8 dígitos')
        return v

class ConsultaEstadoResponse(BaseModel):
    """Response para el estado de los servicios de consulta"""
    servicio_sunat: bool = Field(..., description="Estado del servicio SUNAT")
    servicio_reniec: bool = Field(..., description="Estado del servicio RENIEC")
    apis_disponibles: dict = Field(..., description="APIs disponibles por servicio")
    version: str = Field(..., description="Versión del módulo")
    endpoints_activos: list = Field(..., description="Endpoints activos")
