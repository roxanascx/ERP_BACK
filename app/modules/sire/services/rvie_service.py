"""
Servicio RVIE - Registro de Ventas e Ingresos Electrónico
Implementa todas las operaciones RVIE según manual SUNAT
"""

import asyncio
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
import logging
from io import BytesIO
import zipfile
import csv

from ..models.rvie import (
    RvieComprobante, RviePropuesta, RvieInconsistencia, 
    RvieProcesoResult, RvieResumen, RvieEstadoProceso
)
from ..models.responses import SireApiResponse, TicketResponse, FileDownloadResponse
from ..utils.exceptions import SireException, SireApiException, SireValidationException
from .api_client import SunatApiClient
from .token_manager import SireTokenManager

logger = logging.getLogger(__name__)


class RvieService:
    """Servicio RVIE - Registro de Ventas e Ingresos Electrónico"""
    
    def __init__(self, api_client: SunatApiClient, token_manager: SireTokenManager):
        """
        Inicializar servicio RVIE
        
        Args:
            api_client: Cliente API para comunicación con SUNAT
            token_manager: Gestor de tokens JWT
        """
        self.api_client = api_client
        self.token_manager = token_manager
        
        # Configuración de endpoints RVIE
        self.rvie_endpoints = {
            "propuesta": "/rvie/propuesta",
            "aceptar": "/rvie/aceptar",
            "reemplazar": "/rvie/reemplazar", 
            "preliminar": "/rvie/preliminar",
            "inconsistencias": "/rvie/inconsistencias",
            "ticket": "/rvie/ticket",
            "archivo": "/rvie/archivo"
        }
        
        # Cache de operaciones
        self.operaciones_cache: Dict[str, Dict] = {}
    
    async def descargar_propuesta(self, ruc: str, periodo: str) -> RviePropuesta:
        """
        Descargar propuesta RVIE de SUNAT
        
        Este endpoint obtiene la propuesta inicial generada por SUNAT con todos
        los comprobantes que deberían integrar el registro de ventas.
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
        
        Returns:
            RviePropuesta: Propuesta con comprobantes
        
        Raises:
            SireApiException: Error en API SUNAT
            SireValidationException: Error de validación
        """
        try:
            logger.info(f"📥 [RVIE] Descargando propuesta para RUC {ruc}, periodo {periodo}")
            
            # Validar parámetros
            await self._validar_parametros_rvie(ruc, periodo)
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Hacer request a SUNAT
            params = {
                "ruc": ruc,
                "periodo": periodo,
                "tipo": "propuesta"
            }
            
            response_data = await self.api_client.get_with_auth(
                self.rvie_endpoints["propuesta"],
                token,
                params
            )
            
            # Procesar respuesta y convertir a modelo
            propuesta = await self._procesar_respuesta_propuesta(ruc, periodo, response_data)
            
            logger.info(f"✅ [RVIE] Propuesta descargada: {propuesta.cantidad_comprobantes} comprobantes")
            return propuesta
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error descargando propuesta: {e}")
            raise SireApiException(f"Error descargando propuesta RVIE: {e}")
    
    async def aceptar_propuesta(self, ruc: str, periodo: str) -> RvieProcesoResult:
        """
        Aceptar propuesta RVIE de SUNAT
        
        Actualiza el estado del registro libro y Control de procesos para indicar
        que se está registrando un preliminar a través de la propuesta aceptada.
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
        
        Returns:
            RvieProcesoResult: Resultado del proceso
        """
        try:
            logger.info(f"✅ [RVIE] Aceptando propuesta para RUC {ruc}, periodo {periodo}")
            
            # Validar parámetros
            await self._validar_parametros_rvie(ruc, periodo)
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar datos de aceptación
            data = {
                "ruc": ruc,
                "periodo": periodo,
                "accion": "aceptar",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Hacer request a SUNAT
            response_data = await self.api_client.post_with_auth(
                self.rvie_endpoints["aceptar"],
                token,
                data
            )
            
            # Procesar resultado
            resultado = await self._procesar_resultado_operacion(ruc, periodo, "ACEPTAR", response_data)
            
            logger.info(f"✅ [RVIE] Propuesta aceptada exitosamente")
            return resultado
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error aceptando propuesta: {e}")
            raise SireApiException(f"Error aceptando propuesta RVIE: {e}")
    
    async def reemplazar_propuesta(
        self, 
        ruc: str, 
        periodo: str, 
        archivo_txt: bytes
    ) -> RvieProcesoResult:
        """
        Reemplazar propuesta RVIE con archivo TXT
        
        Permite al generador reemplazar la propuesta SUNAT con lo considerado
        por el contribuyente mediante el uso de un archivo de formato .txt.
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
            archivo_txt: Contenido del archivo TXT
        
        Returns:
            RvieProcesoResult: Resultado del proceso con ticket
        """
        try:
            logger.info(f"🔄 [RVIE] Reemplazando propuesta para RUC {ruc}, periodo {periodo}")
            
            # Validar parámetros
            await self._validar_parametros_rvie(ruc, periodo)
            await self._validar_archivo_txt(archivo_txt)
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar datos de reemplazo
            data = {
                "ruc": ruc,
                "periodo": periodo,
                "accion": "reemplazar",
                "archivo_contenido": archivo_txt.decode('utf-8'),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Hacer request a SUNAT
            response_data = await self.api_client.post_with_auth(
                self.rvie_endpoints["reemplazar"],
                token,
                data
            )
            
            # Procesar resultado
            resultado = await self._procesar_resultado_operacion(ruc, periodo, "REEMPLAZAR", response_data)
            
            logger.info(f"✅ [RVIE] Propuesta reemplazada, ticket: {resultado.ticket_id}")
            return resultado
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error reemplazando propuesta: {e}")
            raise SireApiException(f"Error reemplazando propuesta RVIE: {e}")
    
    async def registrar_preliminar(
        self, 
        ruc: str, 
        periodo: str, 
        comprobantes: List[RvieComprobante]
    ) -> RvieProcesoResult:
        """
        Registrar preliminar RVIE
        
        Permite registrar los comprobantes del preliminar según corresponda
        al proceso ejecutado por el generador.
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
            comprobantes: Lista de comprobantes a registrar
        
        Returns:
            RvieProcesoResult: Resultado del registro
        """
        try:
            logger.info(f"📝 [RVIE] Registrando preliminar para RUC {ruc}, periodo {periodo}")
            logger.info(f"📊 [RVIE] Cantidad de comprobantes: {len(comprobantes)}")
            
            # Validar parámetros
            await self._validar_parametros_rvie(ruc, periodo)
            await self._validar_comprobantes_rvie(comprobantes, periodo)
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar datos de registro
            comprobantes_data = [comp.model_dump() for comp in comprobantes]
            data = {
                "ruc": ruc,
                "periodo": periodo,
                "accion": "registrar_preliminar",
                "comprobantes": comprobantes_data,
                "cantidad": len(comprobantes),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Hacer request a SUNAT
            response_data = await self.api_client.post_with_auth(
                self.rvie_endpoints["preliminar"],
                token,
                data
            )
            
            # Procesar resultado
            resultado = await self._procesar_resultado_operacion(ruc, periodo, "PRELIMINAR", response_data)
            resultado.comprobantes_procesados = len(comprobantes)
            
            logger.info(f"✅ [RVIE] Preliminar registrado exitosamente")
            return resultado
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error registrando preliminar: {e}")
            raise SireApiException(f"Error registrando preliminar RVIE: {e}")
    
    async def descargar_inconsistencias(
        self, 
        ruc: str, 
        periodo: str,
        fase: str = "propuesta"
    ) -> List[RvieInconsistencia]:
        """
        Descargar inconsistencias por comprobantes RVIE
        
        Permite descargar las inconsistencias asociadas a los comprobantes que
        se encuentran en la fase actual del proceso RVIE.
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
            fase: Fase del proceso (propuesta o preliminar)
        
        Returns:
            List[RvieInconsistencia]: Lista de inconsistencias encontradas
        """
        try:
            logger.info(f"⚠️ [RVIE] Descargando inconsistencias para RUC {ruc}, periodo {periodo}, fase {fase}")
            
            # Validar parámetros
            await self._validar_parametros_rvie(ruc, periodo)
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar parámetros
            params = {
                "ruc": ruc,
                "periodo": periodo,
                "fase": fase
            }
            
            # Hacer request a SUNAT
            response_data = await self.api_client.get_with_auth(
                self.rvie_endpoints["inconsistencias"],
                token,
                params
            )
            
            # Procesar inconsistencias
            inconsistencias = await self._procesar_inconsistencias(response_data)
            
            logger.info(f"📋 [RVIE] {len(inconsistencias)} inconsistencias encontradas")
            return inconsistencias
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error descargando inconsistencias: {e}")
            raise SireApiException(f"Error descargando inconsistencias RVIE: {e}")
    
    async def consultar_estado_ticket(self, ruc: str, ticket_id: str) -> TicketResponse:
        """
        Consultar estado del ticket RVIE
        
        Permite consultar el estado del número ticket asociado al proceso que
        genera el archivo de descarga o carga.
        
        Args:
            ruc: RUC del contribuyente
            ticket_id: ID del ticket a consultar
        
        Returns:
            TicketResponse: Estado del ticket
        """
        try:
            logger.info(f"🎫 [RVIE] Consultando ticket {ticket_id} para RUC {ruc}")
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar parámetros
            params = {
                "ruc": ruc,
                "ticket_id": ticket_id
            }
            
            # Hacer request a SUNAT
            response_data = await self.api_client.get_with_auth(
                self.rvie_endpoints["ticket"],
                token,
                params
            )
            
            # Procesar respuesta de ticket
            ticket_response = await self._procesar_respuesta_ticket(response_data)
            
            logger.info(f"📊 [RVIE] Ticket {ticket_id} estado: {ticket_response.status}")
            return ticket_response
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error consultando ticket: {e}")
            raise SireApiException(f"Error consultando ticket RVIE: {e}")
    
    async def descargar_archivo_ticket(self, ruc: str, ticket_id: str) -> FileDownloadResponse:
        """
        Descargar archivo generado por ticket RVIE
        
        Permite realizar la descarga de los archivos generados zipeados y
        particionados guardados en el fileserver.
        
        Args:
            ruc: RUC del contribuyente
            ticket_id: ID del ticket con archivo generado
        
        Returns:
            FileDownloadResponse: Información del archivo descargado
        """
        try:
            logger.info(f"📁 [RVIE] Descargando archivo de ticket {ticket_id} para RUC {ruc}")
            
            # Obtener token válido
            token = await self.token_manager.get_valid_token(ruc)
            if not token:
                raise SireException("Token no válido o expirado")
            
            # Preparar endpoint de descarga
            download_endpoint = f"{self.rvie_endpoints['archivo']}/{ticket_id}"
            
            # Descargar archivo
            file_content = await self.api_client.download_file(download_endpoint, token)
            
            # Procesar archivo descargado
            file_response = await self._procesar_archivo_descargado(ticket_id, file_content)
            
            logger.info(f"✅ [RVIE] Archivo descargado: {file_response.filename} ({file_response.file_size} bytes)")
            return file_response
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error descargando archivo: {e}")
            raise SireApiException(f"Error descargando archivo RVIE: {e}")
    
    async def obtener_resumen_periodo(self, ruc: str, periodo: str) -> RvieResumen:
        """
        Obtener resumen RVIE para un periodo
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo en formato YYYYMM
        
        Returns:
            RvieResumen: Resumen del periodo
        """
        try:
            logger.info(f"📊 [RVIE] Obteniendo resumen para RUC {ruc}, periodo {periodo}")
            
            # Obtener propuesta actual
            propuesta = await self.descargar_propuesta(ruc, periodo)
            
            # Calcular resumen
            resumen = RvieResumen(
                ruc=ruc,
                periodo=periodo,
                total_comprobantes=propuesta.cantidad_comprobantes,
                total_base_imponible=propuesta.total_base_imponible,
                total_igv=propuesta.total_igv,
                total_otros_tributos=propuesta.total_otros_tributos,
                total_importe=propuesta.total_importe,
                estado_actual=propuesta.estado,
                fecha_ultimo_proceso=propuesta.fecha_actualizacion
            )
            
            # Calcular resumen por tipo
            resumen_por_tipo = {}
            for comp in propuesta.comprobantes:
                tipo = comp.tipo_comprobante.value
                if tipo not in resumen_por_tipo:
                    resumen_por_tipo[tipo] = {
                        "cantidad": 0,
                        "base_imponible": 0,
                        "igv": 0,
                        "importe_total": 0
                    }
                
                resumen_por_tipo[tipo]["cantidad"] += 1
                resumen_por_tipo[tipo]["base_imponible"] += float(comp.base_imponible)
                resumen_por_tipo[tipo]["igv"] += float(comp.igv)
                resumen_por_tipo[tipo]["importe_total"] += float(comp.importe_total)
            
            resumen.resumen_por_tipo = resumen_por_tipo
            
            return resumen
            
        except Exception as e:
            logger.error(f"❌ [RVIE] Error obteniendo resumen: {e}")
            raise SireApiException(f"Error obteniendo resumen RVIE: {e}")
    
    # Métodos privados de soporte
    
    async def _validar_parametros_rvie(self, ruc: str, periodo: str):
        """Validar parámetros básicos RVIE"""
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise SireValidationException("RUC debe tener 11 dígitos", "ruc", ruc)
        
        if not periodo or len(periodo) != 6:
            raise SireValidationException("Periodo debe tener formato YYYYMM", "periodo", periodo)
        
        try:
            year = int(periodo[:4])
            month = int(periodo[4:])
            if year < 2000 or year > 2030 or month < 1 or month > 12:
                raise ValueError()
        except ValueError:
            raise SireValidationException("Periodo inválido", "periodo", periodo)
    
    async def _validar_archivo_txt(self, archivo_txt: bytes):
        """Validar formato de archivo TXT"""
        if not archivo_txt:
            raise SireValidationException("Archivo TXT vacío", "archivo", None)
        
        try:
            contenido = archivo_txt.decode('utf-8')
            if len(contenido.strip()) == 0:
                raise SireValidationException("Archivo TXT sin contenido", "archivo", None)
        except UnicodeDecodeError:
            raise SireValidationException("Archivo TXT con codificación inválida", "archivo", None)
    
    async def _validar_comprobantes_rvie(self, comprobantes: List[RvieComprobante], periodo: str):
        """Validar lista de comprobantes RVIE"""
        if not comprobantes:
            raise SireValidationException("Lista de comprobantes vacía", "comprobantes", None)
        
        for i, comp in enumerate(comprobantes):
            if comp.periodo != periodo:
                raise SireValidationException(
                    f"Comprobante {i+1} tiene periodo incorrecto", 
                    f"comprobantes[{i}].periodo", 
                    comp.periodo
                )
    
    async def _procesar_respuesta_propuesta(self, ruc: str, periodo: str, response_data: dict) -> RviePropuesta:
        """Procesar respuesta de propuesta SUNAT"""
        # TODO: Implementar procesamiento real según respuesta SUNAT
        # Por ahora retornamos una propuesta de ejemplo
        
        return RviePropuesta(
            ruc=ruc,
            periodo=periodo,
            fecha_generacion=datetime.utcnow(),
            cantidad_comprobantes=response_data.get("cantidad", 0),
            total_base_imponible=response_data.get("total_base", 0),
            total_igv=response_data.get("total_igv", 0),
            total_importe=response_data.get("total_importe", 0),
            ticket_id=response_data.get("ticket_id")
        )
    
    async def _procesar_resultado_operacion(
        self, 
        ruc: str, 
        periodo: str, 
        operacion: str, 
        response_data: dict
    ) -> RvieProcesoResult:
        """Procesar resultado de operación RVIE"""
        
        exitoso = response_data.get("success", False)
        estado = RvieEstadoProceso.FINALIZADO if exitoso else RvieEstadoProceso.ERROR
        
        return RvieProcesoResult(
            ruc=ruc,
            periodo=periodo,
            operacion=operacion,
            estado=estado,
            exitoso=exitoso,
            mensaje=response_data.get("message", ""),
            ticket_id=response_data.get("ticket_id"),
            fecha_fin=datetime.utcnow()
        )
    
    async def _procesar_inconsistencias(self, response_data: dict) -> List[RvieInconsistencia]:
        """Procesar lista de inconsistencias"""
        inconsistencias = []
        
        for item in response_data.get("inconsistencias", []):
            inconsistencia = RvieInconsistencia(
                linea=item.get("linea", 0),
                campo=item.get("campo", ""),
                valor_encontrado=item.get("valor_encontrado", ""),
                valor_esperado=item.get("valor_esperado", ""),
                descripcion_error=item.get("descripcion", ""),
                tipo_error=item.get("tipo", "ERROR"),
                severidad=item.get("severidad", "ERROR")
            )
            inconsistencias.append(inconsistencia)
        
        return inconsistencias
    
    async def _procesar_respuesta_ticket(self, response_data: dict) -> TicketResponse:
        """Procesar respuesta de consulta de ticket"""
        from ..models.responses import TicketStatus
        
        return TicketResponse(
            ticket_id=response_data.get("ticket_id", ""),
            status=TicketStatus(response_data.get("status", "PENDIENTE")),
            descripcion=response_data.get("descripcion", ""),
            fecha_creacion=datetime.fromisoformat(response_data.get("fecha_creacion", datetime.utcnow().isoformat())),
            fecha_actualizacion=datetime.fromisoformat(response_data.get("fecha_actualizacion", datetime.utcnow().isoformat())),
            archivo_nombre=response_data.get("archivo_nombre"),
            progreso_porcentaje=response_data.get("progreso")
        )
    
    async def _procesar_archivo_descargado(self, ticket_id: str, file_content: bytes) -> FileDownloadResponse:
        """Procesar archivo descargado"""
        
        return FileDownloadResponse(
            filename=f"rvie_{ticket_id}.zip",
            content_type="application/zip",
            file_size=len(file_content),
            created_at=datetime.utcnow()
        )
