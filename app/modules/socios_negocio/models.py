from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId

class SocioNegocioModel(BaseModel):
    """
    Modelo de Socio de Negocio - Unifica proveedores y clientes
    Incluye integración con consulta RUC de SUNAT
    """
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True
    )
    
    # ID para MongoDB
    id: Optional[str] = Field(default=None, alias="_id")
    
    @field_validator('id', mode='before')
    @classmethod
    def validate_object_id(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v
    
    # === IDENTIFICACIÓN ===
    tipo_documento: str = Field(..., description="RUC, DNI, CE")
    numero_documento: str = Field(..., description="Número del documento", min_length=8, max_length=11)
    
    # === DATOS BÁSICOS ===
    razon_social: str = Field(..., description="Razón social/Nombre completo")
    nombre_comercial: Optional[str] = Field(None, description="Nombre comercial")
    
    # === CLASIFICACIÓN ===
    tipo_socio: str = Field(..., description="proveedor, cliente, ambos")
    categoria: Optional[str] = Field(None, description="Categoría del socio")
    
    # === DATOS SUNAT (Solo para RUC) ===
    estado_sunat: Optional[str] = Field(None, description="Estado del contribuyente en SUNAT")
    condicion_sunat: Optional[str] = Field(None, description="Condición del contribuyente en SUNAT")
    tipo_contribuyente: Optional[str] = Field(None, description="Tipo de contribuyente SUNAT")
    fecha_inscripcion: Optional[date] = Field(None, description="Fecha de inscripción en SUNAT")
    actividad_economica: Optional[str] = Field(None, description="Actividad económica principal")
    
    # === UBICACIÓN ===
    ubigeo: Optional[str] = Field(None, description="Código ubigeo")
    direccion: Optional[str] = Field(None, description="Dirección fiscal")
    departamento: Optional[str] = Field(None, description="Departamento")
    provincia: Optional[str] = Field(None, description="Provincia")
    distrito: Optional[str] = Field(None, description="Distrito")
    
    # === CONTACTO ===
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    celular: Optional[str] = Field(None, description="Celular de contacto")
    email: Optional[str] = Field(None, description="Email de contacto")
    contacto_principal: Optional[str] = Field(None, description="Nombre del contacto principal")
    
    # === DATOS FINANCIEROS ===
    moneda_preferida: str = Field("PEN", description="Moneda preferida para transacciones")
    condicion_pago: Optional[str] = Field(None, description="Condición de pago por defecto")
    limite_credito: Optional[float] = Field(None, description="Límite de crédito")
    
    # === ESTADO Y METADATOS ===
    activo: bool = Field(True, description="Si el socio está activo")
    observaciones: Optional[str] = Field(None, description="Observaciones generales")
    
    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    empresa_id: str = Field(..., description="ID de la empresa propietaria")
    
    # === SINCRONIZACIÓN SUNAT ===
    ultimo_sync_sunat: Optional[datetime] = Field(None, description="Última sincronización con SUNAT")
    requiere_actualizacion: bool = Field(False, description="Si requiere actualización desde SUNAT")
    datos_sunat_disponibles: bool = Field(False, description="Si tiene datos obtenidos de SUNAT")
    
    @field_validator('numero_documento')
    @classmethod
    def validate_numero_documento(cls, v, info):
        """Valida el número de documento según el tipo"""
        if not v:
            return v
            
        # Obtener tipo_documento del contexto
        tipo = info.data.get('tipo_documento')
        
        if tipo == 'RUC':
            if len(v) != 11:
                raise ValueError('RUC debe tener 11 dígitos')
            if not v.isdigit():
                raise ValueError('RUC debe contener solo números')
            if v[0] not in ['1', '2']:
                raise ValueError('RUC debe empezar con 1 o 2')
        elif tipo == 'DNI':
            if len(v) != 8:
                raise ValueError('DNI debe tener 8 dígitos')
            if not v.isdigit():
                raise ValueError('DNI debe contener solo números')
        elif tipo == 'CE':
            if len(v) < 8 or len(v) > 12:
                raise ValueError('CE debe tener entre 8 y 12 caracteres')
                
        return v
    
    @field_validator('tipo_socio')
    @classmethod
    def validate_tipo_socio(cls, v):
        """Valida que el tipo de socio sea válido"""
        tipos_validos = ['proveedor', 'cliente', 'ambos']
        if v not in tipos_validos:
            raise ValueError(f'Tipo de socio debe ser uno de: {", ".join(tipos_validos)}')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validación básica de email"""
        if v and '@' not in v:
            raise ValueError('Email debe tener formato válido')
        return v
