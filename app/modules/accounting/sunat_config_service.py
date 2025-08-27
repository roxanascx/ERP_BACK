"""
Servicio de configuración SUNAT para determinar requerimientos específicos por empresa
"""
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from datetime import datetime, date
from ..companies.services import CompanyService
from .schemas import TipoAsientoSunat


class SunatLibroConfig(BaseModel):
    """Configuración SUNAT específica por empresa"""
    empresa_ruc: str
    empresa_id: str
    ingresos_uit_anterior: float
    formato_requerido: str  # "simplificado" | "completo"
    min_digitos_cuenta: int
    requiere_denominacion_cuenta: bool
    plan_contable_aplicable: str
    tipos_asientos_obligatorios: List[Dict[str, Any]]
    validaciones_activas: bool = True
    uit_referencia: float = 4950.0  # UIT 2024
    fecha_calculo: datetime
    
    class Config:
        from_attributes = True


class SunatValidationRule(BaseModel):
    """Regla de validación SUNAT"""
    nombre: str
    descripcion: str
    es_obligatoria: bool
    aplica_a_empresa: bool
    mensaje_error: str
    mensaje_recomendacion: Optional[str] = None


class SunatConfigService:
    """Servicio para configuración SUNAT por empresa"""
    
    def __init__(self, company_service: CompanyService):
        self.company_service = company_service
        self.uit_2024 = 4950.0  # UIT actualizada para 2024
    
    async def obtener_configuracion_empresa(self, empresa_id: str) -> SunatLibroConfig:
        """
        Obtener configuración SUNAT específica por empresa
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            SunatLibroConfig: Configuración específica SUNAT
            
        Raises:
            ValueError: Si la empresa no existe
        """
        empresa = await self.company_service.get_company_by_id(empresa_id)
        if not empresa:
            raise ValueError(f"Empresa {empresa_id} no encontrada")
        
        # Calcular ingresos UIT del año anterior
        ingresos_anterior = await self._calcular_ingresos_uit_anterior(empresa_id)
        
        # Determinar configuración según ingresos
        formato_requerido = self._determinar_formato_ple(ingresos_anterior)
        min_digitos = self._determinar_min_digitos_cuenta(ingresos_anterior)
        requiere_denominacion = self._requiere_denominacion_cuenta(ingresos_anterior)
        
        return SunatLibroConfig(
            empresa_ruc=empresa.ruc,
            empresa_id=empresa_id,
            ingresos_uit_anterior=ingresos_anterior,
            formato_requerido=formato_requerido,
            min_digitos_cuenta=min_digitos,
            requiere_denominacion_cuenta=requiere_denominacion,
            plan_contable_aplicable="PCGR",
            tipos_asientos_obligatorios=self._obtener_tipos_obligatorios(),
            validaciones_activas=True,
            uit_referencia=self.uit_2024,
            fecha_calculo=datetime.utcnow()
        )
    
    async def validar_empresa_para_sunat(self, empresa_id: str) -> Dict[str, Any]:
        """
        Validar si la empresa cumple requisitos básicos para SUNAT
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Dict con resultado de validación
        """
        try:
            empresa = await self.company_service.get_company_by_id(empresa_id)
            if not empresa:
                return {
                    "es_valida": False,
                    "errores": ["Empresa no encontrada"],
                    "warnings": [],
                    "recomendaciones": []
                }
            
            errores = []
            warnings = []
            recomendaciones = []
            
            # Validar RUC
            if not empresa.ruc or len(empresa.ruc) != 11:
                errores.append("RUC debe tener exactamente 11 dígitos")
            
            # Validar razón social
            if not empresa.razon_social or len(empresa.razon_social.strip()) < 3:
                errores.append("Razón social debe tener al menos 3 caracteres")
            
            # Validar fecha de inicio de operaciones
            if not hasattr(empresa, 'fecha_inicio_operaciones') or not empresa.fecha_inicio_operaciones:
                warnings.append("Se recomienda registrar fecha de inicio de operaciones")
            
            # Calcular ingresos y dar recomendaciones
            ingresos_uit = await self._calcular_ingresos_uit_anterior(empresa_id)
            if ingresos_uit >= 100:
                recomendaciones.append(
                    f"Empresa con ingresos {ingresos_uit:.1f} UIT debe usar formato completo PLE"
                )
            
            return {
                "es_valida": len(errores) == 0,
                "errores": errores,
                "warnings": warnings,
                "recomendaciones": recomendaciones,
                "ingresos_uit_anterior": ingresos_uit,
                "formato_sugerido": self._determinar_formato_ple(ingresos_uit)
            }
            
        except Exception as e:
            return {
                "es_valida": False,
                "errores": [f"Error validando empresa: {str(e)}"],
                "warnings": [],
                "recomendaciones": []
            }
    
    async def obtener_reglas_validacion(self, empresa_id: str) -> List[SunatValidationRule]:
        """
        Obtener reglas de validación específicas para una empresa
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Lista de reglas de validación aplicables
        """
        config = await self.obtener_configuracion_empresa(empresa_id)
        
        reglas = [
            # Reglas básicas aplicables a todas las empresas
            SunatValidationRule(
                nombre="balance_asientos",
                descripcion="Todos los asientos deben estar balanceados",
                es_obligatoria=True,
                aplica_a_empresa=True,
                mensaje_error="El asiento debe estar balanceado (Debe = Haber)",
                mensaje_recomendacion=None
            ),
            SunatValidationRule(
                nombre="correlatividad_estricta",
                descripcion="Los asientos deben tener correlatividad estricta sin saltos",
                es_obligatoria=True,
                aplica_a_empresa=True,
                mensaje_error="No se permiten saltos en la numeración correlativa",
                mensaje_recomendacion="Verificar que todos los números sean consecutivos"
            ),
            SunatValidationRule(
                nombre="minimo_digitos_cuenta",
                descripcion=f"Códigos de cuenta deben tener mínimo {config.min_digitos_cuenta} dígitos",
                es_obligatoria=True,
                aplica_a_empresa=True,
                mensaje_error=f"Código de cuenta debe tener mínimo {config.min_digitos_cuenta} dígitos",
                mensaje_recomendacion="Usar códigos de cuenta según Plan Contable General Revisado"
            )
        ]
        
        # Reglas específicas según ingresos
        if config.requiere_denominacion_cuenta:
            reglas.append(
                SunatValidationRule(
                    nombre="denominacion_cuenta_obligatoria",
                    descripcion="Todas las cuentas deben tener denominación",
                    es_obligatoria=True,
                    aplica_a_empresa=True,
                    mensaje_error="La cuenta debe tener denominación",
                    mensaje_recomendacion="Agregar descripción clara de la cuenta contable"
                )
            )
        
        if config.ingresos_uit_anterior >= 100:
            reglas.append(
                SunatValidationRule(
                    nombre="formato_completo_requerido",
                    descripcion="Empresa debe usar formato PLE completo",
                    es_obligatoria=True,
                    aplica_a_empresa=True,
                    mensaje_error="Empresa con ingresos ≥100 UIT debe usar formato completo",
                    mensaje_recomendacion="Asegurar que todos los campos obligatorios estén completos"
                )
            )
        
        return reglas
    
    # Métodos privados
    async def _calcular_ingresos_uit_anterior(self, empresa_id: str) -> float:
        """
        Calcular ingresos en UIT del año anterior
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Ingresos en UIT del año anterior
            
        Note:
            Por ahora retorna valor simulado. En implementación completa
            debería consultar módulo contable o ventas.
        """
        # TODO: Implementar cálculo real desde módulo contable/ventas
        # Por ahora simular valores para diferentes tipos de empresas
        
        empresa = await self.company_service.get_company_by_id(empresa_id)
        if not empresa:
            return 0.0
        
        # Simulación basada en RUC (últimos dígitos)
        ultimo_digito = int(empresa.ruc[-1]) if empresa.ruc else 0
        
        if ultimo_digito <= 3:
            return 25.0   # Empresa pequeña
        elif ultimo_digito <= 6:
            return 75.0   # Empresa mediana
        elif ultimo_digito <= 8:
            return 150.0  # Empresa grande
        else:
            return 250.0  # Empresa muy grande
    
    def _determinar_formato_ple(self, ingresos_uit: float) -> str:
        """
        Determinar formato PLE según ingresos UIT
        
        Args:
            ingresos_uit: Ingresos en UIT del período anterior
            
        Returns:
            "simplificado" o "completo"
        """
        return "completo" if ingresos_uit >= 100 else "simplificado"
    
    def _determinar_min_digitos_cuenta(self, ingresos_uit: float) -> int:
        """
        Determinar mínimo dígitos en código de cuenta según ingresos
        
        Args:
            ingresos_uit: Ingresos en UIT del período anterior
            
        Returns:
            Número mínimo de dígitos requerido
        """
        return 4 if ingresos_uit >= 100 else 3
    
    def _requiere_denominacion_cuenta(self, ingresos_uit: float) -> bool:
        """
        Determinar si se requiere denominación de cuenta
        
        Args:
            ingresos_uit: Ingresos en UIT del período anterior
            
        Returns:
            True si se requiere denominación obligatoria
        """
        # Empresas pequeñas deben incluir denominación
        return ingresos_uit < 100
    
    def _obtener_tipos_obligatorios(self) -> List[Dict[str, Any]]:
        """
        Obtener tipos de asientos obligatorios según normativa SUNAT
        
        Returns:
            Lista de tipos de asientos con sus características
        """
        return [
            {
                "tipo": TipoAsientoSunat.APERTURA,
                "codigo": "A",
                "descripcion": "Asiento de apertura del ejercicio",
                "obligatorio": True,
                "fecha_requerida": "01/01",
                "observaciones": "Debe registrarse al inicio del ejercicio contable"
            },
            {
                "tipo": TipoAsientoSunat.CIERRE,
                "codigo": "C", 
                "descripcion": "Asiento de cierre del ejercicio",
                "obligatorio": True,
                "fecha_requerida": "31/12",
                "observaciones": "Debe registrarse al final del ejercicio contable"
            },
            {
                "tipo": TipoAsientoSunat.OPERACION,
                "codigo": "M",
                "descripcion": "Asientos por operaciones diversas",
                "obligatorio": False,
                "fecha_requerida": None,
                "observaciones": "Asientos normales de operaciones del negocio"
            },
            {
                "tipo": TipoAsientoSunat.AJUSTE,
                "codigo": "J",
                "descripcion": "Asientos de ajuste",
                "obligatorio": False,
                "fecha_requerida": None,
                "observaciones": "Asientos de corrección o ajuste contable"
            },
            {
                "tipo": TipoAsientoSunat.DESTINO,
                "codigo": "D",
                "descripcion": "Asientos de destino",
                "obligatorio": False,
                "fecha_requerida": None,
                "observaciones": "Asientos para distribución de gastos o costos"
            }
        ]

    async def recalcular_configuracion_empresa(self, empresa_id: str) -> SunatLibroConfig:
        """
        Recalcular configuración SUNAT para una empresa
        Útil cuando cambian los datos de la empresa o ingresos
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Nueva configuración calculada
        """
        return await self.obtener_configuracion_empresa(empresa_id)
