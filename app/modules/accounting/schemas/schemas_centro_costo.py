"""
Centros de costo.

Catálogo simple que clasifica en qué área de la empresa se origina un gasto o
ingreso (Producción, Administración, Ventas, Financiero...). Se combina con la
bandera `requiere_centro_costo` del Plan de Cuentas (`app/models/plan_contable.py`):
cuando una cuenta la tiene marcada, el asiento que la use debe traer un centro
de costo de este catálogo (validado en `libro_diario_service._validar_asiento`).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CentroCostoBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=10)
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def codigo_sin_espacios(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("El código del centro de costo no puede estar vacío")
        return v


class CentroCostoCreate(CentroCostoBase):
    """Alta de un centro de costo."""


class CentroCostoUpdate(BaseModel):
    """Modificación. Todo opcional: se actualiza solo lo que venga."""

    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=200)
    activo: Optional[bool] = None


class CentroCostoResponse(CentroCostoBase):
    """Centro de costo tal como se devuelve, con su rastro de auditoría."""

    id: str
    empresa_id: str
    creado_en: Optional[datetime] = None
    creado_por: Optional[str] = None
    modificado_en: Optional[datetime] = None
    modificado_por: Optional[str] = None
