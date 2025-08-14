from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json

from .database import connect_to_mongo, close_mongo_connection
from .routes import users
from .core.router import api_router  # Usar el router centralizado

# Cargar variables de entorno
load_dotenv()

# Configuración para diferentes entornos
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Crear instancia de FastAPI
app = FastAPI(
    title="ERP API",
    description="API para sistema ERP - Gestión empresarial con MongoDB",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,  # Deshabilitar docs en producción
    redoc_url="/redoc" if DEBUG else None,  # Deshabilitar redoc en producción
    redirect_slashes=False  # Evitar redirects automáticos
)

# Configuración CORS dinámica
def get_cors_origins():
    cors_origins_env = os.getenv("CORS_ORIGINS")
    if cors_origins_env:
        try:
            # Intentar parsear como JSON
            return json.loads(cors_origins_env)
        except json.JSONDecodeError:
            # Si no es JSON válido, dividir por comas
            return [origin.strip() for origin in cors_origins_env.split(",")]
    
    # Valores por defecto para desarrollo
    return [
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ]

origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging para debugging en desarrollo
if DEBUG:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"🌍 CORS Origins: {origins}")
    logger.info(f"🔧 Environment: {ENVIRONMENT}")

# Eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

# Ruta raíz
@app.get("/")
async def root():
    return {
        "message": "ERP API - Sistema de gestión empresarial",
        "environment": ENVIRONMENT,
        "version": "1.0.0",
        "status": "operational",
        "database": "MongoDB",
        "docs": "/docs" if DEBUG else "disabled"
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ERP API", "database": "MongoDB"}

# Ruta simple de prueba
@app.get("/hola")
async def hola_mundo():
    return {
        "message": "¡Hola Mundo!",
        "status": "ERP Backend funcionando correctamente",
        "database": "MongoDB configurado",
        "framework": "FastAPI"
    }

# Ruta de prueba para MongoDB
@app.get("/test-db")
async def test_database():
    from .database import get_database
    db = get_database()
    
    try:
        # Prueba simple de conexión
        server_info = await db.command("ping")
        
        return {
            "status": "success",
            "message": "✅ MongoDB conectado y funcionando",
            "ping_response": server_info,
            "database_name": db.name
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"❌ Error de conexión: {str(e)}"
        }

# Incluir rutas centralizadas
app.include_router(users.router, prefix="/api/users", tags=["Usuarios"])
app.include_router(api_router)  # Incluye companies y sire con prefijo /api/v1

# Eventos de ciclo de vida de la aplicación
@app.on_event("startup")
async def startup_event():
    """Inicializar conexiones al arrancar la aplicación"""
    print("🚀 Iniciando aplicación...")
    await connect_to_mongo()
    print("✅ Aplicación lista")

@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexiones al apagar la aplicación"""
    print("🛑 Cerrando aplicación...")
    await close_mongo_connection()
    print("✅ Aplicación cerrada")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
