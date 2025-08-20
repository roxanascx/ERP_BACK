"""
Script de prueba para verificar por qué no se almacenan tokens en MongoDB
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database
from app.modules.sire.services.token_manager import SireTokenManager
from app.modules.sire.models.auth import SireTokenData, SireSession


async def test_token_storage():
    """Probar almacenamiento de tokens en MongoDB"""
    try:
        print("🧪 Iniciando prueba de almacenamiento de tokens...")
        
        # Obtener base de datos
        db = get_database()
        
        if db is None:
            print("❌ Error: No se pudo conectar a la base de datos")
            return
        
        print("✅ Conectado a MongoDB")
        
        # Crear token manager con la colección
        token_manager = SireTokenManager(
            mongo_collection=db.sire_sessions
        )
        
        print("✅ Token manager creado")
        
        # Crear datos de token de prueba
        test_token_data = SireTokenData(
            access_token="test_token_" + str(int(datetime.utcnow().timestamp())),
            refresh_token="refresh_test_token_" + str(int(datetime.utcnow().timestamp())),
            token_type="Bearer",
            expires_in=3600  # 1 hora
        )
        
        test_ruc = "20612969125"
        test_credentials_hash = "test_hash_123"
        
        print(f"🔧 Probando almacenamiento para RUC: {test_ruc}")
        print(f"📝 Token de prueba: {test_token_data.access_token[:20]}...")
        
        # Intentar almacenar el token
        try:
            session_id = await token_manager.store_token(
                test_ruc,
                test_token_data,
                test_credentials_hash
            )
            
            print(f"✅ Token almacenado con session_id: {session_id}")
            
            # Verificar que se almacenó correctamente
            collection = db.sire_sessions
            stored_session = await collection.find_one({"_id": session_id})
            
            if stored_session:
                print("✅ Sesión encontrada en MongoDB:")
                print(f"  - RUC: {stored_session.get('ruc')}")
                print(f"  - Token: {stored_session.get('access_token', '')[:20]}...")
                print(f"  - Activa: {stored_session.get('is_active')}")
                print(f"  - Expira: {stored_session.get('expires_at')}")
            else:
                print("❌ Sesión NO encontrada en MongoDB después del almacenamiento")
                
            # Probar recuperación del token
            print("\n🔍 Probando recuperación de token...")
            
            retrieved_token = await token_manager.get_valid_token(test_ruc)
            
            if retrieved_token:
                print(f"✅ Token recuperado exitosamente: {retrieved_token[:20]}...")
            else:
                print("❌ No se pudo recuperar el token")
                
            # Limpiar token de prueba
            print("\n🧹 Limpiando token de prueba...")
            await collection.delete_one({"_id": session_id})
            print("✅ Token de prueba eliminado")
                
        except Exception as e:
            print(f"❌ Error almacenando token: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error durante prueba: {e}")
        import traceback
        traceback.print_exc()


async def test_manual_session_storage():
    """Probar almacenamiento manual de sesión"""
    try:
        print("\n🔧 Probando almacenamiento manual de sesión...")
        
        db = get_database()
        collection = db.sire_sessions
        
        # Crear sesión manual
        manual_session = {
            "_id": "manual_test_session_" + str(int(datetime.utcnow().timestamp())),
            "ruc": "20612969125",
            "access_token": "manual_test_token_123",
            "refresh_token": "manual_refresh_token_123",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "is_active": True,
            "credentials_hash": "manual_test_hash"
        }
        
        # Insertar manualmente
        result = await collection.insert_one(manual_session)
        print(f"✅ Sesión manual insertada: {result.inserted_id}")
        
        # Verificar que existe
        found_session = await collection.find_one({"_id": result.inserted_id})
        if found_session:
            print("✅ Sesión manual encontrada")
        else:
            print("❌ Sesión manual NO encontrada")
            
        # Limpiar
        await collection.delete_one({"_id": result.inserted_id})
        print("🧹 Sesión manual eliminada")
        
    except Exception as e:
        print(f"❌ Error en prueba manual: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Script de prueba de almacenamiento de tokens SIRE")
    print("=" * 60)
    
    asyncio.run(test_manual_session_storage())
    asyncio.run(test_token_storage())
