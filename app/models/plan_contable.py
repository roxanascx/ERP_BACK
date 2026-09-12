from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId


class NaturalezaCuenta(str, Enum):
    DEUDORA = "DEUDORA"
    ACREEDORA = "ACREEDORA"


class MonedaCuenta(str, Enum):
    MN = "MN"
    ME = "ME"

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
    naturaleza: NaturalezaCuenta = NaturalezaCuenta.DEUDORA
    moneda: MonedaCuenta = MonedaCuenta.MN
    activa: bool = True
    tipo_plan: str = "estandar"  # "estandar" | "personalizado"
    empresa_id: Optional[str] = None  # Para planes personalizados por empresa
    archivo_origen: Optional[str] = None  # Nombre del archivo importado
    # Metadatos para Centro de Costos y Caja/Bancos: solo tienen sentido en
    # cuentas hoja que aceptan movimiento (validado en plan_contable_services).
    requiere_centro_costo: bool = False
    es_cuenta_caja: bool = False
    es_cuenta_bancaria: bool = False
    # Asiento automático inmediato: al postear un movimiento en esta cuenta,
    # se generan además estas dos líneas espejo por el mismo importe (cargo
    # al debe, abono al haber). Validado en plan_contable_services; el motor
    # que las dispara vive en el módulo que registre el asiento (aún no
    # construido, ver plan de expansión de Contabilidad).
    cuenta_cargo_destino: Optional[Dict[str, str]] = None
    cuenta_abono_destino: Optional[Dict[str, str]] = None
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
    naturaleza: NaturalezaCuenta = NaturalezaCuenta.DEUDORA
    moneda: MonedaCuenta = MonedaCuenta.MN
    activa: bool = True
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None
    requiere_centro_costo: bool = False
    es_cuenta_caja: bool = False
    es_cuenta_bancaria: bool = False
    cuenta_cargo_destino: Optional[Dict[str, str]] = None
    cuenta_abono_destino: Optional[Dict[str, str]] = None

class CuentaContableUpdate(BaseModel):
    descripcion: Optional[str] = None
    es_hoja: Optional[bool] = None
    acepta_movimiento: Optional[bool] = None
    naturaleza: Optional[NaturalezaCuenta] = None
    moneda: Optional[MonedaCuenta] = None
    activa: Optional[bool] = None
    requiere_centro_costo: Optional[bool] = None
    es_cuenta_caja: Optional[bool] = None
    es_cuenta_bancaria: Optional[bool] = None
    cuenta_cargo_destino: Optional[Dict[str, str]] = None
    cuenta_abono_destino: Optional[Dict[str, str]] = None

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
    naturaleza: NaturalezaCuenta
    moneda: MonedaCuenta
    activa: bool
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None
    requiere_centro_costo: bool = False
    es_cuenta_caja: bool = False
    es_cuenta_bancaria: bool = False
    cuenta_cargo_destino: Optional[Dict[str, str]] = None
    cuenta_abono_destino: Optional[Dict[str, str]] = None
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


# Nuevos modelos para importación de planes personalizados
class ValidationResult(BaseModel):
    """Resultado de la validación de un archivo de plan contable"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    total_lines: int
    valid_accounts: int
    preview_data: List[Dict[str, Any]]


class ImportResult(BaseModel):
    """Resultado de la importación de un plan contable"""
    success: bool
    imported_count: int
    errors: List[str]
    warnings: List[str]
    backup_created: bool


class PlanContableInfo(BaseModel):
    """Información sobre un plan contable disponible"""
    tipo: str  # "estandar" | "personalizado"
    nombre: str
    descripcion: str
    total_cuentas: int
    fecha_creacion: Optional[datetime] = None
    archivo_origen: Optional[str] = None
    activo: bool = False


class SwitchPlanRequest(BaseModel):
    """Request para cambiar tipo de plan contable"""
    tipo_plan: str  # "estandar" | "personalizado"
    empresa_id: str
