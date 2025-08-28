"""
Test de compatibilidad de datos reales con esquemas PLE Libro Mayor
Autor: Sistema ERP  
Fecha: 2025-08-27
Propósito: Validar que los datos reales sean compatibles con esquemas PLE
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from pymongo import MongoClient
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from app.modules.accounting.services.data_adapter import DataAdapterMayor
from app.modules.accounting.schemas.schemas_mayor import LibroMayorPLE


class TestCompatibilidadDatos:
    """Test de compatibilidad de datos reales"""
    
    @classmethod
    def setup_class(cls):
        """Configuración inicial del test"""
        cls.client = MongoClient('mongodb://localhost:27017/')
        cls.db = cls.client['erp_db']
        cls.adapter = DataAdapterMayor()
        
        # Obtener datos reales
        cls.asientos_reales = list(cls.db.asientos_contables.find())
        cls.empresas = list(cls.db.companies.find({'activa': True}))
        
        print(f"\n🔍 Datos cargados:")
        print(f"   - Asientos contables: {len(cls.asientos_reales)}")
        print(f"   - Empresas activas: {len(cls.empresas)}")
    
    def test_01_validar_estructura_asientos(self):
        """Test 1: Validar estructura de asientos contables"""
        print(f"\n📋 TEST 1: Validando estructura de {len(self.asientos_reales)} asientos...")
        
        # Validar que hay asientos
        assert len(self.asientos_reales) > 0, "No hay asientos contables en la base de datos"
        
        # Validar compatibilidad
        reporte = self.adapter.validar_compatibilidad(self.asientos_reales)
        
        print(f"   ✓ Total asientos: {reporte['total_asientos']}")
        print(f"   ✓ Campos requeridos presentes: {reporte['campos_requeridos_presentes']}")
        print(f"   ✓ Compatibilidad: {reporte['compatibilidad']:.1f}%")
        
        if reporte['errores']:
            print("   ⚠️  Errores encontrados:")
            for error in reporte['errores'][:3]:  # Mostrar solo los primeros 3
                print(f"      - {error}")
        
        if reporte['advertencias']:
            print("   ⚠️  Advertencias:")
            for advertencia in reporte['advertencias'][:3]:
                print(f"      - {advertencia}")
        
        # Debe tener al menos 70% de compatibilidad
        assert reporte['compatibilidad'] >= 70.0, f"Compatibilidad muy baja: {reporte['compatibilidad']:.1f}%"
    
    def test_02_convertir_asiento_individual(self):
        """Test 2: Convertir un asiento individual a Libro Mayor"""
        print(f"\n🔄 TEST 2: Convirtiendo asiento individual...")
        
        assert len(self.asientos_reales) > 0, "No hay asientos para convertir"
        assert len(self.empresas) > 0, "No hay empresas para usar"
        
        # Tomar primer asiento y primera empresa
        asiento = self.asientos_reales[0]
        empresa = self.empresas[0]
        empresa_ruc = empresa.get('ruc', '20123456789')
        periodo = "20250800"  # Agosto 2025
        
        print(f"   📄 Asiento: {asiento.get('numeroCorrelativo', 'N/A')}")
        print(f"   🏢 Empresa: {empresa_ruc}")
        print(f"   📅 Periodo: {periodo}")
        
        # Convertir
        try:
            libro_mayor = self.adapter.convertir_asiento_a_libro_mayor(
                asiento, empresa_ruc, periodo
            )
            
            print(f"   ✓ Conversión exitosa")
            print(f"   ✓ CUO generado: {libro_mayor.codigo_unico_operacion}")
            print(f"   ✓ Cuenta: {libro_mayor.codigo_cuenta_contable}")
            print(f"   ✓ Debe: {libro_mayor.movimiento_debe}")
            print(f"   ✓ Haber: {libro_mayor.movimiento_haber}")
            
            # Validaciones básicas
            assert isinstance(libro_mayor, LibroMayorPLE), "El resultado no es LibroMayorPLE"
            assert libro_mayor.periodo == periodo, "Periodo incorrecto"
            assert libro_mayor.numero_documento_identidad == empresa_ruc, "RUC incorrecto"
            assert len(libro_mayor.codigo_unico_operacion) > 0, "CUO vacío"
            
        except Exception as e:
            pytest.fail(f"Error al convertir asiento: {str(e)}")
    
    def test_03_convertir_lista_completa(self):
        """Test 3: Convertir lista completa de asientos"""
        print(f"\n📋 TEST 3: Convirtiendo lista completa...")
        
        assert len(self.empresas) > 0, "No hay empresas disponibles"
        
        empresa = self.empresas[0]
        empresa_ruc = empresa.get('ruc', '20123456789')
        periodo = "20250800"
        
        print(f"   📊 Convirtiendo {len(self.asientos_reales)} asientos...")
        
        # Convertir lista completa
        try:
            libros_mayor = self.adapter.convertir_lista_asientos(
                self.asientos_reales, empresa_ruc, periodo
            )
            
            print(f"   ✓ Conversiones exitosas: {len(libros_mayor)}")
            print(f"   ✓ Porcentaje de éxito: {(len(libros_mayor)/len(self.asientos_reales))*100:.1f}%")
            
            # Validaciones
            assert len(libros_mayor) > 0, "No se convirtió ningún asiento"
            assert len(libros_mayor) <= len(self.asientos_reales), "Más conversiones que asientos originales"
            
            # Validar algunos campos de los primeros registros
            for i, libro in enumerate(libros_mayor[:3]):
                print(f"   📄 Libro {i+1}: CUO={libro.codigo_unico_operacion}, Cuenta={libro.codigo_cuenta_contable}")
                assert isinstance(libro, LibroMayorPLE), f"Registro {i+1} no es LibroMayorPLE"
                assert libro.periodo == periodo, f"Periodo incorrecto en registro {i+1}"
            
        except Exception as e:
            pytest.fail(f"Error al convertir lista: {str(e)}")
    
    def test_04_validar_campos_sunat(self):
        """Test 4: Validar campos específicos de SUNAT"""
        print(f"\n🏛️  TEST 4: Validando campos SUNAT...")
        
        assert len(self.asientos_reales) > 0 and len(self.empresas) > 0
        
        asiento = self.asientos_reales[0]
        empresa = self.empresas[0]
        empresa_ruc = empresa.get('ruc', '20123456789')
        periodo = "20250800"
        
        libro_mayor = self.adapter.convertir_asiento_a_libro_mayor(
            asiento, empresa_ruc, periodo
        )
        
        # Validaciones SUNAT específicas
        print(f"   📋 Validando formato SUNAT...")
        
        # Periodo: YYYYMM00
        assert len(libro_mayor.periodo) == 8, f"Periodo debe tener 8 dígitos: {libro_mayor.periodo}"
        assert libro_mayor.periodo.endswith('00'), f"Periodo debe terminar en 00: {libro_mayor.periodo}"
        
        # CUO: mínimo 1 carácter
        assert len(libro_mayor.codigo_unico_operacion) >= 1, "CUO muy corto"
        
        # Fecha contable: debe ser date
        assert isinstance(libro_mayor.fecha_contable, date), "Fecha contable debe ser tipo date"
        
        # Movimientos: deben ser Decimal
        assert isinstance(libro_mayor.movimiento_debe, Decimal), "Debe debe ser Decimal"
        assert isinstance(libro_mayor.movimiento_haber, Decimal), "Haber debe ser Decimal"
        
        # Saldos: coherencia
        if libro_mayor.saldo_deudor > 0:
            assert libro_mayor.saldo_acreedor == 0, "No puede tener saldo deudor y acreedor al mismo tiempo"
        if libro_mayor.saldo_acreedor > 0:
            assert libro_mayor.saldo_deudor == 0, "No puede tener saldo deudor y acreedor al mismo tiempo"
        
        print(f"   ✓ Formato SUNAT válido")
        print(f"   ✓ Periodo: {libro_mayor.periodo}")
        print(f"   ✓ CUO: {libro_mayor.codigo_unico_operacion}")
        print(f"   ✓ Fecha: {libro_mayor.fecha_contable}")
        print(f"   ✓ Saldo deudor: {libro_mayor.saldo_deudor}")
        print(f"   ✓ Saldo acreedor: {libro_mayor.saldo_acreedor}")
    
    def test_05_mapeo_tipos_cuenta(self):
        """Test 5: Validar mapeo de tipos de cuenta"""
        print(f"\n🗂️  TEST 5: Validando mapeo de tipos de cuenta...")
        
        # Obtener códigos de cuenta únicos de los asientos
        codigos_cuenta = set()
        for asiento in self.asientos_reales:
            cuenta = asiento.get('cuentaContable', {})
            codigo = cuenta.get('codigo', '')
            if codigo:
                codigos_cuenta.add(codigo)
        
        print(f"   📊 Códigos de cuenta únicos encontrados: {len(codigos_cuenta)}")
        
        # Validar mapeo para cada código
        for codigo in codigos_cuenta:
            tipo_cuenta = self.adapter._determinar_tipo_cuenta(codigo)
            primer_digito = codigo[0] if codigo else ''
            
            print(f"   🔖 Cuenta {codigo}: {tipo_cuenta.value} (dígito {primer_digito})")
            
            # El tipo debe estar en los enums válidos
            assert hasattr(tipo_cuenta, 'value'), f"Tipo de cuenta inválido para {codigo}"
            assert len(tipo_cuenta.value) > 0, f"Tipo de cuenta vacío para {codigo}"
    
    @classmethod
    def teardown_class(cls):
        """Limpieza final"""
        if hasattr(cls, 'client'):
            cls.client.close()
        print(f"\n🏁 Tests completados - Conexión cerrada")


def main():
    """Ejecutar tests de compatibilidad directamente"""
    print("=" * 60)
    print("🔍 EJECUTANDO TESTS DE COMPATIBILIDAD DE DATOS")
    print("=" * 60)
    
    # Ejecutar tests
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
