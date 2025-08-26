"""
Modelos MongoDB para las tablas SUNAT
====================================

Modelos y repositorio para almacenar las 12 tablas de códigos SUNAT
en MongoDB con operaciones CRUD asíncronas.

Autor: Sistema ERP
Fecha: Agosto 2025
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
import logging

from app.database import get_database
from app.modules.accounting.sunat_tables import TablasSUNAT

logger = logging.getLogger(__name__)


class TablaSUNAT(BaseModel):
    """Modelo para una tabla SUNAT en MongoDB"""
    tabla: str
    codigo_tabla: str
    descripcion: str
    codigos: Dict[str, str]
    total_codigos: int
    activa: bool = True
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    version: str = "1.0"


class TablasSUNATRepository:
    """Repositorio para manejar las tablas SUNAT en MongoDB"""
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db or get_database()
        self.collection = self.db.tablas_sunat
    
    def _obtener_descripcion_tabla(self, nombre_tabla: str) -> str:
        """Obtener descripción legible de una tabla"""
        descripciones = {
            "tipos_medio_pago": "TABLA 1: Tipos de Medio de Pago",
            "tipos_documento_identidad": "TABLA 2: Tipos de Documento de Identidad",
            "entidades_financieras": "TABLA 3: Entidades Financieras",
            "tipos_moneda": "TABLA 4: Tipos de Moneda",
            "tipos_existencia": "TABLA 5: Tipos de Existencia",
            "unidades_medida": "TABLA 6: Unidades de Medida",
            "tipos_intangible": "TABLA 7: Tipos de Intangible",
            "codigos_libros_registros": "TABLA 8: Códigos de Libros y Registros",
            "cuentas_contables": "TABLA 9: Códigos de Cuentas Contables",
            "tipos_comprobantes_pago": "TABLA 10: Tipos de Comprobantes de Pago",
            "codigos_aduana": "TABLA 11: Códigos de Aduana",
            "tipos_operacion": "TABLA 12: Tipos de Operación"
        }
        return descripciones.get(nombre_tabla, nombre_tabla.replace("_", " ").title())
    
    def _obtener_codigo_tabla(self, nombre_tabla: str) -> str:
        """Obtener el código numérico de la tabla SUNAT"""
        codigos = {
            "tipos_medio_pago": "1",
            "tipos_documento_identidad": "2",
            "entidades_financieras": "3",
            "tipos_moneda": "4",
            "tipos_existencia": "5",
            "unidades_medida": "6",
            "tipos_intangible": "7",
            "codigos_libros_registros": "8",
            "cuentas_contables": "9",
            "tipos_comprobantes_pago": "10",
            "codigos_aduana": "11",
            "tipos_operacion": "12"
        }
        return codigos.get(nombre_tabla, "0")

    async def inicializar_tablas(self) -> Dict[str, Any]:
        """Inicializar todas las 12 tablas SUNAT en la base de datos"""
        try:
            # Verificar si ya están inicializadas
            count = await self.collection.count_documents({})
            if count >= 12:
                logger.info("Las tablas SUNAT ya están inicializadas")
                return {
                    "exitoso": True,
                    "mensaje": "Las tablas SUNAT ya están inicializadas",
                    "total_tablas": count,
                    "accion": "verificacion"
                }

            # Mapeo de nombres de tabla a diccionarios de datos
            tablas_datos = {
                "tipos_medio_pago": TablasSUNAT.TIPOS_MEDIO_PAGO,
                "tipos_documento_identidad": TablasSUNAT.TIPOS_DOCUMENTO_IDENTIDAD,
                "entidades_financieras": TablasSUNAT.ENTIDADES_FINANCIERAS,
                "tipos_moneda": TablasSUNAT.TIPOS_MONEDA,
                "tipos_existencia": TablasSUNAT.TIPOS_EXISTENCIA,
                "unidades_medida": TablasSUNAT.UNIDADES_MEDIDA,
                "tipos_intangible": TablasSUNAT.TIPOS_INTANGIBLE,
                "codigos_libros_registros": TablasSUNAT.CODIGOS_LIBROS_REGISTROS,
                "cuentas_contables": TablasSUNAT.CUENTAS_CONTABLES,
                "tipos_comprobantes_pago": TablasSUNAT.TIPOS_COMPROBANTES_PAGO,
                "codigos_aduana": TablasSUNAT.CODIGOS_ADUANA,
                "tipos_operacion": TablasSUNAT.TIPOS_OPERACION
            }
            
            tablas_creadas = 0
            tablas_actualizadas = 0
            
            for nombre_tabla, datos in tablas_datos.items():
                # Verificar si la tabla ya existe
                existe = await self.collection.find_one({"tabla": nombre_tabla})
                
                documento = {
                    "tabla": nombre_tabla,
                    "codigo_tabla": self._obtener_codigo_tabla(nombre_tabla),
                    "descripcion": self._obtener_descripcion_tabla(nombre_tabla),
                    "codigos": datos,
                    "total_codigos": len(datos),
                    "activa": True,
                    "fecha_actualizacion": datetime.utcnow(),
                    "version": "1.0"
                }
                
                if existe:
                    # Actualizar datos existentes
                    await self.collection.update_one(
                        {"tabla": nombre_tabla},
                        {"$set": documento}
                    )
                    tablas_actualizadas += 1
                    logger.info(f"Tabla {nombre_tabla} actualizada con {len(datos)} códigos")
                else:
                    # Crear nueva tabla
                    documento["fecha_creacion"] = datetime.utcnow()
                    await self.collection.insert_one(documento)
                    tablas_creadas += 1
                    logger.info(f"Tabla {nombre_tabla} creada con {len(datos)} códigos")
            
            total_tablas = tablas_creadas + tablas_actualizadas
            logger.info(f"✅ {total_tablas} tablas SUNAT inicializadas correctamente")
            
            return {
                "exitoso": True,
                "mensaje": f"Tablas SUNAT inicializadas exitosamente",
                "total_tablas": total_tablas,
                "tablas_creadas": tablas_creadas,
                "tablas_actualizadas": tablas_actualizadas,
                "accion": "inicializacion"
            }
            
        except Exception as e:
            logger.error(f"Error al inicializar tablas SUNAT: {str(e)}")
            return {
                "exitoso": False,
                "mensaje": f"Error al inicializar tablas: {str(e)}",
                "total_tablas": 0,
                "accion": "error"
            }

    async def buscar_codigo(self, tabla: str, codigo: str) -> Optional[Dict[str, Any]]:
        """Buscar un código específico en una tabla"""
        try:
            documento = await self.collection.find_one({"tabla": tabla})
            
            if not documento:
                return {
                    "encontrado": False,
                    "mensaje": f"Tabla '{tabla}' no encontrada"
                }
            
            codigos = documento.get("codigos", {})
            descripcion = codigos.get(codigo)
            
            if descripcion:
                return {
                    "encontrado": True,
                    "tabla": tabla,
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "mensaje": "Código encontrado"
                }
            else:
                return {
                    "encontrado": False,
                    "tabla": tabla,
                    "codigo": codigo,
                    "mensaje": f"Código '{codigo}' no encontrado en tabla '{tabla}'"
                }
                
        except Exception as e:
            logger.error(f"Error al buscar código {codigo} en tabla {tabla}: {str(e)}")
            return {
                "encontrado": False,
                "mensaje": f"Error en búsqueda: {str(e)}"
            }

    async def validar_codigo(self, tabla: str, codigo: str) -> Dict[str, Any]:
        """Validar si un código existe en una tabla"""
        resultado = await self.buscar_codigo(tabla, codigo)
        
        return {
            "valido": resultado.get("encontrado", False),
            "tabla": tabla,
            "codigo": codigo,
            "mensaje": "Código válido" if resultado.get("encontrado") else resultado.get("mensaje", "Código inválido")
        }

    async def buscar_por_descripcion(self, tabla: str, termino: str) -> Dict[str, Any]:
        """Buscar códigos por descripción parcial"""
        try:
            documento = await self.collection.find_one({"tabla": tabla})
            
            if not documento:
                return {
                    "tabla": tabla,
                    "termino": termino,
                    "resultados": [],
                    "total_encontrados": 0,
                    "mensaje": f"Tabla '{tabla}' no encontrada"
                }
            
            codigos = documento.get("codigos", {})
            termino_lower = termino.lower()
            resultados = []
            
            for codigo, descripcion in codigos.items():
                if termino_lower in descripcion.lower():
                    resultados.append({
                        "codigo": codigo,
                        "descripcion": descripcion
                    })
            
            return {
                "tabla": tabla,
                "termino": termino,
                "resultados": resultados,
                "total_encontrados": len(resultados),
                "mensaje": f"{len(resultados)} códigos encontrados"
            }
            
        except Exception as e:
            logger.error(f"Error al buscar por descripción '{termino}' en tabla {tabla}: {str(e)}")
            return {
                "tabla": tabla,
                "termino": termino,
                "resultados": [],
                "total_encontrados": 0,
                "mensaje": f"Error en búsqueda: {str(e)}"
            }

    async def autocomplete(self, tabla: str, termino: str, limite: int = 10) -> Dict[str, Any]:
        """Autocompletado de códigos por descripción"""
        resultado = await self.buscar_por_descripcion(tabla, termino)
        
        # Limitar resultados
        resultados_limitados = resultado["resultados"][:limite]
        
        return {
            "tabla": tabla,
            "termino": termino,
            "resultados": resultados_limitados,
            "total_encontrados": resultado["total_encontrados"],
            "total_mostrados": len(resultados_limitados),
            "limite": limite,
            "mensaje": f"{len(resultados_limitados)} sugerencias"
        }

    async def listar_tabla_completa(self, tabla: str) -> Dict[str, Any]:
        """Obtener todos los códigos de una tabla"""
        try:
            documento = await self.collection.find_one({"tabla": tabla})
            
            if not documento:
                return {
                    "tabla": tabla,
                    "items": [],
                    "total": 0,
                    "mensaje": f"Tabla '{tabla}' no encontrada"
                }
            
            codigos = documento.get("codigos", {})
            items = [{"codigo": k, "descripcion": v} for k, v in codigos.items()]
            
            return {
                "tabla": tabla,
                "descripcion": documento.get("descripcion", ""),
                "items": items,
                "total": len(items),
                "activa": documento.get("activa", False),
                "fecha_actualizacion": documento.get("fecha_actualizacion"),
                "mensaje": f"Tabla completa con {len(items)} códigos"
            }
            
        except Exception as e:
            logger.error(f"Error al listar tabla completa {tabla}: {str(e)}")
            return {
                "tabla": tabla,
                "items": [],
                "total": 0,
                "mensaje": f"Error al obtener tabla: {str(e)}"
            }

    async def obtener_estadisticas(self) -> Dict[str, Any]:
        """Obtener estadísticas de todas las tablas SUNAT"""
        try:
            # Contar total de documentos
            total_tablas = await self.collection.count_documents({})
            tablas_activas = await self.collection.count_documents({"activa": True})
            
            # Obtener detalles de cada tabla
            cursor = self.collection.find({}, {
                "tabla": 1,
                "descripcion": 1,
                "total_codigos": 1,
                "activa": 1,
                "fecha_actualizacion": 1
            })
            
            tablas_detalle = []
            total_codigos = 0
            
            async for doc in cursor:
                tabla_info = {
                    "tabla": doc.get("tabla"),
                    "descripcion": doc.get("descripcion"),
                    "total_codigos": doc.get("total_codigos", 0),
                    "activa": doc.get("activa", False),
                    "fecha_actualizacion": doc.get("fecha_actualizacion")
                }
                tablas_detalle.append(tabla_info)
                total_codigos += tabla_info["total_codigos"]
            
            return {
                "total_tablas": total_tablas,
                "tablas_activas": tablas_activas,
                "total_codigos": total_codigos,
                "tablas_detalle": tablas_detalle,
                "fecha_consulta": datetime.utcnow(),
                "mensaje": f"Estadísticas de {total_tablas} tablas SUNAT"
            }
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return {
                "total_tablas": 0,
                "tablas_activas": 0,
                "total_codigos": 0,
                "tablas_detalle": [],
                "fecha_consulta": datetime.utcnow(),
                "mensaje": f"Error al obtener estadísticas: {str(e)}"
            }

    async def verificar_integridad(self) -> Dict[str, Any]:
        """Verificar la integridad de las tablas SUNAT"""
        try:
            tablas_esperadas = [
                "tipos_medio_pago", "tipos_documento_identidad", "entidades_financieras",
                "tipos_moneda", "tipos_existencia", "unidades_medida", "tipos_intangible",
                "codigos_libros_registros", "cuentas_contables", "tipos_comprobantes_pago",
                "codigos_aduana", "tipos_operacion"
            ]
            
            tablas_verificadas = []
            tablas_faltantes = []
            problemas = []
            
            for tabla_esperada in tablas_esperadas:
                documento = await self.collection.find_one({"tabla": tabla_esperada})
                
                if documento:
                    total_codigos = len(documento.get("codigos", {}))
                    tabla_info = {
                        "tabla": tabla_esperada,
                        "existe": True,
                        "total_codigos": total_codigos,
                        "activa": documento.get("activa", False)
                    }
                    
                    if total_codigos == 0:
                        problemas.append(f"Tabla {tabla_esperada} no tiene códigos")
                    
                    tablas_verificadas.append(tabla_info)
                else:
                    tablas_faltantes.append(tabla_esperada)
                    problemas.append(f"Tabla {tabla_esperada} no existe")
            
            estado_general = "OK" if len(tablas_faltantes) == 0 and len(problemas) == 0 else "CON_PROBLEMAS"
            
            return {
                "estado_general": estado_general,
                "tablas_verificadas": tablas_verificadas,
                "tablas_faltantes": tablas_faltantes,
                "problemas": problemas,
                "total_esperadas": len(tablas_esperadas),
                "total_encontradas": len(tablas_verificadas),
                "fecha_verificacion": datetime.utcnow(),
                "mensaje": f"Verificación completada: {estado_general}"
            }
            
        except Exception as e:
            logger.error(f"Error al verificar integridad: {str(e)}")
            return {
                "estado_general": "ERROR",
                "mensaje": f"Error en verificación: {str(e)}",
                "fecha_verificacion": datetime.utcnow()
            }

    async def obtener_todas_las_tablas(self) -> List[str]:
        """Obtener lista de todas las tablas disponibles"""
        try:
            cursor = self.collection.find({}, {"tabla": 1})
            tablas = []
            async for doc in cursor:
                tablas.append(doc.get("tabla"))
            return sorted(tablas)
        except Exception as e:
            logger.error(f"Error al obtener lista de tablas: {str(e)}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Verificar el estado de salud del sistema de tablas SUNAT"""
        try:
            total_tablas = await self.collection.count_documents({})
            tablas_activas = await self.collection.count_documents({"activa": True})
            
            # Verificar conectividad de la base de datos
            await self.collection.find_one()
            
            estado = "OK" if total_tablas >= 12 else "INCOMPLETO"
            
            return {
                "status": estado,
                "database_conectada": True,
                "total_tablas": total_tablas,
                "tablas_activas": tablas_activas,
                "mensaje": f"Sistema SUNAT {estado.lower()}",
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error en health check: {str(e)}")
            return {
                "status": "ERROR",
                "database_conectada": False,
                "total_tablas": 0,
                "tablas_activas": 0,
                "mensaje": f"Error: {str(e)}",
                "timestamp": datetime.utcnow()
            }
