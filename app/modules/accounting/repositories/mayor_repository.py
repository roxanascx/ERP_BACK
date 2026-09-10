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

Nota sobre el esquema real de datos (corregido):
Los asientos contables se guardan en la colección `asientos_contables`
(ver app/modules/accounting/libro_diario_models.py), **una línea plana por
documento** -no un array `detalles` anidado-, con estos campos:
    empresaId (str, el RUC), numeroCorrelativo, fecha, glosa,
    numeroDocumento, cuentaContable: {codigo, denominacion}, debe, haber
Este repositorio antes consultaba una colección inexistente (`libro_diario`)
con nombres de campo de un esquema que nunca se implementó así
(`codigo_cuenta_contable`, `empresa_id` como ObjectId, `detalles[]`), por lo
que cualquier consulta real habría fallado o devuelto vacío/error.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def _rango_fechas_periodo(periodo_desde: str, periodo_hasta: str) -> Dict[str, Any]:
    """
    Construir un filtro de fecha que funcione tanto si `fecha` se guardó como
    datetime como si se guardó como string "YYYY-MM-DD", a partir de un rango
    de períodos AAAAMM.
    """
    año_desde, mes_desde = int(periodo_desde[:4]), int(periodo_desde[4:6])
    año_hasta, mes_hasta = int(periodo_hasta[:4]), int(periodo_hasta[4:6])

    fecha_inicio = datetime(año_desde, mes_desde, 1)
    fecha_fin = datetime(año_hasta + 1, 1, 1) if mes_hasta == 12 else datetime(año_hasta, mes_hasta + 1, 1)

    prefijos_mes = []
    año, mes = año_desde, mes_desde
    while (año, mes) <= (año_hasta, mes_hasta):
        prefijos_mes.append(f"^{año:04d}-{mes:02d}")
        mes += 1
        if mes > 12:
            mes = 1
            año += 1

    return {
        "$or": [
            {"fecha": {"$gte": fecha_inicio, "$lt": fecha_fin}},
            {"fecha": {"$regex": "|".join(prefijos_mes)}},
            {"periodo": {"$gte": periodo_desde, "$lte": periodo_hasta}},
        ]
    }


class MayorRepository:
    """Repositorio para el Libro Mayor PLE 050200"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Inicializar repositorio del Libro Mayor

        Args:
            db: Base de datos MongoDB
        """
        self.db = db
        self.collection = db.asientos_contables
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
        Obtener movimientos contables por período, agrupados por cuenta contable

        Args:
            empresa_id: ID de la empresa (RUC)
            periodo_desde: Período inicial (AAAAMM)
            periodo_hasta: Período final (AAAAMM)
            codigo_cuenta_desde: Código de cuenta inicial
            codigo_cuenta_hasta: Código de cuenta final

        Returns:
            List[Dict]: Movimientos agrupados por cuenta contable
        """
        try:
            filtro: Dict[str, Any] = {
                "empresaId": empresa_id,
                **_rango_fechas_periodo(periodo_desde, periodo_hasta)
            }

            if codigo_cuenta_desde or codigo_cuenta_hasta:
                filtro_cuenta: Dict[str, Any] = {}
                if codigo_cuenta_desde:
                    filtro_cuenta["$gte"] = codigo_cuenta_desde
                if codigo_cuenta_hasta:
                    filtro_cuenta["$lte"] = codigo_cuenta_hasta
                filtro["cuentaContable.codigo"] = filtro_cuenta

            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": "$cuentaContable.codigo",
                        "denominacion": {"$last": "$cuentaContable.denominacion"},
                        "debe_total": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "haber_total": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}},
                        "cantidad_movimientos": {"$sum": 1},
                        "movimientos": {
                            "$push": {
                                "fecha": "$fecha",
                                "numero_asiento": "$numeroCorrelativo",
                                "documento": "$numeroDocumento",
                                "descripcion": "$glosa",
                                "debe": "$debe",
                                "haber": "$haber"
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "codigo_cuenta_contable": "$_id",
                        "denominacion_cuenta": "$denominacion",
                        "debe": "$debe_total",
                        "haber": "$haber_total",
                        "cantidad_movimientos": 1,
                        "movimientos": 1,
                        "_id": 0
                    }
                },
                {"$sort": {"codigo_cuenta_contable": 1}}
            ]

            cursor = self.collection.aggregate(pipeline)
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
        Obtener saldos iniciales de las cuentas hasta un período (no incluido)

        Args:
            empresa_id: ID de la empresa (RUC)
            periodo_hasta: Período límite, AAAAMM (no incluido)
            cuentas: Lista de códigos de cuenta

        Returns:
            List[Dict]: Saldos iniciales por cuenta
        """
        try:
            if not cuentas:
                return []

            año, mes = int(periodo_hasta[:4]), int(periodo_hasta[4:6])
            fecha_limite = datetime(año, mes, 1)

            filtro = {
                "empresaId": empresa_id,
                "cuentaContable.codigo": {"$in": cuentas},
                "$or": [
                    {"fecha": {"$lt": fecha_limite}},
                    {"fecha": {"$lt": periodo_hasta[:4] + "-" + periodo_hasta[4:6]}},
                    {"periodo": {"$lt": periodo_hasta}}
                ]
            }

            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": "$cuentaContable.codigo",
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
                            "$cond": {"if": {"$gt": ["$saldo_neto", 0]}, "then": "$saldo_neto", "else": 0}
                        },
                        "saldo_acreedor": {
                            "$cond": {"if": {"$lt": ["$saldo_neto", 0]}, "then": {"$abs": "$saldo_neto"}, "else": 0}
                        },
                        "debe_acumulado": 1,
                        "haber_acumulado": 1
                    }
                },
                {"$sort": {"codigo_cuenta_contable": 1}}
            ]

            cursor = self.collection.aggregate(pipeline)
            saldos = await cursor.to_list(length=None)

            self.logger.info(f"Saldos iniciales calculados para {len(saldos)} cuentas")

            return saldos

        except Exception as e:
            self.logger.error(f"Error obteniendo saldos iniciales: {str(e)}")
            raise

    async def obtener_plan_contable_empresa(self, empresa_id: str) -> List[Dict]:
        """
        Obtener plan contable de la empresa (colección `plan_contable`, campo
        `empresa_id` como string/RUC, igual que en accounting.plan_contable_repository)

        Args:
            empresa_id: ID de la empresa (RUC)

        Returns:
            List[Dict]: Plan contable de la empresa
        """
        try:
            cursor = self.db.plan_contable.find({"empresa_id": empresa_id}).sort("codigo", 1)
            plan_contable = await cursor.to_list(length=None)

            # Si no hay plan personalizado para la empresa, usar el plan estándar
            if not plan_contable:
                self.logger.info(f"No hay plan personalizado para empresa {empresa_id}, usando plan estándar")
                filtro_general = {
                    "$or": [
                        {"tipo_plan": "estandar"},
                        {"empresa_id": {"$exists": False}},
                        {"empresa_id": None}
                    ]
                }
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
        periodo_desde: str,
        periodo_hasta: str,
        codigo_cuenta: str
    ) -> Dict[str, Any]:
        """
        Obtener el detalle de movimientos (línea a línea) de una cuenta específica
        en un rango de períodos, incluyendo saldo acumulado por movimiento.

        Args:
            empresa_id: ID de la empresa (RUC)
            periodo_desde: Período inicial (AAAAMM)
            periodo_hasta: Período final (AAAAMM)
            codigo_cuenta: Código de la cuenta contable

        Returns:
            Dict: Resumen y detalle de movimientos de la cuenta
        """
        try:
            filtro = {
                "empresaId": empresa_id,
                "cuentaContable.codigo": codigo_cuenta,
                **_rango_fechas_periodo(periodo_desde, periodo_hasta)
            }

            cursor = self.collection.find(filtro).sort("fecha", 1)
            documentos = await cursor.to_list(length=None)

            if not documentos:
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

            total_debe = 0.0
            total_haber = 0.0
            saldo_acumulado = 0.0
            movimientos_detalle = []

            for doc in documentos:
                debe = float(doc.get("debe") or 0)
                haber = float(doc.get("haber") or 0)
                total_debe += debe
                total_haber += haber
                saldo_acumulado += debe - haber

                movimientos_detalle.append({
                    "fecha": doc.get("fecha"),
                    "numero_asiento": doc.get("numeroCorrelativo"),
                    "documento": doc.get("numeroDocumento"),
                    "descripcion": doc.get("glosa"),
                    "debe": debe,
                    "haber": haber,
                    "saldo_acumulado": saldo_acumulado
                })

            return {
                "codigo_cuenta": codigo_cuenta,
                "denominacion_cuenta": documentos[0].get("cuentaContable", {}).get("denominacion", ""),
                "total_debe": total_debe,
                "total_haber": total_haber,
                "saldo_neto": total_debe - total_haber,
                "cantidad_asientos": len(documentos),
                "primer_movimiento": documentos[0].get("fecha"),
                "ultimo_movimiento": documentos[-1].get("fecha"),
                "movimientos_detalle": movimientos_detalle
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
        Obtener cuentas que tienen saldo (acumulado hasta el período) distinto de cero

        Args:
            empresa_id: ID de la empresa (RUC)
            periodo: Período (AAAAMM)
            tipo_saldo: Tipo de saldo a filtrar

        Returns:
            List[Dict]: Cuentas con saldo
        """
        try:
            año, mes = int(periodo[:4]), int(periodo[4:6])
            fecha_limite = datetime(año + 1, 1, 1) if mes == 12 else datetime(año, mes + 1, 1)

            pipeline = [
                {
                    "$match": {
                        "empresaId": empresa_id,
                        "$or": [
                            {"fecha": {"$lt": fecha_limite}},
                            {"periodo": {"$lte": periodo}}
                        ]
                    }
                },
                {
                    "$group": {
                        "_id": "$cuentaContable.codigo",
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
                            "$cond": {"if": {"$gt": ["$saldo_neto", 0]}, "then": "$saldo_neto", "else": 0}
                        },
                        "saldo_acreedor": {
                            "$cond": {"if": {"$lt": ["$saldo_neto", 0]}, "then": {"$abs": "$saldo_neto"}, "else": 0}
                        },
                        "tiene_saldo": {"$ne": ["$saldo_neto", 0]}
                    }
                }
            ]

            if tipo_saldo == "DEUDOR":
                pipeline.append({"$match": {"saldo_deudor": {"$gt": 0}}})
            elif tipo_saldo == "ACREEDOR":
                pipeline.append({"$match": {"saldo_acreedor": {"$gt": 0}}})
            else:  # AMBOS
                pipeline.append({"$match": {"tiene_saldo": True}})

            pipeline.append({"$sort": {"codigo_cuenta": 1}})

            cursor = self.collection.aggregate(pipeline)
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
            empresa_id: ID de la empresa (RUC)
            periodo: Período a validar (AAAAMM)

        Returns:
            Dict: Resultado de la validación
        """
        try:
            filtro = {"empresaId": empresa_id, **_rango_fechas_periodo(periodo, periodo)}

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
                            "$lte": [{"$abs": {"$subtract": ["$total_debe", "$total_haber"]}}, 0.01]
                        },
                        "_id": 0
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            resultado = await cursor.to_list(length=1)

            if resultado:
                validacion = resultado[0]
                validacion["periodo"] = periodo
                return validacion

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
            empresa_id: ID de la empresa (RUC)
            periodo: Período (AAAAMM)

        Returns:
            Dict: Estadísticas del período
        """
        try:
            filtro = {"empresaId": empresa_id, **_rango_fechas_periodo(periodo, periodo)}

            pipeline = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "total_debe": {"$sum": {"$toDouble": {"$ifNull": ["$debe", 0]}}},
                        "total_haber": {"$sum": {"$toDouble": {"$ifNull": ["$haber", 0]}}},
                        "cantidad_asientos": {"$sum": 1},
                        "cuentas_unicas": {"$addToSet": "$cuentaContable.codigo"},
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

            cursor = self.collection.aggregate(pipeline)
            resultado = await cursor.to_list(length=1)

            if resultado:
                estadisticas = resultado[0]
                estadisticas["periodo"] = periodo
                return estadisticas

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
            await self.collection.create_index([
                ("empresaId", 1),
                ("cuentaContable.codigo", 1),
                ("fecha", 1)
            ])

            await self.db.plan_contable.create_index([
                ("empresa_id", 1),
                ("codigo", 1)
            ])

            self.logger.info("Índices de optimización creados exitosamente")

        except Exception as e:
            self.logger.error(f"Error creando índices: {str(e)}")
            raise
