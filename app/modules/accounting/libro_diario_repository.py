"""
Repository para operaciones de Libro Diario con MongoDB
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.modules.accounting.libro_diario_models import (
    LibroDiarioModel, 
    AsientoContableModel, 
    LibroDiarioStats
)


class LibroDiarioRepository:
    """Repository para operaciones CRUD de Libro Diario"""
    
    def __init__(self):
        self.db = get_database()
        self.libro_model = LibroDiarioModel(self.db)
        self.asiento_model = AsientoContableModel(self.db)
        self.stats = LibroDiarioStats(self.db)
    
    # =====================================
    # OPERACIONES DE LIBRO DIARIO
    # =====================================
    
    async def crear_libro(self, libro_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear un nuevo libro diario"""
        try:
            libro_doc = self.libro_model.to_dict(libro_data)
            result = await self.libro_model.collection.insert_one(libro_doc)
            
            # Obtener el documento insertado
            libro_creado = await self.libro_model.collection.find_one({"_id": result.inserted_id})
            return self.libro_model.from_dict(libro_creado)
            
        except Exception as e:
            raise Exception(f"Error al crear libro diario: {str(e)}")
    
    async def obtener_libro(self, libro_id: str) -> Optional[Dict[str, Any]]:
        """Obtener un libro diario por ID"""
        try:
            libro = await self.libro_model.collection.find_one({"_id": ObjectId(libro_id)})
            if not libro:
                return None
            
            # Cargar asientos asociados
            asientos_cursor = self.asiento_model.collection.find({"libroId": libro_id})
            asientos = await asientos_cursor.to_list(length=None)
            libro["asientos"] = [self.asiento_model.from_dict(asiento) for asiento in asientos]
            
            return self.libro_model.from_dict(libro)
            
        except Exception as e:
            raise Exception(f"Error al obtener libro diario: {str(e)}")
    
    async def actualizar_libro(self, libro_id: str, libro_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Actualizar un libro diario"""
        try:
            # Preparar datos de actualización
            update_data = {
                k: v for k, v in libro_data.items() 
                if k not in ["id", "_id", "fechaCreacion", "asientos"]
            }
            update_data["fechaModificacion"] = datetime.utcnow()
            
            result = await self.libro_model.collection.update_one(
                {"_id": ObjectId(libro_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                return None
            
            return await self.obtener_libro(libro_id)
            
        except Exception as e:
            raise Exception(f"Error al actualizar libro diario: {str(e)}")
    
    async def eliminar_libro(self, libro_id: str) -> bool:
        """Eliminar un libro diario y sus asientos asociados"""
        try:
            # Eliminar asientos asociados
            await self.asiento_model.collection.delete_many({"libroId": libro_id})
            
            # Eliminar libro
            result = await self.libro_model.collection.delete_one({"_id": ObjectId(libro_id)})
            return result.deleted_count > 0
            
        except Exception as e:
            raise Exception(f"Error al eliminar libro diario: {str(e)}")
    
    async def listar_libros_por_empresa(
        self, 
        empresa_id: str, 
        filtros: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Listar libros diario por empresa con filtros opcionales"""
        try:
            # Construir filtro base
            filtro = {"empresaId": empresa_id}
            
            if filtros:
                if filtros.get("periodo"):
                    filtro["periodo"] = filtros["periodo"]
                
                if filtros.get("estado"):
                    filtro["estado"] = filtros["estado"]
                
                if filtros.get("fechaDesde") or filtros.get("fechaHasta"):
                    fecha_filtro = {}
                    if filtros.get("fechaDesde"):
                        fecha_filtro["$gte"] = datetime.fromisoformat(filtros["fechaDesde"])
                    if filtros.get("fechaHasta"):
                        fecha_filtro["$lte"] = datetime.fromisoformat(filtros["fechaHasta"])
                    filtro["fechaCreacion"] = fecha_filtro
                
                if filtros.get("busqueda"):
                    filtro["$text"] = {"$search": filtros["busqueda"]}
            
            # Ejecutar consulta
            cursor = self.libro_model.collection.find(filtro).sort("fechaCreacion", -1)
            libros = []
            
            # Convertir cursor a lista de documentos
            libros_docs = await cursor.to_list(length=None)
            
            for libro_doc in libros_docs:
                libro = self.libro_model.from_dict(libro_doc)
                
                # Para la lista, solo inicializar asientos vacío y calcular totales básicos
                libro["asientos"] = []  # Lista vacía para evitar problemas de validación
                
                # Los totales ya están almacenados en el documento, usar esos valores
                libro["totalDebe"] = libro_doc.get("totalDebe", 0.0)
                libro["totalHaber"] = libro_doc.get("totalHaber", 0.0)
                
                libros.append(libro)
            
            return libros
            
        except Exception as e:
            raise Exception(f"Error al listar libros diario: {str(e)}")
    
    # =====================================
    # OPERACIONES DE ASIENTOS CONTABLES
    # =====================================
    
    async def agregar_asiento(self, libro_id: str, asiento_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agregar un asiento contable a un libro"""
        try:
            # Verificar que el libro existe
            libro = await self.obtener_libro(libro_id)
            if not libro:
                raise Exception("Libro diario no encontrado")
            
            # Preparar datos del asiento
            asiento_data["libroId"] = libro_id
            asiento_doc = self.asiento_model.to_dict(asiento_data)
            
            # Insertar asiento (CORREGIDO: agregar await)
            result = await self.asiento_model.collection.insert_one(asiento_doc)
            
            # Actualizar totales del libro (CORREGIDO: agregar await)
            await self.libro_model.actualizar_totales(libro_id)
            
            # Obtener asiento creado (CORREGIDO: agregar await)
            asiento_creado = await self.asiento_model.collection.find_one({"_id": result.inserted_id})
            return self.asiento_model.from_dict(asiento_creado)
            
        except DuplicateKeyError:
            raise Exception("El número correlativo ya existe para esta empresa")
        except Exception as e:
            raise Exception(f"Error al agregar asiento: {str(e)}")
    
    async def actualizar_asiento(
        self, 
        libro_id: str, 
        asiento_id: str, 
        asiento_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Actualizar un asiento contable"""
        try:
            # Preparar datos de actualización
            update_data = {
                k: v for k, v in asiento_data.items() 
                if k not in ["id", "_id", "fechaCreacion", "libroId"]
            }
            update_data["fechaModificacion"] = datetime.utcnow()
            
            result = self.asiento_model.collection.update_one(
                {"_id": ObjectId(asiento_id), "libroId": libro_id},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                return None
            
            # Actualizar totales del libro
            self.libro_model.actualizar_totales(libro_id)
            
            # Obtener asiento actualizado
            asiento = self.asiento_model.collection.find_one({"_id": ObjectId(asiento_id)})
            return self.asiento_model.from_dict(asiento)
            
        except Exception as e:
            raise Exception(f"Error al actualizar asiento: {str(e)}")
    
    async def eliminar_asiento(self, libro_id: str, asiento_id: str) -> bool:
        """Eliminar un asiento contable"""
        try:
            result = await self.asiento_model.collection.delete_one({
                "_id": ObjectId(asiento_id),
                "libroId": libro_id
            })
            
            if result.deleted_count > 0:
                # Actualizar totales del libro (método asíncrono)
                await self.libro_model.actualizar_totales(libro_id)
                return True
            
            return False
            
        except Exception as e:
            raise Exception(f"Error al eliminar asiento: {str(e)}")
    
    # =====================================
    # OPERACIONES DE CONSULTA Y ESTADÍSTICAS
    # =====================================
    
    async def obtener_resumen(
        self, 
        empresa_id: str, 
        periodo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtener resumen estadístico del libro diario"""
        try:
            return await self.stats.generar_resumen(empresa_id, periodo)
        except Exception as e:
            raise Exception(f"Error al obtener resumen: {str(e)}")
    
    async def validar_libro(self, libro_id: str) -> Dict[str, Any]:
        """Validar un libro diario completo"""
        try:
            libro = await self.obtener_libro(libro_id)
            if not libro:
                return {
                    "isValid": False,
                    "errors": ["Libro diario no encontrado"],
                    "warnings": [],
                    "asientosSinBalancear": []
                }
            
            errors = []
            warnings = []
            asientos_sin_balancear = []
            
            # Validar que el libro esté balanceado
            diferencia = abs(libro["totalDebe"] - libro["totalHaber"])
            if diferencia > 0.01:
                errors.append(f"El libro no está balanceado. Diferencia: {diferencia}")
            
            # Validar asientos individuales
            for asiento in libro.get("asientos", []):
                if asiento.get("debe", 0) == 0 and asiento.get("haber", 0) == 0:
                    errors.append(f"Asiento {asiento.get('numeroCorrelativo')} sin movimiento")
                    asientos_sin_balancear.append(asiento.get("numeroCorrelativo"))
                
                if not asiento.get("glosa", "").strip():
                    warnings.append(f"Asiento {asiento.get('numeroCorrelativo')} sin glosa")
            
            return {
                "isValid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "asientosSinBalancear": asientos_sin_balancear
            }
            
        except Exception as e:
            raise Exception(f"Error en validación: {str(e)}")
    
    async def obtener_siguiente_correlativo(self, empresa_id: str, periodo: str) -> str:
        """Obtener el siguiente número correlativo disponible"""
        try:
            # Buscar el último correlativo usado en el período
            filtro = {
                "empresaId": empresa_id,
                "fecha": {"$regex": f"^{periodo}"}
            }
            
            ultimo_asiento = self.asiento_model.collection.find_one(
                filtro,
                sort=[("numeroCorrelativo", -1)]
            )
            
            if ultimo_asiento:
                try:
                    ultimo_numero = int(ultimo_asiento["numeroCorrelativo"])
                    siguiente = ultimo_numero + 1
                except ValueError:
                    siguiente = 1
            else:
                siguiente = 1
            
            return str(siguiente).zfill(6)  # Formato: 000001
            
        except Exception as e:
            raise Exception(f"Error al obtener correlativo: {str(e)}")
    
    async def buscar_cuentas_contables(
        self, 
        busqueda: str, 
        empresa_id: str, 
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """Buscar cuentas contables para autocompletado"""
        try:
            from app.modules.accounting.repositories import AccountingRepository
            
            # Usar el repositorio existente de contabilidad
            accounting_repo = AccountingRepository()
            cuentas = await accounting_repo.search_cuentas(
                busqueda, 
                empresa_id, 
                limite
            )
            
            # Adaptar formato para el autocompletado
            return [
                {
                    "codigo": cuenta["codigo"],
                    "denominacion": cuenta["descripcion"],
                    "naturaleza": cuenta.get("naturaleza", "DEUDORA"),
                    "nivel": cuenta.get("nivel", 1),
                    "activa": True
                }
                for cuenta in cuentas
            ]
            
        except Exception as e:
            raise Exception(f"Error al buscar cuentas: {str(e)}")
    
    async def buscar_libro_por_descripcion_periodo(
        self, 
        empresa_id: str, 
        descripcion: str, 
        periodo: str
    ) -> Optional[Dict[str, Any]]:
        """Buscar si existe un libro con la misma descripción y período para una empresa"""
        try:
            libro = await self.libro_model.collection.find_one({
                "empresaId": empresa_id,
                "descripcion": descripcion,
                "periodo": periodo
            })
            
            if libro:
                return self.libro_model.from_dict(libro)
            return None
            
        except Exception as e:
            raise Exception(f"Error al buscar libro por descripción y período: {str(e)}")
