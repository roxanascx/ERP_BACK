"""
Script para verificar la empresa y sus credenciales SIRE
"""

import asyncio
import os
import sys
from datetime import datetime

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_database


async def check_company_sire_config():
    """Verificar configuración SIRE de la empresa"""
    try:
        print("🏢 Verificando configuración SIRE de empresa...")
        
        # Obtener base de datos
        db = get_database()
        
        if db is None:
            print("❌ Error: No se pudo conectar a la base de datos")
            return
        
        print("✅ Conectado a MongoDB")
        
        # Verificar empresa específica
        test_ruc = "20612969125"
        
        collection = db.companies
        company = await collection.find_one({"ruc": test_ruc})
        
        if not company:
            print(f"❌ Empresa con RUC {test_ruc} NO encontrada en la base de datos")
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
                print(f"   ✅ {field}: {'*' * len(str(value)[:4])}... (configurado)")
            else:
                print(f"   ❌ {field}: NO configurado")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n⚠️ Campos SIRE faltantes: {', '.join(missing_fields)}")
            print("💡 La empresa necesita configurar credenciales SIRE para autenticarse")
        else:
            print("\n✅ Todas las credenciales SIRE están configuradas")
        
        # Verificar también credenciales legacy si existen
        print("\n🔍 Verificando estructura legacy 'sire_credentials':")
        sire_creds = company.get("sire_credentials", {})
        if sire_creds:
            print("   ✅ Estructura 'sire_credentials' encontrada:")
            for key, value in sire_creds.items():
                if value:
                    print(f"     ✅ {key}: {'*' * len(str(value)[:4])}... (configurado)")
                else:
                    print(f"     ❌ {key}: NO configurado")
        else:
            print("   ℹ️ No hay estructura 'sire_credentials' legacy")
        
    except Exception as e:
        print(f"❌ Error durante verificación: {e}")
        import traceback
        traceback.print_exc()


async def check_all_companies():
    """Verificar todas las empresas en la base de datos"""
    try:
        print("\n📋 Listando todas las empresas...")
        
        db = get_database()
        collection = db.companies
        
        companies = await collection.find({}).to_list(None)
        
        print(f"Total de empresas: {len(companies)}")
        
        for company in companies:
            ruc = company.get('ruc', 'N/A')
            razon_social = company.get('razon_social', 'N/A')
            sire_activo = company.get('sire_activo', False)
            is_active = company.get('is_active', False)
            
            status = "🟢" if is_active else "🔴"
            sire_status = "🟢" if sire_activo else "🔴"
            
            print(f"   {status} RUC: {ruc} | {razon_social[:30]}... | SIRE: {sire_status}")
        
    except Exception as e:
        print(f"❌ Error listando empresas: {e}")


if __name__ == "__main__":
    print("🏢 Script de verificación de empresa y credenciales SIRE")
    print("=" * 60)
    
    asyncio.run(check_all_companies())
    asyncio.run(check_company_sire_config())
