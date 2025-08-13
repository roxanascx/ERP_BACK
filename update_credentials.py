import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def update_credentials():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.erp_db
    
    # Actualizar las credenciales faltantes
    result = await db.companies.update_one(
        {'ruc': '10426346082'},
        {'$set': {
            'sire_usuario_sunat': '42634608',
            'sire_clave_sol': 'Roxana1406'
        }}
    )
    
    if result.modified_count > 0:
        print('✅ Credenciales SUNAT actualizadas correctamente')
        
        # Verificar que se guardaron
        empresa = await db.companies.find_one({'ruc': '10426346082'})
        print()
        print('=== CREDENCIALES ACTUALIZADAS ===')
        print('Usuario SUNAT:', empresa.get('sire_usuario_sunat'))
        print('Clave SOL:', '*' * len(empresa.get('sire_clave_sol', '')))
        print('Client ID:', empresa.get('sire_client_id'))
        print('Client Secret:', '*' * len(empresa.get('sire_client_secret', '')))
    else:
        print('❌ Error actualizando credenciales')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(update_credentials())
