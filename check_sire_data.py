#!/usr/bin/env python3
"""
Script para revisar específicamente los datos SIRE del RUC problemático
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_sire_data():
    """Verificar datos SIRE específicos"""
    print("🔍 Verificando datos SIRE específicos...")
    
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.erp_db
    collection = db.companies
    
    # Buscar el RUC problemático
    ruc_problematico = "10476496077"
    doc = await collection.find_one({"ruc": ruc_problematico})
    
    if doc:
        print(f"\n📄 Datos completos del RUC {ruc_problematico}:")
        print(f"  RUC: {doc.get('ruc')}")
        print(f"  Razón Social: {doc.get('razon_social')}")
        print(f"  sire_activo: {doc.get('sire_activo')} (tipo: {type(doc.get('sire_activo')).__name__})")
        
        # Revisar todos los campos SIRE
        sire_fields = ['sire_client_id', 'sire_client_secret', 'sire_sol_username', 'sire_sol_password']
        for field in sire_fields:
            value = doc.get(field)
            print(f"  {field}: '{value}' (tipo: {type(value).__name__})")
        
        # Simular el método tiene_sire
        print(f"\n🧪 Simulando método tiene_sire():")
        sire_activo = doc.get('sire_activo', False)
        sire_client_id = doc.get('sire_client_id')
        sire_client_secret = doc.get('sire_client_secret')
        sire_sol_username = doc.get('sire_sol_username')
        sire_sol_password = doc.get('sire_sol_password')
        
        print(f"  sire_activo: {sire_activo}")
        print(f"  sire_client_id: {bool(sire_client_id)}")
        print(f"  sire_client_secret: {bool(sire_client_secret)}")
        print(f"  sire_sol_username: {bool(sire_sol_username)}")
        print(f"  sire_sol_password: {bool(sire_sol_password)}")
        
        tiene_sire_result = (
            sire_activo and 
            sire_client_id and 
            sire_client_secret and 
            sire_sol_username and 
            sire_sol_password
        )
        
        print(f"  RESULTADO tiene_sire: {tiene_sire_result}")
        
        # Verificar si algún campo contiene "Fredy221"
        print(f"\n🔍 Buscando 'Fredy221' en los campos:")
        for key, value in doc.items():
            if isinstance(value, str) and 'Fredy221' in value:
                print(f"  ❌ ENCONTRADO en {key}: {value}")
    else:
        print(f"❌ No se encontró el documento con RUC {ruc_problematico}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_sire_data())
