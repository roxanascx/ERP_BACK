"""
Script de Optimización - Índices MongoDB para Libro Mayor
=========================================================

Script para crear índices optimizados específicamente para las consultas
del Libro Mayor PLE 050200, mejorando significativamente el performance
de las operaciones de consulta y agregación.

Índices implementados:
- Consultas por empresa y período
- Consultas por cuenta contable
- Agregaciones de saldos
- Ordenamiento por fecha

Autor: Sistema ERP - FASE 3.1
Fecha: Agosto 2025
"""

import asyncio
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from datetime import datetime
import sys
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimizacion_indices.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class OptimizadorIndicesLibroMayor:
    """Optimizador de índices para Libro Mayor"""
    
    def __init__(self, mongodb_url: str = "mongodb://localhost:27017", db_name: str = "erp_db"):
        """Inicializar optimizador"""
        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.client = None
        self.db = None
        
    def conectar(self):
        """Conectar a MongoDB"""
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client[self.db_name]
            logger.info(f"✅ Conectado a MongoDB: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a MongoDB: {str(e)}")
            return False
    
    def crear_indices_asientos_contables(self):
        """Crear índices optimizados para asientos_contables"""
        logger.info("🔧 Creando índices para collection 'asientos_contables'...")
        
        collection = self.db.asientos_contables
        indices_creados = 0
        
        # Índices para Libro Mayor
        indices_libro_mayor = [
            # 1. Consultas por empresa y período (más frecuente)
            {
                "nombre": "empresa_periodo_idx",
                "campos": [("empresaId", ASCENDING), ("fecha", ASCENDING)],
                "descripcion": "Consultas por empresa y período"
            },
            
            # 2. Consultas por cuenta contable específica
            {
                "nombre": "empresa_cuenta_periodo_idx", 
                "campos": [
                    ("empresaId", ASCENDING),
                    ("movimientos.codigoCuentaContable", ASCENDING),
                    ("fecha", ASCENDING)
                ],
                "descripcion": "Consultas por empresa, cuenta y período"
            },
            
            # 3. Agregaciones de saldos por período
            {
                "nombre": "periodo_agregacion_idx",
                "campos": [
                    ("fecha", ASCENDING),
                    ("empresaId", ASCENDING),
                    ("movimientos.importeDebe", ASCENDING),
                    ("movimientos.importeHaber", ASCENDING)
                ],
                "descripcion": "Agregaciones de saldos por período"
            },
            
            # 4. Consultas por número de asiento
            {
                "nombre": "empresa_numero_asiento_idx",
                "campos": [
                    ("empresaId", ASCENDING),
                    ("numeroAsiento", ASCENDING)
                ],
                "descripcion": "Consultas por número de asiento"
            },
            
            # 5. Índice compuesto para ordenamiento por fecha descendente
            {
                "nombre": "empresa_fecha_desc_idx",
                "campos": [
                    ("empresaId", ASCENDING),
                    ("fecha", DESCENDING)
                ],
                "descripcion": "Ordenamiento por fecha descendente"
            },
            
            # 6. Índice para consultas de rangos de fecha
            {
                "nombre": "fecha_rango_idx",
                "campos": [("fecha", ASCENDING)],
                "descripcion": "Consultas de rangos de fecha"
            }
        ]
        
        for indice in indices_libro_mayor:
            try:
                collection.create_index(
                    indice["campos"],
                    name=indice["nombre"],
                    background=True
                )
                logger.info(f"   ✅ Creado: {indice['nombre']} - {indice['descripcion']}")
                indices_creados += 1
                
            except DuplicateKeyError:
                logger.info(f"   ⚠️  Ya existe: {indice['nombre']}")
            except Exception as e:
                logger.error(f"   ❌ Error creando {indice['nombre']}: {str(e)}")
        
        return indices_creados
    
    def crear_indices_empresas(self):
        """Crear índices optimizados para empresas"""
        logger.info("🔧 Creando índices para collection 'companies'...")
        
        collection = self.db.companies
        indices_creados = 0
        
        indices_empresas = [
            # 1. Búsqueda por RUC
            {
                "nombre": "ruc_idx",
                "campos": [("ruc", ASCENDING)],
                "descripcion": "Búsqueda por RUC"
            },
            
            # 2. Búsqueda por estado activo
            {
                "nombre": "activo_idx", 
                "campos": [("activo", ASCENDING)],
                "descripcion": "Filtro por empresas activas"
            },
            
            # 3. Índice compuesto RUC + estado
            {
                "nombre": "ruc_activo_idx",
                "campos": [("ruc", ASCENDING), ("activo", ASCENDING)],
                "descripcion": "Búsqueda por RUC y estado"
            }
        ]
        
        for indice in indices_empresas:
            try:
                collection.create_index(
                    indice["campos"],
                    name=indice["nombre"],
                    background=True
                )
                logger.info(f"   ✅ Creado: {indice['nombre']} - {indice['descripcion']}")
                indices_creados += 1
                
            except DuplicateKeyError:
                logger.info(f"   ⚠️  Ya existe: {indice['nombre']}")
            except Exception as e:
                logger.error(f"   ❌ Error creando {indice['nombre']}: {str(e)}")
        
        return indices_creados
    
    def analizar_performance_indices(self):
        """Analizar performance de índices existentes"""
        logger.info("📊 Analizando performance de índices...")
        
        # Analizar asientos_contables
        collection = self.db.asientos_contables
        
        # Obtener estadísticas de la colección
        stats = self.db.command("collStats", "asientos_contables")
        
        logger.info(f"📈 Estadísticas de asientos_contables:")
        logger.info(f"   - Documentos: {stats.get('count', 0):,}")
        logger.info(f"   - Tamaño total: {stats.get('size', 0):,} bytes")
        logger.info(f"   - Tamaño promedio doc: {stats.get('avgObjSize', 0):,} bytes")
        
        # Listar índices existentes
        indices = list(collection.list_indexes())
        logger.info(f"   - Índices existentes: {len(indices)}")
        
        for indice in indices:
            nombre = indice.get('name', 'sin_nombre')
            claves = indice.get('key', {})
            logger.info(f"     • {nombre}: {dict(claves)}")
        
        return stats
    
    def ejecutar_optimizacion_completa(self):
        """Ejecutar optimización completa"""
        logger.info("🚀 Iniciando optimización completa de índices para Libro Mayor")
        
        if not self.conectar():
            return False
        
        try:
            # Analizar estado actual
            stats_antes = self.analizar_performance_indices()
            
            # Crear índices optimizados
            indices_asientos = self.crear_indices_asientos_contables()
            indices_empresas = self.crear_indices_empresas()
            
            total_indices = indices_asientos + indices_empresas
            
            logger.info(f"🎯 Optimización completada:")
            logger.info(f"   ✅ Índices creados: {total_indices}")
            logger.info(f"   📊 Performance mejorado para consultas del Libro Mayor")
            
            # Recomendaciones adicionales
            self.generar_recomendaciones_performance()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error durante optimización: {str(e)}")
            return False
        
        finally:
            if self.client:
                self.client.close()
                logger.info("🔐 Conexión MongoDB cerrada")
    
    def generar_recomendaciones_performance(self):
        """Generar recomendaciones adicionales de performance"""
        logger.info("💡 Recomendaciones adicionales de performance:")
        
        recomendaciones = [
            "1. Configurar readPreference a 'secondaryPreferred' para consultas de solo lectura",
            "2. Usar projection para limitar campos devueltos en consultas grandes",
            "3. Implementar paginación para consultas con muchos resultados",
            "4. Considerar sharding si el volumen de datos supera 100GB",
            "5. Monitorear uso de índices con db.collection.explain()",
            "6. Configurar TTL indexes para datos temporales si aplica"
        ]
        
        for rec in recomendaciones:
            logger.info(f"   💡 {rec}")


def main():
    """Función principal"""
    print("🔧 Optimizador de Índices - Libro Mayor PLE 050200")
    print("=" * 60)
    
    # Configuración
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "erp_db")
    
    print(f"📡 MongoDB URL: {MONGODB_URL}")
    print(f"🗄️  Base de datos: {DB_NAME}")
    print()
    
    # Ejecutar optimización
    optimizador = OptimizadorIndicesLibroMayor(MONGODB_URL, DB_NAME)
    
    exito = optimizador.ejecutar_optimizacion_completa()
    
    if exito:
        print("\n🎉 ¡Optimización completada exitosamente!")
        print("📈 El performance de las consultas del Libro Mayor ha sido mejorado")
    else:
        print("\n❌ Error durante la optimización")
        print("📝 Revisar logs para más detalles")
    
    return exito


if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
