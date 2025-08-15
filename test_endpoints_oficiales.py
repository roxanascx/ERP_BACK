#!/usr/bin/env python3
"""
PROBAR ENDPOINTS CORRECTOS SEGÚN DOCUMENTACIÓN SUNAT
Basado en las evidencias de la documentación oficial
"""

import requests
import json
from datetime import datetime

def probar_endpoints_oficiales():
    """
    Probar los endpoints exactos según la documentación oficial adjunta
    """
    
    print("🔍 PROBANDO ENDPOINTS OFICIALES SEGÚN DOCUMENTACIÓN")
    print("=" * 70)
    
    # Usar tu token fresco más reciente (obtenerlo primero)
    token = obtener_token_actual()
    if not token:
        print("❌ No se pudo obtener token")
        return
    
    # Headers correctos
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "PostmanRuntime/7.26.8"
    }
    
    # ENDPOINTS OFICIALES según la documentación adjunta
    endpoints_oficiales = [
        {
            "name": "📊 Consultar años y meses RVIE",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/padron/web/omissos/140000/8/periodos",
            "description": "Según doc: 5.2 Servicio Web Api consultar año y mes"
        },
        {
            "name": "📊 Endpoint básico MIGEIGV",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv",
            "description": "Endpoint raíz del contribuyente"
        },
        {
            "name": "📊 Libros disponibles",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros",
            "description": "Consultar libros electrónicos disponibles"
        },
        {
            "name": "📊 RVIE base",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie",
            "description": "Base RVIE (Registro de Ventas e Ingresos Electrónico)"
        },
        {
            "name": "📊 RVIERCE específico",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce",
            "description": "RVIERCE según documentación"
        }
    ]
    
    print(f"🔑 Token: {token[:50]}...")
    print(f"⏰ Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for i, endpoint in enumerate(endpoints_oficiales, 1):
        print(f"\n{i}. {endpoint['name']}")
        print(f"   {endpoint['description']}")
        print("-" * 50)
        print(f"📡 URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], headers=headers, timeout=30)
            
            print(f"📊 Status: {response.status_code}")
            print(f"⏱️ Time: {response.elapsed.total_seconds():.2f}s")
            print(f"📦 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"📏 Size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print("✅ ¡ÉXITO! - Endpoint válido")
                try:
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        data = response.json()
                        print(f"📄 Response JSON:")
                        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                        if len(json.dumps(data)) > 1000:
                            print("... [truncated]")
                    else:
                        print(f"📄 Response: {response.text[:500]}")
                        if len(response.text) > 500:
                            print("... [truncated]")
                except Exception as e:
                    print(f"📄 Response (raw): {response.text[:300]}")
                    
            elif response.status_code == 401:
                print("🔒 ERROR 401: Token inválido o expirado")
                
            elif response.status_code == 403:
                print("⛔ ERROR 403: Sin permisos para este recurso")
                
            elif response.status_code == 404:
                print("❌ ERROR 404: Endpoint no encontrado")
                
            elif response.status_code == 500:
                print("💥 ERROR 500: Error interno del servidor")
                print("   Posibles causas:")
                print("   - Endpoint no implementado")
                print("   - Parámetros faltantes")
                print("   - Servidor SUNAT con problemas")
                
            else:
                print(f"❓ ERROR {response.status_code}: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("⏰ ERROR: Timeout - SUNAT tardó mucho en responder")
            
        except requests.exceptions.ConnectionError as e:
            print(f"🌐 ERROR: Conexión fallida - {e}")
            
        except Exception as e:
            print(f"💥 ERROR: {e}")

def obtener_token_actual():
    """Obtener token fresco usando las credenciales correctas"""
    
    # Credenciales actualizadas
    client_id = "a4169db2-5e94-4916-a2c5-b4e0a5158938"
    client_secret = "Gk1gXDKkk9aCk/YGzNLefg=="
    username = "42634608"
    password = "Roxana1406"
    scope = "https://api-sire.sunat.gob.pe"
    
    auth_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    
    data = {
        "grant_type": "password",
        "scope": scope,
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    try:
        print("🔄 Obteniendo token fresco...")
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Token obtenido exitosamente")
            return token_data['access_token']
        else:
            print(f"❌ Error obteniendo token: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

def configuracion_postman_correcta():
    """
    Mostrar la configuración exacta para Postman
    """
    
    print("\n🛠️ CONFIGURACIÓN EXACTA PARA POSTMAN")
    print("=" * 60)
    
    print("""
📋 REQUESTS CORRECTOS PARA POSTMAN:

1. 🔑 OBTENER TOKEN (HACER PRIMERO):
   ┌─────────────────────────────────────────────────────────┐
   │ Method: POST                                            │
   │ URL: https://api-seguridad.sunat.gob.pe/v1/clientessol/a4169db2-5e94-4916-a2c5-b4e0a5158938/oauth2/token/ │
   │                                                         │
   │ Headers:                                                │
   │ Content-Type: application/x-www-form-urlencoded        │
   │ Accept: application/json                                │
   │                                                         │
   │ Body (x-www-form-urlencoded):                          │
   │ grant_type=password                                     │
   │ scope=https://api-sire.sunat.gob.pe                    │
   │ client_id=a4169db2-5e94-4916-a2c5-b4e0a5158938        │
   │ client_secret=Gk1gXDKkk9aCk/YGzNLefg==                │
   │ username=42634608                                       │
   │ password=Roxana1406                                     │
   └─────────────────────────────────────────────────────────┘

2. 📊 PROBAR ENDPOINTS (USAR TOKEN DEL PASO 1):
   ┌─────────────────────────────────────────────────────────┐
   │ Method: GET                                             │
   │ URL: https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv │
   │                                                         │
   │ Headers:                                                │
   │ Content-Type: application/json                          │
   │ Accept: application/json                                │
   │ Authorization: Bearer [TOKEN_DEL_PASO_1]                │
   └─────────────────────────────────────────────────────────┘

3. 📋 ENDPOINT ESPECÍFICO SEGÚN DOCUMENTACIÓN:
   ┌─────────────────────────────────────────────────────────┐
   │ Method: GET                                             │
   │ URL: https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/padron/web/omissos/140000/8/periodos │
   │                                                         │
   │ Headers: (igual que arriba)                             │
   └─────────────────────────────────────────────────────────┘

⚠️ IMPORTANTE:
- El token expira en 1 hora
- Siempre obtener token fresco antes de probar
- Usar endpoints exactos de la documentación oficial
""")

if __name__ == "__main__":
    # Probar endpoints oficiales
    probar_endpoints_oficiales()
    
    # Mostrar configuración para Postman
    configuracion_postman_correcta()
