from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# URL de MongoDB
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")

# Cliente de MongoDB
client = None
database = None

async def connect_to_mongo():
    """Conectar a MongoDB"""
    global client, database
    client = AsyncIOMotorClient(MONGODB_URL)
    database = client.erp_db
    print("✅ Conectado a MongoDB")

async def close_mongo_connection():
    """Cerrar conexión a MongoDB"""
    global client
    if client:
        client.close()
        print("❌ Conexión a MongoDB cerrada")

def get_database():
    """Obtener la instancia de la base de datos de forma síncrona"""
    global database
    
    # Si no está inicializada, crear conexión síncrona
    if database is None:
        client = AsyncIOMotorClient(MONGODB_URL)
        database = client.erp_db
    
    return database

# Función async para obtener database (para nuevos módulos SIRE)
async def get_database_async():
    """Obtener la instancia de la base de datos de forma asíncrona"""
    global client, database
    
    if database is None:
        await connect_to_mongo()
    
    return database
