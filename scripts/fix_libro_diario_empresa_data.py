#!/usr/bin/env python3
"""
Script para corregir datos de empresa incorrectos en libros diario existentes
Este script corrige el problema de datos hardcodeados en el libro diario
"""

import asyncio
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Agregar el directorio padre al path para importar módulos de la app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import get_database
from app.modules.companies.services import CompanyService
from bson import ObjectId


class LibroDiarioDataFixer:
    """Clase para corregir datos de empresa en libros diario"""
    
    def __init__(self):
        self.db = get_database()
        self.libros_collection = self.db["libros_diario"]
        self.asientos_collection = self.db["asientos_contables"]
        self.company_service = CompanyService()
        
    async def analizar_problemas(self) -> Dict[str, Any]:
        """Analizar los problemas existentes en los datos"""
        print("🔍 Analizando problemas en los datos del libro diario...")
        
        # Buscar libros con datos hardcodeados
        libros_problematicos = await self.libros_collection.find({
            "$or": [
                {"ruc": "20123456789"},
                {"razonSocial": "Empresa de Prueba S.A.C."}
            ]
        }).to_list(length=None)
        
        # Buscar libros sin datos de empresa
        libros_sin_empresa = await self.libros_collection.find({
            "$or": [
                {"ruc": {"$exists": False}},
                {"razonSocial": {"$exists": False}},
                {"ruc": ""},
                {"razonSocial": ""}
            ]
        }).to_list(length=None)
        
        # Obtener empresas disponibles
        empresas_disponibles = await self.company_service.repository.list_companies(0, 1000)
        
        analisis = {
            "total_libros": await self.libros_collection.count_documents({}),
            "libros_con_datos_mock": len(libros_problematicos),
            "libros_sin_datos_empresa": len(libros_sin_empresa),
            "empresas_disponibles": len(empresas_disponibles),
            "empresas_activas": len([e for e in empresas_disponibles if e.activa]),
            "problemas_encontrados": []
        }
        
        # Detalles de los problemas
        for libro in libros_problematicos:
            analisis["problemas_encontrados"].append({
                "libro_id": str(libro["_id"]),
                "empresa_id": libro.get("empresaId", "N/A"),
                "descripcion": libro.get("descripcion", "N/A"),
                "problema": "Datos hardcodeados",
                "ruc_actual": libro.get("ruc", "N/A"),
                "razon_social_actual": libro.get("razonSocial", "N/A")
            })
            
        for libro in libros_sin_empresa:
            if libro not in libros_problematicos:  # Evitar duplicados
                analisis["problemas_encontrados"].append({
                    "libro_id": str(libro["_id"]),
                    "empresa_id": libro.get("empresaId", "N/A"),
                    "descripcion": libro.get("descripcion", "N/A"),
                    "problema": "Sin datos de empresa",
                    "ruc_actual": libro.get("ruc", "N/A"),
                    "razon_social_actual": libro.get("razonSocial", "N/A")
                })
        
        return analisis
    
    async def corregir_libro(self, libro: Dict[str, Any]) -> Dict[str, Any]:
        """Corregir los datos de un libro específico"""
        empresa_id = libro.get("empresaId")
        if not empresa_id:
            return {
                "success": False,
                "error": "No se encontró empresaId en el libro",
                "libro_id": str(libro["_id"])
            }
        
        try:
            # Obtener información real de la empresa
            empresa = await self.company_service.repository.get_company_by_id(empresa_id)
            if not empresa:
                empresa = await self.company_service.repository.get_company_by_ruc(empresa_id)
            
            if not empresa:
                return {
                    "success": False,
                    "error": f"Empresa no encontrada: {empresa_id}",
                    "libro_id": str(libro["_id"])
                }
            
            # Preparar datos de actualización
            datos_actualizacion = {
                "ruc": empresa.ruc,
                "razonSocial": empresa.razon_social,
                "fechaModificacion": datetime.utcnow()
            }
            
            # Actualizar el libro
            resultado = await self.libros_collection.update_one(
                {"_id": libro["_id"]},
                {"$set": datos_actualizacion}
            )
            
            if resultado.modified_count > 0:
                return {
                    "success": True,
                    "libro_id": str(libro["_id"]),
                    "empresa_id": empresa_id,
                    "ruc_anterior": libro.get("ruc", "N/A"),
                    "ruc_nuevo": empresa.ruc,
                    "razon_social_anterior": libro.get("razonSocial", "N/A"),
                    "razon_social_nueva": empresa.razon_social
                }
            else:
                return {
                    "success": False,
                    "error": "No se pudo actualizar el documento",
                    "libro_id": str(libro["_id"])
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "libro_id": str(libro["_id"])
            }
    
    async def ejecutar_correccion(self, confirmar: bool = False) -> Dict[str, Any]:
        """Ejecutar la corrección de todos los libros problemáticos"""
        print("🔧 Iniciando corrección de datos...")
        
        if not confirmar:
            print("⚠️  MODO SIMULACIÓN - No se realizarán cambios reales")
        
        # Obtener libros problemáticos
        libros_problematicos = await self.libros_collection.find({
            "$or": [
                {"ruc": "20123456789"},
                {"razonSocial": "Empresa de Prueba S.A.C."},
                {"ruc": {"$exists": False}},
                {"razonSocial": {"$exists": False}},
                {"ruc": ""},
                {"razonSocial": ""}
            ]
        }).to_list(length=None)
        
        resultados = {
            "total_procesados": 0,
            "exitosos": 0,
            "errores": 0,
            "detalles": [],
            "errores_detalle": []
        }
        
        for libro in libros_problematicos:
            resultados["total_procesados"] += 1
            
            if confirmar:
                resultado = await self.corregir_libro(libro)
            else:
                # Simular corrección
                empresa_id = libro.get("empresaId")
                empresa = None
                if empresa_id:
                    empresa = await self.company_service.repository.get_company_by_id(empresa_id)
                    if not empresa:
                        empresa = await self.company_service.repository.get_company_by_ruc(empresa_id)
                
                resultado = {
                    "success": empresa is not None,
                    "libro_id": str(libro["_id"]),
                    "empresa_id": empresa_id,
                    "simulacion": True,
                    "ruc_actual": libro.get("ruc", "N/A"),
                    "ruc_nuevo": empresa.ruc if empresa else "ERROR",
                    "razon_social_actual": libro.get("razonSocial", "N/A"),
                    "razon_social_nueva": empresa.razon_social if empresa else "ERROR"
                }
            
            if resultado["success"]:
                resultados["exitosos"] += 1
                resultados["detalles"].append(resultado)
            else:
                resultados["errores"] += 1
                resultados["errores_detalle"].append(resultado)
        
        return resultados
    
    async def generar_reporte(self):
        """Generar reporte completo del estado de los datos"""
        print("📊 Generando reporte completo...")
        
        analisis = await self.analizar_problemas()
        
        print("\n" + "="*80)
        print("📋 REPORTE DE ANÁLISIS DE DATOS DEL LIBRO DIARIO")
        print("="*80)
        
        print(f"\n📈 ESTADÍSTICAS GENERALES:")
        print(f"   • Total de libros diario: {analisis['total_libros']}")
        print(f"   • Libros con datos mock: {analisis['libros_con_datos_mock']}")
        print(f"   • Libros sin datos de empresa: {analisis['libros_sin_datos_empresa']}")
        print(f"   • Empresas disponibles: {analisis['empresas_disponibles']}")
        print(f"   • Empresas activas: {analisis['empresas_activas']}")
        
        if analisis["problemas_encontrados"]:
            print(f"\n🚨 PROBLEMAS ENCONTRADOS ({len(analisis['problemas_encontrados'])}):")
            for i, problema in enumerate(analisis["problemas_encontrados"][:10], 1):
                print(f"   {i}. Libro ID: {problema['libro_id']}")
                print(f"      Empresa ID: {problema['empresa_id']}")
                print(f"      Problema: {problema['problema']}")
                print(f"      RUC actual: {problema['ruc_actual']}")
                print(f"      Razón social actual: {problema['razon_social_actual']}")
                print()
            
            if len(analisis["problemas_encontrados"]) > 10:
                print(f"   ... y {len(analisis['problemas_encontrados']) - 10} problemas más")
        else:
            print("\n✅ No se encontraron problemas en los datos")
        
        return analisis


async def main():
    """Función principal del script"""
    print("🚀 Script de Corrección de Datos del Libro Diario")
    print("="*60)
    
    fixer = LibroDiarioDataFixer()
    
    # Generar reporte inicial
    await fixer.generar_reporte()
    
    print("\n" + "="*80)
    print("🔧 OPCIONES DE CORRECCIÓN")
    print("="*80)
    
    while True:
        print("\nSeleccione una opción:")
        print("1. 👀 Analizar problemas (solo lectura)")
        print("2. 🧪 Simular corrección (sin cambios reales)")
        print("3. ✅ Ejecutar corrección REAL")
        print("4. 📊 Generar reporte completo")
        print("5. 🚪 Salir")
        
        opcion = input("\nIngrese su opción (1-5): ").strip()
        
        if opcion == "1":
            analisis = await fixer.analizar_problemas()
            print(f"\n📊 Análisis completado:")
            print(f"   • Problemas encontrados: {len(analisis['problemas_encontrados'])}")
            
        elif opcion == "2":
            print("\n🧪 Ejecutando simulación...")
            resultados = await fixer.ejecutar_correccion(confirmar=False)
            print(f"\n📊 Resultados de la simulación:")
            print(f"   • Total procesados: {resultados['total_procesados']}")
            print(f"   • Exitosos: {resultados['exitosos']}")
            print(f"   • Errores: {resultados['errores']}")
            
        elif opcion == "3":
            print("\n⚠️  ATENCIÓN: Esta operación modificará datos reales en la base de datos")
            confirmacion = input("¿Está seguro de continuar? (escriba 'CONFIRMAR'): ").strip()
            
            if confirmacion == "CONFIRMAR":
                print("\n✅ Ejecutando corrección real...")
                resultados = await fixer.ejecutar_correccion(confirmar=True)
                print(f"\n📊 Resultados de la corrección:")
                print(f"   • Total procesados: {resultados['total_procesados']}")
                print(f"   • Exitosos: {resultados['exitosos']}")
                print(f"   • Errores: {resultados['errores']}")
                
                if resultados['errores'] > 0:
                    print(f"\n🚨 Errores encontrados:")
                    for error in resultados['errores_detalle'][:5]:
                        print(f"   • Libro {error['libro_id']}: {error['error']}")
                
            else:
                print("❌ Operación cancelada")
                
        elif opcion == "4":
            await fixer.generar_reporte()
            
        elif opcion == "5":
            print("\n👋 Saliendo del script...")
            break
            
        else:
            print("❌ Opción inválida. Intente nuevamente.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        sys.exit(1)
