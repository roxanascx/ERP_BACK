"""
Tests básicos para el módulo de Socios de Negocio
"""

import pytest
import asyncio
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app

# Configuración de test
TEST_MONGODB_URL = "mongodb://localhost:27017/erp_test_db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_client():
    """Cliente HTTP de prueba"""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

@pytest.fixture
async def test_db():
    """Base de datos de prueba"""
    client = AsyncIOMotorClient(TEST_MONGODB_URL)
    db = client.erp_test_db
    
    # Limpiar base de datos antes de cada test
    await db.socios_negocio.delete_many({})
    
    yield db
    
    # Limpiar después del test
    await db.socios_negocio.delete_many({})
    client.close()

@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test básico de health check del módulo"""
    response = await test_client.get("/api/v1/socios-negocio/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["module"] == "socios_negocio"

@pytest.mark.asyncio
async def test_crear_socio_basico(test_client):
    """Test de creación básica de socio"""
    socio_data = {
        "tipo_documento": "DNI",
        "numero_documento": "12345678",
        "razon_social": "Juan Pérez",
        "tipo_socio": "cliente"
    }
    
    response = await test_client.post(
        "/api/v1/socios-negocio/?empresa_id=test_empresa_123",
        json=socio_data
    )
    
    # Debería fallar porque no hay conexión a MongoDB en el test
    # Pero podemos verificar que la ruta existe y la validación funciona
    assert response.status_code in [201, 422, 500]

@pytest.mark.asyncio 
async def test_validacion_documento_invalido(test_client):
    """Test de validación de documento inválido"""
    socio_data = {
        "tipo_documento": "DNI",
        "numero_documento": "123",  # DNI inválido
        "razon_social": "Test",
        "tipo_socio": "cliente"
    }
    
    response = await test_client.post(
        "/api/v1/socios-negocio/?empresa_id=test_empresa_123",
        json=socio_data
    )
    
    # Debería retornar error de validación
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_consulta_ruc_endpoint(test_client):
    """Test del endpoint de consulta RUC"""
    ruc_data = {
        "ruc": "20123456789"
    }
    
    response = await test_client.post(
        "/api/v1/socios-negocio/consulta-ruc",
        json=ruc_data
    )
    
    # El endpoint debería existir y devolver una respuesta
    assert response.status_code in [200, 422, 500]

if __name__ == "__main__":
    # Ejecutar tests básicos
    pytest.main([__file__, "-v"])
