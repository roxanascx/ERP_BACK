"""
RCE Consulta Service - Servicio para consultas avanzadas y reportes RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import io
import csv

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from ..models.rce import (
    RceResumenConsolidado, RceEstadoProceso,
    RceTipoComprobante, RceConsultaAvanzada
)
from ..schemas.rce_schemas import (
    RceConsultaRequest, RceConsultaResponse,
    RceResumenResponse, RceComprobanteResponse,
    RceDescargaMasivaRequest
)
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ....shared.exceptions import SireException


class RceConsultaService:
    """Servicio para consultas avanzadas y reportes RCE"""
    
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
        self.collection_comprobantes = database.rce_comprobantes
        self.collection_resumenes = database.rce_resumenes
        
    async def generar_resumen_periodo(
        self,
        ruc: str,
        periodo: str,
        incluir_detalle_por_tipo: bool = True,
        comparar_con_periodo_anterior: bool = False
    ) -> RceResumenResponse:
        """
        Generar resumen consolidado para un periodo
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo YYYYMM
            incluir_detalle_por_tipo: Incluir detalle por tipo de comprobante
            comparar_con_periodo_anterior: Incluir comparación con periodo anterior
            
        Returns:
            RceResumenResponse: Resumen consolidado del periodo
        """
        try:
            # Calcular totales del periodo
            totales = await self._calcular_totales_periodo(ruc, periodo)
            
            # Generar resumen por tipo de comprobante
            resumen_por_tipo = {}
            if incluir_detalle_por_tipo:
                resumen_por_tipo = await self._generar_resumen_por_tipo(ruc, periodo)
            
            # Comparación con periodo anterior
            comparacion_anterior = None
            if comparar_con_periodo_anterior:
                periodo_anterior = self._calcular_periodo_anterior(periodo)
                totales_anterior = await self._calcular_totales_periodo(ruc, periodo_anterior)
                comparacion_anterior = self._calcular_variaciones(totales, totales_anterior)
            
            # Calcular porcentaje de crédito fiscal
            porcentaje_credito_fiscal = None
            if totales["total_igv"] > 0:
                porcentaje_credito_fiscal = (totales["total_credito_fiscal"] / totales["total_igv"]) * 100
            
            # Determinar estado del periodo
            estado_periodo = await self._determinar_estado_periodo(ruc, periodo)
            
            # Obtener archivos disponibles
            archivos_disponibles = await self._obtener_archivos_disponibles(ruc, periodo)
            
            resumen = RceResumenResponse(
                ruc=ruc,
                periodo=periodo,
                estado_periodo=estado_periodo,
                fecha_generacion=datetime.utcnow(),
                total_comprobantes=totales["total_comprobantes"],
                total_proveedores=totales["total_proveedores"],
                total_importe=totales["total_importe"],
                total_igv=totales["total_igv"],
                total_credito_fiscal=totales["total_credito_fiscal"],
                resumen_por_tipo=resumen_por_tipo,
                porcentaje_credito_fiscal=porcentaje_credito_fiscal,
                comparacion_periodo_anterior=comparacion_anterior,
                archivos_disponibles=archivos_disponibles
            )
            
            # Guardar resumen en base de datos
            await self._guardar_resumen(resumen)
            
            return resumen
            
        except Exception as e:
            raise SireException(f"Error generando resumen: {str(e)}")
    
    async def consultar_comprobantes_sunat(
        self,
        ruc: str,
        request: RceConsultaRequest,
        usuario_sunat: str,
        clave_sunat: str,
        sincronizar_local: bool = True
    ) -> RceConsultaResponse:
        """
        Consultar comprobantes directamente en SUNAT y opcionalmente sincronizar
        
        Args:
            ruc: RUC del contribuyente
            request: Parámetros de consulta
            usuario_sunat: Usuario SUNAT
            clave_sunat: Clave SUNAT
            sincronizar_local: Si sincronizar con base de datos local
            
        Returns:
            RceConsultaResponse: Comprobantes consultados
        """
        try:
            # Autenticar con SUNAT
            token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
            
            # Preparar parámetros para SUNAT
            params_sunat = self._preparar_parametros_consulta_sunat(ruc, request)
            
            # Consultar en SUNAT
            respuesta_sunat = await self.api_client.rce_comprobante_consultar(token.access_token, params_sunat)
            
            # Procesar respuesta de SUNAT
            comprobantes_sunat = self._procesar_respuesta_sunat(respuesta_sunat)
            
            # Sincronizar con base de datos local si se solicita
            if sincronizar_local:
                await self._sincronizar_comprobantes_local(ruc, comprobantes_sunat)
            
            # Convertir a formato de respuesta
            comprobantes_response = [
                self._convertir_comprobante_sunat_a_response(comp) 
                for comp in comprobantes_sunat
            ]
            
            # Calcular totales
            totales = self._calcular_totales_lista(comprobantes_sunat)
            
            return RceConsultaResponse(
                comprobantes=comprobantes_response,
                total_registros=len(comprobantes_response),
                total_paginas=1,  # SUNAT maneja paginación internamente
                pagina_actual=request.pagina,
                registros_por_pagina=len(comprobantes_response),
                total_importe=totales["total_importe"],
                total_igv=totales["total_igv"],
                total_credito_fiscal=totales["total_credito_fiscal"],
                filtros_aplicados=request.dict(exclude_none=True)
            )
            
        except Exception as e:
            raise SireException(f"Error consultando comprobantes en SUNAT: {str(e)}")
    
    async def consultar_lineas_detalle(
        self,
        ruc: str,
        periodo: str,
        correlativo: Optional[str] = None,
        usuario_sunat: str = None,
        clave_sunat: str = None
    ) -> List[Dict[str, Any]]:
        """
        Consultar líneas de detalle de comprobantes RCE
        
        Args:
            ruc: RUC del contribuyente
            periodo: Periodo a consultar
            correlativo: Correlativo específico (opcional)
            usuario_sunat: Usuario SUNAT (requerido para consulta en SUNAT)
            clave_sunat: Clave SUNAT (requerida para consulta en SUNAT)
            
        Returns:
            List[Dict]: Líneas de detalle de comprobantes
        """
        try:
            if usuario_sunat and clave_sunat:
                # Consultar en SUNAT
                token = await self.auth_service.obtener_token_valido(ruc, usuario_sunat, clave_sunat)
                
                params = {
                    "ruc": ruc,
                    "periodo": periodo
                }
                
                if correlativo:
                    params["correlativo"] = correlativo
                
                respuesta_sunat = await self.api_client.rce_linea_detalle_consultar(token.access_token, params)
                return respuesta_sunat.get("lineas_detalle", [])
            else:
                # Consultar en base de datos local
                filtros = {"numero_documento_adquiriente": ruc, "periodo": periodo}
                
                if correlativo:
                    filtros["correlativo"] = correlativo
                
                comprobantes = await self.collection_comprobantes.find(filtros).to_list(length=None)
                
                # Extraer líneas de detalle (si están almacenadas)
                lineas_detalle = []
                for comp in comprobantes:
                    if comp.get("lineas_detalle"):
                        lineas_detalle.extend(comp["lineas_detalle"])
                
                return lineas_detalle
                
        except Exception as e:
            raise SireException(f"Error consultando líneas de detalle: {str(e)}")
    
    async def generar_reporte_credito_fiscal(
        self,
        ruc: str,
        periodo_inicio: str,
        periodo_fin: str,
        incluir_detalle: bool = True
    ) -> Dict[str, Any]:
        """
        Generar reporte de crédito fiscal por rango de periodos
        
        Args:
            ruc: RUC del contribuyente
            periodo_inicio: Periodo inicio YYYYMM
            periodo_fin: Periodo fin YYYYMM
            incluir_detalle: Incluir detalle por comprobante
            
        Returns:
            Dict: Reporte de crédito fiscal
        """
        try:
            # Filtros para consulta
            filtros = {
                "numero_documento_adquiriente": ruc,
                "periodo": {"$gte": periodo_inicio, "$lte": periodo_fin},
                "sustenta_credito_fiscal": True
            }
            
            # Pipeline de agregación para totales
            pipeline_totales = [
                {"$match": filtros},
                {"$group": {
                    "_id": "$periodo",
                    "total_comprobantes": {"$sum": 1},
                    "total_igv": {"$sum": "$igv"},
                    "total_credito_fiscal": {"$sum": "$igv"},
                    "total_base_imponible": {"$sum": "$base_imponible_operaciones_gravadas"},
                    "total_importe": {"$sum": "$importe_total"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            totales_por_periodo = await self.collection_comprobantes.aggregate(pipeline_totales).to_list(length=None)
            
            # Calcular totales generales
            totales_generales = {
                "total_comprobantes": sum(p["total_comprobantes"] for p in totales_por_periodo),
                "total_igv": sum(p["total_igv"] for p in totales_por_periodo),
                "total_credito_fiscal": sum(p["total_credito_fiscal"] for p in totales_por_periodo),
                "total_base_imponible": sum(p["total_base_imponible"] for p in totales_por_periodo),
                "total_importe": sum(p["total_importe"] for p in totales_por_periodo)
            }
            
            # Detalle por comprobante si se solicita
            detalle_comprobantes = []
            if incluir_detalle:
                comprobantes = await self.collection_comprobantes.find(filtros).to_list(length=None)
                detalle_comprobantes = [
                    {
                        "periodo": comp["periodo"],
                        "correlativo": comp["correlativo"],
                        "fecha_emision": comp["fecha_emision"].strftime("%d/%m/%Y"),
                        "tipo_comprobante": comp["tipo_comprobante"],
                        "serie": comp["serie"],
                        "numero": comp["numero"],
                        "proveedor": comp["proveedor"]["razon_social"],
                        "numero_documento_proveedor": comp["proveedor"]["numero_documento"],
                        "base_imponible": float(comp["base_imponible_operaciones_gravadas"]),
                        "igv": float(comp["igv"]),
                        "credito_fiscal": float(comp["igv"]),
                        "importe_total": float(comp["importe_total"])
                    }
                    for comp in comprobantes
                ]
            
            return {
                "ruc": ruc,
                "periodo_inicio": periodo_inicio,
                "periodo_fin": periodo_fin,
                "fecha_generacion": datetime.utcnow().isoformat(),
                "totales_por_periodo": [
                    {
                        "periodo": p["_id"],
                        "total_comprobantes": p["total_comprobantes"],
                        "total_igv": float(p["total_igv"]),
                        "total_credito_fiscal": float(p["total_credito_fiscal"]),
                        "total_base_imponible": float(p["total_base_imponible"]),
                        "total_importe": float(p["total_importe"])
                    }
                    for p in totales_por_periodo
                ],
                "totales_generales": {
                    "total_comprobantes": totales_generales["total_comprobantes"],
                    "total_igv": float(totales_generales["total_igv"]),
                    "total_credito_fiscal": float(totales_generales["total_credito_fiscal"]),
                    "total_base_imponible": float(totales_generales["total_base_imponible"]),
                    "total_importe": float(totales_generales["total_importe"])
                },
                "detalle_comprobantes": detalle_comprobantes
            }
            
        except Exception as e:
            raise SireException(f"Error generando reporte de crédito fiscal: {str(e)}")
    
    async def exportar_comprobantes_csv(
        self,
        ruc: str,
        request: RceConsultaRequest
    ) -> bytes:
        """
        Exportar comprobantes a formato CSV
        
        Args:
            ruc: RUC del contribuyente
            request: Parámetros de consulta
            
        Returns:
            bytes: Contenido del archivo CSV
        """
        try:
            # Consultar comprobantes
            consulta_response = await self.compras_service.consultar_comprobantes(ruc, request)
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Escribir cabeceras
            headers = [
                "Periodo", "Correlativo", "Fecha Emisión", "Tipo Comprobante",
                "Serie", "Número", "Tipo Doc Proveedor", "Número Doc Proveedor",
                "Razón Social Proveedor", "Moneda", "Base Imponible", "IGV",
                "Importe Total", "Sustenta Crédito Fiscal", "Estado"
            ]
            writer.writerow(headers)
            
            # Escribir datos
            for comp in consulta_response.comprobantes:
                row = [
                    comp.periodo,
                    comp.correlativo,
                    comp.fecha_emision.strftime("%d/%m/%Y"),
                    comp.tipo_comprobante.value,
                    comp.serie,
                    comp.numero,
                    comp.tipo_documento_proveedor.value,
                    comp.numero_documento_proveedor,
                    comp.razon_social_proveedor,
                    comp.moneda.value,
                    float(comp.base_imponible_operaciones_gravadas),
                    float(comp.igv),
                    float(comp.importe_total),
                    "Sí" if comp.sustenta_credito_fiscal else "No",
                    comp.estado
                ]
                writer.writerow(row)
            
            # Convertir a bytes
            content = output.getvalue().encode('utf-8-sig')  # UTF-8 con BOM para Excel
            output.close()
            
            return content
            
        except Exception as e:
            raise SireException(f"Error exportando CSV: {str(e)}")
    
    # =======================================
    # MÉTODOS PRIVADOS
    # =======================================
    
    async def _calcular_totales_periodo(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """Calcular totales consolidados de un periodo"""
        pipeline = [
            {"$match": {
                "numero_documento_adquiriente": ruc,
                "periodo": periodo
            }},
            {"$group": {
                "_id": None,
                "total_comprobantes": {"$sum": 1},
                "total_proveedores": {"$addToSet": "$proveedor.numero_documento"},
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
                },
                "total_base_imponible": {"$sum": "$base_imponible_operaciones_gravadas"}
            }},
            {"$project": {
                "total_comprobantes": 1,
                "total_proveedores": {"$size": "$total_proveedores"},
                "total_importe": 1,
                "total_igv": 1,
                "total_credito_fiscal": 1,
                "total_base_imponible": 1
            }}
        ]
        
        resultado = await self.collection_comprobantes.aggregate(pipeline).to_list(length=1)
        
        if resultado:
            return {
                "total_comprobantes": resultado[0]["total_comprobantes"],
                "total_proveedores": resultado[0]["total_proveedores"],
                "total_importe": Decimal(str(resultado[0]["total_importe"])),
                "total_igv": Decimal(str(resultado[0]["total_igv"])),
                "total_credito_fiscal": Decimal(str(resultado[0]["total_credito_fiscal"])),
                "total_base_imponible": Decimal(str(resultado[0]["total_base_imponible"]))
            }
        
        return {
            "total_comprobantes": 0,
            "total_proveedores": 0,
            "total_importe": Decimal("0.00"),
            "total_igv": Decimal("0.00"),
            "total_credito_fiscal": Decimal("0.00"),
            "total_base_imponible": Decimal("0.00")
        }
    
    async def _generar_resumen_por_tipo(self, ruc: str, periodo: str) -> Dict[str, Dict[str, Any]]:
        """Generar resumen agrupado por tipo de comprobante"""
        pipeline = [
            {"$match": {
                "numero_documento_adquiriente": ruc,
                "periodo": periodo
            }},
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
                },
                "total_base_imponible": {"$sum": "$base_imponible_operaciones_gravadas"}
            }}
        ]
        
        resultados = await self.collection_comprobantes.aggregate(pipeline).to_list(length=None)
        
        resumen = {}
        for resultado in resultados:
            tipo = resultado["_id"]
            resumen[tipo] = {
                "cantidad": resultado["cantidad"],
                "total_importe": float(resultado["total_importe"]),
                "total_igv": float(resultado["total_igv"]),
                "total_credito_fiscal": float(resultado["total_credito_fiscal"]),
                "total_base_imponible": float(resultado["total_base_imponible"]),
                "porcentaje_credito_fiscal": (
                    float(resultado["total_credito_fiscal"]) / float(resultado["total_igv"]) * 100
                    if resultado["total_igv"] > 0 else 0
                )
            }
        
        return resumen
    
    def _calcular_periodo_anterior(self, periodo: str) -> str:
        """Calcular periodo anterior (YYYYMM)"""
        año = int(periodo[:4])
        mes = int(periodo[4:])
        
        if mes == 1:
            año -= 1
            mes = 12
        else:
            mes -= 1
        
        return f"{año}{mes:02d}"
    
    def _calcular_variaciones(
        self, 
        totales_actual: Dict[str, Any], 
        totales_anterior: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """Calcular variaciones porcentuales con periodo anterior"""
        variaciones = {}
        
        campos_comparar = ["total_importe", "total_igv", "total_credito_fiscal", "total_comprobantes"]
        
        for campo in campos_comparar:
            actual = float(totales_actual.get(campo, 0))
            anterior = float(totales_anterior.get(campo, 0))
            
            if anterior > 0:
                variacion = ((actual - anterior) / anterior) * 100
                variaciones[f"variacion_{campo}"] = Decimal(str(round(variacion, 2)))
            else:
                variaciones[f"variacion_{campo}"] = Decimal("0.00")
        
        return variaciones
    
    async def _determinar_estado_periodo(self, ruc: str, periodo: str) -> RceEstadoProceso:
        """Determinar estado general del periodo"""
        # Buscar proceso más reciente para el periodo
        from ..services.rce_proceso_service import RceProcesoService
        
        proceso = await self.db.rce_procesos.find_one(
            {"ruc": ruc, "periodo": periodo},
            sort=[("fecha_inicio", -1)]
        )
        
        if proceso:
            return RceEstadoProceso(proceso["estado"])
        
        # Si no hay proceso, verificar si hay propuesta
        propuesta = await self.db.rce_propuestas.find_one({"ruc": ruc, "periodo": periodo})
        
        if propuesta:
            return RceEstadoProceso(propuesta["estado"])
        
        # Si hay comprobantes pero no propuesta ni proceso
        comprobantes = await self.collection_comprobantes.count_documents({
            "numero_documento_adquiriente": ruc,
            "periodo": periodo
        })
        
        return RceEstadoProceso.PENDIENTE if comprobantes > 0 else RceEstadoProceso.PENDIENTE
    
    async def _obtener_archivos_disponibles(self, ruc: str, periodo: str) -> List[str]:
        """Obtener lista de archivos disponibles para el periodo"""
        archivos = []
        
        # Verificar propuesta
        propuesta = await self.db.rce_propuestas.find_one({"ruc": ruc, "periodo": periodo})
        if propuesta:
            if propuesta.get("archivo_propuesta_txt"):
                archivos.append("propuesta.txt")
            if propuesta.get("archivo_propuesta_excel"):
                archivos.append("propuesta.xlsx")
            if propuesta.get("archivo_inconsistencias"):
                archivos.append("inconsistencias.txt")
        
        # Verificar tickets con archivos
        tickets = await self.db.rce_tickets.find({
            "ruc": ruc,
            "periodo": periodo,
            "archivos_disponibles": {"$exists": True, "$ne": []}
        }).to_list(length=None)
        
        for ticket in tickets:
            archivos.extend(ticket.get("archivos_disponibles", []))
        
        return list(set(archivos))  # Eliminar duplicados
    
    async def _guardar_resumen(self, resumen: RceResumenResponse) -> None:
        """Guardar resumen en base de datos"""
        resumen_dict = resumen.dict()
        resumen_dict["_id"] = f"{resumen.ruc}_{resumen.periodo}"
        
        await self.collection_resumenes.replace_one(
            {"_id": resumen_dict["_id"]},
            resumen_dict,
            upsert=True
        )
    
    def _preparar_parametros_consulta_sunat(
        self, 
        ruc: str, 
        request: RceConsultaRequest
    ) -> Dict[str, Any]:
        """Preparar parámetros para consulta en SUNAT"""
        params = {"ruc": ruc}
        
        if request.periodo:
            params["periodo"] = request.periodo
        elif request.periodo_inicio and request.periodo_fin:
            params["periodo_inicio"] = request.periodo_inicio
            params["periodo_fin"] = request.periodo_fin
        
        if request.tipo_comprobante:
            params["tipo_comprobante"] = [tc.value for tc in request.tipo_comprobante]
        
        if request.numero_documento_proveedor:
            params["numero_documento_proveedor"] = request.numero_documento_proveedor
        
        if request.fecha_emision_inicio:
            params["fecha_emision_inicio"] = request.fecha_emision_inicio.strftime("%d/%m/%Y")
        
        if request.fecha_emision_fin:
            params["fecha_emision_fin"] = request.fecha_emision_fin.strftime("%d/%m/%Y")
        
        return params
    
    def _procesar_respuesta_sunat(self, respuesta_sunat: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Procesar respuesta de SUNAT y convertir a formato estándar"""
        comprobantes = respuesta_sunat.get("comprobantes", [])
        
        # Normalizar formato de SUNAT al formato interno
        comprobantes_normalizados = []
        for comp in comprobantes:
            comp_normalizado = {
                "periodo": comp.get("periodo"),
                "correlativo": comp.get("correlativo"),
                "fecha_emision": datetime.strptime(comp.get("fecha_emision"), "%d/%m/%Y").date(),
                "tipo_comprobante": comp.get("tipo_comprobante"),
                "serie": comp.get("serie"),
                "numero": comp.get("numero"),
                "proveedor": {
                    "tipo_documento": comp.get("tipo_documento_proveedor"),
                    "numero_documento": comp.get("numero_documento_proveedor"),
                    "razon_social": comp.get("razon_social_proveedor")
                },
                "base_imponible_operaciones_gravadas": Decimal(str(comp.get("base_imponible", 0))),
                "igv": Decimal(str(comp.get("igv", 0))),
                "importe_total": Decimal(str(comp.get("importe_total", 0))),
                "sustenta_credito_fiscal": comp.get("sustenta_credito_fiscal", False),
                "moneda": comp.get("moneda", "PEN"),
                "estado": comp.get("estado", "SUNAT")
            }
            comprobantes_normalizados.append(comp_normalizado)
        
        return comprobantes_normalizados
    
    async def _sincronizar_comprobantes_local(
        self, 
        ruc: str, 
        comprobantes_sunat: List[Dict[str, Any]]
    ) -> None:
        """Sincronizar comprobantes de SUNAT con base de datos local"""
        for comp in comprobantes_sunat:
            filtro = {
                "numero_documento_adquiriente": ruc,
                "periodo": comp["periodo"],
                "correlativo": comp["correlativo"]
            }
            
            # Actualizar o insertar comprobante
            comp["numero_documento_adquiriente"] = ruc
            comp["fecha_sincronizacion_sunat"] = datetime.utcnow()
            
            await self.collection_comprobantes.replace_one(
                filtro,
                comp,
                upsert=True
            )
    
    def _convertir_comprobante_sunat_a_response(
        self, 
        comp_sunat: Dict[str, Any]
    ) -> RceComprobanteResponse:
        """Convertir comprobante de SUNAT a RceComprobanteResponse"""
        from ..models.rce import RceTipoComprobante, RceTipoDocumento, RceMoneda
        
        return RceComprobanteResponse(
            periodo=comp_sunat["periodo"],
            correlativo=comp_sunat["correlativo"],
            fecha_emision=comp_sunat["fecha_emision"],
            fecha_vencimiento=None,
            tipo_comprobante=RceTipoComprobante(comp_sunat["tipo_comprobante"]),
            serie=comp_sunat["serie"],
            numero=comp_sunat["numero"],
            tipo_documento_proveedor=RceTipoDocumento(comp_sunat["proveedor"]["tipo_documento"]),
            numero_documento_proveedor=comp_sunat["proveedor"]["numero_documento"],
            razon_social_proveedor=comp_sunat["proveedor"]["razon_social"],
            moneda=RceMoneda(comp_sunat["moneda"]),
            tipo_cambio=comp_sunat.get("tipo_cambio"),
            base_imponible_operaciones_gravadas=comp_sunat["base_imponible_operaciones_gravadas"],
            igv=comp_sunat["igv"],
            importe_total=comp_sunat["importe_total"],
            sustenta_credito_fiscal=comp_sunat["sustenta_credito_fiscal"],
            estado=comp_sunat["estado"],
            fecha_registro=datetime.utcnow(),
            observaciones=None,
            credito_fiscal_calculado=comp_sunat["igv"] if comp_sunat["sustenta_credito_fiscal"] else None
        )
    
    def _calcular_totales_lista(self, comprobantes: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Calcular totales de una lista de comprobantes"""
        total_importe = sum(comp["importe_total"] for comp in comprobantes)
        total_igv = sum(comp["igv"] for comp in comprobantes)
        total_credito_fiscal = sum(
            comp["igv"] for comp in comprobantes 
            if comp.get("sustenta_credito_fiscal", False)
        )
        
        return {
            "total_importe": total_importe,
            "total_igv": total_igv,
            "total_credito_fiscal": total_credito_fiscal
        }
