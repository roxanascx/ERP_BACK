import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.modules.socios_negocio.routes import get_sire_ruc_service, get_socio_service

async def test_integration():
    try:
        # Simular contexto de FastAPI
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client['erp_db']
        
        print('🔍 [TEST] Probando integración SIRE...')
        
        # Probar inicialización del servicio SIRE
        sire_service = await get_sire_ruc_service(db)
        
        if sire_service:
            print('✅ [TEST] Servicio SIRE inicializado correctamente')
            
            # Probar verificación de disponibilidad
            status = await sire_service.verificar_disponibilidad_api()
            print(f'📊 [TEST] Status SIRE: {status}')
        else:
            print('⚠️ [TEST] Servicio SIRE no disponible, usará fallback')
        
        # Probar inicialización del servicio de socios
        socio_service = await get_socio_service(db, sire_service)
        print('✅ [TEST] Servicio de socios inicializado correctamente')
        
        client.close()
        print('🎉 [TEST] Integración exitosa!')
        
    except Exception as e:
        print(f'❌ [TEST] Error en integración: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_integration())
