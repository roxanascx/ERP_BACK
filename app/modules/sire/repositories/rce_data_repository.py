"""
Repository para gestión de datos RCE
Capa de acceso a datos para comprobantes de compra
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, TEXT
from bson import ObjectId

from ..models.rce_data_models import (
    RceComprobante, RceResumenPeriodo, RceEstadisticasProveedor,
    RceConfiguracionPeriodo, RceLogOperacion, RceIndexes,
    RceTipoDocumento, RceEstadoComprobante, RceMoneda
)
from ....database import get_database


class RceComprobanteRepository:
    """Repository para gestión de comprobantes RCE"""
    
    def __init__(self):
        self.db = get_database()
        self.collection: AsyncIOMotorCollection = self.db.rce_comprobantes
        self.resumenes_collection: AsyncIOMotorCollection = self.db.rce_resumenes
        self.logs_collection: AsyncIOMotorCollection = self.db.rce_logs
        self.config_collection: AsyncIOMotorCollection = self.db.rce_configuraciones
    
    async def inicializar_indices(self):
        """Crear índices necesarios para optimización"""
        try:
            # Índices para comprobantes
            for index in RceIndexes.COMPROBANTES_INDEXES:
                if isinstance(index, tuple) and len(index) == 2 and index[1] == "text":
                    # Índice de texto
                    await self.collection.create_index([(index[0], TEXT)])
                elif isinstance(index, tuple):
                    # Índice compuesto
                    index_spec = [(field, ASCENDING) for field in index]
                    await self.collection.create_index(index_spec)
                else:
                    # Índice simple
                    await self.collection.create_index(index)
            
            # Índices para resúmenes
            for index in RceIndexes.RESUMENES_INDEXES:
                if isinstance(index, tuple):
                    index_spec = [(field, ASCENDING) for field in index]
                    await self.resumenes_collection.create_index(index_spec)
                else:
                    await self.resumenes_collection.create_index(index)
            
            # Índices para logs
            for index in RceIndexes.LOGS_INDEXES:
                if isinstance(index, tuple):
                    index_spec = [(field, ASCENDING) for field in index]
                    await self.logs_collection.create_index(index_spec)
                else:
                    await self.logs_collection.create_index(index)
                    
            print("✅ Índices RCE creados correctamente")
            
        except Exception as e:
            print(f"❌ Error creando índices RCE: {e}")
    
    # ========================================
    # OPERACIONES CRUD COMPROBANTES
    # ========================================
    
    async def crear_comprobante(self, comprobante: RceComprobante) -> str:
        """Crear un nuevo comprobante"""
        # Verificar si ya existe
        existe = await self.existe_comprobante(
            comprobante.ruc_adquiriente,
            comprobante.serie,
            comprobante.numero,
            comprobante.proveedor.numero_documento
        )
        
        if existe:
            raise ValueError(f"Ya existe un comprobante {comprobante.serie}-{comprobante.numero} del proveedor {comprobante.proveedor.numero_documento}")
        
        # Asignar correlativo automático si no está definido
        if not comprobante.correlativo:
            comprobante.correlativo = await self.obtener_siguiente_correlativo(
                comprobante.ruc_adquiriente, 
                comprobante.periodo
            )
        
        # Convertir a diccionario para MongoDB
        comprobante_dict = comprobante.dict()
        comprobante_dict["fecha_registro"] = datetime.now()
        
        # Insertar en MongoDB
        result = await self.collection.insert_one(comprobante_dict)
        
        # Log de la operación
        await self.registrar_log(
            ruc=comprobante.ruc_adquiriente,
            periodo=comprobante.periodo,
            tipo_operacion="crear",
            comprobante_id=str(result.inserted_id),
            detalle_operacion=f"Creado comprobante {comprobante.serie}-{comprobante.numero}",
            datos_nuevos=comprobante_dict
        )
        
        return str(result.inserted_id)
    
    async def obtener_comprobante_por_id(self, comprobante_id: str) -> Optional[RceComprobante]:
        """Obtener comprobante por ID"""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(comprobante_id)})
            if doc:
                doc["id"] = str(doc["_id"])
                return RceComprobante(**doc)
            return None
        except Exception:
            return None
    
    async def obtener_comprobantes(
        self,
        ruc: str,
        periodo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        tipo_comprobante: Optional[RceTipoDocumento] = None,
        estado: Optional[RceEstadoComprobante] = None,
        ruc_proveedor: Optional[str] = None,
        texto_busqueda: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        ordenar_por: str = "fecha_emision",
        orden_desc: bool = True
    ) -> Tuple[List[RceComprobante], int]:
        """Obtener comprobantes con filtros y paginación"""
        
        # Construir filtros
        filtros = {"ruc_adquiriente": ruc}
        
        if periodo:
            filtros["periodo"] = periodo
        
        if fecha_inicio and fecha_fin:
            filtros["fecha_emision"] = {
                "$gte": fecha_inicio,
                "$lte": fecha_fin
            }
        elif fecha_inicio:
            filtros["fecha_emision"] = {"$gte": fecha_inicio}
        elif fecha_fin:
            filtros["fecha_emision"] = {"$lte": fecha_fin}
        
        if tipo_comprobante:
            filtros["tipo_comprobante"] = tipo_comprobante.value
        
        if estado:
            filtros["estado"] = estado.value
        
        if ruc_proveedor:
            filtros["proveedor.numero_documento"] = ruc_proveedor
        
        if texto_busqueda:
            filtros["$or"] = [
                {"proveedor.razon_social": {"$regex": texto_busqueda, "$options": "i"}},
                {"serie": {"$regex": texto_busqueda, "$options": "i"}},
                {"numero": {"$regex": texto_busqueda, "$options": "i"}},
                {"observaciones": {"$regex": texto_busqueda, "$options": "i"}}
            ]
        
        # Ordenamiento
        orden = DESCENDING if orden_desc else ASCENDING
        
        # Consulta con paginación
        cursor = self.collection.find(filtros).sort(ordenar_por, orden).skip(skip).limit(limit)
        documentos = await cursor.to_list(length=limit)
        
        # Contar total
        total = await self.collection.count_documents(filtros)
        
        # Convertir a modelos
        comprobantes = []
        for doc in documentos:
            doc["id"] = str(doc["_id"])
            comprobantes.append(RceComprobante(**doc))
        
        return comprobantes, total
    
    async def actualizar_comprobante(self, comprobante_id: str, datos_actualizacion: Dict[str, Any]) -> bool:
        """Actualizar un comprobante"""
        try:
            # Obtener datos anteriores para log
            comprobante_anterior = await self.obtener_comprobante_por_id(comprobante_id)
            
            # Actualizar fecha de modificación
            datos_actualizacion["fecha_modificacion"] = datetime.now()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(comprobante_id)},
                {"$set": datos_actualizacion}
            )
            
            if result.modified_count > 0 and comprobante_anterior:
                # Log de la operación
                await self.registrar_log(
                    ruc=comprobante_anterior.ruc_adquiriente,
                    periodo=comprobante_anterior.periodo,
                    tipo_operacion="modificar",
                    comprobante_id=comprobante_id,
                    detalle_operacion=f"Modificado comprobante {comprobante_anterior.serie}-{comprobante_anterior.numero}",
                    datos_anteriores=comprobante_anterior.dict(),
                    datos_nuevos=datos_actualizacion
                )
                return True
            
            return False
        except Exception:
            return False
    
    async def eliminar_comprobante(self, comprobante_id: str) -> bool:
        """Eliminar un comprobante (soft delete)"""
        try:
            comprobante = await self.obtener_comprobante_por_id(comprobante_id)
            if not comprobante:
                return False
            
            result = await self.collection.update_one(
                {"_id": ObjectId(comprobante_id)},
                {"$set": {
                    "estado": RceEstadoComprobante.ANULADO.value,
                    "fecha_modificacion": datetime.now()
                }}
            )
            
            if result.modified_count > 0:
                # Log de la operación
                await self.registrar_log(
                    ruc=comprobante.ruc_adquiriente,
                    periodo=comprobante.periodo,
                    tipo_operacion="eliminar",
                    comprobante_id=comprobante_id,
                    detalle_operacion=f"Eliminado comprobante {comprobante.serie}-{comprobante.numero}"
                )
                return True
            
            return False
        except Exception:
            return False
    
    # ========================================
    # OPERACIONES DE VALIDACIÓN
    # ========================================
    
    async def existe_comprobante(self, ruc: str, serie: str, numero: str, ruc_proveedor: str) -> bool:
        """Verificar si existe un comprobante"""
        count = await self.collection.count_documents({
            "ruc_adquiriente": ruc,
            "serie": serie,
            "numero": numero,
            "proveedor.numero_documento": ruc_proveedor,
            "estado": {"$ne": RceEstadoComprobante.ANULADO.value}
        })
        return count > 0
    
    async def obtener_siguiente_correlativo(self, ruc: str, periodo: str) -> int:
        """Obtener el siguiente número correlativo para el período"""
        # Buscar el correlativo más alto
        pipeline = [
            {"$match": {"ruc_adquiriente": ruc, "periodo": periodo}},
            {"$group": {"_id": None, "max_correlativo": {"$max": "$correlativo"}}}
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if result and result[0]["max_correlativo"]:
            return result[0]["max_correlativo"] + 1
        else:
            return 1
    
    # ========================================
    # OPERACIONES DE RESUMEN Y ESTADÍSTICAS
    # ========================================
    
    async def calcular_resumen_periodo(self, ruc: str, periodo: str) -> RceResumenPeriodo:
        """Calcular resumen del período"""
        pipeline = [
            {"$match": {
                "ruc_adquiriente": ruc,
                "periodo": periodo,
                "estado": {"$ne": RceEstadoComprobante.ANULADO.value}
            }},
            {"$group": {
                "_id": None,
                "total_comprobantes": {"$sum": 1},
                "total_facturas": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "01"]}, 1, 0]}
                },
                "total_boletas": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "03"]}, 1, 0]}
                },
                "total_notas_credito": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "07"]}, 1, 0]}
                },
                "total_notas_debito": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "08"]}, 1, 0]}
                },
                "total_importe_periodo": {"$sum": "$importe_total"},
                "total_igv_periodo": {"$sum": "$igv"},
                "total_base_imponible": {"$sum": "$base_imponible_gravada"},
                "total_credito_fiscal": {
                    "$sum": {"$cond": ["$sustenta_credito_fiscal", "$igv", 0]}
                },
                "fecha_primer_comprobante": {"$min": "$fecha_emision"},
                "fecha_ultimo_comprobante": {"$max": "$fecha_emision"},
                "comprobantes_registrados": {
                    "$sum": {"$cond": [{"$eq": ["$estado", "registrado"]}, 1, 0]}
                },
                "comprobantes_validados": {
                    "$sum": {"$cond": [{"$eq": ["$estado", "validado"]}, 1, 0]}
                },
                "comprobantes_observados": {
                    "$sum": {"$cond": [{"$eq": ["$estado", "observado"]}, 1, 0]}
                }
            }}
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            data = result[0]
            resumen = RceResumenPeriodo(
                ruc=ruc,
                periodo=periodo,
                total_comprobantes=data.get("total_comprobantes", 0),
                total_facturas=data.get("total_facturas", 0),
                total_boletas=data.get("total_boletas", 0),
                total_notas_credito=data.get("total_notas_credito", 0),
                total_notas_debito=data.get("total_notas_debito", 0),
                total_importe_periodo=Decimal(str(data.get("total_importe_periodo", 0))),
                total_igv_periodo=Decimal(str(data.get("total_igv_periodo", 0))),
                total_base_imponible=Decimal(str(data.get("total_base_imponible", 0))),
                total_credito_fiscal=Decimal(str(data.get("total_credito_fiscal", 0))),
                fecha_primer_comprobante=data.get("fecha_primer_comprobante"),
                fecha_ultimo_comprobante=data.get("fecha_ultimo_comprobante"),
                comprobantes_registrados=data.get("comprobantes_registrados", 0),
                comprobantes_validados=data.get("comprobantes_validados", 0),
                comprobantes_observados=data.get("comprobantes_observados", 0)
            )
        else:
            resumen = RceResumenPeriodo(ruc=ruc, periodo=periodo)
        
        # Guardar resumen calculado
        await self.guardar_resumen_periodo(resumen)
        
        return resumen
    
    async def guardar_resumen_periodo(self, resumen: RceResumenPeriodo):
        """Guardar o actualizar resumen de período"""
        await self.resumenes_collection.replace_one(
            {"ruc": resumen.ruc, "periodo": resumen.periodo},
            resumen.dict(),
            upsert=True
        )
    
    async def obtener_estadisticas_proveedores(
        self, 
        ruc: str, 
        periodo: str, 
        limit: int = 20
    ) -> List[RceEstadisticasProveedor]:
        """Obtener estadísticas por proveedor"""
        pipeline = [
            {"$match": {
                "ruc_adquiriente": ruc,
                "periodo": periodo,
                "estado": {"$ne": RceEstadoComprobante.ANULADO.value}
            }},
            {"$group": {
                "_id": "$proveedor.numero_documento",
                "razon_social": {"$first": "$proveedor.razon_social"},
                "total_comprobantes": {"$sum": 1},
                "total_importe": {"$sum": "$importe_total"},
                "facturas": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "01"]}, 1, 0]}
                },
                "boletas": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "03"]}, 1, 0]}
                },
                "notas_credito": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "07"]}, 1, 0]}
                },
                "notas_debito": {
                    "$sum": {"$cond": [{"$eq": ["$tipo_comprobante", "08"]}, 1, 0]}
                },
                "primer_comprobante": {"$min": "$fecha_emision"},
                "ultimo_comprobante": {"$max": "$fecha_emision"}
            }},
            {"$sort": {"total_importe": -1}},
            {"$limit": limit}
        ]
        
        resultados = await self.collection.aggregate(pipeline).to_list(length=limit)
        
        estadisticas = []
        for resultado in resultados:
            estadistica = RceEstadisticasProveedor(
                ruc_proveedor=resultado["_id"],
                razon_social=resultado["razon_social"],
                total_comprobantes=resultado["total_comprobantes"],
                total_importe=Decimal(str(resultado["total_importe"])),
                facturas=resultado["facturas"],
                boletas=resultado["boletas"],
                notas_credito=resultado["notas_credito"],
                notas_debito=resultado["notas_debito"],
                primer_comprobante=resultado["primer_comprobante"],
                ultimo_comprobante=resultado["ultimo_comprobante"]
            )
            estadisticas.append(estadistica)
        
        return estadisticas
    
    # ========================================
    # OPERACIONES DE CONFIGURACIÓN
    # ========================================
    
    async def obtener_configuracion_periodo(self, ruc: str, periodo: str) -> Optional[RceConfiguracionPeriodo]:
        """Obtener configuración de un período"""
        doc = await self.config_collection.find_one({"ruc": ruc, "periodo": periodo})
        if doc:
            return RceConfiguracionPeriodo(**doc)
        return None
    
    async def guardar_configuracion_periodo(self, config: RceConfiguracionPeriodo):
        """Guardar configuración de período"""
        await self.config_collection.replace_one(
            {"ruc": config.ruc, "periodo": config.periodo},
            config.dict(),
            upsert=True
        )
    
    # ========================================
    # OPERACIONES DE LOG Y AUDITORÍA
    # ========================================
    
    async def registrar_log(
        self,
        ruc: str,
        periodo: str,
        tipo_operacion: str,
        detalle_operacion: str,
        comprobante_id: Optional[str] = None,
        comprobante_serie: Optional[str] = None,
        comprobante_numero: Optional[str] = None,
        datos_anteriores: Optional[Dict[str, Any]] = None,
        datos_nuevos: Optional[Dict[str, Any]] = None,
        usuario_operacion: Optional[str] = None,
        ip_usuario: Optional[str] = None,
        exitoso: bool = True,
        mensaje_error: Optional[str] = None
    ):
        """Registrar operación en log de auditoría"""
        log = RceLogOperacion(
            ruc=ruc,
            periodo=periodo,
            tipo_operacion=tipo_operacion,
            comprobante_id=comprobante_id,
            comprobante_serie=comprobante_serie,
            comprobante_numero=comprobante_numero,
            detalle_operacion=detalle_operacion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            usuario_operacion=usuario_operacion,
            ip_usuario=ip_usuario,
            exitoso=exitoso,
            mensaje_error=mensaje_error
        )
        
        await self.logs_collection.insert_one(log.dict())
    
    async def obtener_logs(
        self, 
        ruc: str, 
        periodo: Optional[str] = None,
        tipo_operacion: Optional[str] = None,
        usuario: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RceLogOperacion], int]:
        """Obtener logs de operaciones"""
        filtros = {"ruc": ruc}
        
        if periodo:
            filtros["periodo"] = periodo
        if tipo_operacion:
            filtros["tipo_operacion"] = tipo_operacion
        if usuario:
            filtros["usuario_operacion"] = usuario
        
        cursor = self.logs_collection.find(filtros).sort("fecha_operacion", -1).skip(skip).limit(limit)
        documentos = await cursor.to_list(length=limit)
        
        total = await self.logs_collection.count_documents(filtros)
        
        logs = [RceLogOperacion(**doc) for doc in documentos]
        
        return logs, total
