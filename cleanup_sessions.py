"""
Script para limpiar sesiones SIRE y probar auto-autenticación
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_and_test():
    """Limpiar sesiones y probar auto-autenticación"""
    try:
        print("🧹 Limpiando sesiones SIRE existentes...")
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        # Limpiar todas las sesiones
        result = await db.sire_sessions.delete_many({})
        print(f"   🗑️ Sesiones eliminadas: {result.deleted_count}")
        
        # Verificar que no hay sesiones
        count = await db.sire_sessions.count_documents({})
        print(f"   📊 Sesiones restantes: {count}")
        
        client.close()
        
        print("\n✅ Limpieza completada")
        print("📝 Ahora puedes probar la auto-autenticación seleccionando una empresa en el frontend")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_and_test())
