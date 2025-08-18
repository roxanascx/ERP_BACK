"""
Servicio para Gestión de Ventas RVIE - Versión Oficial
Consulta directa a SUNAT usando únicamente endpoints del manual oficial v25
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from motor.motor_asyncio import AsyncIOMotorDatabase

from .auth_service import SireAuthService
from .api_client import SunatApiClient
from .token_manager import SireTokenManager

logger = logging.getLogger(__name__)

class RvieVentasService:
    """Servicio para gestión de ventas RVIE usando únicamente endpoints oficiales del manual SUNAT v25"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        # Usar servicios oficiales únicamente
        self.api_client = SunatApiClient()
        self.token_manager = SireTokenManager(db)
        self.auth_service = SireAuthService(self.api_client, self.token_manager)

    async def descargar_propuesta(
        self,
        ruc: str,
        periodo: str,
        cod_tipo_archivo: int = 0,
        mto_total_desde: Optional[float] = None,
        mto_total_hasta: Optional[float] = None,
        fec_documento_desde: Optional[str] = None,
        fec_documento_hasta: Optional[str] = None,
        num_ruc_adquiriente: Optional[str] = None,
        num_car_sunat: Optional[str] = None,
        cod_tipo_cdp: Optional[str] = None,
        cod_tipo_inconsistencia: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        5.18 Servicio Web Api descargar propuesta - Según manual SUNAT v25
        URL oficial: /v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{perTributario}/exportapropuesta
        """
        try:
            logger.info(f"📄 Descargando propuesta RVIE oficial para RUC {ruc}, periodo {periodo}")
            
            # Obtener token válido usando el servicio oficial
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                logger.warning(f"No hay token válido para RUC {ruc}, intentando autenticar...")
                # Si no hay token, intentar obtener credenciales y autenticar
                # (esto requeriría implementar get_credentials o usar las predeterminadas)
                raise Exception("No se pudo obtener token válido. Requiere autenticación previa.")
            
            # URL oficial según manual SUNAT v25 - Sección 5.18
            url_base = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta"
            url = f"{url_base}/{periodo}/exportapropuesta"
            
            # Construir parámetros de consulta según manual
            params = {
                "codTipoArchivo": cod_tipo_archivo  # 0: txt, 1: xls
            }
            
            # Agregar parámetros opcionales solo si se proporcionan
            if mto_total_desde is not None:
                params["mtoTotalDesde"] = mto_total_desde
            if mto_total_hasta is not None:
                params["mtoTotalHasta"] = mto_total_hasta
            if fec_documento_desde:
                params["fecDocumentoDesde"] = fec_documento_desde
            if fec_documento_hasta:
                params["fecDocumentoHasta"] = fec_documento_hasta
            if num_ruc_adquiriente:
                params["numRucAdquiriente"] = num_ruc_adquiriente
            if num_car_sunat:
                params["numCarSunat"] = num_car_sunat
            if cod_tipo_cdp:
                params["codTipoCDP"] = cod_tipo_cdp
            if cod_tipo_inconsistencia:
                params["codTipoInconsistencia"] = cod_tipo_inconsistencia
            
            # Headers según manual SUNAT
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            logger.info(f"🌐 Consultando URL oficial: {url}")
            logger.info(f"📋 Parámetros: {params}")
            
            # Realizar consulta con reintento en caso de 401
            max_intentos = 2
            for intento in range(max_intentos):
                try:
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url, headers=headers, params=params) as response:
                            logger.info(f"📡 Respuesta SUNAT: {response.status} (intento {intento + 1})")
                            
                            if response.status == 200:
                                # Respuesta exitosa
                                content_type = response.headers.get('content-type', '').lower()
                                
                                if 'application/json' in content_type:
                                    # El servicio retorna un ticket para descargar después
                                    data = await response.json()
                                    logger.info(f"✅ Ticket recibido: {data}")
                                    return {
                                        "tipo": "ticket",
                                        "ticket": data,
                                        "mensaje": "Ticket generado exitosamente. Use el servicio 5.17 para descargar."
                                    }
                                else:
                                    # Contenido directo (texto/csv/excel)
                                    contenido = await response.text()
                                    logger.info(f"✅ Contenido directo recibido: {len(contenido)} caracteres")
                                    
                                    # Procesar el contenido
                                    comprobantes = self._procesar_contenido_txt(contenido)
                                    
                                    return {
                                        "tipo": "contenido_directo",
                                        "total_comprobantes": len(comprobantes),
                                        "comprobantes": comprobantes,
                                        "resumen": self._generar_resumen(comprobantes),
                                        "contenido_raw": contenido[:1000] if len(contenido) > 1000 else contenido
                                    }
                            
                            elif response.status == 401:
                                logger.warning(f"⚠️ Token expirado (401), requiere renovación... (intento {intento + 1})")
                                if intento < max_intentos - 1:
                                    # Invalidar token actual
                                    await self.token_manager.revoke_token(ruc)
                                    # Para renovar necesitaríamos autenticar de nuevo
                                    raise Exception("Token expirado. Requiere nueva autenticación.")
                                else:
                                    raise Exception("Token inválido después de renovación")
                            
                            else:
                                # Error de respuesta
                                try:
                                    error_json = await response.json()
                                    logger.error(f"❌ Error SUNAT {response.status}: {error_json}")
                                    raise Exception(f"Error SUNAT {response.status}: {error_json}")
                                except:
                                    error_text = await response.text()
                                    logger.error(f"❌ Error SUNAT {response.status}: {error_text}")
                                    raise Exception(f"Error SUNAT {response.status}: {error_text}")
                
                except aiohttp.ClientError as e:
                    logger.error(f"❌ Error de conexión (intento {intento + 1}): {str(e)}")
                    if intento < max_intentos - 1:
                        await asyncio.sleep(2)
                        continue
                    raise Exception(f"Error de conexión: {str(e)}")
            
            # Si llegamos aquí, todos los intentos fallaron
            raise Exception("Se agotaron todos los intentos de consulta")
        
        except Exception as e:
            logger.error(f"❌ Error en descargar_propuesta: {str(e)}")
            raise e

    def _procesar_contenido_txt(self, contenido: str) -> List[Dict[str, Any]]:
        """Procesar contenido TXT de SUNAT y convertir a lista de comprobantes"""
        try:
            comprobantes = []
            lineas = contenido.strip().split('\n')
            
            logger.info(f"📋 Procesando {len(lineas)} líneas de contenido")
            
            for i, linea in enumerate(lineas):
                if not linea.strip():
                    continue
                    
                try:
                    # Procesar según formato estándar SUNAT
                    campos = linea.split('|')
                    
                    if len(campos) >= 5:  # Validar campos mínimos
                        comprobante = {
                            "linea": i + 1,
                            "periodo": campos[0] if len(campos) > 0 else "",
                            "ruc": campos[1] if len(campos) > 1 else "",
                            "serie": campos[2] if len(campos) > 2 else "",
                            "numero": campos[3] if len(campos) > 3 else "",
                            "fecha_emision": campos[4] if len(campos) > 4 else "",
                            "tipo_documento": campos[5] if len(campos) > 5 else "",
                            "importe_total": float(campos[6]) if len(campos) > 6 and campos[6].replace('.', '').replace('-', '').isdigit() else 0.0,
                            "campos_adicionales": campos[7:] if len(campos) > 7 else [],
                            "linea_original": linea
                        }
                        comprobantes.append(comprobante)
                    else:
                        logger.warning(f"⚠️ Línea {i + 1} con formato incompleto: {len(campos)} campos")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando línea {i + 1}: {e}")
                    continue
            
            logger.info(f"✅ Procesados {len(comprobantes)} comprobantes válidos")
            return comprobantes
            
        except Exception as e:
            logger.error(f"❌ Error procesando contenido TXT: {e}")
            return []

    def _generar_resumen(self, comprobantes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generar resumen estadístico de los comprobantes"""
        if not comprobantes:
            return {"total_comprobantes": 0, "importe_total": 0.0}
        
        total_comprobantes = len(comprobantes)
        importe_total = sum(comp.get("importe_total", 0.0) for comp in comprobantes)
        
        # Contar por tipo de documento
        tipos_documento = {}
        for comp in comprobantes:
            tipo = comp.get("tipo_documento", "Sin tipo")
            tipos_documento[tipo] = tipos_documento.get(tipo, 0) + 1
        
        return {
            "total_comprobantes": total_comprobantes,
            "importe_total": round(importe_total, 2),
            "tipos_documento": tipos_documento,
            "primer_comprobante": comprobantes[0] if comprobantes else None,
            "ultimo_comprobante": comprobantes[-1] if comprobantes else None
        }
