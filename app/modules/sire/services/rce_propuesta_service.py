"""
RCE Propuesta Service - Gestión de propuestas RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..models.rce import (
    RcePropuesta, RceComprobante, RceEstadoProceso, 
    RceInconsistencia, RceTipoComprobante
)
from ..schemas.rce_schemas import (
    RcePropuestaGenerarRequest, RcePropuestaResponse,
    RceComprobanteCreateRequest, RceApiResponse
)
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ....shared.exceptions import SireException, SireValidationException


class RcePropuestaService:
    """Servicio para gestión de propuestas RCE"""
    
    def __init__(
        self, 
        database: AsyncIOMotorDatabase, 
        api_client: SunatApiClient, 
        auth_service: SireAuthService,
        compras_service: RceComprasService
    ):
        self.db = database
        self.api_client = api_client
        self.auth_service = auth_service
        self.compras_service = compras_service
        self.collection = database.rce_propuestas
        
    async def generar_propuesta(
        self,
        ruc: str,
        request: RcePropuestaGenerarRequest
    ) -> RcePropuestaResponse:
        """
        Generar una nueva propuesta RCE
        
        Args:
            ruc: RUC del contribuyente
            request: Datos para generar la propuesta
            
        Returns:
            RcePropuestaResponse: Propuesta generada
            
        Raises:
            SireException: Si hay error en la generación
        """
        try:
            # Validar que no exista propuesta activa para el periodo
            await self._validar_propuesta_existente(ruc, request.periodo)
            
            # Validar comprobantes en lote
            comprobantes_validos, inconsistencias = await self.compras_service.validar_comprobantes_lote(
                ruc, request.comprobantes
            )
            
            if not comprobantes_validos:
                raise SireValidationException("No hay comprobantes válidos para generar la propuesta")
            
            # Crear modelos de comprobantes
            comprobantes_models = []
            for comp_request in comprobantes_validos:
                comprobante = await self.compras_service._crear_modelo_comprobante(ruc, comp_request)
                comprobantes_models.append(comprobante)
            
            # Calcular totales de la propuesta
            totales = self._calcular_totales_propuesta(comprobantes_models)
            
            # Crear propuesta
            propuesta = RcePropuesta(
                ruc=ruc,
                periodo=request.periodo,
                estado=RceEstadoProceso.PROPUESTA,
                fecha_generacion=datetime.utcnow(),
                correlativo_propuesta=self._generar_correlativo_propuesta(),
                cantidad_comprobantes=len(comprobantes_models),
                **totales,
                comprobantes=comprobantes_models
            )
            
            # Guardar en base de datos
            resultado = await self.collection.insert_one(propuesta.dict())
            
            # Recuperar propuesta creada
            propuesta_creada = await self.collection.find_one({"_id": resultado.inserted_id})
            
            return self._convertir_a_response(propuesta_creada, inconsistencias)
            
        except Exception as e:
            raise SireException(f"Error generando propuesta: {str(e)}")
    
    async def enviar_propuesta_sunat(
        self,
        ruc: str,
        periodo: str,
        usuario_sunat: str,
        clave_sunat: str
    ) -> RcePropuestaResponse:
        """
        Enviar propuesta a SUNAT
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo de la propuesta
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            
        Returns:
            RcePropuestaResponse: Propuesta con estado actualizado
        """
        try:
            # Obtener propuesta local
            propuesta = await self._obtener_propuesta(ruc, periodo)
            
            if not propuesta:
                raise SireException("Propuesta no encontrada")
            
            if propuesta["estado"] != RceEstadoProceso.PROPUESTA:
                raise SireException(f"La propuesta debe estar en estado PROPUESTA, actual: {propuesta['estado']}")
            
            # Autenticar con SUNAT
            token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
            
            # Preparar datos para SUNAT
            datos_envio = self._preparar_datos_envio_sunat(propuesta)
            
            # Enviar a SUNAT
            respuesta_sunat = await self.api_client.rce_propuesta_generar(token.access_token, datos_envio)
            
            # Actualizar propuesta con respuesta de SUNAT
            await self._actualizar_propuesta_con_respuesta_sunat(ruc, periodo, respuesta_sunat)
            
            # Recuperar propuesta actualizada
            propuesta_actualizada = await self._obtener_propuesta(ruc, periodo)
            
            return self._convertir_a_response(propuesta_actualizada)
            
        except Exception as e:
            # Marcar propuesta como error
            await self._marcar_propuesta_error(ruc, periodo, str(e))
            raise SireException(f"Error enviando propuesta a SUNAT: {str(e)}")
    
    async def consultar_propuesta(
        self,
        ruc: str,
        periodo: str
    ) -> Optional[RcePropuestaResponse]:
        """
        Consultar una propuesta específica
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo de la propuesta
            
        Returns:
            RcePropuestaResponse: Propuesta encontrada o None
        """
        try:
            propuesta = await self._obtener_propuesta(ruc, periodo)
            
            if not propuesta:
                return None
            
            return self._convertir_a_response(propuesta)
            
        except Exception as e:
            raise SireException(f"Error consultando propuesta: {str(e)}")
    
    async def actualizar_propuesta(
        self,
        ruc: str,
        periodo: str,
        request: RcePropuestaGenerarRequest
    ) -> RcePropuestaResponse:
        """
        Actualizar una propuesta existente (solo si está en estado PROPUESTA)
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo de la propuesta
            request: Nuevos datos de la propuesta
            
        Returns:
            RcePropuestaResponse: Propuesta actualizada
        """
        try:
            # Verificar que la propuesta existe y está en estado modificable
            propuesta_existente = await self._obtener_propuesta(ruc, periodo)
            
            if not propuesta_existente:
                raise SireException("Propuesta no encontrada")
            
            if propuesta_existente["estado"] not in [RceEstadoProceso.PROPUESTA, RceEstadoProceso.ERROR]:
                raise SireException(f"No se puede modificar propuesta en estado: {propuesta_existente['estado']}")
            
            # Validar nuevos comprobantes
            comprobantes_validos, inconsistencias = await self.compras_service.validar_comprobantes_lote(
                ruc, request.comprobantes
            )
            
            if not comprobantes_validos:
                raise SireValidationException("No hay comprobantes válidos para actualizar la propuesta")
            
            # Crear modelos de comprobantes actualizados
            comprobantes_models = []
            for comp_request in comprobantes_validos:
                comprobante = await self.compras_service._crear_modelo_comprobante(ruc, comp_request)
                comprobantes_models.append(comprobante)
            
            # Calcular nuevos totales
            totales = self._calcular_totales_propuesta(comprobantes_models)
            
            # Actualizar propuesta
            update_data = {
                "cantidad_comprobantes": len(comprobantes_models),
                "comprobantes": [comp.dict() for comp in comprobantes_models],
                "fecha_actualizacion": datetime.utcnow(),
                "estado": RceEstadoProceso.PROPUESTA,  # Reset a PROPUESTA si estaba en ERROR
                **totales
            }
            
            await self.collection.update_one(
                {"ruc": ruc, "periodo": periodo},
                {"$set": update_data}
            )
            
            # Recuperar propuesta actualizada
            propuesta_actualizada = await self._obtener_propuesta(ruc, periodo)
            
            return self._convertir_a_response(propuesta_actualizada, inconsistencias)
            
        except Exception as e:
            raise SireException(f"Error actualizando propuesta: {str(e)}")
    
    async def eliminar_propuesta(
        self,
        ruc: str,
        periodo: str
    ) -> bool:
        """
        Eliminar una propuesta (solo si no ha sido enviada a SUNAT)
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo de la propuesta
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            propuesta = await self._obtener_propuesta(ruc, periodo)
            
            if not propuesta:
                raise SireException("Propuesta no encontrada")
            
            if propuesta["estado"] not in [RceEstadoProceso.PROPUESTA, RceEstadoProceso.ERROR]:
                raise SireException(f"No se puede eliminar propuesta en estado: {propuesta['estado']}")
            
            resultado = await self.collection.delete_one({"ruc": ruc, "periodo": periodo})
            
            return resultado.deleted_count > 0
            
        except Exception as e:
            raise SireException(f"Error eliminando propuesta: {str(e)}")
    
    async def listar_propuestas(
        self,
        ruc: str,
        estado: Optional[RceEstadoProceso] = None,
        año: Optional[int] = None,
        limit: int = 50
    ) -> List[RcePropuestaResponse]:
        """
        Listar propuestas del contribuyente consultando SUNAT v27
        
        Args:
            ruc: RUC del contribuyente
            estado: Filtro por estado (opcional)
            año: Filtro por año (opcional)
            limit: Límite de resultados
            
        Returns:
            List[RcePropuestaResponse]: Lista de propuestas
        """
        try:
            # Primero intentar consultar SUNAT v27 (como en tus scripts)
            propuestas_sunat = await self._consultar_propuestas_sunat_v27(ruc, año)
            
            if propuestas_sunat:
                # Si SUNAT devuelve datos, filtrar por estado si es necesario
                if estado:
                    propuestas_sunat = [p for p in propuestas_sunat if p.get('estado') == estado]
                
                return propuestas_sunat[:limit]
            
            # Fallback: consultar base de datos local
            filtros = {"ruc": ruc}
            
            if estado:
                filtros["estado"] = estado
            
            if año:
                periodo_inicio = f"{año}01"
                periodo_fin = f"{año}12"
                filtros["periodo"] = {"$gte": periodo_inicio, "$lte": periodo_fin}
            
            cursor = self.collection.find(filtros).sort("fecha_generacion", -1).limit(limit)
            propuestas = await cursor.to_list(length=limit)
            
            return [self._convertir_a_response(prop) for prop in propuestas]
            
        except Exception as e:
            raise SireException(f"Error listando propuestas: {str(e)}")

    async def _consultar_propuestas_sunat_v27(self, ruc: str, año: Optional[int] = None) -> List[dict]:
        """
        Consultar propuestas directamente desde SUNAT v27 (usando URLs que funcionan)
        """
        try:
            # Obtener token válido desde el token manager
            from .token_manager import SireTokenManager
            token_manager = SireTokenManager()
            token = await token_manager.get_valid_token(ruc)
            
            if not token:
                print(f"⚠️ No hay token válido para {ruc}, consultando solo BD local")
                return []
            
            # Determinar períodos a consultar
            if año:
                periodos = [f"{año}{mes:02d}" for mes in range(1, 13)]
            else:
                # Consultar últimos 3 meses
                from datetime import datetime
                fecha_actual = datetime.now()
                año_actual = fecha_actual.year
                mes_actual = fecha_actual.month
                periodos = []
                for i in range(3):
                    mes = mes_actual - i
                    año_periodo = año_actual
                    if mes <= 0:
                        mes += 12
                        año_periodo -= 1
                    periodos.append(f"{año_periodo}{mes:02d}")
            
            propuestas_encontradas = []
            
            for periodo in periodos:
                try:
                    # Llamar directamente con httpx como en tus scripts funcionales
                    import httpx
                    
                    url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"
                    
                    # Parámetros v27 obligatorios (copiados de tus scripts funcionales)
                    params = {
                        'perIni': periodo,
                        'perFin': periodo,
                        'page': 1,
                        'perPage': 20,
                        'codLibro': '080000',      # ← OBLIGATORIO v27
                        'codOrigenEnvio': '2'      # ← OBLIGATORIO v27
                    }
                    
                    headers = {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                    
                    # Hacer request directo (como en tus scripts)
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        registros = data.get('registros', [])
                        
                        # Filtrar solo procesos de propuestas RCE
                        for registro in registros:
                            if (registro.get('desProceso') == 'Generar archivo exportar propuesta' or
                                registro.get('codProceso') in ['10', '5']):  # Códigos de propuestas
                                
                                propuesta = {
                                    'ticket': registro.get('numTicket'),
                                    'periodo': registro.get('perTributario'),
                                    'estado': self._mapear_estado_sunat(registro.get('desEstadoProceso')),
                                    'fecha_proceso': registro.get('fecInicioProceso'),
                                    'archivos': registro.get('archivoReporte', []),
                                    'detalle': registro.get('detalleTicket', {}),
                                    'proceso_descripcion': registro.get('desProceso'),
                                    'registro_completo': registro
                                }
                                propuestas_encontradas.append(propuesta)
                    else:
                        print(f"⚠️ Error consultando período {periodo}: {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Error consultando período {periodo}: {e}")
                    continue
            
            return propuestas_encontradas
            
        except Exception as e:
            print(f"⚠️ Error consultando SUNAT v27: {e}")
            return []
    
    def _mapear_estado_sunat(self, estado_sunat: str) -> str:
        """Mapear estados de SUNAT a estados internos"""
        mapeo = {
            'Terminado': 'completado',
            'Procesado': 'procesado',
            'Procesado con Errores': 'error',
            'En Proceso': 'en_proceso',
            'Pendiente': 'pendiente'
        }
        return mapeo.get(estado_sunat, 'desconocido')
    
    # =======================================
    # MÉTODOS PRIVADOS
    # =======================================
    
    async def _validar_propuesta_existente(self, ruc: str, periodo: str) -> None:
        """Validar que no exista propuesta activa para el periodo"""
        propuesta_existente = await self.collection.find_one({
            "ruc": ruc,
            "periodo": periodo,
            "estado": {"$in": [RceEstadoProceso.ACEPTADO, RceEstadoProceso.FINALIZADO]}
        })
        
        if propuesta_existente:
            raise SireValidationException(f"Ya existe una propuesta finalizada para el periodo {periodo}")
    
    def _generar_correlativo_propuesta(self) -> str:
        """Generar correlativo único para la propuesta"""
        return f"PROP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
    
    def _calcular_totales_propuesta(self, comprobantes: List[RceComprobante]) -> Dict[str, Decimal]:
        """Calcular totales de la propuesta"""
        totales = {
            "cantidad_facturas": 0,
            "cantidad_boletas": 0,
            "cantidad_notas_credito": 0,
            "cantidad_notas_debito": 0,
            "cantidad_otros": 0,
            "total_base_imponible_gravada": Decimal("0.00"),
            "total_base_imponible_gravada_con_derecho": Decimal("0.00"),
            "total_base_imponible_gravada_sin_derecho": Decimal("0.00"),
            "total_igv": Decimal("0.00"),
            "total_importe": Decimal("0.00"),
            "total_credito_fiscal": Decimal("0.00"),
            "total_detraccion": Decimal("0.00"),
            "total_retencion": Decimal("0.00"),
            "total_percepcion": Decimal("0.00")
        }
        
        for comprobante in comprobantes:
            # Contar por tipo
            if comprobante.tipo_comprobante == RceTipoComprobante.FACTURA:
                totales["cantidad_facturas"] += 1
            elif comprobante.tipo_comprobante == RceTipoComprobante.BOLETA:
                totales["cantidad_boletas"] += 1
            elif comprobante.tipo_comprobante == RceTipoComprobante.NOTA_CREDITO:
                totales["cantidad_notas_credito"] += 1
            elif comprobante.tipo_comprobante == RceTipoComprobante.NOTA_DEBITO:
                totales["cantidad_notas_debito"] += 1
            else:
                totales["cantidad_otros"] += 1
            
            # Sumar montos
            totales["total_base_imponible_gravada"] += comprobante.base_imponible_operaciones_gravadas
            
            if comprobante.sustenta_credito_fiscal:
                totales["total_base_imponible_gravada_con_derecho"] += comprobante.base_imponible_operaciones_gravadas
                totales["total_credito_fiscal"] += comprobante.igv
            else:
                totales["total_base_imponible_gravada_sin_derecho"] += comprobante.base_imponible_operaciones_gravadas
            
            totales["total_igv"] += comprobante.igv
            totales["total_importe"] += comprobante.importe_total
            
            # Detracción, retención, percepción
            if comprobante.detraccion and comprobante.detraccion.monto:
                totales["total_detraccion"] += comprobante.detraccion.monto
            
            if comprobante.retencion and comprobante.retencion.monto:
                totales["total_retencion"] += comprobante.retencion.monto
            
            if comprobante.percepcion and comprobante.percepcion.monto:
                totales["total_percepcion"] += comprobante.percepcion.monto
        
        return totales
    
    def _preparar_datos_envio_sunat(self, propuesta: Dict[str, Any]) -> Dict[str, Any]:
        """Preparar datos para envío a SUNAT"""
        return {
            "ruc": propuesta["ruc"],
            "periodo": propuesta["periodo"],
            "correlativo": propuesta["correlativo_propuesta"],
            "cantidad_comprobantes": propuesta["cantidad_comprobantes"],
            "total_importe": float(propuesta["total_importe"]),
            "total_igv": float(propuesta["total_igv"]),
            "total_credito_fiscal": float(propuesta["total_credito_fiscal"]),
            "comprobantes": [
                self._convertir_comprobante_para_sunat(comp) 
                for comp in propuesta["comprobantes"]
            ]
        }
    
    def _convertir_comprobante_para_sunat(self, comprobante: Dict[str, Any]) -> Dict[str, Any]:
        """Convertir comprobante al formato esperado por SUNAT"""
        return {
            "correlativo": comprobante["correlativo"],
            "periodo": comprobante["periodo"],
            "fecha_emision": comprobante["fecha_emision"].strftime("%d/%m/%Y"),
            "tipo_comprobante": comprobante["tipo_comprobante"],
            "serie": comprobante["serie"],
            "numero": comprobante["numero"],
            "tipo_documento_proveedor": comprobante["proveedor"]["tipo_documento"],
            "numero_documento_proveedor": comprobante["proveedor"]["numero_documento"],
            "razon_social_proveedor": comprobante["proveedor"]["razon_social"],
            "base_imponible": float(comprobante["base_imponible_operaciones_gravadas"]),
            "igv": float(comprobante["igv"]),
            "importe_total": float(comprobante["importe_total"]),
            "sustenta_credito_fiscal": comprobante["sustenta_credito_fiscal"],
            "moneda": comprobante.get("moneda", "PEN"),
            "tipo_cambio": float(comprobante["tipo_cambio"]) if comprobante.get("tipo_cambio") else 1.0
        }
    
    async def _obtener_propuesta(self, ruc: str, periodo: str) -> Optional[Dict[str, Any]]:
        """Obtener propuesta de la base de datos"""
        return await self.collection.find_one({"ruc": ruc, "periodo": periodo})
    
    async def _actualizar_propuesta_con_respuesta_sunat(
        self,
        ruc: str,
        periodo: str,
        respuesta_sunat: Dict[str, Any]
    ) -> None:
        """Actualizar propuesta con la respuesta de SUNAT"""
        update_data = {
            "fecha_actualizacion": datetime.utcnow()
        }
        
        if respuesta_sunat.get("exitoso", False):
            update_data.update({
                "estado": RceEstadoProceso.ACEPTADO,
                "ticket_id": respuesta_sunat.get("ticket"),
                "numero_orden": respuesta_sunat.get("numero_orden"),
                "fecha_aceptacion": datetime.utcnow(),
                "observaciones_sunat": respuesta_sunat.get("mensaje")
            })
        else:
            update_data.update({
                "estado": RceEstadoProceso.ERROR,
                "observaciones_sunat": respuesta_sunat.get("mensaje", "Error no especificado"),
                "motivo_rechazo": respuesta_sunat.get("error", "Error en el envío")
            })
        
        await self.collection.update_one(
            {"ruc": ruc, "periodo": periodo},
            {"$set": update_data}
        )
    
    async def _marcar_propuesta_error(self, ruc: str, periodo: str, error: str) -> None:
        """Marcar propuesta como error"""
        await self.collection.update_one(
            {"ruc": ruc, "periodo": periodo},
            {"$set": {
                "estado": RceEstadoProceso.ERROR,
                "motivo_rechazo": error,
                "fecha_actualizacion": datetime.utcnow()
            }}
        )
    
    def _convertir_a_response(
        self,
        propuesta_dict: Dict[str, Any],
        inconsistencias: Optional[List[RceInconsistencia]] = None
    ) -> RcePropuestaResponse:
        """Convertir diccionario de MongoDB a RcePropuestaResponse"""
        archivos_disponibles = []
        
        # Determinar archivos disponibles según el estado
        if propuesta_dict.get("archivo_propuesta_txt"):
            archivos_disponibles.append("propuesta.txt")
        if propuesta_dict.get("archivo_propuesta_excel"):
            archivos_disponibles.append("propuesta.xlsx")
        if propuesta_dict.get("archivo_inconsistencias"):
            archivos_disponibles.append("inconsistencias.txt")
        if propuesta_dict.get("archivo_resumen"):
            archivos_disponibles.append("resumen.pdf")
        
        return RcePropuestaResponse(
            ruc=propuesta_dict["ruc"],
            periodo=propuesta_dict["periodo"],
            estado=RceEstadoProceso(propuesta_dict["estado"]),
            fecha_generacion=propuesta_dict["fecha_generacion"],
            correlativo_propuesta=propuesta_dict.get("correlativo_propuesta"),
            cantidad_comprobantes=propuesta_dict["cantidad_comprobantes"],
            total_importe=Decimal(str(propuesta_dict["total_importe"])),
            total_igv=Decimal(str(propuesta_dict["total_igv"])),
            total_credito_fiscal=Decimal(str(propuesta_dict["total_credito_fiscal"])),
            ticket_id=propuesta_dict.get("ticket_id"),
            numero_orden=propuesta_dict.get("numero_orden"),
            fecha_aceptacion=propuesta_dict.get("fecha_aceptacion"),
            archivos_disponibles=archivos_disponibles,
            observaciones_sunat=propuesta_dict.get("observaciones_sunat")
        )
