"""
PLEFormatterVentas - Formateador PLE 140000 (34 campos oficiales)
================================================================

Formateador especializado para cumplir exactamente con la estructura
oficial SUNAT de 34 campos para Registro de Ventas PLE 140000.

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Estructura oficial 34 campos PLE 140000 (Registro de Ventas):
1. Período                    2. Código único operación (CUO)
3. Correlativo asiento        4. Fecha emisión comprobante  
5. Fecha vencimiento          6. Tipo comprobante pago
7. Serie comprobante          8. Número comprobante
9. Número final (rangos)      10. Tipo documento cliente
11. Número documento cliente  12. Apellidos/razón social cliente
13. Valor facturado exportación  14. Base imponible gravadas
15. Descuento base imponible  16. IGV/IPM
17. Descuento IGV/IPM        18. Importe exonerado
19. Importe inafecto         20. ISC
21. Base imponible IVAP      22. IVAP
23. Otros tributos/cargos    24. Importe total
25. Código moneda            26. Tipo cambio
27. Fecha constancia detracción  28. Número constancia detracción
29. Indicador servicio gravado SPOT  30. Otros conceptos tributos
31. Base imponible ICBPER    32. ICBPER
33. Error tipo 1,2,3,4       34. Estado operación

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

from ..schemas.schemas_ventas import (
    RegistroVentaResponse,
    PLEVentasExportOptions,
    PLEVentasExportResult
)

logger = logging.getLogger(__name__)


@dataclass
class PLELineaVentas:
    """Línea PLE formateada según estructura oficial SUNAT 34 campos"""
    
    # Datos originales
    registro_venta: RegistroVentaResponse
    
    # 34 CAMPOS OFICIALES SUNAT - REGISTRO VENTAS PLE 140000
    campo_01_periodo: str                        # Período AAAAMM
    campo_02_codigo_unico_operacion: str         # Código único de operación (CUO)
    campo_03_numero_correlativo_asiento: str     # Número correlativo del asiento
    campo_04_fecha_emision_comprobante: str      # Fecha emisión comprobante
    campo_05_fecha_vencimiento: str              # Fecha de vencimiento
    campo_06_tipo_comprobante_pago: str          # Tipo comprobante de pago
    campo_07_serie_comprobante: str              # Serie del comprobante
    campo_08_numero_comprobante: str             # Número del comprobante
    campo_09_numero_final_rango: str             # Número final (rangos)
    campo_10_tipo_documento_cliente: str         # Tipo documento cliente
    campo_11_numero_documento_cliente: str       # Número documento cliente
    campo_12_apellidos_razon_social: str         # Apellidos y nombres/razón social cliente
    campo_13_valor_facturado_exportacion: str   # Valor facturado exportación
    campo_14_base_imponible_gravadas: str        # Base imponible operaciones gravadas
    campo_15_descuento_base_imponible: str       # Descuento de la base imponible
    campo_16_igv_ipm: str                        # IGV/IPM
    campo_17_descuento_igv_ipm: str              # Descuento del IGV/IPM
    campo_18_importe_exonerado: str              # Importe exonerado
    campo_19_importe_inafecto: str               # Importe inafecto
    campo_20_isc: str                            # ISC
    campo_21_base_imponible_ivap: str            # Base imponible arroz pilado (IVAP)
    campo_22_ivap: str                           # Impuesto arroz pilado (IVAP)
    campo_23_otros_tributos_cargos: str          # Otros tributos y cargos
    campo_24_importe_total: str                  # Importe total
    campo_25_codigo_moneda: str                  # Código de la moneda
    campo_26_tipo_cambio: str                    # Tipo de cambio
    campo_27_fecha_constancia_detraccion: str    # Fecha emisión constancia depósito detracción
    campo_28_numero_constancia_detraccion: str   # Número constancia depósito detracción
    campo_29_indicador_servicio_gravado_spot: str # Indicador servicio gravado con SPOT
    campo_30_otros_conceptos_tributos: str       # Otros conceptos tributos
    campo_31_base_imponible_icbper: str          # Base imponible ICBPER
    campo_32_icbper: str                         # ICBPER
    campo_33_error_tipo: str                     # Error tipo 1, 2, 3 y 4
    campo_34_estado_operacion: str               # Estado de la operación
    
    def to_ple_line(self) -> str:
        """Convertir a línea PLE oficial separada por | - 34 CAMPOS OFICIALES SUNAT"""
        campos = [
            self.campo_01_periodo,
            self.campo_02_codigo_unico_operacion,
            self.campo_03_numero_correlativo_asiento,
            self.campo_04_fecha_emision_comprobante,
            self.campo_05_fecha_vencimiento,
            self.campo_06_tipo_comprobante_pago,
            self.campo_07_serie_comprobante,
            self.campo_08_numero_comprobante,
            self.campo_09_numero_final_rango,
            self.campo_10_tipo_documento_cliente,
            self.campo_11_numero_documento_cliente,
            self.campo_12_apellidos_razon_social,
            self.campo_13_valor_facturado_exportacion,
            self.campo_14_base_imponible_gravadas,
            self.campo_15_descuento_base_imponible,
            self.campo_16_igv_ipm,
            self.campo_17_descuento_igv_ipm,
            self.campo_18_importe_exonerado,
            self.campo_19_importe_inafecto,
            self.campo_20_isc,
            self.campo_21_base_imponible_ivap,
            self.campo_22_ivap,
            self.campo_23_otros_tributos_cargos,
            self.campo_24_importe_total,
            self.campo_25_codigo_moneda,
            self.campo_26_tipo_cambio,
            self.campo_27_fecha_constancia_detraccion,
            self.campo_28_numero_constancia_detraccion,
            self.campo_29_indicador_servicio_gravado_spot,
            self.campo_30_otros_conceptos_tributos,
            self.campo_31_base_imponible_icbper,
            self.campo_32_icbper,
            self.campo_33_error_tipo,
            self.campo_34_estado_operacion
        ]
        
        return "|".join(campos)


class PLEFormatterVentas:
    """Formateador oficial SUNAT para PLE 140000 - Registro de Ventas (34 campos)"""
    
    def __init__(self):
        """Inicializar formateador con configuración SUNAT"""
        self.logger = logging.getLogger(__name__)
        
        # Configuración según normativa SUNAT
        self.separador = "|"
        self.longitud_maxima_razon_social = 100
        self.precision_montos = 2
        self.precision_tipo_cambio = 3
        self.formato_fecha_sunat = "%d/%m/%Y"
        
        # Códigos por defecto según normativa
        self.codigo_moneda_default = "PEN"
        self.tipo_cambio_default = "1.000"
    
    def formatear_registro_venta(
        self,
        venta: RegistroVentaResponse,
        periodo_aaaamm: str,
        correlativo_asiento: Optional[str] = None
    ) -> PLELineaVentas:
        """
        Formatear registro de venta a línea PLE oficial 34 campos
        
        Args:
            venta: Registro de venta completo
            periodo_aaaamm: Período formato AAAAMM
            correlativo_asiento: Correlativo del asiento contable
            
        Returns:
            PLELineaVentas: Línea completamente formateada con 34 campos oficiales
        """
        
        # CAMPO 1: Período (AAAAMM)
        campo_01 = periodo_aaaamm
        
        # CAMPO 2: Código único operación (CUO)
        campo_02 = self._generar_codigo_unico_operacion(venta.id, periodo_aaaamm)
        
        # CAMPO 3: Número correlativo del asiento
        campo_03 = self._formatear_correlativo_asiento(correlativo_asiento or venta.numero_comprobante)
        
        # CAMPO 4: Fecha emisión comprobante
        campo_04 = self._formatear_fecha(venta.fecha_emision)
        
        # CAMPO 5: Fecha vencimiento
        campo_05 = self._formatear_fecha(venta.fecha_vencimiento)
        
        # CAMPO 6: Tipo comprobante de pago
        campo_06 = str(venta.tipo_comprobante.value)
        
        # CAMPO 7: Serie del comprobante
        campo_07 = self._formatear_serie_comprobante(venta.serie_comprobante)
        
        # CAMPO 8: Número del comprobante
        campo_08 = self._formatear_numero_comprobante(venta.numero_comprobante)
        
        # CAMPO 9: Número final (para rangos)
        campo_09 = self._formatear_numero_final(venta.numero_final_rango)
        
        # CAMPO 10: Tipo documento cliente
        campo_10 = str(venta.tipo_documento_cliente.value)
        
        # CAMPO 11: Número documento cliente
        campo_11 = self._formatear_numero_documento(venta.numero_documento_cliente)
        
        # CAMPO 12: Apellidos y nombres/razón social cliente
        campo_12 = self._formatear_razon_social(venta.razon_social_cliente)
        
        # CAMPO 13: Valor facturado exportación
        campo_13 = self._formatear_monto(venta.valor_facturado_exportacion)
        
        # CAMPO 14: Base imponible operaciones gravadas
        campo_14 = self._formatear_monto(venta.base_imponible_gravada)
        
        # CAMPO 15: Descuento de la base imponible
        campo_15 = self._formatear_monto(venta.descuento_base_imponible)
        
        # CAMPO 16: IGV/IPM
        campo_16 = self._formatear_monto(venta.igv_ipm)
        
        # CAMPO 17: Descuento del IGV/IPM
        campo_17 = self._formatear_monto(venta.descuento_igv_ipm)
        
        # CAMPO 18: Importe exonerado
        campo_18 = self._formatear_monto(venta.importe_exonerado)
        
        # CAMPO 19: Importe inafecto
        campo_19 = self._formatear_monto(venta.importe_inafecto)
        
        # CAMPO 20: ISC
        campo_20 = self._formatear_monto(venta.isc)
        
        # CAMPO 21: Base imponible arroz pilado (IVAP)
        campo_21 = self._formatear_monto(venta.base_imponible_ivap)
        
        # CAMPO 22: Impuesto arroz pilado (IVAP)
        campo_22 = self._formatear_monto(venta.ivap)
        
        # CAMPO 23: Otros tributos y cargos
        campo_23 = self._formatear_monto(venta.otros_tributos_cargos)
        
        # CAMPO 24: Importe total
        campo_24 = self._formatear_monto(venta.importe_total)
        
        # CAMPO 25: Código de la moneda
        campo_25 = self._formatear_codigo_moneda(venta.codigo_moneda)
        
        # CAMPO 26: Tipo de cambio
        campo_26 = self._formatear_tipo_cambio(venta.tipo_cambio)
        
        # CAMPO 27: Fecha emisión constancia depósito detracción
        campo_27 = self._formatear_fecha(venta.fecha_emision_detraccion)
        
        # CAMPO 28: Número constancia depósito detracción
        campo_28 = self._formatear_constancia_detraccion(venta.numero_constancia_detraccion)
        
        # CAMPO 29: Indicador servicio gravado con SPOT
        campo_29 = self._formatear_indicador_spot(venta.indicador_servicio_gravado_spot)
        
        # CAMPO 30: Otros conceptos tributos
        campo_30 = self._formatear_monto(venta.otros_conceptos_tributos)
        
        # CAMPO 31: Base imponible ICBPER
        campo_31 = self._formatear_monto(venta.base_imponible_icbper)
        
        # CAMPO 32: ICBPER
        campo_32 = self._formatear_monto(venta.icbper)
        
        # CAMPO 33: Error tipo 1, 2, 3 y 4
        campo_33 = self._formatear_indicador_error(venta.indicador_error)
        
        # CAMPO 34: Estado de la operación
        campo_34 = str(venta.estado_operacion.value)
        
        return PLELineaVentas(
            registro_venta=venta,
            campo_01_periodo=campo_01,
            campo_02_codigo_unico_operacion=campo_02,
            campo_03_numero_correlativo_asiento=campo_03,
            campo_04_fecha_emision_comprobante=campo_04,
            campo_05_fecha_vencimiento=campo_05,
            campo_06_tipo_comprobante_pago=campo_06,
            campo_07_serie_comprobante=campo_07,
            campo_08_numero_comprobante=campo_08,
            campo_09_numero_final_rango=campo_09,
            campo_10_tipo_documento_cliente=campo_10,
            campo_11_numero_documento_cliente=campo_11,
            campo_12_apellidos_razon_social=campo_12,
            campo_13_valor_facturado_exportacion=campo_13,
            campo_14_base_imponible_gravadas=campo_14,
            campo_15_descuento_base_imponible=campo_15,
            campo_16_igv_ipm=campo_16,
            campo_17_descuento_igv_ipm=campo_17,
            campo_18_importe_exonerado=campo_18,
            campo_19_importe_inafecto=campo_19,
            campo_20_isc=campo_20,
            campo_21_base_imponible_ivap=campo_21,
            campo_22_ivap=campo_22,
            campo_23_otros_tributos_cargos=campo_23,
            campo_24_importe_total=campo_24,
            campo_25_codigo_moneda=campo_25,
            campo_26_tipo_cambio=campo_26,
            campo_27_fecha_constancia_detraccion=campo_27,
            campo_28_numero_constancia_detraccion=campo_28,
            campo_29_indicador_servicio_gravado_spot=campo_29,
            campo_30_otros_conceptos_tributos=campo_30,
            campo_31_base_imponible_icbper=campo_31,
            campo_32_icbper=campo_32,
            campo_33_error_tipo=campo_33,
            campo_34_estado_operacion=campo_34
        )
    
    # ================================
    # MÉTODOS DE FORMATEO ESPECÍFICO
    # ================================
    
    def _generar_codigo_unico_operacion(self, venta_id: str, periodo: str) -> str:
        """Generar código único de operación para venta"""
        # Formato: V + período (6) + ID única (6 últimos)
        id_sufijo = venta_id[-6:].zfill(6) if len(venta_id) >= 6 else venta_id.zfill(6)
        return f"V{periodo}{id_sufijo}"
    
    def _formatear_correlativo_asiento(self, numero: str) -> str:
        """Formatear número correlativo del asiento"""
        return f"V{numero.zfill(9)}"
    
    def _formatear_fecha(self, fecha: Optional[str]) -> str:
        """Formatear fecha DD/MM/YYYY"""
        if not fecha:
            return ""
        
        try:
            # Si viene en formato DD/MM/YYYY, mantener
            if re.match(r'^\d{2}/\d{2}/\d{4}$', fecha):
                return fecha
            # Si viene en formato YYYY-MM-DD, convertir
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', fecha):
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
                return fecha_obj.strftime("%d/%m/%Y")
            else:
                return ""
        except Exception:
            return ""
    
    def _formatear_serie_comprobante(self, serie: Optional[str]) -> str:
        """Formatear serie del comprobante (máximo 20 caracteres)"""
        if not serie:
            return ""
        return str(serie).strip()[:20]
    
    def _formatear_numero_comprobante(self, numero: str) -> str:
        """Formatear número del comprobante (máximo 20 caracteres)"""
        return str(numero).strip()[:20]
    
    def _formatear_numero_final(self, numero_final: Optional[str]) -> str:
        """Formatear número final para rangos"""
        if not numero_final:
            return ""
        return str(numero_final).strip()[:20]
    
    def _formatear_numero_documento(self, numero: str) -> str:
        """Formatear número de documento (máximo 15 caracteres)"""
        return str(numero).strip()[:15]
    
    def _formatear_razon_social(self, razon_social: str) -> str:
        """Formatear razón social (máximo 100 caracteres)"""
        if not razon_social:
            return ""
        return str(razon_social).strip()[:self.longitud_maxima_razon_social]
    
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
            
            # Redondear a 2 decimales
            decimal_formateado = decimal_monto.quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            
            return str(decimal_formateado)
            
        except Exception:
            return "0.00"
    
    def _formatear_codigo_moneda(self, codigo: str) -> str:
        """Formatear código de moneda (3 caracteres)"""
        if not codigo:
            return self.codigo_moneda_default
        return str(codigo).strip()[:3].upper()
    
    def _formatear_tipo_cambio(self, tipo_cambio: Optional[Union[Decimal, float]]) -> str:
        """Formatear tipo de cambio (3 decimales)"""
        if not tipo_cambio or tipo_cambio <= 0:
            return self.tipo_cambio_default
        
        try:
            # Usar Decimal para precisión exacta
            if isinstance(tipo_cambio, (int, float)):
                decimal_tipo_cambio = Decimal(str(tipo_cambio))
            else:
                decimal_tipo_cambio = tipo_cambio
            
            # Formatear con 3 decimales según SUNAT
            decimal_formateado = decimal_tipo_cambio.quantize(
                Decimal('0.001'), rounding=ROUND_HALF_UP
            )
            
            return str(decimal_formateado)
            
        except Exception:
            return self.tipo_cambio_default
    
    def _formatear_constancia_detraccion(self, numero: Optional[str]) -> str:
        """Formatear número constancia detracción (máximo 23 caracteres)"""
        if not numero:
            return ""
        return str(numero).strip()[:23]
    
    def _formatear_indicador_spot(self, indicador: Optional[str]) -> str:
        """Formatear indicador servicio gravado SPOT (0 o 1)"""
        if not indicador:
            return ""
        return str(indicador).strip()[:1]
    
    def _formatear_indicador_error(self, error: str) -> str:
        """Formatear indicador de error (0-4)"""
        if not error:
            return "0"
        return str(error).strip()[:1]
    
    def formatear_multiple_ventas(
        self,
        ventas: List[RegistroVentaResponse],
        periodo_aaaamm: str
    ) -> List[PLELineaVentas]:
        """
        Formatear múltiples registros de ventas
        
        Args:
            ventas: Lista de registros de venta
            periodo_aaaamm: Período formato AAAAMM
            
        Returns:
            Lista de líneas PLE formateadas
        """
        lineas_ple = []
        
        for i, venta in enumerate(ventas, 1):
            try:
                linea = self.formatear_registro_venta(
                    venta, 
                    periodo_aaaamm,
                    correlativo_asiento=f"{i:010d}"
                )
                lineas_ple.append(linea)
                
            except Exception as e:
                self.logger.error(f"Error formateando venta {venta.id}: {str(e)}")
                raise
        
        return lineas_ple
    
    def generar_contenido_archivo_ple(
        self,
        lineas_ple: List[PLELineaVentas]
    ) -> str:
        """
        Generar contenido completo del archivo PLE
        
        Args:
            lineas_ple: Lista de líneas formateadas
            
        Returns:
            Contenido del archivo TXT
        """
        if not lineas_ple:
            return ""
        
        # Convertir cada línea a texto
        lineas_texto = [linea.to_ple_line() for linea in lineas_ple]
        
        # Unir con saltos de línea y agregar salto final
        contenido = "\n".join(lineas_texto) + "\n"
        
        return contenido
    
    def generar_nombre_archivo_ple(
        self,
        empresa_ruc: str,
        periodo_aaaamm: str,
        correlativo: str = "0001"
    ) -> str:
        """
        Generar nombre de archivo según nomenclatura SUNAT
        
        Formato: LE{RUC}{AAAAMM}00140000{CORRELATIVO}1.txt
        
        Args:
            empresa_ruc: RUC de la empresa
            periodo_aaaamm: Período AAAAMM
            correlativo: Correlativo del archivo
            
        Returns:
            Nombre del archivo
        """
        return f"LE{empresa_ruc}{periodo_aaaamm}00140000{correlativo.zfill(4)}1.txt"
