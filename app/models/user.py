from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class UserModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    id: Optional[str] = Field(default=None, alias="_id")
    clerk_id: str = Field(..., description="ID único de Clerk")
    email: str = Field(..., description="Email del usuario")
    username: Optional[str] = Field(None, description="Nombre de usuario")
    first_name: Optional[str] = Field(None, description="Nombre")
    last_name: Optional[str] = Field(None, description="Apellido")
    profile_image_url: Optional[str] = Field(None, description="URL de imagen de perfil")
    is_active: bool = Field(default=True, description="Usuario activo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sign_in_at: Optional[datetime] = Field(None, description="Último inicio de sesión")

class UserCreate(BaseModel):
    clerk_id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: Optional[bool] = None
    last_sign_in_at: Optional[datetime] = None

class UserResponse(BaseModel):
    id: str
    clerk_id: str
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    profile_image_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sign_in_at: Optional[datetime]
