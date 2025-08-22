"""
Repositorio para operaciones de comprobantes RVIE (Ventas) en base de datos
Maneja todas las operaciones CRUD y consultas especializadas
"""

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from bson import ObjectId

from ..models.rvie_comprobante_bd import (
    RvieComprobanteBD, 
    RvieComprobanteBDCreate, 
    RvieComprobanteBDResponse,
    RvieEstadisticas
)
from ....shared.exceptions import SireException


class RvieComprobanteBDRepository:
    """Repositorio para operaciones de comprobantes RVIE en BD"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection: AsyncIOMotorCollection = db.rvie_comprobantes
    
    async def inicializar_indices(self):
        """Crear índices necesarios para optimizar consultas"""
        try:
            # Índice único para evitar duplicados
            await self.collection.create_index([
                ("ruc", 1),
                ("periodo", 1),
                ("tipo_documento", 1),
                ("serie_comprobante", 1),
                ("numero_comprobante", 1)
            ], unique=True, name="idx_unique_comprobante_rvie")
            
            # Índices para consultas frecuentes
            await self.collection.create_index([("ruc", 1), ("periodo", 1)], name="idx_ruc_periodo_rvie")
            await self.collection.create_index([("cliente_ruc", 1)], name="idx_cliente_ruc")
            await self.collection.create_index([("fecha_emision", 1)], name="idx_fecha_emision_rvie")
            await self.collection.create_index([("fecha_registro", 1)], name="idx_fecha_registro_rvie")
            await self.collection.create_index([("estado", 1)], name="idx_estado_rvie")
            await self.collection.create_index([("hash_comprobante", 1)], name="idx_hash_comprobante_rvie")
            await self.collection.create_index([("tipo_documento", 1)], name="idx_tipo_documento_rvie")
            
        except Exception as e:
            raise SireException(f"Error creando índices RVIE: {str(e)}")
    
    def _generar_hash_comprobante(self, ruc: str, periodo: str, tipo_documento: str, 
                                 serie: str, numero: str) -> str:
        """Generar hash único para el comprobante"""
        datos_hash = f"{ruc}_{periodo}_{tipo_documento}_{serie}_{numero}"
        return hashlib.sha256(datos_hash.encode()).hexdigest()[:16]
    
    def _comprobante_a_dict(self, comprobante: RvieComprobanteBD) -> dict:
        """Convertir modelo a diccionario para MongoDB"""
        data = comprobante.dict(by_alias=True, exclude={"id"})
        
        # Convertir Decimal a float para MongoDB
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
                
        return data
    
    def _dict_a_comprobante(self, data: dict) -> RvieComprobanteBDResponse:
        """Convertir documento de MongoDB a modelo de respuesta"""
        if "_id" in data:
            data["id"] = str(data["_id"])
            del data["_id"]
        
        # Convertir fechas datetime a string
        if isinstance(data.get("fecha_registro"), datetime):
            data["fecha_registro"] = data["fecha_registro"].isoformat()
        if data.get("fecha_actualizacion") and isinstance(data["fecha_actualizacion"], datetime):
            data["fecha_actualizacion"] = data["fecha_actualizacion"].isoformat()
        
        # Asegurar que campos opcionales estén presentes
        if "fecha_actualizacion" not in data:
            data["fecha_actualizacion"] = None
        if "observaciones" not in data:
            data["observaciones"] = None
        if "tipo_cambio" not in data:
            data["tipo_cambio"] = None
            
        return RvieComprobanteBDResponse(**data)
    
    async def crear_comprobante(self, comprobante_data: RvieComprobanteBDCreate) -> RvieComprobanteBDResponse:
        """Crear un nuevo comprobante en la BD"""
        try:
            # Generar hash único
            hash_comprobante = self._generar_hash_comprobante(
                comprobante_data.ruc,
                comprobante_data.periodo,
                comprobante_data.tipo_documento,
                comprobante_data.serie_comprobante,
                comprobante_data.numero_comprobante
            )
            
            # Crear modelo completo
            comprobante = RvieComprobanteBD(
                **comprobante_data.dict(),
                hash_comprobante=hash_comprobante,
                fecha_registro=datetime.utcnow()
            )
            
            # Convertir a dict para MongoDB
            data = self._comprobante_a_dict(comprobante)
            
            # Insertar en BD
            resultado = await self.collection.insert_one(data)
            
            # Obtener documento insertado
            documento = await self.collection.find_one({"_id": resultado.inserted_id})
            
            return self._dict_a_comprobante(documento)
            
        except Exception as e:
            if "duplicate key" in str(e).lower():
                raise SireException(f"El comprobante ya existe: {comprobante_data.serie_comprobante}-{comprobante_data.numero_comprobante}")
            raise SireException(f"Error creando comprobante RVIE: {str(e)}")
    
    async def obtener_por_id(self, comprobante_id: str) -> Optional[RvieComprobanteBDResponse]:
        """Obtener comprobante por ID"""
        try:
            documento = await self.collection.find_one({"_id": ObjectId(comprobante_id)})
            if documento:
                return self._dict_a_comprobante(documento)
            return None
        except Exception as e:
            raise SireException(f"Error obteniendo comprobante RVIE: {str(e)}")
    
    async def consultar_comprobantes(self, ruc: str, periodo: str, skip: int = 0, 
                                   limit: int = 50, filtros: Optional[Dict] = None) -> Tuple[List[RvieComprobanteBDResponse], int]:
        """Consultar comprobantes con paginación y filtros"""
        try:
            # Construir query base
            query = {"ruc": ruc, "periodo": periodo}
            
            # Aplicar filtros adicionales
            if filtros:
                if filtros.get("tipo_documento"):
                    query["tipo_documento"] = filtros["tipo_documento"]
                if filtros.get("estado"):
                    query["estado"] = filtros["estado"]
                if filtros.get("cliente_ruc"):
                    query["cliente_ruc"] = filtros["cliente_ruc"]
                if filtros.get("fecha_desde") and filtros.get("fecha_hasta"):
                    query["fecha_emision"] = {
                        "$gte": filtros["fecha_desde"],
                        "$lte": filtros["fecha_hasta"]
                    }
                if filtros.get("monto_min") is not None:
                    query["total"] = {"$gte": float(filtros["monto_min"])}
                if filtros.get("monto_max") is not None:
                    query.setdefault("total", {})["$lte"] = float(filtros["monto_max"])
            
            # Contar total
            total = await self.collection.count_documents(query)
            
            # Obtener documentos con paginación
            cursor = self.collection.find(query).sort("fecha_emision", -1).skip(skip).limit(limit)
            documentos = await cursor.to_list(length=limit)
            
            # Convertir a modelos de respuesta
            comprobantes = [self._dict_a_comprobante(doc) for doc in documentos]
            
            return comprobantes, total
            
        except Exception as e:
            raise SireException(f"Error consultando comprobantes RVIE: {str(e)}")
    
    async def obtener_estadisticas(self, ruc: str, periodo: str) -> RvieEstadisticas:
        """Obtener estadísticas de comprobantes"""
        try:
            pipeline = [
                {"$match": {"ruc": ruc, "periodo": periodo}},
                {
                    "$group": {
                        "_id": None,
                        "total_comprobantes": {"$sum": 1},
                        "total_monto": {"$sum": "$total"},
                        "por_tipo": {
                            "$push": {
                                "tipo": "$tipo_documento",
                                "monto": "$total"
                            }
                        },
                        "por_estado": {
                            "$push": {
                                "estado": "$estado",
                                "monto": "$total"
                            }
                        }
                    }
                }
            ]
            
            resultado = await self.collection.aggregate(pipeline).to_list(length=1)
            
            if not resultado:
                return RvieEstadisticas(
                    total_comprobantes=0,
                    total_monto=0.0,
                    por_tipo={},
                    por_estado={},
                    por_mes={},
                    resumen_montos={}
                )
            
            data = resultado[0]
            
            # Procesar estadísticas por tipo
            por_tipo = {}
            for item in data.get("por_tipo", []):
                tipo = item["tipo"]
                if tipo not in por_tipo:
                    por_tipo[tipo] = {"cantidad": 0, "monto": 0.0}
                por_tipo[tipo]["cantidad"] += 1
                por_tipo[tipo]["monto"] += float(item["monto"])
            
            # Procesar estadísticas por estado
            por_estado = {}
            for item in data.get("por_estado", []):
                estado = item["estado"]
                if estado not in por_estado:
                    por_estado[estado] = 0
                por_estado[estado] += 1
            
            return RvieEstadisticas(
                total_comprobantes=data.get("total_comprobantes", 0),
                total_monto=float(data.get("total_monto", 0.0)),
                por_tipo=por_tipo,
                por_estado=por_estado,
                por_mes={},  # Se puede implementar después
                resumen_montos={
                    "base_gravada": 0.0,  # Se puede calcular después
                    "igv": 0.0,
                    "exonerado": 0.0,
                    "inafecto": 0.0
                }
            )
            
        except Exception as e:
            raise SireException(f"Error obteniendo estadísticas RVIE: {str(e)}")
    
    async def eliminar_comprobante(self, comprobante_id: str) -> bool:
        """Eliminar comprobante por ID"""
        try:
            resultado = await self.collection.delete_one({"_id": ObjectId(comprobante_id)})
            return resultado.deleted_count > 0
        except Exception as e:
            raise SireException(f"Error eliminando comprobante RVIE: {str(e)}")
    
    async def guardar_comprobantes_desde_sunat(self, ruc: str, periodo: str, 
                                             comprobantes_sunat: List[Dict]) -> Dict[str, Any]:
        """
        Guardar múltiples comprobantes desde datos de SUNAT
        🔄 ESTRATEGIA: Reemplazar datos existentes para el mismo RUC + período
        """
        try:
            # 🗑️ PASO 1: Eliminar registros existentes del mismo RUC + período
            filtro_eliminar = {"ruc": ruc, "periodo": periodo}
            resultado_eliminacion = await self.collection.delete_many(filtro_eliminar)
            registros_eliminados = resultado_eliminacion.deleted_count
            
            # 💾 PASO 2: Insertar nuevos datos de SUNAT
            guardados = 0
            errores = []
            
            for comprobante_data in comprobantes_sunat:
                try:
                    # Mapear datos de SUNAT a nuestro modelo
                    comprobante_create = self._mapear_datos_sunat(comprobante_data, ruc, periodo)
                    
                    # Crear nuevo registro (sin verificar duplicados, ya que eliminamos previos)
                    await self._insertar_comprobante_directo(comprobante_create)
                    guardados += 1
                    
                except Exception as e:
                    serie = comprobante_data.get('numSerieCDP', 'N/A')
                    numero = comprobante_data.get('numCDP', 'N/A')
                    error_msg = f"Comprobante {serie}-{numero}: {str(e)}"
                    errores.append(error_msg)
                    continue  # Continuar con el siguiente comprobante
            
            # 📊 PASO 3: Preparar resultado
            mensaje_resultado = f"Reemplazados datos de {ruc} período {periodo}: "
            mensaje_resultado += f"{registros_eliminados} previos → {guardados} nuevos"
            
            return {
                "success": True,
                "guardados": guardados,
                "reemplazados": registros_eliminados,  # Cambié "actualizados" por "reemplazados"
                "errores": errores,
                "total_procesados": len(comprobantes_sunat),
                "mensaje": mensaje_resultado
            }
            
        except Exception as e:
            raise SireException(f"Error guardando comprobantes RVIE desde SUNAT: {str(e)}")
    
    def _mapear_datos_sunat(self, data_sunat: Dict, ruc: str, periodo: str) -> RvieComprobanteBDCreate:
        """Mapear datos de SUNAT a nuestro modelo"""
        try:
            # Mapear usando los nombres correctos de los campos de SUNAT RVIE
            comprobante_create = RvieComprobanteBDCreate(
                ruc=ruc,
                periodo=periodo,
                tipo_documento=data_sunat.get("codTipoCDP", ""),
                tipo_documento_desc=data_sunat.get("desTipoCDP", ""),  
                serie_comprobante=data_sunat.get("numSerieCDP", ""),
                numero_comprobante=data_sunat.get("numCDP", ""),
                fecha_emision=data_sunat.get("fecEmisionCDP", ""),  # Correcto: fecEmisionCDP
                cliente_nombre=data_sunat.get("apeNomRznSocReceptor", ""),  # Correcto: apeNomRznSocReceptor
                cliente_tipo_documento=data_sunat.get("codTipoDocIdentidad", ""),
                cliente_numero_documento=data_sunat.get("numDocReceptor", ""),  # Correcto: numDocReceptor
                cliente_ruc=data_sunat.get("numRuc", ""),  # Usar el RUC del receptor
                moneda=data_sunat.get("codMoneda", "PEN"),
                base_gravada=Decimal(str(data_sunat.get("mtoOperGravadas", 0.0))),  # Correcto: mtoOperGravadas
                igv=Decimal(str(data_sunat.get("mtoIGV", 0.0))),
                exonerado=Decimal(str(data_sunat.get("mtoOperExoneradas", 0.0))),  # Correcto: mtoOperExoneradas
                inafecto=Decimal(str(data_sunat.get("mtoOperInafectas", 0.0))),  # Correcto: mtoOperInafectas
                total=Decimal(str(data_sunat.get("mtoTotalCP", 0.0))),
                estado=data_sunat.get("desEstadoComprobante", ""),
                tipo_operacion=data_sunat.get("indTipoOperacion", "")
            )
            
            return comprobante_create
        except Exception as e:
            raise SireException(f"Error mapeando datos de SUNAT: {str(e)}")
    
    async def _insertar_comprobante_directo(self, comprobante_create: RvieComprobanteBDCreate) -> str:
        """
        Insertar comprobante directamente sin verificar duplicados
        Se usa después de eliminar registros previos del mismo período
        """
        try:
            
            # Mapear estado de SUNAT a estado de registro interno
            estado_registro = self._mapear_estado_a_registro(comprobante_create.estado)
            
            # Crear diccionario y convertir tipos problemáticos
            nuevo_id = ObjectId()
            data = {
                "_id": nuevo_id,
                "ruc": comprobante_create.ruc,
                "periodo": comprobante_create.periodo,
                "tipo_documento": comprobante_create.tipo_documento,
                "tipo_documento_desc": comprobante_create.tipo_documento_desc,
                "serie_comprobante": comprobante_create.serie_comprobante,
                "numero_comprobante": comprobante_create.numero_comprobante,
                "fecha_emision": comprobante_create.fecha_emision,
                "cliente_nombre": comprobante_create.cliente_nombre,
                "cliente_tipo_documento": comprobante_create.cliente_tipo_documento,
                "cliente_numero_documento": comprobante_create.cliente_numero_documento,
                "cliente_ruc": comprobante_create.cliente_ruc,
                "moneda": comprobante_create.moneda,
                "tipo_cambio": float(comprobante_create.tipo_cambio) if comprobante_create.tipo_cambio else None,
                "base_gravada": float(comprobante_create.base_gravada),
                "igv": float(comprobante_create.igv),
                "exonerado": float(comprobante_create.exonerado),
                "inafecto": float(comprobante_create.inafecto),
                "total": float(comprobante_create.total),
                "estado": comprobante_create.estado,
                "tipo_operacion": comprobante_create.tipo_operacion,
                "car_sunat": comprobante_create.car_sunat,
                "ticket_sunat": comprobante_create.ticket_sunat,
                "fecha_registro": datetime.utcnow(),
                "fecha_actualizacion": None,
                "origen": "SUNAT",
                "estado_registro": estado_registro,
                "observaciones": None
            }
            
            # Insertar directamente
            resultado = await self.collection.insert_one(data)
            
            return str(resultado.inserted_id)
            
        except Exception as e:
            raise SireException(f"Error insertando comprobante RVIE: {str(e)}")

    def _mapear_estado_a_registro(self, estado_sunat: str) -> str:
        """Mapea el estado de SUNAT a nuestros estados de registro internos"""
        mapeo_estados = {
            'ACTIVO': 'GUARDADO',
            'ANULADO': 'ERROR',
            'RECHAZADO': 'ERROR',
            'ACEPTADO': 'VALIDADO',
            'PROCESADO': 'PROCESADO'
        }
        return mapeo_estados.get(estado_sunat, 'GUARDADO')
