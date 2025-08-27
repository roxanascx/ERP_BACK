"""
Test Integración PLE SUNAT V3 - Fase 2
======================================

Script de prueba para validar la integración completa de:
- PLEFormatterSunatV3 (24 campos)
- PLEZipGenerator (compresión SUNAT)
- PLEGenerator (generación completa)

Valida el flujo completo de generación de archivos PLE
desde datos de asientos hasta archivo ZIP final.

Autor: Sistema ERP - Implementación SUNAT V3
Fecha: Agosto 2025
"""

import asyncio
import sys
import os
from datetime import datetime, date
from typing import Dict, Any, List
import json

# Agregar path del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports del sistema PLE
from app.modules.accounting.ple.ple_generator import PLEGenerator, PLEOptions
from app.modules.accounting.ple.ple_formatter_sunat_v3 import PLEFormatterSunatV3
from app.modules.accounting.ple.ple_zip_generator import PLEZipGenerator

def crear_datos_prueba() -> List[Dict[str, Any]]:
    """Crear datos de prueba realistas para asientos contables"""
    return [
        {
            'periodo': '202408',
            'numero_correlativo': '000001',
            'codigo_cuenta_contable': '1211',
            'codigo_unidad_operacion': '0000',
            'codigo_centro_costo': '',
            'tipo_moneda': 'PEN',
            'tipo_documento_identidad_emisor': '6',
            'numero_documento_identidad_emisor': '20100123456',
            'tipo_comprobante_pago': '01',
            'numero_serie_comprobante': 'F001',
            'numero_comprobante_pago': '000001',
            'fecha_contable': date(2024, 8, 15),
            'fecha_vencimiento': date(2024, 8, 15),
            'fecha_operacion': date(2024, 8, 15),
            'glosa_descripcion': 'VENTA DE MERCADERIA VARIOS',
            'debe': 1180.00,
            'haber': 0.00,
            'dato_estructurado': '',
            'estado_operacion': '1',
            'campo_libre': ''
        },
        {
            'periodo': '202408',
            'numero_correlativo': '000002',
            'codigo_cuenta_contable': '4011',
            'codigo_unidad_operacion': '0000',
            'codigo_centro_costo': '',
            'tipo_moneda': 'PEN',
            'tipo_documento_identidad_emisor': '6',
            'numero_documento_identidad_emisor': '20100123456',
            'tipo_comprobante_pago': '01',
            'numero_serie_comprobante': 'F001',
            'numero_comprobante_pago': '000001',
            'fecha_contable': date(2024, 8, 15),
            'fecha_vencimiento': date(2024, 8, 15),
            'fecha_operacion': date(2024, 8, 15),
            'glosa_descripcion': 'VENTA DE MERCADERIA VARIOS',
            'debe': 0.00,
            'haber': 1000.00,
            'dato_estructurado': '',
            'estado_operacion': '1',
            'campo_libre': ''
        },
        {
            'periodo': '202408',
            'numero_correlativo': '000003',
            'codigo_cuenta_contable': '4017',
            'codigo_unidad_operacion': '0000',
            'codigo_centro_costo': '',
            'tipo_moneda': 'PEN',
            'tipo_documento_identidad_emisor': '6',
            'numero_documento_identidad_emisor': '20100123456',
            'tipo_comprobante_pago': '01',
            'numero_serie_comprobante': 'F001',
            'numero_comprobante_pago': '000001',
            'fecha_contable': date(2024, 8, 15),
            'fecha_vencimiento': date(2024, 8, 15),
            'fecha_operacion': date(2024, 8, 15),
            'glosa_descripcion': 'VENTA DE MERCADERIA VARIOS',
            'debe': 0.00,
            'haber': 180.00,
            'dato_estructurado': '',
            'estado_operacion': '1',
            'campo_libre': ''
        }
    ]

def test_formateador_sunat_v3():
    """Test del formateador de 24 campos SUNAT V3"""
    print("🧪 Test 1: PLEFormatterSunatV3 - Formateo de 24 campos")
    print("=" * 60)
    
    formatter = PLEFormatterSunatV3()
    datos_prueba = crear_datos_prueba()
    
    try:
        for i, asiento in enumerate(datos_prueba, 1):
            linea_formateada = formatter.formatear_linea_completa(asiento)
            campos = linea_formateada.split('|')
            
            print(f"📝 Asiento {i}:")
            print(f"   Cuenta: {campos[2]}")
            print(f"   Debe: {campos[15]}")
            print(f"   Haber: {campos[16]}")
            print(f"   Total campos: {len(campos)}")
            print(f"   Línea completa: {linea_formateada[:100]}...")
            print()
            
            # Validar 24 campos
            assert len(campos) == 24, f"Esperaban 24 campos, obtenidos: {len(campos)}"
        
        print("✅ Formateador SUNAT V3 funciona correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en formateador SUNAT V3: {str(e)}")
        return False

def test_zip_generator():
    """Test del generador de archivos ZIP"""
    print("🧪 Test 2: PLEZipGenerator - Compresión archivos SUNAT")
    print("=" * 60)
    
    zip_generator = PLEZipGenerator()
    
    # Crear contenido TXT de prueba
    contenido_txt = """202408|000001|1211|0000||PEN|6|20100123456|01|F001|000001|15/08/2024|15/08/2024|15/08/2024|VENTA DE MERCADERIA VARIOS|1180.00|0.00||1||||||
202408|000002|4011|0000||PEN|6|20100123456|01|F001|000001|15/08/2024|15/08/2024|15/08/2024|VENTA DE MERCADERIA VARIOS|0.00|1000.00||1||||||
202408|000003|4017|0000||PEN|6|20100123456|01|F001|000001|15/08/2024|15/08/2024|15/08/2024|VENTA DE MERCADERIA VARIOS|0.00|180.00||1||||||"""
    
    try:
        # Generar ZIP
        metadata = zip_generator.generar_zip_desde_contenido(
            contenido_txt=contenido_txt,
            nombre_archivo_base="LE20100123456202408050100011",
            directorio_salida=None  # Solo en memoria
        )
        
        print(f"📦 Archivo ZIP generado:")
        print(f"   Nombre: {metadata.nombre_archivo_zip}")
        print(f"   TXT interno: {metadata.nombre_archivo_txt_interno}")
        print(f"   Tamaño TXT: {metadata.tamaño_txt_bytes} bytes")
        print(f"   Tamaño ZIP: {metadata.tamaño_zip_bytes} bytes")
        print(f"   Compresión: {metadata.ratio_compresion}%")
        print(f"   Método: {metadata.metodo_compresion}")
        print(f"   Válido: {metadata.es_valido}")
        
        if metadata.errores:
            print(f"   Errores: {metadata.errores}")
        
        assert metadata.es_valido, f"ZIP no válido: {metadata.errores}"
        assert metadata.tamaño_zip_bytes > 0, "ZIP vacío"
        assert metadata.ratio_compresion > 0, "Sin compresión"
        
        print("✅ Generador ZIP funciona correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en generador ZIP: {str(e)}")
        return False

def test_integracion_completa():
    """Test de integración completa PLE Generator"""
    print("🧪 Test 3: PLEGenerator - Integración completa SUNAT V3")
    print("=" * 60)
    
    generator = PLEGenerator()
    datos_prueba = crear_datos_prueba()
    
    try:
        # Configurar opciones
        opciones = PLEOptions(
            validar_antes_generar=True,
            generar_zip=True,
            incluir_metadatos=True,
            validar_con_sunat=False  # Para pruebas sin conexión
        )
        
        # Generar PLE completo con ZIP
        archivo_ple, metadata_zip = generator.generar_ple_zip_sunat_v3(
            datos_asientos=datos_prueba,
            ruc_empresa="20100123456",
            periodo=date(2024, 8, 31),
            opciones=opciones,
            directorio_salida=None
        )
        
        print(f"📄 Archivo PLE generado:")
        print(f"   Nombre: {archivo_ple.nombre_archivo}")
        print(f"   Total líneas: {archivo_ple.total_lineas}")
        print(f"   Total debe: {archivo_ple.resumen_validacion.get('total_debe', 0)}")
        print(f"   Total haber: {archivo_ple.resumen_validacion.get('total_haber', 0)}")
        print(f"   Validación exitosa: {len(archivo_ple.errores) == 0}")
        print(f"   Tamaño TXT: {archivo_ple.tamaño_txt} bytes")
        print(f"   Tamaño ZIP: {archivo_ple.tamaño_zip} bytes")
        
        print(f"\n📦 Metadata ZIP:")
        print(f"   Archivo ZIP: {metadata_zip.nombre_archivo_zip}")
        print(f"   Compresión: {metadata_zip.ratio_compresion}%")
        print(f"   Hash MD5 TXT: {metadata_zip.hash_md5_txt}")
        print(f"   Hash MD5 ZIP: {metadata_zip.hash_md5_zip}")
        print(f"   Válido: {metadata_zip.es_valido}")
        
        # Mostrar contenido TXT (primeras líneas)
        print(f"\n📝 Contenido TXT (muestra):")
        lineas = archivo_ple.contenido_txt.strip().split('\n')
        for i, linea in enumerate(lineas[:2], 1):
            print(f"   Línea {i}: {linea}")
        if len(lineas) > 2:
            print(f"   ... y {len(lineas) - 2} líneas más")
        
        # Validaciones
        assert len(archivo_ple.errores) == 0, f"Validación falló: {archivo_ple.errores}"
        assert archivo_ple.total_lineas == 3, f"Esperaban 3 líneas, obtenidas: {archivo_ple.total_lineas}"
        assert metadata_zip.es_valido, f"ZIP inválido: {metadata_zip.errores}"
        
        total_debe = archivo_ple.resumen_validacion.get('total_debe', 0)
        total_haber = archivo_ple.resumen_validacion.get('total_haber', 0)
        assert abs(total_debe - 1180.00) < 0.01, f"Total debe incorrecto: {total_debe}"
        assert abs(total_haber - 1180.00) < 0.01, f"Total haber incorrecto: {total_haber}"
        
        print("\n✅ Integración completa funciona correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en integración completa: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 INICIANDO TESTS FASE 2 - PLE SUNAT V3")
    print("=" * 60)
    print("Validando integración completa de:")
    print("- PLEFormatterSunatV3 (24 campos oficiales)")
    print("- PLEZipGenerator (compresión SUNAT)")
    print("- PLEGenerator (flujo completo)")
    print("=" * 60)
    print()
    
    resultados = []
    
    # Test 1: Formateador SUNAT V3
    resultados.append(test_formateador_sunat_v3())
    print()
    
    # Test 2: Generador ZIP
    resultados.append(test_zip_generator())
    print()
    
    # Test 3: Integración completa
    resultados.append(test_integracion_completa())
    print()
    
    # Resumen final
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    tests_pasados = sum(resultados)
    total_tests = len(resultados)
    
    print(f"✅ Tests pasados: {tests_pasados}/{total_tests}")
    
    if tests_pasados == total_tests:
        print("🎉 TODOS LOS TESTS PASARON - FASE 2 COMPLETADA")
        print("\nCaracterísticas validadas:")
        print("- ✅ Formateo de 24 campos oficial SUNAT")
        print("- ✅ Generación de archivos ZIP conformes")
        print("- ✅ Nomenclatura oficial de archivos")
        print("- ✅ Integración completa del flujo")
        print("- ✅ Validación de integridad")
        print("- ✅ Cálculo correcto de totales")
        return True
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("Revisar errores arriba para identificar problemas")
        return False

if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
