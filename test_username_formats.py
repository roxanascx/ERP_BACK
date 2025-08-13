import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

async def test_different_formats():
    """Probar diferentes formatos de username"""
    
    # Obtener credenciales de la BD
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.erp_db
    empresa = await db.companies.find_one({'ruc': '10426346082'})
    client.close()
    
    client_id = empresa.get('sire_client_id')
    client_secret = empresa.get('sire_client_secret')
    usuario_sunat = empresa.get('sire_usuario_sunat')
    clave_sol = empresa.get('sire_clave_sol')
    ruc = empresa.get('ruc')
    
    # URL según manual SUNAT
    auth_url = f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    # Diferentes formatos a probar
    username_formats = [
        f"{ruc} {usuario_sunat}",           # 10426346082 42634608
        f"{ruc}{usuario_sunat}",            # 1042634608242634608  
        usuario_sunat,                      # 42634608
        f"{usuario_sunat}",                 # 42634608
        f"MODDATOS"                         # Usuario especial para empresas
    ]
    
    for i, username in enumerate(username_formats, 1):
        print(f"\n=== PRUEBA {i} ===")
        print(f"Username: '{username}'")
        
        auth_data = {
            "grant_type": "password",
            "scope": "https://api-sire.sunat.gob.pe",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": clave_sol
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    url=auth_url,
                    headers=headers,
                    data=auth_data
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ ¡ÉXITO!")
                    token_data = response.json()
                    print(f"Token: {token_data.get('access_token', '')[:50]}...")
                    break
                else:
                    try:
                        error_data = response.json()
                        print(f"❌ Error: {error_data.get('error_description', 'Sin descripción')}")
                    except:
                        print(f"❌ Error text: {response.text}")
                        
        except Exception as e:
            print(f"❌ Excepción: {e}")

if __name__ == "__main__":
    asyncio.run(test_different_formats())
