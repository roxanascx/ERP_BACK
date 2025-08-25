from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_json_schema__(cls, _source_type, _handler):
        return {"type": "string"}

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class CuentaContable(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None
    cuenta_padre: Optional[str] = None
    es_hoja: bool = True
    acepta_movimiento: bool = True
    naturaleza: str = "DEUDORA"
    moneda: str = "MN"
    activa: bool = True
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_modificacion: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class CuentaContableCreate(BaseModel):
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    grupo: Optional[str] = None
    subgrupo: Optional[str] = None
    cuenta_padre: Optional[str] = None
    es_hoja: bool = True
    acepta_movimiento: bool = True
    naturaleza: str = "DEUDORA"
    moneda: str = "MN"
    activa: bool = True

class CuentaContableUpdate(BaseModel):
    descripcion: Optional[str] = None
    es_hoja: Optional[bool] = None
    acepta_movimiento: Optional[bool] = None
    naturaleza: Optional[str] = None
    activa: Optional[bool] = None

class CuentaContableResponse(BaseModel):
    id: str
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    grupo: Optional[str]
    subgrupo: Optional[str]
    cuenta_padre: Optional[str]
    es_hoja: bool
    acepta_movimiento: bool
    naturaleza: str
    moneda: str
    activa: bool
    tiene_hijos: bool = False
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime]

class ClaseContable(BaseModel):
    clase: int
    descripcion: str
    total_cuentas: int = 0
    cuentas: List[CuentaContableResponse] = []

class EstadisticasPlanContable(BaseModel):
    total_cuentas: int
    cuentas_activas: int
    cuentas_inactivas: int
    por_clase: List[ClaseContable]
    por_nivel: List[Dict[str, Any]]
