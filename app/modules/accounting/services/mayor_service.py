"""
MayorService - Servicio de Libro Mayor PLE 050200
=================================================

Servicio especializado para la generación del Libro Mayor (PLE 050200)
según especificaciones oficiales SUNAT.

El Libro Mayor presenta los saldos iniciales, movimientos y saldos finales
de todas las cuentas contables durante un período específico.

Funcionalidades principales:
- Obtención de movimientos contables por período
- Cálculo de saldos iniciales y finales
- Agrupación por cuenta contable
- Generación de archivos PLE 050200
- Validación de partida doble
- Validación de balance de saldos

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.schemas_mayor import (
    LibroMayorResponse,
    LibroMayorRequest,
    TipoCuentaContable,
    NaturalezaCuenta,
    EstadoCuentaMayor,
    LibroMayorPLE
)
from ..ple.ple_formatter_mayor import PLEFormatterMayor, PLELineaMayor
from ..repositories.mayor_repository import MayorRepository
from .data_adapter import DataAdapterMayor
from app.shared.exceptions import AccountingException

logger = logging.getLogger(__name__)


class MayorService:
    """Servicio para el Libro Mayor PLE 050200"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Inicializar servicio del Libro Mayor
        
        Args:
            db: Base de datos MongoDB
        """
        self.db = db
        self.repository = MayorRepository(db)
        self.formatter = PLEFormatterMayor()
        self.data_adapter = DataAdapterMayor()  # Adaptador para datos reales
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # MÉTODOS PRINCIPALES DE CONSULTA
    # ================================
    
    async def obtener_libro_mayor(
        self,
        empresa_id: str,
        periodo_desde: str,
        periodo_hasta: str,
        codigo_cuenta_desde: Optional[str] = None,
        codigo_cuenta_hasta: Optional[str] = None,
        incluir_cuentas_sin_movimiento: bool = True
    ) -> List[LibroMayorResponse]:
        """
        Obtener el Libro Mayor para un período específico
        
        Args:
            empresa_id: ID de la empresa
            periodo_desde: Período inicial (AAAAMM)
            periodo_hasta: Período final (AAAAMM)
            codigo_cuenta_desde: Código de cuenta inicial (opcional)
            codigo_cuenta_hasta: Código de cuenta final (opcional)
            incluir_cuentas_sin_movimiento: Si incluir cuentas sin movimientos
            
        Returns:
            List[LibroMayorResponse]: Lista de cuentas del Libro Mayor
        """
        try:
            self.logger.info(f"Obteniendo Libro Mayor - Empresa: {empresa_id}, Período: {periodo_desde}-{periodo_hasta}")
            
            # Validar parámetros
            self._validar_parametros_periodo(periodo_desde, periodo_hasta)
            
            # Obtener plan contable de la empresa
            plan_contable = await self.repository.obtener_plan_contable_empresa(empresa_id)
            if not plan_contable:
                raise AccountingException(f"No se encontró plan contable para empresa {empresa_id}")
            
            # Obtener movimientos contables del período
            movimientos = await self.repository.obtener_movimientos_por_periodo(
                empresa_id=empresa_id,
                periodo_desde=periodo_desde,
                periodo_hasta=periodo_hasta,
                codigo_cuenta_desde=codigo_cuenta_desde,
                codigo_cuenta_hasta=codigo_cuenta_hasta
            )
            
            # Los movimientos ya vienen agrupados del pipeline de agregación
            # No necesitamos agrupar, solo procesamos directamente
            
            # Calcular saldos iniciales para cada cuenta que tiene movimientos
            codigos_cuentas = [mov.get("codigo_cuenta_contable") for mov in movimientos if mov.get("codigo_cuenta_contable")]
            saldos_iniciales = await self._calcular_saldos_iniciales(
                empresa_id=empresa_id,
                periodo_inicio=periodo_desde,
                cuentas=codigos_cuentas
            )
            
            # Generar registros del Libro Mayor
            libro_mayor = []
            
            for movimiento_agrupado in movimientos:
                codigo_cuenta = movimiento_agrupado.get("codigo_cuenta_contable")
                if not codigo_cuenta:
                    continue
                    
                # Obtener datos de la cuenta del plan contable
                cuenta_plan = next(
                    (c for c in plan_contable if c.get("codigo") == codigo_cuenta), 
                    None
                )
                
                if not cuenta_plan:
                    self.logger.warning(f"Cuenta {codigo_cuenta} no encontrada en plan contable")
                    # Crear cuenta con descripción básica
                    cuenta_plan = {
                        "codigo": codigo_cuenta,
                        "descripcion": f"Cuenta {codigo_cuenta}"
                    }
                
                # Obtener totales ya calculados del pipeline
                saldo_inicial = saldos_iniciales.get(codigo_cuenta, {})
                saldo_inicial_deudor = Decimal(str(saldo_inicial.get("saldo_deudor", 0)))
                saldo_inicial_acreedor = Decimal(str(saldo_inicial.get("saldo_acreedor", 0)))
                
                movimiento_debe = Decimal(str(movimiento_agrupado.get("debe", 0)))
                movimiento_haber = Decimal(str(movimiento_agrupado.get("haber", 0)))
                
                # Calcular saldos finales
                saldo_neto_inicial = saldo_inicial_deudor - saldo_inicial_acreedor
                saldo_neto_final = saldo_neto_inicial + movimiento_debe - movimiento_haber
                
                if saldo_neto_final >= 0:
                    saldo_final_deudor = saldo_neto_final
                    saldo_final_acreedor = Decimal('0.00')
                else:
                    saldo_final_deudor = Decimal('0.00')
                    saldo_final_acreedor = abs(saldo_neto_final)
                
                # Crear registro del Libro Mayor
                from datetime import datetime
                import uuid
                
                registro_mayor = LibroMayorResponse(
                    # Campos requeridos del schema
                    id=str(uuid.uuid4()),  # ID único
                    empresa_id=empresa_id,  # ID de empresa
                    periodo=periodo_hasta,  # Período AAAAMM
                    fecha_creacion=datetime.now().isoformat(),  # Fecha actual
                    
                    # Campos de la cuenta contable
                    codigo_cuenta_contable=codigo_cuenta,
                    descripcion_cuenta=cuenta_plan.get("descripcion", ""),
                    tipo_cuenta=self._determinar_tipo_cuenta(codigo_cuenta),
                    naturaleza_cuenta=self._determinar_naturaleza_cuenta(codigo_cuenta),
                    
                    # Saldos y movimientos calculados
                    saldo_deudor_inicial=saldo_inicial_deudor,
                    saldo_acreedor_inicial=saldo_inicial_acreedor,
                    movimiento_debe=movimiento_debe,
                    movimiento_haber=movimiento_haber,
                    saldo_final_deudor=saldo_final_deudor,
                    saldo_final_acreedor=saldo_final_acreedor,
                    
                    # Campos adicionales
                    estado_cuenta=EstadoCuentaMayor.ACTIVA,
                    nivel_cuenta=len(codigo_cuenta),
                    periodo_reporte=periodo_hasta
                )
                
                libro_mayor.append(registro_mayor)
                
                libro_mayor.append(registro_mayor)
            
            # Incluir cuentas sin movimiento si se solicita
            if incluir_cuentas_sin_movimiento:
                cuentas_sin_movimiento = await self._obtener_cuentas_sin_movimiento(
                    empresa_id=empresa_id,
                    plan_contable=plan_contable,
                    cuentas_con_movimiento=codigos_cuentas,
                    periodo_hasta=periodo_hasta,
                    codigo_cuenta_desde=codigo_cuenta_desde,
                    codigo_cuenta_hasta=codigo_cuenta_hasta
                )
                libro_mayor.extend(cuentas_sin_movimiento)
            
            # Ordenar por código de cuenta
            libro_mayor.sort(key=lambda x: x.codigo_cuenta_contable)
            
            self.logger.info(f"Libro Mayor generado: {len(libro_mayor)} cuentas")
            
            return libro_mayor
            
        except Exception as e:
            self.logger.error(f"Error obteniendo Libro Mayor: {str(e)}")
            raise AccountingException(f"Error obteniendo Libro Mayor: {str(e)}")
    
    # ================================
    # MÉTODOS DE GENERACIÓN PLE
    # ================================
    
    async def generar_archivo_ple_mayor(
        self,
        empresa_id: str,
        empresa_ruc: str,
        periodo_aaaamm: str,
        codigo_cuenta_desde: Optional[str] = None,
        codigo_cuenta_hasta: Optional[str] = None,
        correlativo: str = "001"
    ) -> Dict[str, Any]:
        """
        Generar archivo PLE 050200 del Libro Mayor
        
        Args:
            empresa_id: ID de la empresa
            empresa_ruc: RUC de la empresa
            periodo_aaaamm: Período en formato AAAAMM
            codigo_cuenta_desde: Código de cuenta inicial
            codigo_cuenta_hasta: Código de cuenta final
            correlativo: Correlativo del archivo
            
        Returns:
            Dict: Información del archivo generado
        """
        try:
            self.logger.info(f"Generando archivo PLE 050200 - Empresa: {empresa_ruc}, Período: {periodo_aaaamm}")
            
            # Obtener datos del Libro Mayor
            libro_mayor = await self.obtener_libro_mayor(
                empresa_id=empresa_id,
                periodo_desde=periodo_aaaamm,
                periodo_hasta=periodo_aaaamm,
                codigo_cuenta_desde=codigo_cuenta_desde,
                codigo_cuenta_hasta=codigo_cuenta_hasta,
                incluir_cuentas_sin_movimiento=True
            )
            
            if not libro_mayor:
                raise AccountingException(f"No se encontraron registros para el período {periodo_aaaamm}")
            
            # Formatear a líneas PLE
            lineas_ple = self.formatter.formatear_multiple_cuentas(
                cuentas=libro_mayor,
                periodo_aaaamm=periodo_aaaamm
            )
            
            # Generar contenido del archivo
            contenido_archivo = self.formatter.generar_contenido_archivo_ple(lineas_ple)
            
            # Generar nombre del archivo
            nombre_archivo = self.formatter.generar_nombre_archivo_ple(
                empresa_ruc=empresa_ruc,
                periodo_aaaamm=periodo_aaaamm,
                correlativo=correlativo
            )
            
            # Validaciones
            validacion_partida_doble = self.formatter.validar_partida_doble(libro_mayor)
            validacion_balance = self.formatter.validar_balance_saldos(libro_mayor)
            estadisticas = self.formatter.generar_estadisticas_archivo(libro_mayor, lineas_ple)
            
            # Guardar registro en base de datos
            registro_generacion = await self._guardar_registro_generacion_ple(
                empresa_id=empresa_id,
                empresa_ruc=empresa_ruc,
                periodo=periodo_aaaamm,
                nombre_archivo=nombre_archivo,
                total_registros=len(lineas_ple),
                validaciones={
                    "partida_doble": validacion_partida_doble,
                    "balance_saldos": validacion_balance
                }
            )
            
            return {
                "archivo": {
                    "nombre": nombre_archivo,
                    "contenido": contenido_archivo,
                    "tamano_bytes": len(contenido_archivo.encode('iso-8859-1')),
                    "total_lineas": len(lineas_ple)
                },
                "datos": {
                    "periodo": periodo_aaaamm,
                    "empresa_ruc": empresa_ruc,
                    "total_cuentas": len(libro_mayor),
                    "correlativo": correlativo
                },
                "validaciones": {
                    "partida_doble_valida": validacion_partida_doble[0],
                    "diferencia_partida_doble": str(validacion_partida_doble[1]),
                    "balance_saldos_correcto": validacion_balance["balance_correcto"],
                    "total_saldos_deudores": str(validacion_balance["total_saldos_deudores"]),
                    "total_saldos_acreedores": str(validacion_balance["total_saldos_acreedores"]),
                    "cuentas_con_errores": validacion_balance["cuentas_con_errores"]
                },
                "estadisticas": estadisticas,
                "registro_id": str(registro_generacion.inserted_id) if registro_generacion else None
            }
            
        except Exception as e:
            self.logger.error(f"Error generando archivo PLE: {str(e)}")
            raise AccountingException(f"Error generando archivo PLE: {str(e)}")
    
    # ================================
    # MÉTODOS PRIVADOS DE CÁLCULO
    # ================================
    
    def _agrupar_movimientos_por_cuenta(self, movimientos: List[Dict]) -> Dict[str, List[Dict]]:
        """Agrupar movimientos por código de cuenta contable"""
        cuentas_agrupadas = {}
        
        for movimiento in movimientos:
            codigo_cuenta = movimiento.get("codigo_cuenta_contable")
            if not codigo_cuenta:
                continue
                
            if codigo_cuenta not in cuentas_agrupadas:
                cuentas_agrupadas[codigo_cuenta] = []
            
            cuentas_agrupadas[codigo_cuenta].append(movimiento)
        
        return cuentas_agrupadas
    
    def _calcular_saldos_cuenta(
        self,
        movimientos_cuenta: List[Dict],
        saldo_inicial_deudor: Decimal,
        saldo_inicial_acreedor: Decimal
    ) -> Dict[str, Decimal]:
        """Calcular saldos de una cuenta específica"""
        
        # Sumar movimientos del período
        movimiento_debe = Decimal('0.00')
        movimiento_haber = Decimal('0.00')
        
        for movimiento in movimientos_cuenta:
            debe = Decimal(str(movimiento.get("debe", 0) or 0))
            haber = Decimal(str(movimiento.get("haber", 0) or 0))
            
            movimiento_debe += debe
            movimiento_haber += haber
        
        # Calcular saldos finales
        # Saldo final = Saldo inicial + Movimientos del período
        saldo_final_deudor = saldo_inicial_deudor + movimiento_debe - movimiento_haber
        saldo_final_acreedor = Decimal('0.00')
        
        # Si el saldo es negativo, se convierte en saldo acreedor
        if saldo_final_deudor < 0:
            saldo_final_acreedor = abs(saldo_final_deudor)
            saldo_final_deudor = Decimal('0.00')
        
        return {
            "saldo_deudor_inicial": saldo_inicial_deudor,
            "saldo_acreedor_inicial": saldo_inicial_acreedor,
            "movimiento_debe": movimiento_debe,
            "movimiento_haber": movimiento_haber,
            "saldo_final_deudor": saldo_final_deudor,
            "saldo_final_acreedor": saldo_final_acreedor
        }
    
    async def _calcular_saldos_iniciales(
        self,
        empresa_id: str,
        periodo_inicio: str,
        cuentas: List[str]
    ) -> Dict[str, Dict[str, Decimal]]:
        """Calcular saldos iniciales de las cuentas"""
        try:
            # Obtener movimientos anteriores al período
            saldos_iniciales = await self.repository.obtener_saldos_iniciales(
                empresa_id=empresa_id,
                periodo_hasta=periodo_inicio,
                cuentas=cuentas
            )
            
            # Formatear resultado
            resultado = {}
            for saldo in saldos_iniciales:
                codigo_cuenta = saldo.get("codigo_cuenta_contable")
                if codigo_cuenta:
                    resultado[codigo_cuenta] = {
                        "saldo_deudor": Decimal(str(saldo.get("saldo_deudor", 0) or 0)),
                        "saldo_acreedor": Decimal(str(saldo.get("saldo_acreedor", 0) or 0))
                    }
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error calculando saldos iniciales: {str(e)}")
            # Retornar saldos en cero para todas las cuentas
            return {cuenta: {"saldo_deudor": Decimal('0.00'), "saldo_acreedor": Decimal('0.00')} for cuenta in cuentas}
    
    async def _obtener_cuentas_sin_movimiento(
        self,
        empresa_id: str,
        plan_contable: List[Dict],
        cuentas_con_movimiento: List[str],
        periodo_hasta: str,
        codigo_cuenta_desde: Optional[str] = None,
        codigo_cuenta_hasta: Optional[str] = None
    ) -> List[LibroMayorResponse]:
        """Obtener cuentas del plan contable sin movimientos en el período"""
        cuentas_sin_movimiento = []
        
        for cuenta_plan in plan_contable:
            codigo_cuenta = cuenta_plan.get("codigo")
            
            # Filtrar por rango si se especifica
            if codigo_cuenta_desde and codigo_cuenta < codigo_cuenta_desde:
                continue
            if codigo_cuenta_hasta and codigo_cuenta > codigo_cuenta_hasta:
                continue
            
            # Saltar si ya tiene movimientos
            if codigo_cuenta in cuentas_con_movimiento:
                continue
            
            # Obtener saldo inicial
            saldos_iniciales = await self._calcular_saldos_iniciales(
                empresa_id=empresa_id,
                periodo_inicio=periodo_hasta,
                cuentas=[codigo_cuenta]
            )
            
            saldo_inicial = saldos_iniciales.get(codigo_cuenta, {
                "saldo_deudor": Decimal('0.00'), 
                "saldo_acreedor": Decimal('0.00')
            })
            
            # Solo incluir si tiene saldo inicial
            if saldo_inicial["saldo_deudor"] > 0 or saldo_inicial["saldo_acreedor"] > 0:
                registro_mayor = LibroMayorResponse(
                    codigo_cuenta_contable=codigo_cuenta,
                    descripcion_cuenta=cuenta_plan.get("descripcion", ""),
                    tipo_cuenta=self._determinar_tipo_cuenta(codigo_cuenta),
                    naturaleza_cuenta=self._determinar_naturaleza_cuenta(codigo_cuenta),
                    saldo_deudor_inicial=saldo_inicial["saldo_deudor"],
                    saldo_acreedor_inicial=saldo_inicial["saldo_acreedor"],
                    movimiento_debe=Decimal('0.00'),
                    movimiento_haber=Decimal('0.00'),
                    saldo_final_deudor=saldo_inicial["saldo_deudor"],
                    saldo_final_acreedor=saldo_inicial["saldo_acreedor"],
                    estado_cuenta=EstadoCuentaMayor.ACTIVA,
                    nivel_cuenta=len(codigo_cuenta),
                    periodo_reporte=periodo_hasta
                )
                
                cuentas_sin_movimiento.append(registro_mayor)
        
        return cuentas_sin_movimiento
    
    # ================================
    # MÉTODOS DE CLASIFICACIÓN
    # ================================
    
    def _determinar_tipo_cuenta(self, codigo_cuenta: str) -> TipoCuentaContable:
        """Determinar tipo de cuenta por primer dígito"""
        if not codigo_cuenta:
            return TipoCuentaContable.OTRAS
        
        primer_digito = codigo_cuenta[0]
        
        mapping = {
            '1': TipoCuentaContable.ACTIVO,
            '2': TipoCuentaContable.PASIVO,
            '3': TipoCuentaContable.PATRIMONIO,
            '4': TipoCuentaContable.INGRESOS,
            '5': TipoCuentaContable.GASTOS,
            '6': TipoCuentaContable.COSTOS,
            '7': TipoCuentaContable.CUENTAS_CONTINGENTES,
            '8': TipoCuentaContable.CUENTAS_ORDEN,
            '9': TipoCuentaContable.CUENTAS_ANALITICAS
        }
        
        return mapping.get(primer_digito, TipoCuentaContable.OTRAS)
    
    def _determinar_naturaleza_cuenta(self, codigo_cuenta: str) -> NaturalezaCuenta:
        """Determinar naturaleza de cuenta por primer dígito"""
        if not codigo_cuenta:
            return NaturalezaCuenta.DEUDORA
        
        primer_digito = codigo_cuenta[0]
        
        # Cuentas de naturaleza acreedora: 2, 3, 4 (Pasivo, Patrimonio, Ingresos)
        cuentas_acreedoras = ['2', '3', '4']
        
        if primer_digito in cuentas_acreedoras:
            return NaturalezaCuenta.ACREEDORA
        else:
            return NaturalezaCuenta.DEUDORA
    
    # ================================
    # MÉTODOS DE VALIDACIÓN
    # ================================
    
    def _validar_parametros_periodo(self, periodo_desde: str, periodo_hasta: str):
        """Validar parámetros de período"""
        import re
        
        # Validar formato AAAAMM
        patron_periodo = re.compile(r'^\d{6}$')
        
        if not patron_periodo.match(periodo_desde):
            raise AccountingException(f"Período desde debe tener formato AAAAMM: {periodo_desde}")
        
        if not patron_periodo.match(periodo_hasta):
            raise AccountingException(f"Período hasta debe tener formato AAAAMM: {periodo_hasta}")
        
        # Validar que período desde <= período hasta
        if periodo_desde > periodo_hasta:
            raise AccountingException(f"Período desde ({periodo_desde}) no puede ser mayor que período hasta ({periodo_hasta})")
    
    async def _guardar_registro_generacion_ple(
        self,
        empresa_id: str,
        empresa_ruc: str,
        periodo: str,
        nombre_archivo: str,
        total_registros: int,
        validaciones: Dict
    ) -> Any:
        """Guardar registro de generación PLE en base de datos"""
        try:
            registro = {
                "empresa_id": empresa_id,
                "empresa_ruc": empresa_ruc,
                "tipo_libro": "050200",
                "descripcion_libro": "Libro Mayor",
                "periodo": periodo,
                "nombre_archivo": nombre_archivo,
                "total_registros": total_registros,
                "validaciones": validaciones,
                "fecha_generacion": datetime.utcnow(),
                "estado": "GENERADO",
                "version": "1.0"
            }
            
            result = await self.db.ple_generaciones.insert_one(registro)
            self.logger.info(f"Registro PLE guardado: {result.inserted_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error guardando registro PLE: {str(e)}")
            return None
    
    # ================================
    # MÉTODOS DE CONSULTA ADICIONALES
    # ================================
    
    async def obtener_resumen_periodo(
        self,
        empresa_id: str,
        periodo_aaaamm: str
    ) -> Dict[str, Any]:
        """Obtener resumen del período para el Libro Mayor"""
        try:
            libro_mayor = await self.obtener_libro_mayor(
                empresa_id=empresa_id,
                periodo_desde=periodo_aaaamm,
                periodo_hasta=periodo_aaaamm
            )
            
            # Calcular totales por tipo de cuenta
            resumen_tipos = {}
            total_debe = Decimal('0.00')
            total_haber = Decimal('0.00')
            total_saldos_deudores = Decimal('0.00')
            total_saldos_acreedores = Decimal('0.00')
            
            for cuenta in libro_mayor:
                tipo_cuenta = cuenta.tipo_cuenta.value
                
                if tipo_cuenta not in resumen_tipos:
                    resumen_tipos[tipo_cuenta] = {
                        "cantidad_cuentas": 0,
                        "movimiento_debe": Decimal('0.00'),
                        "movimiento_haber": Decimal('0.00'),
                        "saldo_final": Decimal('0.00')
                    }
                
                resumen_tipos[tipo_cuenta]["cantidad_cuentas"] += 1
                resumen_tipos[tipo_cuenta]["movimiento_debe"] += cuenta.movimiento_debe or Decimal('0.00')
                resumen_tipos[tipo_cuenta]["movimiento_haber"] += cuenta.movimiento_haber or Decimal('0.00')
                resumen_tipos[tipo_cuenta]["saldo_final"] += (
                    (cuenta.saldo_final_deudor or Decimal('0.00')) - 
                    (cuenta.saldo_final_acreedor or Decimal('0.00'))
                )
                
                total_debe += cuenta.movimiento_debe or Decimal('0.00')
                total_haber += cuenta.movimiento_haber or Decimal('0.00')
                total_saldos_deudores += cuenta.saldo_final_deudor or Decimal('0.00')
                total_saldos_acreedores += cuenta.saldo_final_acreedor or Decimal('0.00')
            
            return {
                "periodo": periodo_aaaamm,
                "total_cuentas": len(libro_mayor),
                "total_movimientos_debe": total_debe,
                "total_movimientos_haber": total_haber,
                "diferencia_movimientos": abs(total_debe - total_haber),
                "total_saldos_deudores": total_saldos_deudores,
                "total_saldos_acreedores": total_saldos_acreedores,
                "diferencia_saldos": abs(total_saldos_deudores - total_saldos_acreedores),
                "balance_correcto": abs(total_debe - total_haber) <= Decimal('0.01'),
                "resumen_por_tipos": resumen_tipos
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen del período: {str(e)}")
            raise AccountingException(f"Error obteniendo resumen del período: {str(e)}")

    # ================================
    # MÉTODOS PARA DATOS REALES - FASE 2
    # ================================
    
    def obtener_asientos_contables_reales(
        self,
        empresa_id: str,
        periodo_desde: str = None,
        periodo_hasta: str = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener asientos contables reales desde MongoDB
        
        Args:
            empresa_id: ID de la empresa
            periodo_desde: Fecha desde (opcional)
            periodo_hasta: Fecha hasta (opcional)
            
        Returns:
            List[Dict]: Lista de asientos contables reales
        """
        try:
            self.logger.info(f"Obteniendo asientos contables reales - Empresa: {empresa_id}")
            
            # Construir filtro base
            filtro = {"empresaId": empresa_id}
            
            # Agregar filtros de fecha si se proporcionan
            if periodo_desde or periodo_hasta:
                filtro["fecha"] = {}
                if periodo_desde:
                    filtro["fecha"]["$gte"] = periodo_desde
                if periodo_hasta:
                    filtro["fecha"]["$lte"] = periodo_hasta
            
            # Obtener asientos de MongoDB
            cursor = self.db.asientos_contables.find(filtro).sort("fecha", 1)
            asientos = list(cursor)
            
            self.logger.info(f"Asientos obtenidos: {len(asientos)}")
            
            return asientos
            
        except Exception as e:
            self.logger.error(f"Error obteniendo asientos reales: {str(e)}")
            raise AccountingException(f"Error obteniendo asientos reales: {str(e)}")
    
    def convertir_asientos_a_libro_mayor_ple(
        self,
        empresa_id: str,
        empresa_ruc: str,
        periodo: str,
        periodo_desde: str = None,
        periodo_hasta: str = None
    ) -> List[LibroMayorPLE]:
        """
        Convertir asientos contables reales a formato PLE Libro Mayor
        
        Args:
            empresa_id: ID de la empresa
            empresa_ruc: RUC de la empresa
            periodo: Periodo en formato YYYYMM00
            periodo_desde: Fecha desde (opcional)
            periodo_hasta: Fecha hasta (opcional)
            
        Returns:
            List[LibroMayorPLE]: Asientos convertidos a formato PLE
        """
        try:
            self.logger.info(f"Convirtiendo asientos a PLE Mayor - Empresa: {empresa_id}, Período: {periodo}")
            
            # Obtener asientos contables reales
            asientos = self.obtener_asientos_contables_reales(
                empresa_id=empresa_id,
                periodo_desde=periodo_desde,
                periodo_hasta=periodo_hasta
            )
            
            if not asientos:
                self.logger.warning(f"No se encontraron asientos para empresa {empresa_id}")
                return []
            
            # Convertir usando el adaptador
            libros_mayor_ple = self.data_adapter.convertir_lista_asientos(
                asientos=asientos,
                empresa_ruc=empresa_ruc,
                periodo=periodo
            )
            
            self.logger.info(f"Conversión completada: {len(libros_mayor_ple)} registros PLE generados")
            
            return libros_mayor_ple
            
        except Exception as e:
            self.logger.error(f"Error convirtiendo asientos a PLE: {str(e)}")
            raise AccountingException(f"Error convirtiendo asientos a PLE: {str(e)}")
    
    def generar_archivo_ple_mayor_con_datos_reales(
        self,
        empresa_id: str,
        empresa_ruc: str,
        periodo_aaaamm: str,
        periodo_desde: str = None,
        periodo_hasta: str = None,
        correlativo: str = "001"
    ) -> Dict[str, Any]:
        """
        Generar archivo PLE Libro Mayor usando datos reales de asientos contables
        
        Args:
            empresa_id: ID de la empresa
            empresa_ruc: RUC de la empresa  
            periodo_aaaamm: Período en formato AAAAMM
            periodo_desde: Fecha desde (opcional)
            periodo_hasta: Fecha hasta (opcional)
            correlativo: Número correlativo del archivo
            
        Returns:
            Dict con información del archivo generado
        """
        try:
            self.logger.info(f"Generando PLE Mayor con datos reales - Empresa: {empresa_id}")
            
            # Formatear período para PLE (AAAAMM00)
            periodo_ple = f"{periodo_aaaamm}00"
            
            # Convertir asientos a formato PLE
            libros_mayor_ple = self.convertir_asientos_a_libro_mayor_ple(
                empresa_id=empresa_id,
                empresa_ruc=empresa_ruc,
                periodo=periodo_ple,
                periodo_desde=periodo_desde,
                periodo_hasta=periodo_hasta
            )
            
            if not libros_mayor_ple:
                return {
                    "archivo_generado": False,
                    "mensaje": "No hay datos para generar el archivo PLE",
                    "total_registros": 0,
                    "nombre_archivo": "",
                    "contenido_archivo": ""
                }
            
            # Convertir a formato PLELineaMayor para el formatter
            lineas_ple = []
            for libro_ple in libros_mayor_ple:
                linea = PLELineaMayor(
                    campo_01_periodo=libro_ple.periodo,
                    campo_02_codigo_cuenta=libro_ple.codigo_cuenta_contable,
                    campo_03_descripcion_cuenta=libro_ple.glosa_descripcion[:100],  # Limitar longitud
                    campo_04_saldo_deudor_inicial="0.00",  # Calculado posteriormente
                    campo_05_saldo_acreedor_inicial="0.00",  # Calculado posteriormente
                    campo_06_movimiento_debe=str(libro_ple.movimiento_debe),
                    campo_07_movimiento_haber=str(libro_ple.movimiento_haber),
                    campo_08_saldo_final_deudor=str(libro_ple.saldo_deudor),
                    campo_09_saldo_final_acreedor=str(libro_ple.saldo_acreedor)
                )
                lineas_ple.append(linea)
            
            # Generar archivo usando el formatter
            contenido_archivo = self.formatter.generar_contenido_archivo_ple(lineas_ple)
            
            # Generar nombre de archivo usando el formatter
            nombre_archivo = self.formatter.generar_nombre_archivo_ple(
                empresa_ruc=empresa_ruc,
                periodo_aaaamm=periodo_aaaamm,
                correlativo=correlativo
            )
            
            # Validar archivo generado
            validacion = self.formatter.validar_archivo(contenido_archivo)
            
            resultado = {
                "archivo_generado": True,
                "nombre_archivo": nombre_archivo,
                "total_registros": len(libros_mayor_ple),
                "contenido_archivo": contenido_archivo,
                "validacion": validacion,
                "periodo": periodo_ple,
                "empresa_ruc": empresa_ruc,
                "resumen": {
                    "total_debe": sum(libro.movimiento_debe for libro in libros_mayor_ple),
                    "total_haber": sum(libro.movimiento_haber for libro in libros_mayor_ple),
                    "total_saldo_deudor": sum(libro.saldo_deudor for libro in libros_mayor_ple),
                    "total_saldo_acreedor": sum(libro.saldo_acreedor for libro in libros_mayor_ple),
                    "cuentas_unicas": len(set(libro.codigo_cuenta_contable for libro in libros_mayor_ple))
                }
            }
            
            self.logger.info(f"Archivo PLE Mayor generado exitosamente: {nombre_archivo}")
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error generando archivo PLE Mayor con datos reales: {str(e)}")
            raise AccountingException(f"Error generando archivo PLE Mayor: {str(e)}")
    
    def validar_compatibilidad_datos_reales(self, empresa_id: str) -> Dict[str, Any]:
        """
        Validar compatibilidad de datos reales para PLE Mayor
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Dict con reporte de compatibilidad
        """
        try:
            self.logger.info(f"Validando compatibilidad datos reales - Empresa: {empresa_id}")
            
            # Obtener asientos contables
            asientos = self.obtener_asientos_contables_reales(empresa_id)
            
            # Usar el adaptador para validar compatibilidad
            reporte = self.data_adapter.validar_compatibilidad(asientos)
            
            # Agregar información adicional
            reporte.update({
                "empresa_id": empresa_id,
                "fecha_validacion": datetime.now().isoformat(),
                "recomendaciones": []
            })
            
            # Generar recomendaciones basadas en el reporte
            if reporte['compatibilidad'] < 100:
                reporte['recomendaciones'].append("Revisar campos faltantes en asientos contables")
            
            if reporte['errores']:
                reporte['recomendaciones'].append("Corregir errores de estructura de datos")
            
            if reporte['total_asientos'] == 0:
                reporte['recomendaciones'].append("Cargar asientos contables para la empresa")
            
            self.logger.info(f"Validación completada - Compatibilidad: {reporte['compatibilidad']:.1f}%")
            
            return reporte
            
        except Exception as e:
            self.logger.error(f"Error validando compatibilidad: {str(e)}")
            raise AccountingException(f"Error validando compatibilidad: {str(e)}")
