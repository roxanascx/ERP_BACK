"""
Script de diagnóstico para verificar sesiones SIRE en MongoDB
"""

import asyncio
import os
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database


async def debug_sire_sessions():
    """Verificar estado de sesiones SIRE en MongoDB"""
    try:
        print("🔍 Iniciando diagnóstico de sesiones SIRE...")
        
        # Obtener base de datos
        db = get_database()
        
        if db is None:
            print("❌ Error: No se pudo conectar a la base de datos")
            return
        
        print("✅ Conectado a MongoDB")
        
        # Verificar colección sire_sessions
        collection = db.sire_sessions
        
        # Contar total de documentos
        total_count = await collection.count_documents({})
        print(f"📊 Total de sesiones en BD: {total_count}")
        
        # Contar sesiones activas
        active_count = await collection.count_documents({"is_active": True})
        print(f"🟢 Sesiones activas: {active_count}")
        
        # Contar sesiones no expiradas
        now = datetime.utcnow()
        valid_count = await collection.count_documents({
            "expires_at": {"$gt": now},
            "is_active": True
        })
        print(f"⏰ Sesiones válidas (no expiradas): {valid_count}")
        
        # Mostrar últimas 5 sesiones
        print("\n📋 Últimas 5 sesiones:")
        cursor = collection.find({}).sort("created_at", -1).limit(5)
        
        async for session in cursor:
            ruc = session.get("ruc", "N/A")
            created = session.get("created_at", "N/A")
            expires = session.get("expires_at", "N/A")
            is_active = session.get("is_active", False)
            
            status = "🟢 ACTIVA" if is_active else "🔴 INACTIVA"
            
            # Verificar si está expirada
            if expires != "N/A" and isinstance(expires, datetime):
                if expires < now:
                    status = "⏰ EXPIRADA"
            
            print(f"  - RUC: {ruc} | Creada: {created} | Expira: {expires} | {status}")
        
        # Verificar por RUC específico (el que está en el log)
        test_ruc = "20612969125"
        print(f"\n🔍 Verificando sesiones para RUC {test_ruc}:")
        
        ruc_sessions = await collection.find({"ruc": test_ruc}).to_list(None)
        print(f"  Total sesiones para RUC: {len(ruc_sessions)}")
        
        for session in ruc_sessions:
            created = session.get("created_at", "N/A")
            expires = session.get("expires_at", "N/A")
            is_active = session.get("is_active", False)
            token_preview = session.get("access_token", "")[:20] + "..." if session.get("access_token") else "N/A"
            
            status = "🟢 ACTIVA" if is_active else "🔴 INACTIVA"
            if expires != "N/A" and isinstance(expires, datetime):
                if expires < now:
                    status = "⏰ EXPIRADA"
            
            print(f"    - Creada: {created}")
            print(f"      Expira: {expires}")
            print(f"      Estado: {status}")
            print(f"      Token: {token_preview}")
            print()
        
        # Verificar índices de la colección
        print("📋 Índices de la colección:")
        indexes = await collection.list_indexes().to_list(None)
        for idx in indexes:
            print(f"  - {idx}")
        
        print("\n✅ Diagnóstico completado")
        
    except Exception as e:
        print(f"❌ Error durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()


async def test_mongodb_connection():
    """Probar conexión básica a MongoDB"""
    try:
        print("🔧 Probando conexión a MongoDB...")
        
        # Conectar directamente
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        # Probar inserción simple
        test_collection = db.test_connection
        
        test_doc = {
            "test": "connection",
            "timestamp": datetime.utcnow()
        }
        
        result = await test_collection.insert_one(test_doc)
        print(f"✅ Documento test insertado: {result.inserted_id}")
        
        # Limpiar documento test
        await test_collection.delete_one({"_id": result.inserted_id})
        print("🧹 Documento test eliminado")
        
        # Cerrar conexión
        client.close()
        
        print("✅ Conexión MongoDB OK")
        
    except Exception as e:
        print(f"❌ Error de conexión MongoDB: {e}")


if __name__ == "__main__":
    print("🚀 Script de diagnóstico SIRE")
    print("============================")
    
    # Primero probar conexión básica
    asyncio.run(test_mongodb_connection())
    
    print("\n" + "="*50 + "\n")
    
    # Luego diagnosticar sesiones
    asyncio.run(debug_sire_sessions())
