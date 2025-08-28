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
client = TestClient(app)

class TestEndpointsLibroMayor:
    """Test de endpoints de Libro Mayor"""
    
    @classmethod
    def setup_class(cls):
        """Configuración inicial"""
        cls.empresa_ruc = "20611554282"
        cls.empresa_id = "empresa_demo"
        cls.periodo = "202508"
        
    def test_01_endpoint_validar_compatibilidad(self):
        """Test 1: Endpoint de validación de compatibilidad"""
        print(f"\n🔗 TEST 1: Endpoint validar compatibilidad...")
        
        response = client.get(
            f"/accounting/libro-mayor/validar-compatibilidad-datos-reales",
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
            f"/accounting/libro-mayor/generar-ple-datos-reales",
            json={
                "empresa_id": self.empresa_id,
                "empresa_ruc": self.empresa_ruc,
                "periodo_aaaamm": self.periodo,
                "correlativo": "001"
            }
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
            assert 'contenido_archivo' in data
        
        print(f"   🏁 Test endpoint completado")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
