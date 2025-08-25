#!/usr/bin/env python3
"""Test endpoints del módulo de contabilidad"""
import requests
import json

def test_endpoints():
    base_url = 'http://localhost:8000/api/v1/accounting'
    
    print("🧪 Testing accounting endpoints...\n")
    
    # Test 1: Ping
    print("1️⃣ Test ping...")
    resp = requests.get(f'{base_url}/ping')
    print(f"   Status: {resp.status_code} - {resp.json()}")
    
    # Test 2: Estadísticas
    print("\n2️⃣ Test estadísticas...")
    resp = requests.get(f'{base_url}/plan/estadisticas')
    if resp.status_code == 200:
        stats = resp.json()
        print(f"   Total cuentas: {stats['total_cuentas']}")
        print(f"   Cuentas activas: {stats['cuentas_activas']}")
        print(f"   Clases: {len(stats['por_clase'])}")
        print(f"   Niveles: {len(stats['por_nivel'])}")
    else:
        print(f"   Error: {resp.status_code} - {resp.text}")
    
    # Test 3: Lista de cuentas
    print("\n3️⃣ Test lista cuentas (primeras 5)...")
    resp = requests.get(f'{base_url}/plan/cuentas')
    if resp.status_code == 200:
        cuentas = resp.json()
        print(f"   Total encontradas: {len(cuentas)}")
        for cuenta in cuentas[:5]:
            print(f"   {cuenta['codigo']} - {cuenta['descripcion']}")
    else:
        print(f"   Error: {resp.status_code} - {resp.text}")
    
    # Test 4: Obtener cuenta específica
    print("\n4️⃣ Test obtener cuenta específica (código '101')...")
    resp = requests.get(f'{base_url}/plan/cuentas/101')
    if resp.status_code == 200:
        cuenta = resp.json()
        print(f"   {cuenta['codigo']} - {cuenta['descripcion']}")
        print(f"   Nivel: {cuenta['nivel']}, Clase: {cuenta['clase_contable']}")
        print(f"   Naturaleza: {cuenta['naturaleza']}")
    else:
        print(f"   Error: {resp.status_code} - {resp.text}")
    
    # Test 5: Estructura jerárquica
    print("\n5️⃣ Test estructura jerárquica...")
    resp = requests.get(f'{base_url}/plan/estructura')
    if resp.status_code == 200:
        estructura = resp.json()
        print(f"   Total clases: {estructura['total_clases']}")
        if estructura['estructura']:
            print("   Primeras 3 clases:")
            for clase in estructura['estructura'][:3]:
                print(f"   {clase['codigo']} - {clase['descripcion']}")
    else:
        print(f"   Error: {resp.status_code} - {resp.text}")
    
    print("\n✅ Tests completados!")

if __name__ == "__main__":
    try:
        test_endpoints()
    except requests.ConnectionError:
        print("❌ No se pudo conectar al backend. ¿Está corriendo en localhost:8000?")
    except Exception as e:
        print(f"❌ Error: {e}")
