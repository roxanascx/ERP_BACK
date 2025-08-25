#!/usr/bin/env python3
"""Test CRUD operations para cuentas contables"""
import requests
import json
from datetime import datetime

def test_crud_operations():
    base_url = 'http://localhost:8000/api/v1/accounting/plan/cuentas'
    
    print("🧪 Testing CRUD operations...\n")
    
    # Test código único para no chocar con datos existentes
    test_codigo = f"999{int(datetime.now().timestamp()) % 10000}"
    
    # Test 1: Crear nueva cuenta
    print("1️⃣ Test crear cuenta...")
    nueva_cuenta = {
        "codigo": test_codigo,
        "descripcion": "Cuenta de prueba CRUD",
        "nivel": 3,
        "clase_contable": 1,
        "naturaleza": "DEUDORA",
        "moneda": "MN"
    }
    
    resp = requests.post(base_url, json=nueva_cuenta)
    if resp.status_code == 200:
        cuenta_creada = resp.json()
        print(f"   ✅ Cuenta creada: {cuenta_creada['codigo']} - {cuenta_creada['descripcion']}")
        print(f"   ID: {cuenta_creada['id']}")
    else:
        print(f"   ❌ Error creating: {resp.status_code} - {resp.text}")
        return
    
    # Test 2: Obtener la cuenta creada
    print(f"\n2️⃣ Test obtener cuenta creada ({test_codigo})...")
    resp = requests.get(f"{base_url}/{test_codigo}")
    if resp.status_code == 200:
        cuenta = resp.json()
        print(f"   ✅ Encontrada: {cuenta['descripcion']}")
        print(f"   Naturaleza: {cuenta['naturaleza']}, Activa: {cuenta['activa']}")
    else:
        print(f"   ❌ Error getting: {resp.status_code} - {resp.text}")
    
    # Test 3: Actualizar la cuenta
    print(f"\n3️⃣ Test actualizar cuenta...")
    update_data = {
        "descripcion": "Cuenta de prueba CRUD - ACTUALIZADA",
        "acepta_movimiento": False
    }
    
    resp = requests.put(f"{base_url}/{test_codigo}", json=update_data)
    if resp.status_code == 200:
        cuenta_actualizada = resp.json()
        print(f"   ✅ Actualizada: {cuenta_actualizada['descripcion']}")
        print(f"   Acepta movimiento: {cuenta_actualizada['acepta_movimiento']}")
    else:
        print(f"   ❌ Error updating: {resp.status_code} - {resp.text}")
    
    # Test 4: Eliminar la cuenta (soft delete)
    print(f"\n4️⃣ Test eliminar cuenta...")
    resp = requests.delete(f"{base_url}/{test_codigo}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Eliminada: {result['message']}")
    else:
        print(f"   ❌ Error deleting: {resp.status_code} - {resp.text}")
    
    # Test 5: Verificar que la cuenta está inactiva
    print(f"\n5️⃣ Test verificar cuenta eliminada...")
    resp = requests.get(f"{base_url}/{test_codigo}")
    if resp.status_code == 200:
        cuenta = resp.json()
        print(f"   Cuenta aún existe - Activa: {cuenta['activa']}")
        if not cuenta['activa']:
            print("   ✅ Soft delete funcionó correctamente")
        else:
            print("   ⚠️ La cuenta sigue activa")
    else:
        print(f"   Cuenta no encontrada: {resp.status_code}")
    
    print("\n✅ Tests CRUD completados!")

def test_error_cases():
    base_url = 'http://localhost:8000/api/v1/accounting/plan/cuentas'
    
    print("\n🧪 Testing error cases...\n")
    
    # Test 1: Crear cuenta duplicada
    print("1️⃣ Test crear cuenta duplicada...")
    cuenta_duplicada = {
        "codigo": "101",  # Ya existe
        "descripcion": "Intento duplicado",
        "nivel": 3,
        "clase_contable": 1
    }
    
    resp = requests.post(base_url, json=cuenta_duplicada)
    if resp.status_code == 400:
        print("   ✅ Error 400 correcto para cuenta duplicada")
        print(f"   Mensaje: {resp.json()['detail']}")
    else:
        print(f"   ❌ Respuesta inesperada: {resp.status_code}")
    
    # Test 2: Obtener cuenta inexistente
    print("\n2️⃣ Test obtener cuenta inexistente...")
    resp = requests.get(f"{base_url}/999999999")
    if resp.status_code == 404:
        print("   ✅ Error 404 correcto para cuenta inexistente")
    else:
        print(f"   ❌ Respuesta inesperada: {resp.status_code}")
    
    print("\n✅ Tests de errores completados!")

if __name__ == "__main__":
    try:
        test_crud_operations()
        test_error_cases()
    except requests.ConnectionError:
        print("❌ No se pudo conectar al backend. ¿Está corriendo en localhost:8000?")
    except Exception as e:
        print(f"❌ Error: {e}")
