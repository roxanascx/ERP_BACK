"""
Esquemas Pydantic para el Registro de Compras (PLE 080000).

El PLE 080000 pide 33 campos por comprobante. Los que describen el
comprobante y sus importes principales viven en cada clase; los otros trece
—detracción, retención, destinos mixtos, medio de pago…— están en
`CamposPLECompras`, que todas heredan, para no repetirlos cinco veces y que
no se vuelvan a desincronizar.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from enum import Enum


# Enums para valores específicos
class TipoComprobanteCompra(str, Enum):
    """Tipos de comprobante de compra válidos."""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_SERVICIOS = "12"
    DOCUMENTO_EXTERIOR = "91"


class TipoDocumentoIdentidad(str, Enum):
    """Tipos de documento de identidad."""
    DNI = "1"
    EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "A"


class EstadoOperacion(str, Enum):
    """Estados de operación."""
    VIGENTE = "1"
    ANULADO = "2"
    MODIFICADO = "9"


class CamposPLECompras(BaseModel):
    """
    Los campos del PLE 080000 que no son el comprobante ni sus importes base.

    Todos tienen valor por defecto porque en una compra corriente van vacíos o
    en cero; solo se llenan en los casos que los piden (una importación, una
    detracción, una compra destinada a operaciones mixtas).
    """

    # Campo 8. Solo en importaciones: el año de la DUA/DSI.
    anio_emision_dua_dsi: Optional[str] = Field(
        None, max_length=4, description="Año de emisión de la DUA o DSI"
    )
    # Campo 10. Para comprobantes emitidos por rango.
    numero_final_rango: Optional[str] = Field(None, max_length=20)

    # Campos 16-19. Adquisiciones gravadas según a qué operación se destinan.
    # No son un desglose del campo 14: son columnas distintas del PLE, y por
    # eso no se suman ni se derivan de la base gravada.
    base_imponible_gravada_operaciones_mixtas: Decimal = Field(
        default=Decimal("0.00"), ge=0,
        description="Base gravada destinada a operaciones gravadas y no gravadas",
    )
    igv_operaciones_mixtas: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible_gravada_exportacion: Decimal = Field(
        default=Decimal("0.00"), ge=0,
        description="Base gravada destinada a operaciones de exportación",
    )
    igv_exportacion: Decimal = Field(default=Decimal("0.00"), ge=0)

    # Campo 20. SUNAT lo pide como **un solo número**, y así lo entrega el
    # RCE. Las bases exonerada e inafecta son el desglose interno; si este
    # campo no viene, se calcula sumándolas para que el PLE nunca declare
    # cero teniendo importes cargados.
    base_imponible_no_gravada: Decimal = Field(
        default=Decimal("0.00"), ge=0,
        description="Valor de las adquisiciones no gravadas (campo 20 del PLE)",
    )

    # Campos 26-28. Detracción y retención.
    fecha_emision_detraccion: Optional[date] = None
    numero_constancia_detraccion: Optional[str] = Field(None, max_length=23)
    marca_comprobante_retencion: Optional[str] = Field(None, max_length=1)

    # Campos 30-32.
    identificacion_contrato: Optional[str] = Field(None, max_length=25)
    indicador_error: str = Field(default="0", max_length=1)
    medio_pago: Optional[str] = Field(None, max_length=3)

    @model_validator(mode="after")
    def completar_no_gravada(self) -> "CamposPLECompras":
        """
        Si nadie puso el campo 20, sumarlo del desglose.

        Sin esto, un comprobante cargado con base exonerada saldría en el PLE
        con adquisiciones no gravadas en cero: el archivo cuadra consigo mismo
        pero declara de menos.
        """
        if not self.base_imponible_no_gravada:
            exonerada = getattr(self, "base_imponible_exonerada", None) or Decimal("0.00")
            inafecta = getattr(self, "base_imponible_inafecta", None) or Decimal("0.00")
            suma = Decimal(exonerada) + Decimal(inafecta)
            if suma:
                self.base_imponible_no_gravada = suma
        return self


class CamposPLEComprasOpcionales(BaseModel):
    """
    Lo mismo para las actualizaciones parciales.

    Aquí todo es `None` por defecto y no hay validador: en un PATCH, un campo
    ausente significa «no lo toques», no «ponlo en cero».
    """

    anio_emision_dua_dsi: Optional[str] = None
    numero_final_rango: Optional[str] = None
    base_imponible_gravada_operaciones_mixtas: Optional[Decimal] = None
    igv_operaciones_mixtas: Optional[Decimal] = None
    base_imponible_gravada_exportacion: Optional[Decimal] = None
    igv_exportacion: Optional[Decimal] = None
    base_imponible_no_gravada: Optional[Decimal] = None
    fecha_emision_detraccion: Optional[date] = None
    numero_constancia_detraccion: Optional[str] = None
    marca_comprobante_retencion: Optional[str] = None
    identificacion_contrato: Optional[str] = None
    indicador_error: Optional[str] = None
    medio_pago: Optional[str] = None


class RegistroCompra(CamposPLECompras):
    """Schema base para registro de compras."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = Field(None, description="ID único del registro")
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0, description="Base imponible exonerada")
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0, description="Base imponible inafecta")
    isc: Decimal = Field(default=Decimal("0.00"), ge=0, description="ISC")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0, description="Otros tributos")
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0, description="Tipo de cambio")
    fecha_emision_documento_modificado: Optional[date] = Field(None, description="Fecha de emisión del documento modificado")
    tipo_comprobante_modificado: Optional[str] = Field(None, description="Tipo de comprobante modificado")
    serie_comprobante_modificado: Optional[str] = Field(None, description="Serie del comprobante modificado")
    numero_comprobante_modificado: Optional[str] = Field(None, description="Número del comprobante modificado")
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")
    created_at: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")


class RegistroCompraRequest(CamposPLECompras):
    """Schema para request de registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0)
    isc: Decimal = Field(default=Decimal("0.00"), ge=0)
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0)
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0)
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")


class RegistroCompraCreate(CamposPLECompras):
    """Schema para crear un nuevo registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0)
    isc: Decimal = Field(default=Decimal("0.00"), ge=0)
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0)
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0)
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")


class RegistroCompraUpdate(CamposPLEComprasOpcionales):
    """Schema para actualizar un registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    fecha_comprobante: Optional[date] = None
    tipo_comprobante: Optional[str] = None
    serie_comprobante: Optional[str] = None
    numero_comprobante: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    tipo_documento_proveedor: Optional[str] = None
    numero_documento_proveedor: Optional[str] = None
    razon_social_proveedor: Optional[str] = None
    base_imponible_gravada: Optional[Decimal] = None
    igv: Optional[Decimal] = None
    base_imponible_exonerada: Optional[Decimal] = None
    base_imponible_inafecta: Optional[Decimal] = None
    isc: Optional[Decimal] = None
    otros_tributos: Optional[Decimal] = None
    importe_total: Optional[Decimal] = None
    moneda: Optional[str] = None
    tipo_cambio: Optional[Decimal] = None
    clasificacion_bienes_servicios: Optional[str] = None
    estado_operacion: Optional[str] = None


class RegistroCompraResponse(CamposPLECompras):
    """Schema para respuesta de registro de compras."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    empresa_id: str
    periodo: str
    fecha_comprobante: date
    tipo_comprobante: str
    serie_comprobante: Optional[str] = None
    numero_comprobante: str
    fecha_vencimiento: Optional[date] = None
    tipo_documento_proveedor: str
    numero_documento_proveedor: str
    razon_social_proveedor: str
    base_imponible_gravada: Decimal
    igv: Decimal
    base_imponible_exonerada: Optional[Decimal] = Decimal('0.00')
    base_imponible_inafecta: Optional[Decimal] = Decimal('0.00')
    isc: Optional[Decimal] = Decimal('0.00')
    otros_tributos: Optional[Decimal] = Decimal('0.00')
    importe_total: Decimal
    moneda: Optional[str] = "PEN"
    tipo_cambio: Optional[Decimal] = Decimal('1.00')
    clasificacion_bienes_servicios: Optional[str] = "1"
    estado_operacion: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RegistroCompraFilter(BaseModel):
    """Schema para filtros de búsqueda."""
    model_config = ConfigDict()
    
    periodo: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    tipo_comprobante: Optional[str] = None
    numero_documento_proveedor: Optional[str] = None
    razon_social_proveedor: Optional[str] = None
    monto_minimo: Optional[Decimal] = None
    monto_maximo: Optional[Decimal] = None


class PLEComprasMetadata(BaseModel):
    """Schema para metadatos de archivo PLE."""
    model_config = ConfigDict()
    
    empresa_id: str
    periodo: str
    total_registros: int
    fecha_generacion: datetime
    version_formato: str = "27.0"


class RegistroCompraResumen(BaseModel):
    """
    Totales de un periodo, para las tarjetas de la pantalla.

    Los importes van como `float` y no como `Decimal` porque FastAPI
    serializa los Decimal **como texto**: el front recibia "10.81" en vez de
    10.81 y las sumas del navegador daban cualquier cosa. Aqui no hace falta
    la precision del Decimal, son cifras para mirar.
    """
    model_config = ConfigDict()

    total_registros: int
    total_base_imponible: float
    total_igv: float
    total_importe: float


class ValidationResult(BaseModel):
    """Schema para resultado de validación."""
    model_config = ConfigDict()
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class PLEFileInfo(BaseModel):
    """Schema para información de archivo PLE."""
    model_config = ConfigDict()
    
    nombre: str
    tamaño: int
    fecha_creacion: datetime
    hash_md5: str
    ruta_archivo: str


class PLEComprasExportOptions(BaseModel):
    """
    Qué exportar al PLE 080000.

    Le faltaban `empresa_id`, el rango de periodos y el correlativo, que son
    justo los que `generar_ple_compras` lee. Sin ellos el servicio reventaba
    con AttributeError antes de mirar un solo comprobante.
    """
    model_config = ConfigDict()

    empresa_id: str = Field(..., description="RUC o identificador de la empresa")
    periodo_inicio: str = Field(..., min_length=6, max_length=6, description="AAAAMM")
    periodo_fin: str = Field(..., min_length=6, max_length=6, description="AAAAMM")
    #: Va en el nombre del archivo. SUNAT lo usa para distinguir reenvíos.
    correlativo_archivo: str = Field(default="0001", max_length=4)

    # --- Filtros opcionales ---
    tipo_comprobante: Optional[TipoComprobanteCompra] = None
    tipo_documento_proveedor: Optional[TipoDocumentoIdentidad] = None
    estado_operacion: Optional[EstadoOperacion] = None
    incluir_anulados: bool = False
    solo_errores: bool = False

    formato: str = "txt"
    incluir_cabecera: bool = True
    separador: str = "|"
    codificacion: str = "utf-8"


class PLEComprasExportResult(BaseModel):
    """
    Resultado de generar el PLE 080000.

    Lleva el contenido del archivo y, sobre todo, **cuántos comprobantes se
    quedaron fuera y por qué**: el servicio formatea uno a uno y captura el
    error de cada uno, así que sin estos contadores un archivo vacío parece
    una exportación correcta.
    """
    model_config = ConfigDict()

    nombre_archivo: str
    contenido_archivo: str
    tamaño_archivo: int
    total_registros: int
    registros_exportados: int
    registros_excluidos: int
    registros_con_errores: int
    fecha_generacion: datetime
    periodo_procesado: str
    empresa_id: str
    resumen_montos: Dict[str, Any] = {}
    errores_encontrados: List[str] = []
    warnings: List[str] = []
