#!/usr/bin/env python3
"""
Script para crear índices en la colección plan_contable
"""
import sys
import os

# Añadir backend al path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.database import get_database
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def create_indexes_async():
    """Crear índices para optimizar consultas en plan_contable (versión async)"""
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.erp_db
    collection = db["plan_contable"]
    
    print("Creando índices para plan_contable...")
    
    try:
        # Índice único en código
        await collection.create_index("codigo", unique=True)
        print("✅ Índice único en 'codigo' creado")
        
        # Índice en nivel para consultas jerárquicas
        await collection.create_index("nivel")
        print("✅ Índice en 'nivel' creado")
        
        # Índice en clase_contable para filtros por clase
        await collection.create_index("clase_contable")
        print("✅ Índice en 'clase_contable' creado")
        
        # Índice en activa para filtrar cuentas activas
        await collection.create_index("activa")
        print("✅ Índice en 'activa' creado")
        
        # Índice compuesto para búsquedas frecuentes
        await collection.create_index([("activa", 1), ("nivel", 1)])
        print("✅ Índice compuesto en 'activa' + 'nivel' creado")
        
        # Índice de texto para búsquedas por descripción
        await collection.create_index([("descripcion", "text"), ("codigo", "text")])
        print("✅ Índice de texto en 'descripcion' + 'codigo' creado")
        
        print("\n📊 Índices creados correctamente")
        
    except Exception as e:
        print(f"⚠️ Error creando índices: {e}")
    finally:
        client.close()

def create_indexes():
    """Wrapper síncrono para crear índices"""
    asyncio.run(create_indexes_async())

if __name__ == "__main__":
    create_indexes()
