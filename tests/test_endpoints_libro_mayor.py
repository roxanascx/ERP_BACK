"""
Test de Endpoints - Libro Mayor PLE 050200
==========================================

Test rápido para verificar que los endpoints del Libro Mayor
funcionen correctamente con datos reales.

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_database

# Configuración de test
# Las rutas se montan bajo /api/v1. Sin el prefijo, TestClient devolvia 404
# y el test culpaba al endpoint en vez de a su propia URL.
client = TestClient(app)

class TestEndpointsLibroMayor:
    """Test de endpoints de Libro Mayor"""
    
    @classmethod
    def setup_class(cls):
        """Configuración inicial"""
        # Salen de los asientos que hay en la base. Estaban cableados a una
        # empresa y un periodo de 2025 que ya no existen, asi que el endpoint
        # respondia bien pero sobre cero registros.
        from pymongo import MongoClient

        from app.config import settings

        db = MongoClient(settings.MONGODB_URL)[settings.DATABASE_NAME]
        muestra = db.asientos_contables.find_one({"empresaId": {"$ne": None}})

        if not muestra:
            pytest.skip("No hay asientos contables para probar los endpoints")

        cls.empresa_id = muestra["empresaId"]
        cls.empresa_ruc = muestra["empresaId"]
        cls.periodo = (muestra.get("fecha") or "")[:7].replace("-", "") or "202606"
        
    def test_01_endpoint_validar_compatibilidad(self):
        """Test 1: Endpoint de validación de compatibilidad"""
        print(f"\n🔗 TEST 1: Endpoint validar compatibilidad...")
        
        response = client.get(
            f"/api/v1/accounting/libro-mayor/validar-compatibilidad-datos-reales",
            params={
                "empresa_id": self.empresa_id,
                "empresa_ruc": self.empresa_ruc
            }
        )
        
        print(f"   📡 Status: {response.status_code}")
        assert response.status_code == 200, f"Error en endpoint: {response.text}"
        
        data = response.json()
        print(f"   ✓ Compatibilidad: {data.get('compatibilidad_porcentaje', 0)}%")
        print(f"   ✓ Total asientos: {data.get('total_asientos', 0)}")
        
        assert 'compatibilidad_porcentaje' in data
        assert data['total_asientos'] > 0
    
    def test_02_endpoint_generar_ple(self):
        """Test 2: Endpoint de generación de PLE"""
        print(f"\n📄 TEST 2: Endpoint generar PLE...")
        
        response = client.post(
            f"/api/v1/accounting/libro-mayor/generar-ple-datos-reales",
            params={
                "empresa_id": self.empresa_id,
                "empresa_ruc": self.empresa_ruc,
                "periodo_aaaamm": self.periodo,
                "correlativo": "001",
            },
        )
        
        print(f"   📡 Status: {response.status_code}")
        assert response.status_code == 200, f"Error en endpoint: {response.text}"
        
        data = response.json()
        print(f"   ✓ Archivo generado: {data.get('archivo_generado', False)}")
        
        if data.get('archivo_generado'):
            print(f"   ✓ Nombre: {data.get('nombre_archivo', 'N/A')}")
            print(f"   ✓ Registros: {data.get('total_registros', 0)}")
            print(f"   ✓ Validación SUNAT: {data.get('validacion', {}).get('es_valido', False)}")
            
            assert data['archivo_generado'] == True
            assert data['total_registros'] > 0
            # La ruta devuelve un extracto, no el archivo entero: para bajarlo
            # hay que pedirlo con generar_archivo_fisico=true.
            assert 'preview_contenido' in data
        
        print(f"   🏁 Test endpoint completado")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
