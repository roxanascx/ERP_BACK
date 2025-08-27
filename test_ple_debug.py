#!/usr/bin/env python3
"""
Script de debug más detallado para el endpoint PLE
"""

import requests
import json
import traceback

def test_ple_debug():
    url = "http://127.0.0.1:8000/api/v1/accounting/ple/generar"
    
    data = {
        "libro_diario_id": "68ae3823255bc9585ceec4c6",
        "ejercicio": 2025,
        "mes": 8
    }
    
    print("🔍 Testing con requests más detallado...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        # Primero probar si el endpoint está disponible
        print("\n1. Probando conexión básica...")
        response = requests.get("http://127.0.0.1:8000/api/v1/accounting/ple/contexto/68ae3823255bc9585ceec4c6")
        print(f"   Contexto status: {response.status_code}")
        
        print("\n2. Probando validación...")
        validation_data = {
            "libro_diario_id": "68ae3823255bc9585ceec4c6",
            "ejercicio": 2025,
            "mes": 8
        }
        response = requests.post("http://127.0.0.1:8000/api/v1/accounting/ple/validar", json=validation_data)
        print(f"   Validación status: {response.status_code}")
        if response.status_code == 200:
            validation_result = response.json()
            print(f"   Asientos encontrados: {validation_result.get('total_asientos', 'N/A')}")
        
        print("\n3. Probando generación PLE...")
        response = requests.post(url, json=data, timeout=60)
        
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ Respuesta JSON exitosa:")
                print(json.dumps(result, indent=2))
            except:
                print(f"✅ Respuesta no-JSON (posible archivo): {len(response.content)} bytes")
                if 'zip' in response.headers.get('content-type', ''):
                    with open('test_output.zip', 'wb') as f:
                        f.write(response.content)
                    print("📁 Archivo guardado como test_output.zip")
        else:
            print(f"❌ Error {response.status_code}")
            print(f"Response: {response.text}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_ple_debug()
