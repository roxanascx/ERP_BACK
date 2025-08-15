```
🛠️ CONFIGURACIÓN CORREGIDA PARA POSTMAN - SUNAT SIRE
================================================================

🔧 PASO 1: CORREGIR URL BASE
────────────────────────────
❌ URL INCORRECTA: https://apisire.sunat.gob.pe
✅ URL CORRECTA: https://api-sire.sunat.gob.pe

🔧 PASO 2: HEADERS CORRECTOS
────────────────────────────
Content-Type: application/json
Accept: application/json
Authorization: Bearer {{token}}

⚠️ IMPORTANTE: Asegúrate de que no hay espacios extra o caracteres especiales

🔧 PASO 3: ENDPOINTS OFICIALES
────────────────────────────
❌ ENDPOINT INEXISTENTE: 
/v1/contribuyente/migeigv/libros/rvie/rce/padron/web/omnibus/2024/12

✅ ENDPOINTS OFICIALES (Manual SUNAT v25):
1. GET /v1/contribuyente/migeigv
2. GET /v1/contribuyente/migeigv/libros  
3. GET /v1/contribuyente/migeigv/libros/rvie/propuesta/web/consultar
4. POST /v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{periodo}/exportapropuesta

🔧 PASO 4: OBTENER TOKEN FRESCO
────────────────────────────
URL: https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/
Method: POST
Headers: Content-Type: application/x-www-form-urlencoded

Body (x-www-form-urlencoded):
grant_type: password
scope: https://api-sire.sunat.gob.pe
client_id: a4169db2-5e94-4916-a2c5-b4e0a5158938
client_secret: oMNnkS1%Lp*7
username: 42634608
password: Rox123

🔧 PASO 5: CONFIGURAR VARIABLES POSTMAN
─────────────────────────────────────
base_url: https://api-sire.sunat.gob.pe
token: [TOKEN_OBTENIDO]

🔧 PASO 6: REQUESTS DE PRUEBA
──────────────────────────────
1. OBTENER TOKEN (PRIMERO):
   POST {{auth_url}}/v1/clientessol/{{client_id}}/oauth2/token/

2. PROBAR ENDPOINTS:
   GET {{base_url}}/v1/contribuyente/migeigv
   GET {{base_url}}/v1/contribuyente/migeigv/libros

🚨 ERRORES COMUNES Y SOLUCIONES:
────────────────────────────────────
❌ "Could not send request" 
   → Verificar URL (api-sire, no apisire)

❌ "Header name must be a valid HTTP token ['Content-Type']"
   → Revisar headers, eliminar caracteres especiales

❌ "401 Unauthorized"
   → Token expirado, obtener uno nuevo

❌ "404 Not Found"  
   → Endpoint incorrecto, usar los oficiales

❌ "500 Internal Server Error"
   → Servidor SUNAT con problemas, reintentar más tarde

🎯 REQUESTS MANUALES PARA POSTMAN:
──────────────────────────────────
Copia y pega estos requests exactos:

┌─ REQUEST 1: Obtener Token ─────────────────────────────────┐
│ Method: POST                                               │
│ URL: https://api-seguridad.sunat.gob.pe/v1/clientessol/a4169db2-5e94-4916-a2c5-b4e0a5158938/oauth2/token/ │
│                                                            │
│ Headers:                                                   │
│ Content-Type: application/x-www-form-urlencoded           │
│ Accept: application/json                                   │
│                                                            │
│ Body (x-www-form-urlencoded):                             │
│ grant_type=password                                        │
│ scope=https://api-sire.sunat.gob.pe                       │
│ client_id=a4169db2-5e94-4916-a2c5-b4e0a5158938           │
│ client_secret=oMNnkS1%25Lp*7                             │
│ username=42634608                                          │
│ password=Rox123                                            │
└────────────────────────────────────────────────────────────┘

┌─ REQUEST 2: Probar Endpoint SIRE ──────────────────────────┐
│ Method: GET                                                │
│ URL: https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv │
│                                                            │
│ Headers:                                                   │
│ Content-Type: application/json                             │
│ Accept: application/json                                   │
│ Authorization: Bearer [TOKEN_DEL_REQUEST_1]                │
└────────────────────────────────────────────────────────────┘

✅ RESULTADO ESPERADO:
- Request 1: Status 200, JSON con access_token
- Request 2: Status 200, datos del contribuyente
```
