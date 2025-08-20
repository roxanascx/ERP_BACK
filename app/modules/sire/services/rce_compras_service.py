"""
RCE Compras Service - Lógica de negocio para comprobantes de compra
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..models.rce import (
    RceComprobante, RcePropuesta, RceEstadoProceso, 
    RceTipoComprobante, RceInconsistencia
)
from ..schemas.rce_schemas import (
    RceComprobanteCreateRequest, RceComprobanteResponse,
    RceConsultaRequest, RceConsultaResponse, RceApiResponse
)
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ....shared.exceptions import SireException, SireValidationException


class RceComprasService:
    """Servicio para gestión de comprobantes de compra RCE"""
    
    def __init__(self, database: AsyncIOMotorDatabase, api_client: SunatApiClient, auth_service: SireAuthService):
        self.db = database
        self.api_client = api_client
        self.auth_service = auth_service
        self.collection = database.rce_comprobantes
        
    async def crear_comprobante(
        self, 
        ruc: str, 
        request: RceComprobanteCreateRequest
    ) -> RceComprobanteResponse:
        """
        Crear un nuevo comprobante RCE
        
        Args:
            ruc: RUC del contribuyente
            request: Datos del comprobante a crear
            
        Returns:
            RceComprobanteResponse: Comprobante creado
            
        Raises:
            SireValidationException: Si los datos no son válidos
            SireException: Si hay error en la operación
        """
        try:
            # Validar que no exista duplicado
            await self._validar_duplicado(ruc, request.periodo, request.correlativo)
            
            # Validar datos del comprobante
            await self._validar_comprobante(request)
            
            # Crear modelo completo del comprobante
            comprobante = await self._crear_modelo_comprobante(ruc, request)
            
            # Guardar en base de datos
            resultado = await self.collection.insert_one(comprobante.dict())
            
            # Recuperar comprobante creado
            comprobante_creado = await self.collection.find_one({"_id": resultado.inserted_id})
            
            return self._convertir_a_response(comprobante_creado)
            
        except Exception as e:
            raise SireException(f"Error creando comprobante: {str(e)}")
    
    async def actualizar_comprobante(
        self,
        ruc: str,
        correlativo: str,
        periodo: str,
        request: RceComprobanteCreateRequest
    ) -> RceComprobanteResponse:
        """
        Actualizar un comprobante RCE existente
        
        Args:
            ruc: RUC del contribuyente
            correlativo: Correlativo del comprobante
            periodo: Periodo del comprobante
            request: Nuevos datos del comprobante
            
        Returns:
            RceComprobanteResponse: Comprobante actualizado
        """
        try:
            # Buscar comprobante existente
            filtro = {
                "numero_documento_adquiriente": ruc,
                "periodo": periodo,
                "correlativo": correlativo
            }
            
            comprobante_existente = await self.collection.find_one(filtro)
            if not comprobante_existente:
                raise SireException("Comprobante no encontrado")
            
            # Validar datos actualizados
            await self._validar_comprobante(request)
            
            # Crear modelo actualizado
            comprobante_actualizado = await self._crear_modelo_comprobante(ruc, request)
            comprobante_actualizado.fecha_registro = comprobante_existente["fecha_registro"]
            
            # Actualizar en base de datos
            await self.collection.replace_one(filtro, comprobante_actualizado.dict())
            
            # Recuperar comprobante actualizado
            comprobante_result = await self.collection.find_one(filtro)
            
            return self._convertir_a_response(comprobante_result)
            
        except Exception as e:
            raise SireException(f"Error actualizando comprobante: {str(e)}")
    
    async def eliminar_comprobante(
        self,
        ruc: str,
        correlativo: str,
        periodo: str
    ) -> bool:
        """
        Eliminar un comprobante RCE
        
        Args:
            ruc: RUC del contribuyente
            correlativo: Correlativo del comprobante
            periodo: Periodo del comprobante
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            filtro = {
                "numero_documento_adquiriente": ruc,
                "periodo": periodo,
                "correlativo": correlativo
            }
            
            resultado = await self.collection.delete_one(filtro)
            
            if resultado.deleted_count == 0:
                raise SireException("Comprobante no encontrado")
            
            return True
            
        except Exception as e:
            raise SireException(f"Error eliminando comprobante: {str(e)}")
    
    async def consultar_comprobantes(
        self,
        ruc: str,
        request: RceConsultaRequest
    ) -> RceConsultaResponse:
        """
        Consultar comprobantes RCE con filtros y paginación
        
        Args:
            ruc: RUC del contribuyente
            request: Parámetros de consulta
            
        Returns:
            RceConsultaResponse: Lista de comprobantes con paginación
        """
        try:
            # Construir filtros
            filtros = await self._construir_filtros_consulta(ruc, request)
            
            # Calcular paginación
            skip = (request.pagina - 1) * request.registros_por_pagina
            limit = request.registros_por_pagina
            
            # Ejecutar consulta con paginación
            cursor = self.collection.find(filtros).skip(skip).limit(limit)
            comprobantes_raw = await cursor.to_list(length=limit)
            
            # Contar total de registros
            total_registros = await self.collection.count_documents(filtros)
            total_paginas = (total_registros + request.registros_por_pagina - 1) // request.registros_por_pagina
            
            # Convertir a responses
            comprobantes = [self._convertir_a_response(comp) for comp in comprobantes_raw]
            
            # Calcular totales
            totales = await self._calcular_totales(filtros)
            
            # Generar resumen por tipo
            resumen_por_tipo = await self._generar_resumen_por_tipo(filtros)
            
            return RceConsultaResponse(
                comprobantes=comprobantes,
                total_registros=total_registros,
                total_paginas=total_paginas,
                pagina_actual=request.pagina,
                registros_por_pagina=request.registros_por_pagina,
                total_importe=totales.get("total_importe", Decimal("0.00")),
                total_igv=totales.get("total_igv", Decimal("0.00")),
                total_credito_fiscal=totales.get("total_credito_fiscal", Decimal("0.00")),
                resumen_por_tipo=resumen_por_tipo,
                filtros_aplicados=request.dict(exclude_none=True)
            )
            
        except Exception as e:
            raise SireException(f"Error consultando comprobantes: {str(e)}")
    
    async def obtener_comprobante(
        self,
        ruc: str,
        correlativo: str,
        periodo: str
    ) -> Optional[RceComprobanteResponse]:
        """
        Obtener un comprobante específico
        
        Args:
            ruc: RUC del contribuyente
            correlativo: Correlativo del comprobante
            periodo: Periodo del comprobante
            
        Returns:
            RceComprobanteResponse: Comprobante encontrado o None
        """
        try:
            filtro = {
                "numero_documento_adquiriente": ruc,
                "periodo": periodo,
                "correlativo": correlativo
            }
            
            comprobante = await self.collection.find_one(filtro)
            
            if not comprobante:
                return None
                
            return self._convertir_a_response(comprobante)
            
        except Exception as e:
            raise SireException(f"Error obteniendo comprobante: {str(e)}")
    
    async def validar_comprobantes_lote(
        self,
        ruc: str,
        comprobantes: List[RceComprobanteCreateRequest]
    ) -> Tuple[List[RceComprobanteCreateRequest], List[RceInconsistencia]]:
        """
        Validar un lote de comprobantes y devolver válidos e inconsistencias
        
        Args:
            ruc: RUC del contribuyente
            comprobantes: Lista de comprobantes a validar
            
        Returns:
            Tuple: (comprobantes_validos, inconsistencias)
        """
        comprobantes_validos = []
        inconsistencias = []
        
        for i, comprobante in enumerate(comprobantes):
            try:
                # Validar comprobante individual
                await self._validar_comprobante(comprobante)
                
                # Validar duplicados
                await self._validar_duplicado(ruc, comprobante.periodo, comprobante.correlativo)
                
                comprobantes_validos.append(comprobante)
                
            except SireValidationException as e:
                inconsistencia = RceInconsistencia(
                    linea=i + 1,
                    correlativo=comprobante.correlativo,
                    campo="general",
                    codigo_error="VALIDATION_ERROR",
                    descripcion_error=str(e),
                    valor_encontrado="",
                    tipo_error="CRITICO",
                    severidad="ERROR",
                    afecta_credito_fiscal=True,
                    requiere_correccion=True
                )
                inconsistencias.append(inconsistencia)
        
        return comprobantes_validos, inconsistencias
    
    # =======================================
    # MÉTODOS PRIVADOS DE VALIDACIÓN
    # =======================================
    
    async def _validar_duplicado(self, ruc: str, periodo: str, correlativo: str) -> None:
        """Validar que no exista un comprobante duplicado"""
        filtro = {
            "numero_documento_adquiriente": ruc,
            "periodo": periodo,
            "correlativo": correlativo
        }
        
        existente = await self.collection.find_one(filtro)
        if existente:
            raise SireValidationException(f"Ya existe un comprobante con correlativo {correlativo} en el periodo {periodo}")
    
    async def _validar_comprobante(self, request: RceComprobanteCreateRequest) -> None:
        """Validar datos del comprobante según reglas SUNAT"""
        # Validar periodo
        if not request.periodo or len(request.periodo) != 6:
            raise SireValidationException("Periodo debe tener formato YYYYMM")
        
        # Validar fechas
        if request.fecha_vencimiento and request.fecha_vencimiento < request.fecha_emision:
            raise SireValidationException("Fecha de vencimiento no puede ser anterior a fecha de emisión")
        
        # Validar montos
        if request.importe_total < 0:
            raise SireValidationException("Importe total no puede ser negativo")
        
        if request.igv < 0:
            raise SireValidationException("IGV no puede ser negativo")
        
        # Validar RUC del proveedor si es RUC
        if request.tipo_documento_proveedor.value == "6":  # RUC
            if not request.numero_documento_proveedor or len(request.numero_documento_proveedor) != 11:
                raise SireValidationException("RUC del proveedor debe tener 11 dígitos")
        
        # Validar coherencia de montos
        if request.sustenta_credito_fiscal and request.igv == 0:
            raise SireValidationException("Si sustenta crédito fiscal, debe tener IGV mayor a 0")
    
    async def _crear_modelo_comprobante(
        self,
        ruc: str,
        request: RceComprobanteCreateRequest
    ) -> RceComprobante:
        """Crear modelo completo del comprobante desde request"""
        from ..models.rce import RceProveedor, RceTipoDocumento
        
        # Crear información del proveedor
        proveedor = RceProveedor(
            tipo_documento=request.tipo_documento_proveedor,
            numero_documento=request.numero_documento_proveedor,
            razon_social=request.razon_social_proveedor
        )
        
        # Crear comprobante completo
        comprobante = RceComprobante(
            periodo=request.periodo,
            correlativo=request.correlativo,
            fecha_emision=request.fecha_emision,
            fecha_vencimiento=request.fecha_vencimiento,
            tipo_comprobante=request.tipo_comprobante,
            serie=request.serie,
            numero=request.numero,
            numero_final=request.numero_final,
            proveedor=proveedor,
            numero_documento_adquiriente=ruc,
            moneda=request.moneda,
            tipo_cambio=request.tipo_cambio,
            base_imponible_operaciones_gravadas=request.base_imponible_operaciones_gravadas,
            igv=request.igv,
            importe_total=request.importe_total,
            sustenta_credito_fiscal=request.sustenta_credito_fiscal,
            sustenta_costo_gasto=request.sustenta_costo_gasto,
            observaciones=request.observaciones
        )
        
        return comprobante
    
    async def _construir_filtros_consulta(
        self,
        ruc: str,
        request: RceConsultaRequest
    ) -> Dict[str, Any]:
        """Construir filtros para consulta de comprobantes"""
        filtros = {"numero_documento_adquiriente": ruc}
        
        # Filtro por periodo
        if request.periodo:
            filtros["periodo"] = request.periodo
        elif request.periodo_inicio and request.periodo_fin:
            filtros["periodo"] = {
                "$gte": request.periodo_inicio,
                "$lte": request.periodo_fin
            }
        
        # Filtros de comprobante
        if request.tipo_comprobante:
            if len(request.tipo_comprobante) == 1:
                filtros["tipo_comprobante"] = request.tipo_comprobante[0].value
            else:
                filtros["tipo_comprobante"] = {"$in": [tc.value for tc in request.tipo_comprobante]}
        
        if request.serie:
            filtros["serie"] = request.serie
        
        if request.numero:
            filtros["numero"] = request.numero
        
        if request.numero_documento_proveedor:
            filtros["proveedor.numero_documento"] = request.numero_documento_proveedor
        
        # Filtros de fecha
        if request.fecha_emision_inicio or request.fecha_emision_fin:
            fecha_filtro = {}
            if request.fecha_emision_inicio:
                fecha_filtro["$gte"] = request.fecha_emision_inicio
            if request.fecha_emision_fin:
                fecha_filtro["$lte"] = request.fecha_emision_fin
            filtros["fecha_emision"] = fecha_filtro
        
        # Filtros específicos
        if request.solo_con_credito_fiscal is not None:
            filtros["sustenta_credito_fiscal"] = request.solo_con_credito_fiscal
        
        if request.con_detraccion is not None:
            if request.con_detraccion:
                filtros["detraccion"] = {"$ne": None}
            else:
                filtros["detraccion"] = None
        
        if request.estado:
            filtros["estado"] = request.estado
        
        return filtros
    
    async def _calcular_totales(self, filtros: Dict[str, Any]) -> Dict[str, Decimal]:
        """Calcular totales de la consulta"""
        pipeline = [
            {"$match": filtros},
            {"$group": {
                "_id": None,
                "total_importe": {"$sum": "$importe_total"},
                "total_igv": {"$sum": "$igv"},
                "total_credito_fiscal": {
                    "$sum": {
                        "$cond": [
                            "$sustenta_credito_fiscal",
                            "$igv",
                            0
                        ]
                    }
                }
            }}
        ]
        
        resultado = await self.collection.aggregate(pipeline).to_list(length=1)
        
        if resultado:
            return {
                "total_importe": Decimal(str(resultado[0].get("total_importe", 0))),
                "total_igv": Decimal(str(resultado[0].get("total_igv", 0))),
                "total_credito_fiscal": Decimal(str(resultado[0].get("total_credito_fiscal", 0)))
            }
        
        return {
            "total_importe": Decimal("0.00"),
            "total_igv": Decimal("0.00"),
            "total_credito_fiscal": Decimal("0.00")
        }
    
    async def _generar_resumen_por_tipo(self, filtros: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Generar resumen agrupado por tipo de comprobante"""
        pipeline = [
            {"$match": filtros},
            {"$group": {
                "_id": "$tipo_comprobante",
                "cantidad": {"$sum": 1},
                "total_importe": {"$sum": "$importe_total"},
                "total_igv": {"$sum": "$igv"},
                "total_credito_fiscal": {
                    "$sum": {
                        "$cond": [
                            "$sustenta_credito_fiscal",
                            "$igv",
                            0
                        ]
                    }
                }
            }}
        ]
        
        resultados = await self.collection.aggregate(pipeline).to_list(length=None)
        
        resumen = {}
        for resultado in resultados:
            tipo = resultado["_id"]
            resumen[tipo] = {
                "cantidad": resultado["cantidad"],
                "total_importe": float(resultado["total_importe"]),
                "total_igv": float(resultado["total_igv"]),
                "total_credito_fiscal": float(resultado["total_credito_fiscal"])
            }
        
        return resumen
    
    def _convertir_a_response(self, comprobante_dict: Dict[str, Any]) -> RceComprobanteResponse:
        """Convertir diccionario de MongoDB a RceComprobanteResponse"""
        # Calcular crédito fiscal
        credito_fiscal = None
        if comprobante_dict.get("sustenta_credito_fiscal", False):
            credito_fiscal = comprobante_dict.get("igv", 0)
        
        return RceComprobanteResponse(
            periodo=comprobante_dict["periodo"],
            correlativo=comprobante_dict["correlativo"],
            fecha_emision=comprobante_dict["fecha_emision"],
            fecha_vencimiento=comprobante_dict.get("fecha_vencimiento"),
            tipo_comprobante=comprobante_dict["tipo_comprobante"],
            serie=comprobante_dict["serie"],
            numero=comprobante_dict["numero"],
            tipo_documento_proveedor=comprobante_dict["proveedor"]["tipo_documento"],
            numero_documento_proveedor=comprobante_dict["proveedor"]["numero_documento"],
            razon_social_proveedor=comprobante_dict["proveedor"]["razon_social"],
            moneda=comprobante_dict.get("moneda", "PEN"),
            tipo_cambio=comprobante_dict.get("tipo_cambio"),
            base_imponible_operaciones_gravadas=Decimal(str(comprobante_dict.get("base_imponible_operaciones_gravadas", 0))),
            igv=Decimal(str(comprobante_dict.get("igv", 0))),
            importe_total=Decimal(str(comprobante_dict["importe_total"])),
            sustenta_credito_fiscal=comprobante_dict.get("sustenta_credito_fiscal", False),
            estado=comprobante_dict.get("estado", "RECIBIDO"),
            fecha_registro=comprobante_dict.get("fecha_registro", datetime.utcnow()),
            observaciones=comprobante_dict.get("observaciones"),
            credito_fiscal_calculado=Decimal(str(credito_fiscal)) if credito_fiscal else None,
            monto_detraccion=Decimal(str(comprobante_dict.get("monto_detraccion", 0))) if comprobante_dict.get("monto_detraccion") else None
        )
