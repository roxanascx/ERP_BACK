#!/usr/bin/env python3
"""
Script de prueba para ExchangeRateService
========================================

Prueba las funcionalidades del nuevo servicio de tipos de cambio
"""

import asyncio
import sys
import os
from datetime import date, timedelta

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_exchange_rate_service():
    """Prueba el servicio de tipos de cambio"""
    print("🚀 Iniciando pruebas del ExchangeRateService")
    print("=" * 50)
    
    try:
        from app.modules.consultasapi.services.exchange_rate_service import ExchangeRateService
        
        service = ExchangeRateService()
        
        # Test 1: Consultar tipo de cambio de ayer
        print("\n📡 Test 1: Consultar tipo de cambio de ayer")
        ayer = date.today() - timedelta(days=1)
        
        data = await service.consultar_tipo_cambio_dia(ayer)
        if data:
            print(f"✅ {ayer}: Compra: {data.compra} | Venta: {data.venta}")
        else:
            print(f"❌ No se pudieron obtener datos para {ayer}")
        
        # Test 2: Verificar estado del servicio
        print("\n🔍 Test 2: Verificar estado del servicio")
        estado = await service.verificar_estado_servicio()
        print(f"API externa disponible: {estado.get('api_externa_disponible', False)}")
        print(f"Base de datos disponible: {estado.get('base_datos_disponible', False)}")
        
        # Test 3: Consultar tipo de cambio del 24 de agosto (sabemos que existe)
        print("\n📅 Test 3: Consultar tipo de cambio del 24 de agosto 2025")
        fecha_test = date(2025, 8, 24)
        
        data_24 = await service.consultar_tipo_cambio_dia(fecha_test)
        if data_24:
            print(f"✅ {fecha_test}: Compra: {data_24.compra} | Venta: {data_24.venta}")
            print(f"   SUNAT: {data_24.sunat}")
        else:
            print(f"❌ No se pudieron obtener datos para {fecha_test}")
        
        print("\n✅ Pruebas completadas")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("Asegúrate de que el servidor esté ejecutándose o las dependencias estén instaladas")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    asyncio.run(test_exchange_rate_service())
