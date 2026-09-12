"""
ComprasService - Servicio de negocio para Registro de Compras PLE 080000
========================================================================

Servicio especializado para gestionar el Registro de Compras según 
especificaciones oficiales SUNAT PLE 080000.

Responsabilidades:
- CRUD completo de registros de compras
- Validación de negocio específica para SUNAT
- Generación de archivos PLE 080000 (32 campos oficiales)
- Integración con MongoDB para persistencia
- Cálculos automáticos de totales e IGV

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..schemas.compras_schemas import (
    RegistroCompra,
    RegistroCompraCreate,
    RegistroCompraUpdate,
    RegistroCompraRequest,
    RegistroCompraResponse,
    RegistroCompraFilter,
    PLEComprasMetadata,
    PLEComprasExportOptions,
    PLEComprasExportResult,
    TipoComprobanteCompra,
    TipoDocumentoIdentidad,
    EstadoOperacion,
    ValidationResult
)
from ..ple.ple_formatter_compras import PLEFormatterCompras
from ....shared.exceptions import (
    ValidationException,
    BusinessLogicException,
    NotFoundException
)

logger = logging.getLogger(__name__)


def _a_documento(datos: dict) -> dict:
    """
    Deja el dict listo para Mongo.

    El driver no sabe codificar Decimal y aborta la escritura entera, asi que
    los importes se guardan como float. El registro de compras declara 14
    campos Decimal: crear o editar una compra fallaba siempre con "cannot
    encode object: Decimal", igual que pasaba en ventas.

    Las fechas `date` tampoco viajan: el driver solo entiende `datetime`.
    """
    from datetime import date as _date, datetime as _datetime

    listo = {}
    for campo, valor in datos.items():
        if isinstance(valor, Decimal):
            listo[campo] = float(valor)
        elif isinstance(valor, _date) and not isinstance(valor, _datetime):
            listo[campo] = _datetime(valor.year, valor.month, valor.day)
        else:
            listo[campo] = valor
    return listo


def _codigo(valor) -> str:
    """
    Codigo SUNAT de un campo que puede llegar como texto o como Enum.

    El esquema declara `tipo_comprobante` y compania como `str`, pero el
    servicio hacia `.value` a secas. Cualquier alta o filtro real moria con
    "'str' object has no attribute 'value'".
    """
    if valor is None:
        return ""
    return str(getattr(valor, "value", valor)).strip()


class ComprasService:
    """Servicio de negocio para gestión de compras y generación PLE"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        Inicializar servicio de compras
        
        Args:
            database: Instancia de base de datos MongoDB
        """
        self.db = database
        # `registro_compras`, en plural, igual que `registro_ventas`. Convivian
        # las dos grafias y cada una tenia documentos: lo que escribia una no lo
        # leia la otra.
        self.collection = database.registro_compras
        self.ple_formatter = PLEFormatterCompras()
        self.logger = logging.getLogger(__name__)
    
    # ================================
    # OPERACIONES CRUD PRINCIPALES
    # ================================
    
    async def crear_registro_compra(
        self,
        compra_data: RegistroCompraRequest,
        empresa_id: str,
        periodo: str
    ) -> RegistroCompraResponse:
        """
        Crear nuevo registro de compra con validaciones SUNAT
        
        Args:
            compra_data: Datos del registro de compra
            empresa_id: ID de la empresa
            periodo: Período AAAAMM
            
        Returns:
            RegistroCompraResponse: Registro creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            BusinessLogicException: Si hay errores de negocio
        """
        try:
            # Validar existencia de comprobante
            await self._validar_comprobante_unico(
                empresa_id=empresa_id,
                tipo_comprobante=compra_data.tipo_comprobante,
                serie=compra_data.serie_comprobante,
                numero=compra_data.numero_comprobante,
                periodo=periodo
            )
            
            # Validar consistencia de montos
            self._validar_consistencia_montos(compra_data)
            
            # Preparar documento para MongoDB
            documento = {
                **_a_documento(compra_data.dict()),
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
            self.logger.error(f"Error creando registro de compra: {str(e)}")
            raise BusinessLogicException(f"Error interno creando registro: {str(e)}")
    
    async def obtener_registro_compra(
        self,
        registro_id: str,
        empresa_id: str
    ) -> RegistroCompraResponse:
        """
        Obtener registro de compra por ID
        
        Args:
            registro_id: ID del registro
            empresa_id: ID de la empresa
            
        Returns:
            RegistroCompraResponse: Registro encontrado
            
        Raises:
            NotFoundException: Si no se encuentra el registro
        """
        try:
            registro = await self.collection.find_one({
                "_id": ObjectId(registro_id),
                "empresa_id": empresa_id
            })
            
            if not registro:
                raise NotFoundException(f"Registro de compra {registro_id} no encontrado")
            
            return self._convertir_a_response(registro)
            
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error obteniendo registro {registro_id}: {str(e)}")
            raise BusinessLogicException(f"Error interno obteniendo registro: {str(e)}")
    
    async def actualizar_registro_compra(
        self,
        registro_id: str,
        compra_data: RegistroCompraRequest,
        empresa_id: str
    ) -> RegistroCompraResponse:
        """
        Actualizar registro de compra existente
        
        Args:
            registro_id: ID del registro a actualizar
            compra_data: Nuevos datos del registro
            empresa_id: ID de la empresa
            
        Returns:
            RegistroCompraResponse: Registro actualizado
            
        Raises:
            NotFoundException: Si no se encuentra el registro
            ValidationException: Si los datos no son válidos
        """
        try:
            # Verificar que existe
            registro_existente = await self.obtener_registro_compra(registro_id, empresa_id)
            
            # Validar consistencia de montos
            self._validar_consistencia_montos(compra_data)
            
            # Validar comprobante único (solo si cambió)
            if (compra_data.tipo_comprobante != registro_existente.tipo_comprobante or
                compra_data.serie_comprobante != registro_existente.serie_comprobante or
                compra_data.numero_comprobante != registro_existente.numero_comprobante):
                
                await self._validar_comprobante_unico(
                    empresa_id=empresa_id,
                    tipo_comprobante=compra_data.tipo_comprobante,
                    serie=compra_data.serie_comprobante,
                    numero=compra_data.numero_comprobante,
                    periodo=registro_existente.periodo,
                    excluir_id=registro_id
                )
            
            # Actualizar registro
            datos_actualizacion = {
                **_a_documento(compra_data.dict()),
                "fecha_actualizacion": datetime.utcnow()
            }
            
            await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {"$set": datos_actualizacion}
            )
            
            # Retornar registro actualizado
            return await self.obtener_registro_compra(registro_id, empresa_id)
            
        except (NotFoundException, ValidationException):
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando registro {registro_id}: {str(e)}")
            raise BusinessLogicException(f"Error interno actualizando registro: {str(e)}")
    
    async def eliminar_registro_compra(
        self,
        registro_id: str,
        empresa_id: str
    ) -> bool:
        """
        Eliminar registro de compra (eliminación lógica)
        
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
            await self.obtener_registro_compra(registro_id, empresa_id)
            
            # Marcar como anulado en lugar de eliminar físicamente
            resultado = await self.collection.update_one(
                {"_id": ObjectId(registro_id), "empresa_id": empresa_id},
                {
                    "$set": {
                        "estado_operacion": EstadoOperacion.ANULADO,
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
    
    async def listar_simple(
        self,
        empresa_id: str,
        limite: int = 50
    ) -> List[RegistroCompraResponse]:
        """Método temporal para obtener registros sin filtros complejos"""
        try:
            # Filtro muy simple - solo empresa
            filtros = {"empresa_id": empresa_id}
            
            # Consulta directa sin filtros adicionales
            cursor = self.collection.find(filtros).limit(limite)
            
            registros = []
            async for documento in cursor:
                registro_response = self._convertir_a_response(documento)
                registros.append(registro_response)
            
            return registros
            
        except Exception as e:
            logger.error(f"Error en listar_simple: {str(e)}")
            raise
    
    async def listar_registros_compras(
        self,
        empresa_id: str,
        periodo_inicio: Optional[str] = None,
        periodo_fin: Optional[str] = None,
        tipo_comprobante: Optional[TipoComprobanteCompra] = None,
        numero_documento_proveedor: Optional[str] = None,
        incluir_anulados: bool = False,
        pagina: int = 1,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Listar registros de compras con filtros
        
        Args:
            empresa_id: ID de la empresa
            periodo_inicio: Período inicio AAAAMM
            periodo_fin: Período fin AAAAMM
            tipo_comprobante: Filtro por tipo de comprobante
            numero_documento_proveedor: Filtro por proveedor
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
                filtros["tipo_comprobante"] = _codigo(tipo_comprobante)
            
            if numero_documento_proveedor:
                filtros["numero_documento_proveedor"] = numero_documento_proveedor
            
            if not incluir_anulados:
                # Usar filtro positivo - incluir solo VIGENTE y MODIFICADO
                filtros["estado_operacion"] = "1"  # Solo VIGENTE por ahora
            
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
            self.logger.error(f"Error listando registros de compras: {str(e)}")
            raise BusinessLogicException(f"Error interno listando registros: {str(e)}")
    
    # ================================
    # GENERACIÓN PLE 080000
    # ================================
    
    async def generar_ple_compras(
        self,
        opciones: PLEComprasExportOptions
    ) -> PLEComprasExportResult:
        """
        Generar archivo PLE 080000 (Registro de Compras)
        
        Args:
            opciones: Opciones de exportación
            
        Returns:
            PLEComprasExportResult: Resultado de la generación
        """
        try:
            inicio_tiempo = datetime.utcnow()
            
            # Obtener registros para el PLE
            registros = await self._obtener_registros_para_ple(opciones)
            
            if not registros:
                return PLEComprasExportResult(
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
            
            for registro in registros:
                try:
                    linea = self.ple_formatter.formatear_registro_compra(
                        registro, 
                        opciones.periodo_inicio
                    )
                    lineas_ple.append(linea)
                    
                    # Acumular totales
                    total_importe += registro.importe_total
                    total_igv += registro.igv
                    
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
            resultado = PLEComprasExportResult(
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
                    "total_base_gravada": sum(r.base_imponible_gravada for r in registros)
                },
                errores_encontrados=errores,
                warnings=[]
            )
            
            self.logger.info(f"PLE generado: {nombre_archivo}, {len(lineas_ple)} registros")
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error generando PLE de compras: {str(e)}")
            raise BusinessLogicException(f"Error interno generando PLE: {str(e)}")
    
    # ================================
    # MÉTODOS PRIVADOS DE VALIDACIÓN
    # ================================
    
    async def _validar_comprobante_unico(
        self,
        empresa_id: str,
        tipo_comprobante: TipoComprobanteCompra,
        serie: Optional[str],
        numero: str,
        periodo: str,
        excluir_id: Optional[str] = None
    ):
        """Validar que el comprobante no esté duplicado"""
        filtros = {
            "empresa_id": empresa_id,
            "tipo_comprobante": _codigo(tipo_comprobante),
            "numero_comprobante": numero,
            "periodo": periodo,
            "estado_operacion": {"$ne": EstadoOperacion.ANULADO.value}
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
    
    def _validar_consistencia_montos(self, compra_data: RegistroCompraRequest):
        """Validar consistencia de montos en el registro"""
        # Sumar todas las bases imponibles
        total_bases = (
            compra_data.base_imponible_gravada +
            compra_data.base_imponible_gravada_operaciones_mixtas +
            compra_data.base_imponible_gravada_exportacion +
            compra_data.base_imponible_no_gravada
        )
        
        # Sumar todos los tributos
        total_tributos = (
            compra_data.igv +
            compra_data.igv_operaciones_mixtas +
            compra_data.igv_exportacion +
            compra_data.isc +
            compra_data.otros_tributos
        )
        
        # Verificar que la suma se aproxime al total
        suma_calculada = total_bases + total_tributos
        diferencia = abs(suma_calculada - compra_data.importe_total)
        
        if diferencia > Decimal('0.05'):  # Tolerancia para redondeos
            raise ValidationException(
                f"Inconsistencia en montos: suma calculada ({suma_calculada}) "
                f"vs importe total ({compra_data.importe_total}). "
                f"Diferencia: {diferencia}"
            )
    
    async def _obtener_registros_para_ple(
        self,
        opciones: PLEComprasExportOptions
    ) -> List[RegistroCompraResponse]:
        """Obtener registros filtrados para generar PLE"""
        filtros = {
            "empresa_id": opciones.empresa_id,
            "periodo": {"$gte": opciones.periodo_inicio, "$lte": opciones.periodo_fin}
        }
        
        if opciones.tipo_comprobante:
            filtros["tipo_comprobante"] = opciones.tipo_comprobante.value
        
        if opciones.tipo_documento_proveedor:
            filtros["tipo_documento_proveedor"] = opciones.tipo_documento_proveedor.value
        
        if opciones.estado_operacion:
            filtros["estado_operacion"] = opciones.estado_operacion.value
        elif not opciones.incluir_anulados:
            filtros["estado_operacion"] = {"$ne": EstadoOperacion.ANULADO.value}
        
        if opciones.solo_errores:
            filtros["indicador_error"] = {"$ne": "0"}
        
        # Ordenar por fecha de emisión
        cursor = self.collection.find(filtros).sort("fecha_emision", 1)
        
        registros = []
        async for documento in cursor:
            registros.append(self._convertir_a_response(documento))
        
        return registros
    
    async def _obtener_documento_empresa(self, empresa_id: str) -> Dict[str, Any]:
        """
        Documento de la empresa. `empresa_id` es el RUC, igual que en ventas.

        Buscaba en `empresas` por `_id` convertido a ObjectId: ni la coleccion ni
        la clave eran las correctas, asi que la exportacion moria con
        "is not a valid ObjectId" justo al ir a componer el nombre del archivo.
        """
        empresa = await self.db.companies.find_one({"ruc": empresa_id})
        if not empresa:
            raise NotFoundException(f"Empresa {empresa_id} no encontrada")
        return empresa
    
    def _convertir_a_response(self, documento: Dict[str, Any]) -> RegistroCompraResponse:
        """Convertir documento MongoDB a modelo de respuesta"""
        # Hacer una copia para no modificar el original
        doc_copy = documento.copy()
        doc_copy["id"] = str(doc_copy.pop("_id"))
        
        # Agregar campos faltantes con valores predeterminados
        defaults = {
            "fecha_vencimiento": None,
            "base_imponible_exonerada": 0.00,
            "base_imponible_inafecta": 0.00,
            "isc": 0.00,
            "otros_tributos": 0.00,
            "moneda": "PEN",
            "tipo_cambio": 1.00,
            "clasificacion_bienes_servicios": "1",
            "created_at": None,
            "updated_at": None
        }
        
        for key, default_value in defaults.items():
            if key not in doc_copy:
                doc_copy[key] = default_value
        
        return RegistroCompraResponse(**doc_copy)

    async def obtener_resumen_periodo(
        self,
        empresa_id: str,
        periodo_aaaamm: str
    ) -> Dict[str, Any]:
        """
        Obtener resumen de compras para un período específico
        
        Args:
            empresa_id: ID de la empresa
            periodo_aaaamm: Período en formato AAAAMM
            
        Returns:
            Dict con resumen de compras del período
        """
        try:
            # Pipeline de agregación para obtener estadísticas
            pipeline = [
                {
                    "$match": {
                        "empresa_id": empresa_id,
                        "periodo": periodo_aaaamm,
                        # Los anulados no cuentan, igual que en el listado. Sin
                        # esto las tarjetas dirian una cifra y la tabla otra.
                        "estado_operacion": {"$ne": EstadoOperacion.ANULADO.value},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_registros": {"$sum": 1},
                        # El campo se llama `base_imponible_gravada`. Sumando
                        # `base_imponible`, que no existe, la base salia siempre
                        # en cero aunque hubiera comprobantes gravados.
                        "total_base_imponible": {"$sum": "$base_imponible_gravada"},
                        "total_igv": {"$sum": "$igv"},
                        "total_isc": {"$sum": "$isc"},
                        "total_otros_tributos": {"$sum": "$otros_tributos"},
                        "total_importe": {"$sum": "$importe_total"},
                        "tipos_comprobante": {"$addToSet": "$tipo_comprobante"},
                        "proveedores_unicos": {"$addToSet": "$numero_documento_proveedor"}
                    }
                }
            ]
            
            resultado = await self.collection.aggregate(pipeline).to_list(1)
            
            if resultado:
                resumen = resultado[0]
                return {
                    "empresa_id": empresa_id,
                    "periodo": periodo_aaaamm,
                    "total_registros": resumen.get("total_registros", 0),
                    "total_base_imponible": float(resumen.get("total_base_imponible", 0)),
                    "total_igv": float(resumen.get("total_igv", 0)),
                    "total_isc": float(resumen.get("total_isc", 0)),
                    "total_otros_tributos": float(resumen.get("total_otros_tributos", 0)),
                    "total_importe": float(resumen.get("total_importe", 0)),
                    "tipos_comprobante_count": len(resumen.get("tipos_comprobante", [])),
                    "proveedores_unicos_count": len(resumen.get("proveedores_unicos", []))
                }
            else:
                # Sin datos para el período
                return {
                    "empresa_id": empresa_id,
                    "periodo": periodo_aaaamm,
                    "total_registros": 0,
                    "total_base_imponible": 0.0,
                    "total_igv": 0.0,
                    "total_isc": 0.0,
                    "total_otros_tributos": 0.0,
                    "total_importe": 0.0,
                    "tipos_comprobante_count": 0,
                    "proveedores_unicos_count": 0
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo resumen período {periodo_aaaamm}: {str(e)}")
            raise Exception(f"Error obteniendo resumen: {str(e)}")

    async def obtener_registros_empresa(
        self,
        empresa_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Obtener todos los registros de compras de una empresa con paginación
        
        Args:
            empresa_id: ID de la empresa
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
            
        Returns:
            Dict con registros y metadatos de paginación
        """
        try:
            # Filtro básico por empresa
            filtros = {"empresa_id": empresa_id}
            
            # Obtener total de registros
            total = await self.collection.count_documents(filtros)
            
            # Obtener registros con paginación
            cursor = self.collection.find(filtros).skip(skip).limit(limit)
            registros = await cursor.to_list(length=limit)
            
            # Convertir a formato de respuesta
            registros_response = [self._convertir_a_response(reg) for reg in registros]
            
            return {
                "registros": registros_response,
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + len(registros_response) < total
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo registros empresa {empresa_id}: {str(e)}")
            raise Exception(f"Error obteniendo registros: {str(e)}")

    async def obtener_registro_por_id(self, registro_id: str) -> RegistroCompraResponse:
        """
        Obtener registro de compra por ID (sin validación de empresa)
        
        Args:
            registro_id: ID del registro
            
        Returns:
            RegistroCompraResponse: Registro encontrado
            
        Raises:
            NotFoundException: Si no se encuentra el registro
        """
        try:
            if not ObjectId.is_valid(registro_id):
                raise ValueError(f"ID de registro inválido: {registro_id}")
                
            documento = await self.collection.find_one({"_id": ObjectId(registro_id)})
            
            if not documento:
                raise ValueError(f"Registro no encontrado: {registro_id}")
                
            return self._convertir_a_response(documento)
            
        except Exception as e:
            logger.error(f"Error obteniendo registro {registro_id}: {str(e)}")
            raise Exception(f"Error obteniendo registro: {str(e)}")

    async def crear_registro(
        self,
        registro_data: 'RegistroCompraCreate',
        usuario_id: Optional[str] = None
    ) -> 'RegistroCompraResponse':
        """
        Crear registro de compra simplificado para endpoint
        
        Args:
            registro_data: Datos del registro
            usuario_id: ID del usuario que crea el registro
            
        Returns:
            RegistroCompraResponse: Registro creado
        """
        try:
            # Extraer empresa_id y periodo de los datos
            empresa_id = getattr(registro_data, 'empresa_id', None)
            periodo = getattr(registro_data, 'periodo', None)
            
            if not empresa_id:
                raise ValueError("empresa_id es requerido")
            if not periodo:
                raise ValueError("periodo es requerido")
                
            # Usar el método original
            return await self.crear_registro_compra(registro_data, empresa_id, periodo)
            
        except Exception as e:
            logger.error(f"Error creando registro: {str(e)}")
            raise Exception(f"Error creando registro: {str(e)}")

    async def actualizar_registro(
        self,
        registro_id: str,
        registro_update: 'RegistroCompraUpdate',
        usuario_id: Optional[str] = None
    ) -> 'RegistroCompraResponse':
        """
        Actualizar registro de compra simplificado para endpoint
        
        Args:
            registro_id: ID del registro
            registro_update: Datos a actualizar
            usuario_id: ID del usuario que actualiza
            
        Returns:
            RegistroCompraResponse: Registro actualizado
        """
        try:
            # Para el método original necesitamos empresa_id
            # Vamos a obtener el registro actual para extraer empresa_id
            registro_actual = await self.obtener_registro_por_id(registro_id)
            empresa_id = registro_actual.empresa_id
            
            return await self.actualizar_registro_compra(registro_id, registro_update, empresa_id)
            
        except Exception as e:
            logger.error(f"Error actualizando registro {registro_id}: {str(e)}")
            raise Exception(f"Error actualizando registro: {str(e)}")

    async def eliminar_registro(
        self,
        registro_id: str,
        usuario_id: Optional[str] = None
    ) -> bool:
        """
        Eliminar registro de compra simplificado para endpoint
        
        Args:
            registro_id: ID del registro
            usuario_id: ID del usuario que elimina
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # Para el método original necesitamos empresa_id
            registro_actual = await self.obtener_registro_por_id(registro_id)
            empresa_id = registro_actual.empresa_id
            
            resultado = await self.eliminar_registro_compra(registro_id, empresa_id)
            return bool(resultado)
            
        except Exception as e:
            logger.error(f"Error eliminando registro {registro_id}: {str(e)}")
            raise Exception(f"Error eliminando registro: {str(e)}")

    async def validar_registro(
        self,
        registro_data: 'RegistroCompraCreate'
    ) -> Dict[str, Any]:
        """
        Validar registro de compra
        
        Args:
            registro_data: Datos del registro a validar
            
        Returns:
            Dict con resultado de validación
        """
        try:
            # Validaciones básicas
            errores = []
            advertencias = []
            
            # Validar campos requeridos
            if not getattr(registro_data, 'empresa_id', None):
                errores.append("empresa_id es requerido")
            if not getattr(registro_data, 'periodo', None):
                errores.append("periodo es requerido")
            if not getattr(registro_data, 'numero_documento_proveedor', None):
                errores.append("numero_documento_proveedor es requerido")
                
            # Retornar resultado
            return {
                "valido": len(errores) == 0,
                "errores": errores,
                "advertencias": advertencias
            }
            
        except Exception as e:
            logger.error(f"Error validando registro: {str(e)}")
            return {
                "valido": False,
                "errores": [f"Error en validación: {str(e)}"],
                "advertencias": []
            }
