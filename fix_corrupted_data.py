#!/usr/bin/env python3
"""
Script para arreglar datos corruptos en la base de datos
Específicamente el campo 'sire_activo' que puede tener strings en lugar de booleans
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def fix_corrupted_data():
    """Arreglar datos corruptos en la base de datos"""
    print("🔧 Iniciando reparación de datos corruptos...")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["erp_contable"]
    collection = db["companies"]
    
    try:
        # Buscar TODOS los documentos para inspeccionar
        all_docs = await collection.find({}).to_list(length=None)
        
        print(f"📊 Inspeccionando {len(all_docs)} documentos...")
        
        corrupted_count = 0
        for doc in all_docs:
            ruc = doc.get("ruc", "UNKNOWN")
            print(f"\n🔍 Inspeccionando RUC: {ruc}")
            
            # Verificar campo sire_activo
            sire_activo = doc.get("sire_activo")
            if sire_activo is not None:
                print(f"   📜 sire_activo: {sire_activo} (tipo: {type(sire_activo).__name__})")
                if not isinstance(sire_activo, bool):
                    print(f"   ⚠️  Campo sire_activo corrupto!")
                    corrupted_count += 1
                    
                    # Convertir a boolean
                    if isinstance(sire_activo, str):
                        new_value = sire_activo.lower() in ('true', '1', 'yes', 'on', 'active', 'activo')
                    else:
                        new_value = bool(sire_activo)
                    
                    print(f"   🔧 Corrigiendo a: {new_value}")
                    
                    # Actualizar el documento
                    result = await collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "sire_activo": new_value,
                                "fecha_actualizacion": datetime.now()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        print(f"   ✅ Documento {ruc} actualizado exitosamente")
                    else:
                        print(f"   ❌ No se pudo actualizar el documento {ruc}")
            
            # Verificar otros campos booleanos
            for field in ['activa']:
                value = doc.get(field)
                if value is not None and not isinstance(value, bool):
                    print(f"   ⚠️  Campo {field} corrupto: {value} (tipo: {type(value).__name__})")
                    corrupted_count += 1
        
        if corrupted_count == 0:
            print("\n✅ No se encontraron datos corruptos")
        else:
            print(f"\n📊 Se encontraron y corrigieron {corrupted_count} campos corruptos")
            
    except Exception as e:
        print(f"❌ Error durante la reparación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("🔒 Conexión a base de datos cerrada")

if __name__ == "__main__":
    asyncio.run(fix_corrupted_data())
