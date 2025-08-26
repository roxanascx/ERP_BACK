from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None


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
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None
    fecha_creacion: datetime


# Schemas para importación de planes personalizados
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


class ImportFileRequest(BaseModel):
    """Request para importar archivo de plan contable"""
    empresa_id: str
    filename: str
    content: str  # Contenido del archivo en base64 o texto plano
    fecha_modificacion: Optional[datetime]
