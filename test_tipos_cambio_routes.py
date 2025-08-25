#!/usr/bin/env python3
"""
Script de prueba para las rutas de tipos de cambio
=================================================

Prueba todos los endpoints nuevos del módulo consultasapi
"""

import requests
import json
from datetime import datetime, date, timedelta

# Configuración
BASE_URL = "http://localhost:8000/api/v1/consultas"

def print_section(title):
    """Imprime una sección"""
    print(f"\n{'='*60}")
    print(f"💰 {title}")
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
            
        print(f"   ✅ Status: {response.status_code}")
        
        if response.status_code < 400:
            try:
                result = response.json()
                print(f"   📄 Response: {json.dumps(result, indent=2, default=str)[:500]}...")
                return result
            except:
                print(f"   📄 Response: {response.text[:200]}...")
                return response.text
        else:
            print(f"   ❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"   💥 Exception: {str(e)}")
        return None

def main():
    print("🚀 Iniciando pruebas de las rutas de tipos de cambio")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"🕐 Fecha/Hora: {datetime.now()}")
    
    # ===========================================
    # PRUEBAS DE HEALTH CHECK ACTUALIZADO
    # ===========================================
    
    print_section("HEALTH CHECK ACTUALIZADO")
    
    # Health check del módulo
    test_endpoint("GET", f"{BASE_URL}/health", 
                 description="Health check del módulo consultasapi")
    
    # Estado de tipos de cambio
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio/estado", 
                 description="Estado del servicio de tipos de cambio")
    
    # ===========================================
    # PRUEBAS DE CONSULTA DE TIPOS DE CAMBIO
    # ===========================================
    
    print_section("CONSULTA DE TIPOS DE CAMBIO")
    
    # Obtener tipo de cambio actual
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio/actual", 
                 description="Obtener tipo de cambio actual USD -> PEN")
    
    # Obtener tipo de cambio de ayer
    ayer = date.today() - timedelta(days=1)
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio/{ayer}", 
                 description=f"Obtener tipo de cambio para {ayer}")
    
    # Obtener tipo de cambio del 24 de agosto (sabemos que existe en la API)
    fecha_agosto = "2025-08-24"
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio/{fecha_agosto}", 
                 description=f"Obtener tipo de cambio para {fecha_agosto}")
    
    # ===========================================
    # PRUEBAS DE LISTADO CON FILTROS
    # ===========================================
    
    print_section("LISTADO Y FILTROS")
    
    # Listar todos los tipos de cambio (paginado)
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio?page=1&size=5", 
                 description="Listar tipos de cambio (primera página)")
    
    # Filtrar por rango de fechas
    fecha_desde = date.today() - timedelta(days=7)
    fecha_hasta = date.today()
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio?fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}&size=10", 
                 description="Filtrar por últimos 7 días")
    
    # Filtrar por monedas específicas
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio?moneda_origen=USD&moneda_destino=PEN&size=5", 
                 description="Filtrar por USD -> PEN")
    
    # Filtrar solo oficiales
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio?es_oficial=true&size=5", 
                 description="Solo tipos de cambio oficiales")
    
    # ===========================================
    # PRUEBAS DE ACTUALIZACIÓN
    # ===========================================
    
    print_section("ACTUALIZACIÓN DE DATOS")
    
    # Actualizar tipo de cambio de hoy
    hoy = date.today()
    update_data = {
        "fecha_desde": hoy.isoformat(),
        "fecha_hasta": hoy.isoformat(),
        "forzar_actualizacion": True
    }
    
    test_endpoint("POST", f"{BASE_URL}/tipos-cambio/actualizar", update_data,
                 description="Actualizar tipo de cambio de hoy")
    
    # Poblar datos históricos (solo 3 días para no sobrecargar)
    fecha_inicio = date.today() - timedelta(days=3)
    fecha_fin = date.today() - timedelta(days=1)
    
    test_endpoint("POST", f"{BASE_URL}/tipos-cambio/poblar-historicos?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}&forzar_actualizacion=false", 
                 description="Poblar datos históricos (últimos 3 días)")
    
    # ===========================================
    # PRUEBAS DE CASOS EDGE
    # ===========================================
    
    print_section("CASOS EDGE Y VALIDACIONES")
    
    # Intentar obtener fecha futura (debe fallar)
    fecha_futura = date.today() + timedelta(days=1)
    test_endpoint("GET", f"{BASE_URL}/tipos-cambio/{fecha_futura}", 
                 description=f"Intentar obtener fecha futura {fecha_futura} (debe fallar)")
    
    # Intentar rango de fechas inválido (debe fallar)
    invalid_update = {
        "fecha_desde": "2025-08-30",
        "fecha_hasta": "2025-08-25",  # fecha_hasta < fecha_desde
        "forzar_actualizacion": False
    }
    
    test_endpoint("POST", f"{BASE_URL}/tipos-cambio/actualizar", invalid_update,
                 description="Rango de fechas inválido (debe fallar)")
    
    print_section("RESUMEN")
    print("✅ Pruebas completadas")
    print("📝 Notas:")
    print("   - Los endpoints de tipos de cambio están implementados")
    print("   - Se excluye el endpoint de conversión como solicitaste")
    print("   - Los datos se obtienen de eApiPeru (misma API de tu script)")
    print("   - Algunos endpoints pueden fallar si MongoDB no está disponible")
    print("   - Los datos se almacenan en base de datos para consulta rápida")

if __name__ == "__main__":
    main()
