"""
Subdiarios contables.

Un subdiario clasifica las operaciones por su origen y naturaleza —«Registro
Ventas - Gravadas», «Registro Compras Locales», «Bancos - Ingresos»— y determina
qué tipo de asiento producen. Es la pieza que permite automatizar la
contabilización: sabiendo el subdiario de un comprobante se sabe qué cuentas
mueve y cómo.

Además es lo que SUNAT pide: el PLE del Libro Diario lleva un «código del libro o
registro de origen» de dos dígitos, que es exactamente este código. El campo ya
existía en `AsientoContableSunatV3.codigoLibroOrigen` sin que nadie lo rellenara.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class NaturalezaVenta(str, Enum):
    """
    Naturaleza tributaria de una venta.

    Es lo que distingue a los subdiarios 04-09 entre sí, y se puede **deducir de
    los importes** del comprobante, así que no hace falta que nadie la teclee al
    importar desde SIRE.
    """
    EXPORTACION = "EXPORTACION"
    GRAVADA = "GRAVADA"
    EXONERADA = "EXONERADA"
    INAFECTA = "INAFECTA"
    MIXTO = "MIXTO"
    GRAVADA_IGV_10 = "GRAVADA_IGV_10"


class NaturalezaCompra(str, Enum):
    """
    Naturaleza tributaria de una compra.

    Distingue a los subdiarios 11-18 y, igual que en ventas, se deduce de los
    importes del comprobante para no tener que teclearla al importar.

    SIN_DERECHO_CREDITO es la que se sale del patrón: el IGV existe pero no se
    puede usar como crédito fiscal, así que en vez de ir a la cuenta 40 se
    suma al gasto. No se deduce de los importes —depende de para qué se usó
    la compra—, así que solo aplica si el usuario manda el comprobante a ese
    subdiario a mano.
    """
    GRAVADA = "GRAVADA"
    NO_GRAVADA = "NO_GRAVADA"
    MIXTA = "MIXTA"
    IMPORTACION = "IMPORTACION"
    GRAVADA_Y_NO_GRAVADA = "GRAVADA_Y_NO_GRAVADA"
    SIN_DERECHO_CREDITO = "SIN_DERECHO_CREDITO"
    GRAVADA_IGV_10 = "GRAVADA_IGV_10"


class ModoCaja(str, Enum):
    """Detalle del asiento de caja."""
    AMBOS = "A"
    INGRESO = "I"
    EGRESO = "E"


class ModoBancos(str, Enum):
    """Detalle del asiento de bancos: distingue ingresos de egresos."""
    INGRESO = "I"
    EGRESO = "E"
    AMBOS = "A"


class CuentasSubdiario(BaseModel):
    """
    Cuentas que mueve el asiento de este subdiario.

    Ventas y compras son espejo y comparten la casilla del IGV —es la misma
    cuenta 40 con distinta subcuenta: débito fiscal en ventas, crédito fiscal
    en compras—, pero las otras dos son distintas y por eso llevan nombre
    propio. Un subdiario solo usa las de su tipo; las demás quedan vacías.

        Ventas gravadas      12 Debe  ·  40 Haber  ·  70 Haber
        Ventas exoneradas    12 Debe  ·               70 Haber
        Compras gravadas     60 Debe  ·  40 Debe   ·  42 Haber
        Compras no gravadas  60 Debe  ·               42 Haber
    """

    cuenta_cobro: Optional[str] = Field(
        None, description="Cuenta del Debe. Ventas: cuentas por cobrar (12)"
    )
    cuenta_ingreso: Optional[str] = Field(
        None, description="Cuenta del Haber. Ventas: ingresos (70)"
    )
    cuenta_igv: Optional[str] = Field(
        None,
        description=(
            "Cuenta del IGV (40). Vacía cuando no hay IGV que trasladar "
            "(ventas exoneradas o inafectas, compras no gravadas) o cuando "
            "el IGV no da derecho a crédito fiscal"
        ),
    )

    # --- Compras ---
    cuenta_gasto: Optional[str] = Field(
        None, description="Cuenta del Debe. Compras: compras (60) o gastos (63)"
    )
    cuenta_pago: Optional[str] = Field(
        None, description="Cuenta del Haber. Compras: cuentas por pagar (42)"
    )


class SubdiarioBase(BaseModel):
    """Datos de un subdiario, con la misma forma que la pantalla de mantenimiento."""

    codigo: str = Field(..., description="Código de dos dígitos", min_length=2, max_length=2)
    nombre: str = Field(..., min_length=1, max_length=100)
    detalle: Optional[str] = Field(None, max_length=200)
    sucursal: str = Field(default="0001", max_length=10)

    # --- Considerar subdiario para: ---
    # Son casillas independientes: un subdiario puede servir a varios tipos.
    asiento_compras: bool = False
    asiento_ventas: bool = False
    asiento_honorarios: bool = False
    asiento_cheque: bool = False
    asiento_caja: bool = False
    modo_caja: Optional[ModoCaja] = None
    asiento_bancos: bool = False
    modo_bancos: Optional[ModoBancos] = None
    asiento_canje_aplicacion: bool = False

    # --- Automatización de ventas ---
    naturaleza: Optional[NaturalezaVenta] = Field(
        None,
        description="Solo en subdiarios de venta. Permite asignarlos solos al importar",
    )

    # --- Automatización de compras ---
    # Campo aparte y no reutiliza `naturaleza` porque un subdiario puede
    # estar marcado para compras y para ventas a la vez, y porque los
    # valores de una y otra no son intercambiables.
    naturaleza_compra: Optional[NaturalezaCompra] = Field(
        None,
        description="Solo en subdiarios de compra. Permite asignarlos solos al importar",
    )
    cuentas: CuentasSubdiario = Field(default_factory=CuentasSubdiario)

    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def codigo_de_dos_digitos(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("El código del subdiario debe ser numérico de dos dígitos")
        return v

    def tipos_de_asiento(self) -> List[str]:
        """Para qué sirve este subdiario, en palabras. Útil para listarlos."""
        marcas = [
            (self.asiento_compras, "Compras"),
            (self.asiento_ventas, "Ventas"),
            (self.asiento_honorarios, "Honorarios"),
            (self.asiento_cheque, "Cheque"),
            (self.asiento_caja, "Caja"),
            (self.asiento_bancos, "Bancos"),
            (self.asiento_canje_aplicacion, "Canje/Aplicación"),
        ]
        return [nombre for marcado, nombre in marcas if marcado]

    def listo_para_contabilizar(self) -> bool:
        """
        ¿Se puede generar un asiento de venta con este subdiario?

        Hacen falta la cuenta de cobro y la de ingreso siempre, y la de IGV solo
        cuando la naturaleza lo lleva. Sin esto, contabilizar produciría un
        asiento descuadrado o con una cuenta vacía.
        """
        if not self.asiento_ventas:
            return False

        if not (self.cuentas.cuenta_cobro and self.cuentas.cuenta_ingreso):
            return False

        if self.naturaleza in (NaturalezaVenta.GRAVADA, NaturalezaVenta.GRAVADA_IGV_10):
            return bool(self.cuentas.cuenta_igv)

        return True

    def listo_para_contabilizar_compras(self) -> bool:
        """
        ¿Se puede generar un asiento de compra con este subdiario?

        Espejo del de ventas: hacen falta la cuenta de gasto y la de pago
        siempre, y la de IGV solo cuando la naturaleza lo lleva.

        SIN_DERECHO_CREDITO no la exige a propósito: ahí el IGV no va a la
        cuenta 40, se suma al gasto, así que pedirla sería exigir una cuenta
        que el asiento no va a usar.
        """
        if not self.asiento_compras:
            return False

        if not (self.cuentas.cuenta_gasto and self.cuentas.cuenta_pago):
            return False

        if self.naturaleza_compra in (
            NaturalezaCompra.GRAVADA,
            NaturalezaCompra.GRAVADA_IGV_10,
            NaturalezaCompra.MIXTA,
            NaturalezaCompra.IMPORTACION,
        ):
            return bool(self.cuentas.cuenta_igv)

        return True


class SubdiarioCreate(SubdiarioBase):
    """Alta de un subdiario."""


class SubdiarioUpdate(BaseModel):
    """Modificación. Todo opcional: se actualiza solo lo que venga."""

    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    detalle: Optional[str] = Field(None, max_length=200)
    sucursal: Optional[str] = Field(None, max_length=10)
    asiento_compras: Optional[bool] = None
    asiento_ventas: Optional[bool] = None
    asiento_honorarios: Optional[bool] = None
    asiento_cheque: Optional[bool] = None
    asiento_caja: Optional[bool] = None
    modo_caja: Optional[ModoCaja] = None
    asiento_bancos: Optional[bool] = None
    modo_bancos: Optional[ModoBancos] = None
    asiento_canje_aplicacion: Optional[bool] = None
    naturaleza: Optional[NaturalezaVenta] = None
    naturaleza_compra: Optional[NaturalezaCompra] = None
    cuentas: Optional[CuentasSubdiario] = None
    activo: Optional[bool] = None


class SubdiarioResponse(SubdiarioBase):
    """Subdiario tal como se devuelve, con su rastro de auditoría."""

    id: str
    empresa_id: str
    tipos: List[str] = Field(default_factory=list)
    listo: bool = False
    creado_en: Optional[datetime] = None
    creado_por: Optional[str] = None
    modificado_en: Optional[datetime] = None
    modificado_por: Optional[str] = None
