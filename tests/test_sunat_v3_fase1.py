"""
Tests para funcionalidad SUNAT V3 - Fase 1
"""
import pytest
import asyncio
from datetime import datetime, date
from typing import List

# Importar schemas y servicios SUNAT
from app.modules.accounting.schemas import (
    TipoAsientoSunat,
    EstadoOperacionSunat,
    DetalleAsientoSunatV3,
    AsientoContableSunatV3,
    LibroDiarioSunatV3
)
from app.modules.accounting.sunat_config_service import (
    SunatConfigService,
    SunatLibroConfig
)
from app.modules.accounting.sunat_validator import (
    SunatLibroDiarioValidator,
    SunatValidationResult
)


class TestSunatSchemasV3:
    """Test para schemas SUNAT V3"""
    
    def test_detalle_asiento_sunat_valido(self):
        """Test para schema de detalle asiento válido"""
        detalle = DetalleAsientoSunatV3(
            codigoCuenta="10.1.1.1",
            denominacionCuenta="Caja",
            descripcion="Pago a proveedor",
            debe=1000.0,
            haber=0.0
        )
        
        assert detalle.codigoCuenta == "10.1.1.1"
        assert detalle.debe == 1000.0
        assert detalle.haber == 0.0
    
    def test_detalle_asiento_codigo_invalido(self):
        """Test para código de cuenta inválido"""
        with pytest.raises(ValueError, match="no cumple formato PCGR"):
            DetalleAsientoSunatV3(
                codigoCuenta="10A.1.B",  # Contiene letras
                denominacionCuenta="Cuenta inválida",
                descripcion="Test",
                debe=100.0,
                haber=0.0
            )
    
    def test_detalle_asiento_debe_haber_exclusivos(self):
        """Test para validar que debe y haber sean mutuamente exclusivos"""
        with pytest.raises(ValueError, match="No puede tener valores en Debe y Haber"):
            DetalleAsientoSunatV3(
                codigoCuenta="10.1",
                denominacionCuenta="Cuenta",
                descripcion="Test",
                debe=100.0,
                haber=50.0  # Error: ambos con valor
            )
    
    def test_asiento_contable_sunat_valido(self):
        """Test para asiento contable SUNAT válido"""
        detalles = [
            DetalleAsientoSunatV3(
                codigoCuenta="10.1",
                denominacionCuenta="Caja",
                descripcion="Ingreso",
                debe=1000.0,
                haber=0.0
            ),
            DetalleAsientoSunatV3(
                codigoCuenta="70.1",
                denominacionCuenta="Ventas",
                descripcion="Venta de mercadería",
                debe=0.0,
                haber=1000.0
            )
        ]
        
        asiento = AsientoContableSunatV3(
            numero="1",
            fecha="2024-01-15",
            descripcion="Venta del día",
            detalles=detalles,
            tipoAsiento=TipoAsientoSunat.OPERACION
        )
        
        assert asiento.numero == "1"
        assert len(asiento.detalles) == 2
        assert asiento.tipoAsiento == TipoAsientoSunat.OPERACION
    
    def test_asiento_desbalanceado(self):
        """Test para asiento desbalanceado"""
        detalles = [
            DetalleAsientoSunatV3(
                codigoCuenta="10.1",
                denominacionCuenta="Caja",
                descripcion="Ingreso",
                debe=1000.0,
                haber=0.0
            ),
            DetalleAsientoSunatV3(
                codigoCuenta="70.1",
                denominacionCuenta="Ventas",
                descripcion="Venta",
                debe=0.0,
                haber=800.0  # Desbalanceado: 1000 != 800
            )
        ]
        
        with pytest.raises(ValueError, match="Asiento desbalanceado"):
            AsientoContableSunatV3(
                numero="1",
                fecha="2024-01-15",
                descripcion="Test desbalanceado",
                detalles=detalles
            )
    
    def test_libro_diario_sunat_valido(self):
        """Test para libro diario SUNAT válido"""
        libro = LibroDiarioSunatV3(
            descripcion="Libro Diario Enero 2024",
            periodo="2024-01",
            empresaId="empresa123",
            minDigitosCuenta=3
        )
        
        assert libro.periodo == "2024-01"
        assert libro.minDigitosCuenta == 3
        assert libro.requiereValidacionSunat == True
    
    def test_libro_digitos_minimos_por_ingresos(self):
        """Test para validación de dígitos mínimos según ingresos UIT"""
        with pytest.raises(ValueError, match="mínimo 4 dígitos"):
            LibroDiarioSunatV3(
                descripcion="Libro empresa grande",
                periodo="2024",
                empresaId="empresa456",
                ingresosBrutosAnteriores=500000.0,  # >100 UIT
                minDigitosCuenta=3  # Error: requiere 4
            )


class MockCompanyService:
    """Mock del servicio de empresa para testing"""
    
    async def get_company_by_id(self, empresa_id: str):
        """Mock que retorna empresa de prueba"""
        if empresa_id == "empresa_no_existe":
            return None
        
        return type('MockCompany', (), {
            'ruc': '20123456789',
            'razon_social': 'Empresa de Prueba S.A.C.',
            'fecha_inicio_operaciones': date(2020, 1, 1)
        })()


class TestSunatConfigService:
    """Test para servicio de configuración SUNAT"""
    
    @pytest.fixture
    def config_service(self):
        """Fixture para servicio de configuración"""
        mock_company_service = MockCompanyService()
        return SunatConfigService(mock_company_service)
    
    @pytest.mark.asyncio
    async def test_obtener_configuracion_empresa_valida(self, config_service):
        """Test obtener configuración para empresa válida"""
        config = await config_service.obtener_configuracion_empresa("empresa123")
        
        assert isinstance(config, SunatLibroConfig)
        assert config.empresa_ruc == "20123456789"
        assert config.min_digitos_cuenta >= 3
        assert config.plan_contable_aplicable == "PCGR"
        assert len(config.tipos_asientos_obligatorios) > 0
    
    @pytest.mark.asyncio
    async def test_configuracion_empresa_no_existe(self, config_service):
        """Test para empresa que no existe"""
        with pytest.raises(ValueError, match="no encontrada"):
            await config_service.obtener_configuracion_empresa("empresa_no_existe")
    
    @pytest.mark.asyncio
    async def test_validar_empresa_para_sunat(self, config_service):
        """Test validación de empresa para SUNAT"""
        resultado = await config_service.validar_empresa_para_sunat("empresa123")
        
        assert isinstance(resultado, dict)
        assert "es_valida" in resultado
        assert "errores" in resultado
        assert "warnings" in resultado
        assert "recomendaciones" in resultado
    
    @pytest.mark.asyncio
    async def test_obtener_reglas_validacion(self, config_service):
        """Test obtener reglas de validación"""
        reglas = await config_service.obtener_reglas_validacion("empresa123")
        
        assert isinstance(reglas, list)
        assert len(reglas) > 0
        
        # Verificar que todas las reglas tienen campos requeridos
        for regla in reglas:
            assert hasattr(regla, 'nombre')
            assert hasattr(regla, 'descripcion')
            assert hasattr(regla, 'es_obligatoria')
            assert hasattr(regla, 'mensaje_error')


class TestSunatValidator:
    """Test para validador SUNAT"""
    
    @pytest.fixture
    def validator(self):
        """Fixture para validador SUNAT"""
        mock_company_service = MockCompanyService()
        config_service = SunatConfigService(mock_company_service)
        return SunatLibroDiarioValidator(config_service)
    
    def crear_asiento_valido(self, numero="1") -> AsientoContableSunatV3:
        """Crear asiento válido para testing"""
        detalles = [
            DetalleAsientoSunatV3(
                codigoCuenta="10.1.1",
                denominacionCuenta="Caja",
                descripcion="Ingreso efectivo",
                debe=1000.0,
                haber=0.0
            ),
            DetalleAsientoSunatV3(
                codigoCuenta="70.1.1",
                denominacionCuenta="Ventas gravadas",
                descripcion="Venta productos",
                debe=0.0,
                haber=1000.0
            )
        ]
        
        return AsientoContableSunatV3(
            numero=numero,
            fecha="2024-01-15",
            descripcion="Venta del día",
            detalles=detalles,
            tipoAsiento=TipoAsientoSunat.OPERACION
        )
    
    def crear_libro_valido(self) -> LibroDiarioSunatV3:
        """Crear libro diario válido para testing"""
        return LibroDiarioSunatV3(
            descripcion="Libro Diario Enero 2024",
            periodo="2024-01",
            empresaId="empresa123",
            minDigitosCuenta=3
        )
    
    @pytest.mark.asyncio
    async def test_validar_asiento_individual_valido(self, validator):
        """Test validar asiento individual válido"""
        asiento = self.crear_asiento_valido()
        resultado = await validator.validar_asiento_individual(asiento, "empresa123")
        
        assert isinstance(resultado, SunatValidationResult)
        assert resultado.es_valido == True
        assert len(resultado.errores) == 0
    
    @pytest.mark.asyncio
    async def test_validar_libro_completo_valido(self, validator):
        """Test validar libro completo válido"""
        libro = self.crear_libro_valido()
        asientos = [
            self.crear_asiento_valido("1"),
            self.crear_asiento_valido("2")
        ]
        
        resultado = await validator.validar_libro_completo(libro, asientos)
        
        assert isinstance(resultado, SunatValidationResult)
        assert len(resultado.errores) == 0  # Puede tener warnings pero no errores
        assert resultado.tiempo_validacion is not None
    
    @pytest.mark.asyncio
    async def test_validar_correlatividad_con_saltos(self, validator):
        """Test validar correlatividad con saltos"""
        libro = self.crear_libro_valido()
        asientos = [
            self.crear_asiento_valido("1"),
            self.crear_asiento_valido("3"),  # Salto: falta el 2
            self.crear_asiento_valido("4")
        ]
        
        resultado = await validator.validar_libro_completo(libro, asientos)
        
        assert resultado.es_valido == False
        assert any("correlatividad" in error.lower() for error in resultado.errores)
    
    @pytest.mark.asyncio
    async def test_validar_libro_sin_asientos(self, validator):
        """Test validar libro sin asientos"""
        libro = self.crear_libro_valido()
        asientos = []
        
        resultado = await validator.validar_libro_completo(libro, asientos)
        
        assert resultado.es_valido == False
        assert any("al menos un asiento" in error.lower() for error in resultado.errores)
    
    @pytest.mark.asyncio
    async def test_validacion_resultado_metodos(self, validator):
        """Test métodos del resultado de validación"""
        resultado = SunatValidationResult()
        
        # Test agregar errores
        resultado.agregar_error("Error de prueba", "regla_test")
        assert not resultado.es_valido
        assert len(resultado.errores) == 1
        
        # Test agregar warnings
        resultado.agregar_warning("Warning de prueba", "regla_warning")
        assert len(resultado.warnings) == 1
        
        # Test puede enviar SUNAT
        assert not resultado.puede_enviar_sunat()  # Tiene errores y warnings
        
        # Test resumen
        resumen = resultado.resumen()
        assert resumen["es_valido"] == False
        assert resumen["total_errores"] == 1
        assert resumen["total_warnings"] == 1


@pytest.mark.integration
class TestIntegracionSunatCompleta:
    """Tests de integración completa para funcionalidad SUNAT"""
    
    @pytest.mark.asyncio
    async def test_flujo_completo_validacion_sunat(self):
        """Test del flujo completo: configuración -> validación -> resultado"""
        # 1. Crear servicios
        mock_company_service = MockCompanyService()
        config_service = SunatConfigService(mock_company_service)
        validator = SunatLibroDiarioValidator(config_service)
        
        # 2. Obtener configuración
        config = await config_service.obtener_configuracion_empresa("empresa123")
        assert config.empresa_ruc == "20123456789"
        
        # 3. Crear libro y asientos de prueba
        libro = LibroDiarioSunatV3(
            descripcion="Libro de prueba integración",
            periodo="2024-01",
            empresaId="empresa123",
            minDigitosCuenta=config.min_digitos_cuenta
        )
        
        asientos = []
        for i in range(1, 6):  # 5 asientos de prueba
            detalles = [
                DetalleAsientoSunatV3(
                    codigoCuenta=f"10.{i}",
                    denominacionCuenta=f"Cuenta {i}",
                    descripcion=f"Operación {i}",
                    debe=1000.0 * i,
                    haber=0.0
                ),
                DetalleAsientoSunatV3(
                    codigoCuenta=f"70.{i}",
                    denominacionCuenta=f"Venta {i}",
                    descripcion=f"Ingreso {i}",
                    debe=0.0,
                    haber=1000.0 * i
                )
            ]
            
            asiento = AsientoContableSunatV3(
                numero=str(i),
                fecha=f"2024-01-{i:02d}",
                descripcion=f"Asiento número {i}",
                detalles=detalles,
                tipoAsiento=TipoAsientoSunat.OPERACION
            )
            asientos.append(asiento)
        
        # 4. Ejecutar validación completa
        resultado = await validator.validar_libro_completo(libro, asientos)
        
        # 5. Verificar resultado
        assert isinstance(resultado, SunatValidationResult)
        assert resultado.tiempo_validacion is not None
        assert "configuracion_sunat" in resultado.detalles_validacion
        
        # 6. Verificar resumen
        resumen = resultado.resumen()
        assert "es_valido" in resumen
        assert "puede_enviar_sunat" in resumen
        assert "total_errores" in resumen
        assert "total_warnings" in resumen
        
        print(f"✅ Validación completa:")
        print(f"   - Válido: {resultado.es_valido}")
        print(f"   - Puede enviar SUNAT: {resultado.puede_enviar_sunat()}")
        print(f"   - Errores: {len(resultado.errores)}")
        print(f"   - Warnings: {len(resultado.warnings)}")
        print(f"   - Tiempo: {resultado.tiempo_validacion}")


if __name__ == "__main__":
    # Ejecutar tests básicos
    print("🚀 Ejecutando tests SUNAT V3 - Fase 1...")
    
    # Test rápido de schemas
    print("\n📋 Testing schemas...")
    try:
        detalle1 = DetalleAsientoSunatV3(
            codigoCuenta="10.1.1",
            denominacionCuenta="Caja",
            descripcion="Ingreso",
            debe=100.0,
            haber=0.0
        )
        
        detalle2 = DetalleAsientoSunatV3(
            codigoCuenta="70.1.1",
            denominacionCuenta="Ventas",
            descripcion="Venta",
            debe=0.0,
            haber=100.0  # Balance correcto
        )
        print("✅ Schema DetalleAsientoSunatV3: OK")
        
        asiento = AsientoContableSunatV3(
            numero="1",
            fecha="2024-01-15",
            descripcion="Test asiento",
            detalles=[detalle1, detalle2]  # Balanceado: 100 debe = 100 haber
        )
        print("✅ Schema AsientoContableSunatV3: OK")
        
        libro = LibroDiarioSunatV3(
            descripcion="Test libro",
            periodo="2024-01",
            empresaId="test123"
        )
        print("✅ Schema LibroDiarioSunatV3: OK")
        
    except Exception as e:
        print(f"❌ Error en schemas: {e}")
    
    print("\n✅ Tests básicos completados. Para tests completos ejecutar con pytest.")
    print("   Comando: pytest test_sunat_v3_fase1.py -v")
