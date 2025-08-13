#!/usr/bin/env python3
"""
Script de migración para unificar credenciales SIRE
Migra de sire_sol_* a sunat_* para consistencia
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Añadir el directorio app al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")

async def migrate_sire_credentials():
    """Migrar credenciales SIRE para consistencia"""
    
    print("🚀 Iniciando migración de credenciales SIRE...")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.erp_db
    companies_collection = db.companies
    
    try:
        # Buscar empresas con credenciales sire_sol_*
        print("🔍 Buscando empresas con credenciales sire_sol_*...")
        companies_with_sire_sol = await companies_collection.find({
            "$or": [
                {"sire_sol_username": {"$exists": True, "$ne": None, "$ne": ""}},
                {"sire_sol_password": {"$exists": True, "$ne": None, "$ne": ""}}
            ]
        }).to_list(length=None)
        
        print(f"📊 Empresas encontradas con sire_sol_*: {len(companies_with_sire_sol)}")
        
        for company in companies_with_sire_sol:
            ruc = company.get('ruc', 'N/A')
            razon_social = company.get('razon_social', 'N/A')
            
            print(f"\n🏢 Migrando: {ruc} - {razon_social}")
            
            # Preparar actualización
            update_data = {}
            
            # Migrar sire_sol_username a sunat_usuario si no existe
            if company.get('sire_sol_username') and not company.get('sunat_usuario'):
                update_data['sunat_usuario'] = company['sire_sol_username']
                print(f"   👤 Migrando username: {company['sire_sol_username']}")
            
            # Migrar sire_sol_password a sunat_clave si no existe
            if company.get('sire_sol_password') and not company.get('sunat_clave'):
                update_data['sunat_clave'] = company['sire_sol_password']
                print(f"   🔒 Migrando password: ***")
            
            # Si hay algo que migrar
            if update_data:
                # Actualizar el documento
                result = await companies_collection.update_one(
                    {"_id": company["_id"]},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    print(f"   ✅ Migración exitosa")
                else:
                    print(f"   ❌ No se pudo migrar")
            else:
                print(f"   ℹ️  Ya tiene sunat_usuario/sunat_clave, no necesita migración")
        
        # Verificar resultado final
        print(f"\n🔍 Verificando resultado de la migración...")
        all_companies = await companies_collection.find({}).to_list(length=None)
        
        for company in all_companies:
            ruc = company.get('ruc', 'N/A')
            tiene_sire_completo = (
                bool(company.get('sire_activo')) and 
                bool(company.get('sire_client_id')) and 
                bool(company.get('sire_client_secret')) and 
                bool(company.get('sunat_usuario')) and 
                bool(company.get('sunat_clave'))
            )
            
            if company.get('sire_activo'):
                print(f"🏢 {ruc}: SIRE activo - Completo: {tiene_sire_completo}")
                if not tiene_sire_completo:
                    print(f"   ❌ Falta: client_id={bool(company.get('sire_client_id'))}, "
                          f"client_secret={bool(company.get('sire_client_secret'))}, "
                          f"sunat_usuario={bool(company.get('sunat_usuario'))}, "
                          f"sunat_clave={bool(company.get('sunat_clave'))}")
        
        print(f"\n✅ Migración completada")
        
    except Exception as e:
        print(f"❌ Error en migración: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 Traceback:\n{traceback.format_exc()}")
    finally:
        client.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    asyncio.run(migrate_sire_credentials())
