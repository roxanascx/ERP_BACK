"""
Script para probar autenticación SIRE completa
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.modules.sire.services.auth_service import SireAuthService
from app.modules.sire.services.api_client import SunatApiClient
from app.modules.sire.services.token_manager import SireTokenManager
from app.modules.sire.models.auth import SireCredentials


async def test_complete_authentication():
    """Probar proceso completo de autenticación"""
    try:
        print("🔐 Probando autenticación SIRE completa...")
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        print("✅ Conectado a MongoDB")
        
        # Obtener credenciales de la empresa
        test_ruc = "20612969125"
        company = await db.companies.find_one({"ruc": test_ruc})
        
        if not company:
            print(f"❌ Empresa {test_ruc} no encontrada")
            return
        
        # Crear credenciales SIRE
        credentials = SireCredentials(
            ruc=test_ruc,
            sunat_usuario=company["sunat_usuario"],
            sunat_clave=company["sunat_clave"],
            client_id=company["sire_client_id"],
            client_secret=company["sire_client_secret"]
        )
        
        print(f"🔧 Credenciales obtenidas para RUC: {test_ruc}")
        print(f"   Usuario: {credentials.sunat_usuario}")
        print(f"   Client ID: {credentials.client_id[:8]}...")
        
        # Crear servicios
        api_client = SunatApiClient()
        token_manager = SireTokenManager(mongo_collection=db.sire_sessions)
        auth_service = SireAuthService(api_client, token_manager)
        
        print("✅ Servicios de autenticación creados")
        
        # Verificar si ya existe una sesión válida
        print("🔍 Verificando sesión existente...")
        existing_token = await token_manager.get_valid_token(test_ruc)
        
        if existing_token:
            print(f"✅ Token existente encontrado: {existing_token[:20]}...")
        else:
            print("ℹ️ No hay tokens válidos existentes")
        
        # Intentar autenticación
        print("\n🚀 Iniciando autenticación con SUNAT...")
        
        try:
            auth_response = await auth_service.authenticate(credentials)
            
            print("✅ AUTENTICACIÓN EXITOSA!")
            print(f"   Session ID: {auth_response.session_id}")
            print(f"   Expira en: {auth_response.expires_at}")
            print(f"   Token: {auth_response.token_data.access_token[:20]}...")
            
            # Verificar que se guardó en MongoDB
            print("\n🔍 Verificando almacenamiento en MongoDB...")
            session_count = await db.sire_sessions.count_documents({"ruc": test_ruc})
            print(f"   Sesiones para RUC {test_ruc}: {session_count}")
            
            # Mostrar la sesión más reciente
            latest_session = await db.sire_sessions.find_one(
                {"ruc": test_ruc}, 
                sort=[("created_at", -1)]
            )
            
            if latest_session:
                print("   ✅ Sesión más reciente:")
                print(f"      ID: {latest_session.get('_id')}")
                print(f"      Activa: {latest_session.get('is_active')}")
                print(f"      Creada: {latest_session.get('created_at')}")
                print(f"      Expira: {latest_session.get('expires_at')}")
            
        except Exception as auth_error:
            print(f"❌ Error de autenticación: {auth_error}")
            import traceback
            traceback.print_exc()
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 Script de prueba de autenticación SIRE")
    print("=" * 50)
    
    asyncio.run(test_complete_authentication())
