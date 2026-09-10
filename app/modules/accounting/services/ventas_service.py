"""
VentasService - Servicio de negocio para Registro de Ventas PLE 140000
======================================================================

Servicio especializado para gestionar el Registro de Ventas según 
especificaciones oficiales SUNAT PLE 140000.

Responsabilidades:
- CRUD completo de registros de ventas
- Validación de negocio específica para SUNAT
- Generación de archivos PLE 140000 (34 campos oficiales)
- Integración con MongoDB para persistencia
- Cálculos automáticos de totales e IGV

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025
"""

import logging
import io
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.schemas_ventas import (
    RegistroVentaRequest,
    RegistroVentaResponse,
    PLEVentasExportOptions,
    PLEVentasExportResult,
    TipoComprobanteVenta,
    TipoDocumentoCliente,
    EstadoOperacionVenta
)
from ..ple.ple_formatter_ventas import PLEFormatterVentas
from ....shared.exceptions import (
    ValidationException,
    BusinessLogicException,
    NotFoundException
)

logger = logging.getLogger(__name__)


class VentasService:
    """Servicio de negocio para gestión de ventas y generación PLE"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Inicializar servicio de ventas
        
        Args:
            database: Instancia de base de datos MongoDB
        """
        self.db = database
        self.collection = database.registro_ventas
        self.ple_formatter = PLEFormatterVentas()
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # OPERACIONES CRUD PRINCIPALES
    # ================================
    
    async def crear_registro_venta(
        self,
        venta_data: RegistroVentaRequest,
        empresa_id: str,
        periodo: str
    ) -> RegistroVentaResponse:
        """
        Crear nuevo registro de venta con validaciones SUNAT
        
        Args:
            venta_data: Datos del registro de venta
            empresa_id: ID de la empresa
            periodo: Período AAAAMM
            
        Returns:
            RegistroVentaResponse: Registro creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            BusinessLogicException: Si hay errores de negocio
        """
        try:
            # Validar existencia de comprobante
            await self._validar_comprobante_unico(
                empresa_id=empresa_id,
                tipo_comprobante=venta_data.tipo_comprobante,
                serie=venta_data.serie_comprobante,
                numero=venta_data.numero_comprobante,
                periodo=periodo
            )
            
            # Validar consistencia de montos
            self._validar_consistencia_montos(venta_data)
            
            # Preparar documento para MongoDB
            documento = {
                **venta_data.dict(),
                "empresa_id": empresa_id,
                "periodo": periodo,
                "fecha_creacion": datetime.utcnow(),
                "fecha_actualizacion": None
            }
            
            # Insertar en MongoDB
            resultado = await self.collection.insert_one(documento)
            
            # Recuperar registro creado
            registro_creado = await self.collection.find_one(
                {"_id": resultado.inserted_id}
            )
            
            return self._convertir_a_response(registro_creado)
            
        except ValidationException:
            raise
        except BusinessLogicException:
            raise
        except Exception as e:
            self.logger.error(f"Error creando registro de venta: {str(e)}")
            raise BusinessLogicException(f"Error interno creando registro: {str(e)}")
    
    async def obtener_registro_venta(
        self,
        registro_id: str,
        empresa_id: str
    ) -> RegistroVentaResponse:
        """
        Obtener registro de venta por ID
        
        Args:
            registro_id: ID del registro
            empresa_id: ID de la empresa
            
        Returns:
            RegistroVentaResponse: Registro encontrado
            
        Raises:
            NotFoundException: Si no se encuentra el registro
        """
        try:
            registro = await self.collection.find_one({
                "_id": ObjectId(registro_id),
                "empresa_id": empresa_id
            })
            
            if not registro:
                raise NotFoundException(f"Registro de venta {registro_id} no encontrado")
            
            return self._convertir_a_response(registro)
            
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error obteniendo registro {registro_id}: {str(e)}")
            raise BusinessLogicException(f"Error interno obteniendo registro: {str(e)}")
    
    async def actualizar_registro_venta(
        self,
        registro_id: str,
        venta_data: RegistroVentaRequest,
        empresa_id: str
    ) -> RegistroVentaResponse:
        """
        Actualizar registro de venta existente
        
        Args:
            registro_id: ID del registro a actualizar
            venta_data: Nuevos datos del registro
            empresa_id: ID de la empresa
            
        Returns:
            RegistroVentaResponse: Registro actualizado
            
        Raises:
            NotFoundException: Si no se encuentra el registro
            ValidationException: Si los datos no son válidos
        """
        try:
            # Verificar que existe
            registro_existente = await self.obtener_registro_venta(registro_id, empresa_id)
            
            # Validar consistencia de montos
            self._validar_consistencia_montos(venta_data)
            
            # Validar comprobante único (solo si cambió)
            if (venta_data.tipo_comprobante != registro_existente.tipo_comprobante or
                venta_data.serie_comprobante != registro_existente.serie_comprobante or
                venta_data.numero_comprobante != registro_existente.numero_comprobante):
                
                await self._validar_comprobante_unico(
                    empresa_id=empresa_id,
                    tipo_comprobante=venta_data.tipo_comprobante,
                    serie=venta_data.serie_comprobante,
                    numero=venta_data.numero_comprobante,
                    periodo=registro_existente.periodo,
                    excluir_id=registro_id
                )
            
            # Actualizar registro
            datos_actualizacion = {
                **venta_data.dict(),
                "fecha_actualizacion": datetime.utcnow()
            }
            
            await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {"$set": datos_actualizacion}
            )
            
            # Retornar registro actualizado
            return await self.obtener_registro_venta(registro_id, empresa_id)
            
        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando registro {registro_id}: {str(e)}")
            raise BusinessLogicException(f"Error interno actualizando registro: {str(e)}")
    
    async def eliminar_registro_venta(
        self,
        registro_id: str,
        empresa_id: str
    ) -> bool:
        """
        Eliminar registro de venta (eliminación lógica)
        
        Args:
            registro_id: ID del registro a eliminar
            empresa_id: ID de la empresa
            
        Returns:
            bool: True si se eliminó correctamente
            
        Raises:
            NotFoundException: Si no se encuentra el registro
        """
        try:
            # Verificar que existe
            await self.obtener_registro_venta(registro_id, empresa_id)
            
            # Marcar como anulado en lugar de eliminar físicamente
            resultado = await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {
                    "$set": {
                        "estado_operacion": EstadoOperacionVenta.ANULADO,
                        "fecha_actualizacion": datetime.utcnow()
                    }
                }
            )
            
            return resultado.modified_count > 0
            
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error eliminando registro {registro_id}: {str(e)}")
            raise BusinessLogicException(f"Error interno eliminando registro: {str(e)}")
    
    # ================================
    # CONSULTAS Y FILTROS
    # ================================
    
    async def listar_registros_ventas(
        self,
        empresa_id: str,
        periodo_inicio: Optional[str] = None,
        periodo_fin: Optional[str] = None,
        tipo_comprobante: Optional[TipoComprobanteVenta] = None,
        numero_documento_cliente: Optional[str] = None,
        incluir_anulados: bool = False,
        pagina: int = 1,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Listar registros de ventas con filtros
        
        Args:
            empresa_id: ID de la empresa
            periodo_inicio: Período inicio AAAAMM
            periodo_fin: Período fin AAAAMM
            tipo_comprobante: Filtro por tipo de comprobante
            numero_documento_cliente: Filtro por cliente
            incluir_anulados: Incluir registros anulados
            pagina: Página actual (1-based)
            limite: Registros por página
            
        Returns:
            Dict con registros, total y metadatos de paginación
        """
        try:
            # Construir filtros
            filtros = {"empresa_id": empresa_id}
            
            if periodo_inicio and periodo_fin:
                filtros["periodo"] = {"$gte": periodo_inicio, "$lte": periodo_fin}
            elif periodo_inicio:
                filtros["periodo"] = {"$gte": periodo_inicio}
            elif periodo_fin:
                filtros["periodo"] = {"$lte": periodo_fin}
            
            if tipo_comprobante:
                filtros["tipo_comprobante"] = tipo_comprobante.value
            
            if numero_documento_cliente:
                filtros["numero_documento_cliente"] = numero_documento_cliente
            
            if not incluir_anulados:
                filtros["estado_operacion"] = {"$ne": EstadoOperacionVenta.ANULADO.value}
            
            # Calcular skip para paginación
            skip = (pagina - 1) * limite
            
            # Ejecutar consultas en paralelo
            registros_cursor = self.collection.find(filtros).skip(skip).limit(limite)
            total_registros = await self.collection.count_documents(filtros)
            
            # Convertir resultados
            registros = []
            async for registro in registros_cursor:
                registros.append(self._convertir_a_response(registro))
            
            # Calcular metadatos de paginación
            total_paginas = (total_registros + limite - 1) // limite
            
            return {
                "registros": registros,
                "total_registros": total_registros,
                "pagina_actual": pagina,
                "total_paginas": total_paginas,
                "limite": limite,
                "tiene_siguiente": pagina < total_paginas,
                "tiene_anterior": pagina > 1
            }
            
        except Exception as e:
            self.logger.error(f"Error listando registros de ventas: {str(e)}")
            raise BusinessLogicException(f"Error interno listando registros: {str(e)}")
    
    # ================================
    # GENERACIÓN PLE 140000
    # ================================
    
    async def generar_ple_ventas(
        self,
        opciones: PLEVentasExportOptions
    ) -> PLEVentasExportResult:
        """
        Generar archivo PLE 140000 (Registro de Ventas)
        
        Args:
            opciones: Opciones de exportación
            
        Returns:
            PLEVentasExportResult: Resultado de la generación
        """
        try:
            inicio_tiempo = datetime.utcnow()
            
            # Obtener registros para el PLE
            registros = await self._obtener_registros_para_ple(opciones)
            
            if not registros:
                return PLEVentasExportResult(
                    nombre_archivo="",
                    contenido_archivo="",
                    tamaño_archivo=0,
                    total_registros=0,
                    registros_exportados=0,
                    registros_excluidos=0,
                    registros_con_errores=0,
                    fecha_generacion=inicio_tiempo,
                    periodo_procesado=f"{opciones.periodo_inicio}-{opciones.periodo_fin}",
                    empresa_id=opciones.empresa_id,
                    resumen_montos={},
                    errores_encontrados=["No se encontraron registros para el período especificado"],
                    warnings=[]
                )
            
            # Formatear registros a líneas PLE
            lineas_ple = []
            errores = []
            total_importe = Decimal('0.00')
            total_igv = Decimal('0.00')
            total_exportaciones = Decimal('0.00')
            
            for registro in registros:
                try:
                    linea = self.ple_formatter.formatear_registro_venta(
                        registro, 
                        opciones.periodo_inicio
                    )
                    lineas_ple.append(linea)
                    
                    # Acumular totales
                    total_importe += registro.importe_total
                    total_igv += registro.igv_ipm
                    total_exportaciones += registro.valor_facturado_exportacion
                    
                except Exception as e:
                    errores.append(f"Error formateando registro {registro.id}: {str(e)}")
            
            # Generar contenido del archivo
            contenido_archivo = self.ple_formatter.generar_contenido_archivo_ple(lineas_ple)
            
            # Generar nombre del archivo
            empresa_doc = await self._obtener_documento_empresa(opciones.empresa_id)
            ruc_empresa = empresa_doc.get("ruc", "00000000000")
            
            nombre_archivo = self.ple_formatter.generar_nombre_archivo_ple(
                empresa_ruc=ruc_empresa,
                periodo_aaaamm=opciones.periodo_inicio,
                correlativo=opciones.correlativo_archivo
            )
            
            # Preparar resultado
            resultado = PLEVentasExportResult(
                nombre_archivo=nombre_archivo,
                contenido_archivo=contenido_archivo,
                tamaño_archivo=len(contenido_archivo.encode('utf-8')),
                total_registros=len(registros),
                registros_exportados=len(lineas_ple),
                registros_excluidos=len(registros) - len(lineas_ple),
                registros_con_errores=len(errores),
                fecha_generacion=inicio_tiempo,
                periodo_procesado=f"{opciones.periodo_inicio}-{opciones.periodo_fin}",
                empresa_id=opciones.empresa_id,
                resumen_montos={
                    "total_importe": total_importe,
                    "total_igv": total_igv,
                    "total_base_gravada": sum(r.base_imponible_gravada for r in registros),
                    "total_exportaciones": total_exportaciones
                },
                errores_encontrados=errores,
                warnings=[]
            )
            
            self.logger.info(f"PLE generado: {nombre_archivo}, {len(lineas_ple)} registros")
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error generando PLE de ventas: {str(e)}")
            raise BusinessLogicException(f"Error interno generando PLE: {str(e)}")
    
    # ================================
    # MÉTODOS PRIVADOS DE VALIDACIÓN
    # ================================
    
    async def _validar_comprobante_unico(
        self,
        empresa_id: str,
        tipo_comprobante: TipoComprobanteVenta,
        serie: Optional[str],
        numero: str,
        periodo: str,
        excluir_id: Optional[str] = None
    ):
        """Validar que el comprobante no esté duplicado"""
        filtros = {
            "empresa_id": empresa_id,
            "tipo_comprobante": tipo_comprobante.value,
            "numero_comprobante": numero,
            "periodo": periodo,
            "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
        }
        
        if serie:
            filtros["serie_comprobante"] = serie
        
        if excluir_id:
            filtros["_id"] = {"$ne": ObjectId(excluir_id)}
        
        existente = await self.collection.find_one(filtros)
        
        if existente:
            raise ValidationException(
                f"Ya existe un comprobante {tipo_comprobante.name} "
                f"con serie '{serie}' y número '{numero}' en el período {periodo}"
            )
    
    def _validar_consistencia_montos(self, venta_data: RegistroVentaRequest):
        """Validar consistencia de montos en el registro"""
        # Sumar todas las bases imponibles y conceptos
        total_bases = (
            venta_data.valor_facturado_exportacion +
            venta_data.base_imponible_gravada +
            venta_data.importe_exonerado +
            venta_data.importe_inafecto +
            venta_data.base_imponible_ivap +
            venta_data.base_imponible_icbper
        )
        
        # Sumar todos los tributos
        total_tributos = (
            venta_data.igv_ipm +
            venta_data.isc +
            venta_data.ivap +
            venta_data.icbper +
            venta_data.otros_tributos_cargos +
            venta_data.otros_conceptos_tributos
        )
        
        # Restar descuentos
        total_descuentos = (
            venta_data.descuento_base_imponible +
            venta_data.descuento_igv_ipm
        )
        
        # Verificar que la suma se aproxime al total
        suma_calculada = total_bases + total_tributos - total_descuentos
        diferencia = abs(suma_calculada - venta_data.importe_total)
        
        if diferencia > Decimal('0.05'):  # Tolerancia para redondeos
            raise ValidationException(
                f"Inconsistencia en montos: suma calculada ({suma_calculada}) "
                f"vs importe total ({venta_data.importe_total}). "
                f"Diferencia: {diferencia}"
            )
    
    async def _obtener_registros_para_ple(
        self,
        opciones: PLEVentasExportOptions
    ) -> List[RegistroVentaResponse]:
        """Obtener registros filtrados para generar PLE"""
        filtros = {
            "empresa_id": opciones.empresa_id,
            "periodo": {"$gte": opciones.periodo_inicio, "$lte": opciones.periodo_fin}
        }
        
        if opciones.tipo_comprobante:
            filtros["tipo_comprobante"] = opciones.tipo_comprobante.value
        
        if opciones.tipo_documento_cliente:
            filtros["tipo_documento_cliente"] = opciones.tipo_documento_cliente.value
        
        if opciones.estado_operacion:
            filtros["estado_operacion"] = opciones.estado_operacion.value
        elif not opciones.incluir_anulados:
            filtros["estado_operacion"] = {"$ne": EstadoOperacionVenta.ANULADO.value}
        
        if opciones.solo_errores:
            filtros["indicador_error"] = {"$ne": "0"}
        
        # Ordenar por fecha de emisión
        cursor = self.collection.find(filtros).sort("fecha_emision", 1)
        
        registros = []
        async for documento in cursor:
            registros.append(self._convertir_a_response(documento))
        
        return registros
    
    async def _obtener_documento_empresa(self, empresa_id: str) -> Dict[str, Any]:
        """Obtener documento de empresa desde la base de datos (empresa_id = RUC)"""
        empresa = await self.db.companies.find_one({"ruc": empresa_id})
        if not empresa:
            raise NotFoundException(f"Empresa {empresa_id} no encontrada")
        return empresa

    # ================================
    # RESUMEN / ESTADÍSTICAS
    # ================================

    async def obtener_resumen_periodo(
        self,
        empresa_id: str,
        periodo_aaaamm: str
    ) -> Dict[str, Any]:
        """
        Obtener resumen estadístico de ventas para un período (AAAAMM)

        Args:
            empresa_id: ID de la empresa
            periodo_aaaamm: Período AAAAMM

        Returns:
            Dict con totales, desglose por comprobante y top clientes
        """
        try:
            filtro = {
                "empresa_id": empresa_id,
                "periodo": periodo_aaaamm,
                "estado_operacion": {"$ne": EstadoOperacionVenta.ANULADO.value}
            }

            pipeline_totales = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "total_registros": {"$sum": 1},
                        "total_monto": {"$sum": {"$toDouble": "$importe_total"}},
                        "total_igv": {"$sum": {"$toDouble": "$igv_ipm"}},
                        "clientes_unicos": {"$addToSet": "$numero_documento_cliente"}
                    }
                }
            ]

            pipeline_por_tipo = [
                {"$match": filtro},
                {"$group": {"_id": "$tipo_comprobante", "total": {"$sum": 1}}}
            ]

            pipeline_top_clientes = [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": "$numero_documento_cliente",
                        "nombres": {"$last": "$razon_social_cliente"},
                        "monto_total": {"$sum": {"$toDouble": "$importe_total"}},
                        "cantidad_ventas": {"$sum": 1}
                    }
                },
                {"$sort": {"monto_total": -1}},
                {"$limit": 5}
            ]

            resultado_totales = await self.collection.aggregate(pipeline_totales).to_list(length=1)
            resultado_por_tipo = await self.collection.aggregate(pipeline_por_tipo).to_list(length=None)
            resultado_top_clientes = await self.collection.aggregate(pipeline_top_clientes).to_list(length=None)

            totales = resultado_totales[0] if resultado_totales else {
                "total_registros": 0, "total_monto": 0.0, "total_igv": 0.0, "clientes_unicos": []
            }
            total_registros = totales["total_registros"]
            total_monto = totales["total_monto"]

            return {
                "periodo": periodo_aaaamm,
                "empresa_id": empresa_id,
                "total_registros": total_registros,
                "total_monto": total_monto,
                "total_igv": totales["total_igv"],
                "promedio_venta": (total_monto / total_registros) if total_registros else 0.0,
                "clientes_unicos": len(totales["clientes_unicos"]),
                "comprobantes_por_tipo": {r["_id"]: r["total"] for r in resultado_por_tipo},
                "montos_por_mes": [
                    {"mes": periodo_aaaamm, "monto": total_monto, "cantidad": total_registros}
                ] if total_registros else [],
                "top_clientes": [
                    {
                        "documento": r["_id"],
                        "nombres": r.get("nombres", ""),
                        "monto_total": r["monto_total"],
                        "cantidad_ventas": r["cantidad_ventas"]
                    }
                    for r in resultado_top_clientes
                ]
            }

        except Exception as e:
            self.logger.error(f"Error obteniendo resumen del período {periodo_aaaamm}: {str(e)}")
            raise BusinessLogicException(f"Error interno obteniendo resumen: {str(e)}")

    # ================================
    # EXPORTACIÓN A EXCEL
    # ================================

    async def exportar_excel(
        self,
        empresa_id: str,
        periodo_inicio: Optional[str] = None,
        periodo_fin: Optional[str] = None,
        incluir_anulados: bool = False
    ) -> bytes:
        """Exportar registros de ventas filtrados a un archivo .xlsx"""
        from openpyxl import Workbook

        resultado = await self.listar_registros_ventas(
            empresa_id=empresa_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            incluir_anulados=incluir_anulados,
            limite=10000
        )
        registros = resultado["registros"]

        wb = Workbook()
        ws = wb.active
        ws.title = "Registro de Ventas"

        columnas = [
            "fecha_emision", "tipo_comprobante", "serie_comprobante", "numero_comprobante",
            "tipo_documento_cliente", "numero_documento_cliente", "razon_social_cliente",
            "base_imponible_gravada", "igv_ipm", "importe_total", "estado_operacion"
        ]
        ws.append(columnas)

        for registro in registros:
            fila = registro.dict()
            ws.append([str(fila.get(col, "")) for col in columnas])

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
    
    def _convertir_a_response(self, documento: Dict[str, Any]) -> RegistroVentaResponse:
        """Convertir documento MongoDB a modelo de respuesta"""
        documento["id"] = str(documento.pop("_id"))
        return RegistroVentaResponse(**documento)
