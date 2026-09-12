"""
Tests de Integración - Filtrado Avanzado Libro Mayor
====================================================

Tests completos para los endpoints de filtrado avanzado del Libro Mayor,
incluyendo filtros complejos, búsquedas, estadísticas y agrupaciones.

Casos de prueba:
- Filtros básicos y avanzados con datos reales
- Búsqueda de cuentas por patrones
- Estadísticas filtradas y balanceadas
- Agrupaciones por diferentes criterios
- Paginación y ordenamiento
- Validación de parámetros

Autor: Sistema ERP - FASE 3.2
Fecha: Agosto 2025
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, List

# Configuración del entorno de test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import get_database
from app.modules.accounting.services.filtrado_avanzado_service import (
    ServiceFiltradoAvanzadoMayor,
    FiltroAvanzado,
    TipoOrdenamiento,
    CampoOrdenamiento,
    TipoAgrupacion
)
from app.modules.accounting.schemas.schemas_mayor import TipoCuentaContable

from app.config import settings

# Variables globales para tests
DB_CLIENT = None
#: Estaba cableado a "sistema_erp", que no existe. Sale de la configuracion
#: para que el test mire la misma base que la aplicacion.
DB_NAME = settings.DATABASE_NAME
EMPRESA_ID_TEST = "60b9b9b9b9b9b9b9b9b9b9b9"  # ID de prueba
RUC_EMPRESA_TEST = "20123456789"


def setup_module(module):
    """Setup para el módulo de tests"""
    global DB_CLIENT
    print("\n" + "="*80)
    print("🧪 INICIANDO TESTS DE FILTRADO AVANZADO LIBRO MAYOR")
    print("="*80)
    
    # Conectar a MongoDB usando el método síncrono
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    
    # URL de MongoDB desde las variables de entorno
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DB_CLIENT = AsyncIOMotorClient(mongodb_url)
    print(f"✅ Conectado a MongoDB: {DB_NAME}")


def teardown_module(module):
    """Cleanup después de los tests"""
    global DB_CLIENT
    if DB_CLIENT:
        DB_CLIENT.close()
    print("\n" + "="*80)
    print("✅ TESTS DE FILTRADO AVANZADO COMPLETADOS")
    print("="*80)


def aplicar(filtro):
    """
    Aplicar un filtro esperando de verdad al servicio.

    `aplicar_filtro_avanzado` es `async`, y estos tests son funciones
    normales: llamarlo sin `await` devolvia una corrutina, y cada aserto
    moria con "'coroutine' object has no attribute". El modulo estaba bien;
    el test no lo esperaba.

    El cliente se crea aqui dentro, no en `setup_module`: Motor se ata al
    primer bucle que ve, y cada `asyncio.run()` abre y cierra el suyo.
    """
    async def correr():
        from motor.motor_asyncio import AsyncIOMotorClient

        cliente = AsyncIOMotorClient(settings.MONGODB_URL)
        try:
            servicio = ServiceFiltradoAvanzadoMayor(cliente, DB_NAME)
            return await servicio.aplicar_filtro_avanzado(filtro)
        finally:
            cliente.close()

    return asyncio.run(correr())


class TestFiltradoAvanzadoBasico:
    """Tests para filtros básicos del Libro Mayor"""
    
    def test_filtro_empresa_periodo(self):
        """Test: Filtro básico por empresa y período"""
        print("\n🧪 Test: Filtro básico por empresa y período")
        
        try:
            # Crear servicio
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Crear filtro básico
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                periodo_desde="202401",
                periodo_hasta="202412",
                incluir_totales=True
            )
            
            # Aplicar filtro
            resultado = aplicar(filtro)
            
            # Validaciones
            assert resultado is not None, "Resultado no debe ser None"
            assert resultado.total_registros >= 0, "Total de registros debe ser >= 0"
            
            if resultado.total_registros > 0:
                assert len(resultado.registros) > 0, "Debe tener registros si total > 0"
                assert resultado.total_saldo_deudor >= 0, "Total saldo deudor debe ser >= 0"
                assert resultado.total_saldo_acreedor >= 0, "Total saldo acreedor debe ser >= 0"
                
                # Validar estructura de registro
                primer_registro = resultado.registros[0]
                assert hasattr(primer_registro, 'codigo_cuenta_contable'), "Registro debe tener código de cuenta"
                assert hasattr(primer_registro, 'descripcion_cuenta'), "Registro debe tener descripción"
                
                print(f"✅ Total de registros encontrados: {resultado.total_registros}")
                print(f"   Total saldo deudor: {resultado.total_saldo_deudor}")
                print(f"   Total saldo acreedor: {resultado.total_saldo_acreedor}")
            else:
                print("ℹ️  No se encontraron registros para los criterios especificados")
            
            print("✅ Test filtro básico completado")
            
        except Exception as e:
            print(f"❌ Error en test filtro básico: {str(e)}")
            raise
    
    def test_filtro_codigo_cuenta_especifico(self):
        """Test: Filtro por código de cuenta específico"""
        print("\n🧪 Test: Filtro por código de cuenta específico")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Probar con cuentas comunes
            codigos_test = ["10", "101", "1011", "40", "401", "42"]
            
            for codigo in codigos_test:
                print(f"  Probando código: {codigo}")
                
                filtro = FiltroAvanzado(
                    empresa_id=EMPRESA_ID_TEST,
                    codigo_cuenta=codigo,
                    incluir_saldos_cero=True
                )
                
                resultado = aplicar(filtro)
                
                if resultado.total_registros > 0:
                    print(f"    ✅ Encontrados {resultado.total_registros} registros para {codigo}")
                    
                    # Validar que los códigos coincidan
                    for registro in resultado.registros:
                        assert registro.codigo_cuenta_contable == codigo, f"Código debe ser exactamente {codigo}"
                    
                    break  # Si encontramos datos, salimos del loop
            
            print("✅ Test filtro código específico completado")
            
        except Exception as e:
            print(f"❌ Error en test código específico: {str(e)}")
            raise
    
    def test_filtro_rangos_numericos(self):
        """Test: Filtros por rangos numéricos"""
        print("\n🧪 Test: Filtros por rangos numéricos")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Test 1: Filtro por saldo deudor mínimo
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                saldo_deudor_min=Decimal('1000.00'),
                incluir_saldos_cero=False,
                limite=10
            )
            
            resultado = aplicar(filtro)
            print(f"  Cuentas con saldo deudor >= 1000: {resultado.total_registros}")
            
            # Validar que cumplan el criterio
            for registro in resultado.registros:
                assert registro.saldo_final_deudor >= Decimal('1000.00'), "Saldo deudor debe ser >= 1000"
            
            # Test 2: Filtro por movimientos
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                movimiento_debe_min=Decimal('500.00'),
                solo_con_movimientos=True,
                limite=5
            )
            
            resultado = aplicar(filtro)
            print(f"  Cuentas con movimiento debe >= 500: {resultado.total_registros}")
            
            # Validar que tengan movimientos
            for registro in resultado.registros:
                assert registro.movimiento_debe >= Decimal('500.00'), "Movimiento debe ser >= 500"
            
            print("✅ Test filtros rangos numéricos completado")
            
        except Exception as e:
            print(f"❌ Error en test rangos numéricos: {str(e)}")
            raise


class TestFiltradoAvanzadoTexto:
    """Tests para filtros de búsqueda de texto"""
    
    def test_busqueda_texto_descripcion(self):
        """Test: Búsqueda de texto en descripción"""
        print("\n🧪 Test: Búsqueda de texto en descripción")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Términos de búsqueda comunes en contabilidad
            terminos_test = ["CAJA", "BANCO", "VENTAS", "COMPRAS", "DEUDORES", "ACREEDORES"]
            
            for termino in terminos_test:
                print(f"  Buscando: {termino}")
                
                filtro = FiltroAvanzado(
                    empresa_id=EMPRESA_ID_TEST,
                    buscar_texto=termino,
                    limite=5
                )
                
                resultado = aplicar(filtro)
                
                if resultado.total_registros > 0:
                    print(f"    ✅ Encontrados {resultado.total_registros} registros con '{termino}'")
                    
                    # Validar que el texto aparezca en la descripción
                    for registro in resultado.registros:
                        descripcion_upper = registro.descripcion_cuenta.upper()
                        assert termino.upper() in descripcion_upper, f"'{termino}' debe estar en la descripción"
                    
                    # Mostrar algunos resultados
                    for i, registro in enumerate(resultado.registros[:3]):
                        print(f"      {registro.codigo_cuenta_contable}: {registro.descripcion_cuenta}")
                    
                    break  # Si encontramos datos, salimos del loop
            
            print("✅ Test búsqueda texto completado")
            
        except Exception as e:
            print(f"❌ Error en test búsqueda texto: {str(e)}")
            raise
    
    def test_busqueda_patron_codigo(self):
        """Test: Búsqueda por patrón en código de cuenta"""
        print("\n🧪 Test: Búsqueda por patrón en código de cuenta")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Patrones regex comunes
            patrones_test = [
                ("^10", "Cuentas que empiecen con 10"),
                ("^4", "Cuentas que empiecen con 4"),
                ("1$", "Cuentas que terminen en 1"),
                ("^[1-2]", "Cuentas del 1 al 2")
            ]
            
            for patron, descripcion in patrones_test:
                print(f"  Probando patrón: {patron} ({descripcion})")
                
                filtro = FiltroAvanzado(
                    empresa_id=EMPRESA_ID_TEST,
                    patron_codigo_cuenta=patron,
                    limite=10
                )
                
                try:
                    resultado = aplicar(filtro)
                    
                    if resultado.total_registros > 0:
                        print(f"    ✅ Encontrados {resultado.total_registros} registros con patrón '{patron}'")
                        
                        # Mostrar algunos códigos encontrados
                        codigos = [r.codigo_cuenta_contable for r in resultado.registros[:5]]
                        print(f"      Ejemplos: {', '.join(codigos)}")
                        
                        break  # Si encontramos datos, salimos del loop
                    
                except Exception as regex_error:
                    print(f"    ⚠️  Error con patrón '{patron}': {str(regex_error)}")
                    continue
            
            print("✅ Test búsqueda patrón completado")
            
        except Exception as e:
            print(f"❌ Error en test búsqueda patrón: {str(e)}")
            raise


class TestFiltradoAvanzadoOrdenamiento:
    """Tests para ordenamiento y paginación"""
    
    def test_ordenamiento_campos(self):
        """Test: Ordenamiento por diferentes campos"""
        print("\n🧪 Test: Ordenamiento por diferentes campos")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Test ordenamiento por código de cuenta
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                ordenar_por=CampoOrdenamiento.CODIGO_CUENTA,
                tipo_orden=TipoOrdenamiento.ASCENDENTE,
                limite=10
            )
            
            resultado = aplicar(filtro)
            
            if resultado.total_registros > 0:
                print(f"  Ordenado por código (ASC): {resultado.total_registros} registros")
                
                # Validar ordenamiento ascendente
                codigos = [r.codigo_cuenta_contable for r in resultado.registros]
                print(f"    Códigos: {', '.join(codigos[:5])}")
                
                # Verificar orden
                for i in range(1, len(codigos)):
                    assert codigos[i] >= codigos[i-1], "Códigos deben estar en orden ascendente"
                
                # Test ordenamiento descendente
                filtro.tipo_orden = TipoOrdenamiento.DESCENDENTE
                resultado_desc = aplicar(filtro)
                
                codigos_desc = [r.codigo_cuenta_contable for r in resultado_desc.registros]
                print(f"    Códigos (DESC): {', '.join(codigos_desc[:5])}")
                
                # Verificar orden descendente
                for i in range(1, len(codigos_desc)):
                    assert codigos_desc[i] <= codigos_desc[i-1], "Códigos deben estar en orden descendente"
            
            print("✅ Test ordenamiento completado")
            
        except Exception as e:
            print(f"❌ Error en test ordenamiento: {str(e)}")
            raise
    
    def test_paginacion(self):
        """Test: Paginación de resultados"""
        print("\n🧪 Test: Paginación de resultados")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Primera página
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                limite=5,
                offset=0,
                ordenar_por=CampoOrdenamiento.CODIGO_CUENTA
            )
            
            primera_pagina = aplicar(filtro)
            
            if primera_pagina.total_registros > 5:
                print(f"  Primera página: {len(primera_pagina.registros)} registros")
                codigos_pagina1 = [r.codigo_cuenta_contable for r in primera_pagina.registros]
                
                # Segunda página
                filtro.offset = 5
                segunda_pagina = aplicar(filtro)
                
                print(f"  Segunda página: {len(segunda_pagina.registros)} registros")
                codigos_pagina2 = [r.codigo_cuenta_contable for r in segunda_pagina.registros]
                
                # Validar que no se repitan registros
                assert len(set(codigos_pagina1) & set(codigos_pagina2)) == 0, "No debe haber códigos repetidos entre páginas"
                
                print(f"    Página 1: {', '.join(codigos_pagina1)}")
                print(f"    Página 2: {', '.join(codigos_pagina2)}")
                
                # Validar paginación
                if primera_pagina.total_paginas:
                    assert primera_pagina.total_paginas >= 2, "Debe haber al menos 2 páginas"
                    assert primera_pagina.pagina_actual == 1, "Primera página debe ser 1"
                    assert segunda_pagina.pagina_actual == 2, "Segunda página debe ser 2"
            else:
                print("  ℹ️  No hay suficientes registros para probar paginación")
            
            print("✅ Test paginación completado")
            
        except Exception as e:
            print(f"❌ Error en test paginación: {str(e)}")
            raise


class TestFiltradoAvanzadoEstadisticas:
    """Tests para estadísticas y agrupaciones"""
    
    def test_estadisticas_generales(self):
        """Test: Estadísticas generales del filtro"""
        print("\n🧪 Test: Estadísticas generales")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                incluir_totales=True,
                incluir_estadisticas=True
            )
            
            resultado = aplicar(filtro)
            
            print(f"  Total de cuentas: {resultado.total_registros}")
            print(f"  Total saldo deudor: {resultado.total_saldo_deudor}")
            print(f"  Total saldo acreedor: {resultado.total_saldo_acreedor}")
            print(f"  Total movimiento debe: {resultado.total_movimiento_debe}")
            print(f"  Total movimiento haber: {resultado.total_movimiento_haber}")
            
            # Validar balance
            diferencia = abs(resultado.total_movimiento_debe - resultado.total_movimiento_haber)
            print(f"  Diferencia de balance: {diferencia}")
            
            # Validaciones básicas
            assert resultado.total_saldo_deudor >= 0, "Total saldo deudor debe ser >= 0"
            assert resultado.total_saldo_acreedor >= 0, "Total saldo acreedor debe ser >= 0"
            assert resultado.total_movimiento_debe >= 0, "Total movimiento debe ser >= 0"
            assert resultado.total_movimiento_haber >= 0, "Total movimiento haber debe ser >= 0"
            
            # El balance debería estar cuadrado (diferencia mínima por redondeos)
            if diferencia > Decimal('1.00'):
                print(f"  ⚠️  Advertencia: Diferencia de balance significativa: {diferencia}")
            
            print("✅ Test estadísticas generales completado")
            
        except Exception as e:
            print(f"❌ Error en test estadísticas: {str(e)}")
            raise
    
    def test_agrupaciones(self):
        """Test: Agrupaciones por diferentes criterios"""
        print("\n🧪 Test: Agrupaciones")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Test agrupación por tipo de cuenta
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                agrupar_por=TipoAgrupacion.POR_TIPO_CUENTA,
                incluir_totales=True,
                limite=50  # Más registros para agrupar
            )
            
            resultado = aplicar(filtro)
            
            if resultado.agrupaciones:
                print(f"  Agrupaciones por tipo de cuenta:")
                for tipo, stats in resultado.agrupaciones.items():
                    print(f"    {tipo}: {stats}")
            else:
                print("  ℹ️  No se generaron agrupaciones (puede requerir más datos)")
            
            # Test agrupación por nivel
            filtro.agrupar_por = TipoAgrupacion.POR_NIVEL_CUENTA
            resultado_nivel = aplicar(filtro)
            
            if resultado_nivel.agrupaciones:
                print(f"  Agrupaciones por nivel de cuenta:")
                for nivel, stats in resultado_nivel.agrupaciones.items():
                    print(f"    Nivel {nivel}: {stats}")
            
            print("✅ Test agrupaciones completado")
            
        except Exception as e:
            print(f"❌ Error en test agrupaciones: {str(e)}")
            raise


class TestFiltradoAvanzadoComplejos:
    """Tests para filtros complejos combinados"""
    
    def test_filtros_combinados(self):
        """Test: Combinación de múltiples filtros"""
        print("\n🧪 Test: Filtros combinados")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Filtro complejo: cuentas de activo con movimientos significativos
            filtro = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                patron_codigo_cuenta="^[1]",  # Cuentas que empiecen con 1 (activos)
                movimiento_debe_min=Decimal('100.00'),
                incluir_saldos_cero=False,
                ordenar_por=CampoOrdenamiento.SALDO_DEUDOR,
                tipo_orden=TipoOrdenamiento.DESCENDENTE,
                limite=10,
                incluir_totales=True
            )
            
            resultado = aplicar(filtro)
            
            print(f"  Cuentas de activo con movimientos >= 100: {resultado.total_registros}")
            
            if resultado.total_registros > 0:
                print(f"  Total movimientos debe: {resultado.total_movimiento_debe}")
                print(f"  Total saldo deudor: {resultado.total_saldo_deudor}")
                
                # Validar criterios
                for registro in resultado.registros:
                    assert registro.codigo_cuenta_contable.startswith('1'), "Debe empezar con 1"
                    assert registro.movimiento_debe >= Decimal('100.00'), "Movimiento debe >= 100"
                
                # Validar ordenamiento por saldo deudor descendente
                saldos = [r.saldo_final_deudor for r in resultado.registros]
                for i in range(1, len(saldos)):
                    assert saldos[i] <= saldos[i-1], "Saldos deben estar en orden descendente"
                
                print("    ✅ Todos los criterios combinados se cumplen")
            
            print("✅ Test filtros combinados completado")
            
        except Exception as e:
            print(f"❌ Error en test filtros combinados: {str(e)}")
            raise
    
    def test_validacion_parametros(self):
        """Test: Validación de parámetros incorrectos"""
        print("\n🧪 Test: Validación de parámetros")
        
        try:
            service = ServiceFiltradoAvanzadoMayor(DB_CLIENT, DB_NAME)
            
            # Test con empresa inexistente
            filtro_empresa_inexistente = FiltroAvanzado(
                empresa_id="000000000000000000000000",  # ID inexistente
                limite=5
            )
            
            resultado = aplicar(filtro_empresa_inexistente)
            assert resultado.total_registros == 0, "No debe encontrar registros para empresa inexistente"
            print("  ✅ Empresa inexistente: 0 registros")
            
            # Test con rango de fechas inválido
            filtro_fechas_invalidas = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                fecha_desde=date(2025, 1, 1),
                fecha_hasta=date(2024, 12, 31),  # Fecha hasta anterior a fecha desde
                limite=5
            )
            
            # Esto debería devolver 0 registros o manejar el error
            resultado = aplicar(filtro_fechas_invalidas)
            print(f"  ✅ Rango fechas inválido: {resultado.total_registros} registros")
            
            # Test con límite muy grande
            filtro_limite_grande = FiltroAvanzado(
                empresa_id=EMPRESA_ID_TEST,
                limite=999999  # Límite muy grande
            )
            
            resultado = aplicar(filtro_limite_grande)
            print(f"  ✅ Límite grande manejado: {resultado.total_registros} registros")
            
            print("✅ Test validación parámetros completado")
            
        except Exception as e:
            print(f"❌ Error en test validación: {str(e)}")
            raise


def main():
    """Ejecutar todos los tests de filtrado avanzado"""
    print("\n" + "="*80)
    print("🚀 EJECUTANDO SUITE COMPLETA DE TESTS - FILTRADO AVANZADO")
    print("="*80)
    
    try:
        # Setup
        setup_module(None)
        
        # Tests básicos
        test_basico = TestFiltradoAvanzadoBasico()
        test_basico.test_filtro_empresa_periodo()
        test_basico.test_filtro_codigo_cuenta_especifico()
        test_basico.test_filtro_rangos_numericos()
        
        # Tests de texto
        test_texto = TestFiltradoAvanzadoTexto()
        test_texto.test_busqueda_texto_descripcion()
        test_texto.test_busqueda_patron_codigo()
        
        # Tests de ordenamiento
        test_orden = TestFiltradoAvanzadoOrdenamiento()
        test_orden.test_ordenamiento_campos()
        test_orden.test_paginacion()
        
        # Tests de estadísticas
        test_stats = TestFiltradoAvanzadoEstadisticas()
        test_stats.test_estadisticas_generales()
        test_stats.test_agrupaciones()
        
        # Tests complejos
        test_complejos = TestFiltradoAvanzadoComplejos()
        test_complejos.test_filtros_combinados()
        test_complejos.test_validacion_parametros()
        
        print("\n" + "="*80)
        print("🎉 TODOS LOS TESTS DE FILTRADO AVANZADO COMPLETADOS EXITOSAMENTE")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERROR EN SUITE DE TESTS: {str(e)}")
        raise
    finally:
        # Cleanup
        teardown_module(None)


if __name__ == "__main__":
    main()
