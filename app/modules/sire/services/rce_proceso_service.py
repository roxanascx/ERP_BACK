"""
RCE Proceso Service - Gestión de procesos RCE y seguimiento de tickets
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..models.rce import (
    RceProcesoResult, RceEstadoProceso, RceTicketConsulta,
    RceInconsistencia
)
from ..schemas.rce_schemas import (
    RceProcesoEnviarRequest, RceProcesoResponse,
    RceTicketConsultaRequest, RceTicketResponse,
    RceDescargaMasivaRequest
)
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_propuesta_service import RcePropuestaService
from ....shared.exceptions import SireException, SireValidationException


class RceProcesoService:
    """Servicio para gestión de procesos RCE y seguimiento de tickets"""
    
    def __init__(
        self, 
        database: AsyncIOMotorDatabase, 
        api_client: SunatApiClient, 
        auth_service: SireAuthService,
        propuesta_service: RcePropuestaService
    ):
        self.db = database
        self.api_client = api_client
        self.auth_service = auth_service
        self.propuesta_service = propuesta_service
        self.collection_procesos = database.rce_procesos
        self.collection_tickets = database.rce_tickets
        
    async def enviar_proceso(
        self,
        ruc: str,
        request: RceProcesoEnviarRequest,
        usuario_sunat: str,
        clave_sunat: str
    ) -> RceProcesoResponse:
        """
        Enviar proceso RCE a SUNAT
        
        Args:
            ruc: RUC del contribuyente
            request: Datos del proceso a enviar
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            
        Returns:
            RceProcesoResponse: Resultado del envío
            
        Raises:
            SireException: Si hay error en el envío
        """
        try:
            # Validar que existe la propuesta
            propuesta = await self.propuesta_service.consultar_propuesta(ruc, request.periodo)
            
            if not propuesta:
                raise SireException(f"No existe propuesta para el periodo {request.periodo}")
            
            if propuesta.estado != RceEstadoProceso.ACEPTADO:
                raise SireException(f"La propuesta debe estar ACEPTADA, estado actual: {propuesta.estado}")
            
            # Autenticar con SUNAT
            token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
            
            # Crear registro del proceso
            proceso = await self._crear_proceso_inicial(ruc, request, propuesta)
            
            # Preparar datos para SUNAT
            datos_envio = self._preparar_datos_proceso_sunat(proceso, request)
            
            # Enviar a SUNAT
            respuesta_sunat = await self.api_client.rce_proceso_enviar(token.access_token, datos_envio)
            
            # Actualizar proceso con respuesta
            proceso_actualizado = await self._actualizar_proceso_con_respuesta(
                proceso["_id"], respuesta_sunat
            )
            
            # Si hay ticket, crear registro de seguimiento
            if respuesta_sunat.get("ticket"):
                await self._crear_ticket_seguimiento(ruc, request.periodo, respuesta_sunat)
            
            return self._convertir_proceso_a_response(proceso_actualizado)
            
        except Exception as e:
            # Marcar proceso como error si ya se creó
            if 'proceso' in locals():
                await self._marcar_proceso_error(proceso["_id"], str(e))
            raise SireException(f"Error enviando proceso: {str(e)}")
    
    async def consultar_estado_proceso(
        self,
        ruc: str,
        periodo: str,
        ticket_id: Optional[str] = None
    ) -> Optional[RceProcesoResponse]:
        """
        Consultar estado de un proceso RCE
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo del proceso
            ticket_id: ID del ticket (opcional)
            
        Returns:
            RceProcesoResponse: Estado del proceso o None
        """
        try:
            filtros = {"ruc": ruc, "periodo": periodo}
            
            if ticket_id:
                filtros["ticket_id"] = ticket_id
            
            proceso = await self.collection_procesos.find_one(
                filtros,
                sort=[("fecha_inicio", -1)]  # Obtener el más reciente
            )
            
            if not proceso:
                return None
            
            return self._convertir_proceso_a_response(proceso)
            
        except Exception as e:
            raise SireException(f"Error consultando proceso: {str(e)}")
    
    async def consultar_ticket(
        self,
        ruc: str,
        ticket_id: str,
        usuario_sunat: str,
        clave_sunat: str,
        actualizar_desde_sunat: bool = True
    ) -> Optional[RceTicketResponse]:
        """
        Consultar estado de un ticket RCE
        
        Args:
            ruc: RUC del contribuyente
            ticket_id: ID del ticket
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            actualizar_desde_sunat: Si consultar estado actual en SUNAT
            
        Returns:
            RceTicketResponse: Estado del ticket o None
        """
        try:
            # Buscar ticket en base de datos local
            ticket_local = await self.collection_tickets.find_one({
                "ruc": ruc,
                "ticket_id": ticket_id
            })
            
            if not ticket_local:
                return None
            
            # Si se solicita, actualizar desde SUNAT
            if actualizar_desde_sunat:
                try:
                    token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
                    respuesta_sunat = await self.api_client.rce_ticket_consultar(token.access_token, ticket_id)
                    
                    # Actualizar ticket local con respuesta de SUNAT
                    await self._actualizar_ticket_con_respuesta_sunat(ticket_id, respuesta_sunat)
                    
                    # Recuperar ticket actualizado
                    ticket_local = await self.collection_tickets.find_one({
                        "ruc": ruc,
                        "ticket_id": ticket_id
                    })
                    
                except Exception as e:
                    # Si falla la consulta a SUNAT, usar datos locales
                    print(f"Warning: No se pudo consultar ticket en SUNAT: {e}")
            
            return self._convertir_ticket_a_response(ticket_local)
            
        except Exception as e:
            raise SireException(f"Error consultando ticket: {str(e)}")
    
    async def cancelar_proceso(
        self,
        ruc: str,
        periodo: str,
        usuario_sunat: str,
        clave_sunat: str,
        motivo: str
    ) -> RceProcesoResponse:
        """
        Cancelar un proceso RCE en SUNAT
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo del proceso
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            motivo: Motivo de la cancelación
            
        Returns:
            RceProcesoResponse: Resultado de la cancelación
        """
        try:
            # Buscar proceso activo
            proceso = await self.collection_procesos.find_one({
                "ruc": ruc,
                "periodo": periodo,
                "estado": {"$in": [RceEstadoProceso.ACEPTADO, RceEstadoProceso.PRELIMINAR]}
            })
            
            if not proceso:
                raise SireException("No hay proceso activo para cancelar")
            
            # Autenticar con SUNAT
            token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
            
            # Preparar datos de cancelación
            datos_cancelacion = {
                "ruc": ruc,
                "periodo": periodo,
                "numero_orden": proceso.get("numero_orden"),
                "motivo": motivo
            }
            
            # Enviar cancelación a SUNAT
            respuesta_sunat = await self.api_client.rce_proceso_cancelar(token.access_token, datos_cancelacion)
            
            # Actualizar proceso local
            await self.collection_procesos.update_one(
                {"_id": proceso["_id"]},
                {"$set": {
                    "estado": RceEstadoProceso.CANCELADO,
                    "fecha_fin": datetime.utcnow(),
                    "observaciones_cancelacion": motivo,
                    "respuesta_cancelacion": respuesta_sunat
                }}
            )
            
            # Recuperar proceso actualizado
            proceso_actualizado = await self.collection_procesos.find_one({"_id": proceso["_id"]})
            
            return self._convertir_proceso_a_response(proceso_actualizado)
            
        except Exception as e:
            raise SireException(f"Error cancelando proceso: {str(e)}")
    
    async def solicitar_descarga_masiva(
        self,
        ruc: str,
        request: RceDescargaMasivaRequest,
        usuario_sunat: str,
        clave_sunat: str
    ) -> RceTicketResponse:
        """
        Solicitar descarga masiva de comprobantes RCE
        
        Args:
            ruc: RUC del contribuyente
            request: Parámetros de descarga masiva
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            
        Returns:
            RceTicketResponse: Ticket de la descarga solicitada
        """
        try:
            # Autenticar con SUNAT
            token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
            
            # Preparar datos para SUNAT
            datos_descarga = self._preparar_datos_descarga_masiva(ruc, request)
            
            # Solicitar descarga a SUNAT
            respuesta_sunat = await self.api_client.rce_descarga_masiva_solicitar(token.access_token, datos_descarga)
            
            # Crear ticket de seguimiento
            ticket_data = {
                "ruc": ruc,
                "ticket_id": respuesta_sunat["ticket"],
                "tipo_operacion": "DESCARGA_MASIVA",
                "estado": "EN_PROCESO",
                "fecha_solicitud": datetime.utcnow(),
                "parametros_solicitud": request.dict(),
                "fecha_vencimiento": datetime.utcnow() + timedelta(hours=24),  # 24 horas por defecto
                "respuesta_sunat": respuesta_sunat
            }
            
            await self.collection_tickets.insert_one(ticket_data)
            
            return self._convertir_ticket_a_response(ticket_data)
            
        except Exception as e:
            raise SireException(f"Error solicitando descarga masiva: {str(e)}")
    
    async def listar_procesos(
        self,
        ruc: str,
        estado: Optional[RceEstadoProceso] = None,
        periodo_inicio: Optional[str] = None,
        periodo_fin: Optional[str] = None,
        limit: int = 50
    ) -> List[RceProcesoResponse]:
        """
        Listar procesos RCE del contribuyente
        
        Args:
            ruc: RUC del contribuyente
            estado: Filtro por estado (opcional)
            periodo_inicio: Periodo inicio (opcional)
            periodo_fin: Periodo fin (opcional)
            limit: Límite de resultados
            
        Returns:
            List[RceProcesoResponse]: Lista de procesos
        """
        try:
            filtros = {"ruc": ruc}
            
            if estado:
                filtros["estado"] = estado
            
            if periodo_inicio and periodo_fin:
                filtros["periodo"] = {"$gte": periodo_inicio, "$lte": periodo_fin}
            elif periodo_inicio:
                filtros["periodo"] = {"$gte": periodo_inicio}
            elif periodo_fin:
                filtros["periodo"] = {"$lte": periodo_fin}
            
            cursor = self.collection_procesos.find(filtros).sort("fecha_inicio", -1).limit(limit)
            procesos = await cursor.to_list(length=limit)
            
            return [self._convertir_proceso_a_response(proc) for proc in procesos]
            
        except Exception as e:
            raise SireException(f"Error listando procesos: {str(e)}")
    
    async def listar_tickets_activos(
        self,
        ruc: str,
        limit: int = 20
    ) -> List[RceTicketResponse]:
        """
        Listar tickets activos (no finalizados) del contribuyente
        
        Args:
            ruc: RUC del contribuyente
            limit: Límite de resultados
            
        Returns:
            List[RceTicketResponse]: Lista de tickets activos
        """
        try:
            filtros = {
                "ruc": ruc,
                "estado": {"$nin": ["FINALIZADO", "ERROR", "VENCIDO"]}
            }
            
            cursor = self.collection_tickets.find(filtros).sort("fecha_solicitud", -1).limit(limit)
            tickets = await cursor.to_list(length=limit)
            
            return [self._convertir_ticket_a_response(ticket) for ticket in tickets]
            
        except Exception as e:
            raise SireException(f"Error listando tickets: {str(e)}")
    
    # =======================================
    # MÉTODOS PRIVADOS
    # =======================================
    
    async def _crear_proceso_inicial(
        self,
        ruc: str,
        request: RceProcesoEnviarRequest,
        propuesta: Any
    ) -> Dict[str, Any]:
        """Crear registro inicial del proceso"""
        proceso_data = {
            "ruc": ruc,
            "periodo": request.periodo,
            "operacion": "ENVIO_PROCESO",
            "tipo_envio": request.tipo_envio,
            "estado": RceEstadoProceso.PENDIENTE,
            "fecha_inicio": datetime.utcnow(),
            "comprobantes_enviados": propuesta.cantidad_comprobantes,
            "total_importe_enviado": float(propuesta.total_importe),
            "observaciones_envio": request.observaciones_envio,
            "propuesta_referencia": propuesta.correlativo_propuesta
        }
        
        resultado = await self.collection_procesos.insert_one(proceso_data)
        proceso_data["_id"] = resultado.inserted_id
        
        return proceso_data
    
    def _preparar_datos_proceso_sunat(
        self,
        proceso: Dict[str, Any],
        request: RceProcesoEnviarRequest
    ) -> Dict[str, Any]:
        """Preparar datos del proceso para SUNAT"""
        return {
            "ruc": proceso["ruc"],
            "periodo": proceso["periodo"],
            "tipo_envio": request.tipo_envio,
            "confirmar_envio": request.confirmar_envio,
            "observaciones": request.observaciones_envio
        }
    
    async def _actualizar_proceso_con_respuesta(
        self,
        proceso_id: ObjectId,
        respuesta_sunat: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Actualizar proceso con respuesta de SUNAT"""
        update_data = {
            "fecha_fin": datetime.utcnow(),
            "respuesta_sunat": respuesta_sunat
        }
        
        if respuesta_sunat.get("exitoso", False):
            update_data.update({
                "estado": RceEstadoProceso.ACEPTADO,
                "exitoso": True,
                "ticket_id": respuesta_sunat.get("ticket"),
                "numero_orden": respuesta_sunat.get("numero_orden"),
                "mensaje": respuesta_sunat.get("mensaje", "Proceso enviado exitosamente")
            })
        else:
            update_data.update({
                "estado": RceEstadoProceso.ERROR,
                "exitoso": False,
                "mensaje": respuesta_sunat.get("mensaje", "Error en el envío"),
                "errores_criticos": respuesta_sunat.get("errores", [])
            })
        
        await self.collection_procesos.update_one(
            {"_id": proceso_id},
            {"$set": update_data}
        )
        
        return await self.collection_procesos.find_one({"_id": proceso_id})
    
    async def _marcar_proceso_error(self, proceso_id: ObjectId, error: str) -> None:
        """Marcar proceso como error"""
        await self.collection_procesos.update_one(
            {"_id": proceso_id},
            {"$set": {
                "estado": RceEstadoProceso.ERROR,
                "exitoso": False,
                "mensaje": error,
                "fecha_fin": datetime.utcnow()
            }}
        )
    
    async def _crear_ticket_seguimiento(
        self,
        ruc: str,
        periodo: str,
        respuesta_sunat: Dict[str, Any]
    ) -> None:
        """Crear ticket de seguimiento"""
        ticket_data = {
            "ruc": ruc,
            "periodo": periodo,
            "ticket_id": respuesta_sunat["ticket"],
            "tipo_operacion": "PROCESO_RCE",
            "estado": "EN_PROCESO",
            "fecha_solicitud": datetime.utcnow(),
            "numero_orden": respuesta_sunat.get("numero_orden"),
            "fecha_vencimiento": datetime.utcnow() + timedelta(hours=72),  # 72 horas por defecto
            "respuesta_inicial": respuesta_sunat
        }
        
        await self.collection_tickets.insert_one(ticket_data)
    
    async def _actualizar_ticket_con_respuesta_sunat(
        self,
        ticket_id: str,
        respuesta_sunat: Dict[str, Any]
    ) -> None:
        """Actualizar ticket con respuesta de SUNAT"""
        update_data = {
            "estado": respuesta_sunat.get("estado", "EN_PROCESO"),
            "porcentaje_avance": respuesta_sunat.get("porcentaje_avance"),
            "fecha_ultima_consulta": datetime.utcnow(),
            "mensaje_usuario": respuesta_sunat.get("mensaje"),
            "resultados_disponibles": respuesta_sunat.get("resultados_disponibles", False)
        }
        
        if respuesta_sunat.get("archivos_disponibles"):
            update_data["archivos_disponibles"] = respuesta_sunat["archivos_disponibles"]
        
        if respuesta_sunat.get("url_descarga"):
            update_data["url_descarga"] = respuesta_sunat["url_descarga"]
        
        await self.collection_tickets.update_one(
            {"ticket_id": ticket_id},
            {"$set": update_data}
        )
    
    def _preparar_datos_descarga_masiva(
        self,
        ruc: str,
        request: RceDescargaMasivaRequest
    ) -> Dict[str, Any]:
        """Preparar datos para descarga masiva"""
        datos = {
            "ruc": ruc,
            "periodo_inicio": request.periodo_inicio,
            "periodo_fin": request.periodo_fin,
            "formato": request.formato,
            "incluir_detalle": request.incluir_detalle,
            "incluir_resumen": request.incluir_resumen,
            "incluir_anulados": request.incluir_anulados
        }
        
        if request.tipo_comprobante:
            datos["tipo_comprobante"] = [tc.value for tc in request.tipo_comprobante]
        
        if request.solo_con_credito_fiscal is not None:
            datos["solo_con_credito_fiscal"] = request.solo_con_credito_fiscal
        
        return datos
    
    def _convertir_proceso_a_response(self, proceso_dict: Dict[str, Any]) -> RceProcesoResponse:
        """Convertir diccionario de MongoDB a RceProcesoResponse"""
        tiempo_procesamiento = None
        if proceso_dict.get("fecha_fin") and proceso_dict.get("fecha_inicio"):
            delta = proceso_dict["fecha_fin"] - proceso_dict["fecha_inicio"]
            tiempo_procesamiento = int(delta.total_seconds())
        
        return RceProcesoResponse(
            ruc=proceso_dict["ruc"],
            periodo=proceso_dict["periodo"],
            operacion=proceso_dict["operacion"],
            estado=RceEstadoProceso(proceso_dict["estado"]),
            exitoso=proceso_dict.get("exitoso", False),
            codigo_respuesta=proceso_dict.get("codigo_respuesta"),
            mensaje=proceso_dict.get("mensaje", ""),
            ticket_id=proceso_dict.get("ticket_id"),
            numero_orden=proceso_dict.get("numero_orden"),
            comprobantes_procesados=proceso_dict.get("comprobantes_enviados", 0),
            comprobantes_aceptados=proceso_dict.get("comprobantes_aceptados", 0),
            comprobantes_rechazados=proceso_dict.get("comprobantes_rechazados", 0),
            total_credito_fiscal=Decimal(str(proceso_dict.get("total_credito_fiscal", 0))),
            total_importe_procesado=Decimal(str(proceso_dict.get("total_importe_enviado", 0))),
            fecha_inicio=proceso_dict["fecha_inicio"],
            fecha_fin=proceso_dict.get("fecha_fin"),
            tiempo_procesamiento_segundos=tiempo_procesamiento,
            errores_criticos=proceso_dict.get("errores_criticos", []),
            archivos_respuesta=proceso_dict.get("archivos_respuesta", [])
        )
    
    def _convertir_ticket_a_response(self, ticket_dict: Dict[str, Any]) -> RceTicketResponse:
        """Convertir diccionario de MongoDB a RceTicketResponse"""
        return RceTicketResponse(
            ticket_id=ticket_dict["ticket_id"],
            estado=ticket_dict["estado"],
            descripcion_estado=ticket_dict.get("descripcion_estado"),
            porcentaje_avance=ticket_dict.get("porcentaje_avance"),
            fecha_inicio=ticket_dict.get("fecha_solicitud"),
            fecha_estimada_fin=ticket_dict.get("fecha_estimada_fin"),
            fecha_vencimiento=ticket_dict.get("fecha_vencimiento"),
            resultados_disponibles=ticket_dict.get("resultados_disponibles", False),
            archivos_disponibles=ticket_dict.get("archivos_disponibles", []),
            url_descarga=ticket_dict.get("url_descarga"),
            comprobantes_procesados=ticket_dict.get("comprobantes_procesados"),
            errores_encontrados=ticket_dict.get("errores_encontrados"),
            mensaje_usuario=ticket_dict.get("mensaje_usuario"),
            observaciones=ticket_dict.get("observaciones")
        )
