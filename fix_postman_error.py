#!/usr/bin/env python3
"""
Script CORREGIDO para Postman - Endpoint RVIE SUNAT
Soluciona los problemas identificados
"""

import requests
import json
from datetime import datetime

def get_fresh_token():
    """Obtener un token fresco para asegurar que no esté expirado"""
    
    # Datos de autenticación
    client_id = "a4169db2-5e94-4916-a2c5-b4e0a5158938"
    client_secret = "oMNnkS1%Lp*7"  # Tu client_secret real
    username = "42634608"
    password = "Rox123"  # Tu password SOL
    scope = "https://api-sire.sunat.gob.pe"
    
    # URL correcta para token
    auth_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    
    # Datos para el POST
    data = {
        "grant_type": "password",
        "scope": scope,
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password
    }
    
    # Headers para autenticación
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    print("🔄 Obteniendo token fresco...")
    
    try:
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Token obtenido: {token_data['access_token'][:50]}...")
            return token_data['access_token']
        else:
            print(f"❌ Error obteniendo token: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

def test_endpoint_correcto():
    """
    Probar el endpoint CORREGIDO según la documentación oficial
    """
    
    # Obtener token fresco
    token = get_fresh_token()
    if not token:
        print("❌ No se pudo obtener el token")
        return
    
    print("\n🎯 PROBANDO ENDPOINT RVIE CORREGIDO")
    print("=" * 60)
    
    # URL CORREGIDA (usando la oficial)
    base_url = "https://api-sire.sunat.gob.pe"  # ✅ URL oficial
    
    # Endpoints a probar según manual SUNAT
    endpoints = [
        {
            "name": "Consultar propuestas RVIE",
            "url": f"{base_url}/v1/contribuyente/migeigv/libros/rvie/propuesta/web/consultar"
        },
        {
            "name": "Información básica del contribuyente",
            "url": f"{base_url}/v1/contribuyente/migeigv"
        },
        {
            "name": "Libros electrónicos disponibles",
            "url": f"{base_url}/v1/contribuyente/migeigv/libros"
        }
    ]
    
    # Headers LIMPIOS (sin caracteres especiales)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PostmanRuntime/7.26.8"  # Simular Postman
    }
    
    print("📋 Headers a usar:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"   {key}: Bearer [TOKEN_HIDDEN]")
        else:
            print(f"   {key}: {value}")
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n{i}. 🔍 {endpoint['name']}")
        print("-" * 50)
        print(f"📡 URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], headers=headers, timeout=30)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📦 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            if response.status_code == 200:
                print("✅ ¡ÉXITO!")
                try:
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        data = response.json()
                        print(f"📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    else:
                        print(f"📄 Response (texto): {response.text}")
                except:
                    print(f"📄 Response (raw): {response.text}")
                    
            elif response.status_code == 401:
                print("🔒 ERROR 401: Token inválido - Revisar autenticación")
                print(f"📄 Response: {response.text}")
                
            elif response.status_code == 403:
                print("⛔ ERROR 403: Sin permisos")
                print(f"📄 Response: {response.text}")
                
            elif response.status_code == 404:
                print("❌ ERROR 404: Endpoint no encontrado")
                print(f"📄 Response: {response.text}")
                
            elif response.status_code == 500:
                print("💥 ERROR 500: Error del servidor SUNAT")
                print(f"📄 Response: {response.text}")
                
            else:
                print(f"❓ ERROR {response.status_code}")
                print(f"📄 Response: {response.text}")
                
        except Exception as e:
            print(f"💥 ERROR: {e}")

def configuracion_postman():
    """
    Generar configuración corregida para Postman
    """
    
    print("\n🛠️ CONFIGURACIÓN CORREGIDA PARA POSTMAN")
    print("=" * 60)
    
    print("""
📋 SETTINGS CORRECTOS PARA POSTMAN:

1. 🌐 URL Base:
   https://api-sire.sunat.gob.pe

2. 🔑 Headers (sin errores):
   Content-Type: application/json
   Accept: application/json
   Authorization: Bearer {{token}}

3. 📡 Endpoints a probar:
   GET {{base_url}}/v1/contribuyente/migeigv
   GET {{base_url}}/v1/contribuyente/migeigv/libros
   GET {{base_url}}/v1/contribuyente/migeigv/libros/rvie/propuesta/web/consultar

4. ⚠️ PROBLEMAS IDENTIFICADOS EN TU POSTMAN:
   ❌ URL incorrecta: apisire.sunat.gob.pe
   ✅ URL correcta: api-sire.sunat.gob.pe
   
   ❌ Token posiblemente expirado
   ✅ Usar token fresco (válido por 1 hora)
   
   ❌ Endpoint inexistente: /rce/padron/web/omnibus
   ✅ Usar endpoints oficiales del manual SUNAT

5. 🔧 Variables de Postman:
   base_url: https://api-sire.sunat.gob.pe
   token: [USAR TOKEN FRESCO]
   
6. 💡 TIPS:
   - Siempre usar token fresco (obtener cada hora)
   - Verificar que la URL no tenga typos
   - Los headers deben estar escritos exactamente así
   - Probar primero endpoints básicos (/v1/contribuyente/migeigv)
""")

if __name__ == "__main__":
    # Probar endpoints corregidos
    test_endpoint_correcto()
    
    # Mostrar configuración para Postman
    configuracion_postman()
