"""
Script para autenticar automáticamente una empresa específica
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.modules.sire.services.auth_service import SireAuthService
from app.modules.sire.services.api_client import SunatApiClient
from app.modules.sire.services.token_manager import SireTokenManager
from app.modules.sire.models.auth import SireCredentials


async def auto_authenticate_company(ruc):
    """Autenticar automáticamente una empresa"""
    try:
        print(f"🔐 Autenticando automáticamente RUC: {ruc}")
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        # Obtener credenciales de la empresa
        company = await db.companies.find_one({"ruc": ruc})
        
        if not company:
            print(f"❌ Empresa {ruc} no encontrada")
            return False
        
        if not company.get("sire_activo"):
            print(f"❌ SIRE no está activo para RUC {ruc}")
            return False
        
        # Verificar que tenga todas las credenciales
        required_fields = ["sunat_usuario", "sunat_clave", "sire_client_id", "sire_client_secret"]
        missing_fields = [field for field in required_fields if not company.get(field)]
        
        if missing_fields:
            print(f"❌ Credenciales faltantes: {', '.join(missing_fields)}")
            return False
        
        # Crear credenciales SIRE
        credentials = SireCredentials(
            ruc=ruc,
            sunat_usuario=company["sunat_usuario"],
            sunat_clave=company["sunat_clave"],
            client_id=company["sire_client_id"],
            client_secret=company["sire_client_secret"]
        )
        
        print(f"✅ Credenciales obtenidas para: {company.get('razon_social', 'N/A')}")
        
        # Crear servicios
        api_client = SunatApiClient()
        token_manager = SireTokenManager(mongo_collection=db.sire_sessions)
        auth_service = SireAuthService(api_client, token_manager)
        
        # Verificar si ya existe una sesión válida
        existing_token = await token_manager.get_valid_token(ruc)
        
        if existing_token:
            print(f"✅ Sesión válida existente encontrada")
            client.close()
            return True
        
        # Realizar autenticación
        print(f"🚀 Iniciando autenticación con SUNAT...")
        
        try:
            auth_response = await auth_service.authenticate(credentials)
            
            print("✅ AUTENTICACIÓN EXITOSA!")
            print(f"   Session ID: {auth_response.session_id}")
            print(f"   Expira en: {auth_response.expires_at}")
            
            client.close()
            return True
            
        except Exception as auth_error:
            print(f"❌ Error de autenticación: {auth_error}")
            client.close()
            return False
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False


async def authenticate_all_active_companies():
    """Autenticar todas las empresas activas con SIRE"""
    try:
        print("🏢 Autenticando todas las empresas activas...")
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        # Obtener todas las empresas con SIRE activo
        companies = await db.companies.find({
            "sire_activo": True,
            "sunat_usuario": {"$exists": True, "$ne": ""},
            "sunat_clave": {"$exists": True, "$ne": ""},
            "sire_client_id": {"$exists": True, "$ne": ""},
            "sire_client_secret": {"$exists": True, "$ne": ""}
        }).to_list(None)
        
        print(f"📋 Empresas con SIRE configurado: {len(companies)}")
        
        success_count = 0
        error_count = 0
        
        for company in companies:
            ruc = company.get("ruc")
            razon_social = company.get("razon_social", "N/A")
            
            print(f"\n🔄 Procesando: {razon_social} (RUC: {ruc})")
            
            success = await auto_authenticate_company(ruc)
            
            if success:
                success_count += 1
                print(f"   ✅ Autenticado exitosamente")
            else:
                error_count += 1
                print(f"   ❌ Error en autenticación")
        
        print(f"\n📊 RESUMEN:")
        print(f"   ✅ Autenticaciones exitosas: {success_count}")
        print(f"   ❌ Errores: {error_count}")
        print(f"   📋 Total procesadas: {len(companies)}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error general: {e}")


if __name__ == "__main__":
    print("🔐 Script de auto-autenticación SIRE")
    print("=" * 50)
    
    # Opción 1: Autenticar empresa específica del frontend
    specific_ruc = "20611554282"
    print(f"Opción 1: Autenticar RUC específico {specific_ruc}")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        print("Ejecutando autenticación masiva...")
        asyncio.run(authenticate_all_active_companies())
    else:
        print("Ejecutando autenticación específica...")
        asyncio.run(auto_authenticate_company(specific_ruc))
