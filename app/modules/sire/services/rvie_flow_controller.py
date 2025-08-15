"""
Controlador de flujo RVIE - Secuencia completa según Manual SUNAT v25

SECUENCIA OFICIAL PARA REGISTRO PRELIMINAR:
1. Autenticarse con credenciales SUNAT
2. Descargar propuesta SUNAT 
3. Aceptar propuesta (Funcionalidad 1)
4. Registrar preliminar (paso final)

SERVICIOS COMPLEMENTARIOS:
- Reemplazar propuesta (Funcionalidad 2) 
- Consultar inconsistencias
- Descargar resumen
"""

import asyncio
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
import logging

from fastapi import HTTPException
from ..models.rvie import RviePropuesta, RvieEstadoProceso, RvieProcesoResult
from ..models.responses import SireApiResponse
from ..utils.exceptions import SireException, SireApiException, SireValidationException
from .rvie_descarga_service import RvieDescargaService
from .api_client import SunatApiClient
from .token_manager import SireTokenManager

logger = logging.getLogger(__name__)


class RvieFlowController:
    """
    Controlador de flujo completo RVIE
    Implementa secuencia oficial según Manual SUNAT v25
    """
    
    def __init__(self, api_client: SunatApiClient, token_manager: SireTokenManager, database=None):
        """
        Inicializar controlador de flujo RVIE
        
        Args:
            api_client: Cliente API para comunicación con SUNAT
            token_manager: Gestor de tokens JWT
            database: Conexión a MongoDB (opcional)
        """
        self.api_client = api_client
        self.token_manager = token_manager
        self.database = database
        
        # Servicios especializados
        self.descarga_service = RvieDescargaService(api_client, token_manager, database)
        
        # Estados válidos para cada operación según Manual v25
        self.ESTADOS_VALIDOS = {
            "descargar_propuesta": [RvieEstadoProceso.PENDIENTE],
            "aceptar_propuesta": [RvieEstadoProceso.PROPUESTA],
            "reemplazar_propuesta": [RvieEstadoProceso.PROPUESTA],
            "registrar_preliminar": [RvieEstadoProceso.ACEPTADO]
        }
    
    async def ejecutar_flujo_completo_preliminar(
        self, 
        ruc: str, 
        periodo: str,
        auto_aceptar: bool = True,
        incluir_detalle: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecutar flujo completo para registrar preliminar RVIE
        
        SECUENCIA SEGÚN MANUAL v25:
        1. Validar prerrequisitos
        2. Descargar propuesta SUNAT
        3. Aceptar propuesta (si auto_aceptar=True)
        4. Preparar para registro preliminar
        
        Args:
            ruc: RUC del contribuyente
            periodo: Período en formato YYYYMM
            auto_aceptar: True para aceptar automáticamente la propuesta
            incluir_detalle: True para incluir detalle completo
        
        Returns:
            Dict con resultado del flujo completo
        
        Raises:
            SireException: Error en el flujo
        """
        try:
            inicio_flujo = datetime.utcnow()
            logger.info(f"🚀 [RVIE-FLOW] Iniciando flujo completo preliminar RUC {ruc}, período {periodo}")
            
            resultado = {
                "ruc": ruc,
                "periodo": periodo,
                "timestamp_inicio": inicio_flujo.isoformat(),
                "pasos_ejecutados": [],
                "estado_final": None,
                "propuesta": None,
                "errores": []
            }
            
            # PASO 1: VALIDAR PRERREQUISITOS
            await self._validar_prerrequisitos_flujo(ruc, periodo)
            resultado["pasos_ejecutados"].append({
                "paso": "validar_prerrequisitos",
                "estado": "completado",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # PASO 2: DESCARGAR PROPUESTA
            logger.info(f"📥 [RVIE-FLOW] Paso 2: Descargando propuesta...")
            try:
                propuesta = await self.descarga_service.descargar_propuesta_completa(
                    ruc=ruc,
                    periodo=periodo,
                    cod_tipo_archivo=0,  # TXT por defecto
                    forzar_descarga=False
                )
                
                resultado["propuesta"] = {
                    "cantidad_comprobantes": propuesta.cantidad_comprobantes,
                    "total_importe": float(propuesta.total_importe),
                    "estado": propuesta.estado.value,
                    "fecha_generacion": propuesta.fecha_generacion.isoformat()
                }
                
                resultado["pasos_ejecutados"].append({
                    "paso": "descargar_propuesta",
                    "estado": "completado",
                    "timestamp": datetime.utcnow().isoformat(),
                    "detalles": {
                        "comprobantes": propuesta.cantidad_comprobantes,
                        "total": float(propuesta.total_importe)
                    }
                })
                
            except Exception as e:
                error_msg = f"Error descargando propuesta: {str(e)}"
                logger.error(f"❌ [RVIE-FLOW] {error_msg}")
                resultado["errores"].append(error_msg)
                resultado["pasos_ejecutados"].append({
                    "paso": "descargar_propuesta",
                    "estado": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": error_msg
                })
                raise SireException(error_msg)
            
            # PASO 3: ACEPTAR PROPUESTA (si está habilitado)
            if auto_aceptar and propuesta.estado == RvieEstadoProceso.PROPUESTA:
                logger.info(f"✅ [RVIE-FLOW] Paso 3: Aceptando propuesta automáticamente...")
                try:
                    resultado_aceptacion = await self.aceptar_propuesta_sunat(
                        ruc=ruc,
                        periodo=periodo,
                        acepta_completa=True,
                        observaciones="Aceptación automática del flujo ERP"
                    )
                    
                    resultado["pasos_ejecutados"].append({
                        "paso": "aceptar_propuesta",
                        "estado": "completado",
                        "timestamp": datetime.utcnow().isoformat(),
                        "detalles": resultado_aceptacion
                    })
                    
                    # Actualizar estado de la propuesta
                    propuesta.estado = RvieEstadoProceso.ACEPTADO
                    propuesta.fecha_aceptacion = datetime.utcnow()
                    
                except Exception as e:
                    error_msg = f"Error aceptando propuesta: {str(e)}"
                    logger.warning(f"⚠️ [RVIE-FLOW] {error_msg}")
                    resultado["errores"].append(error_msg)
                    resultado["pasos_ejecutados"].append({
                        "paso": "aceptar_propuesta",
                        "estado": "error",
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": error_msg
                    })
                    # No es crítico, continuar con flujo
            
            # PASO 4: PREPARAR PARA REGISTRO PRELIMINAR
            logger.info(f"📋 [RVIE-FLOW] Paso 4: Preparando registro preliminar...")
            
            estado_preliminar = await self._preparar_registro_preliminar(ruc, periodo, propuesta)
            resultado["pasos_ejecutados"].append({
                "paso": "preparar_preliminar",
                "estado": "completado",
                "timestamp": datetime.utcnow().isoformat(),
                "detalles": estado_preliminar
            })
            
            # RESULTADO FINAL
            tiempo_total = (datetime.utcnow() - inicio_flujo).total_seconds()
            resultado.update({
                "estado_final": "LISTO_PARA_PRELIMINAR",
                "tiempo_total_segundos": tiempo_total,
                "timestamp_fin": datetime.utcnow().isoformat(),
                "siguiente_paso": "Ejecutar registro preliminar cuando esté listo"
            })
            
            logger.info(
                f"✅ [RVIE-FLOW] Flujo completado exitosamente en {tiempo_total:.2f}s. "
                f"Estado: {resultado['estado_final']}"
            )
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ [RVIE-FLOW] Error en flujo completo: {e}")
            resultado["estado_final"] = "ERROR"
            resultado["timestamp_fin"] = datetime.utcnow().isoformat()
            raise SireException(f"Error en flujo completo RVIE: {str(e)}")
    
    async def aceptar_propuesta_sunat(
        self, 
        ruc: str, 
        periodo: str,
        acepta_completa: bool = True,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aceptar propuesta RVIE en SUNAT
        Implementa Funcionalidad 1 según Manual v25
        
        Args:
            ruc: RUC del contribuyente
            periodo: Período YYYYMM
            acepta_completa: True para aceptación completa
            observaciones: Observaciones opcionales
        
        Returns:
            Dict con resultado de la aceptación
        """
        try:
            logger.info(f"✅ [RVIE-FLOW] Aceptando propuesta RUC {ruc}, período {periodo}")
            
            # Validar estado actual
            await self._validar_estado_para_operacion(ruc, periodo, "aceptar_propuesta")
            
            # Obtener token activo
            token = await self.token_manager.get_active_session_token(ruc)
            if not token:
                raise SireException("No hay sesión activa. Debe autenticarse primero.")
            
            # Preparar datos según especificación SUNAT
            data = {
                "periodo": periodo,
                "acepta": "S" if acepta_completa else "N",
                "observaciones": observaciones or ""
            }
            
            # Realizar petición a SUNAT
            endpoint_url = self.api_client.endpoints["rvie_aceptar_propuesta"]
            
            response = await self.api_client._make_request(
                method="POST",
                url=f"{self.api_client.base_url}{endpoint_url}",
                data=data,
                token=token
            )
            
            response_data = response.json()
            
            # Procesar respuesta
            resultado = {
                "estado": "aceptado",
                "mensaje": response_data.get("mensaje", "Propuesta aceptada exitosamente"),
                "fecha_aceptacion": datetime.utcnow().isoformat(),
                "acepta_completa": acepta_completa,
                "observaciones": observaciones
            }
            
            # Actualizar estado en base de datos
            await self._actualizar_estado_proceso(ruc, periodo, RvieEstadoProceso.ACEPTADO)
            
            logger.info(f"✅ [RVIE-FLOW] Propuesta aceptada exitosamente")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ [RVIE-FLOW] Error aceptando propuesta: {e}")
            raise SireException(f"Error aceptando propuesta: {str(e)}")
    
    async def obtener_estado_proceso_rvie(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """
        Obtener estado actual del proceso RVIE
        
        Args:
            ruc: RUC del contribuyente
            periodo: Período YYYYMM
        
        Returns:
            Dict con estado detallado del proceso
        """
        try:
            if not self.database:
                return {
                    "ruc": ruc,
                    "periodo": periodo,
                    "estado": "DESCONOCIDO",
                    "mensaje": "No hay conexión a base de datos"
                }
            
            # Buscar propuesta en BD
            collection = self.database.rvie_propuestas
            propuesta_doc = await collection.find_one({
                "ruc": ruc,
                "periodo": periodo
            })
            
            if not propuesta_doc:
                return {
                    "ruc": ruc,
                    "periodo": periodo,
                    "estado": "NO_INICIADO",
                    "mensaje": "No se ha descargado propuesta para este período",
                    "siguiente_accion": "Descargar propuesta"
                }
            
            # Determinar siguiente acción según estado
            estado = propuesta_doc.get("estado", "DESCONOCIDO")
            siguiente_accion = self._determinar_siguiente_accion(estado)
            
            return {
                "ruc": ruc,
                "periodo": periodo,
                "estado": estado,
                "cantidad_comprobantes": propuesta_doc.get("cantidad_comprobantes", 0),
                "total_importe": propuesta_doc.get("total_importe", 0),
                "fecha_generacion": propuesta_doc.get("fecha_generacion"),
                "fecha_aceptacion": propuesta_doc.get("fecha_aceptacion"),
                "ticket_id": propuesta_doc.get("ticket_id"),
                "siguiente_accion": siguiente_accion
            }
            
        except Exception as e:
            logger.error(f"❌ [RVIE-FLOW] Error obteniendo estado: {e}")
            return {
                "ruc": ruc,
                "periodo": periodo,
                "estado": "ERROR",
                "mensaje": f"Error consultando estado: {str(e)}"
            }
    
    def _determinar_siguiente_accion(self, estado: str) -> str:
        """Determinar la siguiente acción según el estado actual"""
        acciones = {
            "PENDIENTE": "Descargar propuesta",
            "PROPUESTA": "Aceptar o reemplazar propuesta",
            "ACEPTADO": "Registrar preliminar",
            "PRELIMINAR": "Proceso completado",
            "FINALIZADO": "Proceso completado",
            "ERROR": "Revisar errores y reiniciar"
        }
        
        return acciones.get(estado, "Acción no definida")
    
    async def _validar_prerrequisitos_flujo(self, ruc: str, periodo: str) -> None:
        """Validar prerrequisitos para el flujo completo"""
        
        # Validar formato de parámetros
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise SireValidationException("RUC debe tener 11 dígitos numéricos")
        
        if not periodo or len(periodo) != 6 or not periodo.isdigit():
            raise SireValidationException("Período debe tener formato YYYYMM")
        
        # Validar que hay sesión activa
        token = await self.token_manager.get_active_session_token(ruc)
        if not token:
            raise SireException(
                "No hay sesión activa para SUNAT. Debe autenticarse primero "
                "usando el endpoint /api/v1/sire/auth/login"
            )
        
        # Validar que el período no sea futuro
        try:
            periodo_date = datetime.strptime(periodo + "01", "%Y%m%d").date()
            if periodo_date > date.today().replace(day=1):
                raise SireValidationException("No se puede procesar período futuro")
        except ValueError:
            raise SireValidationException("Formato de período inválido")
        
        logger.info(f"✅ [RVIE-FLOW] Prerrequisitos validados correctamente")
    
    async def _validar_estado_para_operacion(
        self, 
        ruc: str, 
        periodo: str, 
        operacion: str
    ) -> None:
        """Validar que el estado actual permite la operación solicitada"""
        
        if operacion not in self.ESTADOS_VALIDOS:
            raise SireValidationException(f"Operación no válida: {operacion}")
        
        estado_actual = await self._obtener_estado_actual(ruc, periodo)
        estados_validos = self.ESTADOS_VALIDOS[operacion]
        
        if estado_actual not in estados_validos:
            raise SireValidationException(
                f"No se puede ejecutar {operacion} en estado {estado_actual}. "
                f"Estados válidos: {', '.join(estados_validos)}"
            )
    
    async def _obtener_estado_actual(self, ruc: str, periodo: str) -> RvieEstadoProceso:
        """Obtener el estado actual del proceso"""
        
        if not self.database:
            return RvieEstadoProceso.PENDIENTE
        
        try:
            collection = self.database.rvie_propuestas
            doc = await collection.find_one({
                "ruc": ruc,
                "periodo": periodo
            })
            
            if doc:
                return RvieEstadoProceso(doc.get("estado", "PENDIENTE"))
            else:
                return RvieEstadoProceso.PENDIENTE
                
        except Exception as e:
            logger.warning(f"⚠️ Error obteniendo estado actual: {e}")
            return RvieEstadoProceso.PENDIENTE
    
    async def _actualizar_estado_proceso(
        self, 
        ruc: str, 
        periodo: str, 
        nuevo_estado: RvieEstadoProceso
    ) -> None:
        """Actualizar estado del proceso en base de datos"""
        
        if not self.database:
            logger.warning("⚠️ No hay conexión a BD, no se puede actualizar estado")
            return
        
        try:
            collection = self.database.rvie_propuestas
            await collection.update_one(
                {"ruc": ruc, "periodo": periodo},
                {
                    "$set": {
                        "estado": nuevo_estado.value,
                        "fecha_actualizacion": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"📝 [RVIE-FLOW] Estado actualizado a {nuevo_estado.value}")
        except Exception as e:
            logger.error(f"❌ Error actualizando estado: {e}")
    
    async def _preparar_registro_preliminar(
        self, 
        ruc: str, 
        periodo: str, 
        propuesta: RviePropuesta
    ) -> Dict[str, Any]:
        """Preparar datos para el registro preliminar"""
        
        # Validar que la propuesta está en estado correcto
        if propuesta.estado not in [RvieEstadoProceso.PROPUESTA, RvieEstadoProceso.ACEPTADO]:
            logger.warning(f"⚠️ Propuesta en estado {propuesta.estado}, puede no estar lista para preliminar")
        
        # Preparar resumen de datos
        estado_preliminar = {
            "listo_para_preliminar": propuesta.estado == RvieEstadoProceso.ACEPTADO,
            "total_comprobantes": propuesta.cantidad_comprobantes,
            "total_importe": float(propuesta.total_importe),
            "validaciones_pendientes": [],
            "siguiente_servicio": "Registrar preliminar (5.8 Servicio Web Api aceptar propuesta del RVIE)"
        }
        
        # Realizar validaciones adicionales
        if propuesta.cantidad_comprobantes == 0:
            estado_preliminar["validaciones_pendientes"].append(
                "No hay comprobantes en la propuesta"
            )
        
        if propuesta.total_importe <= 0:
            estado_preliminar["validaciones_pendientes"].append(
                "Importe total es cero o negativo"
            )
        
        return estado_preliminar
