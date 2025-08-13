#!/usr/bin/env python3
"""
Script de debug para verificar datos SIRE en MongoDB
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

async def debug_sire_data():
    """Verificar datos SIRE en MongoDB"""
    
    print("🔍 Iniciando debug de datos SIRE...")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.erp_db
    companies_collection = db.companies
    
    try:
        # Obtener todas las empresas
        print("📊 Obteniendo empresas de MongoDB...")
        companies = await companies_collection.find({}).to_list(length=None)
        
        print(f"📈 Total de empresas encontradas: {len(companies)}")
        
        for company in companies:
            print(f"\n🏢 EMPRESA: {company.get('ruc', 'N/A')} - {company.get('razon_social', 'N/A')}")
            print(f"   📋 ID: {company.get('_id', 'N/A')}")
            print(f"   🔴 Activa: {company.get('activa', 'N/A')}")
            print(f"   🔵 SIRE Activo: {company.get('sire_activo', 'N/A')} (tipo: {type(company.get('sire_activo'))})")
            print(f"   🔑 Client ID: {company.get('sire_client_id', 'N/A')}")
            print(f"   🔐 Client Secret: {'***' if company.get('sire_client_secret') else 'N/A'}")
            print(f"   👤 SUNAT Usuario: {company.get('sunat_usuario', 'N/A')}")
            print(f"   🔒 SUNAT Clave: {'***' if company.get('sunat_clave') else 'N/A'}")
            print(f"   📅 Fecha Registro: {company.get('fecha_registro', 'N/A')}")
            print(f"   📅 Fecha Actualización: {company.get('fecha_actualizacion', 'N/A')}")
            
            # Verificar si tiene SIRE según lógica del modelo
            tiene_sire = (
                bool(company.get('sire_activo')) and 
                bool(company.get('sire_client_id')) and 
                bool(company.get('sire_client_secret')) and 
                bool(company.get('sunat_usuario')) and 
                bool(company.get('sunat_clave'))
            )
            print(f"   ✅ Tiene SIRE (calculado): {tiene_sire}")
            
            # Mostrar todos los campos para debug
            print(f"   🗃️  Todos los campos:")
            for key, value in company.items():
                if key not in ['_id', 'ruc', 'razon_social', 'sire_client_secret', 'sunat_clave']:
                    print(f"      {key}: {value} (tipo: {type(value)})")
        
        # Buscar específicamente empresas con SIRE
        print(f"\n🔍 Buscando empresas con SIRE activo...")
        sire_companies = await companies_collection.find({"sire_activo": True}).to_list(length=None)
        print(f"📊 Empresas con sire_activo=True: {len(sire_companies)}")
        
        # Buscar empresas con client_id
        client_id_companies = await companies_collection.find({"sire_client_id": {"$exists": True, "$ne": None, "$ne": ""}}).to_list(length=None)
        print(f"📊 Empresas con sire_client_id: {len(client_id_companies)}")
        
    except Exception as e:
        print(f"❌ Error en debug: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 Traceback:\n{traceback.format_exc()}")
    finally:
        client.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    asyncio.run(debug_sire_data())
