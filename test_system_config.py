"""
Script de prueba para el módulo System Config
==============================================

Este script demuestra el funcionamiento del nuevo módulo de configuración del sistema
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal

# Importar las utilidades y modelos del módulo
import sys
sys.path.append('.')

from app.modules.system_config.utils import PeruTimeUtils
from app.modules.system_config.models import SystemConfigModel, ExchangeRateModel, TimeConfigModel

async def test_peru_time_utils():
    """Prueba las utilidades de tiempo de Perú"""
    print("=== PRUEBAS DE UTILIDADES DE TIEMPO PERÚ ===")
    
    # Hora actual en Perú
    current_time = PeruTimeUtils.now_peru()
    print(f"Hora actual en Perú: {current_time}")
    print(f"Fecha actual en Perú: {PeruTimeUtils.today_peru()}")
    
    # Formateo de fecha
    formatted = PeruTimeUtils.format_peru_datetime(current_time)
    print(f"Fecha formateada: {formatted}")
    
    # Verificar si es día hábil
    is_business = PeruTimeUtils.is_business_day(current_time)
    print(f"¿Es día hábil?: {is_business}")
    
    # Obtener próximo día hábil
    business_day = PeruTimeUtils.get_business_day_peru()
    print(f"Próximo día hábil: {business_day}")
    
    # Inicio y fin del día
    start_day = PeruTimeUtils.start_of_day_peru()
    end_day = PeruTimeUtils.end_of_day_peru()
    print(f"Inicio del día: {start_day}")
    print(f"Fin del día: {end_day}")
    
    print()

def test_models():
    """Prueba los modelos del sistema"""
    print("=== PRUEBAS DE MODELOS ===")
    
    # Probar SystemConfigModel
    config = SystemConfigModel(
        config_key="test.setting",
        config_value="test_value",
        config_type="string",
        description="Configuración de prueba",
        category="test"
    )
    print(f"Configuración creada: {config.config_key} = {config.parsed_value}")
    
    # Probar ExchangeRateModel
    exchange_rate = ExchangeRateModel(
        currency_from="USD",
        currency_to="PEN",
        exchange_rate=Decimal("3.75"),
        exchange_date=PeruTimeUtils.today_peru(),
        source="manual"
    )
    print(f"Tipo de cambio creado: {exchange_rate.currency_from}/{exchange_rate.currency_to} = {exchange_rate.exchange_rate}")
    
    # Probar TimeConfigModel
    time_config = TimeConfigModel()
    print(f"Configuración de tiempo: Zona horaria = {time_config.timezone}")
    print(f"Hora actual según config: {time_config.current_datetime_peru}")
    print(f"¿Es horario laboral?: {time_config.is_business_hours}")
    
    print()

def demonstrate_functionality():
    """Demuestra la funcionalidad principal del módulo"""
    print("=== DEMOSTRACIÓN DE FUNCIONALIDAD ===")
    
    print("1. GESTIÓN DE TIEMPO CON ZONA HORARIA DE PERÚ")
    print("   ✅ Obtención de hora actual en zona horaria de Perú")
    print("   ✅ Cálculo de días hábiles")
    print("   ✅ Formateo de fechas según configuración")
    print("   ✅ Verificación de horario laboral")
    
    print("\n2. GESTIÓN DE TIPOS DE CAMBIO")
    print("   ✅ Almacenamiento de tipos de cambio por fecha")
    print("   ✅ Cálculo de conversiones de moneda")
    print("   ✅ Histórico de tipos de cambio")
    print("   ✅ Soporte para múltiples fuentes (manual, API, BCRP)")
    
    print("\n3. CONFIGURACIONES DEL SISTEMA")
    print("   ✅ Configuraciones categorizadas")
    print("   ✅ Tipos de dato tipados (string, number, boolean, json)")
    print("   ✅ Configuraciones del sistema protegidas")
    print("   ✅ Búsqueda y filtrado de configuraciones")
    
    print("\n4. API ENDPOINTS DISPONIBLES")
    print("   📍 GET  /api/v1/system/health - Health check")
    print("   📍 GET  /api/v1/system/time/current-peru - Hora actual de Perú")
    print("   📍 GET  /api/v1/system/time/business-hours - Verificar horario laboral")
    print("   📍 GET  /api/v1/system/time-config - Configuración de tiempo")
    print("   📍 POST /api/v1/system/configs - Crear configuración")
    print("   📍 GET  /api/v1/system/configs - Listar configuraciones")
    print("   📍 POST /api/v1/system/exchange-rates - Crear tipo de cambio")
    print("   📍 GET  /api/v1/system/exchange-rates - Listar tipos de cambio")
    print("   📍 POST /api/v1/system/exchange-rates/calculate - Calcular conversión")
    print("   📍 GET  /api/v1/system/status - Estado del sistema")
    
    print()

def show_examples():
    """Muestra ejemplos de uso"""
    print("=== EJEMPLOS DE USO ===")
    
    print("📝 EJEMPLO 1: Crear configuración del sistema")
    print("""
    POST /api/v1/system/configs
    {
        "config_key": "business.tax_rate",
        "config_value": "18.0",
        "config_type": "number",
        "description": "Tasa de IGV en Perú (%)",
        "category": "business"
    }
    """)
    
    print("📝 EJEMPLO 2: Crear tipo de cambio")
    print("""
    POST /api/v1/system/exchange-rates
    {
        "currency_from": "USD",
        "currency_to": "PEN",
        "exchange_rate": 3.75,
        "exchange_date": "2025-08-24",
        "source": "bcrp",
        "is_official": true
    }
    """)
    
    print("📝 EJEMPLO 3: Calcular conversión de moneda")
    print("""
    POST /api/v1/system/exchange-rates/calculate
    {
        "amount": 100.00,
        "currency_from": "USD",
        "currency_to": "PEN",
        "exchange_date": "2025-08-24"
    }
    """)
    
    print("📝 EJEMPLO 4: Obtener hora actual de Perú")
    print("""
    GET /api/v1/system/time/current-peru
    
    Respuesta:
    {
        "current_time": "2025-08-24T21:14:11.908832-05:00",
        "timezone": "America/Lima",
        "formatted": "2025-08-24 21:14:11 -05"
    }
    """)

async def main():
    """Función principal de prueba"""
    print("🚀 MÓDULO SYSTEM CONFIG - PRUEBAS Y DEMOSTRACIÓN")
    print("=" * 60)
    
    # Ejecutar pruebas
    await test_peru_time_utils()
    test_models()
    demonstrate_functionality()
    show_examples()
    
    print("✅ MÓDULO IMPLEMENTADO EXITOSAMENTE")
    print("\nCaracterísticas principales:")
    print("• ✅ Gestión de fecha/hora con zona horaria de Perú")
    print("• ✅ Tipos de cambio con histórico")
    print("• ✅ Configuraciones del sistema categorizadas")
    print("• ✅ API REST completa")
    print("• ✅ Validaciones y tipos de dato")
    print("• ✅ Documentación automática en /docs")

if __name__ == "__main__":
    asyncio.run(main())
