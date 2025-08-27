#!/usr/bin/env python3
"""
Script de prueba para el endpoint de generación PLE
"""

import requests
import json

def test_ple_generar():
    # URL del endpoint
    url = "http://127.0.0.1:8000/api/v1/accounting/ple/generar"
    
    # Datos de prueba
    data = {
        "libro_diario_id": "68ae3823255bc9585ceec4c6",
        "ejercicio": 2025,
        "mes": 8
    }
    
    print("🧪 Probando endpoint de generación PLE...")
    print(f"URL: {url}")
    print(f"Datos: {json.dumps(data, indent=2)}")
    print("-" * 50)
    
    try:
        # Realizar la petición
        response = requests.post(url, json=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Respuesta exitosa")
            
            # Si es un archivo ZIP, guardar
            if 'application/zip' in response.headers.get('content-type', ''):
                with open('ple_export_test.zip', 'wb') as f:
                    f.write(response.content)
                print(f"📁 Archivo guardado como: ple_export_test.zip ({len(response.content)} bytes)")
            else:
                # Si es JSON, mostrar el contenido
                try:
                    json_response = response.json()
                    print(f"📄 Respuesta JSON: {json.dumps(json_response, indent=2)}")
                except:
                    print(f"📄 Respuesta texto: {response.text[:500]}...")
        else:
            print("❌ Error en la respuesta")
            print(f"Texto de error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_ple_generar()
