# ERP Backend

API backend para sistema ERP desarrollado con FastAPI y MongoDB.

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno (crear archivo .env):
```
MONGODB_URL=mongodb://localhost:27017/erp_db
DEBUG=True
ENVIRONMENT=development
```

4. Asegúrate de tener MongoDB ejecutándose:
```bash
# Si tienes MongoDB instalado localmente
mongod

# O usar Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

5. Ejecutar la aplicación:
```bash
uvicorn app.main:app --reload
```

## Estructura del proyecto

```
backend/
├── app/
│   ├── main.py         # Aplicación principal
│   ├── database.py     # Configuración de MongoDB
│   └── __init__.py     # Paquete Python
├── requirements.txt    # Dependencias
└── README.md          # Este archivo
```

## API Documentation

Una vez que la aplicación esté ejecutándose, puedes acceder a:
- Documentación Swagger: http://localhost:8000/docs
- Documentación ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health
- Test Database: http://localhost:8000/test-db

## Base de datos

Este proyecto usa MongoDB como base de datos. Asegúrate de tener MongoDB ejecutándose en tu sistema antes de iniciar la aplicación.
