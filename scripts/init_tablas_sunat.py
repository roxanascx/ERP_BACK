#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialización de las tablas SUNAT
===========================================

Script para inicializar las tablas de códigos SUNAT necesarias
para la generación de archivos PLE en el sistema ERP.

Uso:
    python scripts/init_tablas_sunat.py
    
Autor: Sistema ERP
Fecha: Agosto 2025
"""

import asyncio
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path para importaciones
sys.path.append(str(Path(__file__).parent.parent))

from app.modules.accounting.sunat_models import inicializar_tablas_sunat
from app.modules.accounting.sunat_service import TablasSUNATService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tablas_sunat_init.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Función principal para inicializar las tablas SUNAT"""
    
    print("🏛️ INICIALIZACIÓN DE TABLAS SUNAT")
    print("=" * 50)
    print("📅 Iniciando proceso de inicialización...")
    print()
    
    try:
        # Inicializar tablas utilizando la función utilitaria
        print("📋 Inicializando tablas SUNAT...")
        success = await inicializar_tablas_sunat()
        
        if success:
            print("✅ Tablas SUNAT inicializadas correctamente!")
            
            # Verificar con el servicio
            print("\n🔍 Verificando integridad...")
            service = TablasSUNATService()
            
            # Obtener estadísticas
            stats = await service.obtener_estadisticas()
            print(f"📊 Total de tablas activas: {stats.tablas_activas}")
            print(f"📊 Total de tablas: {stats.total_tablas}")
            
            # Mostrar detalle de tablas
            print("\n📋 Detalle de tablas inicializadas:")
            print("-" * 50)
            for tabla in stats.tablas_detalle:
                print(f"  • {tabla.descripcion}")
                print(f"    Tabla: {tabla.tabla}")
                print(f"    Códigos: {tabla.total_codigos}")
                print(f"    Actualizada: {tabla.fecha_actualizacion}")
                print()
            
            # Verificar integridad
            integridad = await service.verificar_integridad_tablas()
            
            if integridad["estado_general"] == "OK":
                print("✅ Verificación de integridad: EXITOSA")
            else:
                print("⚠️ Verificación de integridad: PROBLEMAS DETECTADOS")
                if integridad["errores"]:
                    print("❌ Errores:")
                    for error in integridad["errores"]:
                        print(f"  • {error}")
                
                if integridad["warnings"]:
                    print("⚠️ Advertencias:")
                    for warning in integridad["warnings"]:
                        print(f"  • {warning}")
            
            # Pruebas básicas
            print("\n🧪 Ejecutando pruebas básicas...")
            
            # Test 1: Buscar RUC en documentos de identidad
            busqueda_ruc = await service.buscar_codigo("tipos_documento_identidad", "6")
            if busqueda_ruc.encontrado:
                print(f"✅ Test RUC: {busqueda_ruc.descripcion}")
            else:
                print("❌ Test RUC: No encontrado")
            
            # Test 2: Buscar FACTURA en comprobantes
            busqueda_factura = await service.buscar_codigo("tipos_comprobantes_pago", "01")
            if busqueda_factura.encontrado:
                print(f"✅ Test FACTURA: {busqueda_factura.descripcion}")
            else:
                print("❌ Test FACTURA: No encontrada")
            
            # Test 3: Buscar LIBRO DIARIO en libros
            busqueda_libro = await service.buscar_codigo("codigos_libros_registros", "05")
            if busqueda_libro.encontrado:
                print(f"✅ Test LIBRO DIARIO: {busqueda_libro.descripcion}")
            else:
                print("❌ Test LIBRO DIARIO: No encontrado")
            
            # Test 4: Autocompletado
            autocomplete = await service.autocomplete("tipos_comprobantes_pago", "FACTURA", 5)
            if autocomplete.total_encontrados > 0:
                print(f"✅ Test AUTOCOMPLETADO: {autocomplete.total_encontrados} resultados")
            else:
                print("❌ Test AUTOCOMPLETADO: Sin resultados")
            
            print("\n🎉 INICIALIZACIÓN COMPLETADA EXITOSAMENTE!")
            print("=" * 50)
            print("📋 Las tablas SUNAT están listas para usar en el sistema PLE")
            print("🔗 Endpoints disponibles en: /accounting/tablas-sunat/")
            print()
            
        else:
            print("❌ Error al inicializar las tablas SUNAT")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error crítico en inicialización: {str(e)}")
        print(f"💥 Error crítico: {str(e)}")
        sys.exit(1)


async def verificar_conexion_db():
    """Verificar conexión a la base de datos"""
    try:
        from app.database import get_database
        db = get_database()
        
        # Realizar una operación básica para verificar conexión
        collections = await db.list_collection_names()
        print(f"✅ Conexión a MongoDB establecida. Colecciones: {len(collections)}")
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión a MongoDB: {str(e)}")
        return False


async def limpiar_tablas_existentes():
    """Limpiar tablas existentes (usar con precaución)"""
    print("⚠️ LIMPIANDO TABLAS EXISTENTES...")
    
    try:
        from app.database import get_database
        db = get_database()
        
        # Eliminar colección de tablas SUNAT
        await db.drop_collection("tablas_sunat")
        print("✅ Tablas SUNAT eliminadas")
        
    except Exception as e:
        logger.error(f"Error al limpiar tablas: {str(e)}")
        print(f"❌ Error al limpiar: {str(e)}")


def mostrar_ayuda():
    """Mostrar ayuda del script"""
    print("📖 AYUDA - Script de Inicialización de Tablas SUNAT")
    print("=" * 50)
    print()
    print("Uso:")
    print("  python scripts/init_tablas_sunat.py [opciones]")
    print()
    print("Opciones:")
    print("  --help, -h        Mostrar esta ayuda")
    print("  --clean           Limpiar tablas existentes antes de inicializar")
    print("  --verify-only     Solo verificar integridad sin inicializar")
    print("  --verbose, -v     Modo verboso")
    print()
    print("Ejemplos:")
    print("  python scripts/init_tablas_sunat.py")
    print("  python scripts/init_tablas_sunat.py --clean")
    print("  python scripts/init_tablas_sunat.py --verify-only")
    print()


async def solo_verificar():
    """Solo verificar integridad de las tablas existentes"""
    print("🔍 VERIFICACIÓN DE INTEGRIDAD DE TABLAS SUNAT")
    print("=" * 50)
    
    try:
        service = TablasSUNATService()
        
        # Verificar estadísticas
        stats = await service.obtener_estadisticas()
        
        if stats.total_tablas == 0:
            print("❌ No se encontraron tablas SUNAT en la base de datos")
            print("💡 Ejecute el script sin --verify-only para inicializarlas")
            return False
        
        print(f"📊 Tablas encontradas: {stats.total_tablas}")
        print(f"📊 Tablas activas: {stats.tablas_activas}")
        
        # Verificar integridad
        integridad = await service.verificar_integridad_tablas()
        
        print(f"\n🎯 Estado general: {integridad['estado_general']}")
        
        if integridad["errores"]:
            print("\n❌ Errores encontrados:")
            for error in integridad["errores"]:
                print(f"  • {error}")
        
        if integridad["warnings"]:
            print("\n⚠️ Advertencias:")
            for warning in integridad["warnings"]:
                print(f"  • {warning}")
        
        print(f"\n✅ Tablas verificadas: {len(integridad['tablas_verificadas'])}")
        
        return integridad["estado_general"] == "OK"
        
    except Exception as e:
        logger.error(f"Error en verificación: {str(e)}")
        print(f"❌ Error en verificación: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Inicializar tablas SUNAT para PLE")
    parser.add_argument("--clean", action="store_true", help="Limpiar tablas existentes")
    parser.add_argument("--verify-only", action="store_true", help="Solo verificar integridad")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verboso")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async def run():
        # Verificar conexión primero
        if not await verificar_conexion_db():
            sys.exit(1)
        
        if args.verify_only:
            success = await solo_verificar()
            sys.exit(0 if success else 1)
        
        if args.clean:
            await limpiar_tablas_existentes()
        
        await main()
    
    # Ejecutar función asíncrona
    asyncio.run(run())
