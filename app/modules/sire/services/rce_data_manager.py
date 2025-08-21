"""
Servicio de Gestión de Datos RCE
Lógica de negocio para manejo de comprobantes en base de datos local
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from ..repositories.rce_data_repository import RceComprobanteRepository
from ..models.rce_data_models import (
    RceComprobante, RceResumenPeriodo, RceEstadisticasProveedor,
    RceConfiguracionPeriodo, RceLogOperacion,
    RceTipoDocumento, RceEstadoComprobante, RceMoneda, RceProveedor
)
from ..schemas.rce_schemas import (
    RceComprobanteCreateRequest, RceComprobanteResponse,
    RceConsultaRequest, RceConsultaResponse
)
from ....shared.exceptions import SireException, SireValidationException


class RceDataManager:
    """Manager para gestión completa de datos RCE"""
    
    def __init__(self):
        self.repository = RceComprobanteRepository()
    
    async def inicializar(self):
        """Inicializar manager y crear índices necesarios"""
        await self.repository.inicializar_indices()
    
    # ========================================
    # GESTIÓN DE COMPROBANTES
    # ========================================
    
    async def crear_comprobante_desde_sunat(
        self, 
        ruc: str, 
        datos_sunat: Dict[str, Any]
    ) -> str:
        """Crear comprobante desde datos descargados de SUNAT"""
        try:
            # Parsear datos de SUNAT al formato interno
            comprobante = await self._parsear_comprobante_sunat(ruc, datos_sunat)
            
            # Validar datos
            await self._validar_comprobante(comprobante)
            
            # Crear en base de datos
            comprobante_id = await self.repository.crear_comprobante(comprobante)
            
            return comprobante_id
            
        except Exception as e:
            raise SireException(f"Error creando comprobante desde SUNAT: {str(e)}")
    
    async def crear_comprobante_manual(
        self, 
        ruc: str, 
        request: RceComprobanteCreateRequest
    ) -> str:
        """Crear comprobante manualmente"""
        try:
            # Convertir request a modelo interno
            comprobante = await self._convertir_request_a_modelo(ruc, request)
            
            # Validar datos
            await self._validar_comprobante(comprobante)
            
            # Crear en base de datos
            comprobante_id = await self.repository.crear_comprobante(comprobante)
            
            return comprobante_id
            
        except Exception as e:
            raise SireException(f"Error creando comprobante manual: {str(e)}")
    
    async def obtener_comprobantes_periodo(
        self,
        ruc: str,
        periodo: str,
        filtros: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RceComprobanteResponse], int]:
        """Obtener comprobantes de un período con filtros"""
        try:
            # Aplicar filtros adicionales
            filtros = filtros or {}
            
            comprobantes, total = await self.repository.obtener_comprobantes(
                ruc=ruc,
                periodo=periodo,
                fecha_inicio=filtros.get("fecha_inicio"),
                fecha_fin=filtros.get("fecha_fin"),
                tipo_comprobante=filtros.get("tipo_comprobante"),
                estado=filtros.get("estado"),
                ruc_proveedor=filtros.get("ruc_proveedor"),
                texto_busqueda=filtros.get("texto_busqueda"),
                skip=skip,
                limit=limit
            )
            
            # Convertir a response
            responses = [
                await self._convertir_modelo_a_response(comp) 
                for comp in comprobantes
            ]
            
            return responses, total
            
        except Exception as e:
            raise SireException(f"Error obteniendo comprobantes: {str(e)}")
    
    async def actualizar_comprobante(
        self, 
        comprobante_id: str, 
        datos_actualizacion: Dict[str, Any]
    ) -> bool:
        """Actualizar un comprobante existente"""
        try:
            # Validar datos de actualización
            await self._validar_datos_actualizacion(datos_actualizacion)
            
            return await self.repository.actualizar_comprobante(
                comprobante_id, 
                datos_actualizacion
            )
            
        except Exception as e:
            raise SireException(f"Error actualizando comprobante: {str(e)}")
    
    async def eliminar_comprobante(self, comprobante_id: str) -> bool:
        """Eliminar (anular) un comprobante"""
        return await self.repository.eliminar_comprobante(comprobante_id)
    
    # ========================================
    # OPERACIONES MASIVAS
    # ========================================
    
    async def importar_comprobantes_masivo(
        self, 
        ruc: str, 
        periodo: str,
        comprobantes_sunat: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Importar comprobantes masivamente desde SUNAT"""
        resultado = {
            "total_procesados": 0,
            "exitosos": 0,
            "errores": 0,
            "duplicados": 0,
            "detalles_errores": []
        }
        
        for datos_comprobante in comprobantes_sunat:
            try:
                resultado["total_procesados"] += 1
                
                # Verificar si ya existe
                if await self._existe_comprobante_sunat(ruc, datos_comprobante):
                    resultado["duplicados"] += 1
                    continue
                
                # Crear comprobante
                await self.crear_comprobante_desde_sunat(ruc, datos_comprobante)
                resultado["exitosos"] += 1
                
            except Exception as e:
                resultado["errores"] += 1
                resultado["detalles_errores"].append({
                    "comprobante": datos_comprobante.get("serie", "") + "-" + datos_comprobante.get("numero", ""),
                    "error": str(e)
                })
        
        return resultado
    
    async def validar_comprobantes_periodo(
        self, 
        ruc: str, 
        periodo: str
    ) -> Dict[str, Any]:
        """Validar todos los comprobantes de un período"""
        comprobantes, _ = await self.repository.obtener_comprobantes(
            ruc=ruc,
            periodo=periodo,
            limit=10000  # Procesar en lotes si es necesario
        )
        
        resultado = {
            "total_comprobantes": len(comprobantes),
            "validos": 0,
            "con_errores": 0,
            "errores_encontrados": []
        }
        
        for comprobante in comprobantes:
            try:
                await self._validar_comprobante(comprobante)
                resultado["validos"] += 1
                
                # Marcar como validado si no tiene errores
                await self.repository.actualizar_comprobante(
                    comprobante.id,
                    {"estado": RceEstadoComprobante.VALIDADO.value}
                )
                
            except Exception as e:
                resultado["con_errores"] += 1
                resultado["errores_encontrados"].append({
                    "comprobante_id": comprobante.id,
                    "serie_numero": f"{comprobante.serie}-{comprobante.numero}",
                    "error": str(e)
                })
                
                # Marcar como observado
                await self.repository.actualizar_comprobante(
                    comprobante.id,
                    {"estado": RceEstadoComprobante.OBSERVADO.value}
                )
        
        return resultado
    
    # ========================================
    # RESÚMENES Y ESTADÍSTICAS
    # ========================================
    
    async def obtener_resumen_periodo(self, ruc: str, periodo: str) -> RceResumenPeriodo:
        """Obtener resumen completo del período"""
        return await self.repository.calcular_resumen_periodo(ruc, periodo)
    
    async def obtener_estadisticas_proveedores(
        self, 
        ruc: str, 
        periodo: str, 
        limit: int = 20
    ) -> List[RceEstadisticasProveedor]:
        """Obtener estadísticas por proveedor"""
        return await self.repository.obtener_estadisticas_proveedores(ruc, periodo, limit)
    
    async def comparar_con_sunat(
        self, 
        ruc: str, 
        periodo: str,
        datos_sunat: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comparar datos locales con resumen de SUNAT"""
        resumen_local = await self.obtener_resumen_periodo(ruc, periodo)
        
        # Extraer datos de SUNAT
        total_sunat = datos_sunat.get("total_documentos", 0)
        importe_sunat = float(datos_sunat.get("total_cp", 0))
        
        # Comparación
        diferencias = {
            "cantidad_local": resumen_local.total_comprobantes,
            "cantidad_sunat": total_sunat,
            "diferencia_cantidad": resumen_local.total_comprobantes - total_sunat,
            "importe_local": float(resumen_local.total_importe_periodo),
            "importe_sunat": importe_sunat,
            "diferencia_importe": float(resumen_local.total_importe_periodo) - importe_sunat,
            "coincide": (
                resumen_local.total_comprobantes == total_sunat and 
                abs(float(resumen_local.total_importe_periodo) - importe_sunat) < 0.01
            )
        }
        
        return diferencias
    
    # ========================================
    # CONFIGURACIÓN Y PERÍODOS
    # ========================================
    
    async def configurar_periodo(
        self, 
        ruc: str, 
        periodo: str,
        configuracion: Dict[str, Any]
    ) -> RceConfiguracionPeriodo:
        """Configurar un período específico"""
        config_existente = await self.repository.obtener_configuracion_periodo(ruc, periodo)
        
        if config_existente:
            # Actualizar configuración existente
            for key, value in configuracion.items():
                setattr(config_existente, key, value)
            config = config_existente
        else:
            # Crear nueva configuración
            config = RceConfiguracionPeriodo(
                ruc=ruc,
                periodo=periodo,
                **configuracion
            )
        
        await self.repository.guardar_configuracion_periodo(config)
        return config
    
    async def cerrar_periodo(self, ruc: str, periodo: str) -> bool:
        """Cerrar un período (no permitir más modificaciones)"""
        try:
            config = await self.repository.obtener_configuracion_periodo(ruc, periodo)
            if not config:
                config = RceConfiguracionPeriodo(ruc=ruc, periodo=periodo)
            
            config.estado_periodo = "cerrado"
            config.fecha_cierre = datetime.now()
            
            await self.repository.guardar_configuracion_periodo(config)
            return True
            
        except Exception:
            return False
    
    # ========================================
    # AUDITORÍA Y LOGS
    # ========================================
    
    async def obtener_logs_periodo(
        self, 
        ruc: str, 
        periodo: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[RceLogOperacion], int]:
        """Obtener logs de operaciones del período"""
        return await self.repository.obtener_logs(
            ruc=ruc,
            periodo=periodo,
            skip=skip,
            limit=limit
        )
    
    # ========================================
    # MÉTODOS PRIVADOS DE VALIDACIÓN Y CONVERSIÓN
    # ========================================
    
    async def _parsear_comprobante_sunat(
        self, 
        ruc: str, 
        datos_sunat: Dict[str, Any]
    ) -> RceComprobante:
        """Convertir datos de SUNAT a modelo interno"""
        # Mapear campos de SUNAT a nuestro modelo
        proveedor = RceProveedor(
            tipo_documento=datos_sunat.get("tipo_documento_proveedor", "6"),
            numero_documento=datos_sunat.get("ruc_proveedor", ""),
            razon_social=datos_sunat.get("razon_social_proveedor", "")
        )
        
        comprobante = RceComprobante(
            ruc_adquiriente=ruc,
            periodo=datos_sunat.get("periodo", ""),
            correlativo=0,  # Se asignará automáticamente
            fecha_emision=datetime.strptime(datos_sunat.get("fecha_emision", ""), "%Y-%m-%d").date(),
            tipo_comprobante=RceTipoDocumento(datos_sunat.get("tipo_documento", "01")),
            serie=datos_sunat.get("serie_comprobante", ""),
            numero=datos_sunat.get("numero_comprobante", ""),
            proveedor=proveedor,
            moneda=RceMoneda(datos_sunat.get("moneda", "PEN")),
            base_imponible_gravada=Decimal(str(datos_sunat.get("base_imponible_gravada", 0))),
            igv=Decimal(str(datos_sunat.get("igv", 0))),
            importe_total=Decimal(str(datos_sunat.get("importe_total", 0))),
            valor_adquisicion_no_gravada=Decimal(str(datos_sunat.get("valor_adquisicion_no_gravada", 0)))
        )
        
        return comprobante
    
    async def _convertir_request_a_modelo(
        self, 
        ruc: str, 
        request: RceComprobanteCreateRequest
    ) -> RceComprobante:
        """Convertir request a modelo interno"""
        proveedor = RceProveedor(
            tipo_documento=request.tipo_documento_proveedor,
            numero_documento=request.numero_documento_proveedor,
            razon_social=request.razon_social_proveedor
        )
        
        comprobante = RceComprobante(
            ruc_adquiriente=ruc,
            periodo=request.periodo,
            correlativo=request.correlativo or 0,
            fecha_emision=request.fecha_emision,
            fecha_vencimiento=request.fecha_vencimiento,
            tipo_comprobante=RceTipoDocumento(request.tipo_comprobante),
            serie=request.serie,
            numero=request.numero,
            proveedor=proveedor,
            moneda=RceMoneda(request.moneda or "PEN"),
            tipo_cambio=request.tipo_cambio,
            base_imponible_gravada=request.base_imponible_operaciones_gravadas,
            igv=request.igv,
            importe_total=request.importe_total,
            sustenta_credito_fiscal=request.sustenta_credito_fiscal,
            sustenta_costo_gasto=request.sustenta_costo_gasto,
            observaciones=request.observaciones
        )
        
        return comprobante
    
    async def _convertir_modelo_a_response(self, comprobante: RceComprobante) -> RceComprobanteResponse:
        """Convertir modelo interno a response"""
        return RceComprobanteResponse(
            periodo=comprobante.periodo,
            correlativo=comprobante.correlativo,
            fecha_emision=comprobante.fecha_emision,
            fecha_vencimiento=comprobante.fecha_vencimiento,
            tipo_comprobante=comprobante.tipo_comprobante.value,
            serie=comprobante.serie,
            numero=comprobante.numero,
            numero_final=comprobante.numero_final,
            tipo_documento_proveedor=comprobante.proveedor.tipo_documento,
            numero_documento_proveedor=comprobante.proveedor.numero_documento,
            razon_social_proveedor=comprobante.proveedor.razon_social,
            moneda=comprobante.moneda.value,
            tipo_cambio=comprobante.tipo_cambio,
            base_imponible_operaciones_gravadas=comprobante.base_imponible_gravada,
            igv=comprobante.igv,
            importe_total=comprobante.importe_total,
            sustenta_credito_fiscal=comprobante.sustenta_credito_fiscal,
            sustenta_costo_gasto=comprobante.sustenta_costo_gasto,
            estado=comprobante.estado.value,
            fecha_registro=comprobante.fecha_registro,
            observaciones=comprobante.observaciones
        )
    
    async def _validar_comprobante(self, comprobante: RceComprobante):
        """Validar datos del comprobante"""
        errores = []
        
        # Validaciones básicas
        if not comprobante.ruc_adquiriente or len(comprobante.ruc_adquiriente) != 11:
            errores.append("RUC adquiriente inválido")
        
        if not comprobante.proveedor.numero_documento:
            errores.append("RUC/documento proveedor requerido")
        
        if comprobante.importe_total <= 0:
            errores.append("Importe total debe ser mayor a cero")
        
        # Validación de coherencia IGV
        if comprobante.base_imponible_gravada > 0:
            igv_calculado = comprobante.base_imponible_gravada * Decimal("0.18")
            if abs(comprobante.igv - igv_calculado) > Decimal("0.01"):
                errores.append("IGV no corresponde a la base imponible gravada")
        
        # Validación de total
        total_calculado = (
            comprobante.base_imponible_gravada + 
            comprobante.base_imponible_exonerada + 
            comprobante.base_imponible_inafecta + 
            comprobante.igv + 
            comprobante.isc + 
            comprobante.otros_tributos
        )
        
        if abs(comprobante.importe_total - total_calculado) > Decimal("0.01"):
            errores.append("Importe total no coincide con la suma de componentes")
        
        if errores:
            raise SireValidationException(f"Errores de validación: {'; '.join(errores)}")
    
    async def _validar_datos_actualizacion(self, datos: Dict[str, Any]):
        """Validar datos de actualización"""
        campos_no_modificables = [
            "ruc_adquiriente", "periodo", "correlativo", "fecha_registro"
        ]
        
        for campo in campos_no_modificables:
            if campo in datos:
                raise SireValidationException(f"El campo {campo} no puede ser modificado")
    
    async def _existe_comprobante_sunat(self, ruc: str, datos_sunat: Dict[str, Any]) -> bool:
        """Verificar si un comprobante de SUNAT ya existe"""
        return await self.repository.existe_comprobante(
            ruc=ruc,
            serie=datos_sunat.get("serie_comprobante", ""),
            numero=datos_sunat.get("numero_comprobante", ""),
            ruc_proveedor=datos_sunat.get("ruc_proveedor", "")
        )
