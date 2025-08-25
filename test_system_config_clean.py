#!/usr/bin/env python3
"""
Script de prueba para el módulo System Config (sin tipo de cambio)
===============================================================

Prueba todas las funcionalidades del módulo de configuración del sistema
sin las funcionalidades de tipo de cambio que fueron removidas.
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000/api/v1/system"

def print_section(title):
    """Imprime una sección"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)

def test_endpoint(method, url, data=None, description=""):
    """Prueba un endpoint y muestra el resultado"""
    try:
        print(f"\n📡 {description}")
        print(f"   {method} {url}")
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
            
        print(f"   ✅ Status: {response.status_code}")
        
        if response.status_code < 400:
            try:
                result = response.json()
                print(f"   📄 Response: {json.dumps(result, indent=2, default=str)}")
                return result
            except:
                print(f"   📄 Response: {response.text}")
                return response.text
        else:
            print(f"   ❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   💥 Exception: {str(e)}")
        return None

def main():
    print("🚀 Iniciando pruebas del módulo System Config")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"🕐 Fecha/Hora: {datetime.now()}")
    
    # ===========================================
    # PRUEBAS DE HEALTH CHECK Y TIEMPO
    # ===========================================
    
    print_section("HEALTH CHECK Y TIEMPO")
    
    # Health check
    test_endpoint("GET", f"{BASE_URL}/health", 
                 description="Health check del módulo")
    
    # Tiempo actual de Perú
    test_endpoint("GET", f"{BASE_URL}/time/current-peru", 
                 description="Obtener tiempo actual de Perú")
    
    # Verificar horario laboral
    test_endpoint("GET", f"{BASE_URL}/time/business-hours", 
                 description="Verificar si estamos en horario laboral")
    
    # ===========================================
    # PRUEBAS DE CONFIGURACIÓN DE TIEMPO
    # ===========================================
    
    print_section("CONFIGURACIÓN DE TIEMPO")
    
    # Obtener configuración de tiempo
    test_endpoint("GET", f"{BASE_URL}/time-config", 
                 description="Obtener configuración de tiempo actual")
    
    # Actualizar configuración de tiempo
    time_update = {
        "business_hour_start": "08:30:00",
        "business_hour_end": "17:30:00",
        "time_format": "%H:%M:%S",
        "date_format": "%d/%m/%Y",
        "datetime_format": "%d/%m/%Y %H:%M:%S"
    }
    
    test_endpoint("PUT", f"{BASE_URL}/time-config", time_update,
                 description="Actualizar configuración de tiempo")
    
    # ===========================================
    # PRUEBAS DE CONFIGURACIONES DEL SISTEMA
    # ===========================================
    
    print_section("CONFIGURACIONES DEL SISTEMA")
    
    # Inicializar configuraciones por defecto
    test_endpoint("POST", f"{BASE_URL}/configs/initialize", 
                 description="Inicializar configuraciones por defecto")
    
    # Listar configuraciones
    test_endpoint("GET", f"{BASE_URL}/configs?page=1&size=5", 
                 description="Listar configuraciones (paginado)")
    
    # Crear nueva configuración
    new_config = {
        "key": "app.test_config",
        "value": "test_value_123",
        "config_type": "string",
        "category": "testing",
        "description": "Configuración de prueba para el módulo",
        "is_active": True,
        "is_system": False
    }
    
    created_config = test_endpoint("POST", f"{BASE_URL}/configs", new_config,
                                  description="Crear nueva configuración")
    
    if created_config:
        config_id = created_config.get("id")
        
        # Obtener configuración por clave
        test_endpoint("GET", f"{BASE_URL}/configs/app.test_config", 
                     description="Obtener configuración por clave")
        
        # Actualizar configuración
        config_update = {
            "value": "updated_test_value_456",
            "description": "Configuración actualizada mediante prueba",
            "is_active": True
        }
        
        test_endpoint("PUT", f"{BASE_URL}/configs/{config_id}", config_update,
                     description="Actualizar configuración")
        
        # Eliminar configuración
        test_endpoint("DELETE", f"{BASE_URL}/configs/{config_id}", 
                     description="Eliminar configuración de prueba")
    
    # Filtrar configuraciones por categoría
    test_endpoint("GET", f"{BASE_URL}/configs?category=general&page=1&size=3", 
                 description="Filtrar configuraciones por categoría 'general'")
    
    # Buscar configuraciones
    test_endpoint("GET", f"{BASE_URL}/configs?search=app&page=1&size=3", 
                 description="Buscar configuraciones que contengan 'app'")
    
    # ===========================================
    # PRUEBAS DE ESTADO DEL SISTEMA
    # ===========================================
    
    print_section("ESTADO DEL SISTEMA")
    
    # Estado general del sistema (puede fallar si no hay MongoDB)
    test_endpoint("GET", f"{BASE_URL}/status", 
                 description="Obtener estado general del sistema")
    
    print_section("RESUMEN")
    print("✅ Pruebas completadas")
    print("📝 Notas:")
    print("   - Las funcionalidades de tipo de cambio han sido removidas")
    print("   - El módulo ahora solo gestiona tiempo y configuraciones")
    print("   - Algunos endpoints pueden fallar si MongoDB no está disponible")
    print("   - Los endpoints de tiempo funcionan sin base de datos")

if __name__ == "__main__":
    main()
