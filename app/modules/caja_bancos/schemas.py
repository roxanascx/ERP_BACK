"""
Caja/Bancos (MVP): catálogo de cajas y cuentas bancarias, y sus pagos/cobros.

Cada `CuentaCajaBanco` apunta a una cuenta del Plan Contable marcada
`es_cuenta_caja` o `es_cuenta_bancaria` (ver `app/models/plan_contable.py`),
en vez de duplicar el plan de cuentas dentro de este módulo. Los movimientos
se contabilizan en lotes reversibles, igual que
`contabilizacion_ventas_service.py`. Sin conciliación bancaria: queda para una
fase posterior.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class TipoCuentaCajaBanco(str, Enum):
    CAJA = "CAJA"
    BANCO = "BANCO"


class MonedaCajaBanco(str, Enum):
    MN = "MN"
    ME = "ME"


class TipoMovimientoCajaBanco(str, Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class MedioPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"
    TARJETA = "TARJETA"


class CuentaCajaBancoBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=10)
    nombre: str = Field(..., min_length=1, max_length=100)
    tipo: TipoCuentaCajaBanco
    moneda: MonedaCajaBanco = MonedaCajaBanco.MN
    # {codigo, denominacion} de una cuenta del Plan Contable marcada
    # es_cuenta_caja (si tipo=CAJA) o es_cuenta_bancaria (si tipo=BANCO).
    cuenta_contable: Dict[str, str]
    banco: Optional[str] = Field(None, max_length=100)
    numero_cuenta: Optional[str] = Field(None, max_length=30)
    cci: Optional[str] = Field(None, max_length=30)
    saldo_inicial: float = 0.0
    activa: bool = True

    @field_validator("codigo")
    @classmethod
    def codigo_sin_espacios(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("El código no puede estar vacío")
        return v

    @field_validator("cuenta_contable")
    @classmethod
    def cuenta_contable_con_codigo(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v.get("codigo"):
            raise ValueError("cuenta_contable debe traer al menos el código")
        return v


class CuentaCajaBancoCreate(CuentaCajaBancoBase):
    """Alta de una cuenta de caja o banco."""


class CuentaCajaBancoUpdate(BaseModel):
    """Modificación. Todo opcional: se actualiza solo lo que venga."""

    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    banco: Optional[str] = Field(None, max_length=100)
    numero_cuenta: Optional[str] = Field(None, max_length=30)
    cci: Optional[str] = Field(None, max_length=30)
    activa: Optional[bool] = None


class CuentaCajaBancoResponse(CuentaCajaBancoBase):
    id: str
    empresa_id: str
    saldo_actual: float = 0.0
    creado_en: Optional[datetime] = None
    creado_por: Optional[str] = None
    modificado_en: Optional[datetime] = None
    modificado_por: Optional[str] = None


class MovimientoCajaBancoBase(BaseModel):
    cuenta_caja_banco_id: str
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    tipo: TipoMovimientoCajaBanco
    monto: float = Field(..., gt=0)
    glosa: str = Field(..., max_length=500)
    medio_pago: MedioPago = MedioPago.EFECTIVO
    documento_referencia: Optional[str] = Field(None, max_length=50)
    # Solo de referencia (quién cobró/pagó); no reemplaza la contra-cuenta.
    socio_negocio_id: Optional[str] = None
    # Cuenta contra la que se contabiliza el movimiento (la cuenta por
    # cobrar/pagar del socio, un gasto, un ingreso...). Se exige siempre:
    # este ERP no tiene todavía una cuenta contable asociada a cada socio
    # de negocio, así que adivinarla produciría asientos mal imputados.
    contra_cuenta: Dict[str, str]
    centro_costo: Optional[Dict[str, str]] = None

    @field_validator("contra_cuenta")
    @classmethod
    def contra_cuenta_con_codigo(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v.get("codigo"):
            raise ValueError("contra_cuenta debe traer al menos el código")
        return v


class MovimientoCajaBancoCreate(MovimientoCajaBancoBase):
    """Alta de un movimiento (pago o cobro)."""


class MovimientoCajaBancoResponse(MovimientoCajaBancoBase):
    id: str
    empresa_id: str
    contabilizado: bool = False
    lote_contabilizacion: Optional[str] = None
    numeroAsiento: Optional[str] = None
    creado_en: Optional[datetime] = None
    creado_por: Optional[str] = None
