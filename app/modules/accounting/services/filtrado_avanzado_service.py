"""
Service Avanzado de Filtrado - Libro Mayor PLE 050200
====================================================

Servicio especializado para filtrado avanzado del Libro Mayor con
múltiples criterios de búsqueda, ordenamiento y agrupación.

Funcionalidades implementadas:
- Filtros por múltiples criterios
- Búsqueda de texto avanzada
- Agrupación por diferentes campos
- Ordenamiento personalizable
- Filtros de rangos numéricos
- Filtros de fechas flexibles

Autor: Sistema ERP - FASE 3.2
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from app.config import settings
from ..schemas.schemas_mayor import LibroMayorResponse, TipoCuentaContable
from .data_adapter import DataAdapterMayor
from app.shared.exceptions import AccountingException

logger = logging.getLogger(__name__)


class TipoOrdenamiento(str, Enum):
    """Tipos de ordenamiento disponibles"""
    ASCENDENTE = "asc"
    DESCENDENTE = "desc"


class CampoOrdenamiento(str, Enum):
    """Campos disponibles para ordenamiento"""
    FECHA = "fecha"
    CODIGO_CUENTA = "codigo_cuenta"
    DESCRIPCION = "descripcion" 
    SALDO_DEUDOR = "saldo_deudor"
    SALDO_ACREEDOR = "saldo_acreedor"
    MOVIMIENTO_DEBE = "movimiento_debe"
    MOVIMIENTO_HABER = "movimiento_haber"


def _fecha_iso(valor) -> str:
    """La fecha como la guardan los asientos: texto YYYY-MM-DD."""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    return str(valor or "")[:10]


class TipoAgrupacion(str, Enum):
    """Tipos de agrupación disponibles"""
    POR_CUENTA = "cuenta"
    POR_TIPO_CUENTA = "tipo_cuenta"
    POR_NIVEL_CUENTA = "nivel_cuenta"
    POR_PERIODO = "periodo"
    POR_MES = "mes"


@dataclass
class FiltroAvanzado:
    """Filtro avanzado para consultas del Libro Mayor"""
    
    # Filtros básicos
    empresa_id: Optional[str] = None
    empresa_ruc: Optional[str] = None
    periodo_desde: Optional[str] = None
    periodo_hasta: Optional[str] = None
    
    # Filtros de cuenta contable
    codigo_cuenta: Optional[str] = None
    codigos_cuenta: Optional[List[str]] = None
    patron_codigo_cuenta: Optional[str] = None  # Regex pattern
    tipo_cuenta: Optional[TipoCuentaContable] = None
    nivel_cuenta: Optional[int] = None  # 1=Mayor, 2=Submayores, etc.
    
    # Filtros de texto
    buscar_texto: Optional[str] = None  # Búsqueda en descripción
    buscar_texto_glosa: Optional[str] = None  # Búsqueda en glosa
    
    # Filtros de rangos numéricos
    saldo_deudor_min: Optional[Decimal] = None
    saldo_deudor_max: Optional[Decimal] = None
    saldo_acreedor_min: Optional[Decimal] = None
    saldo_acreedor_max: Optional[Decimal] = None
    movimiento_debe_min: Optional[Decimal] = None
    movimiento_debe_max: Optional[Decimal] = None
    movimiento_haber_min: Optional[Decimal] = None
    movimiento_haber_max: Optional[Decimal] = None
    
    # Filtros de fechas específicas
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    incluir_saldos_cero: bool = True
    solo_con_movimientos: bool = False
    
    # Opciones de resultado
    ordenar_por: CampoOrdenamiento = CampoOrdenamiento.CODIGO_CUENTA
    tipo_orden: TipoOrdenamiento = TipoOrdenamiento.ASCENDENTE
    agrupar_por: Optional[TipoAgrupacion] = None
    limite: Optional[int] = None
    offset: Optional[int] = None
    
    # Opciones de formato
    incluir_totales: bool = True
    incluir_estadisticas: bool = False


@dataclass
class ResultadoFiltrado:
    """Resultado de filtro avanzado"""
    
    registros: List[LibroMayorResponse]
    total_registros: int
    total_paginas: Optional[int] = None
    pagina_actual: Optional[int] = None
    
    # Totales calculados
    total_saldo_deudor: Decimal = Decimal('0.00')
    total_saldo_acreedor: Decimal = Decimal('0.00')
    total_movimiento_debe: Decimal = Decimal('0.00')
    total_movimiento_haber: Decimal = Decimal('0.00')
    
    # Estadísticas opcionales
    estadisticas: Optional[Dict[str, Any]] = None
    agrupaciones: Optional[Dict[str, Any]] = None


class ServiceFiltradoAvanzadoMayor:
    """Servicio de filtrado avanzado para Libro Mayor"""
    
    def __init__(self, mongodb_client: MongoClient, db_name: Optional[str] = None):
        """Inicializar servicio"""
        self.client = mongodb_client
        self.db = self.client[db_name or settings.DATABASE_NAME]
        self.collection_asientos = self.db.asientos_contables
        self.collection_empresas = self.db.companies
        self.adapter = DataAdapterMayor()  # No requiere parámetros
        self.logger = logging.getLogger(__name__)
    
    async def aplicar_filtro_avanzado(
        self,
        filtro: FiltroAvanzado
    ) -> ResultadoFiltrado:
        """
        Aplicar filtro avanzado al Libro Mayor (ASYNC)
        
        Args:
            filtro: Configuración de filtro avanzado
            
        Returns:
            ResultadoFiltrado: Resultado filtrado con estadísticas
        """
        try:
            self.logger.info(f"Aplicando filtro avanzado - Empresa: {filtro.empresa_id}")
            
            # Construir query MongoDB
            query = self._construir_query_mongodb(filtro)
            
            # Configurar pipeline de agregación
            pipeline = self._construir_pipeline_agregacion(query, filtro)
            
            # Ejecutar consulta ASYNC
            cursor = self.collection_asientos.aggregate(pipeline)
            asientos_raw = await cursor.to_list(length=None)  # Convertir a lista de forma asíncrona
            
            # Convertir a formato Libro Mayor
            if asientos_raw:
                registros_mayor = self._convertir_asientos_a_libro_mayor(
                    asientos_raw, filtro
                )
            else:
                registros_mayor = []
            
            # Aplicar filtros post-procesamiento
            registros_filtrados = self._aplicar_filtros_post_procesamiento(
                registros_mayor, filtro
            )
            
            # Calcular totales y estadísticas
            resultado = self._calcular_resultado_final(registros_filtrados, filtro)
            
            self.logger.info(f"Filtro aplicado: {len(resultado.registros)} registros encontrados")
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtro avanzado: {str(e)}")
            raise AccountingException(f"Error en filtro avanzado: {str(e)}")
    
    def _construir_query_mongodb(self, filtro: FiltroAvanzado) -> Dict[str, Any]:
        """Construir query base de MongoDB"""
        query = {}
        
        # Filtro por empresa
        if filtro.empresa_id:
            query["empresaId"] = filtro.empresa_id
        
        # Filtros de fecha.
        #
        # Se comparan como texto ISO porque asi es como se guarda `fecha` en los
        # asientos. Pasar el `date` tal cual fallaba dos veces: Mongo no sabe
        # codificar `date` —solo `datetime`— y, aunque lo codificara, comparar un
        # objeto contra un campo de texto no habria casado nunca.
        fecha_query = {}
        if filtro.fecha_desde:
            fecha_query["$gte"] = _fecha_iso(filtro.fecha_desde)
        if filtro.fecha_hasta:
            fecha_query["$lte"] = _fecha_iso(filtro.fecha_hasta)
        if fecha_query:
            query["fecha"] = fecha_query
        
        # Filtros de código de cuenta
        if filtro.codigo_cuenta:
            query["movimientos.codigoCuentaContable"] = filtro.codigo_cuenta
        elif filtro.codigos_cuenta:
            query["movimientos.codigoCuentaContable"] = {"$in": filtro.codigos_cuenta}
        elif filtro.patron_codigo_cuenta:
            query["movimientos.codigoCuentaContable"] = {
                "$regex": filtro.patron_codigo_cuenta,
                "$options": "i"
            }
        
        # Filtros de texto
        if filtro.buscar_texto:
            query["$or"] = [
                {"movimientos.glosaDetalle": {"$regex": filtro.buscar_texto, "$options": "i"}},
                {"glosa": {"$regex": filtro.buscar_texto, "$options": "i"}}
            ]
        
        if filtro.buscar_texto_glosa:
            query["glosa"] = {"$regex": filtro.buscar_texto_glosa, "$options": "i"}
        
        return query
    
    def _construir_pipeline_agregacion(
        self, 
        query: Dict[str, Any], 
        filtro: FiltroAvanzado
    ) -> List[Dict[str, Any]]:
        """Construir pipeline de agregación MongoDB"""
        pipeline = []
        
        # Stage 1: Match inicial
        if query:
            pipeline.append({"$match": query})
        
        # Stage 2: Unwind movimientos
        pipeline.append({"$unwind": "$movimientos"})
        
        # Stage 3: Match específico en movimientos
        movimientos_match = {}
        
        if filtro.codigo_cuenta:
            movimientos_match["movimientos.codigoCuentaContable"] = filtro.codigo_cuenta
        elif filtro.codigos_cuenta:
            movimientos_match["movimientos.codigoCuentaContable"] = {"$in": filtro.codigos_cuenta}
        elif filtro.patron_codigo_cuenta:
            movimientos_match["movimientos.codigoCuentaContable"] = {
                "$regex": filtro.patron_codigo_cuenta,
                "$options": "i"
            }
        
        # Filtros por tipo de cuenta (basado en primer dígito)
        if filtro.tipo_cuenta:
            tipo_digit = self._get_tipo_cuenta_digit(filtro.tipo_cuenta)
            movimientos_match["movimientos.codigoCuentaContable"] = {
                "$regex": f"^{tipo_digit}",
                "$options": "i"
            }
        
        # Filtros por nivel de cuenta
        if filtro.nivel_cuenta:
            nivel_pattern = "^" + "[0-9]" * filtro.nivel_cuenta + "$"
            movimientos_match["movimientos.codigoCuentaContable"] = {
                "$regex": nivel_pattern
            }
        
        if movimientos_match:
            pipeline.append({"$match": movimientos_match})
        
        # Stage 4: Group por cuenta contable
        pipeline.append({
            "$group": {
                "_id": "$movimientos.codigoCuentaContable",
                "descripcion_cuenta": {"$first": "$movimientos.glosaDetalle"},
                "empresa_id": {"$first": "$empresaId"},
                "periodo_desde": {"$min": "$fecha"},
                "periodo_hasta": {"$max": "$fecha"},
                "movimiento_debe": {"$sum": "$movimientos.importeDebe"},
                "movimiento_haber": {"$sum": "$movimientos.importeHaber"},
                "cantidad_movimientos": {"$sum": 1}
            }
        })
        
        # Stage 5: Project para formato final
        pipeline.append({
            "$project": {
                "_id": 0,
                "codigo_cuenta_contable": "$_id",
                "descripcion_cuenta": 1,
                "empresa_id": 1,
                "periodo_desde": 1,
                "periodo_hasta": 1,
                "movimiento_debe": 1,
                "movimiento_haber": 1,
                "cantidad_movimientos": 1,
                "saldo_final_deudor": {
                    "$cond": {
                        "if": {"$gt": ["$movimiento_debe", "$movimiento_haber"]},
                        "then": {"$subtract": ["$movimiento_debe", "$movimiento_haber"]},
                        "else": 0
                    }
                },
                "saldo_final_acreedor": {
                    "$cond": {
                        "if": {"$gt": ["$movimiento_haber", "$movimiento_debe"]},
                        "then": {"$subtract": ["$movimiento_haber", "$movimiento_debe"]},
                        "else": 0
                    }
                }
            }
        })
        
        # Stage 6: Match post-cálculo (rangos numéricos)
        post_match = {}
        
        if filtro.movimiento_debe_min is not None:
            post_match["movimiento_debe"] = {"$gte": float(filtro.movimiento_debe_min)}
        if filtro.movimiento_debe_max is not None:
            if "movimiento_debe" not in post_match:
                post_match["movimiento_debe"] = {}
            post_match["movimiento_debe"]["$lte"] = float(filtro.movimiento_debe_max)
        
        if filtro.movimiento_haber_min is not None:
            post_match["movimiento_haber"] = {"$gte": float(filtro.movimiento_haber_min)}
        if filtro.movimiento_haber_max is not None:
            if "movimiento_haber" not in post_match:
                post_match["movimiento_haber"] = {}
            post_match["movimiento_haber"]["$lte"] = float(filtro.movimiento_haber_max)
        
        # Filtrar saldos cero si requerido
        if not filtro.incluir_saldos_cero:
            post_match["$or"] = [
                {"saldo_final_deudor": {"$gt": 0}},
                {"saldo_final_acreedor": {"$gt": 0}}
            ]
        
        # Solo con movimientos
        if filtro.solo_con_movimientos:
            post_match["$or"] = [
                {"movimiento_debe": {"$gt": 0}},
                {"movimiento_haber": {"$gt": 0}}
            ]
        
        if post_match:
            pipeline.append({"$match": post_match})
        
        # Stage 7: Sort
        sort_field = self._get_sort_field(filtro.ordenar_por)
        sort_direction = ASCENDING if filtro.tipo_orden == TipoOrdenamiento.ASCENDENTE else DESCENDING
        pipeline.append({"$sort": {sort_field: sort_direction}})
        
        # Stage 8: Skip y Limit (paginación)
        if filtro.offset:
            pipeline.append({"$skip": filtro.offset})
        if filtro.limite:
            pipeline.append({"$limit": filtro.limite})
        
        return pipeline
    
    def _convertir_asientos_a_libro_mayor(
        self, 
        asientos_raw: List[Dict], 
        filtro: FiltroAvanzado
    ) -> List[LibroMayorResponse]:
        """Convertir resultados de agregación a LibroMayorResponse"""
        registros = []
        
        for asiento in asientos_raw:
            try:
                registro = LibroMayorResponse(
                    codigo_cuenta_contable=asiento.get("codigo_cuenta_contable", ""),
                    descripcion_cuenta=asiento.get("descripcion_cuenta", "")[:200],  # Limitar longitud
                    periodo_desde=asiento.get("periodo_desde"),
                    periodo_hasta=asiento.get("periodo_hasta"),
                    saldo_deudor_inicial=Decimal('0.00'),  # Calculado posteriormente si necesario
                    saldo_acreedor_inicial=Decimal('0.00'),  # Calculado posteriormente si necesario
                    movimiento_debe=Decimal(str(asiento.get("movimiento_debe", 0))),
                    movimiento_haber=Decimal(str(asiento.get("movimiento_haber", 0))),
                    saldo_final_deudor=Decimal(str(asiento.get("saldo_final_deudor", 0))),
                    saldo_final_acreedor=Decimal(str(asiento.get("saldo_final_acreedor", 0))),
                    empresa_id=asiento.get("empresa_id", filtro.empresa_id or ""),
                    estado=EstadoCuentaMayor.ACTIVA  # Por defecto
                )
                registros.append(registro)
            except Exception as e:
                self.logger.warning(f"Error convirtiendo asiento {asiento}: {str(e)}")
                continue
        
        return registros
    
    def _aplicar_filtros_post_procesamiento(
        self, 
        registros: List[LibroMayorResponse], 
        filtro: FiltroAvanzado
    ) -> List[LibroMayorResponse]:
        """Aplicar filtros adicionales post-MongoDB"""
        registros_filtrados = registros
        
        # Filtros de rangos de saldos
        if filtro.saldo_deudor_min is not None or filtro.saldo_deudor_max is not None:
            registros_filtrados = [
                r for r in registros_filtrados 
                if self._validar_rango_decimal(
                    r.saldo_final_deudor, 
                    filtro.saldo_deudor_min, 
                    filtro.saldo_deudor_max
                )
            ]
        
        if filtro.saldo_acreedor_min is not None or filtro.saldo_acreedor_max is not None:
            registros_filtrados = [
                r for r in registros_filtrados 
                if self._validar_rango_decimal(
                    r.saldo_final_acreedor, 
                    filtro.saldo_acreedor_min, 
                    filtro.saldo_acreedor_max
                )
            ]
        
        return registros_filtrados
    
    def _calcular_resultado_final(
        self, 
        registros: List[LibroMayorResponse], 
        filtro: FiltroAvanzado
    ) -> ResultadoFiltrado:
        """Calcular resultado final con totales y estadísticas"""
        
        # Calcular totales
        total_saldo_deudor = sum(r.saldo_final_deudor for r in registros)
        total_saldo_acreedor = sum(r.saldo_final_acreedor for r in registros)
        total_movimiento_debe = sum(r.movimiento_debe for r in registros)
        total_movimiento_haber = sum(r.movimiento_haber for r in registros)
        
        # Calcular paginación
        total_registros = len(registros)
        total_paginas = None
        pagina_actual = None
        
        if filtro.limite and filtro.offset is not None:
            total_paginas = (total_registros + filtro.limite - 1) // filtro.limite
            pagina_actual = (filtro.offset // filtro.limite) + 1
        
        # Estadísticas adicionales
        estadisticas = None
        if filtro.incluir_estadisticas:
            estadisticas = self._calcular_estadisticas_avanzadas(registros)
        
        # Agrupaciones
        agrupaciones = None
        if filtro.agrupar_por:
            agrupaciones = self._calcular_agrupaciones(registros, filtro.agrupar_por)
        
        return ResultadoFiltrado(
            registros=registros,
            total_registros=total_registros,
            total_paginas=total_paginas,
            pagina_actual=pagina_actual,
            total_saldo_deudor=total_saldo_deudor,
            total_saldo_acreedor=total_saldo_acreedor,
            total_movimiento_debe=total_movimiento_debe,
            total_movimiento_haber=total_movimiento_haber,
            estadisticas=estadisticas,
            agrupaciones=agrupaciones
        )
    
    def _get_tipo_cuenta_digit(self, tipo_cuenta: TipoCuentaContable) -> str:
        """Obtener dígito correspondiente al tipo de cuenta"""
        mapping = {
            TipoCuentaContable.ACTIVO: "1",
            TipoCuentaContable.PASIVO: "2", 
            TipoCuentaContable.PATRIMONIO: "3",
            TipoCuentaContable.INGRESOS: "4",
            TipoCuentaContable.GASTOS: "5"
        }
        return mapping.get(tipo_cuenta, "0")
    
    def _get_sort_field(self, campo: CampoOrdenamiento) -> str:
        """Obtener campo MongoDB para ordenamiento"""
        mapping = {
            CampoOrdenamiento.FECHA: "periodo_desde",
            CampoOrdenamiento.CODIGO_CUENTA: "codigo_cuenta_contable",
            CampoOrdenamiento.DESCRIPCION: "descripcion_cuenta",
            CampoOrdenamiento.SALDO_DEUDOR: "saldo_final_deudor",
            CampoOrdenamiento.SALDO_ACREEDOR: "saldo_final_acreedor",
            CampoOrdenamiento.MOVIMIENTO_DEBE: "movimiento_debe",
            CampoOrdenamiento.MOVIMIENTO_HABER: "movimiento_haber"
        }
        return mapping.get(campo, "codigo_cuenta_contable")
    
    def _validar_rango_decimal(
        self, 
        valor: Decimal, 
        minimo: Optional[Decimal], 
        maximo: Optional[Decimal]
    ) -> bool:
        """Validar si un valor decimal está en el rango especificado"""
        if minimo is not None and valor < minimo:
            return False
        if maximo is not None and valor > maximo:
            return False
        return True
    
    def _calcular_estadisticas_avanzadas(
        self, 
        registros: List[LibroMayorResponse]
    ) -> Dict[str, Any]:
        """Calcular estadísticas avanzadas"""
        if not registros:
            return {}
        
        # Estadísticas básicas
        total_cuentas = len(registros)
        cuentas_con_saldo_deudor = len([r for r in registros if r.saldo_final_deudor > 0])
        cuentas_con_saldo_acreedor = len([r for r in registros if r.saldo_final_acreedor > 0])
        
        # Promedios
        promedio_debe = sum(r.movimiento_debe for r in registros) / total_cuentas
        promedio_haber = sum(r.movimiento_haber for r in registros) / total_cuentas
        
        # Cuenta con mayor movimiento
        cuenta_mayor_debe = max(registros, key=lambda r: r.movimiento_debe, default=None)
        cuenta_mayor_haber = max(registros, key=lambda r: r.movimiento_haber, default=None)
        
        return {
            "total_cuentas": total_cuentas,
            "cuentas_con_saldo_deudor": cuentas_con_saldo_deudor,
            "cuentas_con_saldo_acreedor": cuentas_con_saldo_acreedor,
            "promedio_movimiento_debe": promedio_debe,
            "promedio_movimiento_haber": promedio_haber,
            "cuenta_mayor_debe": {
                "codigo": cuenta_mayor_debe.codigo_cuenta_contable if cuenta_mayor_debe else None,
                "importe": cuenta_mayor_debe.movimiento_debe if cuenta_mayor_debe else Decimal('0.00')
            },
            "cuenta_mayor_haber": {
                "codigo": cuenta_mayor_haber.codigo_cuenta_contable if cuenta_mayor_haber else None,
                "importe": cuenta_mayor_haber.movimiento_haber if cuenta_mayor_haber else Decimal('0.00')
            }
        }
    
    def _calcular_agrupaciones(
        self, 
        registros: List[LibroMayorResponse], 
        tipo_agrupacion: TipoAgrupacion
    ) -> Dict[str, Any]:
        """Calcular agrupaciones según el tipo especificado"""
        agrupaciones = {}
        
        if tipo_agrupacion == TipoAgrupacion.POR_TIPO_CUENTA:
            agrupaciones = self._agrupar_por_tipo_cuenta(registros)
        elif tipo_agrupacion == TipoAgrupacion.POR_NIVEL_CUENTA:
            agrupaciones = self._agrupar_por_nivel_cuenta(registros)
        
        return agrupaciones
    
    def _agrupar_por_tipo_cuenta(self, registros: List[LibroMayorResponse]) -> Dict[str, Any]:
        """Agrupar registros por tipo de cuenta"""
        grupos = {}
        
        for registro in registros:
            primer_digito = registro.codigo_cuenta_contable[0] if registro.codigo_cuenta_contable else "0"
            tipo_cuenta = {
                "1": "ACTIVO",
                "2": "PASIVO",
                "3": "PATRIMONIO", 
                "4": "INGRESOS",
                "5": "GASTOS"
            }.get(primer_digito, "OTROS")
            
            if tipo_cuenta not in grupos:
                grupos[tipo_cuenta] = {
                    "cantidad": 0,
                    "total_debe": Decimal('0.00'),
                    "total_haber": Decimal('0.00'),
                    "total_saldo_deudor": Decimal('0.00'),
                    "total_saldo_acreedor": Decimal('0.00')
                }
            
            grupos[tipo_cuenta]["cantidad"] += 1
            grupos[tipo_cuenta]["total_debe"] += registro.movimiento_debe
            grupos[tipo_cuenta]["total_haber"] += registro.movimiento_haber
            grupos[tipo_cuenta]["total_saldo_deudor"] += registro.saldo_final_deudor
            grupos[tipo_cuenta]["total_saldo_acreedor"] += registro.saldo_final_acreedor
        
        return grupos
    
    def _agrupar_por_nivel_cuenta(self, registros: List[LibroMayorResponse]) -> Dict[str, Any]:
        """Agrupar registros por nivel de cuenta"""
        grupos = {}
        
        for registro in registros:
            nivel = len(registro.codigo_cuenta_contable) if registro.codigo_cuenta_contable else 0
            nivel_str = f"Nivel_{nivel}"
            
            if nivel_str not in grupos:
                grupos[nivel_str] = {
                    "cantidad": 0,
                    "total_debe": Decimal('0.00'),
                    "total_haber": Decimal('0.00')
                }
            
            grupos[nivel_str]["cantidad"] += 1
            grupos[nivel_str]["total_debe"] += registro.movimiento_debe
            grupos[nivel_str]["total_haber"] += registro.movimiento_haber
        
        return grupos


# Importar EstadoCuentaMayor si no está disponible
try:
    from ..schemas.schemas_mayor import EstadoCuentaMayor
except ImportError:
    class EstadoCuentaMayor(str, Enum):
        ACTIVA = "activa"
        INACTIVA = "inactiva"
