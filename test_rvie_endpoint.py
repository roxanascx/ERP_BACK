#!/usr/bin/env python3
"""
Script para probar endpoint RVIE de SUNAT SIRE
Basado en el Manual SUNAT v25 - Servicio Web Api consultar año y mes
"""

import requests
import json
from datetime import datetime

def test_rvie_consultar_anio_mes():
    """
    Probar el endpoint de consulta año y mes de RVIE
    Según Manual SUNAT v25 página 24
    """
    
    # Tu token válido
    token = "eyJraWQiOiJhcGkuc3VuYXQuZ29iLnBlLmtpZDAwMSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxMDQyNjM0NjA4MiIsImF1ZCI6Ilt7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbGNwZVwiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX0se1wiYXBpXCI6XCJodHRwczpcL1wvYXBpLXNpcmUuc3VuYXQuZ29iLnBlXCIsXCJyZWN1cnNvXCI6W3tcImlkXCI6XCJcL3YxXC9jb250cmlidXllbnRlXC9taWdlaWd2XCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvZ2VtXCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbG1zZ1wiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX1dIiwidXNlcmRhdGEiOnsibnVtUlVDIjoiMTA0MjYzNDYwODIiLCJ0aWNrZXQiOiIxMjI2MjAxMzAwODg1IiwibnJvUmVnaXN0cm8iOiIiLCJhcGVNYXRlcm5vIjoiIiwibG9naW4iOiIxMDQyNjM0NjA4MjQyNjM0NjA4Iiwibm9tYnJlQ29tcGxldG8iOiJDVVRJUEEgTU9MTEVIVUFOQ0EgUk9YQU5BIiwibm9tYnJlcyI6IkNVVElQQSBNT0xMRUhVQU5DQSBST1hBTkEiLCJjb2REZXBlbmQiOiIwMTkzIiwiY29kVE9wZUNvbWVyIjoiIiwiY29kQ2F0ZSI6IiIsIm5pdmVsVU8iOjAsImNvZFVPIjoiIiwiY29ycmVvIjoiIiwidXN1YXJpb1NPTCI6IjQyNjM0NjA4IiwiaWQiOiIiLCJkZXNVTyI6IiIsImRlc0NhdGUiOiIiLCJhcGVQYXRlcm5vIjoiIiwiaWRDZWx1bGFyIjpudWxsLCJtYXAiOnsiaXNDbG9uIjpmYWxzZSwiZGRwRGF0YSI6eyJkZHBfbnVtcnVjIjoiMTA0MjYzNDYwODIiLCJkZHBfbnVtcmVnIjoiMDE5MyIsImRkcF9lc3RhZG8iOiIwMCIsImRkcF9mbGFnMjIiOiIwMCIsImRkcF91YmlnZW8iOiIxMDAxMDEiLCJkZHBfdGFtYW5vIjoiMDMiLCJkZHBfdHBvZW1wIjoiMDIiLCJkZHBfY2lpdSI6IjU1MjA1In0sImlkTWVudSI6IjEyMjYyMDEzMDA4ODUiLCJqbmRpUG9vbCI6InAwMTkzIiwidGlwVXN1YXJpbyI6IjAiLCJ0aXBPcmlnZW4iOiJJVCIsInByaW1lckFjY2VzbyI6ZmFsc2V9fSwibmJmIjoxNzU1MjIwMzgwLCJjbGllbnRJZCI6ImE0MTY5ZGIyLTVlOTQtNDkxNi1hMmM1LWI0ZTBhNTE1ODkzOCIsImlzcyI6Imh0dHBzOlwvXC9hcGktc2VndXJpZGFkLnN1bmF0LmdvYi5wZVwvdjFcL2NsaWVudGVzc29sXC9hNDE2OWRiMi01ZTk0LTQ5MTYtYTJjNS1iNGUwYTUxNTg5MzhcL29hdXRoMlwvdG9rZW5cLyIsImV4cCI6MTc1NTIyMzk4MCwiZ3JhbnRUeXBlIjoicGFzc3dvcmQiLCJpYXQiOjE3NTUyMjAzODB9.K6WngwSE19ZZAOr-WFiwAJASE7JsIffpr_ZYlyIr_jyiQJ6bAfpSBGIiYFn_LHe4GMnnlo0RN6BHgwES4gQCmVuFc06dOK2TFD-9Op1CBLxYqhMabhhBN0QC8j1-xAVh-3HpwgwmpyVkX-Px8BZjHmIy3njjBrh3NFqN5XT3ENtNxOzXpthxm0rb-5H5UNyv1GWyun6F1axH1J1JMRs_MYt-iRAZLBtLL3V1LuSD2do30WW26AtD4XI2Hs9f7fhm_S3aj_r368G-cc3LsIWCx91RvbYjFqF2B-W9VtZvbNaYRsp8YE1WWWveGKaCWLuaUDmaGMSVuv45v2wGhgeIQw"
    
    # Endpoint según manual SUNAT (página 24)
    # GET /v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/{anio}/{mes}
    base_url = "https://apisire.sunat.gob.pe"
    endpoint = "/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus"
    
    # Parámetros de prueba
    anio = "2024"  # Año de consulta
    mes = "12"     # Mes de consulta
    
    # URL completa
    url = f"{base_url}{endpoint}/{anio}/{mes}"
    
    print("🔍 PROBANDO ENDPOINT RVIE - CONSULTAR AÑO Y MES")
    print("=" * 60)
    print(f"📡 URL: {url}")
    print(f"📅 Período: {anio}-{mes}")
    print(f"🔑 Token: {token[:50]}...")
    
    # Headers correctos según manual SUNAT
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'SIRE-Client/1.0'
    }
    
    print("\n📋 Headers:")
    for key, value in headers.items():
        if key == 'Authorization':
            print(f"   {key}: Bearer {value[7:50]}...")
        else:
            print(f"   {key}: {value}")
    
    try:
        print("\n🚀 Enviando request...")
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"\n📊 RESPUESTA:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"   Content-Length: {response.headers.get('content-length', 'N/A')}")
        
        # Mostrar headers de respuesta relevantes
        print(f"\n📝 Headers de Respuesta:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length', 'date', 'server']:
                print(f"   {key}: {value}")
        
        if response.status_code == 200:
            print(f"\n✅ ¡ÉXITO! Response:")
            try:
                data = response.json()
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print(f"   Contenido (texto): {response.text[:500]}...")
        
        elif response.status_code == 401:
            print(f"\n🔒 ERROR DE AUTENTICACIÓN:")
            print(f"   El token puede estar expirado o ser inválido")
            print(f"   Response: {response.text}")
            
        elif response.status_code == 403:
            print(f"\n⛔ ERROR DE PERMISOS:")
            print(f"   No tienes permisos para este recurso")
            print(f"   Response: {response.text}")
            
        elif response.status_code == 404:
            print(f"\n❌ ENDPOINT NO ENCONTRADO:")
            print(f"   Verifica la URL del endpoint")
            print(f"   Response: {response.text}")
            
        else:
            print(f"\n❌ ERROR HTTP {response.status_code}:")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n🌐 ERROR DE CONEXIÓN:")
        print(f"   No se pudo conectar al servidor: {e}")
        
    except requests.exceptions.Timeout as e:
        print(f"\n⏰ ERROR DE TIMEOUT:")
        print(f"   La request tardó más de 30 segundos: {e}")
        
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO:")
        print(f"   {type(e).__name__}: {e}")

def test_multiple_endpoints():
    """Probar múltiples endpoints RVIE para encontrar el correcto"""
    
    token = "eyJraWQiOiJhcGkuc3VuYXQuZ29iLnBlLmtpZDAwMSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxMDQyNjM0NjA4MiIsImF1ZCI6Ilt7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbGNwZVwiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX0se1wiYXBpXCI6XCJodHRwczpcL1wvYXBpLXNpcmUuc3VuYXQuZ29iLnBlXCIsXCJyZWN1cnNvXCI6W3tcImlkXCI6XCJcL3YxXC9jb250cmlidXllbnRlXC9taWdlaWd2XCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvZ2VtXCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbG1zZ1wiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX1dIiwidXNlcmRhdGEiOnsibnVtUlVDIjoiMTA0MjYzNDYwODIiLCJ0aWNrZXQiOiIxMjI2MjAxMzAwODg1IiwibnJvUmVnaXN0cm8iOiIiLCJhcGVNYXRlcm5vIjoiIiwibG9naW4iOiIxMDQyNjM0NjA4MjQyNjM0NjA4Iiwibm9tYnJlQ29tcGxldG8iOiJDVVRJUEEgTU9MTEVIVUFOQ0EgUk9YQU5BIiwibm9tYnJlcyI6IkNVVElQQSBNT0xMRUhVQU5DQSBST1hBTkEiLCJjb2REZXBlbmQiOiIwMTkzIiwiY29kVE9wZUNvbWVyIjoiIiwiY29kQ2F0ZSI6IiIsIm5pdmVsVU8iOjAsImNvZFVPIjoiIiwiY29ycmVvIjoiIiwidXN1YXJpb1NPTCI6IjQyNjM0NjA4IiwiaWQiOiIiLCJkZXNVTyI6IiIsImRlc0NhdGUiOiIiLCJhcGVQYXRlcm5vIjoiIiwiaWRDZWx1bGFyIjpudWxsLCJtYXAiOnsiaXNDbG9uIjpmYWxzZSwiZGRwRGF0YSI6eyJkZHBfbnVtcnVjIjoiMTA0MjYzNDYwODIiLCJkZHBfbnVtcmVnIjoiMDE5MyIsImRkcF9lc3RhZG8iOiIwMCIsImRkcF9mbGFnMjIiOiIwMCIsImRkcF91YmlnZW8iOiIxMDAxMDEiLCJkZHBfdGFtYW5vIjoiMDMiLCJkZHBfdHBvZW1wIjoiMDIiLCJkZHBfY2lpdSI6IjU1MjA1In0sImlkTWVudSI6IjEyMjYyMDEzMDA4ODUiLCJqbmRpUG9vbCI6InAwMTkzIiwidGlwVXN1YXJpbyI6IjAiLCJ0aXBPcmlnZW4iOiJJVCIsInByaW1lckFjY2VzbyI6ZmFsc2V9fSwibmJmIjoxNzU1MjIwMzgwLCJjbGllbnRJZCI6ImE0MTY5ZGIyLTVlOTQtNDkxNi1hMmM1LWI0ZTBhNTE1ODkzOCIsImlzcyI6Imh0dHBzOlwvXC9hcGktc2VndXJpZGFkLnN1bmF0LmdvYi5wZVwvdjFcL2NsaWVudGVzc29sXC9hNDE2OWRiMi01ZTk0LTQ5MTYtYTJjNS1iNGUwYTUxNTg5MzhcL29hdXRoMlwvdG9rZW5cLyIsImV4cCI6MTc1NTIyMzk4MCwiZ3JhbnRUeXBlIjoicGFzc3dvcmQiLCJpYXQiOjE3NTUyMjAzODB9.K6WngwSE19ZZAOr-WFiwAJASE7JsIffpr_ZYlyIr_jyiQJ6bAfpSBGIiYFn_LHe4GMnnlo0RN6BHgwES4gQCmVuFc06dOK2TFD-9Op1CBLxYqhMabhhBN0QC8j1-xAVh-3HpwgwmpyVkX-Px8BZjHmIy3njjBrh3NFqN5XT3ENtNxOzXpthxm0rb-5H5UNyv1GWyun6F1axH1J1JMRs_MYt-iRAZLBtLL3V1LuSD2do30WW26AtD4XI2Hs9f7fhm_S3aj_r368G-cc3LsIWCx91RvbYjFqF2B-W9VtZvbNaYRsp8YE1WWWveGKaCWLuaUDmaGMSVuv45v2wGhgeIQw"
    
    # URLs y endpoints a probar según manual SUNAT
    test_cases = [
        {
            "name": "API SIRE Principal",
            "base_url": "https://api-sire.sunat.gob.pe",
            "endpoint": "/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/2024/12"
        },
        {
            "name": "API SIRE Alternativo",
            "base_url": "https://apisire.sunat.gob.pe", 
            "endpoint": "/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/2024/12"
        },
        {
            "name": "Endpoint documentación",
            "base_url": "https://api-sire.sunat.gob.pe",
            "endpoint": "/v1/contribuyente/migeigv/libros/rvierce/padron/web/omnibus/2024/12"
        }
    ]
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("🧪 PROBANDO MÚLTIPLES ENDPOINTS RVIE")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        url = test_case['base_url'] + test_case['endpoint']
        print(f"📡 URL: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ ¡ÉXITO!")
                try:
                    data = response.json()
                    print(f"📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}...")
                except:
                    print(f"📄 Response (texto): {response.text[:200]}...")
            else:
                print(f"❌ Error: {response.text[:200]}...")
                
        except Exception as e:
            print(f"💥 Excepción: {e}")
    
if __name__ == "__main__":
    print("🚀 DIAGNÓSTICO DE ENDPOINTS RVIE SUNAT")
    print("=" * 60)
    
    # Probar endpoint principal
    test_rvie_consultar_anio_mes()
    
    print("\n" + "=" * 60)
    
    # Probar múltiples variantes
    test_multiple_endpoints()
