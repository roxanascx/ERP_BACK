"""
Servicios de lógica de negocio para Socios de Negocio
Integración con módulo consultasapi para consultas RUC/DNI
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging

from .models import SocioNegocioModel
from .schemas import (
    SocioNegocioCreate, SocioNegocioUpdate, SocioNegocioResponse,
    ConsultaRucResponse, SocioListResponse, SocioStatsResponse
)
from .repositories import SocioNegocioRepository
from .exceptions import (
    SocioNotFoundException, SocioAlreadyExistsException,
    SocioValidationException, RucConsultaException
)
from .utils.ruc_validator import validar_documento

# ✅ IMPORTAR SERVICIOS DEL MÓDULO CONSULTASAPI
from ..consultasapi.services import SunatService, ReniecService

logger = logging.getLogger(__name__)

class SocioNegocioService:
    """Servicio principal para gestión de socios de negocio con integración consultasapi"""
    
    def __init__(self, repository: SocioNegocioRepository):
        self.repository = repository
        # ✅ USAR SERVICIOS DEL MÓDULO CONSULTASAPI
        self.sunat_service = SunatService()
        self.reniec_service = ReniecService()
    
    async def create_socio(self, empresa_id: str, socio_data: SocioNegocioCreate) -> SocioNegocioResponse:
        """
        Crea un nuevo socio de negocio
        
        Args:
            empresa_id: ID de la empresa
            socio_data: Datos del socio a crear
            
        Returns:
            SocioNegocioResponse: Socio creado
            
        Raises:
            SocioValidationException: Si los datos no son válidos
            SocioAlreadyExistsException: Si ya existe el socio
        """
        try:
            logger.info(f"Creando socio para empresa {empresa_id}: {socio_data.numero_documento}")
            
            # Validar documento
            es_valido, mensaje = validar_documento(socio_data.tipo_documento, socio_data.numero_documento)
            if not es_valido:
                raise SocioValidationException(f"Documento inválido: {mensaje}")
            
            # Crear modelo
            socio = SocioNegocioModel(
                **socio_data.model_dump(),
                empresa_id=empresa_id,
                requiere_actualizacion=socio_data.tipo_documento == 'RUC'  # Solo RUC requiere sync con SUNAT
            )
            
            # Guardar en repositorio
            socio_id = await self.repository.create(socio)
            
            # Obtener socio creado
            socio_creado = await self.repository.get_by_id(socio_id)
            if not socio_creado:
                raise Exception("Error recuperando socio creado")
            
            logger.info(f"Socio creado exitosamente: {socio_id}")
            return self._model_to_response(socio_creado)
            
        except (SocioValidationException, SocioAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(f"Error creando socio: {str(e)}")
            raise Exception(f"Error interno creando socio: {str(e)}")
    
    async def get_socio(self, socio_id: str) -> SocioNegocioResponse:
        """
        Obtiene un socio por ID
        
        Args:
            socio_id: ID del socio
            
        Returns:
            SocioNegocioResponse: Datos del socio
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
        """
        try:
            socio = await self.repository.get_by_id(socio_id)
            if not socio:
                raise SocioNotFoundException(f"Socio no encontrado: {socio_id}")
            
            return self._model_to_response(socio)
            
        except SocioNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo socio {socio_id}: {str(e)}")
            raise Exception(f"Error interno obteniendo socio: {str(e)}")
    
    async def update_socio(self, socio_id: str, update_data: SocioNegocioUpdate) -> SocioNegocioResponse:
        """
        Actualiza un socio de negocio
        
        Args:
            socio_id: ID del socio
            update_data: Datos a actualizar
            
        Returns:
            SocioNegocioResponse: Socio actualizado
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
        """
        try:
            logger.info(f"Actualizando socio: {socio_id}")
            
            # Preparar datos de actualización (solo campos no None)
            update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
            
            if not update_dict:
                # Si no hay datos para actualizar, solo devolver el socio actual
                return await self.get_socio(socio_id)
            
            # Actualizar en repositorio
            await self.repository.update(socio_id, update_dict)
            
            # Obtener socio actualizado
            socio_actualizado = await self.repository.get_by_id(socio_id)
            if not socio_actualizado:
                raise SocioNotFoundException(f"Socio no encontrado después de actualizar: {socio_id}")
            
            logger.info(f"Socio actualizado exitosamente: {socio_id}")
            return self._model_to_response(socio_actualizado)
            
        except SocioNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error actualizando socio {socio_id}: {str(e)}")
            raise Exception(f"Error interno actualizando socio: {str(e)}")
    
    async def delete_socio(self, socio_id: str) -> bool:
        """
        Elimina (desactiva) un socio de negocio
        
        Args:
            socio_id: ID del socio
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
        """
        try:
            logger.info(f"Eliminando socio: {socio_id}")
            
            result = await self.repository.delete(socio_id)
            
            logger.info(f"Socio eliminado: {socio_id}")
            return result
            
        except SocioNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error eliminando socio {socio_id}: {str(e)}")
            raise Exception(f"Error interno eliminando socio: {str(e)}")
    
    async def list_socios(
        self, 
        empresa_id: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
        offset: int = 0
    ) -> SocioListResponse:
        """
        Lista socios de una empresa con filtros y paginación
        
        Args:
            empresa_id: ID de la empresa
            filters: Filtros opcionales
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            SocioListResponse: Lista paginada de socios
        """
        try:
            logger.debug(f"Listando socios para empresa {empresa_id}")
            
            # Obtener socios
            socios = await self.repository.list_by_empresa(empresa_id, filters, limit, offset)
            
            # Obtener total
            total = await self.repository.count_by_empresa(empresa_id, filters)
            
            # Convertir a respuestas
            socios_response = [self._model_to_response(socio) for socio in socios]
            
            return SocioListResponse(
                socios=socios_response,
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(socios) < total
            )
            
        except Exception as e:
            logger.error(f"Error listando socios para empresa {empresa_id}: {str(e)}")
            raise Exception(f"Error interno listando socios: {str(e)}")
    
    async def search_socios(
        self,
        empresa_id: str,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
        offset: int = 0
    ) -> SocioListResponse:
        """
        Busca socios por texto
        
        Args:
            empresa_id: ID de la empresa
            query: Texto a buscar
            filters: Filtros adicionales
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            SocioListResponse: Resultados de búsqueda
        """
        try:
            logger.debug(f"Buscando socios en empresa {empresa_id} con query: {query}")
            
            # Realizar búsqueda
            socios = await self.repository.search(empresa_id, query, filters, limit, offset)
            
            # Para el total en búsquedas, usamos el número de resultados obtenidos
            # En una implementación más completa, se haría una consulta separada de count
            total = len(socios)
            
            # Convertir a respuestas
            socios_response = [self._model_to_response(socio) for socio in socios]
            
            return SocioListResponse(
                socios=socios_response,
                total=total,
                limit=limit,
                offset=offset,
                has_more=len(socios) == limit  # Heurística simple
            )
            
        except Exception as e:
            logger.error(f"Error buscando socios: {str(e)}")
            raise Exception(f"Error interno en búsqueda: {str(e)}")
    
    async def get_stats(self, empresa_id: str) -> SocioStatsResponse:
        """
        Obtiene estadísticas de socios para una empresa
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            SocioStatsResponse: Estadísticas de socios
        """
        try:
            logger.debug(f"Obteniendo estadísticas para empresa {empresa_id}")
            
            stats = await self.repository.get_stats_by_empresa(empresa_id)
            
            return SocioStatsResponse(**stats)
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas para empresa {empresa_id}: {str(e)}")
            raise Exception(f"Error interno obteniendo estadísticas: {str(e)}")
    
    async def consultar_ruc(self, ruc: str) -> ConsultaRucResponse:
        """
        Consulta un RUC usando el módulo consultasapi
        
        Args:
            ruc: RUC a consultar
            
        Returns:
            ConsultaRucResponse: Resultado de la consulta
            
        Raises:
            RucConsultaException: Si no se puede realizar la consulta
        """
        try:
            logger.info(f"🔍 [CONSULTA-RUC] Consultando RUC usando consultasapi: {ruc}")
            
            # ✅ USAR SERVICIO CONSULTASAPI
            resultado_consulta = await self.sunat_service.consultar_ruc(ruc)
            
            if resultado_consulta.success and resultado_consulta.data:
                logger.info(f"✅ [CONSULTA-RUC] Éxito para RUC: {ruc}")
                
                # Convertir datos del consultasapi al formato esperado por socios_negocio
                from .schemas import DatosSunatResponse
                datos_sunat = DatosSunatResponse(
                    ruc=resultado_consulta.data.ruc,
                    razon_social=resultado_consulta.data.razon_social,
                    nombre_comercial=resultado_consulta.data.nombre_comercial or '',
                    tipo_contribuyente=resultado_consulta.data.tipo_empresa or '',
                    estado_contribuyente=resultado_consulta.data.estado,
                    condicion_contribuyente='HABIDO',  # Por defecto
                    domicilio_fiscal=resultado_consulta.data.direccion or '',
                    actividad_economica=resultado_consulta.data.actividad_economica or '',
                    fecha_inscripcion=resultado_consulta.data.fecha_inscripcion or '',
                    ubigeo=resultado_consulta.data.ubigeo or ''
                )
                
                return ConsultaRucResponse(
                    success=True,
                    ruc=ruc,
                    data=datos_sunat,
                    timestamp=datetime.utcnow(),
                    metodo=resultado_consulta.fuente or 'CONSULTASAPI'
                )
            else:
                # Error en consulta
                logger.error(f"❌ [CONSULTA-RUC] Falló para RUC: {ruc} - {resultado_consulta.message}")
                raise RucConsultaException(f"Error en consulta: {resultado_consulta.message}")
                        
        except Exception as e:
            logger.error(f"❌ [CONSULTA-RUC] Error para RUC {ruc}: {e}")
            raise RucConsultaException(f"Error en consulta: {e}")
    
    async def consultar_dni(self, dni: str) -> Dict[str, Any]:
        """
        Consulta un DNI usando el módulo consultasapi
        
        Args:
            dni: DNI a consultar
            
        Returns:
            Dict[str, Any]: Resultado de la consulta DNI
        """
        try:
            logger.info(f"🔍 [CONSULTA-DNI] Consultando DNI usando consultasapi: {dni}")
            
            # ✅ USAR SERVICIO CONSULTASAPI RENIEC
            resultado_consulta = await self.reniec_service.consultar_dni(dni)
            
            if resultado_consulta.success and resultado_consulta.data:
                logger.info(f"✅ [CONSULTA-DNI] Éxito para DNI: {dni}")
                
                return {
                    "success": True,
                    "data": {
                        "dni": resultado_consulta.data.dni,
                        "nombres": resultado_consulta.data.nombres,
                        "apellido_paterno": resultado_consulta.data.apellido_paterno,
                        "apellido_materno": resultado_consulta.data.apellido_materno,
                        "apellidos": resultado_consulta.data.apellidos,
                        "fecha_nacimiento": resultado_consulta.data.fecha_nacimiento,
                        "estado_civil": resultado_consulta.data.estado_civil,
                        "direccion": resultado_consulta.data.direccion,
                        "ubigeo": resultado_consulta.data.ubigeo
                    },
                    "message": resultado_consulta.message,
                    "fuente": resultado_consulta.fuente
                }
            else:
                logger.warning(f"⚠️ [CONSULTA-DNI] No se encontraron datos para DNI: {dni}")
                return {
                    "success": False,
                    "data": None,
                    "message": resultado_consulta.message,
                    "fuente": None
                }
                        
        except Exception as e:
            logger.error(f"❌ [CONSULTA-DNI] Error para DNI {dni}: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"Error en consulta DNI: {e}",
                "fuente": None
            }
    
    async def create_socio_from_ruc(self, empresa_id: str, ruc: str, tipo_socio: str) -> SocioNegocioResponse:
        """
        Crea un socio automáticamente desde una consulta RUC
        
        Args:
            empresa_id: ID de la empresa
            ruc: RUC a consultar y crear
            tipo_socio: Tipo de socio (proveedor, cliente, ambos)
            
        Returns:
            SocioNegocioResponse: Socio creado
            
        Raises:
            RucConsultaException: Si no se puede consultar el RUC
            SocioAlreadyExistsException: Si ya existe el socio
        """
        try:
            logger.info(f"Creando socio desde RUC: {ruc}")
            
            # Consultar RUC en SUNAT
            consulta_result = await self.consultar_ruc(ruc)
            
            if not consulta_result.success or not consulta_result.data:
                raise RucConsultaException(f"No se pudo consultar el RUC: {consulta_result.error}")
            
            datos_sunat = consulta_result.data
            
            # Crear datos del socio con información de SUNAT
            socio_data = SocioNegocioCreate(
                tipo_documento="RUC",
                numero_documento=ruc,
                razon_social=datos_sunat.razon_social,
                nombre_comercial=datos_sunat.nombre_comercial or None,
                tipo_socio=tipo_socio,
                direccion=datos_sunat.domicilio_fiscal or None
            )
            
            # Crear socio
            socio_response = await self.create_socio(empresa_id, socio_data)
            
            # Marcar como sincronizado con SUNAT
            await self.repository.mark_as_synced(
                socio_response.id,
                datos_sunat.model_dump()
            )
            
            # Obtener socio actualizado
            socio_final = await self.repository.get_by_id(socio_response.id)
            
            logger.info(f"Socio creado desde RUC exitosamente: {socio_response.id}")
            return self._model_to_response(socio_final)
            
        except (RucConsultaException, SocioAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(f"Error creando socio desde RUC {ruc}: {str(e)}")
            raise Exception(f"Error interno creando socio desde RUC: {str(e)}")
    
    async def sync_socio_with_sunat(self, socio_id: str) -> SocioNegocioResponse:
        """
        Sincroniza un socio con datos de SUNAT
        
        Args:
            socio_id: ID del socio
            
        Returns:
            SocioNegocioResponse: Socio actualizado
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
            RucConsultaException: Si no se puede consultar SUNAT
        """
        try:
            logger.info(f"Sincronizando socio con SUNAT: {socio_id}")
            
            # Obtener socio
            socio = await self.repository.get_by_id(socio_id)
            if not socio:
                raise SocioNotFoundException(f"Socio no encontrado: {socio_id}")
            
            # Solo sincronizar RUCs
            if socio.tipo_documento != 'RUC':
                raise SocioValidationException("Solo se pueden sincronizar socios con RUC")
            
            # Consultar SUNAT
            consulta_result = await self.consultar_ruc(socio.numero_documento)
            
            if not consulta_result.success or not consulta_result.data:
                raise RucConsultaException(f"No se pudo consultar SUNAT: {consulta_result.error}")
            
            # Marcar como sincronizado
            await self.repository.mark_as_synced(
                socio_id,
                consulta_result.data.model_dump()
            )
            
            # Obtener socio actualizado
            socio_actualizado = await self.repository.get_by_id(socio_id)
            
            logger.info(f"Socio sincronizado exitosamente: {socio_id}")
            return self._model_to_response(socio_actualizado)
            
        except (SocioNotFoundException, RucConsultaException, SocioValidationException):
            raise
        except Exception as e:
            logger.error(f"Error sincronizando socio {socio_id}: {str(e)}")
            raise Exception(f"Error interno sincronizando socio: {str(e)}")
    
    def _model_to_response(self, socio: SocioNegocioModel) -> SocioNegocioResponse:
        """Convierte un modelo a respuesta"""
        return SocioNegocioResponse(**socio.model_dump())
