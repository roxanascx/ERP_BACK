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
from typing import Dict, List, Optional

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


class DocumentoTipo(str, Enum):
    """A qué registro pertenece un documento aplicado: Compras o Ventas."""
    COMPRA = "COMPRA"
    VENTA = "VENTA"


class DocumentoAplicadoBase(BaseModel):
    """
    Una aplicación de pago/cobro contra un documento pendiente de Registro de
    Compras o Ventas (ver `pendientes.py`). El saldo de ese documento se
    deriva sumando estas aplicaciones, nunca se guarda un campo "saldo" en el
    documento origen.
    """
    documento_tipo: DocumentoTipo
    documento_id: str
    monto: float = Field(..., gt=0)


class DocumentoAplicadoCreate(DocumentoAplicadoBase):
    """Alta de una aplicación, dentro de un `MovimientoCajaBancoCreate`."""


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
    # Códigos de los catálogos en `catalogos.py` (Tipo de Documento, Medio de
    # Pago, Flujo de Efectivo). Se validan en el servicio, no aquí con un
    # Enum de Pydantic, para no tener que tocar el schema cada vez que se
    # corrija una entrada de un catálogo que es solo texto de referencia.
    tipo_documento: str = Field(..., max_length=2)
    medio_pago: str = Field(..., max_length=3)
    flujo_efectivo: str = Field(..., max_length=3)
    documento_referencia: Optional[str] = Field(None, max_length=50)
    # Solo de referencia (quién cobró/pagó); también se usa para buscar sus
    # documentos pendientes en `pendientes.py`.
    socio_negocio_id: Optional[str] = None
    # Documentos de Compras/Ventas que este movimiento cancela, total o
    # parcialmente. Ver `DocumentoAplicadoBase`.
    documentos_aplicados: List[DocumentoAplicadoCreate] = Field(default_factory=list)
    # Cuenta contra la que se contabiliza la parte del importe que NO quedó
    # cubierta por `documentos_aplicados` (un pago a cuenta sin factura, un
    # vuelto, etc.). Opcional: solo hace falta si sobra importe sin aplicar.
    contra_cuenta: Optional[Dict[str, str]] = None
    centro_costo: Optional[Dict[str, str]] = None

    @field_validator("contra_cuenta")
    @classmethod
    def contra_cuenta_con_codigo(cls, v: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        if v is not None and not v.get("codigo"):
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


class DocumentoPendiente(BaseModel):
    """
    Un documento de Registro de Compras o Ventas con saldo pendiente de
    pago/cobro, tal como lo devuelve `pendientes.listar_pendientes`.
    """
    documento_id: str
    documento_tipo: DocumentoTipo
    tipo_comprobante: Optional[str] = None
    serie: Optional[str] = None
    numero: Optional[str] = None
    fecha_comprobante: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    moneda: Optional[str] = None
    importe_total: float
    monto_pagado: float
    saldo_pendiente: float
    dias_vencido: Optional[int] = None
    # Quién debe/a quién se le debe este documento (RUC/DNI y razón social
    # del proveedor o cliente, tal como quedaron en Registro de Compras o
    # Ventas). Se incluye siempre, no solo en el modo "todos los pendientes",
    # para no tener que volver a resolverlo en el frontend.
    contraparte_nombre: Optional[str] = None
    contraparte_documento: Optional[str] = None
