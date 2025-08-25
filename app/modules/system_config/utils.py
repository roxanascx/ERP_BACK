"""
Utilidades para manejo de tiempo y zona horaria
===============================================

Funciones para trabajar con fechas y horas usando la zona horaria de Perú (America/Lima)
"""

from datetime import datetime, date, time
from typing import Optional, Union
import pytz
from dateutil import parser
from zoneinfo import ZoneInfo

# Zona horaria de Perú
PERU_TIMEZONE = pytz.timezone('America/Lima')

class PeruTimeUtils:
    """Utilidades para manejo de tiempo en zona horaria de Perú"""
    
    @staticmethod
    def get_peru_timezone():
        """Obtiene la zona horaria de Perú"""
        return PERU_TIMEZONE
    
    @staticmethod
    def now_peru() -> datetime:
        """Obtiene la fecha y hora actual en zona horaria de Perú"""
        utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        return utc_now.astimezone(PERU_TIMEZONE)
    
    @staticmethod
    def today_peru() -> date:
        """Obtiene la fecha actual en zona horaria de Perú"""
        return PeruTimeUtils.now_peru().date()
    
    @staticmethod
    def to_peru_time(dt: datetime) -> datetime:
        """
        Convierte una fecha/hora a zona horaria de Perú
        
        Args:
            dt: DateTime que puede ser naive o aware
            
        Returns:
            DateTime en zona horaria de Perú
        """
        if dt.tzinfo is None:
            # Si es naive, asumimos que está en UTC
            dt = pytz.UTC.localize(dt)
        
        return dt.astimezone(PERU_TIMEZONE)
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """
        Convierte una fecha/hora de Perú a UTC
        
        Args:
            dt: DateTime en zona horaria de Perú
            
        Returns:
            DateTime en UTC
        """
        if dt.tzinfo is None:
            # Si es naive, asumimos que está en zona horaria de Perú
            dt = PERU_TIMEZONE.localize(dt)
        
        return dt.astimezone(pytz.UTC)
    
    @staticmethod
    def parse_date_peru(date_str: str) -> datetime:
        """
        Parsea una cadena de fecha y la convierte a zona horaria de Perú
        
        Args:
            date_str: Cadena de fecha en formato ISO o común
            
        Returns:
            DateTime en zona horaria de Perú
        """
        parsed_dt = parser.parse(date_str)
        
        if parsed_dt.tzinfo is None:
            # Si no tiene timezone, asumimos zona horaria de Perú
            parsed_dt = PERU_TIMEZONE.localize(parsed_dt)
        else:
            # Si tiene timezone, convertimos a Perú
            parsed_dt = parsed_dt.astimezone(PERU_TIMEZONE)
        
        return parsed_dt
    
    @staticmethod
    def format_peru_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
        """
        Formatea una fecha/hora en zona horaria de Perú
        
        Args:
            dt: DateTime a formatear
            format_str: Formato de salida (por defecto: "%Y-%m-%d %H:%M:%S %Z")
            
        Returns:
            String formateado
        """
        peru_dt = PeruTimeUtils.to_peru_time(dt)
        return peru_dt.strftime(format_str)
    
    @staticmethod
    def get_business_day_peru() -> datetime:
        """
        Obtiene el día hábil actual en zona horaria de Perú
        Si es fin de semana, devuelve el próximo lunes
        """
        today = PeruTimeUtils.now_peru()
        
        # Si es sábado (5) o domingo (6), mover al próximo lunes
        if today.weekday() == 5:  # Sábado
            today = today.replace(day=today.day + 2)
        elif today.weekday() == 6:  # Domingo
            today = today.replace(day=today.day + 1)
        
        return today
    
    @staticmethod
    def is_business_day(dt: datetime) -> bool:
        """
        Verifica si una fecha es día hábil (lunes a viernes)
        
        Args:
            dt: DateTime a verificar
            
        Returns:
            True si es día hábil, False si es fin de semana
        """
        return dt.weekday() < 5  # 0-4 son lunes a viernes
    
    @staticmethod
    def start_of_day_peru(dt: Optional[datetime] = None) -> datetime:
        """
        Obtiene el inicio del día (00:00:00) para una fecha dada en zona horaria de Perú
        
        Args:
            dt: DateTime base (si es None, usa fecha actual)
            
        Returns:
            DateTime al inicio del día en zona horaria de Perú
        """
        if dt is None:
            dt = PeruTimeUtils.now_peru()
        else:
            dt = PeruTimeUtils.to_peru_time(dt)
        
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def end_of_day_peru(dt: Optional[datetime] = None) -> datetime:
        """
        Obtiene el final del día (23:59:59.999999) para una fecha dada en zona horaria de Perú
        
        Args:
            dt: DateTime base (si es None, usa fecha actual)
            
        Returns:
            DateTime al final del día en zona horaria de Perú
        """
        if dt is None:
            dt = PeruTimeUtils.now_peru()
        else:
            dt = PeruTimeUtils.to_peru_time(dt)
        
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    @staticmethod
    def days_difference_peru(start_date: datetime, end_date: datetime) -> int:
        """
        Calcula la diferencia en días entre dos fechas en zona horaria de Perú
        
        Args:
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            Número de días de diferencia
        """
        start_peru = PeruTimeUtils.to_peru_time(start_date).date()
        end_peru = PeruTimeUtils.to_peru_time(end_date).date()
        
        return (end_peru - start_peru).days
    
    @staticmethod
    def add_business_days(start_date: datetime, business_days: int) -> datetime:
        """
        Añade días hábiles a una fecha (excluyendo fines de semana)
        
        Args:
            start_date: Fecha inicial
            business_days: Número de días hábiles a añadir
            
        Returns:
            Nueva fecha después de añadir los días hábiles
        """
        current_date = PeruTimeUtils.to_peru_time(start_date)
        added_days = 0
        
        while added_days < business_days:
            current_date = current_date.replace(day=current_date.day + 1)
            
            # Solo contar si es día hábil
            if PeruTimeUtils.is_business_day(current_date):
                added_days += 1
        
        return current_date
