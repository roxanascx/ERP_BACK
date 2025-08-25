"""
Modelos para configuración del sistema
=====================================

Modelos Pydantic para gestión de configuraciones y fechas/horas
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from bson import ObjectId
from .utils import PeruTimeUtils

class SystemConfigModel(BaseModel):
    """
    Modelo para configuración general del sistema
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    # ID para MongoDB
    id: Optional[str] = Field(default=None, alias="_id")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_object_id(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v
    
    # Configuraciones básicas
    config_key: str = Field(..., description="Clave única de configuración")
    config_value: str = Field(..., description="Valor de la configuración")
    config_type: str = Field(default="string", description="Tipo de dato (string, number, boolean, json)")
    description: Optional[str] = Field(None, description="Descripción de la configuración")
    category: str = Field(default="general", description="Categoría de la configuración")
    
    # Metadatos
    is_active: bool = Field(default=True, description="Si la configuración está activa")
    is_system: bool = Field(default=False, description="Si es configuración del sistema (no editable)")
    created_at: datetime = Field(default_factory=PeruTimeUtils.now_peru)
    updated_at: datetime = Field(default_factory=PeruTimeUtils.now_peru)
    created_by: Optional[str] = Field(None, description="Usuario que creó la configuración")
    updated_by: Optional[str] = Field(None, description="Usuario que actualizó la configuración")
    
    # Validaciones y restricciones
    allowed_values: Optional[List[str]] = Field(None, description="Valores permitidos (para validación)")
    min_value: Optional[float] = Field(None, description="Valor mínimo (para números)")
    max_value: Optional[float] = Field(None, description="Valor máximo (para números)")
    
    @field_validator('config_type')
    def validate_config_type(cls, v):
        allowed_types = ['string', 'number', 'boolean', 'json', 'date', 'datetime']
        if v not in allowed_types:
            raise ValueError(f"config_type debe ser uno de: {allowed_types}")
        return v
    
    @computed_field
    @property
    def parsed_value(self) -> Any:
        """Parsea el valor según el tipo de configuración"""
        if self.config_type == "number":
            return float(self.config_value)
        elif self.config_type == "boolean":
            return self.config_value.lower() in ['true', '1', 'yes', 'on']
        elif self.config_type == "json":
            import json
            return json.loads(self.config_value)
        elif self.config_type == "date":
            return datetime.fromisoformat(self.config_value).date()
        elif self.config_type == "datetime":
            return datetime.fromisoformat(self.config_value)
        else:
            return self.config_value


class TimeConfigModel(BaseModel):
    """
    Modelo para configuración de tiempo y zona horaria
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    # ID para MongoDB
    id: Optional[str] = Field(default=None, alias="_id")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_object_id(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v
    
    # Configuración de tiempo
    timezone: str = Field(default="America/Lima", description="Zona horaria del sistema")
    date_format: str = Field(default="%Y-%m-%d", description="Formato de fecha predeterminado")
    datetime_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Formato de fecha y hora predeterminado")
    time_format: str = Field(default="%H:%M:%S", description="Formato de hora predeterminado")
    
    # Configuraciones de negocio
    business_start_time: str = Field(default="09:00", description="Hora de inicio del día laboral")
    business_end_time: str = Field(default="18:00", description="Hora de fin del día laboral")
    business_days: List[int] = Field(default=[0, 1, 2, 3, 4], description="Días laborales (0=Lunes, 6=Domingo)")
    
    # Configuraciones fiscales
    fiscal_year_start: str = Field(default="01-01", description="Inicio del año fiscal (MM-DD)")
    fiscal_year_end: str = Field(default="12-31", description="Fin del año fiscal (MM-DD)")
    
    # Metadatos
    created_at: datetime = Field(default_factory=PeruTimeUtils.now_peru)
    updated_at: datetime = Field(default_factory=PeruTimeUtils.now_peru)
    created_by: Optional[str] = Field(None, description="Usuario que creó la configuración")
    updated_by: Optional[str] = Field(None, description="Usuario que actualizó la configuración")
    
    @computed_field
    @property
    def current_datetime_peru(self) -> datetime:
        """Fecha y hora actual en zona horaria configurada"""
        return PeruTimeUtils.now_peru()
    
    @computed_field
    @property
    def current_date_peru(self) -> date:
        """Fecha actual en zona horaria configurada"""
        return PeruTimeUtils.today_peru()
    
    @computed_field
    @property
    def current_business_day(self) -> datetime:
        """Día hábil actual"""
        return PeruTimeUtils.get_business_day_peru()
    
    @computed_field
    @property
    def is_business_hours(self) -> bool:
        """Verifica si estamos en horario laboral"""
        now = PeruTimeUtils.now_peru()
        current_time = now.time()
        
        # Parsear horarios de negocio
        from datetime import time as datetime_time
        start_parts = self.business_start_time.split(":")
        end_parts = self.business_end_time.split(":")
        
        start_time = datetime_time(int(start_parts[0]), int(start_parts[1]))
        end_time = datetime_time(int(end_parts[0]), int(end_parts[1]))
        
        # Verificar día y hora
        is_business_day = now.weekday() in self.business_days
        is_business_time = start_time <= current_time <= end_time
        
        return is_business_day and is_business_time
