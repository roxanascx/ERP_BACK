"""
Servicio SUNAT para consultas RUC
Basado en el código funcional proporcionado
"""

import requests
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..models import RucData, RucConsultaResponse

logger = logging.getLogger(__name__)

class SunatService:
    """Servicio para consultas reales a SUNAT"""
    
    def __init__(self):
        self.base_url = "https://api.apis.net.pe/v1/ruc"
        self.backup_urls = [
            "https://dniruc.apisperu.com/api/v1/ruc/",
            "https://api.sunat.gob.pe/v1/contribuyente/contribuyentes/"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.timeout = 10
        self.max_retries = 3
    
    async def consultar_ruc(self, ruc: str) -> RucConsultaResponse:
        """
        Consulta información de empresa por RUC en SUNAT
        
        Args:
            ruc: RUC de 11 dígitos
            
        Returns:
            RucConsultaResponse: Datos de la empresa
        """
        try:
            logger.info(f"🔍 [SUNAT] Consultando RUC: {ruc}")
            
            # Validar RUC
            if not self._validar_ruc(ruc):
                logger.error(f"❌ [SUNAT] RUC inválido: {ruc}")
                return RucConsultaResponse(
                    success=False,
                    message="RUC inválido. Debe tener 11 dígitos numéricos y formato válido.",
                    data=None
                )
            
            # Intentar consulta con API principal
            resultado = await self._consultar_api_principal(ruc)
            if resultado.success:
                logger.info(f"✅ [SUNAT] API principal exitosa para RUC: {ruc}")
                return resultado
            
            # Si falla, intentar APIs de respaldo
            for backup_url in self.backup_urls:
                try:
                    logger.info(f"🔄 [SUNAT] Probando API backup: {backup_url}")
                    resultado = await self._consultar_api_backup(ruc, backup_url)
                    if resultado.success:
                        logger.info(f"✅ [SUNAT] API backup exitosa: {backup_url}")
                        return resultado
                except Exception as e:
                    logger.warning(f"⚠️ [SUNAT] API backup falló {backup_url}: {e}")
                    continue
            
            # Si todas las APIs fallan
            logger.error(f"❌ [SUNAT] Todas las APIs fallaron para RUC: {ruc}")
            return RucConsultaResponse(
                success=False,
                message="No se pudo obtener información del RUC. Todos los servicios no están disponibles.",
                data=None
            )
            
        except Exception as e:
            logger.error(f"❌ [SUNAT] Error general para RUC {ruc}: {e}")
            return RucConsultaResponse(
                success=False,
                message=f"Error en consulta SUNAT: {str(e)}",
                data=None
            )
    
    async def _consultar_api_principal(self, ruc: str) -> RucConsultaResponse:
        """Consulta usando API principal"""
        try:
            url = f"{self.base_url}?numero={ruc}"
            
            # Usar requests de forma síncrona (para mantener compatibilidad)
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                ruc_data = self._normalizar_datos_sunat(data)
                
                return RucConsultaResponse(
                    success=True,
                    message="Consulta exitosa",
                    data=ruc_data,
                    fuente="API Principal"
                )
            else:
                return RucConsultaResponse(
                    success=False,
                    message=f"Error HTTP {response.status_code} en API principal",
                    data=None
                )
                
        except Exception as e:
            return RucConsultaResponse(
                success=False,
                message=f"Error API principal: {str(e)}",
                data=None
            )
    
    async def _consultar_api_backup(self, ruc: str, backup_url: str) -> RucConsultaResponse:
        """Consulta usando APIs de respaldo"""
        try:
            url = f"{backup_url}{ruc}"
            response = requests.get(url, headers=self.headers, timeout=8)
            
            if response.status_code == 200:
                data = response.json()
                ruc_data = self._normalizar_datos_sunat(data)
                
                return RucConsultaResponse(
                    success=True,
                    message="Consulta exitosa",
                    data=ruc_data,
                    fuente="API Backup"
                )
            else:
                return RucConsultaResponse(
                    success=False,
                    message=f"Error HTTP {response.status_code} en API backup",
                    data=None
                )
                
        except Exception as e:
            return RucConsultaResponse(
                success=False,
                message=f"Error API backup: {str(e)}",
                data=None
            )
    
    def _normalizar_datos_sunat(self, data: Dict) -> RucData:
        """Normaliza los datos de diferentes APIs a un formato estándar"""
        
        return RucData(
            ruc=data.get("numeroDocumento") or data.get("ruc") or "",
            razon_social=data.get("razonSocial") or data.get("nombre") or "",
            nombre_comercial=data.get("nombreComercial") or data.get("nombreComercial") or None,
            estado=data.get("estado") or data.get("condicion") or "ACTIVO",
            tipo_empresa=data.get("tipoDocumento") or data.get("tipo") or None,
            direccion=data.get("direccion") or data.get("domicilioFiscal") or None,
            ubigeo=data.get("ubigeo") or None,
            departamento=data.get("departamento") or None,
            provincia=data.get("provincia") or None,
            distrito=data.get("distrito") or None,
            fecha_inscripcion=data.get("fechaInscripcion") or None,
            actividad_economica=data.get("actividadEconomica") or None,
            sistema_contabilidad=data.get("sistemaContabilidad") or None,
            tipo_facturacion=data.get("tipoFacturacion") or None,
            comercio_exterior=data.get("comercioExterior") or None,
            telefono=data.get("telefono") or None,
            email=data.get("email") or None,
            representante_legal=data.get("representanteLegal") or None,
            trabajadores=data.get("trabajadores") or 0
        )
    
    def _validar_ruc(self, ruc: str) -> bool:
        """Valida que el RUC tenga el formato correcto"""
        if not ruc or len(ruc) != 11:
            return False
        
        if not ruc.isdigit():
            return False
        
        # Los primeros dos dígitos deben ser válidos para tipo de contribuyente
        tipo_contrib = ruc[:2]
        tipos_validos = ["10", "15", "17", "20"]
        
        return tipo_contrib in tipos_validos
    
    async def verificar_estado_servicio(self) -> Dict[str, Any]:
        """Verifica el estado del servicio SUNAT"""
        try:
            # Probar con RUC conocido (SUNAT mismo)
            ruc_test = "20131312955"  # RUC de SUNAT
            resultado = await self.consultar_ruc(ruc_test)
            
            return {
                "disponible": resultado.success,
                "apis_principales": 1,
                "apis_backup": len(self.backup_urls),
                "ultimo_test": datetime.utcnow(),
                "test_ruc": ruc_test
            }
        except Exception as e:
            return {
                "disponible": False,
                "error": str(e),
                "ultimo_test": datetime.utcnow()
            }
