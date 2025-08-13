from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

class AccountType(str, Enum):
    """Tipos de cuentas contables"""
    ASSET = "asset"          # Activo
    LIABILITY = "liability"  # Pasivo  
    EQUITY = "equity"        # Patrimonio
    INCOME = "income"        # Ingresos
    EXPENSE = "expense"      # Gastos

class EntryType(str, Enum):
    """Tipos de asientos contables"""
    OPENING = "opening"      # Apertura
    REGULAR = "regular"      # Operación
    ADJUSTMENT = "adjustment" # Ajuste
    CLOSING = "closing"      # Cierre

# ============ SCHEMAS DE ENTRADA ============

class AccountCreate(BaseModel):
    """Schema para crear una cuenta contable"""
    code: str = Field(..., description="Código de la cuenta (ej: 1.1.01.001)")
    name: str = Field(..., description="Nombre de la cuenta")
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    parent_code: Optional[str] = Field(None, description="Código de la cuenta padre")
    description: Optional[str] = Field(None, description="Descripción adicional")
    is_active: bool = Field(True, description="Si la cuenta está activa")

class JournalEntryLineCreate(BaseModel):
    """Schema para crear una línea de asiento contable"""
    account_code: str = Field(..., description="Código de la cuenta")
    description: str = Field(..., description="Descripción de la línea")
    debit: Decimal = Field(0, ge=0, description="Monto al debe")
    credit: Decimal = Field(0, ge=0, description="Monto al haber")

class JournalEntryCreate(BaseModel):
    """Schema para crear un asiento contable"""
    reference: str = Field(..., description="Referencia del asiento")
    description: str = Field(..., description="Descripción del asiento")
    entry_type: EntryType = Field(EntryType.REGULAR, description="Tipo de asiento")
    entry_date: datetime = Field(default_factory=datetime.now, description="Fecha del asiento")
    lines: List[JournalEntryLineCreate] = Field(..., min_items=2, description="Líneas del asiento")

# ============ SCHEMAS DE RESPUESTA ============

class AccountResponse(BaseModel):
    """Schema de respuesta para cuentas contables"""
    id: str = Field(..., description="ID de la cuenta")
    code: str = Field(..., description="Código de la cuenta")
    name: str = Field(..., description="Nombre de la cuenta")
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    parent_code: Optional[str] = Field(None, description="Código de la cuenta padre")
    description: Optional[str] = Field(None, description="Descripción")
    balance: Decimal = Field(0, description="Saldo actual")
    is_active: bool = Field(..., description="Si está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")

class JournalEntryLineResponse(BaseModel):
    """Schema de respuesta para líneas de asiento"""
    id: str = Field(..., description="ID de la línea")
    account_code: str = Field(..., description="Código de la cuenta")
    account_name: str = Field(..., description="Nombre de la cuenta")
    description: str = Field(..., description="Descripción")
    debit: Decimal = Field(..., description="Monto al debe")
    credit: Decimal = Field(..., description="Monto al haber")

class JournalEntryResponse(BaseModel):
    """Schema de respuesta para asientos contables"""
    id: str = Field(..., description="ID del asiento")
    entry_number: str = Field(..., description="Número de asiento")
    reference: str = Field(..., description="Referencia")
    description: str = Field(..., description="Descripción")
    entry_type: EntryType = Field(..., description="Tipo de asiento")
    entry_date: datetime = Field(..., description="Fecha del asiento")
    total_debit: Decimal = Field(..., description="Total debe")
    total_credit: Decimal = Field(..., description="Total haber")
    is_balanced: bool = Field(..., description="Si está balanceado")
    lines: List[JournalEntryLineResponse] = Field(..., description="Líneas del asiento")
    created_by: str = Field(..., description="Usuario que creó el asiento")
    created_at: datetime = Field(..., description="Fecha de creación")

# ============ SCHEMAS DE ACTUALIZACIÓN ============

class AccountUpdate(BaseModel):
    """Schema para actualizar una cuenta contable"""
    name: Optional[str] = Field(None, description="Nombre de la cuenta")
    description: Optional[str] = Field(None, description="Descripción")
    is_active: Optional[bool] = Field(None, description="Si está activa")

# ============ SCHEMAS DE REPORTES ============

class TrialBalanceItem(BaseModel):
    """Item del balance de comprobación"""
    account_code: str = Field(..., description="Código de cuenta")
    account_name: str = Field(..., description="Nombre de cuenta")
    account_type: AccountType = Field(..., description="Tipo de cuenta")
    debit_balance: Decimal = Field(0, description="Saldo deudor")
    credit_balance: Decimal = Field(0, description="Saldo acreedor")

class TrialBalanceResponse(BaseModel):
    """Response del balance de comprobación"""
    period_start: datetime = Field(..., description="Inicio del período")
    period_end: datetime = Field(..., description="Fin del período")
    total_debits: Decimal = Field(..., description="Total débitos")
    total_credits: Decimal = Field(..., description="Total créditos")
    is_balanced: bool = Field(..., description="Si está balanceado")
    accounts: List[TrialBalanceItem] = Field(..., description="Cuentas")
    generated_at: datetime = Field(default_factory=datetime.now, description="Fecha de generación")
