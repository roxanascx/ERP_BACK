#!/usr/bin/env python3
"""
Test para verificar que el fix de MongoDB funciona correctamente
"""
import asyncio
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.abspath('.'))

async def test_rvie_service():
    """Probar la creación del servicio RVIE"""
    try:
        print("🧪 [TEST] Probando creación del servicio RVIE...")
        
        from app.modules.sire.routes.rvie_routes import get_rvie_service
        
        # Crear servicio
        service = await get_rvie_service()
        print("✅ [TEST] Servicio RVIE creado exitosamente")
        
        # Verificar database
        print(f"📊 [TEST] Database type: {type(service.database)}")
        print(f"📊 [TEST] Database is not None: {service.database is not None}")
        
        # Probar generación de ticket (simulada)
        print("🎫 [TEST] Probando generación de ticket...")
        
        ticket = await service.generar_ticket(
            ruc="10426346082",
            periodo="202508",
            operacion="descargar-propuesta"
        )
        
        print("✅ [TEST] Ticket generado exitosamente:")
        print(f"   - ID: {ticket['ticket_id']}")
        print(f"   - Status: {ticket['status']}")
        print(f"   - Operación: {ticket['operacion']}")
        
        return True
        
    except Exception as e:
        print(f"❌ [TEST] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rvie_service())
    if success:
        print("\n🎉 [TEST] Todos los tests pasaron correctamente!")
    else:
        print("\n💥 [TEST] Hubo errores en los tests")
        sys.exit(1)
