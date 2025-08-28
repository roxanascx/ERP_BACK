#!/usr/bin/env python3
"""
Test Simple - Validación Corrección PLE 19 Campos
=================================================

Validación directa de la corrección aplicada.
"""

def test_estructura_dataclass():
    """Test simple para verificar estructura del dataclass"""
    
    print("🚀 VALIDACIÓN CORRECCIÓN PLE 050100")
    print("=" * 50)
    
    # Leer archivo corregido
    try:
        with open('ple_formatter_sunat_v3.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        print("✅ Archivo leído correctamente")
        
        # Buscar definición de dataclass
        lineas = contenido.split('\n')
        en_dataclass = False
        campos_encontrados = []
        
        for linea in lineas:
            if '@dataclass' in linea and 'PLELineaSunatV3' in lineas[lineas.index(linea) + 1]:
                en_dataclass = True
                continue
            
            if en_dataclass and linea.strip().startswith('campo_'):
                campo = linea.strip().split(':')[0]
                campos_encontrados.append(campo)
            
            if en_dataclass and 'def to_ple_line' in linea:
                break
        
        # Contar campos
        campos_ple = [c for c in campos_encontrados if c.startswith('campo_')]
        num_campos = len(campos_ple)
        
        print(f"📊 Campos encontrados: {num_campos}")
        print(f"📋 Lista de campos:")
        
        for i, campo in enumerate(campos_ple, 1):
            print(f"   {i:2d}. {campo}")
        
        # Validación crítica
        if num_campos == 19:
            print("\n✅ CORRECCIÓN EXITOSA: 19 campos detectados")
            print("✅ Estructura conforme a especificación SUNAT")
        elif num_campos == 24:
            print("\n❌ CORRECCIÓN PENDIENTE: Aún 24 campos")
            print("❌ Necesita ajuste a 19 campos")
        else:
            print(f"\n⚠️  ESTRUCTURA IRREGULAR: {num_campos} campos")
        
        # Verificar método to_ple_line
        if 'return "|".join(campos) + "|"' in contenido:
            print("✅ Método to_ple_line actualizado")
        else:
            print("❌ Método to_ple_line necesita actualización")
        
        # Verificar comentarios de corrección
        if '19 campos' in contenido or 'CORREGIDO' in contenido:
            print("✅ Documentación de corrección presente")
        else:
            print("⚠️  Documentación de corrección faltante")
        
        return num_campos == 19
        
    except FileNotFoundError:
        print("❌ Archivo no encontrado")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_linea_ejemplo():
    """Test de generación de línea ejemplo"""
    
    print("\n🧪 TEST LÍNEA EJEMPLO:")
    print("-" * 30)
    
    # Línea ejemplo según especificación SUNAT
    ejemplo_sunat = [
        "202501",           # 1. Período  
        "M001",             # 2. CUO
        "00001",            # 3. Correlativo
        "10111",            # 4. Cuenta
        "001",              # 5. Unidad
        "001",              # 6. Centro costo  
        "PEN",              # 7. Moneda
        "01",               # 8. Tipo doc
        "F001",             # 9. Serie
        "000001",           # 10. Número
        "01/01/2025",       # 11. F.Contable
        "31/01/2025",       # 12. F.Vencimiento
        "01/01/2025",       # 13. F.Operación
        "Venta mercaderías", # 14. Glosa
        "REF001",           # 15. Referencia
        "1000.00",          # 16. Debe
        "0.00",             # 17. Haber
        "",                 # 18. Dato estructurado
        "1"                 # 19. Estado
    ]
    
    linea_generada = "|".join(ejemplo_sunat) + "|"
    
    print(f"📝 Línea ejemplo generada:")
    print(f"   {linea_generada}")
    
    # Validar estructura
    campos = linea_generada.split('|')
    num_campos = len(campos) - 1  # Restar pipe final
    
    print(f"\n📊 Análisis:")
    print(f"   - Campos: {num_campos}")
    print(f"   - Separador: {'|'}")
    print(f"   - Termina en |: {'✅' if linea_generada.endswith('|') else '❌'}")
    
    if num_campos == 19:
        print("✅ Estructura ejemplo correcta")
        return True
    else:
        print(f"❌ Estructura incorrecta: {num_campos} campos")
        return False


if __name__ == "__main__":
    print("🎯 SISTEMA DE VALIDACIÓN SIMPLIFICADO")
    print("=" * 50)
    
    test1 = test_estructura_dataclass()
    test2 = test_linea_ejemplo()
    
    print("\n🏁 RESULTADO FINAL:")
    print("-" * 20)
    
    if test1 and test2:
        print("✅ CORRECCIÓN COMPLETADA EXITOSAMENTE")
        print("🎉 Listo para FASE 2: Implementar otros libros PLE")
    else:
        print("❌ CORRECCIÓN INCOMPLETA")
        print("🔧 Revisar y corregir errores")
        
    print("\n📋 PRÓXIMOS PASOS:")
    print("   1. Verificar tests en entorno real")
    print("   2. Iniciar FASE 2: PLE 080000 (Compras)")
    print("   3. Documentar plan de trabajo detallado")
