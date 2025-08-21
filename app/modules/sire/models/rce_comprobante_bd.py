"""
Modelo para comprobantes RCE en base de datos
Estructura optimizada para almacenar datos de SUNAT
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
from bson import ObjectId

class RceComprobanteBD(BaseModel):
    """Modelo para comprobantes RCE en base de datos"""
    
    # ID único
    id: Optional[str] = Field(None, alias="_id")
    
    # Datos de identificación
    ruc: str = Field(..., description="RUC del adquiriente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    
    # Datos del proveedor
    ruc_proveedor: str = Field(..., description="RUC del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    
    # Datos del comprobante
    tipo_documento: str = Field(..., description="Tipo de documento")
    serie_comprobante: str = Field(..., description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_emision: str = Field(..., description="Fecha de emisión YYYY-MM-DD")
    fecha_vencimiento: Optional[str] = Field(None, description="Fecha de vencimiento")
    
    # Montos (como Decimal para precisión)
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    base_imponible_gravada: Decimal = Field(..., description="Base imponible gravada")
    igv: Decimal = Field(..., description="IGV")
    valor_adquisicion_no_gravada: Decimal = Field(default=Decimal("0.00"), description="Valor adquisición no gravada")
    isc: Decimal = Field(default=Decimal("0.00"), description="ISC")
    icbper: Decimal = Field(default=Decimal("0.00"), description="ICBPER")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos")
    importe_total: Decimal = Field(..., description="Importe total")
    
    # Metadatos de control
    fecha_registro: datetime = Field(default_factory=datetime.utcnow, description="Fecha de registro en BD")
    fecha_actualizacion: Optional[datetime] = Field(None, description="Fecha de última actualización")
    origen: Literal["SUNAT", "MANUAL"] = Field(default="SUNAT", description="Origen del dato")
    estado: Literal["GUARDADO", "VALIDADO", "PROCESADO", "ERROR"] = Field(default="GUARDADO", description="Estado del comprobante")
    observaciones: Optional[str] = Field(None, description="Observaciones")
    
    # Datos adicionales de SUNAT
    car_sunat: Optional[str] = Field(None, description="CAR SUNAT")
    numero_dua: Optional[str] = Field(None, description="Número DUA")
    
    # Hash para detectar duplicados
    hash_comprobante: Optional[str] = Field(None, description="Hash único del comprobante")
    
    class Config:
        # Configuración para MongoDB
        validate_assignment = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            Decimal: float,
            datetime: lambda v: v.isoformat()
        }
        
    def dict(self, *args, **kwargs):
        """Override dict to convert Decimal to float"""
        data = super().dict(*args, **kwargs)
        # Convertir todos los Decimal a float
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data

class RceComprobanteBDCreate(BaseModel):
    """Modelo para crear comprobantes desde datos de SUNAT"""
    
    ruc: str
    periodo: str
    ruc_proveedor: str
    razon_social_proveedor: str
    tipo_documento: str
    serie_comprobante: str
    numero_comprobante: str
    fecha_emision: str
    fecha_vencimiento: Optional[str] = None
    moneda: str = "PEN"
    tipo_cambio: Optional[Decimal] = None
    base_imponible_gravada: Decimal
    igv: Decimal
    valor_adquisicion_no_gravada: Decimal = Decimal("0.00")
    isc: Decimal = Decimal("0.00")
    icbper: Decimal = Decimal("0.00")
    otros_tributos: Decimal = Decimal("0.00")
    importe_total: Decimal
    car_sunat: Optional[str] = None
    numero_dua: Optional[str] = None
    observaciones: Optional[str] = None
    
    def dict(self, *args, **kwargs):
        """Override dict to convert Decimal to float"""
        data = super().dict(*args, **kwargs)
        # Convertir todos los Decimal a float
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data

class RceComprobanteBDResponse(BaseModel):
    """Modelo de respuesta para comprobantes"""
    
    id: str
    ruc: str
    periodo: str
    ruc_proveedor: str
    razon_social_proveedor: str
    tipo_documento: str
    serie_comprobante: str
    numero_comprobante: str
    fecha_emision: str
    fecha_vencimiento: Optional[str]
    moneda: str
    tipo_cambio: Optional[float]
    base_imponible_gravada: float
    igv: float
    valor_adquisicion_no_gravada: float
    isc: float
    icbper: float
    otros_tributos: float
    importe_total: float
    fecha_registro: str
    fecha_actualizacion: Optional[str]
    origen: str
    estado: str
    observaciones: Optional[str]

class RceGuardarResponse(BaseModel):
    """Respuesta al guardar comprobantes"""
    
    exitoso: bool
    mensaje: str
    comprobantes_guardados: int = Field(0, alias="total_nuevos")
    comprobantes_actualizados: int = Field(0, alias="total_actualizados") 
    comprobantes_duplicados: int = Field(0, alias="total_duplicados")
    errores: int = Field(0, alias="total_errores")
    detalles: Optional[dict] = None
    
    class Config:
        allow_population_by_field_name = True

class RceEstadisticasBD(BaseModel):
    """Estadísticas de comprobantes en BD"""
    
    total_comprobantes: int
    total_importe: float
    total_igv: float
    total_base_imponible: float
    periodo_inicio: Optional[str] = None
    periodo_fin: Optional[str] = None
    comprobantes_por_periodo: dict
    proveedores_principales: list
    tipos_documento: dict
