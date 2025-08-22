"""
Modelo para comprobantes RVIE (Ventas) en base de datos
Estructura optimizada para almacenar datos de SUNAT RVIE
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
from bson import ObjectId

class RvieComprobanteBD(BaseModel):
    """Modelo para comprobantes RVIE (Ventas) en base de datos"""
    
    # ID único
    id: Optional[str] = Field(None, alias="_id")
    
    # Datos de identificación
    ruc: str = Field(..., description="RUC del emisor/vendedor")
    periodo: str = Field(..., description="Periodo YYYYMM")
    
    # Datos del comprobante
    tipo_documento: str = Field(..., description="Código tipo de documento (01=Factura, 03=Boleta, etc.)")
    tipo_documento_desc: Optional[str] = Field(None, description="Descripción del tipo de documento")
    serie_comprobante: str = Field(..., description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_emision: str = Field(..., description="Fecha de emisión YYYY-MM-DD")
    
    # Datos del cliente/receptor
    cliente_nombre: str = Field(..., description="Nombre/Razón social del cliente")
    cliente_tipo_documento: Optional[str] = Field(None, description="Tipo de documento del cliente")
    cliente_numero_documento: Optional[str] = Field(None, description="Número de documento del cliente")
    cliente_ruc: Optional[str] = Field(None, description="RUC del cliente (si aplica)")
    
    # Montos (como Decimal para precisión)
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    base_gravada: Decimal = Field(default=Decimal("0.00"), description="Base imponible gravada")
    igv: Decimal = Field(default=Decimal("0.00"), description="IGV")
    exonerado: Decimal = Field(default=Decimal("0.00"), description="Monto exonerado")
    inafecto: Decimal = Field(default=Decimal("0.00"), description="Monto inafecto")
    total: Decimal = Field(..., description="Monto total del comprobante")
    
    # Estado y tipo de operación
    estado: str = Field(..., description="Estado del comprobante (ACTIVO, ANULADO, etc.)")
    tipo_operacion: Optional[str] = Field(None, description="Código tipo de operación")
    
    # Metadatos de control
    fecha_registro: datetime = Field(default_factory=datetime.utcnow, description="Fecha de registro en BD")
    fecha_actualizacion: Optional[datetime] = Field(None, description="Fecha de última actualización")
    origen: Literal["SUNAT", "MANUAL"] = Field(default="SUNAT", description="Origen del dato")
    estado_registro: Literal["GUARDADO", "VALIDADO", "PROCESADO", "ERROR"] = Field(default="GUARDADO", description="Estado del registro")
    observaciones: Optional[str] = Field(None, description="Observaciones")
    
    # Datos adicionales de SUNAT
    car_sunat: Optional[str] = Field(None, description="CAR SUNAT")
    ticket_sunat: Optional[str] = Field(None, description="Ticket SUNAT")
    
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

class RvieComprobanteBDCreate(BaseModel):
    """Modelo para crear comprobantes RVIE desde datos de SUNAT"""
    
    ruc: str
    periodo: str
    tipo_documento: str
    tipo_documento_desc: Optional[str] = None
    serie_comprobante: str
    numero_comprobante: str
    fecha_emision: str
    cliente_nombre: str
    cliente_tipo_documento: Optional[str] = None
    cliente_numero_documento: Optional[str] = None
    cliente_ruc: Optional[str] = None
    moneda: str = "PEN"
    tipo_cambio: Optional[Decimal] = None
    base_gravada: Decimal = Decimal("0.00")
    igv: Decimal = Decimal("0.00")
    exonerado: Decimal = Decimal("0.00")
    inafecto: Decimal = Decimal("0.00")
    total: Decimal
    estado: str
    tipo_operacion: Optional[str] = None
    car_sunat: Optional[str] = None
    ticket_sunat: Optional[str] = None

class RvieComprobanteBDUpdate(BaseModel):
    """Modelo para actualizar comprobantes RVIE"""
    
    cliente_nombre: Optional[str] = None
    cliente_tipo_documento: Optional[str] = None
    cliente_numero_documento: Optional[str] = None
    cliente_ruc: Optional[str] = None
    base_gravada: Optional[Decimal] = None
    igv: Optional[Decimal] = None
    exonerado: Optional[Decimal] = None
    inafecto: Optional[Decimal] = None
    total: Optional[Decimal] = None
    estado: Optional[str] = None
    tipo_operacion: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)

class RvieComprobanteBDResponse(BaseModel):
    """Modelo de respuesta para comprobantes RVIE"""
    
    id: str
    ruc: str
    periodo: str
    tipo_documento: str
    tipo_documento_desc: Optional[str]
    serie_comprobante: str
    numero_comprobante: str
    fecha_emision: str
    cliente_nombre: str
    cliente_tipo_documento: Optional[str]
    cliente_numero_documento: Optional[str]
    cliente_ruc: Optional[str]
    moneda: str
    tipo_cambio: Optional[float]
    base_gravada: float
    igv: float
    exonerado: float
    inafecto: float
    total: float
    estado: str
    tipo_operacion: Optional[str]
    fecha_registro: str
    fecha_actualizacion: Optional[str]
    origen: str
    estado_registro: str
    observaciones: Optional[str]

class RvieEstadisticas(BaseModel):
    """Estadísticas de comprobantes RVIE"""
    
    total_comprobantes: int
    total_monto: float
    por_tipo: dict
    por_estado: dict
    por_mes: dict
    resumen_montos: dict
