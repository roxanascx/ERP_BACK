"""
PLEFormatterMayor - Formateador PLE 050200 Libro Mayor
=====================================================

Formateador especializado para generar archivos PLE 050200 (Libro Mayor)
según especificaciones oficiales SUNAT.

El Libro Mayor muestra los movimientos contables agrupados por cuenta,
con 9 campos oficiales según Resolución SUNAT N° 286-2009.

Campos PLE 050200 (9 campos oficiales):
1. Período (AAAAMM00)
2. Código de cuenta contable
3. Descripción de cuenta contable
4. Saldo deudor inicial
5. Saldo acreedor inicial
6. Movimiento del debe
7. Movimiento del haber
8. Saldo final deudor
9. Saldo final acreedor

Características:
- Formato de texto separado por |
- Codificación ISO-8859-1
- Precisión decimal 2 lugares
- Validaciones SUNAT completas

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

from ..schemas.schemas_mayor import (
    LibroMayorResponse,
    TipoCuentaContable,
    NaturalezaCuenta,
    EstadoCuentaMayor
)

logger = logging.getLogger(__name__)


@dataclass
class PLELineaMayor:
    """Línea formateada para PLE 050200 - Libro Mayor (9 campos oficiales)"""
    
    # CAMPOS OFICIALES SUNAT PLE 050200
    campo_01_periodo: str                        # Período AAAAMM00
    campo_02_codigo_cuenta: str                  # Código de cuenta contable
    campo_03_descripcion_cuenta: str             # Descripción de cuenta contable
    campo_04_saldo_deudor_inicial: str           # Saldo deudor inicial
    campo_05_saldo_acreedor_inicial: str         # Saldo acreedor inicial
    campo_06_movimiento_debe: str                # Movimiento del debe
    campo_07_movimiento_haber: str               # Movimiento del haber
    campo_08_saldo_final_deudor: str             # Saldo final deudor
    campo_09_saldo_final_acreedor: str           # Saldo final acreedor
    
    def to_ple_line(self) -> str:
        """Convertir a línea PLE oficial separada por | - 9 CAMPOS OFICIALES SUNAT"""
        campos = [
            self.campo_01_periodo,
            self.campo_02_codigo_cuenta,
            self.campo_03_descripcion_cuenta,
            self.campo_04_saldo_deudor_inicial,
            self.campo_05_saldo_acreedor_inicial,
            self.campo_06_movimiento_debe,
            self.campo_07_movimiento_haber,
            self.campo_08_saldo_final_deudor,
            self.campo_09_saldo_final_acreedor
        ]
        
        # Unir con separador oficial SUNAT (no agregar | al final)
        return "|".join(campos)
    
    def validar_estructura(self) -> tuple[bool, List[str]]:
        """Validar estructura de la línea PLE"""
        errores = []
        
        # Validar que todos los campos estén presentes
        campos = [
            self.campo_01_periodo,
            self.campo_02_codigo_cuenta,
            self.campo_03_descripcion_cuenta,
            self.campo_04_saldo_deudor_inicial,
            self.campo_05_saldo_acreedor_inicial,
            self.campo_06_movimiento_debe,
            self.campo_07_movimiento_haber,
            self.campo_08_saldo_final_deudor,
            self.campo_09_saldo_final_acreedor
        ]
        
        if len(campos) != 9:
            errores.append(f"Número de campos incorrecto: {len(campos)}, esperado: 9")
        
        # Validar período
        if not re.match(r'^\d{8}$', self.campo_01_periodo):
            errores.append(f"Formato de período incorrecto: {self.campo_01_periodo}")
        
        # Validar código de cuenta
        if not self.campo_02_codigo_cuenta.strip():
            errores.append("Código de cuenta contable es obligatorio")
        
        # Validar descripción
        if not self.campo_03_descripcion_cuenta.strip():
            errores.append("Descripción de cuenta es obligatoria")
        
        # Validar montos
        for i, campo_monto in enumerate([
            self.campo_04_saldo_deudor_inicial,
            self.campo_05_saldo_acreedor_inicial,
            self.campo_06_movimiento_debe,
            self.campo_07_movimiento_haber,
            self.campo_08_saldo_final_deudor,
            self.campo_09_saldo_final_acreedor
        ], 4):
            try:
                if campo_monto and campo_monto != "0.00":
                    Decimal(campo_monto)
            except:
                errores.append(f"Campo {i} - formato de monto inválido: {campo_monto}")
        
        return len(errores) == 0, errores


class PLEFormatterMayor:
    """Formateador para Libro Mayor PLE 050200"""
    
    def __init__(self):
        """Inicializar formateador"""
        self.logger = logging.getLogger(__name__)
    
    def formatear_cuenta_mayor(
        self,
        cuenta: LibroMayorResponse,
        periodo_aaaamm: str
    ) -> PLELineaMayor:
        """
        Formatear una cuenta del Libro Mayor a línea PLE 050200
        
        Args:
            cuenta: Datos de la cuenta del Libro Mayor
            periodo_aaaamm: Período en formato AAAAMM
            
        Returns:
            PLELineaMayor: Línea formateada para PLE
        """
        
        # CAMPO 1: Período (AAAAMM00)
        campo_01 = self._formatear_periodo(periodo_aaaamm)
        
        # CAMPO 2: Código de cuenta contable
        campo_02 = self._formatear_codigo_cuenta(cuenta.codigo_cuenta_contable)
        
        # CAMPO 3: Descripción de cuenta contable
        campo_03 = self._formatear_descripcion_cuenta(cuenta.descripcion_cuenta)
        
        # CAMPO 4: Saldo deudor inicial
        campo_04 = self._formatear_monto(cuenta.saldo_deudor_inicial)
        
        # CAMPO 5: Saldo acreedor inicial
        campo_05 = self._formatear_monto(cuenta.saldo_acreedor_inicial)
        
        # CAMPO 6: Movimiento del debe
        campo_06 = self._formatear_monto(cuenta.movimiento_debe)
        
        # CAMPO 7: Movimiento del haber
        campo_07 = self._formatear_monto(cuenta.movimiento_haber)
        
        # CAMPO 8: Saldo final deudor
        campo_08 = self._formatear_monto(cuenta.saldo_final_deudor)
        
        # CAMPO 9: Saldo final acreedor
        campo_09 = self._formatear_monto(cuenta.saldo_final_acreedor)
        
        return PLELineaMayor(
            campo_01_periodo=campo_01,
            campo_02_codigo_cuenta=campo_02,
            campo_03_descripcion_cuenta=campo_03,
            campo_04_saldo_deudor_inicial=campo_04,
            campo_05_saldo_acreedor_inicial=campo_05,
            campo_06_movimiento_debe=campo_06,
            campo_07_movimiento_haber=campo_07,
            campo_08_saldo_final_deudor=campo_08,
            campo_09_saldo_final_acreedor=campo_09
        )
    
    # ================================
    # MÉTODOS PRIVADOS DE FORMATEO
    # ================================
    
    def _formatear_periodo(self, periodo_aaaamm: str) -> str:
        """Formatear período a formato AAAAMM00"""
        if not periodo_aaaamm or len(periodo_aaaamm) != 6:
            raise ValueError(f"Período debe tener formato AAAAMM: {periodo_aaaamm}")
        
        try:
            # Validar que sea numérico
            int(periodo_aaaamm)
            return periodo_aaaamm + "00"  # AAAAMM00
        except ValueError:
            raise ValueError(f"Período debe ser numérico: {periodo_aaaamm}")
    
    def _formatear_codigo_cuenta(self, codigo: str) -> str:
        """Formatear código de cuenta contable"""
        if not codigo:
            raise ValueError("Código de cuenta contable es obligatorio")
        
        # Limpiar y formatear
        codigo_limpio = codigo.strip().upper()
        
        # Validar longitud máxima según SUNAT
        if len(codigo_limpio) > 24:
            raise ValueError(f"Código de cuenta muy largo: {len(codigo_limpio)} caracteres")
        
        return codigo_limpio
    
    def _formatear_descripcion_cuenta(self, descripcion: str) -> str:
        """Formatear descripción de cuenta contable"""
        if not descripcion:
            raise ValueError("Descripción de cuenta es obligatoria")
        
        # Limpiar descripción
        descripcion_limpia = descripcion.strip()
        
        # Reemplazar caracteres especiales que pueden causar problemas en PLE
        descripcion_limpia = re.sub(r'[|]', '-', descripcion_limpia)  # Reemplazar separadores
        descripcion_limpia = re.sub(r'[\r\n\t]', ' ', descripcion_limpia)  # Reemplazar saltos
        descripcion_limpia = re.sub(r'\s+', ' ', descripcion_limpia)  # Normalizar espacios
        
        # Validar longitud máxima
        if len(descripcion_limpia) > 200:
            descripcion_limpia = descripcion_limpia[:197] + "..."
        
        return descripcion_limpia
    
    def _formatear_monto(self, monto: Optional[Union[Decimal, float]]) -> str:
        """Formatear monto con precisión SUNAT (2 decimales)"""
        if not monto or monto == 0:
            return "0.00"
        
        try:
            # Usar Decimal para precisión exacta
            if isinstance(monto, (int, float)):
                decimal_monto = Decimal(str(monto))
            else:
                decimal_monto = monto
            
            # Redondear a 2 decimales según normas SUNAT
            decimal_formateado = decimal_monto.quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            # Formatear sin separadores de miles (según especificación SUNAT)
            return str(decimal_formateado)
            
        except Exception as e:
            self.logger.error(f"Error formateando monto {monto}: {str(e)}")
            return "0.00"
    
    # ================================
    # MÉTODOS DE GENERACIÓN DE ARCHIVO
    # ================================
    
    def formatear_multiple_cuentas(
        self,
        cuentas: List[LibroMayorResponse],
        periodo_aaaamm: str
    ) -> List[PLELineaMayor]:
        """
        Formatear múltiples cuentas del Libro Mayor
        
        Args:
            cuentas: Lista de cuentas del Libro Mayor
            periodo_aaaamm: Período en formato AAAAMM
            
        Returns:
            List[PLELineaMayor]: Lista de líneas formateadas
        """
        lineas_ple = []
        errores = []
        
        for i, cuenta in enumerate(cuentas):
            try:
                linea = self.formatear_cuenta_mayor(cuenta, periodo_aaaamm)
                
                # Validar línea generada
                es_valida, errores_linea = linea.validar_estructura()
                if not es_valida:
                    self.logger.warning(f"Cuenta {cuenta.codigo_cuenta_contable}: {errores_linea}")
                
                lineas_ple.append(linea)
                
            except Exception as e:
                error_msg = f"Error formateando cuenta {i+1} ({cuenta.codigo_cuenta_contable}): {str(e)}"
                self.logger.error(error_msg)
                errores.append(error_msg)
        
        if errores:
            self.logger.warning(f"Se encontraron {len(errores)} errores durante el formateo")
        
        return lineas_ple
    
    def generar_contenido_archivo_ple(self, lineas_ple: List[PLELineaMayor]) -> str:
        """
        Generar contenido completo del archivo PLE 050200
        
        Args:
            lineas_ple: Lista de líneas PLE formateadas
            
        Returns:
            str: Contenido del archivo PLE
        """
        if not lineas_ple:
            return ""
        
        # Convertir objetos PLELineaMayor a texto
        lineas_texto = [linea.to_ple_line() for linea in lineas_ple]
        
        # Unir líneas con salto de línea
        contenido = "\n".join(lineas_texto)
        
        self.logger.info(f"Archivo PLE generado: {len(lineas_texto)} líneas")
        
        return contenido
    
    def generar_nombre_archivo_ple(
        self,
        empresa_ruc: str,
        periodo_aaaamm: str,
        correlativo: str = "001"
    ) -> str:
        """
        Generar nombre oficial del archivo PLE 050200
        
        Formato: LE{RUC}{AAAA}{MM}00050200{CORRELATIVO}11.txt
        
        Args:
            empresa_ruc: RUC de la empresa (11 dígitos)
            periodo_aaaamm: Período AAAAMM
            correlativo: Correlativo del archivo (001-999)
            
        Returns:
            str: Nombre del archivo PLE
        """
        try:
            # Validar RUC
            if not empresa_ruc or len(empresa_ruc) != 11:
                raise ValueError(f"RUC debe tener 11 dígitos: {empresa_ruc}")
            
            # Validar período
            if not periodo_aaaamm or len(periodo_aaaamm) != 6:
                raise ValueError(f"Período debe tener formato AAAAMM: {periodo_aaaamm}")
            
            # Validar correlativo
            if not correlativo or len(correlativo) != 3:
                correlativo = "001"
            
            # Extraer año y mes
            año = periodo_aaaamm[:4]
            mes = periodo_aaaamm[4:6]
            
            # Formato oficial SUNAT para PLE 050200
            # LE + RUC + AAAA + MM + 00 + 050200 + CORRELATIVO + 11 + .txt
            nombre_archivo = f"LE{empresa_ruc}{año}{mes}0005020000{correlativo}11.txt"
            
            self.logger.info(f"Nombre de archivo PLE generado: {nombre_archivo}")
            
            return nombre_archivo
            
        except Exception as e:
            self.logger.error(f"Error generando nombre de archivo: {str(e)}")
            # Nombre por defecto en caso de error
            return f"LE{empresa_ruc or '00000000000'}{periodo_aaaamm or '202408'}0005020000{correlativo or '001'}11.txt"
    
    # ================================
    # MÉTODOS DE VALIDACIÓN Y CONTROL
    # ================================
    
    def validar_partida_doble(self, cuentas: List[LibroMayorResponse]) -> tuple[bool, Decimal]:
        """
        Validar principio de partida doble en el Libro Mayor
        
        Args:
            cuentas: Lista de cuentas del Libro Mayor
            
        Returns:
            tuple[bool, Decimal]: (Es válido, Diferencia)
        """
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        
        for cuenta in cuentas:
            total_debe += cuenta.movimiento_debe or Decimal('0.00')
            total_haber += cuenta.movimiento_haber or Decimal('0.00')
        
        diferencia = abs(total_debe - total_haber)
        es_valido = diferencia <= Decimal('0.01')  # Tolerancia para redondeos
        
        if not es_valido:
            self.logger.warning(f"Diferencia en partida doble: {diferencia}")
        
        return es_valido, diferencia
    
    def validar_balance_saldos(self, cuentas: List[LibroMayorResponse]) -> Dict[str, Any]:
        """
        Validar balance de saldos finales
        
        Args:
            cuentas: Lista de cuentas del Libro Mayor
            
        Returns:
            Dict: Resultado de validación con totales
        """
        total_saldos_deudores = Decimal('0.00')
        total_saldos_acreedores = Decimal('0.00')
        
        cuentas_con_error = []
        
        for cuenta in cuentas:
            # Sumar saldos finales
            saldo_deudor = cuenta.saldo_final_deudor or Decimal('0.00')
            saldo_acreedor = cuenta.saldo_final_acreedor or Decimal('0.00')
            
            total_saldos_deudores += saldo_deudor
            total_saldos_acreedores += saldo_acreedor
            
            # Validar que no tenga saldo deudor y acreedor simultáneamente
            if saldo_deudor > 0 and saldo_acreedor > 0:
                cuentas_con_error.append({
                    "codigo": cuenta.codigo_cuenta_contable,
                    "error": "Saldo deudor y acreedor simultáneo",
                    "saldo_deudor": saldo_deudor,
                    "saldo_acreedor": saldo_acreedor
                })
        
        diferencia_balance = abs(total_saldos_deudores - total_saldos_acreedores)
        balance_correcto = diferencia_balance <= Decimal('0.01')
        
        return {
            "balance_correcto": balance_correcto,
            "total_saldos_deudores": total_saldos_deudores,
            "total_saldos_acreedores": total_saldos_acreedores,
            "diferencia": diferencia_balance,
            "cuentas_con_errores": cuentas_con_error,
            "total_cuentas": len(cuentas),
            "cuentas_erroneas": len(cuentas_con_error)
        }
    
    def validar_archivo(self, contenido_archivo: str) -> Dict[str, Any]:
        """
        Validar archivo PLE 050200 generado
        
        Args:
            contenido_archivo: Contenido del archivo PLE
            
        Returns:
            Dict: Resultado de validación
        """
        errores = []
        warnings = []
        
        if not contenido_archivo or contenido_archivo.strip() == "":
            return {
                "es_valido": False,
                "errores": ["Archivo vacío"],
                "warnings": [],
                "total_lineas": 0,
                "estadisticas": {}
            }
        
        lineas = contenido_archivo.strip().split('\n')
        total_lineas = len(lineas)
        
        # Validar estructura de líneas
        for i, linea in enumerate(lineas, 1):
            campos = linea.split('|')
            
            # Validar número de campos (debe ser 9)
            if len(campos) != 9:
                errores.append(f"Línea {i}: Número de campos incorrecto ({len(campos)}, esperado: 9)")
                continue
            
            # Validar período (campo 1)
            if not re.match(r'^\d{8}$', campos[0]):
                errores.append(f"Línea {i}: Formato de período incorrecto ({campos[0]})")
            
            # Validar código de cuenta (campo 2)
            if not campos[1].strip():
                errores.append(f"Línea {i}: Código de cuenta vacío")
            
            # Validar descripción (campo 3)
            if not campos[2].strip():
                errores.append(f"Línea {i}: Descripción de cuenta vacía")
            
            # Validar montos (campos 4-9)
            for j in range(3, 9):
                try:
                    if campos[j] and campos[j] != "0.00":
                        Decimal(campos[j])
                except:
                    errores.append(f"Línea {i}, Campo {j+1}: Formato de monto inválido ({campos[j]})")
        
        # Calcular estadísticas
        total_debe = Decimal('0.00')
        total_haber = Decimal('0.00')
        
        for linea in lineas:
            campos = linea.split('|')
            if len(campos) >= 9:
                try:
                    total_debe += Decimal(campos[5]) if campos[5] else Decimal('0.00')
                    total_haber += Decimal(campos[6]) if campos[6] else Decimal('0.00')
                except:
                    pass
        
        diferencia = abs(total_debe - total_haber)
        if diferencia > Decimal('0.01'):
            warnings.append(f"Diferencia en partida doble: {diferencia}")
        
        es_valido = len(errores) == 0
        
        return {
            "es_valido": es_valido,
            "errores": errores,
            "warnings": warnings,
            "total_lineas": total_lineas,
            "estadisticas": {
                "total_debe": total_debe,
                "total_haber": total_haber,
                "diferencia": diferencia,
                "partida_doble_correcta": diferencia <= Decimal('0.01')
            }
        }

    def generar_estadisticas_archivo(
        self,
        cuentas: List[LibroMayorResponse],
        lineas_ple: List[PLELineaMayor]
    ) -> Dict[str, Any]:
        """
        Generar estadísticas del archivo PLE generado
        
        Args:
            cuentas: Lista original de cuentas
            lineas_ple: Líneas PLE generadas
            
        Returns:
            Dict: Estadísticas completas
        """
        # Calcular totales por tipo de cuenta
        totales_por_tipo = {}
        cuentas_por_naturaleza = {"DEUDORA": 0, "ACREEDORA": 0}
        
        total_movimientos_debe = Decimal('0.00')
        total_movimientos_haber = Decimal('0.00')
        
        for cuenta in cuentas:
            # Determinar tipo de cuenta por primer dígito
            primer_digito = cuenta.codigo_cuenta_contable[0] if cuenta.codigo_cuenta_contable else '0'
            tipo_cuenta = {
                '1': 'ACTIVO',
                '2': 'PASIVO', 
                '3': 'PATRIMONIO',
                '4': 'INGRESOS',
                '5': 'GASTOS'
            }.get(primer_digito, 'OTROS')
            
            if tipo_cuenta not in totales_por_tipo:
                totales_por_tipo[tipo_cuenta] = {
                    "cantidad": 0,
                    "saldo_final": Decimal('0.00'),
                    "movimientos": Decimal('0.00')
                }
            
            totales_por_tipo[tipo_cuenta]["cantidad"] += 1
            totales_por_tipo[tipo_cuenta]["saldo_final"] += (
                (cuenta.saldo_final_deudor or Decimal('0.00')) - 
                (cuenta.saldo_final_acreedor or Decimal('0.00'))
            )
            totales_por_tipo[tipo_cuenta]["movimientos"] += (
                (cuenta.movimiento_debe or Decimal('0.00')) + 
                (cuenta.movimiento_haber or Decimal('0.00'))
            )
            
            # Sumar movimientos totales
            total_movimientos_debe += cuenta.movimiento_debe or Decimal('0.00')
            total_movimientos_haber += cuenta.movimiento_haber or Decimal('0.00')
            
            # Contar por naturaleza
            if (cuenta.saldo_final_deudor or Decimal('0.00')) > (cuenta.saldo_final_acreedor or Decimal('0.00')):
                cuentas_por_naturaleza["DEUDORA"] += 1
            else:
                cuentas_por_naturaleza["ACREEDORA"] += 1
        
        return {
            "total_cuentas_procesadas": len(cuentas),
            "total_lineas_generadas": len(lineas_ple),
            "totales_por_tipo_cuenta": totales_por_tipo,
            "cuentas_por_naturaleza": cuentas_por_naturaleza,
            "total_movimientos_debe": total_movimientos_debe,
            "total_movimientos_haber": total_movimientos_haber,
            "diferencia_movimientos": abs(total_movimientos_debe - total_movimientos_haber),
            "validacion_partida_doble": abs(total_movimientos_debe - total_movimientos_haber) <= Decimal('0.01')
        }
