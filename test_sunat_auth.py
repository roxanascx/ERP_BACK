import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

async def test_sunat_auth():
    """Probar autenticación directa con SUNAT usando el formato correcto"""
    
    # Obtener credenciales de la BD
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.erp_db
    empresa = await db.companies.find_one({'ruc': '10426346082'})
    client.close()
    
    if not empresa:
        print("❌ Empresa no encontrada")
        return
    
    # Extraer credenciales
    client_id = empresa.get('sire_client_id')
    client_secret = empresa.get('sire_client_secret')
    usuario_sunat = empresa.get('sire_usuario_sunat')
    clave_sol = empresa.get('sire_clave_sol')
    ruc = empresa.get('ruc')
    
    print("=== PROBANDO AUTENTICACIÓN SUNAT ===")
    print(f"RUC: {ruc}")
    print(f"Usuario: {usuario_sunat}")
    print(f"Client ID: {client_id}")
    print()
    
    # Preparar datos según manual SUNAT
    auth_data = {
        "grant_type": "password",
        "scope": "https://api-sire.sunat.gob.pe",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": f"{ruc} {usuario_sunat}",
        "password": clave_sol
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    # URL según manual SUNAT
    auth_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    
    print(f"🌐 URL: {auth_url}")
    print("📤 Headers:", headers)
    print("📤 Data:", {k: "***" if k in ['client_secret', 'password'] else v for k, v in auth_data.items()})
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            print("🔄 Enviando request...")
            response = await http_client.post(
                url=auth_url,
                headers=headers,
                data=auth_data  # Usar data para form-urlencoded
            )
            
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                token_data = response.json()
                print("✅ AUTENTICACIÓN EXITOSA!")
                print(f"🎟️ Token: {token_data.get('access_token', '')[:50]}...")
                print(f"⏰ Expires in: {token_data.get('expires_in')} segundos")
                print(f"🔑 Token type: {token_data.get('token_type')}")
            else:
                print("❌ ERROR EN AUTENTICACIÓN")
                try:
                    error_data = response.json()
                    print(f"💀 Error: {error_data}")
                except:
                    print(f"💀 Error text: {response.text}")
                    
    except Exception as e:
        print(f"❌ Excepción: {e}")

if __name__ == "__main__":
    asyncio.run(test_sunat_auth())
