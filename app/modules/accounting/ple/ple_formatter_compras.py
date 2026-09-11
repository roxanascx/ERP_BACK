"""
PLEFormatterCompras - Formateador PLE 080000 (32 campos oficiales)
================================================================

Formateador especializado para cumplir exactamente con la estructura
oficial SUNAT de 32 campos para Registro de Compras PLE 080000.

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Estructura oficial 32 campos PLE 080000 (Registro de Compras):
1. Período                    2. Código único operación (CUO)
3. Correlativo asiento        4. Fecha emisión comprobante  
5. Fecha vencimiento          6. Tipo comprobante pago
7. Serie comprobante          8. Año emisión DUA/DSI
9. Número comprobante         10. Número final (rangos)
11. Tipo documento proveedor  12. Número documento proveedor
13. Apellidos/razón social    14. Base imponible gravadas
15. IGV                       16. Base imponible op. mixtas
17. IGV op. mixtas           18. Base imponible exportación
19. IGV exportación          20. Base imponible no gravadas
21. ISC                      22. Otros tributos y cargos
23. Importe total            24. Código moneda
25. Tipo cambio              26. Fecha constancia detracción
27. Número constancia detracción  28. Marca retención
29. Clasificación bienes     30. Identificación contrato
31. Error tipo 1,2,3,4       32. Medio pago
33. Estado operación

Autor: Sistema ERP - FASE 2.1
Fecha: Agosto 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

from ..schemas.compras_schemas import (
    RegistroCompraResponse,
    PLEComprasExportOptions,
    PLEComprasExportResult
)

logger = logging.getLogger(__name__)


@dataclass
class PLELineaCompras:
    """Línea PLE formateada según estructura oficial SUNAT 32 campos"""
    
    # Datos originales
    registro_compra: RegistroCompraResponse
    
    # 32 CAMPOS OFICIALES SUNAT - REGISTRO COMPRAS PLE 080000
    campo_01_periodo: str                        # Período AAAAMM
    campo_02_codigo_unico_operacion: str         # Código único de operación (CUO)
    campo_03_numero_correlativo_asiento: str     # Número correlativo del asiento
    campo_04_fecha_emision_comprobante: str      # Fecha emisión comprobante
    campo_05_fecha_vencimiento: str              # Fecha de vencimiento
    campo_06_tipo_comprobante_pago: str          # Tipo comprobante de pago
    campo_07_serie_comprobante: str              # Serie del comprobante
    campo_08_anio_emision_dua_dsi: str          # Año emisión DUA/DSI
    campo_09_numero_comprobante: str             # Número del comprobante
    campo_10_numero_final_rango: str             # Número final (rangos)
    campo_11_tipo_documento_proveedor: str       # Tipo documento proveedor
    campo_12_numero_documento_proveedor: str     # Número documento proveedor
    campo_13_apellidos_razon_social: str         # Apellidos y nombres/razón social
    campo_14_base_imponible_gravadas: str        # Base imponible adquisiciones gravadas
    campo_15_igv: str                            # IGV
    campo_16_base_imponible_mixtas: str          # Base imponible gravadas dest. op. gravadas y exoneradas
    campo_17_igv_mixtas: str                     # IGV adquisiciones gravadas dest. op. gravadas y exoneradas
    campo_18_base_imponible_exportacion: str     # Base imponible gravadas dest. operaciones exportación
    campo_19_igv_exportacion: str                # IGV adquisiciones gravadas dest. operaciones exportación
    campo_20_base_imponible_no_gravadas: str     # Base imponible adquisiciones no gravadas
    campo_21_isc: str                            # ISC
    campo_22_otros_tributos_cargos: str          # Otros tributos y cargos
    campo_23_importe_total: str                  # Importe total
    campo_24_codigo_moneda: str                  # Código de la moneda
    campo_25_tipo_cambio: str                    # Tipo de cambio
    campo_26_fecha_constancia_detraccion: str    # Fecha emisión constancia depósito detracción
    campo_27_numero_constancia_detraccion: str   # Número constancia depósito detracción
    campo_28_marca_retencion: str                # Marca comprobante sujeto retención
    campo_29_clasificacion_bienes: str           # Clasificación bienes y servicios
    campo_30_identificacion_contrato: str        # Identificación del contrato
    campo_31_error_tipo: str                     # Error tipo 1, 2, 3 y 4
    campo_32_medio_pago: str                     # Medio de pago
    campo_33_estado_operacion: str               # Estado de la operación
    
    def to_ple_line(self) -> str:
        """Convertir a línea PLE oficial separada por | - 32 CAMPOS OFICIALES SUNAT"""
        campos = [
            self.campo_01_periodo,
            self.campo_02_codigo_unico_operacion,
            self.campo_03_numero_correlativo_asiento,
            self.campo_04_fecha_emision_comprobante,
            self.campo_05_fecha_vencimiento,
            self.campo_06_tipo_comprobante_pago,
            self.campo_07_serie_comprobante,
            self.campo_08_anio_emision_dua_dsi,
            self.campo_09_numero_comprobante,
            self.campo_10_numero_final_rango,
            self.campo_11_tipo_documento_proveedor,
            self.campo_12_numero_documento_proveedor,
            self.campo_13_apellidos_razon_social,
            self.campo_14_base_imponible_gravadas,
            self.campo_15_igv,
            self.campo_16_base_imponible_mixtas,
            self.campo_17_igv_mixtas,
            self.campo_18_base_imponible_exportacion,
            self.campo_19_igv_exportacion,
            self.campo_20_base_imponible_no_gravadas,
            self.campo_21_isc,
            self.campo_22_otros_tributos_cargos,
            self.campo_23_importe_total,
            self.campo_24_codigo_moneda,
            self.campo_25_tipo_cambio,
            self.campo_26_fecha_constancia_detraccion,
            self.campo_27_numero_constancia_detraccion,
            self.campo_28_marca_retencion,
            self.campo_29_clasificacion_bienes,
            self.campo_30_identificacion_contrato,
            self.campo_31_error_tipo,
            self.campo_32_medio_pago,
            self.campo_33_estado_operacion
        ]
        
        return "|".join(campos) + "|"


def _codigo(valor) -> str:
    """
    Codigo SUNAT de un campo que puede llegar como texto o como Enum.

    El esquema los declara `str`, pero hay rutas que todavia construyen el
    registro con los Enum de compras_schemas. La version anterior hacia `.value`
    a secas y fallaba con AttributeError sobre cualquier registro real.
    """
    if valor is None:
        return ""
    return str(getattr(valor, "value", valor)).strip()


class PLEFormatterCompras:
    """Formateador oficial SUNAT para PLE 080000 - Registro de Compras (32 campos)"""
    
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
    
    def formatear_registro_compra(
        self,
        compra: RegistroCompraResponse,
        periodo_aaaamm: str,
        correlativo_asiento: Optional[str] = None
    ) -> PLELineaCompras:
        """
        Formatear registro de compra a línea PLE oficial 32 campos
        
        Args:
            compra: Registro de compra completo
            periodo_aaaamm: Período formato AAAAMM
            correlativo_asiento: Correlativo del asiento contable
            
        Returns:
            PLELineaCompras: Línea completamente formateada con 32 campos oficiales
        """
        
        # CAMPO 1: Período (AAAAMM)
        campo_01 = periodo_aaaamm
        
        # CAMPO 2: Código único operación (CUO)
        campo_02 = self._generar_codigo_unico_operacion(compra.id, periodo_aaaamm)
        
        # CAMPO 3: Número correlativo del asiento
        campo_03 = self._formatear_correlativo_asiento(correlativo_asiento or compra.numero_comprobante)
        
        # CAMPO 4: Fecha emisión comprobante
        campo_04 = self._formatear_fecha(compra.fecha_comprobante)
        
        # CAMPO 5: Fecha vencimiento
        campo_05 = self._formatear_fecha(compra.fecha_vencimiento)
        
        # CAMPO 6: Tipo comprobante de pago
        campo_06 = _codigo(compra.tipo_comprobante)
        
        # CAMPO 7: Serie del comprobante
        campo_07 = self._formatear_serie_comprobante(compra.serie_comprobante)
        
        # CAMPO 8: Año emisión DUA/DSI (solo para importaciones)
        campo_08 = str(compra.anio_emision_dua_dsi or "")[:4]
        
        # CAMPO 9: Número del comprobante
        campo_09 = self._formatear_numero_comprobante(compra.numero_comprobante)
        
        # CAMPO 10: Número final (para rangos)
        campo_10 = self._formatear_numero_final(compra.numero_final_rango)
        
        # CAMPO 11: Tipo documento proveedor
        campo_11 = _codigo(compra.tipo_documento_proveedor)
        
        # CAMPO 12: Número documento proveedor
        campo_12 = self._formatear_numero_documento(compra.numero_documento_proveedor)
        
        # CAMPO 13: Apellidos y nombres/razón social
        campo_13 = self._formatear_razon_social(compra.razon_social_proveedor)
        
        # CAMPO 14: Base imponible adquisiciones gravadas
        campo_14 = self._formatear_monto(compra.base_imponible_gravada)
        
        # CAMPO 15: IGV
        campo_15 = self._formatear_monto(compra.igv)
        
        # CAMPO 16: Base imponible gravadas destinadas a operaciones gravadas y exoneradas
        campo_16 = self._formatear_monto(compra.base_imponible_gravada_operaciones_mixtas)
        
        # CAMPO 17: IGV adquisiciones gravadas destinadas a operaciones gravadas y exoneradas
        campo_17 = self._formatear_monto(compra.igv_operaciones_mixtas)
        
        # CAMPO 18: Base imponible adquisiciones gravadas destinadas a operaciones de exportación
        campo_18 = self._formatear_monto(compra.base_imponible_gravada_exportacion)
        
        # CAMPO 19: IGV adquisiciones gravadas destinadas a operaciones de exportación
        campo_19 = self._formatear_monto(compra.igv_exportacion)
        
        # CAMPO 20: Base imponible adquisiciones no gravadas
        campo_20 = self._formatear_monto(compra.base_imponible_no_gravada)
        
        # CAMPO 21: ISC
        campo_21 = self._formatear_monto(compra.isc)
        
        # CAMPO 22: Otros tributos y cargos
        campo_22 = self._formatear_monto(compra.otros_tributos)
        
        # CAMPO 23: Importe total
        campo_23 = self._formatear_monto(compra.importe_total)
        
        # CAMPO 24: Código de la moneda
        campo_24 = self._formatear_codigo_moneda(compra.moneda)
        
        # CAMPO 25: Tipo de cambio
        campo_25 = self._formatear_tipo_cambio(compra.tipo_cambio)
        
        # CAMPO 26: Fecha emisión constancia depósito detracción
        campo_26 = self._formatear_fecha(compra.fecha_emision_detraccion)
        
        # CAMPO 27: Número constancia depósito detracción
        campo_27 = self._formatear_constancia_detraccion(compra.numero_constancia_detraccion)
        
        # CAMPO 28: Marca comprobante sujeto retención
        campo_28 = self._formatear_marca_retencion(compra.marca_comprobante_retencion)
        
        # CAMPO 29: Clasificación bienes y servicios
        campo_29 = self._formatear_clasificacion_bienes(compra.clasificacion_bienes_servicios)
        
        # CAMPO 30: Identificación del contrato
        campo_30 = self._formatear_identificacion_contrato(compra.identificacion_contrato)
        
        # CAMPO 31: Error tipo 1, 2, 3 y 4
        campo_31 = self._formatear_indicador_error(compra.indicador_error)
        
        # CAMPO 32: Medio de pago
        campo_32 = self._formatear_medio_pago(compra.medio_pago)
        
        # CAMPO 33: Estado de la operación
        campo_33 = _codigo(compra.estado_operacion)
        
        return PLELineaCompras(
            registro_compra=compra,
            campo_01_periodo=campo_01,
            campo_02_codigo_unico_operacion=campo_02,
            campo_03_numero_correlativo_asiento=campo_03,
            campo_04_fecha_emision_comprobante=campo_04,
            campo_05_fecha_vencimiento=campo_05,
            campo_06_tipo_comprobante_pago=campo_06,
            campo_07_serie_comprobante=campo_07,
            campo_08_anio_emision_dua_dsi=campo_08,
            campo_09_numero_comprobante=campo_09,
            campo_10_numero_final_rango=campo_10,
            campo_11_tipo_documento_proveedor=campo_11,
            campo_12_numero_documento_proveedor=campo_12,
            campo_13_apellidos_razon_social=campo_13,
            campo_14_base_imponible_gravadas=campo_14,
            campo_15_igv=campo_15,
            campo_16_base_imponible_mixtas=campo_16,
            campo_17_igv_mixtas=campo_17,
            campo_18_base_imponible_exportacion=campo_18,
            campo_19_igv_exportacion=campo_19,
            campo_20_base_imponible_no_gravadas=campo_20,
            campo_21_isc=campo_21,
            campo_22_otros_tributos_cargos=campo_22,
            campo_23_importe_total=campo_23,
            campo_24_codigo_moneda=campo_24,
            campo_25_tipo_cambio=campo_25,
            campo_26_fecha_constancia_detraccion=campo_26,
            campo_27_numero_constancia_detraccion=campo_27,
            campo_28_marca_retencion=campo_28,
            campo_29_clasificacion_bienes=campo_29,
            campo_30_identificacion_contrato=campo_30,
            campo_31_error_tipo=campo_31,
            campo_32_medio_pago=campo_32,
            campo_33_estado_operacion=campo_33
        )
    
    # ================================
    # MÉTODOS DE FORMATEO ESPECÍFICO
    # ================================
    
    def _generar_codigo_unico_operacion(self, compra_id: str, periodo: str) -> str:
        """Generar código único de operación para compra"""
        # Formato: C + período (6) + ID única (6 últimos)
        id_sufijo = compra_id[-6:].zfill(6) if len(compra_id) >= 6 else compra_id.zfill(6)
        return f"C{periodo}{id_sufijo}"
    
    def _formatear_correlativo_asiento(self, numero: str) -> str:
        """Formatear número correlativo del asiento"""
        return f"C{numero.zfill(9)}"
    
    def _formatear_fecha(self, fecha) -> str:
        """
        Fecha en DD/MM/YYYY, que es como la quiere SUNAT.

        Acepta objetos `date` además de texto: el esquema declara los campos
        de fecha como `date`, y la versión anterior solo miraba cadenas. Al
        pasarle un `date`, el `re.match` lanzaba TypeError, el `except` se lo
        tragaba y **todas las fechas del archivo salían vacías** sin un solo
        mensaje de error.
        """
        if not fecha:
            return ""

        if isinstance(fecha, (datetime, date)):
            return fecha.strftime("%d/%m/%Y")

        try:
            texto = str(fecha).strip()
            # Ya viene como la quiere SUNAT
            if re.match(r'^\d{2}/\d{2}/\d{4}$', texto):
                return texto
            # ISO, que es como lo guarda Mongo
            if re.match(r'^\d{4}-\d{2}-\d{2}', texto):
                return datetime.strptime(texto[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
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
    
    def _formatear_marca_retencion(self, marca: Optional[str]) -> str:
        """Formatear marca retención (0 o 1)"""
        if not marca:
            return ""
        return str(marca).strip()[:1]
    
    def _formatear_clasificacion_bienes(self, clasificacion: Optional[str]) -> str:
        """Formatear clasificación bienes y servicios (máximo 30 caracteres)"""
        if not clasificacion:
            return ""
        return str(clasificacion).strip()[:30]
    
    def _formatear_identificacion_contrato(self, identificacion: Optional[str]) -> str:
        """Formatear identificación del contrato (máximo 30 caracteres)"""
        if not identificacion:
            return ""
        return str(identificacion).strip()[:30]
    
    def _formatear_indicador_error(self, error: str) -> str:
        """Formatear indicador de error (0-4)"""
        if not error:
            return "0"
        return str(error).strip()[:1]
    
    def _formatear_medio_pago(self, medio: Optional[str]) -> str:
        """Formatear medio de pago (máximo 3 caracteres)"""
        if not medio:
            return ""
        return str(medio).strip()[:3]
    
    def formatear_multiple_compras(
        self,
        compras: List[RegistroCompraResponse],
        periodo_aaaamm: str
    ) -> List[PLELineaCompras]:
        """
        Formatear múltiples registros de compras
        
        Args:
            compras: Lista de registros de compra
            periodo_aaaamm: Período formato AAAAMM
            
        Returns:
            Lista de líneas PLE formateadas
        """
        lineas_ple = []
        
        for i, compra in enumerate(compras, 1):
            try:
                linea = self.formatear_registro_compra(
                    compra, 
                    periodo_aaaamm,
                    correlativo_asiento=f"{i:010d}"
                )
                lineas_ple.append(linea)
                
            except Exception as e:
                self.logger.error(f"Error formateando compra {compra.id}: {str(e)}")
                raise
        
        return lineas_ple
    
    def generar_contenido_archivo_ple(
        self,
        lineas_ple: List[PLELineaCompras]
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
        
        Formato: LE{RUC}{AAAAMM}00080000{CORRELATIVO}1.txt
        
        Args:
            empresa_ruc: RUC de la empresa
            periodo_aaaamm: Período AAAAMM
            correlativo: Correlativo del archivo
            
        Returns:
            Nombre del archivo
        """
        return f"LE{empresa_ruc}{periodo_aaaamm}00080000{correlativo.zfill(4)}1.txt"
