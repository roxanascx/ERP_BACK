"""
Schemas para el módulo de configuración del sistema
==================================================

Esquemas Pydantic para validación y serialización de datos
"""

from datetime import datetime, date, time
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, validator


# ===========================================
# SCHEMAS PARA CONFIGURACIONES DEL SISTEMA
# ===========================================

class SystemConfigBase(BaseModel):
    """Schema base para configuraciones del sistema"""
    key: str = Field(..., description="Clave única de la configuración")
    value: Any = Field(..., description="Valor de la configuración")
    config_type: str = Field(..., description="Tipo de datos (string, number, boolean, json)")
    category: str = Field("general", description="Categoría de la configuración")
    description: Optional[str] = Field(None, description="Descripción de la configuración")
    is_active: bool = Field(True, description="Si la configuración está activa")
    is_system: bool = Field(False, description="Si es una configuración del sistema")


class SystemConfigCreate(SystemConfigBase):
    """Schema para crear configuración del sistema"""
    pass


class SystemConfigUpdate(BaseModel):
    """Schema para actualizar configuración del sistema"""
    value: Optional[Any] = None
    config_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_system: Optional[bool] = None


class SystemConfigResponse(SystemConfigBase):
    """Schema de respuesta para configuración del sistema"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    updated_at: datetime


class SystemConfigQuery(BaseModel):
    """Schema para filtros de consulta de configuraciones"""
    category: Optional[str] = None
    config_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_system: Optional[bool] = None
    search: Optional[str] = None


class SystemConfigListResponse(BaseModel):
    """Schema de respuesta para lista de configuraciones"""
    configs: List[SystemConfigResponse]
    total: int
    page: int
    size: int


# ===========================================
# SCHEMAS PARA CONFIGURACIÓN DE TIEMPO
# ===========================================

class TimeConfigUpdate(BaseModel):
    """Schema para actualizar configuración de tiempo"""
    business_hour_start: Optional[time] = Field(None, description="Hora de inicio del horario laboral")
    business_hour_end: Optional[time] = Field(None, description="Hora de fin del horario laboral")
    time_format: Optional[str] = Field(None, description="Formato para mostrar la hora")
    date_format: Optional[str] = Field(None, description="Formato para mostrar la fecha")
    datetime_format: Optional[str] = Field(None, description="Formato para mostrar fecha y hora")


class TimeConfigResponse(BaseModel):
    """Schema de respuesta para configuración de tiempo"""
    model_config = ConfigDict(from_attributes=True)
    
    timezone: str
    current_datetime_peru: datetime
    current_date_peru: date
    current_time_peru: time
    is_business_hours: bool
    current_business_day: datetime
    business_hour_start: time
    business_hour_end: time
    time_format: str
    date_format: str
    datetime_format: str


# ===========================================
# SCHEMAS PARA ESTADO DEL SISTEMA
# ===========================================

class SystemStatus(BaseModel):
    """Schema para el estado general del sistema"""
    model_config = ConfigDict(from_attributes=True)
    
    current_time_peru: datetime
    is_business_hours: bool
    current_business_day: date
    active_configs: int
    system_timezone: str
