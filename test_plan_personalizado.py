#!/usr/bin/env python3
"""
Script de prueba para las nuevas funcionalidades del plan contable personalizado
"""
import sys
import os
import asyncio

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.accounting.import_service import PlanContableImportService


async def test_plantilla_generation():
    """Prueba la generación de plantilla"""
    print("🧪 Probando generación de plantilla...")
    
    service = PlanContableImportService()
    plantilla = service.generar_plantilla_txt()
    
    print(f"✅ Plantilla generada exitosamente ({len(plantilla)} caracteres)")
    print("📄 Primeras líneas de la plantilla:")
    print("-" * 50)
    for i, line in enumerate(plantilla.split('\n')[:10]):
        print(f"{i+1:2d}: {line}")
    print("-" * 50)
    
    # Guardar plantilla en archivo de prueba
    test_file = "plantilla_test.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(plantilla)
    
    print(f"💾 Plantilla guardada en: {test_file}")
    return test_file


async def test_validation():
    """Prueba la validación de archivo"""
    print("\n🧪 Probando validación de archivo...")
    
    service = PlanContableImportService()
    
    # Crear contenido de prueba válido
    test_content = """# Plan de prueba
1               ACTIVO
10              ACTIVO CORRIENTE
101             EFECTIVO Y EQUIVALENTES
1011            CAJA
10111           Caja Moneda Nacional
10112           Caja Moneda Extranjera
102             BANCOS
1021            Banco de Crédito
2               PASIVO
20              PASIVO CORRIENTE
201             CUENTAS POR PAGAR
"""
    
    result = service.validar_formato_archivo(test_content)
    
    print(f"✅ Validación completada:")
    print(f"   - Es válido: {result.is_valid}")
    print(f"   - Total líneas: {result.total_lines}")
    print(f"   - Cuentas válidas: {result.valid_accounts}")
    print(f"   - Errores: {len(result.errors)}")
    print(f"   - Advertencias: {len(result.warnings)}")
    
    if result.errors:
        print("❌ Errores encontrados:")
        for error in result.errors[:5]:  # Mostrar solo los primeros 5
            print(f"   - {error}")
    
    if result.warnings:
        print("⚠️ Advertencias:")
        for warning in result.warnings:
            print(f"   - {warning}")
    
    print(f"📊 Preview de datos (primeras 5 cuentas):")
    for i, account in enumerate(result.preview_data[:5]):
        print(f"   {i+1}. {account['codigo']} - {account['descripcion']} (Nivel {account['nivel']})")
    
    return result


async def test_invalid_content():
    """Prueba validación con contenido inválido"""
    print("\n🧪 Probando validación con contenido inválido...")
    
    service = PlanContableImportService()
    
    # Contenido con errores
    invalid_content = """# Plan con errores
ABC             CUENTA INVALIDA (código no numérico)
123             CUENTA VÁLIDA
123             CUENTA DUPLICADA
1234567890123   CÓDIGO MUY LARGO (más de 10 dígitos)
456             
789             CUENTA SIN PADRE (nivel 3 sin padre de nivel 2)
"""
    
    result = service.validar_formato_archivo(invalid_content)
    
    print(f"🔍 Validación de contenido inválido:")
    print(f"   - Es válido: {result.is_valid}")
    print(f"   - Cuentas válidas: {result.valid_accounts}")
    print(f"   - Errores encontrados: {len(result.errors)}")
    
    if result.errors:
        print("❌ Errores detectados (como se esperaba):")
        for error in result.errors:
            print(f"   - {error}")
    
    return result


async def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DE PLAN CONTABLE PERSONALIZADO")
    print("=" * 60)
    
    try:
        # Prueba 1: Generación de plantilla
        plantilla_file = await test_plantilla_generation()
        
        # Prueba 2: Validación con contenido válido
        valid_result = await test_validation()
        
        # Prueba 3: Validación con contenido inválido
        invalid_result = await test_invalid_content()
        
        print("\n🎉 RESUMEN DE PRUEBAS:")
        print("=" * 60)
        print(f"✅ Generación de plantilla: OK")
        print(f"✅ Validación contenido válido: {'OK' if valid_result.is_valid else 'FALLO'}")
        print(f"✅ Detección de errores: {'OK' if not invalid_result.is_valid else 'FALLO'}")
        
        print(f"\n📁 Archivos generados:")
        print(f"   - {plantilla_file}")
        
        print(f"\n🔧 PRÓXIMOS PASOS:")
        print(f"   1. Probar endpoint de descarga de plantilla")
        print(f"   2. Probar endpoint de validación")
        print(f"   3. Implementar importación completa")
        print(f"   4. Crear interfaz frontend")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
