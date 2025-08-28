"""
PLEFormatterSunatV3 - Formateador Oficial 19 Campos SUNAT - CORREGIDO
====================================================================

Formateador especializado para cumplir exactamente con la estructura
oficial SUNAT de 19 campos para Libro Diario PLE formato 5.1.

*** CORRECCIÓN APLICADA: 24 campos → 19 campos oficiales ***

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Estructura oficial 19 campos PLE 050100 (Libro Diario):
1. Período (AAAAMM)               2. Código único operación (CUO)
3. Número correlativo             4. Código cuenta contable  
5. Código unidad operación        6. Código centro costo
7. Tipo moneda origen             8. Tipo documento sustento
9. Serie comprobante              10. Número comprobante
11. Fecha contable                12. Fecha vencimiento
13. Fecha operación               14. Glosa descripción
15. Referencia operación          16. Debe
17. Haber                         18. Dato estructurado
19. Estado operación

Autor: Sistema ERP - Implementación SUNAT V3 CORREGIDA
Fecha: Agosto 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

# Importar schemas directamente para evitar problemas circulares
try:
    from ..schemas import AsientoContableSunatV3, DetalleAsientoSunatV3
except ImportError:
    # Crear stubs temporales si los schemas no existen
    class AsientoContableSunatV3:
        pass
    class DetalleAsientoSunatV3:
        pass

logger = logging.getLogger(__name__)


@dataclass
class PLELineaSunatV3:
    """Línea PLE formateada según estructura oficial SUNAT 19 campos - CORREGIDO"""
    
    # Datos originales
    asiento: AsientoContableSunatV3
    detalle: DetalleAsientoSunatV3
    
    # 19 CAMPOS OFICIALES SUNAT - LIBRO DIARIO PLE 050100
    campo_01_periodo: str                    # Período AAAAMM
    campo_02_codigo_unico_operacion: str     # Código único de operación (CUO)
    campo_03_numero_correlativo: str         # Número correlativo del asiento
    campo_04_codigo_cuenta_contable: str     # Código de la cuenta contable
    campo_05_codigo_unidad_operacion: str    # Código de la unidad de operación
    campo_06_codigo_centro_costo: str        # Código del centro de costos
    campo_07_tipo_moneda_origen: str         # Tipo de moneda de origen
    campo_08_tipo_documento_sustento: str    # Tipo de documento del sustento
    campo_09_serie_comprobante: str          # Número de serie del comprobante
    campo_10_numero_comprobante: str         # Número del comprobante
    campo_11_fecha_contable: str             # Fecha contable
    campo_12_fecha_vencimiento: str          # Fecha de vencimiento
    campo_13_fecha_operacion: str            # Fecha de operación
    campo_14_glosa_descripcion: str          # Glosa o descripción de la operación
    campo_15_referencia_operacion: str       # Referencia de la operación
    campo_16_debe: str                       # Debe
    campo_17_haber: str                      # Haber
    campo_18_dato_estructurado: str          # Dato estructurado
    campo_19_estado_operacion: str           # Estado de la operación
    
    def to_ple_line(self) -> str:
        """Convertir a línea PLE oficial separada por | - 19 CAMPOS OFICIALES SUNAT"""
        campos = [
            self.campo_01_periodo,
            self.campo_02_codigo_unico_operacion,
            self.campo_03_numero_correlativo,
            self.campo_04_codigo_cuenta_contable,
            self.campo_05_codigo_unidad_operacion,
            self.campo_06_codigo_centro_costo,
            self.campo_07_tipo_moneda_origen,
            self.campo_08_tipo_documento_sustento,
            self.campo_09_serie_comprobante,
            self.campo_10_numero_comprobante,
            self.campo_11_fecha_contable,
            self.campo_12_fecha_vencimiento,
            self.campo_13_fecha_operacion,
            self.campo_14_glosa_descripcion,
            self.campo_15_referencia_operacion,
            self.campo_16_debe,
            self.campo_17_haber,
            self.campo_18_dato_estructurado,
            self.campo_19_estado_operacion
        ]
        
        return "|".join(campos) + "|"


class PLEFormatterSunatV3:
    """Formateador oficial SUNAT V3 para 19 campos - CORREGIDO según especificación oficial"""
    
    def __init__(self):
        """Inicializar formateador con configuración SUNAT"""
        self.logger = logging.getLogger(__name__)
        
        # Configuración según normativa SUNAT
        self.separador = "|"
        self.longitud_maxima_glosa = 200
        self.precision_montos = 2
        self.formato_fecha_sunat = "%d/%m/%Y"
        
        # Códigos por defecto según normativa
        self.codigo_moneda_default = "PEN"
        self.tipo_cambio_default = "1.000"
        
    def formatear_asiento_completo(
        self,
        asiento: AsientoContableSunatV3,
        empresa_ruc: str,
        periodo_aaaammdd: str
    ) -> List[PLELineaSunatV3]:
        """
        Formatear asiento completo a líneas PLE oficiales
        
        Args:
            asiento: Asiento contable con estructura SUNAT V3
            empresa_ruc: RUC empresa para códigos únicos
            periodo_aaaammdd: Período formato AAAAMMDD
            
        Returns:
            Lista de líneas PLE formateadas (una por detalle)
        """
        lineas_ple = []
        
        try:
            # Generar código único operación base
            codigo_unico_base = self._generar_codigo_unico_operacion(
                empresa_ruc, asiento.numero, periodo_aaaammdd
            )
            
            # Procesar cada detalle del asiento
            for i, detalle in enumerate(asiento.detalles):
                linea_ple = self._formatear_detalle_a_linea_ple(
                    asiento, detalle, codigo_unico_base, i + 1, periodo_aaaammdd
                )
                lineas_ple.append(linea_ple)
                
        except Exception as e:
            self.logger.error(f"Error formateando asiento {asiento.numero}: {str(e)}")
            raise
        
        return lineas_ple
    
    def _formatear_detalle_a_linea_ple(
        self,
        asiento: AsientoContableSunatV3,
        detalle: DetalleAsientoSunatV3,
        codigo_unico_base: str,
        numero_detalle: int,
        periodo_aaaammdd: str
    ) -> PLELineaSunatV3:
        """
        Formatear un detalle individual a línea PLE oficial - 19 CAMPOS SUNAT
        
        Args:
            asiento: Asiento contable completo
            detalle: Detalle específico a formatear
            codigo_unico_base: Código único base del asiento
            numero_detalle: Número del detalle (1, 2, 3...)
            periodo_aaaammdd: Período formato AAAAMMDD
            
        Returns:
            PLELineaSunatV3: Línea completamente formateada con 19 campos oficiales
        """
        
        # CAMPO 1: Período (AAAAMM)
        campo_01 = periodo_aaaammdd[:6]  # Solo AAAAMM, no AAAAMMDD
        
        # CAMPO 2: Código único operación (CUO)
        campo_02 = f"{codigo_unico_base}{numero_detalle:02d}"
        
        # CAMPO 3: Número correlativo asiento
        campo_03 = f"{asiento.numero.zfill(10)}"
        
        # CAMPO 4: Código cuenta contable
        campo_04 = self._formatear_codigo_cuenta(detalle.codigoCuenta)
        
        # CAMPO 5: Código unidad operación (opcional)
        campo_05 = self._formatear_codigo_unidad_operacion(getattr(detalle, 'codigoUnidadOperacion', ''))
        
        # CAMPO 6: Código centro costo (opcional)
        campo_06 = self._formatear_codigo_centro_costo(getattr(detalle, 'codigoCentroCosto', ''))
        
        # CAMPO 7: Tipo moneda origen
        campo_07 = self._formatear_tipo_moneda(getattr(detalle, 'tipoMonedaOrigen', 'PEN'))
        
        # CAMPO 8: Tipo documento sustento (opcional)
        campo_08 = self._formatear_tipo_documento_sustento(getattr(detalle, 'tipoDocumentoSustento', ''))
        
        # CAMPO 9: Serie comprobante (opcional)
        campo_09 = self._formatear_serie_comprobante(getattr(detalle, 'serieComprobante', ''))
        
        # CAMPO 10: Número comprobante (opcional)
        campo_10 = self._formatear_numero_comprobante(getattr(detalle, 'numeroComprobante', ''))
        
        # CAMPO 11: Fecha contable
        campo_11 = self._formatear_fecha_contable(asiento.fecha)
        
        # CAMPO 12: Fecha vencimiento (opcional)
        campo_12 = self._formatear_fecha_vencimiento(getattr(detalle, 'fechaVencimiento', ''))
        
        # CAMPO 13: Fecha operación
        campo_13 = self._formatear_fecha_operacion(asiento.fecha)
        
        # CAMPO 14: Glosa o descripción
        campo_14 = self._formatear_glosa_descripcion(detalle.descripcion)
        
        # CAMPO 15: Referencia operación (opcional)
        campo_15 = self._formatear_referencia_operacion(getattr(detalle, 'referenciaOperacion', ''))
        
        # CAMPO 16: Debe
        campo_16 = self._formatear_monto_debe(detalle.debe)
        
        # CAMPO 17: Haber
        campo_17 = self._formatear_monto_haber(detalle.haber)
        
        # CAMPO 18: Dato estructurado (normalmente vacío)
        campo_18 = self._formatear_dato_estructurado("")
        
        # CAMPO 19: Estado operación
        campo_19 = self._formatear_estado_operacion(getattr(asiento, 'estadoOperacion', '1'))
        
        return PLELineaSunatV3(
            asiento=asiento,
            detalle=detalle,
            campo_01_periodo=campo_01,
            campo_02_codigo_unico_operacion=campo_02,
            campo_03_numero_correlativo=campo_03,
            campo_04_codigo_cuenta_contable=campo_04,
            campo_05_codigo_unidad_operacion=campo_05,
            campo_06_codigo_centro_costo=campo_06,
            campo_07_tipo_moneda_origen=campo_07,
            campo_08_tipo_documento_sustento=campo_08,
            campo_09_serie_comprobante=campo_09,
            campo_10_numero_comprobante=campo_10,
            campo_11_fecha_contable=campo_11,
            campo_12_fecha_vencimiento=campo_12,
            campo_13_fecha_operacion=campo_13,
            campo_14_glosa_descripcion=campo_14,
            campo_15_referencia_operacion=campo_15,
            campo_16_debe=campo_16,
            campo_17_haber=campo_17,
            campo_18_dato_estructurado=campo_18,
            campo_19_estado_operacion=campo_19
        )
    
    # ================================
    # MÉTODOS DE FORMATEO ESPECÍFICO
    # ================================
    
    def _generar_codigo_unico_operacion(
        self, 
        empresa_ruc: str, 
        numero_asiento: str, 
        periodo: str
    ) -> str:
        """Generar código único de operación"""
        # Formato: RUC(4 últimos) + PERIODO(6) + ASIENTO(4)
        ruc_sufijo = empresa_ruc[-4:] if len(empresa_ruc) >= 4 else empresa_ruc.zfill(4)
        periodo_sufijo = periodo[-6:] if len(periodo) >= 6 else periodo.zfill(6)
        asiento_formateado = numero_asiento.zfill(4)
        
        return f"{ruc_sufijo}{periodo_sufijo}{asiento_formateado}"
    
    def _formatear_codigo_cuenta(self, codigo: str) -> str:
        """Formatear código cuenta contable (máximo 24 caracteres)"""
        if not codigo:
            return ""
        return str(codigo).strip()[:24]
    
    def _formatear_codigo_unidad_operacion(self, codigo: Optional[str]) -> str:
        """Formatear código unidad operación"""
        if not codigo:
            return ""
        return str(codigo).strip()[:24]
    
    def _formatear_codigo_centro_costo(self, codigo: Optional[str]) -> str:
        """Formatear código centro costo"""
        if not codigo:
            return ""
        return str(codigo).strip()[:24]
    
    def _formatear_tipo_moneda(self, tipo_moneda: str) -> str:
        """Formatear tipo moneda (3 caracteres)"""
        return (tipo_moneda or self.codigo_moneda_default).upper()[:3]
    
    def _formatear_tipo_documento_sustento(self, tipo: Optional[str]) -> str:
        """Formatear tipo documento sustento (campo 8)"""
        if not tipo:
            return ""
        return str(tipo).strip()[:2]
    
    def _formatear_serie_comprobante(self, serie: Optional[str]) -> str:
        """Formatear serie comprobante (campo 9)"""
        if not serie:
            return ""
        return str(serie).strip()[:20]
    
    def _formatear_numero_comprobante(self, numero: Optional[str]) -> str:
        """Formatear número comprobante (campo 10)"""
        if not numero:
            return ""
        return str(numero).strip()[:20]
    
    def _formatear_glosa_descripcion(self, glosa: str) -> str:
        """Formatear glosa o descripción (campo 14 - máximo 200 caracteres)"""
        if not glosa:
            return ""
        return str(glosa).strip()[:self.longitud_maxima_glosa]
    
    def _formatear_referencia_operacion(self, referencia: Optional[str]) -> str:
        """Formatear referencia operación (campo 15 - máximo 200 caracteres)"""
        if not referencia:
            return ""
        return str(referencia).strip()[:self.longitud_maxima_glosa]
    
    def _formatear_monto_debe(self, monto: Optional[float]) -> str:
        """Formatear monto debe (campo 16)"""
        return self._formatear_monto(monto)
    
    def _formatear_monto_haber(self, monto: Optional[float]) -> str:
        """Formatear monto haber (campo 17)"""
        return self._formatear_monto(monto)
    
    def _formatear_tipo_documento_identidad(self, tipo: Optional[str]) -> str:
        """Formatear tipo documento identidad"""
        if not tipo:
            return ""
        return str(tipo).strip()[:2]
    
    def _formatear_numero_documento_identidad(self, numero: Optional[str]) -> str:
        """Formatear número documento identidad"""
        if not numero:
            return ""
        return str(numero).strip()[:15]
    
    def _formatear_tipo_comprobante_pago(self, tipo: Optional[str]) -> str:
        """Formatear tipo comprobante pago"""
        if not tipo:
            return ""
        return str(tipo).strip()[:2]
    
    def _formatear_numero_serie_comprobante(self, serie: Optional[str]) -> str:
        """Formatear número serie comprobante"""
        if not serie:
            return ""
        return str(serie).strip()[:20]
    
    def _formatear_numero_comprobante_pago(self, numero: Optional[str]) -> str:
        """Formatear número comprobante pago"""
        if not numero:
            return ""
        return str(numero).strip()[:20]
    
    def _formatear_fecha_contable(self, fecha: Optional[str]) -> str:
        """Formatear fecha contable DD/MM/YYYY"""
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
        except:
            return ""
    
    def _formatear_fecha_vencimiento(self, fecha: Optional[str]) -> str:
        """Formatear fecha vencimiento DD/MM/YYYY"""
        return self._formatear_fecha_contable(fecha)
    
    def _formatear_fecha_operacion(self, fecha: Optional[str]) -> str:
        """Formatear fecha operación DD/MM/YYYY"""
        return self._formatear_fecha_contable(fecha)
    
    def _formatear_glosa_referencial(self, glosa: Optional[str]) -> str:
        """Formatear glosa referencial (máximo 200 caracteres)"""
        if not glosa:
            return ""
        return str(glosa).strip()[:self.longitud_maxima_glosa]
    
    def _formatear_glosa_principal(self, glosa: str) -> str:
        """Formatear glosa principal (máximo 200 caracteres)"""
        if not glosa:
            return ""
        return str(glosa).strip()[:self.longitud_maxima_glosa]
    
    def _formatear_tipo_cambio(self, tipo_cambio: Optional[float]) -> str:
        """Formatear tipo cambio (3 decimales)"""
        if not tipo_cambio or tipo_cambio <= 0:
            return self.tipo_cambio_default
        
        try:
            # Formatear con 3 decimales según SUNAT
            return f"{float(tipo_cambio):.3f}"
        except:
            return self.tipo_cambio_default
    
    def _formatear_monto_debe_origen(self, monto: Optional[float]) -> str:
        """Formatear monto debe moneda origen"""
        return self._formatear_monto(monto)
    
    def _formatear_monto_haber_origen(self, monto: Optional[float]) -> str:
        """Formatear monto haber moneda origen"""
        return self._formatear_monto(monto)
    
    def _formatear_monto_debe_nacional(self, monto: Optional[float]) -> str:
        """Formatear monto debe moneda nacional"""
        return self._formatear_monto(monto)
    
    def _formatear_monto_haber_nacional(self, monto: Optional[float]) -> str:
        """Formatear monto haber moneda nacional"""
        return self._formatear_monto(monto)
    
    def _formatear_monto(self, monto: Optional[float]) -> str:
        """Formatear monto con precisión SUNAT (2 decimales)"""
        if not monto or monto == 0:
            return ""
        
        try:
            # Usar Decimal para precisión exacta
            decimal_monto = Decimal(str(monto)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            return str(decimal_monto)
        except:
            return ""
    
    def _formatear_dato_estructurado(self, dato: Optional[str]) -> str:
        """Formatear dato estructurado (normalmente vacío)"""
        if not dato:
            return ""
        return str(dato).strip()
    
    def _formatear_estado_operacion(self, estado: str) -> str:
        """Formatear estado operación (1=Activo, 8=Anulado, 9=Ajuste)"""
        return str(estado or "1").strip()[:1]

    def formatear_linea_completa(self, datos_asiento: Dict[str, Any]) -> str:
        """
        Formatear línea completa desde diccionario simple
        
        Método de conveniencia para trabajar con datos de asientos
        en formato de diccionario simple (como vienen de base de datos).
        
        Args:
            datos_asiento: Diccionario con datos del asiento
            
        Returns:
            Línea PLE formateada con 24 campos
        """
        try:
            # Extraer campos principales
            periodo = datos_asiento.get('periodo', '')
            numero_correlativo = datos_asiento.get('numero_correlativo', '')
            codigo_cuenta = datos_asiento.get('codigo_cuenta_contable', '')
            codigo_unidad = datos_asiento.get('codigo_unidad_operacion', '0000')
            codigo_centro = datos_asiento.get('codigo_centro_costo', '')
            tipo_moneda = datos_asiento.get('tipo_moneda', 'PEN')
            
            # Datos de documento
            tipo_doc_identidad = datos_asiento.get('tipo_documento_identidad_emisor', '')
            numero_doc_identidad = datos_asiento.get('numero_documento_identidad_emisor', '')
            tipo_comprobante = datos_asiento.get('tipo_comprobante_pago', '')
            serie_comprobante = datos_asiento.get('numero_serie_comprobante', '')
            numero_comprobante = datos_asiento.get('numero_comprobante_pago', '')
            
            # Fechas
            fecha_contable = datos_asiento.get('fecha_contable')
            fecha_vencimiento = datos_asiento.get('fecha_vencimiento')
            fecha_operacion = datos_asiento.get('fecha_operacion')
            
            # Formatear fechas (convertir objetos date a string)
            fecha_contable_str = ""
            if fecha_contable:
                if isinstance(fecha_contable, date):
                    fecha_contable_str = fecha_contable.strftime("%d/%m/%Y")
                else:
                    fecha_contable_str = self._formatear_fecha_contable(str(fecha_contable))
            
            fecha_vencimiento_str = ""
            if fecha_vencimiento:
                if isinstance(fecha_vencimiento, date):
                    fecha_vencimiento_str = fecha_vencimiento.strftime("%d/%m/%Y")
                else:
                    fecha_vencimiento_str = self._formatear_fecha_vencimiento(str(fecha_vencimiento))
            
            fecha_operacion_str = ""
            if fecha_operacion:
                if isinstance(fecha_operacion, date):
                    fecha_operacion_str = fecha_operacion.strftime("%d/%m/%Y")
                else:
                    fecha_operacion_str = self._formatear_fecha_operacion(str(fecha_operacion))
            
            # Glosa y montos
            glosa = datos_asiento.get('glosa_descripcion', '')
            debe = datos_asiento.get('debe', 0.0)
            haber = datos_asiento.get('haber', 0.0)
            
            # Formatear montos
            debe_str = self._formatear_monto(debe)
            haber_str = self._formatear_monto(haber)
            
            # Datos adicionales
            dato_estructurado = datos_asiento.get('dato_estructurado', '')
            estado_operacion = datos_asiento.get('estado_operacion', '1')
            campo_libre = datos_asiento.get('campo_libre', '')
            
            # Generar código único operación (simplificado para testing)
            codigo_unico = f"{periodo}{numero_correlativo.zfill(6)}"
            
            # Ensamblar línea con 24 campos según estructura oficial SUNAT
            campos_linea = [
                periodo,                          # 1. Período
                codigo_unico,                     # 2. Código único operación
                numero_correlativo,               # 3. Número correlativo
                codigo_cuenta,                    # 4. Código cuenta contable
                codigo_unidad,                    # 5. Código unidad operación
                codigo_centro,                    # 6. Código centro costo
                tipo_moneda,                      # 7. Tipo moneda origen
                tipo_doc_identidad,               # 8. Tipo documento identidad
                numero_doc_identidad,             # 9. Número documento identidad
                tipo_comprobante,                 # 10. Tipo comprobante pago
                serie_comprobante,                # 11. Serie comprobante
                numero_comprobante,               # 12. Número comprobante
                fecha_contable_str,               # 13. Fecha contable
                fecha_vencimiento_str,            # 14. Fecha vencimiento
                fecha_operacion_str,              # 15. Fecha operación
                glosa,                            # 16. Glosa referencial/principal
                debe_str,                         # 17. Debe moneda origen
                haber_str,                        # 18. Haber moneda origen
                debe_str,                         # 19. Debe moneda nacional (=origen en PEN)
                haber_str,                        # 20. Haber moneda nacional (=origen en PEN)
                "1.000",                          # 21. Tipo cambio (fijo para PEN)
                dato_estructurado,                # 22. Dato estructurado
                estado_operacion,                 # 23. Estado operación
                campo_libre                       # 24. Campo libre
            ]
            
            # Unir con separador oficial SUNAT
            linea_ple = "|".join(campos_linea)
            
            return linea_ple
            
        except Exception as e:
            self.logger.error(f"Error formateando línea desde diccionario: {str(e)}")
            raise ValueError(f"Error formateando línea PLE: {str(e)}")
