from datetime import datetime
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId

class CompanyModel(BaseModel):
    """
    Modelo de empresa con soporte completo para credenciales SIRE
    Adaptado del modelo original empresa.py
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
    
    # Datos básicos de la empresa
    ruc: str = Field(..., description="RUC de la empresa", min_length=11, max_length=11)
    razon_social: str = Field(..., description="Razón social de la empresa")
    direccion: Optional[str] = Field("", description="Dirección de la empresa")
    telefono: Optional[str] = Field("", description="Teléfono de la empresa")
    email: Optional[str] = Field("", description="Email de la empresa")
    activa: bool = Field(True, description="Si la empresa está activa")
    
    # Credenciales SIRE (según manual SUNAT)
    sire_client_id: Optional[str] = Field(None, description="Client ID de SIRE")
    sire_client_secret: Optional[str] = Field(None, description="Client Secret de SIRE")
    sire_activo: bool = Field(False, description="Si SIRE está habilitado")
    
    # Credenciales SUNAT principales (para SIRE y otros servicios)
    sunat_usuario: Optional[str] = Field(None, description="Usuario SUNAT principal")
    sunat_clave: Optional[str] = Field(None, description="Clave SUNAT principal")
    
    # Credenciales SUNAT adicionales
    sunat_usuario_secundario: Optional[str] = Field(None, description="Usuario SUNAT secundario")
    sunat_clave_secundaria: Optional[str] = Field(None, description="Clave SUNAT secundaria")
    
    # Credenciales bancarias
    sistema_bancario: Optional[str] = Field(None, description="Sistema bancario (BCP, BBVA, etc.)")
    banco_usuario: Optional[str] = Field(None, description="Usuario del banco")
    banco_clave: Optional[str] = Field(None, description="Clave del banco")
    
    # Credenciales PDT
    pdt_usuario: Optional[str] = Field(None, description="Usuario PDT")
    pdt_clave: Optional[str] = Field(None, description="Clave PDT")
    
    # Credenciales PLAME
    plame_usuario: Optional[str] = Field(None, description="Usuario PLAME")
    plame_clave: Optional[str] = Field(None, description="Clave PLAME")
    
    # Configuraciones y notas
    configuraciones: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuraciones adicionales")
    notas_internas: Optional[str] = Field(None, description="Notas internas")
    
    # Timestamps
    fecha_registro: datetime = Field(default_factory=datetime.now, description="Fecha de registro")
    fecha_actualizacion: datetime = Field(default_factory=datetime.now, description="Fecha de última actualización")
    
    def tiene_sire(self) -> bool:
        """Verifica si la empresa tiene credenciales SIRE configuradas y activas"""
        try:
            # Verificar que sire_activo sea un booleano verdadero
            sire_activo = self.sire_activo
            if isinstance(sire_activo, str):
                sire_activo = sire_activo.lower() in ('true', '1', 'yes', 'on')
            elif not isinstance(sire_activo, bool):
                sire_activo = False
                
            # Verificar que todos los campos requeridos existan y no estén vacíos
            return (
                bool(sire_activo) and 
                bool(self.sire_client_id) and 
                bool(self.sire_client_secret) and 
                bool(self.sunat_usuario) and  # Usar credenciales SUNAT principales
                bool(self.sunat_clave)
            )
        except:
            # Si hay cualquier error, asumir que no tiene SIRE
            return False
    
    def obtener_credenciales_sire_original(self) -> Optional[Dict[str, str]]:
        """
        Obtiene credenciales para el método SIRE original
        Endpoint: /clientessol/{client_id}/oauth2/token/
        Username: RUC + Usuario SOL (concatenado con espacio)
        Password: Clave SOL
        """
        if not self.tiene_sire():
            return None
        
        return {
            'client_id': self.sire_client_id,
            'client_secret': self.sire_client_secret,
            'username': f"{self.ruc} {self.sunat_usuario}",  # RUC + espacio + usuario SUNAT
            'password': self.sunat_clave,  # Clave SUNAT
            'endpoint_url': f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{self.sire_client_id}/oauth2/token/",
            'metodo': 'original'
        }
    
    def obtener_credenciales_sire_migrado(self) -> Optional[Dict[str, str]]:
        """
        Obtiene credenciales para el método SIRE migrado
        Endpoint: /clientessol/{ruc}/oauth2/token/
        Username: Solo el usuario SOL (sin RUC)
        Password: Clave SOL
        """
        if not self.tiene_sire():
            return None
        
        return {
            'ruc': self.ruc,
            'client_id': self.sire_client_id,
            'client_secret': self.sire_client_secret,
            'username': self.sunat_usuario,  # Usuario SUNAT
            'password': self.sunat_clave,  # Clave SUNAT
            'endpoint_url': f"https://api-seguridad.sunat.gob.pe/v1/clientessol/{self.ruc}/oauth2/token/",
            'metodo': 'migrado'
        }
