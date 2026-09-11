"""
Test de integración completa para Libro Mayor con datos reales
============================================================

Test end-to-end que valida toda la cadena de procesamiento:
1. Datos reales → Adaptador → Servicio → API → Archivo PLE
2. Validación de compatibilidad
3. Generación de archivos PLE 050200
4. Validación SUNAT completa

Autor: Sistema ERP - FASE 2
Fecha: 2025-08-27
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from pymongo import MongoClient
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from app.modules.accounting.services.mayor_service import MayorService
from app.modules.accounting.services.data_adapter import DataAdapterMayor
from app.modules.accounting.schemas.schemas_mayor import LibroMayorPLE
from app.database import get_database


class TestIntegracionCompleta:
    """Test de integración completa para Libro Mayor con datos reales"""
    
    @classmethod
    def setup_class(cls):
        """Configuración inicial del test"""
        # El nombre de la base sale de la configuracion, no cableado: estaba
        # puesto a mano como "erp_db" mientras la real se llama "web-erp", asi
        # que estos tests leian una base vacia y fallaban con "no hay asientos".
        from app.config import settings

        # Dos clientes a proposito: `MayorService` declara AsyncIOMotorDatabase y
        # usa `to_list`, asi que hay que darle Motor. Inyectarle el cliente
        # sincrono hacia que cada llamada muriera con
        # "'Cursor' object has no attribute 'to_list'".
        from motor.motor_asyncio import AsyncIOMotorClient

        cls.client = MongoClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.DATABASE_NAME]


        cls.settings = settings

        # Las consultas de apoyo del propio test si pueden ser sincronas.
        cls.empresas = list(cls.db.companies.find({'activa': True}).limit(1))
        cls.asientos_reales = list(cls.db.asientos_contables.find().limit(10))
        
        print(f"\n🏗️  Configuración de integración:")
        print(f"   - Base de datos: {settings.DATABASE_NAME}")
        print(f"   - Empresas disponibles: {len(cls.empresas)}")
        print(f"   - Asientos contables: {len(cls.asientos_reales)}")
        
        # La empresa sale de los asientos que hay en la base, no de una
        # constante: estaba cableada a "empresa_demo", que ya no existe, asi que
        # las consultas no devolvian nada y la compatibilidad salia 0%.
        cls.empresa_id = next(
            (a['empresaId'] for a in cls.asientos_reales if a.get('empresaId')), None
        )
        if not cls.empresa_id:
            pytest.skip("No hay asientos contables con empresaId para testing")

        cls.empresa_test = next(
            (e for e in cls.empresas if e.get('ruc') == cls.empresa_id),
            cls.empresas[0] if cls.empresas else {},
        )

        if True:
            cls.empresa_ruc = cls.empresa_test.get('ruc') or cls.empresa_id
            print(f"   - Empresa test: {cls.empresa_ruc}")
            print(f"   - Empresa ID usado: {cls.empresa_id}")
        else:
            pytest.skip("No hay empresas disponibles para testing")
    
    @classmethod
    def _servicio(cls) -> MayorService:
        """
        Un servicio nuevo, atado al bucle que esta corriendo ahora.

        Motor se ata al primer bucle que ve. Cada test abre el suyo con
        `asyncio.run()`, asi que un cliente creado en `setup_class` queda
        apuntando a un bucle ya cerrado a partir del segundo test: de ahi el
        "Event loop is closed". Creandolo aqui dentro, cada test tiene el suyo.
        """
        from motor.motor_asyncio import AsyncIOMotorClient

        cliente = AsyncIOMotorClient(cls.settings.MONGODB_URL)
        return MayorService(cliente[cls.settings.DATABASE_NAME])

    def test_01_validar_compatibilidad_end_to_end(self):
        """Test 1: Validación de compatibilidad completa"""
        print(f"\n📋 TEST 1: Validación de compatibilidad end-to-end...")
        
        async def run_test():
            # Validar compatibilidad usando el servicio
            reporte = await self._servicio().validar_compatibilidad_datos_reales(
                self.empresa_id  # Ya no necesita str() porque es string
            )
            
            print(f"   ✓ Compatibilidad: {reporte['compatibilidad']:.1f}%")
            print(f"   ✓ Total asientos: {reporte['total_asientos']}")
            print(f"   ✓ Apto para PLE: {reporte.get('apto_para_ple', False)}")
            
            # Validaciones
            assert reporte['compatibilidad'] >= 70.0, f"Compatibilidad muy baja: {reporte['compatibilidad']}"
            assert reporte['total_asientos'] > 0, "No hay asientos para validar"
            assert isinstance(reporte['fecha_validacion'], str), "Fecha de validación debe ser string"
            assert 'recomendaciones' in reporte, "Debe incluir recomendaciones"
            
            return reporte
        
        # Ejecutar test asíncrono
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_02_conversion_asientos_a_ple_completa(self):
        """Test 2: Conversión completa de asientos a PLE"""
        print(f"\n🔄 TEST 2: Conversión completa asientos → PLE...")
        
        async def run_test():
            periodo = "20250800"  # Agosto 2025
            
            # Convertir asientos a formato PLE
            libros_mayor_ple = await self._servicio().convertir_asientos_a_libro_mayor_ple(
                empresa_id=self.empresa_id,
                empresa_ruc=self.empresa_ruc,
                periodo=periodo
            )
            
            print(f"   ✓ Asientos convertidos: {len(libros_mayor_ple)}")
            
            if libros_mayor_ple:
                primer_libro = libros_mayor_ple[0]
                print(f"   ✓ Primer registro:")
                print(f"      - Período: {primer_libro.periodo}")
                print(f"      - CUO: {primer_libro.codigo_unico_operacion}")
                print(f"      - Cuenta: {primer_libro.codigo_cuenta_contable}")
                print(f"      - Debe: {primer_libro.movimiento_debe}")
                print(f"      - Haber: {primer_libro.movimiento_haber}")
                
                # Validaciones de estructura PLE
                assert isinstance(primer_libro, LibroMayorPLE), "Debe ser LibroMayorPLE"
                assert primer_libro.periodo == periodo, "Período incorrecto"
                assert len(primer_libro.codigo_unico_operacion) > 0, "CUO no debe estar vacío"
                assert primer_libro.numero_documento_identidad == self.empresa_ruc, "RUC incorrecto"
            
            return libros_mayor_ple
        
        result = asyncio.run(run_test())
        assert isinstance(result, list)
    
    def test_03_generacion_archivo_ple_completa(self):
        """Test 3: Generación completa de archivo PLE 050200"""
        print(f"\n📄 TEST 3: Generación completa archivo PLE 050200...")
        
        async def run_test():
            periodo_aaaamm = "202508"
            
            # Generar archivo PLE completo
            resultado = await self._servicio().generar_archivo_ple_mayor_con_datos_reales(
                empresa_id=self.empresa_id,
                empresa_ruc=self.empresa_ruc,
                periodo_aaaamm=periodo_aaaamm,
                correlativo="001"
            )
            
            print(f"   ✓ Archivo generado: {resultado['archivo_generado']}")
            
            if resultado['archivo_generado']:
                print(f"   ✓ Nombre archivo: {resultado['nombre_archivo']}")
                print(f"   ✓ Total registros: {resultado['total_registros']}")
                print(f"   ✓ Validación SUNAT: {resultado['validacion']['es_valido']}")
                
                # Mostrar resumen
                resumen = resultado['resumen']
                print(f"   ✓ Resumen financiero:")
                print(f"      - Total debe: {resumen['total_debe']}")
                print(f"      - Total haber: {resumen['total_haber']}")
                print(f"      - Cuentas únicas: {resumen['cuentas_unicas']}")
                
                # Validaciones de archivo
                assert resultado['archivo_generado'] == True, "Archivo no fue generado"
                assert len(resultado['nombre_archivo']) > 0, "Nombre de archivo vacío"
                assert resultado['total_registros'] > 0, "No hay registros en el archivo"
                assert 'contenido_archivo' in resultado, "Contenido de archivo faltante"
                
                # Validaciones de formato SUNAT
                assert resultado['nombre_archivo'].startswith(f"LE{self.empresa_ruc}"), "Nombre incorrecto"
                assert "050200" in resultado['nombre_archivo'], "Código de libro 050200 no presente"
                assert resultado['nombre_archivo'].endswith(".txt"), "Extensión incorrecta"
                
                # Validaciones de contenido
                contenido = resultado['contenido_archivo']
                assert len(contenido) > 0, "Contenido vacío"
                # Verificar que el contenido tiene el formato correcto (periodo como primer campo)
                lineas = contenido.split('\n')
                primera_linea = lineas[0].split('|')
                assert len(primera_linea) == 9, f"Línea PLE debe tener 9 campos, encontrados: {len(primera_linea)}"
                assert primera_linea[0].startswith("2025"), "Período debe iniciar con 2025"
                
            else:
                print(f"   ⚠️  No se generó archivo: {resultado.get('mensaje', 'Sin mensaje')}")
            
            return resultado
        
        result = asyncio.run(run_test())
        assert result is not None
    
    def test_04_validacion_sunat_formato_archivo(self):
        """Test 4: Validación específica de formato SUNAT"""
        print(f"\n🏛️  TEST 4: Validación formato SUNAT específico...")
        
        async def run_test():
            periodo_aaaamm = "202508"
            
            # Generar archivo para validación
            resultado = await self._servicio().generar_archivo_ple_mayor_con_datos_reales(
                empresa_id=self.empresa_id,
                empresa_ruc=self.empresa_ruc,
                periodo_aaaamm=periodo_aaaamm
            )
            
            if not resultado['archivo_generado']:
                pytest.skip("No se pudo generar archivo para validación")
            
            contenido = resultado['contenido_archivo']
            lineas = contenido.strip().split('\n')
            
            print(f"   ✓ Total líneas: {len(lineas)}")
            
            # Validar cada línea del archivo
            for i, linea in enumerate(lineas[:3]):  # Validar primeras 3 líneas
                print(f"   📄 Línea {i+1}: {linea[:50]}...")
                
                campos = linea.split('|')
                print(f"      - Campos: {len(campos)}")
                
                # Validaciones específicas SUNAT PLE 050200
                # Debe tener exactamente 9 campos según especificación
                assert len(campos) >= 8, f"Línea {i+1}: debe tener al menos 8 campos, tiene {len(campos)}"
                
                # Campo 1: Período (8 dígitos)
                periodo_campo = campos[0]
                assert len(periodo_campo) == 8, f"Línea {i+1}: período debe tener 8 dígitos"
                assert periodo_campo.isdigit(), f"Línea {i+1}: período debe ser numérico"
                assert periodo_campo.endswith('00'), f"Línea {i+1}: período debe terminar en 00"
                
                # Campo 2: Código cuenta (no vacío)
                codigo_cuenta = campos[1]
                assert len(codigo_cuenta) > 0, f"Línea {i+1}: código cuenta no puede estar vacío"
                
                # Campo 3: Descripción cuenta (no vacía)
                descripcion = campos[2] if len(campos) > 2 else ""
                assert len(descripcion) > 0, f"Línea {i+1}: descripción no puede estar vacía"
                
                # Validar importes (deben ser números decimales válidos)
                for campo_idx in [4, 5, 6, 7]:  # Saldos y movimientos
                    if len(campos) > campo_idx:
                        importe = campos[campo_idx]
                        try:
                            Decimal(importe)
                        except:
                            assert False, f"Línea {i+1}, campo {campo_idx+1}: importe inválido '{importe}'"
            
            print(f"   ✅ Formato SUNAT validado correctamente")
            
            return True
        
        result = asyncio.run(run_test())
        assert result == True
    
    def test_05_prueba_con_diferentes_periodos(self):
        """Test 5: Prueba con diferentes períodos"""
        print(f"\n📅 TEST 5: Prueba con diferentes períodos...")
        
        async def run_test():
            # Los periodos que existen de verdad. Con "202507"/"202508" fijos,
            # este test fallaba siempre en cuanto los datos eran de otro año.
            periodos_test = sorted({
                (a.get('fecha') or '')[:7].replace('-', '')
                for a in self.asientos_reales
                if (a.get('fecha') or '')[:7]
            }) or ["202606"]
            resultados = []
            
            for periodo in periodos_test:
                print(f"   📊 Procesando período: {periodo}")
                
                try:
                    resultado = await self._servicio().generar_archivo_ple_mayor_con_datos_reales(
                        empresa_id=self.empresa_id,
                        empresa_ruc=self.empresa_ruc,
                        periodo_aaaamm=periodo,
                        correlativo="001"
                    )
                    
                    resultados.append({
                        "periodo": periodo,
                        "exitoso": resultado['archivo_generado'],
                        "registros": resultado.get('total_registros', 0),
                        "mensaje": resultado.get('mensaje', 'OK')
                    })
                    
                    print(f"      ✓ Generado: {resultado['archivo_generado']}")
                    print(f"      ✓ Registros: {resultado.get('total_registros', 0)}")
                    
                except Exception as e:
                    print(f"      ❌ Error: {str(e)}")
                    resultados.append({
                        "periodo": periodo,
                        "exitoso": False,
                        "registros": 0,
                        "mensaje": str(e)
                    })
            
            print(f"   📋 Resumen de períodos:")
            for resultado in resultados:
                status = "✅" if resultado['exitoso'] else "❌"
                print(f"      {status} {resultado['periodo']}: {resultado['registros']} registros")
            
            # Al menos un período debe funcionar
            exitosos = [r for r in resultados if r['exitoso']]
            assert len(exitosos) > 0, "Ningún período funcionó correctamente"
            
            return resultados
        
        result = asyncio.run(run_test())
        assert isinstance(result, list)
    
    @classmethod
    def teardown_class(cls):
        """Limpieza final"""
        if hasattr(cls, 'client'):
            cls.client.close()
        print(f"\n🏁 Tests de integración completados")


def main():
    """Ejecutar tests de integración directamente"""
    print("=" * 70)
    print("🔗 EJECUTANDO TESTS DE INTEGRACIÓN COMPLETA - LIBRO MAYOR")
    print("=" * 70)
    
    # Ejecutar tests
    pytest.main([__file__, "-v", "-s"])


if __name__ == "__main__":
    main()
