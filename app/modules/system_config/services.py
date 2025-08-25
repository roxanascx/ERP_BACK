"""
Servicios para configuración del sistema
========================================

Lógica de negocio para gestión de configuraciones y tiempo
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple

from .models import SystemConfigModel, TimeConfigModel
from .repositories import SystemConfigRepository, TimeConfigRepository
from .utils import PeruTimeUtils
from .schemas import (
    SystemConfigCreate, SystemConfigUpdate, SystemConfigQuery,
    TimeConfigUpdate
)


class SystemConfigService:
    """Servicio para gestión de configuraciones del sistema"""
    
    def __init__(self):
        self.config_repo = SystemConfigRepository()
    
    async def create_config(self, config_data: SystemConfigCreate) -> SystemConfigModel:
        """Crea una nueva configuración"""
        config = SystemConfigModel(**config_data.model_dump())
        return await self.config_repo.create_config(config)
    
    async def get_config_by_key(self, config_key: str) -> Optional[SystemConfigModel]:
        """Obtiene una configuración por su clave"""
        return await self.config_repo.get_config_by_key(config_key)
    
    async def get_config_value(self, config_key: str, default_value: Any = None) -> Any:
        """Obtiene el valor parseado de una configuración"""
        config = await self.get_config_by_key(config_key)
        if config and config.is_active:
            return config.parsed_value
        return default_value
    
    async def set_config_value(self, config_key: str, value: str, user_id: Optional[str] = None) -> SystemConfigModel:
        """Establece el valor de una configuración"""
        config = await self.get_config_by_key(config_key)
        if not config:
            raise ValueError(f"Configuración '{config_key}' no encontrada")
        
        if config.is_system:
            raise ValueError("No se puede modificar una configuración del sistema")
        
        updates = {
            "config_value": value,
            "updated_by": user_id
        }
        
        updated_config = await self.config_repo.update_config(config.id, updates)
        if not updated_config:
            raise ValueError("Error al actualizar la configuración")
        
        return updated_config
    
    async def list_configs(self, query: SystemConfigQuery, page: int = 1, size: int = 10) -> Tuple[List[SystemConfigModel], int]:
        """Lista configuraciones con filtros y paginación"""
        skip = (page - 1) * size
        
        configs, total = await self.config_repo.list_configs(
            category=query.category,
            config_type=query.config_type,
            is_active=query.is_active,
            is_system=query.is_system,
            search=query.search,
            skip=skip,
            limit=size
        )
        
        return configs, total
    
    async def update_config(self, config_id: str, updates: SystemConfigUpdate) -> Optional[SystemConfigModel]:
        """Actualiza una configuración"""
        config = await self.config_repo.get_config_by_id(config_id)
        if not config:
            raise ValueError("Configuración no encontrada")
        
        if config.is_system and updates.config_value is not None:
            raise ValueError("No se puede modificar el valor de una configuración del sistema")
        
        update_data = updates.model_dump(exclude_unset=True)
        return await self.config_repo.update_config(config_id, update_data)
    
    async def delete_config(self, config_id: str) -> bool:
        """Elimina una configuración"""
        return await self.config_repo.delete_config(config_id)
    
    async def initialize_default_configs(self):
        """Inicializa configuraciones por defecto del sistema"""
        default_configs = [
            {
                "config_key": "system.timezone",
                "config_value": "America/Lima",
                "config_type": "string",
                "description": "Zona horaria del sistema",
                "category": "system",
                "is_system": True
            },
            {
                "config_key": "system.default_currency",
                "config_value": "PEN",
                "config_type": "string",
                "description": "Moneda por defecto del sistema",
                "category": "currency",
                "is_system": True
            },
            {
                "config_key": "business.decimal_places",
                "config_value": "2",
                "config_type": "number",
                "description": "Número de decimales para cálculos financieros",
                "category": "business",
                "is_system": False
            },
            {
                "config_key": "business.tax_rate",
                "config_value": "18.0",
                "config_type": "number",
                "description": "Tasa de IGV en Perú (%)",
                "category": "business",
                "is_system": False
            }
        ]
        
        for config_data in default_configs:
            existing = await self.get_config_by_key(config_data["config_key"])
            if not existing:
                config = SystemConfigModel(**config_data)
                await self.config_repo.create_config(config)


class TimeConfigService:
    """Servicio para gestión de configuración de tiempo"""
    
    def __init__(self):
        self.time_repo = TimeConfigRepository()
    
    async def get_time_config(self) -> TimeConfigModel:
        """Obtiene la configuración de tiempo actual"""
        config = await self.time_repo.get_time_config()
        if not config:
            # Crear configuración por defecto
            config = await self.create_default_time_config()
        return config
    
    async def create_default_time_config(self) -> TimeConfigModel:
        """Crea la configuración de tiempo por defecto"""
        default_config = TimeConfigModel(
            timezone="America/Lima",
            date_format="%Y-%m-%d",
            datetime_format="%Y-%m-%d %H:%M:%S",
            time_format="%H:%M:%S",
            business_start_time="09:00",
            business_end_time="18:00",
            business_days=[0, 1, 2, 3, 4],  # Lunes a Viernes
            fiscal_year_start="01-01",
            fiscal_year_end="12-31"
        )
        
        return await self.time_repo.create_or_update_time_config(default_config)
    
    async def update_time_config(self, updates: TimeConfigUpdate) -> TimeConfigModel:
        """Actualiza la configuración de tiempo"""
        update_data = updates.model_dump(exclude_unset=True)
        updated_config = await self.time_repo.update_time_config(update_data)
        
        if not updated_config:
            raise ValueError("Error al actualizar la configuración de tiempo")
        
        return updated_config
    
    async def get_current_peru_time(self) -> datetime:
        """Obtiene la hora actual en zona horaria de Perú"""
        return PeruTimeUtils.now_peru()
    
    async def is_business_hours(self) -> bool:
        """Verifica si estamos en horario laboral"""
        config = await self.get_time_config()
        return config.is_business_hours
    
    async def get_next_business_day(self, from_date: Optional[date] = None) -> date:
        """Obtiene el próximo día hábil"""
        if from_date is None:
            from_date = PeruTimeUtils.today_peru()
        
        config = await self.get_time_config()
        current_date = datetime.combine(from_date, datetime.min.time())
        current_date = PeruTimeUtils.to_peru_time(current_date)
        
        # Buscar el próximo día hábil
        while current_date.weekday() not in config.business_days:
            current_date = current_date.replace(day=current_date.day + 1)
        
        return current_date.date()
    
    async def add_business_days(self, start_date: date, business_days: int) -> date:
        """Añade días hábiles a una fecha"""
        config = await self.get_time_config()
        current_date = datetime.combine(start_date, datetime.min.time())
        current_date = PeruTimeUtils.to_peru_time(current_date)
        
        added_days = 0
        while added_days < business_days:
            current_date = current_date.replace(day=current_date.day + 1)
            
            if current_date.weekday() in config.business_days:
                added_days += 1
        
        return current_date.date()
    
    async def format_datetime(self, dt: datetime, format_type: str = "datetime") -> str:
        """Formatea una fecha/hora según la configuración"""
        config = await self.get_time_config()
        peru_dt = PeruTimeUtils.to_peru_time(dt)
        
        if format_type == "date":
            return peru_dt.strftime(config.date_format)
        elif format_type == "time":
            return peru_dt.strftime(config.time_format)
        else:  # datetime
            return peru_dt.strftime(config.datetime_format)


class SystemStatusService:
    """Servicio para obtener el estado general del sistema"""
    
    def __init__(self):
        self.config_service = SystemConfigService()
        self.time_service = TimeConfigService()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Obtiene el estado general del sistema"""
        time_config = await self.time_service.get_time_config()
        
        # Contar configuraciones activas
        configs, total_configs = await self.config_service.list_configs(
            SystemConfigQuery(is_active=True),
            page=1, size=1000
        )
        
        return {
            "current_time_peru": time_config.current_datetime_peru,
            "is_business_hours": time_config.is_business_hours,
            "current_business_day": time_config.current_business_day.date(),
            "active_configs": len(configs),
            "system_timezone": time_config.timezone
        }
