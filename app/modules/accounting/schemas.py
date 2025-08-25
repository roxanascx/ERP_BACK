from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CuentaContableCreate(BaseModel):
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    cuenta_padre: Optional[str] = None
    es_hoja: bool = True
    acepta_movimiento: bool = True
    naturaleza: str = "DEUDORA"
    moneda: str = "MN"


class CuentaContableResponse(BaseModel):
    id: Optional[str]
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    cuenta_padre: Optional[str]
    es_hoja: bool
    acepta_movimiento: bool
    naturaleza: str
    moneda: str
    activa: bool
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime]
