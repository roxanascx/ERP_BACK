import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_credentials_detailed():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.erp_db
    
    empresa = await db.companies.find_one({'ruc': '10426346082'})
    
    if empresa:
        print('=== CREDENCIALES DETALLADAS ===')
        print(f'RUC: "{empresa.get("ruc")}"')
        client_id = empresa.get('sire_client_id', '')
        client_secret = empresa.get('sire_client_secret', '')
        usuario_sunat = empresa.get('sire_usuario_sunat', '')
        clave_sol = empresa.get('sire_clave_sol', '')
        
        print(f'Client ID: "{client_id}"')
        print(f'Client Secret: "{client_secret[:10]}..."')
        print(f'Usuario SUNAT: "{usuario_sunat}"')
        print(f'Clave SOL: "{clave_sol}"')
        
        print()
        print('=== FORMATO ESPERADO POR SUNAT ===')
        print('Username debería ser: "[RUC] [USUARIO_SUNAT]"')
        print(f'Username generado: "{empresa.get("ruc")} {usuario_sunat}"')
        
        # Verificar si hay espacios extra o caracteres especiales
        print()
        print('=== VERIFICACIÓN DE CARACTERES ===')
        print(f'RUC length: {len(empresa.get("ruc", ""))}')
        print(f'Usuario length: {len(usuario_sunat)}')
        print(f'RUC repr: {repr(empresa.get("ruc", ""))}')
        print(f'Usuario repr: {repr(usuario_sunat)}')
        
        # Simular el request que se envía a SUNAT
        print()
        print('=== REQUEST A SUNAT ===')
        auth_data = {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": f"{empresa.get('ruc')} {usuario_sunat}",
            "password": clave_sol,
            "scope": "sire"
        }
        
        for key, value in auth_data.items():
            if key == 'client_secret':
                print(f'{key}: "{value[:10]}..."')
            elif key == 'password':
                print(f'{key}: "{value}"')
            else:
                print(f'{key}: "{value}"')
        
    client.close()

if __name__ == "__main__":
    asyncio.run(check_credentials_detailed())
