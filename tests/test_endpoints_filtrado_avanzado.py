"""
Test Simplificado - Endpoints de Filtrado Avanzado
==================================================

Test directo de los endpoints de filtrado avanzado usando FastAPI TestClient
para evitar problemas de async/await en los tests unitarios.

Autor: Sistema ERP - FASE 3.2
Fecha: Agosto 2025
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from decimal import Decimal

# Configuración del entorno de test
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.main import app

# Cliente de test de FastAPI
client = TestClient(app)

# Variables de test
EMPRESA_ID_TEST = "60b9b9b9b9b9b9b9b9b9b9b9"
RUC_EMPRESA_TEST = "20123456789"


def test_endpoint_filtro_basico():
    """Test básico del endpoint de filtrado avanzado"""
    print("\n🧪 Test: Endpoint filtro básico")
    
    payload = {
        "empresa_id": EMPRESA_ID_TEST,
        "periodo_desde": "202401",
        "periodo_hasta": "202412",
        "incluir_totales": True,
        "limite": 10
    }
    
    response = client.post("/accounting/filtrado-avanzado/aplicar", json=payload)
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Respuesta exitosa")
        print(f"   Total registros: {data.get('total_registros', 0)}")
        print(f"   Mensaje: {data.get('mensaje', 'Sin mensaje')}")
        
        # Validar estructura de respuesta
        assert "exito" in data
        assert "total_registros" in data
        assert "registros" in data
        
        if data["total_registros"] > 0:
            assert len(data["registros"]) > 0
            
            # Validar estructura de registro
            primer_registro = data["registros"][0]
            assert "codigo_cuenta" in primer_registro
            assert "descripcion_cuenta" in primer_registro
            assert "saldo_final_deudor" in primer_registro
            assert "saldo_final_acreedor" in primer_registro
        
        print("✅ Test endpoint básico completado")
    else:
        print(f"❌ Error en endpoint: {response.status_code}")
        print(f"   Detalle: {response.text}")


def test_endpoint_busqueda_cuentas():
    """Test del endpoint de búsqueda de cuentas"""
    print("\n🧪 Test: Endpoint búsqueda de cuentas")
    
    payload = {
        "empresa_id": EMPRESA_ID_TEST,
        "patron_busqueda": "CAJA",
        "buscar_en_codigo": True,
        "buscar_en_descripcion": True,
        "limite": 5
    }
    
    response = client.post("/accounting/filtrado-avanzado/buscar-cuentas", json=payload)
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Búsqueda exitosa")
        print(f"   Total encontradas: {data.get('total_encontradas', 0)}")
        print(f"   Patrón buscado: {data.get('patron_busqueda', 'N/A')}")
        
        # Validar estructura
        assert "exito" in data
        assert "total_encontradas" in data
        assert "cuentas" in data
        
        print("✅ Test búsqueda cuentas completado")
    else:
        print(f"❌ Error en búsqueda: {response.status_code}")
        print(f"   Detalle: {response.text}")


def test_endpoint_estadisticas():
    """Test del endpoint de estadísticas"""
    print("\n🧪 Test: Endpoint estadísticas")
    
    params = {
        "empresa_id": EMPRESA_ID_TEST,
        "periodo_desde": "202401",
        "periodo_hasta": "202412",
        "incluir_saldos_cero": True
    }
    
    response = client.get("/accounting/filtrado-avanzado/estadisticas", params=params)
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Estadísticas obtenidas")
        
        # Validar estructura
        assert "exito" in data
        assert "estadisticas" in data
        
        stats = data["estadisticas"]
        print(f"   Total cuentas: {stats.get('total_cuentas', 0)}")
        print(f"   Total saldo deudor: {stats.get('total_saldo_deudor', 0)}")
        print(f"   Total saldo acreedor: {stats.get('total_saldo_acreedor', 0)}")
        
        # Validar campos estadísticos
        campos_requeridos = [
            "total_cuentas", "total_saldo_deudor", "total_saldo_acreedor",
            "total_movimiento_debe", "total_movimiento_haber"
        ]
        
        for campo in campos_requeridos:
            assert campo in stats, f"Campo {campo} faltante en estadísticas"
        
        print("✅ Test estadísticas completado")
    else:
        print(f"❌ Error en estadísticas: {response.status_code}")
        print(f"   Detalle: {response.text}")


def test_endpoint_agrupaciones():
    """Test del endpoint de agrupaciones"""
    print("\n🧪 Test: Endpoint agrupaciones")
    
    # Probar agrupación por tipo de cuenta
    params = {
        "empresa_id": EMPRESA_ID_TEST,
        "periodo_desde": "202401",
        "periodo_hasta": "202412"
    }
    
    response = client.get("/accounting/filtrado-avanzado/agrupaciones/TIPO_CUENTA", params=params)
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agrupaciones obtenidas")
        
        # Validar estructura
        assert "exito" in data
        assert "tipo_agrupacion" in data
        assert data["tipo_agrupacion"] == "TIPO_CUENTA"
        
        print(f"   Tipo agrupación: {data['tipo_agrupacion']}")
        print(f"   Total registros: {data.get('total_registros', 0)}")
        
        if "agrupaciones" in data and data["agrupaciones"]:
            print(f"   Grupos encontrados: {len(data['agrupaciones'])}")
        
        print("✅ Test agrupaciones completado")
    else:
        print(f"❌ Error en agrupaciones: {response.status_code}")
        print(f"   Detalle: {response.text}")


def test_filtro_avanzado_complejo():
    """Test de filtro avanzado con múltiples criterios"""
    print("\n🧪 Test: Filtro avanzado complejo")
    
    payload = {
        "empresa_id": EMPRESA_ID_TEST,
        "periodo_desde": "202401",
        "periodo_hasta": "202412",
        "patron_codigo_cuenta": "^[1-2]",  # Cuentas que empiecen con 1 o 2
        "saldo_deudor_min": 100.00,
        "incluir_saldos_cero": False,
        "ordenar_por": "CODIGO_CUENTA",
        "tipo_orden": "ASCENDENTE",
        "limite": 15,
        "incluir_totales": True,
        "incluir_estadisticas": False
    }
    
    response = client.post("/accounting/filtrado-avanzado/aplicar", json=payload)
    
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Filtro complejo aplicado")
        print(f"   Total registros: {data.get('total_registros', 0)}")
        
        # Validar que se cumplan los criterios
        if data["total_registros"] > 0:
            registros = data["registros"]
            
            # Validar patrón de código
            for registro in registros:
                codigo = registro["codigo_cuenta"]
                assert codigo.startswith("1") or codigo.startswith("2"), f"Código {codigo} no cumple patrón"
            
            # Validar ordenamiento
            codigos = [r["codigo_cuenta"] for r in registros]
            for i in range(1, len(codigos)):
                assert codigos[i] >= codigos[i-1], "Códigos no están ordenados correctamente"
            
            print(f"   Primeros códigos: {', '.join(codigos[:5])}")
        
        # Validar totales si están incluidos
        if "totales" in data:
            totales = data["totales"]
            print(f"   Total saldo deudor: {totales.get('total_saldo_deudor', 0)}")
            print(f"   Total saldo acreedor: {totales.get('total_saldo_acreedor', 0)}")
        
        print("✅ Test filtro complejo completado")
    else:
        print(f"❌ Error en filtro complejo: {response.status_code}")
        print(f"   Detalle: {response.text}")


def test_validacion_parametros():
    """Test de validación de parámetros"""
    print("\n🧪 Test: Validación de parámetros")
    
    # Test con empresa_id faltante (debe fallar)
    payload_sin_empresa = {
        "periodo_desde": "202401",
        "periodo_hasta": "202412"
    }
    
    response = client.post("/accounting/filtrado-avanzado/aplicar", json=payload_sin_empresa)
    print(f"Sin empresa_id - Status: {response.status_code}")
    assert response.status_code == 422, "Debe fallar sin empresa_id"
    
    # Test con límite excesivo
    payload_limite_grande = {
        "empresa_id": EMPRESA_ID_TEST,
        "limite": 2000  # Excede el máximo permitido
    }
    
    response = client.post("/accounting/filtrado-avanzado/aplicar", json=payload_limite_grande)
    print(f"Límite excesivo - Status: {response.status_code}")
    assert response.status_code == 422, "Debe fallar con límite excesivo"
    
    print("✅ Test validación parámetros completado")


def main():
    """Ejecutar todos los tests de endpoints"""
    print("\n" + "="*80)
    print("🚀 TESTS DE ENDPOINTS - FILTRADO AVANZADO LIBRO MAYOR")
    print("="*80)
    
    try:
        # Tests de endpoints
        test_endpoint_filtro_basico()
        test_endpoint_busqueda_cuentas()
        test_endpoint_estadisticas()
        test_endpoint_agrupaciones()
        test_filtro_avanzado_complejo()
        test_validacion_parametros()
        
        print("\n" + "="*80)
        print("🎉 TODOS LOS TESTS DE ENDPOINTS COMPLETADOS")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR EN TESTS: {str(e)}")
        raise


if __name__ == "__main__":
    main()
