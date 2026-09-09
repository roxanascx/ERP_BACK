from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from .config import settings

# Cargar variables de entorno
load_dotenv()

# URL de MongoDB y nombre de la base de datos (local o MongoDB Atlas)
MONGODB_URL = settings.MONGODB_URL
DATABASE_NAME = settings.DATABASE_NAME

# Cliente de MongoDB
client = None
database = None

async def connect_to_mongo():
    """Conectar a MongoDB"""
    global client, database
    client = AsyncIOMotorClient(MONGODB_URL)
    database = client[DATABASE_NAME]
    print(f"✅ Conectado a MongoDB (base de datos: {DATABASE_NAME})")

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
        database = client[DATABASE_NAME]
    
    return database

# Función async para obtener database (para nuevos módulos SIRE)
async def get_database_async():
    """Obtener la instancia de la base de datos de forma asíncrona"""
    global client, database
    
    if database is None:
        await connect_to_mongo()
    
    return database

async def get_database_connection():
    """Obtener conexión a la base de datos para dependencias"""
    return await get_database_async()

# Función get_db para compatibilidad con FastAPI Depends
async def get_db():
    """Función de dependencia estándar para obtener la base de datos"""
    return await get_database_async()
