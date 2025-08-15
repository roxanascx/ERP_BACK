"""
Servicio especializado para descarga de propuestas RVIE
Implementación según Manual SUNAT v25 - Secuencia oficial de servicios
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from decimal import Decimal
import logging
from io import BytesIO
import zipfile
import csv
import json
import base64

from fastapi import HTTPException

from ..models.rvie import (
    RvieComprobante, RviePropuesta, RvieInconsistencia, 
    RvieProcesoResult, RvieResumen, RvieEstadoProceso
)
from ..models.responses import SireApiResponse, TicketResponse, FileDownloadResponse
from ..utils.exceptions import SireException, SireApiException, SireValidationException
from .api_client import SunatApiClient
from .token_manager import SireTokenManager

logger = logging.getLogger(__name__)


class RvieDescargaService:
    """
    Servicio especializado para descarga de propuestas RVIE
    Implementa secuencia completa según Manual SUNAT v25
    """
    
    def __init__(self, api_client: SunatApiClient, token_manager: SireTokenManager, database=None):
        """
        Inicializar servicio de descarga RVIE
        
        Args:
            api_client: Cliente API para comunicación con SUNAT
            token_manager: Gestor de tokens JWT
            database: Conexión a MongoDB (opcional)
        """
        self.api_client = api_client
        self.token_manager = token_manager
        self.database = database
        
        # Códigos según Manual SUNAT v25
        self.CODIGO_TIPO_ARCHIVO = {
            "TXT": 0,
            "CSV": 1
        }
        
        self.CODIGO_TIPO_RESUMEN = {
            "PROPUESTA": 1,
            "PRELIMINAR": 2,
            "NO_INCLUIDOS": 3,
            "EXCLUIDOS": 4,
            "PRELIMINAR_REGISTRADO": 5,
            "AJUSTES_POSTERIORES": 6,
            "NO_DOMICILIADOS": 7
        }
        
        # Estados de ticket según SUNAT
        self.ESTADOS_TICKET = {
            "EN_PROCESO": ["0", "1", "2"],  # En proceso, Enviado, En cola
            "TERMINADO": ["3"],             # Terminado
            "ERROR": ["4", "5", "6"]        # Error, Cancelado, Timeout
        }
    
    async def descargar_propuesta_completa(
        self, 
        ruc: str, 
        periodo: str,
        cod_tipo_archivo: int = 0,  # 0=TXT, 1=CSV
        forzar_descarga: bool = False
    ) -> RviePropuesta:
        """
        Descarga completa de propuesta RVIE según secuencia oficial SUNAT v25
        
        SECUENCIA SEGÚN MANUAL:
        1. Validar parámetros
        2. Obtener token activo
        3. Realizar petición de descarga
        4. Si es asíncrona: manejar ticket
        5. Procesar archivo descargado
        6. Validar y estructurar datos
        
        Args:
            ruc: RUC del contribuyente (11 dígitos)
            periodo: Período en formato YYYYMM  
            cod_tipo_archivo: 0=TXT, 1=CSV (según manual)
            forzar_descarga: True para ignorar cache
        
        Returns:
            RviePropuesta: Propuesta completa con comprobantes
        
        Raises:
            SireApiException: Error en comunicación con SUNAT
            SireValidationException: Error de validación
        """
        try:
            inicio_proceso = datetime.utcnow()
            logger.info(f"📥 [RVIE-DESCARGA] Iniciando descarga completa para RUC {ruc}, período {periodo}")
            
            # PASO 1: VALIDACIONES ROBUSTAS
            await self._validar_parametros_descarga(ruc, periodo, cod_tipo_archivo)
            
            # PASO 2: VERIFICAR CACHE (si no se fuerza descarga)
            if not forzar_descarga:
                propuesta_cache = await self._obtener_propuesta_cache(ruc, periodo)
                if propuesta_cache:
                    logger.info(f"📦 [RVIE-DESCARGA] Propuesta encontrada en cache")
                    return propuesta_cache
            
            # PASO 3: OBTENER TOKEN ACTIVO
            token = await self.token_manager.get_active_session_token(ruc)
            if not token:
                raise SireException(
                    "No hay sesión activa para SUNAT. Debe autenticarse primero."
                )
            
            # PASO 4: REALIZAR PETICIÓN SEGÚN ESPECIFICACIÓN OFICIAL
            # URL del Manual SUNAT v25 línea 2893 (sin codTipoArchivo en la URL)
            endpoint_url = self.api_client.endpoints["rvie_descargar_propuesta"].format(
                periodo=periodo
            )
            
            logger.info(f"🌐 [RVIE-DESCARGA] Solicitando propuesta a: {endpoint_url}")
            
            # Parámetros según Manual v25 línea 2893 (van en query string)
            params = {
                "codTipoArchivo": str(cod_tipo_archivo),  # 0=TXT, 1=CSV según manual
                # Parámetros opcionales del manual (se pueden agregar después):
                # "mtoTotalDesde": "",
                # "mtoTotalHasta": "",
                # "fecDocumentoDesde": "",
                # "fecDocumentoHasta": "",
                # "numRucAdquiriente": "",
                # "numCarSunat": "",
                # "codTipoCDP": "",
                # "codTipoInconsistencia": ""
            }
            
            response = await self.api_client._make_request(
                method="GET",
                url=f"{self.api_client.base_url}{endpoint_url}",
                params=params,
                token=token
            )
            
            response_data = response.json()
            
            # PASO 5: DETERMINAR TIPO DE RESPUESTA
            if self._es_respuesta_asincrona(response_data):
                # Respuesta con ticket (datos masivos)
                propuesta = await self._procesar_descarga_asincrona(
                    ruc, periodo, response_data, cod_tipo_archivo
                )
            else:
                # Respuesta síncrona directa
                propuesta = await self._procesar_descarga_sincrona(
                    ruc, periodo, response_data, cod_tipo_archivo
                )
            
            # PASO 6: ALMACENAR RESULTADO
            await self._almacenar_propuesta(propuesta)
            
            # PASO 7: AUDITORÍA
            tiempo_procesamiento = (datetime.utcnow() - inicio_proceso).total_seconds()
            await self._registrar_auditoria_descarga(
                ruc, periodo, propuesta, tiempo_procesamiento
            )
            
            logger.info(
                f"✅ [RVIE-DESCARGA] Propuesta descargada exitosamente. "
                f"Comprobantes: {propuesta.cantidad_comprobantes}, "
                f"Total: S/ {propuesta.total_importe}, "
                f"Tiempo: {tiempo_procesamiento:.2f}s"
            )
            
            return propuesta
            
        except SireValidationException:
            raise
        except SireApiException:
            raise
        except Exception as e:
            logger.error(f"❌ [RVIE-DESCARGA] Error inesperado: {e}")
            raise SireException(f"Error interno en descarga de propuesta: {str(e)}")
    
    async def _validar_parametros_descarga(
        self, 
        ruc: str, 
        periodo: str, 
        cod_tipo_archivo: int
    ) -> None:
        """Validar parámetros según especificación SUNAT"""
        
        # Validar RUC
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise SireValidationException("RUC debe tener 11 dígitos numéricos")
        
        # Validar período
        if not periodo or len(periodo) != 6 or not periodo.isdigit():
            raise SireValidationException("Período debe tener formato YYYYMM")
        
        try:
            year = int(periodo[:4])
            month = int(periodo[4:])
            if year < 2010 or year > 2030 or month < 1 or month > 12:
                raise SireValidationException("Período fuera de rango válido")
        except:
            raise SireValidationException("Formato de período inválido")
        
        # Validar código tipo archivo
        if cod_tipo_archivo not in [0, 1]:
            raise SireValidationException("Código tipo archivo debe ser 0 (TXT) o 1 (CSV)")
        
        # Validar que el período no sea futuro
        periodo_date = datetime.strptime(periodo + "01", "%Y%m%d").date()
        if periodo_date > date.today().replace(day=1):
            raise SireValidationException("No se puede descargar propuesta de período futuro")
    
    def _es_respuesta_asincrona(self, response_data: Dict[str, Any]) -> bool:
        """Determinar si la respuesta contiene un ticket (asíncrona)"""
        return (
            "ticket" in response_data or 
            "ticketId" in response_data or
            "numeroTicket" in response_data or
            ("estado" in response_data and response_data.get("estado") == "EN_PROCESO")
        )
    
    async def _procesar_descarga_asincrona(
        self, 
        ruc: str, 
        periodo: str, 
        response_data: Dict[str, Any],
        cod_tipo_archivo: int
    ) -> RviePropuesta:
        """
        Procesar descarga asíncrona con ticket
        Según Manual v25: consultar estado y descargar cuando esté listo
        """
        
        # Extraer ticket ID
        ticket_id = (
            response_data.get("ticket") or 
            response_data.get("ticketId") or 
            response_data.get("numeroTicket")
        )
        
        if not ticket_id:
            raise SireApiException("Respuesta asíncrona sin ticket ID válido")
        
        logger.info(f"🎫 [RVIE-DESCARGA] Procesando ticket asíncrono: {ticket_id}")
        
        # Esperar a que el ticket esté listo
        archivo_data = await self._esperar_ticket_completado(ruc, ticket_id)
        
        # Procesar archivo descargado
        propuesta = await self._procesar_archivo_propuesta(
            ruc, periodo, archivo_data, cod_tipo_archivo, ticket_id
        )
        
        return propuesta
    
    async def _procesar_descarga_sincrona(
        self, 
        ruc: str, 
        periodo: str, 
        response_data: Dict[str, Any],
        cod_tipo_archivo: int
    ) -> RviePropuesta:
        """Procesar respuesta síncrona directa"""
        
        logger.info(f"⚡ [RVIE-DESCARGA] Procesando respuesta síncrona")
        
        # El contenido puede venir en diferentes campos según SUNAT
        archivo_content = None
        
        if "contenido" in response_data:
            archivo_content = response_data["contenido"]
        elif "archivo" in response_data:
            archivo_content = response_data["archivo"]
        elif "data" in response_data:
            archivo_content = response_data["data"]
        else:
            # Asumir que toda la respuesta es el contenido
            archivo_content = response_data
        
        # Procesar contenido
        propuesta = await self._procesar_archivo_propuesta(
            ruc, periodo, archivo_content, cod_tipo_archivo, None
        )
        
        return propuesta
    
    async def _esperar_ticket_completado(
        self, 
        ruc: str, 
        ticket_id: str,
        max_intentos: int = 30,
        intervalo_segundos: int = 10
    ) -> bytes:
        """
        Esperar a que un ticket esté completado y descargar el archivo
        Según Manual v25: consultar estado periódicamente
        """
        
        token = await self.token_manager.get_active_session_token(ruc)
        
        for intento in range(max_intentos):
            try:
                # Consultar estado del ticket
                estado_url = self.api_client.endpoints["consultar_ticket"].format(
                    ticket_id=ticket_id
                )
                
                response = await self.api_client._make_request(
                    method="GET",
                    url=f"{self.api_client.base_url}{estado_url}",
                    token=token
                )
                
                estado_data = response.json()
                estado = str(estado_data.get("estado", ""))
                
                logger.info(f"🔍 [TICKET] Intento {intento + 1}: Estado {estado}")
                
                if estado in self.ESTADOS_TICKET["TERMINADO"]:
                    # Ticket completado, descargar archivo
                    nombre_archivo = estado_data.get("nombreArchivo")
                    if not nombre_archivo:
                        raise SireApiException("Ticket completado pero sin nombre de archivo")
                    
                    return await self._descargar_archivo_ticket(ruc, ticket_id, nombre_archivo)
                
                elif estado in self.ESTADOS_TICKET["ERROR"]:
                    # Error en el ticket
                    error_msg = estado_data.get("mensaje", "Error desconocido en ticket")
                    raise SireApiException(f"Error en ticket {ticket_id}: {error_msg}")
                
                # Ticket aún en proceso, esperar
                await asyncio.sleep(intervalo_segundos)
                
            except SireApiException:
                raise
            except Exception as e:
                logger.warning(f"⚠️ [TICKET] Error consultando estado: {e}")
                await asyncio.sleep(intervalo_segundos)
        
        raise SireTimeoutException(
            f"Timeout esperando ticket {ticket_id} después de {max_intentos} intentos"
        )
    
    async def _descargar_archivo_ticket(
        self, 
        ruc: str, 
        ticket_id: str, 
        nombre_archivo: str
    ) -> bytes:
        """Descargar archivo de ticket completado"""
        
        token = await self.token_manager.get_active_session_token(ruc)
        
        descarga_url = self.api_client.endpoints["descargar_archivo"].format(
            ticket_id=ticket_id,
            nombre_archivo=nombre_archivo
        )
        
        response = await self.api_client._make_request(
            method="GET",
            url=f"{self.api_client.base_url}{descarga_url}",
            token=token
        )
        
        # El archivo puede venir como binario o base64
        if response.headers.get("content-type", "").startswith("application/"):
            return response.content
        else:
            # Intentar decodificar como base64
            try:
                response_json = response.json()
                if "archivo" in response_json:
                    return base64.b64decode(response_json["archivo"])
            except:
                pass
            
            return response.content
    
    async def _procesar_archivo_propuesta(
        self, 
        ruc: str, 
        periodo: str, 
        archivo_data: Any,
        cod_tipo_archivo: int,
        ticket_id: Optional[str] = None
    ) -> RviePropuesta:
        """
        Procesar archivo de propuesta (TXT o CSV) según formato SUNAT
        """
        
        logger.info(f"📄 [RVIE-DESCARGA] Procesando archivo de propuesta")
        
        # Determinar formato del archivo
        if isinstance(archivo_data, bytes):
            # Archivo binario, puede estar comprimido
            archivo_content = await self._procesar_archivo_binario(archivo_data)
        elif isinstance(archivo_data, str):
            # Contenido de texto directo
            archivo_content = archivo_data
        elif isinstance(archivo_data, dict):
            # Respuesta JSON con datos estructurados
            return await self._procesar_respuesta_json(ruc, periodo, archivo_data, ticket_id)
        else:
            raise SireException(f"Tipo de archivo no soportado: {type(archivo_data)}")
        
        # Parsear contenido según tipo de archivo
        if cod_tipo_archivo == 0:  # TXT
            comprobantes = await self._parsear_archivo_txt(archivo_content)
        else:  # CSV
            comprobantes = await self._parsear_archivo_csv(archivo_content)
        
        # Crear propuesta
        propuesta = RviePropuesta(
            ruc=ruc,
            periodo=periodo,
            estado=RvieEstadoProceso.PROPUESTA,
            fecha_generacion=datetime.utcnow(),
            cantidad_comprobantes=len(comprobantes),
            total_base_imponible=sum(c.base_imponible for c in comprobantes),
            total_igv=sum(c.igv for c in comprobantes),
            total_otros_tributos=sum(c.otros_tributos for c in comprobantes),
            total_importe=sum(c.importe_total for c in comprobantes),
            comprobantes=comprobantes,
            ticket_id=ticket_id
        )
        
        return propuesta
    
    async def _procesar_archivo_binario(self, archivo_data: bytes) -> str:
        """Procesar archivo binario (puede estar comprimido)"""
        
        try:
            # Intentar descomprimir como ZIP
            with zipfile.ZipFile(BytesIO(archivo_data)) as zip_file:
                # Buscar el primer archivo de texto
                for filename in zip_file.namelist():
                    if filename.endswith(('.txt', '.csv')):
                        with zip_file.open(filename) as file:
                            return file.read().decode('utf-8')
                
                raise SireException("No se encontró archivo de texto en el ZIP")
        
        except zipfile.BadZipFile:
            # No es un ZIP, intentar como texto directo
            try:
                return archivo_data.decode('utf-8')
            except UnicodeDecodeError:
                return archivo_data.decode('latin-1')
    
    async def _parsear_archivo_txt(self, content: str) -> List[RvieComprobante]:
        """Parsear archivo TXT según formato SUNAT"""
        # TODO: Implementar parsing específico del formato TXT de SUNAT
        # El formato específico debe consultarse en el manual técnico
        comprobantes = []
        
        lines = content.strip().split('\n')
        for i, line in enumerate(lines[1:], 1):  # Skip header
            if line.strip():
                try:
                    # Parsing básico - DEBE AJUSTARSE AL FORMATO REAL
                    fields = line.split('|')
                    if len(fields) >= 10:
                        comprobante = RvieComprobante(
                            periodo=self._extract_field(fields, 0),
                            correlativo=str(i),
                            fecha_emision=datetime.strptime(self._extract_field(fields, 1), '%d/%m/%Y').date(),
                            tipo_comprobante=self._extract_field(fields, 2),
                            serie=self._extract_field(fields, 3),
                            numero=self._extract_field(fields, 4),
                            tipo_documento_cliente=self._extract_field(fields, 5),
                            numero_documento_cliente=self._extract_field(fields, 6),
                            razon_social_cliente=self._extract_field(fields, 7),
                            base_imponible=Decimal(self._extract_field(fields, 8) or "0"),
                            igv=Decimal(self._extract_field(fields, 9) or "0"),
                            importe_total=Decimal(self._extract_field(fields, 10) or "0")
                        )
                        comprobantes.append(comprobante)
                except Exception as e:
                    logger.warning(f"⚠️ Error parseando línea {i}: {e}")
        
        return comprobantes
    
    async def _parsear_archivo_csv(self, content: str) -> List[RvieComprobante]:
        """Parsear archivo CSV según formato SUNAT"""
        comprobantes = []
        
        lines = content.strip().split('\n')
        reader = csv.DictReader(lines)
        
        for i, row in enumerate(reader, 1):
            try:
                comprobante = RvieComprobante(
                    periodo=row.get('periodo', ''),
                    correlativo=str(i),
                    fecha_emision=datetime.strptime(row['fecha_emision'], '%d/%m/%Y').date(),
                    tipo_comprobante=row['tipo_comprobante'],
                    serie=row['serie'],
                    numero=row['numero'],
                    tipo_documento_cliente=row['tipo_documento_cliente'],
                    numero_documento_cliente=row['numero_documento_cliente'],
                    razon_social_cliente=row['razon_social_cliente'],
                    base_imponible=Decimal(row.get('base_imponible', '0')),
                    igv=Decimal(row.get('igv', '0')),
                    importe_total=Decimal(row.get('importe_total', '0'))
                )
                comprobantes.append(comprobante)
            except Exception as e:
                logger.warning(f"⚠️ Error parseando fila CSV {i}: {e}")
        
        return comprobantes
    
    def _extract_field(self, fields: List[str], index: int) -> str:
        """Extraer campo de lista de manera segura"""
        return fields[index].strip() if index < len(fields) else ""
    
    async def _procesar_respuesta_json(
        self, 
        ruc: str, 
        periodo: str, 
        data: Dict[str, Any],
        ticket_id: Optional[str]
    ) -> RviePropuesta:
        """Procesar respuesta JSON estructurada"""
        
        # Crear propuesta básica desde JSON
        comprobantes = []
        
        if "comprobantes" in data:
            for comp_data in data["comprobantes"]:
                comprobante = RvieComprobante(**comp_data)
                comprobantes.append(comprobante)
        
        propuesta = RviePropuesta(
            ruc=ruc,
            periodo=periodo,
            estado=RvieEstadoProceso.PROPUESTA,
            fecha_generacion=datetime.utcnow(),
            cantidad_comprobantes=len(comprobantes),
            total_base_imponible=sum(c.base_imponible for c in comprobantes),
            total_igv=sum(c.igv for c in comprobantes),
            total_otros_tributos=sum(c.otros_tributos for c in comprobantes),
            total_importe=sum(c.importe_total for c in comprobantes),
            comprobantes=comprobantes,
            ticket_id=ticket_id
        )
        
        return propuesta
    
    async def _obtener_propuesta_cache(self, ruc: str, periodo: str) -> Optional[RviePropuesta]:
        """Obtener propuesta del cache si existe"""
        if not self.database:
            return None
        
        try:
            collection = self.database.rvie_propuestas
            doc = await collection.find_one({
                "ruc": ruc,
                "periodo": periodo,
                "estado": {"$in": ["PROPUESTA", "ACEPTADO"]}
            })
            
            if doc:
                return RviePropuesta(**doc)
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo cache: {e}")
        
        return None
    
    async def _almacenar_propuesta(self, propuesta: RviePropuesta) -> None:
        """Almacenar propuesta en base de datos"""
        if not self.database:
            logger.warning("⚠️ No hay conexión a BD, no se puede almacenar propuesta")
            return
        
        try:
            collection = self.database.rvie_propuestas
            doc = propuesta.dict()
            doc["_id"] = f"{propuesta.ruc}_{propuesta.periodo}"
            
            await collection.replace_one(
                {"_id": doc["_id"]}, 
                doc, 
                upsert=True
            )
            
            logger.info(f"💾 [RVIE-DESCARGA] Propuesta almacenada en BD")
        except Exception as e:
            logger.error(f"❌ Error almacenando propuesta: {e}")
    
    async def _registrar_auditoria_descarga(
        self, 
        ruc: str, 
        periodo: str, 
        propuesta: RviePropuesta, 
        tiempo_procesamiento: float
    ) -> None:
        """Registrar auditoría de la descarga"""
        if not self.database:
            return
        
        try:
            collection = self.database.rvie_auditoria
            doc = {
                "ruc": ruc,
                "periodo": periodo,
                "operacion": "DESCARGAR_PROPUESTA",
                "timestamp": datetime.utcnow(),
                "resultado": {
                    "cantidad_comprobantes": propuesta.cantidad_comprobantes,
                    "total_importe": float(propuesta.total_importe),
                    "tiempo_procesamiento": tiempo_procesamiento,
                    "ticket_id": propuesta.ticket_id
                }
            }
            
            await collection.insert_one(doc)
        except Exception as e:
            logger.warning(f"⚠️ Error registrando auditoría: {e}")


# Importación de excepciones faltantes
class SireTimeoutException(SireException):
    """Excepción para timeouts"""
    pass
