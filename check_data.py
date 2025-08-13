#!/usr/bin/env python3
"""
Script para verificar los datos en la base de datos y encontrar el problema específico
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_database():
    """Verificar datos en la base de datos"""
    print("🔍 Conectando a MongoDB...")
    
    # Conectar a MongoDB con los nombres correctos
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    # Listar todas las bases de datos
    print("\n📊 Bases de datos disponibles:")
    db_list = await client.list_database_names()
    for db_name in db_list:
        print(f"  - {db_name}")
    
    # Probar con erp_db
    db = client.erp_db
    print(f"\n📊 Colecciones en erp_db:")
    collection_list = await db.list_collection_names()
    for col_name in collection_list:
        print(f"  - {col_name}")
    
    # Revisar la colección companies
    if "companies" in collection_list:
        collection = db.companies
        print(f"\n📄 Documentos en companies:")
        
        count = 0
        async for doc in collection.find():
            count += 1
            ruc = doc.get('ruc', 'N/A')
            razon_social = doc.get('razon_social', 'N/A')
            sire_activo = doc.get('sire_activo')
            activa = doc.get('activa')
            
            print(f"\n  📝 Documento #{count}:")
            print(f"    RUC: {ruc}")
            print(f"    Razón Social: {razon_social}")
            print(f"    sire_activo: {sire_activo} (tipo: {type(sire_activo).__name__})")
            print(f"    activa: {activa} (tipo: {type(activa).__name__})")
            
            # Verificar si tiene el método tiene_sire
            if 'tiene_sire' in doc:
                tiene_sire = doc.get('tiene_sire')
                print(f"    tiene_sire: {tiene_sire} (tipo: {type(tiene_sire).__name__})")
            
            # Mostrar todos los campos para debug
            print(f"    Todos los campos: {list(doc.keys())}")
            
            # Buscar campos con tipos incorrectos
            problemas = []
            for key, value in doc.items():
                if key in ['sire_activo', 'activa'] and not isinstance(value, bool):
                    problemas.append(f"{key}: {value} (tipo: {type(value).__name__})")
            
            if problemas:
                print(f"    ❌ PROBLEMAS: {', '.join(problemas)}")
            else:
                print(f"    ✅ Sin problemas detectados")
        
        print(f"\n📊 Total de documentos: {count}")
    else:
        print("❌ No se encontró la colección 'companies'")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_database())
