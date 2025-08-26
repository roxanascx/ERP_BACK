"""
Modelos y repositorio para tablas SUNAT
======================================

Modelos MongoDB para manejar las tablas de códigos SUNAT
necesarias para la generación de archivos PLE.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.modules.accounting.sunat_tables import TablasSUNAT

logger = logging.getLogger(__name__)


class TablasSUNATModel:
    """Modelo para manejar tablas SUNAT en MongoDB"""
    
    def __init__(self, db):
        self.collection = db["tablas_sunat"]
        self._create_indexes()
    
    def _create_indexes(self):
        """Crear índices para optimizar consultas"""
        # Índice único por tabla
        self.collection.create_index("tabla", unique=True)
        
        # Índice por código de tabla
        self.collection.create_index("codigo")
        
        # Índice de texto para búsquedas
        self.collection.create_index([
            ("descripcion", "text")
        ])
    
    async def inicializar_tablas(self) -> bool:
        """Inicializar todas las tablas SUNAT en la base de datos"""
        try:
            # Verificar si ya existen las tablas
            count = await self.collection.count_documents({})
            if count > 0:
                logger.info("Las tablas SUNAT ya están inicializadas")
                return True
            
            # Definir todas las tablas
            tablas_data = [
                {
                    "tabla": "tipos_documento_identidad",
                    "codigo": "2",
                    "descripcion": "Tipos de Documentos de Identidad",
                    "data": TablasSUNAT.TIPOS_DOCUMENTO_IDENTIDAD,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "codigos_libros_registros",
                    "codigo": "8", 
                    "descripcion": "Códigos de Libros y Registros",
                    "data": TablasSUNAT.CODIGOS_LIBROS_REGISTROS,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "tipos_comprobantes_pago",
                    "codigo": "10",
                    "descripcion": "Tipos de Comprobantes de Pago", 
                    "data": TablasSUNAT.TIPOS_COMPROBANTES_PAGO,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "entidades_financieras",
                    "codigo": "3",
                    "descripcion": "Entidades Financieras",
                    "data": TablasSUNAT.ENTIDADES_FINANCIERAS,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "tipos_moneda", 
                    "codigo": "4",
                    "descripcion": "Tipos de Moneda",
                    "data": TablasSUNAT.TIPOS_MONEDA,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "tipos_existencias",
                    "codigo": "5",
                    "descripcion": "Tipos de Existencias",
                    "data": TablasSUNAT.TIPOS_EXISTENCIAS,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "unidades_medida",
                    "codigo": "6",
                    "descripcion": "Códigos de Unidades de Medida",
                    "data": TablasSUNAT.UNIDADES_MEDIDA,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "tipos_intangibles",
                    "codigo": "7",
                    "descripcion": "Tipos de Intangibles",
                    "data": TablasSUNAT.TIPOS_INTANGIBLES,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                },
                {
                    "tabla": "tipos_operacion_inventario",
                    "codigo": "12",
                    "descripcion": "Tipos de Operación del Inventario",
                    "data": TablasSUNAT.TIPOS_OPERACION_INVENTARIO,
                    "activa": True,
                    "fecha_creacion": datetime.utcnow(),
                    "fecha_actualizacion": datetime.utcnow()
                }
            ]
            
            # Insertar todas las tablas
            result = await self.collection.insert_many(tablas_data)
            
            logger.info(f"✅ {len(result.inserted_ids)} tablas SUNAT inicializadas correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar tablas SUNAT: {str(e)}")
            return False
    
    async def obtener_tabla(self, nombre_tabla: str) -> Optional[Dict[str, Any]]:
        """Obtener una tabla específica por su nombre"""
        try:
            tabla = await self.collection.find_one({"tabla": nombre_tabla})
            if tabla:
                tabla["id"] = str(tabla.pop("_id"))
            return tabla
        except Exception as e:
            logger.error(f"Error al obtener tabla {nombre_tabla}: {str(e)}")
            return None
    
    async def obtener_datos_tabla(self, nombre_tabla: str) -> Optional[Dict[str, str]]:
        """Obtener solo los datos de una tabla específica"""
        try:
            tabla = await self.collection.find_one(
                {"tabla": nombre_tabla},
                {"data": 1}
            )
            return tabla.get("data") if tabla else None
        except Exception as e:
            logger.error(f"Error al obtener datos de tabla {nombre_tabla}: {str(e)}")
            return None
    
    async def listar_tablas(self) -> List[Dict[str, Any]]:
        """Listar todas las tablas disponibles"""
        try:
            tablas = []
            async for tabla in self.collection.find(
                {"activa": True},
                {"_id": 0, "data": 0}  # Excluir _id y data para listar
            ):
                tablas.append(tabla)
            return tablas
        except Exception as e:
            logger.error(f"Error al listar tablas: {str(e)}")
            return []
    
    async def buscar_codigo(self, nombre_tabla: str, codigo: str) -> Optional[str]:
        """Buscar la descripción de un código en una tabla específica"""
        try:
            tabla = await self.collection.find_one(
                {"tabla": nombre_tabla},
                {"data": 1}
            )
            
            if tabla and "data" in tabla:
                return tabla["data"].get(codigo)
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar código {codigo} en tabla {nombre_tabla}: {str(e)}")
            return None
    
    async def validar_codigo(self, nombre_tabla: str, codigo: str) -> bool:
        """Validar si un código existe en una tabla específica"""
        try:
            descripcion = await self.buscar_codigo(nombre_tabla, codigo)
            return descripcion is not None
        except Exception as e:
            logger.error(f"Error al validar código {codigo} en tabla {nombre_tabla}: {str(e)}")
            return False
    
    async def buscar_por_descripcion(self, nombre_tabla: str, descripcion_parcial: str) -> List[Dict[str, str]]:
        """Buscar códigos por descripción parcial"""
        try:
            tabla = await self.collection.find_one(
                {"tabla": nombre_tabla},
                {"data": 1}
            )
            
            if not tabla or "data" not in tabla:
                return []
            
            resultados = []
            descripcion_lower = descripcion_parcial.lower()
            
            for codigo, descripcion in tabla["data"].items():
                if descripcion_lower in descripcion.lower():
                    resultados.append({
                        "codigo": codigo,
                        "descripcion": descripcion
                    })
            
            return resultados
            
        except Exception as e:
            logger.error(f"Error en búsqueda por descripción en tabla {nombre_tabla}: {str(e)}")
            return []
    
    async def actualizar_tabla(self, nombre_tabla: str, nuevos_datos: Dict[str, str]) -> bool:
        """Actualizar los datos de una tabla"""
        try:
            result = await self.collection.update_one(
                {"tabla": nombre_tabla},
                {
                    "$set": {
                        "data": nuevos_datos,
                        "fecha_actualizacion": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Tabla {nombre_tabla} actualizada correctamente")
                return True
            else:
                logger.warning(f"No se pudo actualizar la tabla {nombre_tabla}")
                return False
                
        except Exception as e:
            logger.error(f"Error al actualizar tabla {nombre_tabla}: {str(e)}")
            return False
    
    async def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtener estadísticas de las tablas SUNAT"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_tablas": {"$sum": 1},
                        "tablas_activas": {
                            "$sum": {"$cond": ["$activa", 1, 0]}
                        }
                    }
                }
            ]
            
            result = []
            async for doc in self.collection.aggregate(pipeline):
                result.append(doc)
            
            if result:
                stats = result[0]
                
                # Obtener información adicional por tabla
                tablas_info = []
                async for tabla in self.collection.find({"activa": True}):
                    tabla_stats = {
                        "tabla": tabla["tabla"],
                        "descripcion": tabla["descripcion"],
                        "total_codigos": len(tabla.get("data", {})),
                        "fecha_actualizacion": tabla.get("fecha_actualizacion")
                    }
                    tablas_info.append(tabla_stats)
                
                return {
                    "total_tablas": stats.get("total_tablas", 0),
                    "tablas_activas": stats.get("tablas_activas", 0),
                    "tablas_detalle": tablas_info,
                    "fecha_consulta": datetime.utcnow()
                }
            
            return {
                "total_tablas": 0,
                "tablas_activas": 0,
                "tablas_detalle": [],
                "fecha_consulta": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return {
                "error": str(e),
                "fecha_consulta": datetime.utcnow()
            }


class TablasSUNATRepository:
    """Repositorio para operaciones con tablas SUNAT"""
    
    def __init__(self):
        from app.database import get_database
        self.db = get_database()
        self.model = TablasSUNATModel(self.db)
    
    async def inicializar_todas_las_tablas(self) -> bool:
        """Inicializar todas las tablas SUNAT"""
        return await self.model.inicializar_tablas()
    
    async def obtener_tipos_documento_identidad(self) -> Dict[str, str]:
        """Obtener tabla de tipos de documento de identidad"""
        datos = await self.model.obtener_datos_tabla("tipos_documento_identidad")
        return datos or TablasSUNAT.TIPOS_DOCUMENTO_IDENTIDAD
    
    async def obtener_tipos_comprobantes_pago(self) -> Dict[str, str]:
        """Obtener tabla de tipos de comprobantes de pago"""
        datos = await self.model.obtener_datos_tabla("tipos_comprobantes_pago")
        return datos or TablasSUNAT.TIPOS_COMPROBANTES_PAGO
    
    async def obtener_codigos_libros_registros(self) -> Dict[str, str]:
        """Obtener tabla de códigos de libros y registros"""
        datos = await self.model.obtener_datos_tabla("codigos_libros_registros")
        return datos or TablasSUNAT.CODIGOS_LIBROS_REGISTROS
    
    async def obtener_entidades_financieras(self) -> Dict[str, str]:
        """Obtener tabla de entidades financieras"""
        datos = await self.model.obtener_datos_tabla("entidades_financieras")
        return datos or TablasSUNAT.ENTIDADES_FINANCIERAS
    
    async def obtener_tipos_moneda(self) -> Dict[str, str]:
        """Obtener tabla de tipos de moneda"""
        datos = await self.model.obtener_datos_tabla("tipos_moneda")
        return datos or TablasSUNAT.TIPOS_MONEDA
    
    async def validar_documento_identidad(self, codigo: str) -> bool:
        """Validar código de documento de identidad"""
        return await self.model.validar_codigo("tipos_documento_identidad", codigo)
    
    async def validar_comprobante_pago(self, codigo: str) -> bool:
        """Validar código de comprobante de pago"""
        return await self.model.validar_codigo("tipos_comprobantes_pago", codigo)
    
    async def validar_codigo_libro(self, codigo: str) -> bool:
        """Validar código de libro o registro"""
        return await self.model.validar_codigo("codigos_libros_registros", codigo)
    
    async def buscar_comprobante_por_descripcion(self, descripcion: str) -> List[Dict[str, str]]:
        """Buscar comprobantes por descripción"""
        return await self.model.buscar_por_descripcion("tipos_comprobantes_pago", descripcion)
    
    async def buscar_documento_por_descripcion(self, descripcion: str) -> List[Dict[str, str]]:
        """Buscar documentos por descripción"""
        return await self.model.buscar_por_descripcion("tipos_documento_identidad", descripcion)
    
    async def obtener_descripcion_documento(self, codigo: str) -> Optional[str]:
        """Obtener descripción de un documento de identidad"""
        return await self.model.buscar_codigo("tipos_documento_identidad", codigo)
    
    async def obtener_descripcion_comprobante(self, codigo: str) -> Optional[str]:
        """Obtener descripción de un comprobante de pago"""
        return await self.model.buscar_codigo("tipos_comprobantes_pago", codigo)
    
    async def obtener_descripcion_libro(self, codigo: str) -> Optional[str]:
        """Obtener descripción de un libro o registro"""
        return await self.model.buscar_codigo("codigos_libros_registros", codigo)
    
    async def listar_todas_las_tablas(self) -> List[Dict[str, Any]]:
        """Listar todas las tablas disponibles"""
        return await self.model.listar_tablas()
    
    async def obtener_estadisticas_tablas(self) -> Dict[str, Any]:
        """Obtener estadísticas de las tablas"""
        return await self.model.obtener_estadisticas()


# Función de utilidad para inicializar las tablas al arranque
async def inicializar_tablas_sunat():
    """Función utilitaria para inicializar las tablas SUNAT al arranque del sistema"""
    try:
        repo = TablasSUNATRepository()
        success = await repo.inicializar_todas_las_tablas()
        
        if success:
            stats = await repo.obtener_estadisticas_tablas()
            logger.info(f"✅ Tablas SUNAT inicializadas: {stats.get('tablas_activas', 0)} tablas activas")
        else:
            logger.error("❌ Error al inicializar las tablas SUNAT")
            
        return success
        
    except Exception as e:
        logger.error(f"Error en inicialización de tablas SUNAT: {str(e)}")
        return False
