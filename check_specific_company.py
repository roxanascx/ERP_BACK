"""
Script para verificar empresa específica y sus credenciales SIRE
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_specific_company(ruc):
    """Verificar empresa específica"""
    try:
        # Conectar directamente
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        print(f"🔍 Verificando empresa RUC: {ruc}")
        
        # Verificar empresa específica
        collection = db.companies
        company = await collection.find_one({"ruc": ruc})
        
        if not company:
            print(f"❌ Empresa con RUC {ruc} NO encontrada")
            return
        
        print(f"✅ Empresa encontrada: {company.get('razon_social', 'N/A')}")
        print(f"   RUC: {company.get('ruc')}")
        print(f"   Activa: {company.get('is_active', False)}")
        print(f"   SIRE Activo: {company.get('sire_activo', False)}")
        
        # Verificar credenciales SIRE
        print("\n🔐 Verificando credenciales SIRE:")
        
        sire_fields = [
            "sunat_usuario",
            "sunat_clave", 
            "sire_client_id",
            "sire_client_secret"
        ]
        
        missing_fields = []
        configured_fields = []
        
        for field in sire_fields:
            value = company.get(field)
            if value and str(value).strip():
                masked_value = str(value)[:4] + '*' * max(0, len(str(value)) - 4)
                print(f"   ✅ {field}: {masked_value}")
                configured_fields.append(field)
            else:
                print(f"   ❌ {field}: NO configurado")
                missing_fields.append(field)
        
        # Verificar estructura legacy
        sire_creds = company.get("sire_credentials", {})
        if sire_creds:
            print("\n📋 Estructura legacy 'sire_credentials':")
            for key, value in sire_creds.items():
                if value and str(value).strip():
                    masked_value = str(value)[:4] + '*' * max(0, len(str(value)) - 4)
                    print(f"   ✅ {key}: {masked_value}")
                else:
                    print(f"   ❌ {key}: NO configurado")
        
        # Verificar sesiones existentes
        print(f"\n🔍 Verificando sesiones SIRE para RUC {ruc}:")
        sessions = await db.sire_sessions.find({"ruc": ruc}).to_list(None)
        print(f"   Total de sesiones: {len(sessions)}")
        
        for i, session in enumerate(sessions, 1):
            print(f"   Sesión {i}:")
            print(f"     - ID: {session.get('_id')}")
            print(f"     - Activa: {session.get('is_active')}")
            print(f"     - Creada: {session.get('created_at')}")
            print(f"     - Expira: {session.get('expires_at')}")
        
        # Conclusión
        print(f"\n📊 RESUMEN para RUC {ruc}:")
        if len(configured_fields) == 4:
            print("   ✅ Credenciales SIRE: COMPLETAS")
            if len(sessions) > 0:
                print("   ✅ Sesiones: EXISTEN")
                print("   💡 Recomendación: Verificar si la sesión está expirada")
            else:
                print("   ⚠️ Sesiones: NO EXISTEN")
                print("   💡 Recomendación: Realizar autenticación SIRE")
        else:
            print("   ❌ Credenciales SIRE: INCOMPLETAS")
            print(f"   📝 Faltan: {', '.join(missing_fields)}")
            print("   💡 Recomendación: Configurar credenciales SIRE en la empresa")
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ruc_to_check = "20611554282"  # RUC del frontend
    print(f"🏢 Verificando empresa RUC: {ruc_to_check}")
    print("=" * 50)
    
    asyncio.run(check_specific_company(ruc_to_check))
