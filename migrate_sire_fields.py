#!/usr/bin/env python3
"""
Script de migración para actualizar campos SIRE
Migra de sire_sol_* a sunat_* y elimina campos obsoletos
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def migrate_sire_fields():
    """Migrar campos SIRE de sire_sol_* a sunat_*"""
    
    # Conexión a MongoDB
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.erp_db
    companies_collection = db.companies
    
    print("🔄 Iniciando migración de campos SIRE...")
    print("=" * 60)
    
    try:
        # Buscar todas las empresas que tengan campos sire_sol_*
        companies_with_old_fields = await companies_collection.find({
            "$or": [
                {"sire_sol_username": {"$exists": True}},
                {"sire_sol_password": {"$exists": True}}
            ]
        }).to_list(length=None)
        
        print(f"📊 Encontradas {len(companies_with_old_fields)} empresas con campos obsoletos")
        
        migrated_count = 0
        
        for company in companies_with_old_fields:
            ruc = company.get("ruc", "UNKNOWN")
            razon_social = company.get("razon_social", "UNKNOWN")
            
            print(f"\n🏢 Procesando: {ruc} - {razon_social}")
            
            # Preparar datos de actualización
            update_data = {}
            unset_data = {}
            
            # Migrar sire_sol_username a sunat_usuario (solo si sunat_usuario no existe o está vacío)
            if "sire_sol_username" in company:
                if not company.get("sunat_usuario"):
                    update_data["sunat_usuario"] = company["sire_sol_username"]
                    print(f"  ✅ Migrando sire_sol_username → sunat_usuario: {company['sire_sol_username']}")
                else:
                    print(f"  ⚠️  sunat_usuario ya existe: {company['sunat_usuario']}")
                
                # Marcar para eliminar
                unset_data["sire_sol_username"] = ""
            
            # Migrar sire_sol_password a sunat_clave (solo si sunat_clave no existe o está vacío)
            if "sire_sol_password" in company:
                if not company.get("sunat_clave"):
                    update_data["sunat_clave"] = company["sire_sol_password"]
                    print(f"  ✅ Migrando sire_sol_password → sunat_clave: ***")
                else:
                    print(f"  ⚠️  sunat_clave ya existe")
                
                # Marcar para eliminar
                unset_data["sire_sol_password"] = ""
            
            # Actualizar timestamp
            from datetime import datetime
            update_data["fecha_actualizacion"] = datetime.now()
            
            # Ejecutar actualización
            if update_data or unset_data:
                update_operation = {}
                if update_data:
                    update_operation["$set"] = update_data
                if unset_data:
                    update_operation["$unset"] = unset_data
                
                result = await companies_collection.update_one(
                    {"_id": company["_id"]},
                    update_operation
                )
                
                if result.modified_count > 0:
                    migrated_count += 1
                    print(f"  ✅ Empresa {ruc} migrada exitosamente")
                else:
                    print(f"  ❌ Error migrando empresa {ruc}")
            else:
                print(f"  📝 No hay cambios necesarios para {ruc}")
        
        print("\n" + "=" * 60)
        print(f"✅ Migración completada:")
        print(f"   📊 Empresas procesadas: {len(companies_with_old_fields)}")
        print(f"   ✅ Empresas migradas: {migrated_count}")
        
        # Verificar que no queden campos obsoletos
        remaining_old_fields = await companies_collection.count_documents({
            "$or": [
                {"sire_sol_username": {"$exists": True}},
                {"sire_sol_password": {"$exists": True}}
            ]
        })
        
        if remaining_old_fields == 0:
            print(f"   🎉 Todos los campos obsoletos eliminados correctamente")
        else:
            print(f"   ⚠️  Aún quedan {remaining_old_fields} documentos con campos obsoletos")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {type(e).__name__}: {str(e)}")
        raise
    finally:
        client.close()
        print("\n🔌 Conexión cerrada")

async def verify_migration():
    """Verificar el estado después de la migración"""
    
    # Conexión a MongoDB
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.erp_db
    companies_collection = db.companies
    
    print("\n🔍 Verificando migración...")
    print("=" * 40)
    
    try:
        # Contar empresas con credenciales SIRE
        companies_with_sire = await companies_collection.find({
            "sire_activo": True,
            "sire_client_id": {"$exists": True, "$ne": None, "$ne": ""},
            "sunat_usuario": {"$exists": True, "$ne": None, "$ne": ""},
            "sunat_clave": {"$exists": True, "$ne": None, "$ne": ""}
        }).to_list(length=None)
        
        print(f"📊 Empresas con SIRE configurado correctamente: {len(companies_with_sire)}")
        
        for company in companies_with_sire:
            print(f"  ✅ {company['ruc']} - {company['razon_social']}")
            print(f"     📋 Client ID: {company['sire_client_id'][:10]}...")
            print(f"     👤 Usuario SUNAT: {company['sunat_usuario']}")
        
        # Verificar campos obsoletos
        obsolete_fields = await companies_collection.count_documents({
            "$or": [
                {"sire_sol_username": {"$exists": True}},
                {"sire_sol_password": {"$exists": True}}
            ]
        })
        
        if obsolete_fields == 0:
            print(f"\n🎉 ¡Migración exitosa! No quedan campos obsoletos.")
        else:
            print(f"\n⚠️  Atención: Aún quedan {obsolete_fields} documentos con campos obsoletos")
            
    except Exception as e:
        print(f"❌ Error verificando migración: {type(e).__name__}: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    print("🔄 MIGRACIÓN DE CAMPOS SIRE")
    print("De: sire_sol_* → A: sunat_*")
    print("=" * 60)
    
    # Ejecutar migración
    asyncio.run(migrate_sire_fields())
    
    # Verificar resultados
    asyncio.run(verify_migration())
    
    print("\n✅ Proceso completo")
