# Configuración global del sistema ERP
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Base de datos
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/erp_db")
    DATABASE_NAME: str = "erp_db"
    
    # Seguridad
    SECRET_KEY: str = os.getenv("SECRET_KEY", "tu-clave-secreta-muy-segura")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    
    # Aplicación
    APP_NAME: str = "ERP Contable"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Contabilidad
    DEFAULT_CURRENCY: str = "USD"
    DECIMAL_PLACES: int = 2
    
    # Facturación
    INVOICE_PREFIX: str = "INV"
    RECEIPT_PREFIX: str = "REC"

settings = Settings()
