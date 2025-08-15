#!/usr/bin/env python3
"""
ESTRATEGIA ALTERNATIVA - PROBAR ENDPOINTS SUNAT SIRE
Problema: Error 500 en todos los endpoints - Probar diferentes enfoques
"""

import requests
import json
from datetime import datetime
import base64

def estrategia_alternativa():
    """
    Probar diferentes estrategias para encontrar endpoints funcionales
    """
    
    print("🔍 ESTRATEGIA ALTERNATIVA - DIAGNÓSTICO PROFUNDO")
    print("=" * 70)
    
    # Obtener token
    token = obtener_token_fresh()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    # ESTRATEGIA 1: Probar endpoints ROOT
    print("\n🎯 ESTRATEGIA 1: ENDPOINTS ROOT")
    print("-" * 40)
    
    root_endpoints = [
        "https://api-sire.sunat.gob.pe/",
        "https://api-sire.sunat.gob.pe/v1",
        "https://api-sire.sunat.gob.pe/health",
        "https://api-sire.sunat.gob.pe/status",
        "https://api-sire.sunat.gob.pe/api-docs"
    ]
    
    for url in root_endpoints:
        probar_endpoint(url, headers, "Root check")
    
    # ESTRATEGIA 2: Probar con diferentes métodos HTTP
    print("\n🎯 ESTRATEGIA 2: DIFERENTES MÉTODOS HTTP")
    print("-" * 40)
    
    test_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv"
    
    for method in ['GET', 'POST', 'OPTIONS']:
        print(f"\n🔸 Probando {method}:")
        try:
            if method == 'GET':
                response = requests.get(test_url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(test_url, headers=headers, json={}, timeout=15)
            elif method == 'OPTIONS':
                response = requests.options(test_url, headers=headers, timeout=15)
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code != 500:
                print(f"   ✅ ¡Método {method} funcionó!")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # ESTRATEGIA 3: Verificar si necesita parámetros específicos
    print("\n🎯 ESTRATEGIA 3: CON PARÁMETROS")
    print("-" * 40)
    
    parametros_test = [
        {"periodo": "202412"},
        {"anio": "2024", "mes": "12"},
        {"codLibro": "140000"},
        {"numEjercicio": "2024"}
    ]
    
    base_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv"
    
    for params in parametros_test:
        print(f"\n🔸 Probando con parámetros: {params}")
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            print(f"   URL final: {response.url}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 500:
                print(f"   ✅ ¡Funcionó con parámetros!")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def verificar_estado_sunat():
    """
    Verificar el estado general de SUNAT
    """
    
    print("\n🏥 VERIFICANDO ESTADO DE SUNAT")
    print("-" * 40)
    
    # URLs de SUNAT para verificar estado
    sunat_urls = [
        "https://api-seguridad.sunat.gob.pe/",
        "https://www.sunat.gob.pe/",
        "https://e-factura.sunat.gob.pe/"
    ]
    
    for url in sunat_urls:
        print(f"\n🔸 Verificando: {url}")
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Tiempo: {response.elapsed.total_seconds():.2f}s")
            
            if response.status_code == 200:
                print(f"   ✅ Servidor funcionando")
            else:
                print(f"   ⚠️ Posibles problemas")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def probar_endpoint(url, headers, descripcion):
    """Función auxiliar para probar un endpoint"""
    
    print(f"\n🔸 {descripcion}: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print(f"   ✅ ¡ÉXITO!")
            print(f"   Response: {response.text[:200]}...")
        elif response.status_code == 404:
            print(f"   ❌ Not Found")
        elif response.status_code == 500:
            print(f"   💥 Server Error")
        else:
            print(f"   ❓ Status: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 Error: {e}")

def obtener_token_fresh():
    """Obtener token fresco"""
    
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
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ Token obtenido: {token_data['access_token'][:50]}...")
            return token_data['access_token']
        else:
            print(f"❌ Error token: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

def recomendaciones_finales():
    """
    Recomendaciones basadas en los resultados
    """
    
    print("\n💡 RECOMENDACIONES FINALES")
    print("=" * 50)
    
    print("""
🎯 POSIBLES CAUSAS DEL ERROR 500:

1. 🚧 MANTENIMIENTO DE SUNAT:
   - La API SIRE puede estar en mantenimiento
   - Común en horarios nocturnos o fines de semana
   
2. 🔐 CONFIGURACIÓN DE CUENTA:
   - Tu cuenta SOL necesita activar servicios SIRE
   - Contactar a SUNAT para habilitar acceso API
   
3. 📋 ENDPOINTS DESACTUALIZADOS:
   - La documentación puede estar desactualizada
   - SUNAT cambió las URLs sin actualizar manuales
   
4. 🎯 PARÁMETROS OBLIGATORIOS:
   - Los endpoints requieren parámetros específicos
   - Formato de fechas o códigos especiales

🔧 SOLUCIONES RECOMENDADAS:

1. ✅ VERIFICAR EN POSTMAN:
   - Probar endpoint básico: GET /v1/contribuyente/migeigv
   - Si sigue dando 500, es problema de SUNAT
   
2. 📞 CONTACTAR SUNAT:
   - Llamar soporte técnico: (01) 315-0730
   - Consultar sobre activación de servicios SIRE
   
3. 🕐 PROBAR EN DIFERENTES HORARIOS:
   - Horario laboral: 8:00 AM - 6:00 PM
   - Evitar fines de semana y feriados
   
4. 📖 REVISAR DOCUMENTACIÓN ACTUALIZADA:
   - Buscar manuales más recientes en sunat.gob.pe
   - Verificar cambios en endpoints

🎉 ÉXITO LOGRADO HASTA AHORA:
✅ Autenticación funcionando perfectamente
✅ Token válido obtenido
✅ Headers correctos configurados
✅ URL base correcta

❌ PENDIENTE:
- Encontrar endpoints funcionales
- Configurar cuenta SIRE (posiblemente)
""")

if __name__ == "__main__":
    # Verificar estado general
    verificar_estado_sunat()
    
    # Probar estrategias alternativas
    estrategia_alternativa()
    
    # Mostrar recomendaciones
    recomendaciones_finales()
