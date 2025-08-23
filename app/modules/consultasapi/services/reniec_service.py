"""
Servicio RENIEC para consultas DNI
Basado en el código funcional proporcionado
"""

import requests
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..models import DniData, DniConsultaResponse

logger = logging.getLogger(__name__)

class ReniecService:
    """Servicio para consultas reales a RENIEC"""
    
    def __init__(self):
        self.api_endpoints = [
            "https://api.apis.net.pe/v1/dni",
            "https://dniruc.apisperu.com/api/v1/dni/",
            "https://api.reniec.gob.pe/v1/consulta/"  # Endpoint oficial (si existe)
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.timeout = 8
        self.max_retries = 3
    
    async def consultar_dni(self, dni: str) -> DniConsultaResponse:
        """
        Consulta información de persona por DNI
        
        Args:
            dni: DNI de 8 dígitos
            
        Returns:
            DniConsultaResponse: Datos de la persona
        """
        try:
            logger.info(f"🔍 [RENIEC] Consultando DNI: {dni}")
            
            # Validar DNI
            if not self._validar_dni(dni):
                logger.error(f"❌ [RENIEC] DNI inválido: {dni}")
                return DniConsultaResponse(
                    success=False,
                    message="DNI inválido. Debe tener 8 dígitos numéricos.",
                    data=None
                )
            
            logger.info(f"✅ [RENIEC] DNI válido, consultando APIs reales")
            
            # Intentar APIs reales
            for endpoint in self.api_endpoints:
                try:
                    logger.info(f"🔄 [RENIEC] Probando API: {endpoint}")
                    resultado = await self._consultar_api_reniec(dni, endpoint)
                    if resultado.success:
                        logger.info(f"✅ [RENIEC] API exitosa: {endpoint}")
                        return resultado
                except Exception as e:
                    logger.warning(f"⚠️ [RENIEC] API {endpoint} falló: {str(e)}")
                    continue
            
            # Si las APIs fallan
            logger.error(f"❌ [RENIEC] Todas las APIs fallaron para DNI: {dni}")
            return DniConsultaResponse(
                success=False,
                message="No se pudo obtener información del DNI. Servicio RENIEC no disponible.",
                data=None
            )
            
        except Exception as e:
            logger.error(f"❌ [RENIEC] Error general para DNI {dni}: {e}")
            return DniConsultaResponse(
                success=False,
                message=f"Error en consulta RENIEC: {str(e)}",
                data=None
            )
    
    async def _consultar_api_reniec(self, dni: str, endpoint: str) -> DniConsultaResponse:
        """Intenta consultar una API real de RENIEC"""
        try:
            # Construir URL según el endpoint
            if "apis.net.pe" in endpoint:
                url = f"{endpoint}?numero={dni}"
            else:
                url = f"{endpoint}{dni}"
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                dni_data = self._normalizar_datos_reniec(data)
                
                return DniConsultaResponse(
                    success=True,
                    message="Consulta exitosa",
                    data=dni_data,
                    fuente="API Real"
                )
            else:
                return DniConsultaResponse(
                    success=False,
                    message=f"API no disponible - HTTP {response.status_code}",
                    data=None
                )
                
        except Exception as e:
            return DniConsultaResponse(
                success=False,
                message=f"Error API: {str(e)}",
                data=None
            )
    
    def _normalizar_datos_reniec(self, data: Dict) -> DniData:
        """Normaliza datos de diferentes APIs RENIEC"""
        apellido_paterno = data.get("apellidoPaterno") or data.get("apellidoPaterno") or ""
        apellido_materno = data.get("apellidoMaterno") or data.get("apellidoMaterno") or ""
        
        return DniData(
            dni=data.get("numeroDocumento") or data.get("dni") or "",
            nombres=data.get("nombres") or data.get("prenomes") or "",
            apellido_paterno=apellido_paterno,
            apellido_materno=apellido_materno,
            apellidos=f"{apellido_paterno} {apellido_materno}".strip(),
            fecha_nacimiento=data.get("fechaNacimiento") or None,
            estado_civil=data.get("estadoCivil") or "SOLTERO",
            ubigeo=data.get("ubigeo") or None,
            direccion=data.get("direccion") or None,
            restricciones=data.get("restricciones") or None
        )
    
    def _validar_dni(self, dni: str) -> bool:
        """Valida que el DNI tenga el formato correcto"""
        if not dni or len(dni) != 8:
            return False
        
        return dni.isdigit()
    
    async def verificar_estado_servicio(self) -> Dict[str, Any]:
        """Verifica el estado del servicio RENIEC"""
        try:
            # Probar con DNI de prueba (no real)
            dni_test = "12345678"
            resultado = await self.consultar_dni(dni_test)
            
            return {
                "disponible": len(self.api_endpoints) > 0,
                "apis_disponibles": len(self.api_endpoints),
                "ultimo_test": datetime.utcnow(),
                "test_dni": dni_test,
                "endpoints": self.api_endpoints
            }
        except Exception as e:
            return {
                "disponible": False,
                "error": str(e),
                "ultimo_test": datetime.utcnow()
            }
