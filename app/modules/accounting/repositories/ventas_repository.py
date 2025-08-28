"""
VentasRepository - Capa de acceso a datos para Registro de Ventas
================================================================

Repositorio especializado para operaciones de base de datos relacionadas
con el Registro de Ventas según especificaciones SUNAT PLE 140000.

Responsabilidades:
- Operaciones CRUD optimizadas para MongoDB
- Índices especializados para consultas de ventas
- Agregaciones para reportes y totales
- Consultas específicas para generación PLE
- Manejo de transacciones y consistencia

Patrón utilizado: Repository Pattern
Basado en documentación oficial SUNAT PLE 140000

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from decimal import Decimal
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

from ..schemas.schemas_ventas import (
    TipoComprobanteVenta,
    TipoDocumentoCliente,
    EstadoOperacionVenta
)
from ....shared.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class VentasRepository:
    """Repositorio para gestión de datos de ventas en MongoDB"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Inicializar repositorio de ventas
        
        Args:
            database: Instancia de base de datos MongoDB
        """
        self.db = database
        self.collection: AsyncIOMotorCollection = database.registro_ventas
        self.logger = logging.getLogger(__name__)
    
    async def create_indexes(self):
        """
        Crear índices optimizados para operaciones de ventas
        
        Índices incluidos:
        - Único: empresa_id + tipo_comprobante + serie + numero + periodo
        - Búsqueda: empresa_id + periodo + estado_operacion
        - Consultas: empresa_id + fecha_emision
        - Cliente: empresa_id + numero_documento_cliente
        - Texto: razon_social_cliente
        - PLE: empresa_id + periodo + tipo_comprobante
        """
        try:
            indices = [
                # Índice único para evitar duplicados de comprobantes
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("tipo_comprobante", ASCENDING),
                        ("serie_comprobante", ASCENDING),
                        ("numero_comprobante", ASCENDING),
                        ("periodo", ASCENDING)
                    ],
                    unique=True,
                    name="unique_comprobante_periodo",
                    partialFilterExpression={
                        "estado_operacion": {"$ne": "anulado"}
                    }
                ),
                
                # Índice para consultas por empresa y período
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("periodo", ASCENDING),
                        ("estado_operacion", ASCENDING)
                    ],
                    name="empresa_periodo_estado"
                ),
                
                # Índice para consultas por fecha
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("fecha_emision", DESCENDING),
                        ("tipo_comprobante", ASCENDING)
                    ],
                    name="empresa_fecha_tipo"
                ),
                
                # Índice para búsqueda por cliente
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("numero_documento_cliente", ASCENDING),
                        ("fecha_emision", DESCENDING)
                    ],
                    name="empresa_cliente_fecha"
                ),
                
                # Índice de texto para búsqueda por razón social
                IndexModel(
                    [
                        ("razon_social_cliente", TEXT),
                        ("numero_comprobante", TEXT)
                    ],
                    name="texto_cliente_comprobante"
                ),
                
                # Índice para generación PLE
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("periodo", ASCENDING),
                        ("tipo_comprobante", ASCENDING),
                        ("fecha_emision", ASCENDING)
                    ],
                    name="ple_generation_index"
                ),
                
                # Índice para análisis de montos
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("periodo", ASCENDING),
                        ("importe_total", DESCENDING)
                    ],
                    name="empresa_periodo_monto"
                ),
                
                # Índice para auditoria
                IndexModel(
                    [
                        ("empresa_id", ASCENDING),
                        ("fecha_creacion", DESCENDING),
                        ("fecha_actualizacion", DESCENDING)
                    ],
                    name="auditoria_fechas"
                )
            ]
            
            await self.collection.create_indexes(indices)
            self.logger.info(f"Índices creados exitosamente para registro_ventas")
            
        except Exception as e:
            self.logger.error(f"Error creando índices: {str(e)}")
            raise DatabaseException(f"Error configurando índices: {str(e)}")
    
    # ================================
    # OPERACIONES CRUD BÁSICAS
    # ================================
    
    async def insert_one(self, documento: Dict[str, Any]) -> str:
        """
        Insertar un nuevo registro de venta
        
        Args:
            documento: Datos del registro
            
        Returns:
            str: ID del documento insertado
        """
        try:
            resultado = await self.collection.insert_one(documento)
            return str(resultado.inserted_id)
        except Exception as e:
            self.logger.error(f"Error insertando registro: {str(e)}")
            raise DatabaseException(f"Error insertando registro: {str(e)}")
    
    async def find_by_id(self, registro_id: str, empresa_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar registro por ID y empresa
        
        Args:
            registro_id: ID del registro
            empresa_id: ID de la empresa
            
        Returns:
            Dict o None si no se encuentra
        """
        try:
            return await self.collection.find_one({
                "_id": ObjectId(registro_id),
                "empresa_id": empresa_id
            })
        except Exception as e:
            self.logger.error(f"Error buscando registro {registro_id}: {str(e)}")
            raise DatabaseException(f"Error buscando registro: {str(e)}")
    
    async def update_one(
        self,
        registro_id: str,
        empresa_id: str,
        datos_actualizacion: Dict[str, Any]
    ) -> bool:
        """
        Actualizar un registro existente
        
        Args:
            registro_id: ID del registro
            empresa_id: ID de la empresa
            datos_actualizacion: Nuevos datos
            
        Returns:
            bool: True si se actualizó exitosamente
        """
        try:
            resultado = await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {"$set": datos_actualizacion}
            )
            return resultado.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error actualizando registro {registro_id}: {str(e)}")
            raise DatabaseException(f"Error actualizando registro: {str(e)}")
    
    async def delete_one(self, registro_id: str, empresa_id: str) -> bool:
        """
        Eliminar registro (eliminación lógica)
        
        Args:
            registro_id: ID del registro
            empresa_id: ID de la empresa
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        try:
            resultado = await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {
                    "$set": {
                        "estado_operacion": EstadoOperacionVenta.ANULADO.value,
                        "fecha_actualizacion": datetime.utcnow()
                    }
                }
            )
            return resultado.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error eliminando registro {registro_id}: {str(e)}")
            raise DatabaseException(f"Error eliminando registro: {str(e)}")
    
    # ================================
    # CONSULTAS ESPECIALIZADAS
    # ================================
    
    async def find_by_comprobante(
        self,
        empresa_id: str,
        tipo_comprobante: TipoComprobanteVenta,
        serie: Optional[str],
        numero: str,
        periodo: str,
        excluir_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Buscar registro por datos del comprobante
        
        Args:
            empresa_id: ID de la empresa
            tipo_comprobante: Tipo de comprobante
            serie: Serie del comprobante (opcional)
            numero: Número del comprobante
            periodo: Período AAAAMM
            excluir_id: ID a excluir de la búsqueda (para actualizaciones)
            
        Returns:
            Dict o None si no se encuentra
        """
        try:
            filtros = {
                "empresa_id": empresa_id,
                "tipo_comprobante": tipo_comprobante.value,
                "numero_comprobante": numero,
                "periodo": periodo,
                "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
            }
            
            if serie:
                filtros["serie_comprobante"] = serie
            
            if excluir_id:
                filtros["_id"] = {"$ne": ObjectId(excluir_id)}
            
            return await self.collection.find_one(filtros)
            
        except Exception as e:
            self.logger.error(f"Error buscando comprobante: {str(e)}")
            raise DatabaseException(f"Error buscando comprobante: {str(e)}")
    
    async def find_with_filters(
        self,
        empresa_id: str,
        filtros: Dict[str, Any],
        skip: int = 0,
        limit: int = 50,
        sort_field: str = "fecha_emision",
        sort_direction: int = -1
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Buscar registros con filtros y paginación
        
        Args:
            empresa_id: ID de la empresa
            filtros: Filtros adicionales
            skip: Registros a omitir
            limit: Límite de registros
            sort_field: Campo para ordenar
            sort_direction: Dirección del ordenamiento (1=ASC, -1=DESC)
            
        Returns:
            Tupla (registros, total_count)
        """
        try:
            # Agregar filtro de empresa
            filtros_completos = {"empresa_id": empresa_id, **filtros}
            
            # Ejecutar consultas en paralelo
            cursor = self.collection.find(filtros_completos).skip(skip).limit(limit).sort(sort_field, sort_direction)
            count_task = self.collection.count_documents(filtros_completos)
            
            # Obtener resultados
            registros = await cursor.to_list(length=limit)
            total = await count_task
            
            return registros, total
            
        except Exception as e:
            self.logger.error(f"Error buscando con filtros: {str(e)}")
            raise DatabaseException(f"Error ejecutando consulta: {str(e)}")
    
    async def find_for_ple_generation(
        self,
        empresa_id: str,
        periodo_inicio: str,
        periodo_fin: str,
        filtros_adicionales: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar registros para generación de PLE
        
        Args:
            empresa_id: ID de la empresa
            periodo_inicio: Período inicio AAAAMM
            periodo_fin: Período fin AAAAMM
            filtros_adicionales: Filtros adicionales opcionales
            
        Returns:
            List[Dict]: Registros ordenados por fecha de emisión
        """
        try:
            filtros = {
                "empresa_id": empresa_id,
                "periodo": {"$gte": periodo_inicio, "$lte": periodo_fin}
            }
            
            if filtros_adicionales:
                filtros.update(filtros_adicionales)
            
            # Ordenar por fecha de emisión y correlativo
            cursor = self.collection.find(filtros).sort([
                ("fecha_emision", ASCENDING),
                ("tipo_comprobante", ASCENDING),
                ("serie_comprobante", ASCENDING),
                ("numero_comprobante", ASCENDING)
            ])
            
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo registros para PLE: {str(e)}")
            raise DatabaseException(f"Error obteniendo registros para PLE: {str(e)}")
    
    async def find_by_cliente(
        self,
        empresa_id: str,
        numero_documento_cliente: str,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar registros por cliente y rango de fechas
        
        Args:
            empresa_id: ID de la empresa
            numero_documento_cliente: Número de documento del cliente
            fecha_inicio: Fecha inicio opcional
            fecha_fin: Fecha fin opcional
            
        Returns:
            List[Dict]: Registros del cliente
        """
        try:
            filtros = {
                "empresa_id": empresa_id,
                "numero_documento_cliente": numero_documento_cliente,
                "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
            }
            
            if fecha_inicio and fecha_fin:
                filtros["fecha_emision"] = {"$gte": fecha_inicio, "$lte": fecha_fin}
            elif fecha_inicio:
                filtros["fecha_emision"] = {"$gte": fecha_inicio}
            elif fecha_fin:
                filtros["fecha_emision"] = {"$lte": fecha_fin}
            
            cursor = self.collection.find(filtros).sort("fecha_emision", DESCENDING)
            return await cursor.to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"Error buscando registros por cliente: {str(e)}")
            raise DatabaseException(f"Error buscando por cliente: {str(e)}")
    
    # ================================
    # AGREGACIONES Y REPORTES
    # ================================
    
    async def aggregate_by_period(
        self,
        empresa_id: str,
        periodo_inicio: str,
        periodo_fin: str
    ) -> Dict[str, Any]:
        """
        Agregar datos por período para reportes
        
        Args:
            empresa_id: ID de la empresa
            periodo_inicio: Período inicio AAAAMM
            periodo_fin: Período fin AAAAMM
            
        Returns:
            Dict con totales agregados
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "empresa_id": empresa_id,
                        "periodo": {"$gte": periodo_inicio, "$lte": periodo_fin},
                        "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_registros": {"$sum": 1},
                        "total_importe": {"$sum": "$importe_total"},
                        "total_igv": {"$sum": "$igv_ipm"},
                        "total_base_gravada": {"$sum": "$base_imponible_gravada"},
                        "total_exportaciones": {"$sum": "$valor_facturado_exportacion"},
                        "total_exonerado": {"$sum": "$importe_exonerado"},
                        "total_inafecto": {"$sum": "$importe_inafecto"},
                        "tipos_comprobante": {"$addToSet": "$tipo_comprobante"}
                    }
                }
            ]
            
            resultado = await self.collection.aggregate(pipeline).to_list(length=1)
            
            if not resultado:
                return {
                    "total_registros": 0,
                    "total_importe": Decimal('0.00'),
                    "total_igv": Decimal('0.00'),
                    "total_base_gravada": Decimal('0.00'),
                    "total_exportaciones": Decimal('0.00'),
                    "total_exonerado": Decimal('0.00'),
                    "total_inafecto": Decimal('0.00'),
                    "tipos_comprobante": []
                }
            
            return resultado[0]
            
        except Exception as e:
            self.logger.error(f"Error agregando por período: {str(e)}")
            raise DatabaseException(f"Error ejecutando agregación: {str(e)}")
    
    async def aggregate_by_tipo_comprobante(
        self,
        empresa_id: str,
        periodo: str
    ) -> List[Dict[str, Any]]:
        """
        Agregar datos por tipo de comprobante
        
        Args:
            empresa_id: ID de la empresa
            periodo: Período AAAAMM
            
        Returns:
            List[Dict]: Totales por tipo de comprobante
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "empresa_id": empresa_id,
                        "periodo": periodo,
                        "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
                    }
                },
                {
                    "$group": {
                        "_id": "$tipo_comprobante",
                        "cantidad": {"$sum": 1},
                        "total_importe": {"$sum": "$importe_total"},
                        "total_igv": {"$sum": "$igv_ipm"},
                        "total_base_gravada": {"$sum": "$base_imponible_gravada"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            return await self.collection.aggregate(pipeline).to_list(length=None)
            
        except Exception as e:
            self.logger.error(f"Error agregando por tipo comprobante: {str(e)}")
            raise DatabaseException(f"Error ejecutando agregación: {str(e)}")
    
    async def get_last_comprobante_number(
        self,
        empresa_id: str,
        tipo_comprobante: TipoComprobanteVenta,
        serie: Optional[str],
        periodo: str
    ) -> Optional[str]:
        """
        Obtener el último número de comprobante para una serie
        
        Args:
            empresa_id: ID de la empresa
            tipo_comprobante: Tipo de comprobante
            serie: Serie del comprobante
            periodo: Período AAAAMM
            
        Returns:
            str: Último número de comprobante o None
        """
        try:
            filtros = {
                "empresa_id": empresa_id,
                "tipo_comprobante": tipo_comprobante.value,
                "periodo": periodo,
                "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
            }
            
            if serie:
                filtros["serie_comprobante"] = serie
            
            ultimo = await self.collection.find_one(
                filtros,
                sort=[("numero_comprobante", DESCENDING)]
            )
            
            return ultimo.get("numero_comprobante") if ultimo else None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo último número: {str(e)}")
            raise DatabaseException(f"Error obteniendo último número: {str(e)}")
    
    # ================================
    # MÉTODOS DE UTILIDAD
    # ================================
    
    async def count_by_filters(self, empresa_id: str, filtros: Dict[str, Any]) -> int:
        """Contar registros con filtros"""
        try:
            filtros_completos = {"empresa_id": empresa_id, **filtros}
            return await self.collection.count_documents(filtros_completos)
        except Exception as e:
            self.logger.error(f"Error contando registros: {str(e)}")
            raise DatabaseException(f"Error contando registros: {str(e)}")
    
    async def exists_comprobante(
        self,
        empresa_id: str,
        tipo_comprobante: TipoComprobanteVenta,
        serie: Optional[str],
        numero: str,
        periodo: str
    ) -> bool:
        """Verificar si existe un comprobante"""
        documento = await self.find_by_comprobante(
            empresa_id, tipo_comprobante, serie, numero, periodo
        )
        return documento is not None
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de la colección"""
        try:
            stats = await self.db.command("collStats", "registro_ventas")
            return {
                "total_documentos": stats.get("count", 0),
                "tamaño_coleccion": stats.get("size", 0),
                "tamaño_promedio_documento": stats.get("avgObjSize", 0),
                "total_indices": stats.get("nindexes", 0)
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}
