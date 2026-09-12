"""
Modelos MongoDB para el módulo de Libro Diario
"""
from pymongo import MongoClient
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class AsientoContableModel:
    """Modelo para Asiento Contable en MongoDB"""
    
    def __init__(self, db):
        self.collection = db["asientos_contables"]
        self._create_indexes()
    
    def _create_indexes(self):
        """Crear índices para optimizar consultas"""
        # Índice compuesto para empresa y fecha
        self.collection.create_index([
            ("empresaId", 1),
            ("fecha", -1)
        ])
        
        # Índice para número correlativo único por empresa
        self.collection.create_index([
            ("empresaId", 1),
            ("numeroCorrelativo", 1)
        ], unique=True)
        
        # Índice para búsquedas por cuenta contable
        self.collection.create_index([
            ("empresaId", 1),
            ("cuentaContable.codigo", 1)
        ])

        # Índice para agrupar las líneas de una misma operación/asiento padre.
        # Nombre explícito porque ya existe en la base de datos (creado antes
        # por scripts/optimizar_indices_libro_mayor.py) con este mismo nombre;
        # sin el `name=` aquí, pymongo genera un nombre distinto para la misma
        # combinación de campos y Mongo lo rechaza (IndexOptionsConflict).
        self.collection.create_index([
            ("empresaId", 1),
            ("numeroAsiento", 1)
        ], name="empresa_numero_asiento_idx")
        
        # Índice de texto para búsquedas en glosa
        self.collection.create_index([
            ("glosa", "text"),
            ("numeroDocumento", "text")
        ])
    
    def to_dict(self, asiento_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir datos del asiento para MongoDB"""
        asiento = asiento_data.copy()
        
        # Agregar metadatos
        now = datetime.utcnow()
        if "_id" not in asiento:
            asiento["fechaCreacion"] = now
        asiento["fechaModificacion"] = now
        
        # Validaciones básicas
        if asiento.get("debe", 0) < 0 or asiento.get("haber", 0) < 0:
            raise ValueError("Los valores de debe y haber no pueden ser negativos")
        
        if asiento.get("debe", 0) > 0 and asiento.get("haber", 0) > 0:
            raise ValueError("No puede tener valores en debe y haber simultáneamente")
        
        return asiento
    
    def from_dict(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir documento de MongoDB a formato API"""
        if doc is None:
            return None
        
        doc["id"] = str(doc.pop("_id"))
        return doc


class LibroDiarioModel:
    """Modelo para Libro Diario en MongoDB"""
    
    def __init__(self, db):
        self.collection = db["libros_diario"]
        self.asientos_collection = db["asientos_contables"]
        self._create_indexes()
    
    def _create_indexes(self):
        """Crear índices para optimizar consultas"""
        # Índice compuesto para empresa y período
        self.collection.create_index([
            ("empresaId", 1),
            ("periodo", -1)
        ])
        
        # Índice para búsquedas por estado
        self.collection.create_index([
            ("empresaId", 1),
            ("estado", 1)
        ])
        
        # Índice para fechas de creación
        self.collection.create_index([
            ("empresaId", 1),
            ("fechaCreacion", -1)
        ])
        
        # Índice de texto para búsquedas en descripción
        self.collection.create_index([
            ("descripcion", "text")
        ])
    
    def to_dict(self, libro_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir datos del libro para MongoDB"""
        libro = libro_data.copy()
        
        # Agregar metadatos
        now = datetime.utcnow()
        if "_id" not in libro:
            libro["fechaCreacion"] = now
        libro["fechaModificacion"] = now
        
        # Inicializar campos calculados
        libro.setdefault("totalDebe", 0.0)
        libro.setdefault("totalHaber", 0.0)
        libro.setdefault("asientos", [])
        
        return libro
    
    def from_dict(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir documento de MongoDB a formato API"""
        if doc is None:
            return None
        
        doc["id"] = str(doc.pop("_id"))
        return doc
    
    async def calcular_totales(self, libro_id: str) -> Dict[str, float]:
        """Calcular totales de debe y haber para un libro"""
        pipeline = [
            {"$match": {"libroId": libro_id}},
            {"$group": {
                "_id": None,
                "totalDebe": {"$sum": "$debe"},
                "totalHaber": {"$sum": "$haber"},
                "totalAsientos": {"$sum": 1}
            }}
        ]
        
        result = []
        async for doc in self.asientos_collection.aggregate(pipeline):
            result.append(doc)
            
        if result:
            return {
                "totalDebe": result[0]["totalDebe"],
                "totalHaber": result[0]["totalHaber"],
                "totalAsientos": result[0]["totalAsientos"]
            }
        
        return {"totalDebe": 0.0, "totalHaber": 0.0, "totalAsientos": 0}
    
    async def actualizar_totales(self, libro_id: str):
        """Actualizar los totales calculados en el libro"""
        totales = await self.calcular_totales(libro_id)
        
        await self.collection.update_one(
            {"_id": ObjectId(libro_id)},
            {
                "$set": {
                    "totalDebe": totales["totalDebe"],
                    "totalHaber": totales["totalHaber"],
                    "fechaModificacion": datetime.utcnow()
                }
            }
        )
        
        return totales


class LibroDiarioStats:
    """Clase para generar estadísticas del Libro Diario"""
    
    def __init__(self, db):
        self.libros_collection = db["libros_diario"]
        self.asientos_collection = db["asientos_contables"]
    
    async def generar_resumen(self, empresa_id: str, periodo: Optional[str] = None) -> Dict[str, Any]:
        """Generar resumen estadístico para una empresa"""
        
        # Filtro base
        filtro_libros = {"empresaId": empresa_id}
        filtro_asientos = {"empresaId": empresa_id}
        
        if periodo:
            filtro_libros["periodo"] = periodo
            # Para asientos, filtrar por fecha si es período específico
            if len(periodo) == 7:  # YYYY-MM
                year, month = periodo.split("-")
                filtro_asientos["fecha"] = {
                    "$regex": f"^{year}-{month.zfill(2)}"
                }
            else:  # YYYY
                filtro_asientos["fecha"] = {
                    "$regex": f"^{periodo}"
                }
        
        # Contar libros
        total_libros = await self.libros_collection.count_documents(filtro_libros)
        
        # Contar asientos por estado
        pipeline_estados = [
            {"$match": filtro_libros},
            {"$group": {
                "_id": "$estado",
                "count": {"$sum": 1}
            }}
        ]
        
        estados_cursor = self.libros_collection.aggregate(pipeline_estados)
        estados_result = await estados_cursor.to_list(length=None)
        asientos_por_estado = {estado["_id"]: estado["count"] for estado in estados_result}
        
        # Totales de debe/haber
        pipeline_totales = [
            {"$match": filtro_asientos},
            {"$group": {
                "_id": None,
                "totalDebe": {"$sum": "$debe"},
                "totalHaber": {"$sum": "$haber"},
                "totalAsientos": {"$sum": 1}
            }}
        ]
        
        totales_cursor = self.asientos_collection.aggregate(pipeline_totales)
        totales_result = await totales_cursor.to_list(length=None)
        if totales_result:
            totales = totales_result[0]
        else:
            totales = {"totalDebe": 0, "totalHaber": 0, "totalAsientos": 0}
        
        # Último libro creado
        ultimo_libro = await self.libros_collection.find_one(
            filtro_libros,
            sort=[("fechaCreacion", -1)]
        )
        
        ultimo_libro_info = None
        if ultimo_libro:
            ultimo_libro_info = {
                "id": str(ultimo_libro["_id"]),
                "descripcion": ultimo_libro["descripcion"],
                "fechaCreacion": ultimo_libro["fechaCreacion"].isoformat()
            }
        
        # Períodos disponibles
        periodos = await self.libros_collection.distinct("periodo", {"empresaId": empresa_id})
        periodos.sort(reverse=True)
        
        return {
            "totalLibros": total_libros,
            "totalAsientos": totales["totalAsientos"],
            "totalDebe": totales["totalDebe"],
            "totalHaber": totales["totalHaber"],
            "diferencia": totales["totalDebe"] - totales["totalHaber"],
            "balanceado": abs(totales["totalDebe"] - totales["totalHaber"]) < 0.01,
            "periodos": periodos,
            "ultimaModificacion": datetime.utcnow(),
            "asientosPorEstado": asientos_por_estado,
            "ultimoLibro": ultimo_libro_info
        }
