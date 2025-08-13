#!/usr/bin/env python3
"""
Script para verificar exactamente qué campos SIRE tiene cada empresa
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_sire_fields():
    """Verificar campos SIRE específicamente"""
    print("🔍 Verificando campos SIRE en detalle...")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["erp_db"]
    collection = db["companies"]
    
    try:
        # Buscar TODOS los documentos
        all_docs = await collection.find({}).to_list(length=None)
        
        print(f"📊 Empresas encontradas: {len(all_docs)}")
        
        for doc in all_docs:
            ruc = doc.get("ruc", "UNKNOWN")
            print(f"\n🏢 Empresa: {ruc}")
            print(f"   📋 Razón social: {doc.get('razon_social', 'N/A')}")
            
            # Campos SIRE específicos
            sire_fields = [
                'sire_client_id',
                'sire_client_secret', 
                'sire_sol_username',
                'sire_sol_password',
                'sire_activo'
            ]
            
            print("   🔐 Campos SIRE:")
            for field in sire_fields:
                value = doc.get(field)
                if value is not None:
                    if field in ['sire_client_secret', 'sire_sol_password']:
                        # Mostrar solo los primeros caracteres de campos sensibles
                        display_value = f"{str(value)[:5]}..." if value else "None"
                    else:
                        display_value = value
                    print(f"      {field}: {display_value}")
                else:
                    print(f"      {field}: NOT EXISTS")
            
            # Verificar si tiene SIRE configurado
            has_basic_sire = doc.get('sire_client_id') and doc.get('sire_client_secret')
            has_full_sire = has_basic_sire and doc.get('sire_sol_username') and doc.get('sire_sol_password')
            print(f"   ✅ Tiene SIRE básico: {has_basic_sire}")
            print(f"   ✅ Tiene SIRE completo: {has_full_sire}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("\n🔒 Conexión cerrada")

if __name__ == "__main__":
    asyncio.run(check_sire_fields())
