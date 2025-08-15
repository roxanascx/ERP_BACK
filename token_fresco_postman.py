#!/usr/bin/env python3
"""
OBTENER TOKEN FRESCO PARA POSTMAN - SUNAT SIRE
Problema: Token expirado (generado ayer 14/08, hoy es 15/08)
"""

import requests
import json
from datetime import datetime, timedelta
import base64

def obtener_token_fresco_ahora():
    """
    Obtener token fresco para usar INMEDIATAMENTE en Postman
    """
    
    print("🔄 OBTENIENDO TOKEN FRESCO PARA POSTMAN")
    print("=" * 60)
    print(f"⏰ Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Problema identificado: Token expirado (generado ayer)")
    
    # Credenciales correctas
    client_id = "a4169db2-5e94-4916-a2c5-b4e0a5158938"
    client_secret = "Gk1gXDKkk9aCk/YGzNLefg=="
    username = "42634608"  # Tu usuario SOL
    password = "Roxana1406"    # Tu password SOL
    scope = "https://api-sire.sunat.gob.pe"
    
    # URL correcta para token
    auth_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    
    print(f"📡 URL: {auth_url}")
    print(f"👤 Username: {username}")
    print(f"🔑 Client ID: {client_id}")
    
    # Datos para el POST (application/x-www-form-urlencoded)
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
        "Accept": "application/json",
        "User-Agent": "PostmanRuntime/7.26.8"
    }
    
    try:
        print(f"\n🚀 Enviando request de autenticación...")
        
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📦 Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            token_data = response.json()
            
            # Calcular tiempo de expiración
            expires_in = token_data.get('expires_in', 3600)
            expira_en = datetime.now() + timedelta(seconds=expires_in)
            
            print(f"\n✅ ¡TOKEN OBTENIDO EXITOSAMENTE!")
            print("=" * 50)
            print(f"🎫 Access Token: {token_data['access_token']}")
            print(f"🔑 Token Type: {token_data.get('token_type', 'JWT')}")
            print(f"⏰ Expires In: {expires_in} segundos")
            print(f"📅 Expira el: {expira_en.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Guardar para uso
            token_info = {
                "access_token": token_data['access_token'],
                "token_type": token_data.get('token_type', 'JWT'),
                "expires_in": expires_in,
                "expires_at": expira_en.isoformat(),
                "scope": scope,
                "generado": datetime.now().isoformat()
            }
            
            with open("token_fresco_postman.json", "w") as f:
                json.dump(token_info, f, indent=2)
            
            print(f"\n💾 Token guardado en: token_fresco_postman.json")
            
            # Instrucciones para Postman
            print(f"\n📋 PARA USAR EN POSTMAN:")
            print("=" * 40)
            print(f"1. Copia este token:")
            print(f"   {token_data['access_token']}")
            print(f"\n2. En Postman, Authorization header:")
            print(f"   Bearer {token_data['access_token']}")
            print(f"\n3. Válido hasta: {expira_en.strftime('%H:%M:%S')} de hoy")
            
            # Probar el token inmediatamente
            probar_token_inmediatamente(token_data['access_token'])
            
            return token_data['access_token']
            
        else:
            print(f"\n❌ ERROR OBTENIENDO TOKEN:")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Analizar error específico
            if response.status_code == 401:
                print(f"\n🔍 ANÁLISIS DEL ERROR 401:")
                print(f"- Verificar client_id y client_secret")
                print(f"- Verificar username y password SOL")
                print(f"- Verificar que la aplicación esté activa en SUNAT Virtual")
                
            return None
            
    except Exception as e:
        print(f"\n💥 ERROR DE CONEXIÓN: {e}")
        return None

def probar_token_inmediatamente(token):
    """
    Probar el token recién obtenido con un endpoint simple
    """
    
    print(f"\n🧪 PROBANDO TOKEN RECIÉN OBTENIDO")
    print("=" * 40)
    
    # Endpoint básico para probar
    test_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=20)
        
        print(f"📡 URL probada: {test_url}")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ ¡TOKEN VÁLIDO! Funciona correctamente")
            try:
                data = response.json()
                print(f"📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                print(f"📄 Response (texto): {response.text}")
                
        elif response.status_code == 401:
            print(f"❌ Token aún inválido - verificar credenciales")
            
        elif response.status_code == 500:
            print(f"⚠️ Error 500 - problema del servidor SUNAT")
            
        else:
            print(f"❓ Status {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"💥 Error probando: {e}")

def instrucciones_postman():
    """
    Mostrar instrucciones específicas para corregir Postman
    """
    
    print(f"\n📝 INSTRUCCIONES ESPECÍFICAS PARA TU POSTMAN:")
    print("=" * 60)
    print(f"""
🔧 PASO 1: Reemplazar Token Expirado
┌─────────────────────────────────────────────────────────┐
│ Tu token actual (EXPIRADO):                             │
│ eyJraWQiOiJhcGkuc3VuYXQuZ29iLnBlLmtpZDAwMSIsInR5cCI... │
│                                                         │
│ ❌ Generado: 14 agosto 2025, 20:20                     │
│ ❌ Expiró: 14 agosto 2025, 21:20                       │
│ ❌ Hoy es: 15 agosto 2025, 14:07                       │
│ ❌ Estado: EXPIRADO hace ~17 horas                      │
└─────────────────────────────────────────────────────────┘

🔧 PASO 2: URL Correcta (YA LO TIENES BIEN)
✅ https://api-sire.sunat.gob.pe

🔧 PASO 3: Headers Correctos (YA LOS TIENES BIEN)
✅ Content-Type: application/json
✅ Accept: application/json  
✅ Authorization: Bearer [NUEVO_TOKEN]

🔧 PASO 4: Endpoint Recomendado
En lugar de: /v1/contribuyente/migeigv/libros/rvierce/padron/web/omnibus
Prueba: /v1/contribuyente/migeigv

🎯 RESULTADO ESPERADO:
- Status: 200 OK
- Content-Type: application/json
- Response: Datos del contribuyente
""")

if __name__ == "__main__":
    # Obtener token fresco
    token = obtener_token_fresco_ahora()
    
    # Mostrar instrucciones
    instrucciones_postman()
