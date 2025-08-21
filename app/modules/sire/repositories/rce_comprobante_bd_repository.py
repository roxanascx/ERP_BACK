"""
Repositorio para operaciones de comprobantes RCE en base de datos
Maneja todas las operaciones CRUD y consultas especializadas
"""

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from bson import ObjectId

from ..models.rce_comprobante_bd import (
    RceComprobanteBD, 
    RceComprobanteBDCreate, 
    RceComprobanteBDResponse,
    RceGuardarResponse,
    RceEstadisticasBD
)
from ....shared.exceptions import SireException


class RceComprobanteBDRepository:
    """Repositorio para operaciones de comprobantes en BD"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection: AsyncIOMotorCollection = db.rce_comprobantes
    
    async def inicializar_indices(self):
        """Crear índices necesarios para optimizar consultas"""
        try:
            # Índice único para evitar duplicados
            await self.collection.create_index([
                ("ruc", 1),
                ("periodo", 1),
                ("ruc_proveedor", 1),
                ("tipo_documento", 1),
                ("serie_comprobante", 1),
                ("numero_comprobante", 1)
            ], unique=True, name="idx_unique_comprobante")
            
            # Índices para consultas frecuentes
            await self.collection.create_index([("ruc", 1), ("periodo", 1)], name="idx_ruc_periodo")
            await self.collection.create_index([("ruc_proveedor", 1)], name="idx_ruc_proveedor")
            await self.collection.create_index([("fecha_emision", 1)], name="idx_fecha_emision")
            await self.collection.create_index([("fecha_registro", 1)], name="idx_fecha_registro")
            await self.collection.create_index([("estado", 1)], name="idx_estado")
            await self.collection.create_index([("hash_comprobante", 1)], name="idx_hash_comprobante")
            
            print("✅ Índices de RCE comprobantes creados exitosamente")
            
        except Exception as e:
            print(f"⚠️ Error creando índices: {e}")
    
    def _generar_hash_comprobante(self, comprobante: RceComprobanteBDCreate) -> str:
        """Generar hash único para identificar duplicados"""
        data = f"{comprobante.ruc}|{comprobante.periodo}|{comprobante.ruc_proveedor}|{comprobante.tipo_documento}|{comprobante.serie_comprobante}|{comprobante.numero_comprobante}|{comprobante.fecha_emision}|{comprobante.importe_total}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def guardar_comprobantes(
        self, 
        comprobantes: List[RceComprobanteBDCreate]
    ) -> RceGuardarResponse:
        """Guardar comprobantes evitando duplicados"""
        
        guardados = 0
        actualizados = 0
        duplicados = 0
        errores = 0
        detalles_errores = []
        
        for comprobante_data in comprobantes:
            try:
                # Generar hash único
                hash_comprobante = self._generar_hash_comprobante(comprobante_data)
                
                # Verificar si ya existe
                filtro_existente = {
                    "ruc": comprobante_data.ruc,
                    "periodo": comprobante_data.periodo,
                    "ruc_proveedor": comprobante_data.ruc_proveedor,
                    "tipo_documento": comprobante_data.tipo_documento,
                    "serie_comprobante": comprobante_data.serie_comprobante,
                    "numero_comprobante": comprobante_data.numero_comprobante
                }
                
                existente = await self.collection.find_one(filtro_existente)
                
                # Preparar documento para guardar
                documento = RceComprobanteBD(
                    **comprobante_data.dict(),
                    hash_comprobante=hash_comprobante,
                    fecha_registro=datetime.utcnow(),
                    estado="GUARDADO"
                )
                
                if existente:
                    # Verificar si hay cambios
                    if existente.get("hash_comprobante") == hash_comprobante:
                        duplicados += 1
                    else:
                        # Actualizar registro existente
                        documento.fecha_actualizacion = datetime.utcnow()
                        await self.collection.update_one(
                            {"_id": existente["_id"]},
                            {"$set": documento.dict(exclude={"id"}, by_alias=True)}
                        )
                        actualizados += 1
                else:
                    # Insertar nuevo registro
                    await self.collection.insert_one(
                        documento.dict(exclude={"id"}, by_alias=True)
                    )
                    guardados += 1
                    
            except Exception as e:
                errores += 1
                detalles_errores.append({
                    "comprobante": f"{comprobante_data.serie_comprobante}-{comprobante_data.numero_comprobante}",
                    "error": str(e)
                })
        
        return RceGuardarResponse(
            exitoso=errores == 0,
            mensaje=f"Procesados {len(comprobantes)} comprobantes: {guardados} guardados, {actualizados} actualizados, {duplicados} duplicados, {errores} errores",
            comprobantes_guardados=guardados,
            comprobantes_actualizados=actualizados,
            comprobantes_duplicados=duplicados,
            errores=errores,
            detalles={
                "errores_detalle": detalles_errores
            } if detalles_errores else None
        )
    
    async def consultar_comprobantes(
        self,
        ruc: str,
        periodo: Optional[str] = None,
        ruc_proveedor: Optional[str] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        estado: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[RceComprobanteBDResponse], int]:
        """Consultar comprobantes con filtros y paginación"""
        
        # Construir filtro de consulta
        filtro = {"ruc": ruc}
        
        if periodo:
            filtro["periodo"] = periodo
        
        if ruc_proveedor:
            filtro["ruc_proveedor"] = ruc_proveedor
        
        if fecha_desde or fecha_hasta:
            filtro["fecha_emision"] = {}
            if fecha_desde:
                filtro["fecha_emision"]["$gte"] = fecha_desde
            if fecha_hasta:
                filtro["fecha_emision"]["$lte"] = fecha_hasta
        
        if estado:
            filtro["estado"] = estado
        
        # Contar total
        total = await self.collection.count_documents(filtro)
        
        # Consultar con paginación
        cursor = self.collection.find(filtro).sort("fecha_emision", -1).skip(skip).limit(limit)
        documentos = await cursor.to_list(length=limit)
        
        # Convertir a modelos de respuesta
        comprobantes = []
        for doc in documentos:
            # Convertir ObjectId a string
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            
            # Convertir Decimal a float para JSON
            for campo in ["tipo_cambio", "base_imponible_gravada", "igv", "valor_adquisicion_no_gravada", 
                         "isc", "icbper", "otros_tributos", "importe_total"]:
                if campo in doc and doc[campo] is not None:
                    doc[campo] = float(doc[campo])
            
            # Convertir fechas a string
            if "fecha_registro" in doc and doc["fecha_registro"] is not None:
                doc["fecha_registro"] = doc["fecha_registro"].isoformat()
            if "fecha_actualizacion" in doc and doc["fecha_actualizacion"] is not None:
                doc["fecha_actualizacion"] = doc["fecha_actualizacion"].isoformat()
            else:
                doc["fecha_actualizacion"] = None
            
            comprobantes.append(RceComprobanteBDResponse(**doc))
        
        return comprobantes, total
    
    async def obtener_estadisticas(
        self,
        ruc: str,
        periodo: Optional[str] = None
    ) -> RceEstadisticasBD:
        """Obtener estadísticas de comprobantes guardados"""
        
        # Filtro base
        filtro = {"ruc": ruc}
        if periodo:
            filtro["periodo"] = periodo
        
        # Pipeline de agregación
        pipeline = [
            {"$match": filtro},
            {
                "$group": {
                    "_id": None,
                    "total_comprobantes": {"$sum": 1},
                    "total_importe": {"$sum": "$importe_total"},
                    "total_igv": {"$sum": "$igv"},
                    "total_base_imponible": {"$sum": "$base_imponible_gravada"},
                    "periodo_min": {"$min": "$periodo"},
                    "periodo_max": {"$max": "$periodo"}
                }
            }
        ]
        
        resultado = await self.collection.aggregate(pipeline).to_list(1)
        
        if not resultado:
            return RceEstadisticasBD(
                total_comprobantes=0,
                total_importe=0.0,
                total_igv=0.0,
                total_base_imponible=0.0,
                comprobantes_por_periodo={},
                proveedores_principales=[],
                tipos_documento={}
            )
        
        stats = resultado[0]
        
        # Estadísticas por período
        pipeline_periodo = [
            {"$match": filtro},
            {
                "$group": {
                    "_id": "$periodo",
                    "cantidad": {"$sum": 1},
                    "importe": {"$sum": "$importe_total"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        por_periodo = await self.collection.aggregate(pipeline_periodo).to_list(None)
        comprobantes_por_periodo = {
            item["_id"]: {
                "cantidad": item["cantidad"],
                "importe": float(item["importe"])
            }
            for item in por_periodo
        }
        
        # Top proveedores
        pipeline_proveedores = [
            {"$match": filtro},
            {
                "$group": {
                    "_id": {
                        "ruc": "$ruc_proveedor",
                        "razon_social": "$razon_social_proveedor"
                    },
                    "cantidad": {"$sum": 1},
                    "importe_total": {"$sum": "$importe_total"}
                }
            },
            {"$sort": {"importe_total": -1}},
            {"$limit": 10}
        ]
        
        top_proveedores = await self.collection.aggregate(pipeline_proveedores).to_list(10)
        proveedores_principales = [
            {
                "ruc": item["_id"]["ruc"],
                "razon_social": item["_id"]["razon_social"],
                "cantidad": item["cantidad"],
                "importe_total": float(item["importe_total"])
            }
            for item in top_proveedores
        ]
        
        # Tipos de documento
        pipeline_tipos = [
            {"$match": filtro},
            {
                "$group": {
                    "_id": "$tipo_documento",
                    "cantidad": {"$sum": 1}
                }
            }
        ]
        
        tipos = await self.collection.aggregate(pipeline_tipos).to_list(None)
        tipos_documento = {item["_id"]: item["cantidad"] for item in tipos}
        
        return RceEstadisticasBD(
            total_comprobantes=stats["total_comprobantes"],
            total_importe=float(stats["total_importe"]),
            total_igv=float(stats["total_igv"]),
            total_base_imponible=float(stats["total_base_imponible"]),
            periodo_inicio=stats.get("periodo_min"),
            periodo_fin=stats.get("periodo_max"),
            comprobantes_por_periodo=comprobantes_por_periodo,
            proveedores_principales=proveedores_principales,
            tipos_documento=tipos_documento
        )
    
    async def eliminar_comprobantes(
        self,
        ruc: str,
        periodo: Optional[str] = None,
        comprobante_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Eliminar comprobantes por período o IDs específicos"""
        
        if comprobante_ids:
            # Eliminar por IDs específicos
            filtro = {
                "_id": {"$in": [ObjectId(id) for id in comprobante_ids]},
                "ruc": ruc
            }
        elif periodo:
            # Eliminar por período
            filtro = {"ruc": ruc, "periodo": periodo}
        else:
            raise SireException("Debe especificar período o IDs de comprobantes")
        
        resultado = await self.collection.delete_many(filtro)
        
        return {
            "eliminados": resultado.deleted_count,
            "mensaje": f"Se eliminaron {resultado.deleted_count} comprobantes"
        }
    
    async def verificar_salud_datos(
        self,
        ruc: str,
        periodo: str
    ) -> Dict[str, Any]:
        """Verificar integridad y salud de los datos"""
        
        filtro = {"ruc": ruc, "periodo": periodo}
        
        # Verificaciones básicas
        total = await self.collection.count_documents(filtro)
        
        # Comprobantes con problemas
        sin_proveedor = await self.collection.count_documents({
            **filtro,
            "$or": [
                {"ruc_proveedor": {"$exists": False}},
                {"ruc_proveedor": ""},
                {"razon_social_proveedor": {"$exists": False}},
                {"razon_social_proveedor": ""}
            ]
        })
        
        sin_fecha = await self.collection.count_documents({
            **filtro,
            "$or": [
                {"fecha_emision": {"$exists": False}},
                {"fecha_emision": ""}
            ]
        })
        
        importe_cero = await self.collection.count_documents({
            **filtro,
            "importe_total": {"$lte": 0}
        })
        
        return {
            "total_comprobantes": total,
            "integridad": {
                "comprobantes_sin_proveedor": sin_proveedor,
                "comprobantes_sin_fecha": sin_fecha,
                "comprobantes_importe_cero": importe_cero
            },
            "salud_general": {
                "porcentaje_integridad": round((total - sin_proveedor - sin_fecha - importe_cero) / total * 100, 2) if total > 0 else 100
            }
        }
    
    async def obtener_periodos_disponibles(self, ruc: str) -> List[str]:
        """Obtener períodos únicos disponibles para un RUC"""
        
        pipeline = [
            {"$match": {"ruc": ruc}},
            {"$group": {"_id": "$periodo"}},
            {"$sort": {"_id": -1}}  # Más recientes primero
        ]
        
        resultado = await self.collection.aggregate(pipeline).to_list(length=None)
        
        return [item["_id"] for item in resultado if item["_id"]]
