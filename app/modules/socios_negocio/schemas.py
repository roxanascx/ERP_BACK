from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# ESQUEMAS DE REQUEST (INPUT)
# ==========================================

class SocioNegocioCreate(BaseModel):
    """Esquema para crear un nuevo socio de negocio"""
    tipo_documento: str = Field(..., description="RUC, DNI, CE")
    numero_documento: str = Field(..., description="Número del documento")
    razon_social: str = Field(..., description="Razón social/Nombre")
    nombre_comercial: Optional[str] = Field(None)
    tipo_socio: str = Field(..., description="proveedor, cliente, ambos")
    categoria: Optional[str] = Field(None)
    
    # Ubicación
    direccion: Optional[str] = Field(None)
    ubigeo: Optional[str] = Field(None)
    departamento: Optional[str] = Field(None)
    provincia: Optional[str] = Field(None)
    distrito: Optional[str] = Field(None)
    
    # Contacto
    telefono: Optional[str] = Field(None)
    celular: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    contacto_principal: Optional[str] = Field(None)
    
    # Financiero
    moneda_preferida: str = Field("PEN")
    condicion_pago: Optional[str] = Field(None)
    limite_credito: Optional[float] = Field(None)
    
    # Observaciones
    observaciones: Optional[str] = Field(None)
    activo: bool = Field(True)

class SocioNegocioUpdate(BaseModel):
    """Esquema para actualizar un socio de negocio"""
    razon_social: Optional[str] = Field(None)
    nombre_comercial: Optional[str] = Field(None)
    tipo_socio: Optional[str] = Field(None)
    categoria: Optional[str] = Field(None)
    
    # Ubicación
    direccion: Optional[str] = Field(None)
    ubigeo: Optional[str] = Field(None)
    departamento: Optional[str] = Field(None)
    provincia: Optional[str] = Field(None)
    distrito: Optional[str] = Field(None)
    
    # Contacto
    telefono: Optional[str] = Field(None)
    celular: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    contacto_principal: Optional[str] = Field(None)
    
    # Financiero
    moneda_preferida: Optional[str] = Field(None)
    condicion_pago: Optional[str] = Field(None)
    limite_credito: Optional[float] = Field(None)
    
    # Estado
    activo: Optional[bool] = Field(None)
    observaciones: Optional[str] = Field(None)

class SocioSearchRequest(BaseModel):
    """Esquema para búsqueda de socios"""
    query: Optional[str] = Field(None, description="Texto a buscar")
    tipo_socio: Optional[str] = Field(None, description="Filtrar por tipo")
    categoria: Optional[str] = Field(None, description="Filtrar por categoría")
    activo: Optional[bool] = Field(None, description="Filtrar por estado")
    limit: int = Field(20, description="Límite de resultados", ge=1, le=100)
    offset: int = Field(0, description="Offset para paginación", ge=0)

# ==========================================
# ESQUEMAS DE RESPONSE (OUTPUT)
# ==========================================

class SocioNegocioResponse(BaseModel):
    """Esquema de respuesta para socio de negocio"""
    id: str
    tipo_documento: str
    numero_documento: str
    razon_social: str
    nombre_comercial: Optional[str] = None
    tipo_socio: str
    categoria: Optional[str] = None
    
    # Datos SUNAT
    estado_sunat: Optional[str] = None
    condicion_sunat: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    fecha_inscripcion: Optional[date] = None
    actividad_economica: Optional[str] = None
    
    # Ubicación
    direccion: Optional[str] = None
    ubigeo: Optional[str] = None
    departamento: Optional[str] = None
    provincia: Optional[str] = None
    distrito: Optional[str] = None
    
    # Contacto
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    contacto_principal: Optional[str] = None
    
    # Financiero
    moneda_preferida: str
    condicion_pago: Optional[str] = None
    limite_credito: Optional[float] = None
    
    # Estado y metadatos
    activo: bool
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    ultimo_sync_sunat: Optional[datetime] = None
    datos_sunat_disponibles: bool

class ConsultaRucRequest(BaseModel):
    """Esquema para solicitud de consulta RUC"""
    ruc: str = Field(..., pattern=r'^\d{11}$', description="RUC de 11 dígitos")

class ConsultaDniRequest(BaseModel):
    """Esquema para solicitud de consulta DNI"""
    dni: str = Field(..., pattern=r'^\d{8}$', description="DNI de 8 dígitos")

class ConsultaRucResponse(BaseModel):
    """Esquema de respuesta para consulta RUC"""
    success: bool
    ruc: str
    data: Optional['DatosSunatResponse'] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metodo: Optional[str] = Field(None, description="Método utilizado para la consulta")

class ConsultaDniResponse(BaseModel):
    """Esquema de respuesta para consulta DNI"""
    success: bool
    dni: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metodo: Optional[str] = Field(None, description="Método utilizado para la consulta")

class SocioCreateFromRucRequest(BaseModel):
    """Esquema para crear socio desde consulta RUC"""
    empresa_id: str = Field(..., description="ID de la empresa")
    ruc: str = Field(..., pattern=r'^\d{11}$', description="RUC de 11 dígitos")
    tipo_socio: str = Field(..., pattern=r'^(proveedor|cliente|ambos)$', description="Tipo de socio")

class DatosSunatResponse(BaseModel):
    """Datos obtenidos de SUNAT"""
    ruc: str
    razon_social: str
    nombre_comercial: str
    tipo_contribuyente: str
    estado_contribuyente: str
    condicion_contribuyente: str
    domicilio_fiscal: str
    actividad_economica: str
    fecha_inscripcion: str
    ubigeo: Optional[str] = None

class SocioListResponse(BaseModel):
    """Esquema de respuesta para lista de socios"""
    socios: List[SocioNegocioResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class SocioStatsResponse(BaseModel):
    """Esquema de respuesta para estadísticas"""
    total_socios: int
    total_proveedores: int
    total_clientes: int
    total_ambos: int
    total_activos: int
    total_inactivos: int
    total_con_ruc: int
    total_sincronizados_sunat: int

class OperationResponse(BaseModel):
    """Respuesta genérica para operaciones"""
    success: bool
    message: str
    data: Optional[dict] = None

# ==========================================
# ESQUEMAS AUXILIARES
# ==========================================

class CategoriaResponse(BaseModel):
    """Esquema para categorías de socios"""
    id: str
    nombre: str
    descripcion: Optional[str] = None
    activa: bool

class CategoriaCreate(BaseModel):
    """Esquema para crear categoría"""
    nombre: str = Field(..., min_length=2, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=200)
