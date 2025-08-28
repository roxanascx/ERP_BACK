"""
MayorRepository - Repositorio para Libro Mayor PLE 050200
=========================================================

Repositorio especializado para el acceso a datos del Libro Mayor.
Maneja consultas optimizadas a MongoDB para obtener movimientos contables,
saldos iniciales y datos del plan contable necesarios para el PLE 050200.

Funcionalidades principales:
- Consultas de movimientos por período y cuenta
- Cálculo de saldos iniciales
- Obtención del plan contable
- Agregaciones optimizadas para el Libro Mayor
- Filtros por rango de cuentas

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

logger = logging.getLogger(__name__)


class MayorRepository:
    """Repositorio para el Libro Mayor PLE 050200"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Inicializar repositorio del Libro Mayor
        
        Args:
            db: Base de datos MongoDB
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # CONSULTAS PRINCIPALES
    # ================================
    
    async def obtener_movimientos_por_periodo(
        self,
        empresa_id: str,
        periodo_desde: str,
        periodo_hasta: str,
        codigo_cuenta_desde: Optional[str] = None,
        codigo_cuenta_hasta: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtener movimientos contables por período
        
        Args:
            empresa_id: ID de la empresa
            periodo_desde: Período inicial (AAAAMM)
            periodo_hasta: Período final (AAAAMM)
            codigo_cuenta_desde: Código de cuenta inicial
            codigo_cuenta_hasta: Código de cuenta final
            
        Returns:
            List[Dict]: Lista de movimientos contables
        """
        try:
            # Construir filtro base - manejar empresa_id como string o ObjectId
            try:
                # Intentar convertir a ObjectId
                empresa_oid = ObjectId(empresa_id)
                filtro_empresa = {"empresa_id": empresa_oid}
            except:
                # Si falla, usar como string (para datos legacy)
                filtro_empresa = {"empresaId": empresa_id}
            
            # Construir filtro de período que funciona con DateTime Y strings
            from datetime import datetime
            
            año_desde = int(periodo_desde[:4])
            mes_desde = int(periodo_desde[4:6])
            año_hasta = int(periodo_hasta[:4])
            mes_hasta = int(periodo_hasta[4:6])
            
            # Crear fechas DateTime para el rango
            fecha_inicio = datetime(año_desde, mes_desde, 1)
            
            # Fecha fin: último día del mes final
            if mes_hasta == 12:
                fecha_fin = datetime(año_hasta + 1, 1, 1)
            else:
                fecha_fin = datetime(año_hasta, mes_hasta + 1, 1)
            
            # Filtro que funciona con DateTime Y strings
            filtro_fecha = {
                "$or": [
                    # Para fechas DateTime
                    {
                        "fecha": {
                            "$gte": fecha_inicio,
                            "$lt": fecha_fin
                        }
                    },
                    # Para fechas string (YYYY-MM-DD)
                    {
                        "fecha": {
                            "$regex": f"^{año_desde:04d}-{mes_desde:02d}"
                        }
                    },
                    # Para campo período directo
                    {
                        "periodo": {
                            "$gte": periodo_desde,
                            "$lte": periodo_hasta
                        }
                    }
                ]
            }
            
            filtro = {
                **filtro_empresa,
                **filtro_fecha
            }
            
            # Agregar filtros de cuenta si se especifican
            if codigo_cuenta_desde or codigo_cuenta_hasta:
                filtro_cuenta = {}
                
                if codigo_cuenta_desde:
                    filtro_cuenta["$gte"] = codigo_cuenta_desde
                
                if codigo_cuenta_hasta:
                    filtro_cuenta["$lte"] = codigo_cuenta_hasta
                
                if filtro_cuenta:
                    filtro["cuentaContable.codigo"] = filtro_cuenta
            
            # Pipeline de agregación optimizada
            # Pipeline de agregación corregido para datos reales
            pipeline = [
                {"$match": filtro},
                # Descomponer detalles para procesar cada movimiento contable
                {"$unwind": "$detalles"},
                {
                    "$group": {
                        "_id": {
                            "codigo_cuenta_contable": "$detalles.codigo_cuenta",
                            "periodo": {
                                "$concat": [
                                    {"$substr": [{"$toString": "$fecha"}, 0, 4]},  # Año
                                    {"$substr": [{"$toString": "$fecha"}, 5, 2]}   # Mes
                                ]
                            }
                        },
                        "debe_total": {"$sum": {"$toDouble": {"$ifNull": ["$detalles.debe", 0]}}},
                        "haber_total": {"$sum": {"$toDouble": {"$ifNull": ["$detalles.haber", 0]}}},
                        "cantidad_movimientos": {"$sum": 1},
                        "movimientos": {
                            "$push": {
                                "fecha": "$fecha",
                                "numero_asiento": "$numero_asiento",
                                "descripcion": "$descripcion",
                                "detalle_descripcion": "$detalles.descripcion",
                                "debe": "$detalles.debe",
                                "haber": "$detalles.haber"
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta_contable": "$_id.codigo_cuenta_contable",
                        "periodo": "$_id.periodo",
                        "debe": "$debe_total",
                        "haber": "$haber_total",
                        "cantidad_movimientos": 1,
                        "movimientos": 1,
                        "_id": 0
                    }
                },
                {"$sort": {"codigo_cuenta_contable": 1, "periodo": 1}}
            ]
            
            cursor = self.db.asientos_contables.aggregate(pipeline)
            movimientos = await cursor.to_list(length=None)
            
            self.logger.info(f"Movimientos obtenidos: {len(movimientos)} cuentas con movimientos")
            
            return movimientos
            
        except Exception as e:
            self.logger.error(f"Error obteniendo movimientos por período: {str(e)}")
            raise
    
    async def obtener_saldos_iniciales(
        self,
        empresa_id: str,
        periodo_hasta: str,
        cuentas: List[str]
    ) -> List[Dict]:
        """
        Obtener saldos iniciales de las cuentas hasta un período
        
        Args:
            empresa_id: ID de la empresa
            periodo_hasta: Período límite (no incluido)
            cuentas: Lista de códigos de cuenta
            
        Returns:
            List[Dict]: Saldos iniciales por cuenta
        """
        try:
            # Filtro para movimientos anteriores al período
            filtro = {
                "empresa_id": ObjectId(empresa_id),
                "periodo": {"$lt": periodo_hasta},
                "codigo_cuenta_contable": {"$in": cuentas}
            }
            
            # Pipeline para calcular saldos acumulados
            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": "$codigo_cuenta_contable",
                        "debe_acumulado": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "haber_acumulado": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}}
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta_contable": "$_id",
                        "saldo_neto": {"$subtract": ["$debe_acumulado", "$haber_acumulado"]},
                        "debe_acumulado": 1,
                        "haber_acumulado": 1,
                        "_id": 0
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta_contable": 1,
                        "saldo_deudor": {
                            "$cond": {
                                "if": {"$gt": ["$saldo_neto", 0]},
                                "then": "$saldo_neto",
                                "else": 0
                            }
                        },
                        "saldo_acreedor": {
                            "$cond": {
                                "if": {"$lt": ["$saldo_neto", 0]},
                                "then": {"$abs": "$saldo_neto"},
                                "else": 0
                            }
                        },
                        "debe_acumulado": 1,
                        "haber_acumulado": 1
                    }
                },
                {"$sort": {"codigo_cuenta_contable": 1}}
            ]
            
            cursor = self.db.libro_diario.aggregate(pipeline)
            saldos = await cursor.to_list(length=None)
            
            self.logger.info(f"Saldos iniciales calculados para {len(saldos)} cuentas")
            
            return saldos
            
        except Exception as e:
            self.logger.error(f"Error obteniendo saldos iniciales: {str(e)}")
            raise
    
    async def obtener_plan_contable_empresa(self, empresa_id: str) -> List[Dict]:
        """
        Obtener plan contable de la empresa
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            List[Dict]: Plan contable de la empresa
        """
        try:
            # Primero intentar buscar plan contable específico de la empresa
            try:
                empresa_oid = ObjectId(empresa_id)
                filtro_empresa = {"empresa_id": empresa_oid}
            except:
                # Si falla ObjectId, usar como string
                filtro_empresa = {"empresaId": empresa_id}
                
            cursor = self.db.plan_contable.find(filtro_empresa).sort("codigo", 1)
            plan_contable = await cursor.to_list(length=None)
            
            # Si no encuentra plan específico, usar plan contable general
            if not plan_contable:
                self.logger.info(f"No encontrado plan específico para empresa {empresa_id}, usando plan general")
                filtro_general = {"empresa_id": {"$exists": False}, "empresaId": {"$exists": False}}
                cursor = self.db.plan_contable.find(filtro_general).sort("codigo", 1)
                plan_contable = await cursor.to_list(length=None)
            
            self.logger.info(f"Plan contable obtenido: {len(plan_contable)} cuentas")
            
            return plan_contable
            
        except Exception as e:
            self.logger.error(f"Error obteniendo plan contable: {str(e)}")
            raise
    
    # ================================
    # CONSULTAS ESPECIALIZADAS
    # ================================
    
    async def obtener_resumen_movimientos_por_cuenta(
        self,
        empresa_id: str,
        periodo: str,
        codigo_cuenta: str
    ) -> Dict[str, Any]:
        """
        Obtener resumen detallado de movimientos de una cuenta específica
        
        Args:
            empresa_id: ID de la empresa
            periodo: Período (AAAAMM)
            codigo_cuenta: Código de la cuenta contable
            
        Returns:
            Dict: Resumen de movimientos de la cuenta
        """
        try:
            filtro = {
                "empresa_id": ObjectId(empresa_id),
                "periodo": periodo,
                "codigo_cuenta_contable": codigo_cuenta
            }
            
            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": "$codigo_cuenta_contable",
                        "total_debe": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "total_haber": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}},
                        "cantidad_asientos": {"$sum": 1},
                        "primer_movimiento": {"$min": "$fecha"},
                        "ultimo_movimiento": {"$max": "$fecha"},
                        "movimientos_detalle": {
                            "$push": {
                                "fecha": "$fecha",
                                "documento": "$documento",
                                "descripcion": "$descripcion",
                                "debe": "$debe",
                                "haber": "$haber",
                                "referencia": "$referencia"
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta": "$_id",
                        "total_debe": 1,
                        "total_haber": 1,
                        "saldo_neto": {"$subtract": ["$total_debe", "$total_haber"]},
                        "cantidad_asientos": 1,
                        "primer_movimiento": 1,
                        "ultimo_movimiento": 1,
                        "movimientos_detalle": 1,
                        "_id": 0
                    }
                }
            ]
            
            cursor = self.db.libro_diario.aggregate(pipeline)
            resultado = await cursor.to_list(length=1)
            
            if resultado:
                return resultado[0]
            else:
                # Retornar estructura vacía si no hay movimientos
                return {
                    "codigo_cuenta": codigo_cuenta,
                    "total_debe": 0.0,
                    "total_haber": 0.0,
                    "saldo_neto": 0.0,
                    "cantidad_asientos": 0,
                    "primer_movimiento": None,
                    "ultimo_movimiento": None,
                    "movimientos_detalle": []
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen de cuenta {codigo_cuenta}: {str(e)}")
            raise
    
    async def obtener_cuentas_con_saldo_en_periodo(
        self,
        empresa_id: str,
        periodo: str,
        tipo_saldo: str = "AMBOS"  # DEUDOR, ACREEDOR, AMBOS
    ) -> List[Dict]:
        """
        Obtener cuentas que tienen saldo en un período específico
        
        Args:
            empresa_id: ID de la empresa
            periodo: Período (AAAAMM)
            tipo_saldo: Tipo de saldo a filtrar
            
        Returns:
            List[Dict]: Cuentas con saldo
        """
        try:
            # Pipeline para obtener saldos finales
            pipeline = [
                {
                    "$match": {
                        "empresa_id": ObjectId(empresa_id),
                        "periodo": {"$lte": periodo}
                    }
                },
                {
                    "$group": {
                        "_id": "$codigo_cuenta_contable",
                        "debe_acumulado": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "haber_acumulado": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}}
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta": "$_id",
                        "saldo_neto": {"$subtract": ["$debe_acumulado", "$haber_acumulado"]},
                        "debe_acumulado": 1,
                        "haber_acumulado": 1,
                        "_id": 0
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta": 1,
                        "saldo_deudor": {
                            "$cond": {
                                "if": {"$gt": ["$saldo_neto", 0]},
                                "then": "$saldo_neto",
                                "else": 0
                            }
                        },
                        "saldo_acreedor": {
                            "$cond": {
                                "if": {"$lt": ["$saldo_neto", 0]},
                                "then": {"$abs": "$saldo_neto"},
                                "else": 0
                            }
                        },
                        "tiene_saldo": {
                            "$ne": ["$saldo_neto", 0]
                        }
                    }
                }
            ]
            
            # Agregar filtro por tipo de saldo
            if tipo_saldo == "DEUDOR":
                pipeline.append({"$match": {"saldo_deudor": {"$gt": 0}}})
            elif tipo_saldo == "ACREEDOR":
                pipeline.append({"$match": {"saldo_acreedor": {"$gt": 0}}})
            else:  # AMBOS
                pipeline.append({"$match": {"tiene_saldo": True}})
            
            pipeline.append({"$sort": {"codigo_cuenta": 1}})
            
            cursor = self.db.libro_diario.aggregate(pipeline)
            cuentas_con_saldo = await cursor.to_list(length=None)
            
            self.logger.info(f"Cuentas con saldo encontradas: {len(cuentas_con_saldo)}")
            
            return cuentas_con_saldo
            
        except Exception as e:
            self.logger.error(f"Error obteniendo cuentas con saldo: {str(e)}")
            raise
    
    # ================================
    # MÉTODOS DE VALIDACIÓN
    # ================================
    
    async def validar_partida_doble_periodo(
        self,
        empresa_id: str,
        periodo: str
    ) -> Dict[str, Any]:
        """
        Validar que se cumple el principio de partida doble en un período
        
        Args:
            empresa_id: ID de la empresa
            periodo: Período a validar (AAAAMM)
            
        Returns:
            Dict: Resultado de la validación
        """
        try:
            filtro = {
                "empresa_id": ObjectId(empresa_id),
                "periodo": periodo
            }
            
            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "total_debe": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "total_haber": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}},
                        "cantidad_asientos": {"$sum": 1}
                    }
                },
                {
                    "$project": {
                        "total_debe": 1,
                        "total_haber": 1,
                        "diferencia": {"$abs": {"$subtract": ["$total_debe", "$total_haber"]}},
                        "cantidad_asientos": 1,
                        "es_valido": {
                            "$lte": [
                                {"$abs": {"$subtract": ["$total_debe", "$total_haber"]}},
                                0.01
                            ]
                        },
                        "_id": 0
                    }
                }
            ]
            
            cursor = self.db.libro_diario.aggregate(pipeline)
            resultado = await cursor.to_list(length=1)
            
            if resultado:
                validacion = resultado[0]
                validacion["periodo"] = periodo
                return validacion
            else:
                return {
                    "periodo": periodo,
                    "total_debe": 0.0,
                    "total_haber": 0.0,
                    "diferencia": 0.0,
                    "cantidad_asientos": 0,
                    "es_valido": True
                }
                
        except Exception as e:
            self.logger.error(f"Error validando partida doble: {str(e)}")
            raise
    
    async def obtener_estadisticas_periodo(
        self,
        empresa_id: str,
        periodo: str
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas generales de un período
        
        Args:
            empresa_id: ID de la empresa
            periodo: Período (AAAAMM)
            
        Returns:
            Dict: Estadísticas del período
        """
        try:
            filtro = {
                "empresa_id": ObjectId(empresa_id),
                "periodo": periodo
            }
            
            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "total_debe": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "total_haber": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}},
                        "cantidad_asientos": {"$sum": 1},
                        "cuentas_unicas": {"$addToSet": "$codigo_cuenta_contable"},
                        "primer_asiento": {"$min": "$fecha"},
                        "ultimo_asiento": {"$max": "$fecha"}
                    }
                },
                {
                    "$project": {
                        "total_debe": 1,
                        "total_haber": 1,
                        "cantidad_asientos": 1,
                        "cantidad_cuentas": {"$size": "$cuentas_unicas"},
                        "primer_asiento": 1,
                        "ultimo_asiento": 1,
                        "diferencia": {"$abs": {"$subtract": ["$total_debe", "$total_haber"]}},
                        "_id": 0
                    }
                }
            ]
            
            cursor = self.db.libro_diario.aggregate(pipeline)
            resultado = await cursor.to_list(length=1)
            
            if resultado:
                estadisticas = resultado[0]
                estadisticas["periodo"] = periodo
                return estadisticas
            else:
                return {
                    "periodo": periodo,
                    "total_debe": 0.0,
                    "total_haber": 0.0,
                    "cantidad_asientos": 0,
                    "cantidad_cuentas": 0,
                    "primer_asiento": None,
                    "ultimo_asiento": None,
                    "diferencia": 0.0
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas del período: {str(e)}")
            raise
    
    # ================================
    # MÉTODOS DE OPTIMIZACIÓN
    # ================================
    
    async def crear_indices_optimizacion(self):
        """Crear índices para optimizar consultas del Libro Mayor"""
        try:
            # Índices para libro_diario
            await self.db.libro_diario.create_index([
                ("empresa_id", 1),
                ("periodo", 1),
                ("codigo_cuenta_contable", 1)
            ])
            
            await self.db.libro_diario.create_index([
                ("empresa_id", 1),
                ("codigo_cuenta_contable", 1),
                ("fecha", 1)
            ])
            
            # Índices para plan_contable
            await self.db.plan_contable.create_index([
                ("empresa_id", 1),
                ("codigo", 1)
            ])
            
            self.logger.info("Índices de optimización creados exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error creando índices: {str(e)}")
            raise
