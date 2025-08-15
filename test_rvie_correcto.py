#!/usr/bin/env python3
"""
Script para probar endpoints RVIE CORRECTOS de SUNAT SIRE
Basado en la documentación oficial adjunta
"""

import requests
import json
from datetime import datetime

def test_endpoint_correcto():
    """
    Probar el endpoint correcto según la documentación oficial
    """
    
    # Tu token válido
    token = "eyJraWQiOiJhcGkuc3VuYXQuZ29iLnBlLmtpZDAwMSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxMDQyNjM0NjA4MiIsImF1ZCI6Ilt7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbGNwZVwiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX0se1wiYXBpXCI6XCJodHRwczpcL1wvYXBpLXNpcmUuc3VuYXQuZ29iLnBlXCIsXCJyZWN1cnNvXCI6W3tcImlkXCI6XCJcL3YxXC9jb250cmlidXllbnRlXC9taWdlaWd2XCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvZ2VtXCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbG1zZ1wiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX1dIiwidXNlcmRhdGEiOnsibnVtUlVDIjoiMTA0MjYzNDYwODIiLCJ0aWNrZXQiOiIxMjI2MjAxMzAwODg1IiwibnJvUmVnaXN0cm8iOiIiLCJhcGVNYXRlcm5vIjoiIiwibG9naW4iOiIxMDQyNjM0NjA4MjQyNjM0NjA4Iiwibm9tYnJlQ29tcGxldG8iOiJDVVRJUEEgTU9MTEVIVUFOQ0EgUk9YQU5BIiwibm9tYnJlcyI6IkNVVElQQSBNT0xMRUhVQU5DQSBST1hBTkEiLCJjb2REZXBlbmQiOiIwMTkzIiwiY29kVE9wZUNvbWVyIjoiIiwiY29kQ2F0ZSI6IiIsIm5pdmVsVU8iOjAsImNvZFVPIjoiIiwiY29ycmVvIjoiIiwidXN1YXJpb1NPTCI6IjQyNjM0NjA4IiwiaWQiOiIiLCJkZXNVTyI6IiIsImRlc0NhdGUiOiIiLCJhcGVQYXRlcm5vIjoiIiwiaWRDZWx1bGFyIjpudWxsLCJtYXAiOnsiaXNDbG9uIjpmYWxzZSwiZGRwRGF0YSI6eyJkZHBfbnVtcnVjIjoiMTA0MjYzNDYwODIiLCJkZHBfbnVtcmVnIjoiMDE5MyIsImRkcF9lc3RhZG8iOiIwMCIsImRkcF9mbGFnMjIiOiIwMCIsImRkcF91YmlnZW8iOiIxMDAxMDEiLCJkZHBfdGFtYW5vIjoiMDMiLCJkZHBfdHBvZW1wIjoiMDIiLCJkZHBfY2lpdSI6IjU1MjA1In0sImlkTWVudSI6IjEyMjYyMDEzMDA4ODUiLCJqbmRpUG9vbCI6InAwMTkzIiwidGlwVXN1YXJpbyI6IjAiLCJ0aXBPcmlnZW4iOiJJVCIsInByaW1lckFjY2VzbyI6ZmFsc2V9fSwibmJmIjoxNzU1MjIwMzgwLCJjbGllbnRJZCI6ImE0MTY5ZGIyLTVlOTQtNDkxNi1hMmM1LWI0ZTBhNTE1ODkzOCIsImlzcyI6Imh0dHBzOlwvXC9hcGktc2VndXJpZGFkLnN1bmF0LmdvYi5wZVwvdjFcL2NsaWVudGVzc29sXC9hNDE2OWRiMi01ZTk0LTQ5MTYtYTJjNS1iNGUwYTUxNTg5MzhcL29hdXRoMlwvdG9rZW5cLyIsImV4cCI6MTc1NTIyMzk4MCwiZ3JhbnRUeXBlIjoicGFzc3dvcmQiLCJpYXQiOjE3NTUyMjAzODB9.K6WngwSE19ZZAOr-WFiwAJASE7JsIffpr_ZYlyIr_jyiQJ6bAfpSBGIiYFn_LHe4GMnnlo0RN6BHgwES4gQCmVuFc06dOK2TFD-9Op1CBLxYqhMabhhBN0QC8j1-xAVh-3HpwgwmpyVkX-Px8BZjHmIy3njjBrh3NFqN5XT3ENtNxOzXpthxm0rb-5H5UNyv1GWyun6F1axH1J1JMRs_MYt-iRAZLBtLL3V1LuSD2do30WW26AtD4XI2Hs9f7fhm_S3aj_r368G-cc3LsIWCx91RvbYjFqF2B-W9VtZvbNaYRsp8YE1WWWveGKaCWLuaUDmaGMSVuv45v2wGhgeIQw"
    
    # Según la imagen de Postman que enviaste, el endpoint parece ser:
    # GET https://apisire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/{anio}/{mes}
    
    # Pero según el manual OFICIAL de SUNAT, los endpoints correctos son diferentes
    
    # Lista de endpoints OFICIALES según el manual SUNAT v25
    endpoints_oficiales = [
        {
            "name": "📋 Consultar años y meses disponibles (según manual)",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie/propuesta/web/consultar"
        },
        {
            "name": "📋 Descargar propuesta RVIE (según manual)",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/202412/exportapropuesta"
        },
        {
            "name": "📋 Endpoint básico MIGEIGV",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv"
        },
        {
            "name": "📋 Endpoint libros",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros"
        },
        {
            "name": "📋 Endpoint RVIE base",
            "url": "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie"
        }
    ]
    
    # Headers correctos
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'SIRE-Client/1.0'
    }
    
    print("🔍 PROBANDO ENDPOINTS OFICIALES SUNAT SIRE")
    print("=" * 70)
    print(f"🔑 Token: {token[:50]}...")
    
    for i, endpoint in enumerate(endpoints_oficiales, 1):
        print(f"\n{i}. {endpoint['name']}")
        print("-" * 50)
        print(f"📡 URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], headers=headers, timeout=20)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📏 Content-Length: {len(response.content)} bytes")
            print(f"📦 Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                print("✅ ¡ÉXITO! - Endpoint válido")
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        data = response.json()
                        print(f"📄 Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
                    else:
                        print(f"📄 Response (texto): {response.text[:300]}...")
                except Exception as e:
                    print(f"📄 Response (raw): {response.text[:300]}...")
                    
            elif response.status_code == 401:
                print("🔒 ERROR 401: Token inválido o expirado")
                
            elif response.status_code == 403:
                print("⛔ ERROR 403: Sin permisos para este recurso")
                
            elif response.status_code == 404:
                print("❌ ERROR 404: Endpoint no encontrado")
                
            elif response.status_code == 500:
                print("💥 ERROR 500: Error interno del servidor")
                print(f"📄 Response: {response.text[:200]}...")
                
            else:
                print(f"❓ ERROR {response.status_code}: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError as e:
            print(f"🌐 ERROR DE CONEXIÓN: {e}")
            
        except requests.exceptions.Timeout:
            print(f"⏰ ERROR DE TIMEOUT")
            
        except Exception as e:
            print(f"💥 ERROR INESPERADO: {e}")

def test_postman_endpoint():
    """
    Probar el endpoint específico que estás usando en Postman
    """
    
    token = "eyJraWQiOiJhcGkuc3VuYXQuZ29iLnBlLmtpZDAwMSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIxMDQyNjM0NjA4MiIsImF1ZCI6Ilt7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbGNwZVwiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX0se1wiYXBpXCI6XCJodHRwczpcL1wvYXBpLXNpcmUuc3VuYXQuZ29iLnBlXCIsXCJyZWN1cnNvXCI6W3tcImlkXCI6XCJcL3YxXC9jb250cmlidXllbnRlXC9taWdlaWd2XCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn1dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvZ2VtXCIsXCJpbmRpY2Fkb3JcIjpcIjFcIixcImd0XCI6XCIwMDEwMDBcIn9dfSx7XCJhcGlcIjpcImh0dHBzOlwvXC9hcGktY3BlLnN1bmF0LmdvYi5wZVwiLFwicmVjdXJzb1wiOlt7XCJpZFwiOlwiXC92MVwvY29udHJpYnV5ZW50ZVwvY29udHJvbG1zZ1wiLFwiaW5kaWNhZG9yXCI6XCIxXCIsXCJndFwiOlwiMDAxMDAwXCJ9XX1dIiwidXNlcmRhdGEiOnsibnVtUlVDIjoiMTA0MjYzNDYwODIiLCJ0aWNrZXQiOiIxMjI2MjAxMzAwODg1IiwibnJvUmVnaXN0cm8iOiIiLCJhcGVNYXRlcm5vIjoiIiwibG9naW4iOiIxMDQyNjM0NjA4MjQyNjM0NjA4Iiwibm9tYnJlQ29tcGxldG8iOiJDVVRJUEEgTU9MTEVIVUFOQ0EgUk9YQU5BIiwibm9tYnJlcyI6IkNVVElQQSBNT0xMRUhVQU5DQSBST1hBTkEiLCJjb2REZXBlbmQiOiIwMTkzIiwiY29kVE9wZUNvbWVyIjoiIiwiY29kQ2F0ZSI6IiIsIm5pdmVsVU8iOjAsImNvZFVPIjoiIiwiY29ycmVvIjoiIiwidXN1YXJpb1NPTCI6IjQyNjM0NjA4IiwiaWQiOiIiLCJkZXNVTyI6IiIsImRlc0NhdGUiOiIiLCJhcGVQYXRlcm5vIjoiIiwiaWRDZWx1bGFyIjpudWxsLCJtYXAiOnsiaXNDbG9uIjpmYWxzZSwiZGRwRGF0YSI6eyJkZHBfbnVtcnVjIjoiMTA0MjYzNDYwODIiLCJkZHBfbnVtcmVnIjoiMDE5MyIsImRkcF9lc3RhZG8iOiIwMCIsImRkcF9mbGFnMjIiOiIwMCIsImRkcF91YmlnZW8iOiIxMDAxMDEiLCJkZHBfdGFtYW5vIjoiMDMiLCJkZHBfdHBvZW1wIjoiMDIiLCJkZHBfY2lpdSI6IjU1MjA1In0sImlkTWVudSI6IjEyMjYyMDEzMDA4ODUiLCJqbmRpUG9vbCI6InAwMTkzIiwidGlwVXN1YXJpbyI6IjAiLCJ0aXBPcmlnZW4iOiJJVCIsInByaW1lckFjY2VzbyI6ZmFsc2V9fSwibmJmIjoxNzU1MjIwMzgwLCJjbGllbnRJZCI6ImE0MTY5ZGIyLTVlOTQtNDkxNi1hMmM1LWI0ZTBhNTE1ODkzOCIsImlzcyI6Imh0dHBzOlwvXC9hcGktc2VndXJpZGFkLnN1bmF0LmdvYi5wZVwvdjFcL2NsaWVudGVzc29sXC9hNDE2OWRiMi01ZTk0LTQ5MTYtYTJjNS1iNGUwYTUxNTg5MzhcL29hdXRoMlwvdG9rZW5cLyIsImV4cCI6MTc1NTIyMzk4MCwiZ3JhbnRUeXBlIjoicGFzc3dvcmQiLCJpYXQiOjE3NTUyMjAzODB9.K6WngwSE19ZZAOr-WFiwAJASE7JsIffpr_ZYlyIr_jyiQJ6bAfpSBGIiYFn_LHe4GMnnlo0RN6BHgwES4gQCmVuFc06dOK2TFD-9Op1CBLxYqhMabhhBN0QC8j1-xAVh-3HpwgwmpyVkX-Px8BZjHmIy3njjBrh3NFqN5XT3ENtNxOzXpthxm0rb-5H5UNyv1GWyun6F1axH1J1JMRs_MYt-iRAZLBtLL3V1LuSD2do30WW26AtD4XI2Hs9f7fhm_S3aj_r368G-cc3LsIWCx91RvbYjFqF2B-W9VtZvbNaYRsp8YE1WWWveGKaCWLuaUDmaGMSVuv45v2wGhgeIQw"
    
    # El endpoint exacto de tu Postman
    url = "https://apisire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/2024/12"
    
    print("\n🎯 PROBANDO ENDPOINT ESPECÍFICO DE POSTMAN")
    print("=" * 60)
    print(f"📡 URL: {url}")
    
    # Reproducir exactamente los headers de Postman
    headers = {
        'Content-Type': 'application/json',  # Aquí puede estar el problema
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    # Analizar el problema del header
    print("\n🔍 ANÁLISIS DE HEADERS:")
    print("----------------------------------------")
    for key, value in headers.items():
        print(f"✓ {key}: {value if key != 'Authorization' else 'Bearer [TOKEN]'}")
    
    # Verificar si hay caracteres especiales en los headers
    for key, value in headers.items():
        if any(ord(char) > 127 for char in key):
            print(f"⚠️ PROBLEMA: Header '{key}' contiene caracteres no ASCII")
        if any(ord(char) > 127 for char in value):
            print(f"⚠️ PROBLEMA: Valor del header '{key}' contiene caracteres no ASCII")
    
    try:
        print(f"\n🚀 Enviando request GET a SUNAT...")
        response = requests.get(url, headers=headers, timeout=20)
        
        print(f"\n📊 RESULTADO:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text[:500]}...")
        
    except Exception as e:
        print(f"💥 ERROR: {e}")

if __name__ == "__main__":
    # Primero probar endpoints oficiales
    test_endpoint_correcto()
    
    # Luego probar el específico de Postman
    test_postman_endpoint()
