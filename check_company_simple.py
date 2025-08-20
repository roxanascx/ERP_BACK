"""
Script simplificado para verificar la empresa
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    """Función principal"""
    try:
        # Conectar directamente
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client.erp_db
        
        print("✅ Conectado a MongoDB")
        
        # Verificar empresa específica
        test_ruc = "20612969125"
        collection = db.companies
        company = await collection.find_one({"ruc": test_ruc})
        
        if not company:
            print(f"❌ Empresa con RUC {test_ruc} NO encontrada")
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
        for field in sire_fields:
            value = company.get(field)
            if value:
                masked_value = str(value)[:4] + '*' * max(0, len(str(value)) - 4)
                print(f"   ✅ {field}: {masked_value}")
            else:
                print(f"   ❌ {field}: NO configurado")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n⚠️ Campos SIRE faltantes: {', '.join(missing_fields)}")
        else:
            print("\n✅ Todas las credenciales SIRE están configuradas")
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
