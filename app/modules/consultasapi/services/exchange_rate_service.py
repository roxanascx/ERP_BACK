"""
Servicio para consulta de tipos de cambio externos
=================================================

Integra APIs externas para obtener tipos de cambio diarios
Basado en el script agosto_limpia.py verificado y funcional
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

import httpx
from httpx import AsyncClient

from ..models import ExchangeRate, ExchangeRateData
from ..repositories import ExchangeRateRepository
from ..schemas import (
    ExchangeRateCreate, 
    ActualizarTiposCambioResponse,
    ExchangeRateCalculationRequest,
    ExchangeRateCalculationResponse
)

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Servicio para gestión de tipos de cambio"""
    
    def __init__(self):
        self.repository = ExchangeRateRepository()
        self.api_base_url = "https://free.e-api.net.pe/tipo-cambio"
        self.timeout = 15
        self.retry_attempts = 3
        self.retry_delay = 1  # segundos
    
    async def consultar_tipo_cambio_dia(self, fecha: date) -> Optional[ExchangeRateData]:
        """
        Consulta tipo de cambio para un día específico desde eApiPeru
        Basado en el script agosto_limpia.py verificado
        """
        fecha_str = fecha.strftime("%Y-%m-%d")
        url = f"{self.api_base_url}/{fecha_str}.json"
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ERP-TipoCambio/1.0'
        }
        
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"Consultando tipo de cambio para {fecha_str} (intento {attempt + 1})")
                
                async with AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Validar que tenga los campos necesarios
                        if 'compra' in data and 'venta' in data:
                            result = ExchangeRateData(
                                fecha=fecha,
                                compra=Decimal(str(data['compra'])),
                                venta=Decimal(str(data['venta'])),
                                sunat=Decimal(str(data.get('sunat', 0))) if data.get('sunat') else None,
                                moneda_origen="USD",
                                moneda_destino="PEN"
                            )
                            
                            logger.info(f"✅ {fecha_str}: Compra: {result.compra} | Venta: {result.venta}")
                            return result
                        else:
                            logger.warning(f"❌ {fecha_str}: Formato inválido en respuesta")
                            
                    elif response.status_code == 404:
                        logger.warning(f"❌ {fecha_str}: No se encontraron datos")
                        return None
                    else:
                        logger.warning(f"❌ {fecha_str}: Error HTTP {response.status_code}")
                        
            except httpx.TimeoutException:
                logger.warning(f"⏰ {fecha_str}: Timeout en intento {attempt + 1}")
            except httpx.RequestError as e:
                logger.warning(f"🌐 {fecha_str}: Error de conexión en intento {attempt + 1}: {e}")
            except Exception as e:
                logger.error(f"💥 {fecha_str}: Error inesperado en intento {attempt + 1}: {e}")
            
            # Esperar antes del siguiente intento (excepto en el último)
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_delay)
        
        logger.error(f"❌ {fecha_str}: Fallaron todos los intentos de consulta")
        return None
    
    async def guardar_tipo_cambio(self, data: ExchangeRateData, fuente: str = "eApiPeru") -> Optional[ExchangeRate]:
        """Guarda un tipo de cambio en la base de datos"""
        try:
            # Verificar si ya existe
            existe = await self.repository.exchange_rate_exists(
                data.fecha, 
                data.moneda_origen, 
                data.moneda_destino
            )
            
            if existe:
                logger.info(f"Tipo de cambio para {data.fecha} ya existe, omitiendo")
                return await self.repository.get_exchange_rate_by_date(
                    data.fecha, 
                    data.moneda_origen, 
                    data.moneda_destino
                )
            
            # Crear nuevo registro
            exchange_rate = ExchangeRate(
                fecha=data.fecha,
                moneda_origen=data.moneda_origen,
                moneda_destino=data.moneda_destino,
                compra=data.compra,
                venta=data.venta,
                oficial=data.sunat,
                fuente=fuente,
                es_oficial=True,
                es_activo=True,
                notas=f"Consultado automáticamente desde {fuente}"
            )
            
            resultado = await self.repository.create_exchange_rate(exchange_rate)
            logger.info(f"✅ Guardado tipo de cambio para {data.fecha}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error guardando tipo de cambio para {data.fecha}: {e}")
            raise
    
    async def actualizar_tipo_cambio_dia(
        self, 
        fecha: date, 
        forzar: bool = False
    ) -> Dict[str, Any]:
        """Actualiza el tipo de cambio para un día específico"""
        try:
            # Verificar si ya existe y no forzar
            if not forzar:
                existe = await self.repository.exchange_rate_exists(fecha)
                if existe:
                    return {
                        "success": True,
                        "message": f"Tipo de cambio para {fecha} ya existe",
                        "action": "skipped",
                        "data": await self.repository.get_exchange_rate_by_date(fecha)
                    }
            
            # Consultar datos externos
            data = await self.consultar_tipo_cambio_dia(fecha)
            
            if not data:
                return {
                    "success": False,
                    "message": f"No se pudieron obtener datos para {fecha}",
                    "action": "failed",
                    "data": None
                }
            
            # Guardar en base de datos
            if forzar:
                # Buscar registro existente para actualizar
                existing = await self.repository.get_exchange_rate_by_date(fecha)
                if existing:
                    updates = {
                        "compra": data.compra,
                        "venta": data.venta,
                        "oficial": data.sunat,
                        "updated_at": datetime.utcnow(),
                        "notas": f"Actualizado automáticamente desde eApiPeru"
                    }
                    resultado = await self.repository.update_exchange_rate(existing.id, updates)
                    action = "updated"
                else:
                    resultado = await self.guardar_tipo_cambio(data)
                    action = "created"
            else:
                resultado = await self.guardar_tipo_cambio(data)
                action = "created"
            
            return {
                "success": True,
                "message": f"Tipo de cambio para {fecha} {action} exitosamente",
                "action": action,
                "data": resultado
            }
            
        except Exception as e:
            logger.error(f"Error actualizando tipo de cambio para {fecha}: {e}")
            return {
                "success": False,
                "message": f"Error interno: {str(e)}",
                "action": "error",
                "data": None
            }
    
    async def poblar_datos_historicos(
        self, 
        fecha_inicio: date, 
        fecha_fin: date,
        forzar_actualizacion: bool = False
    ) -> ActualizarTiposCambioResponse:
        """
        Pobla datos históricos de tipos de cambio
        Basado en el script agosto_limpia.py que demostró 100% de éxito
        """
        logger.info(f"Iniciando población de datos históricos desde {fecha_inicio} hasta {fecha_fin}")
        
        registros_procesados = 0
        registros_creados = 0
        registros_actualizados = 0
        registros_error = 0
        detalles = []
        
        fecha_actual = fecha_inicio
        
        while fecha_actual <= fecha_fin:
            try:
                resultado = await self.actualizar_tipo_cambio_dia(fecha_actual, forzar_actualizacion)
                
                registros_procesados += 1
                
                if resultado["success"]:
                    if resultado["action"] == "created":
                        registros_creados += 1
                        detalles.append(f"✅ {fecha_actual}: Creado exitosamente")
                    elif resultado["action"] == "updated":
                        registros_actualizados += 1
                        detalles.append(f"🔄 {fecha_actual}: Actualizado exitosamente")
                    elif resultado["action"] == "skipped":
                        detalles.append(f"⏭️ {fecha_actual}: Ya existe, omitido")
                else:
                    registros_error += 1
                    detalles.append(f"❌ {fecha_actual}: {resultado['message']}")
                
                # Pausa breve para no sobrecargar la API
                await asyncio.sleep(0.3)
                
            except Exception as e:
                registros_error += 1
                detalles.append(f"💥 {fecha_actual}: Error inesperado: {str(e)}")
                logger.error(f"Error procesando {fecha_actual}: {e}")
            
            fecha_actual += timedelta(days=1)
        
        # Calcular estadísticas
        tasa_exito = ((registros_creados + registros_actualizados) / registros_procesados * 100) if registros_procesados > 0 else 0
        
        success = registros_error == 0 or tasa_exito >= 80  # Consideramos éxito si hay al menos 80% de éxito
        
        message = f"Procesados {registros_procesados} registros. "
        message += f"Creados: {registros_creados}, "
        message += f"Actualizados: {registros_actualizados}, "
        message += f"Errores: {registros_error}. "
        message += f"Tasa de éxito: {tasa_exito:.1f}%"
        
        logger.info(f"Población completada: {message}")
        
        return ActualizarTiposCambioResponse(
            success=success,
            message=message,
            registros_procesados=registros_procesados,
            registros_creados=registros_creados,
            registros_actualizados=registros_actualizados,
            registros_error=registros_error,
            fecha_desde=fecha_inicio,
            fecha_hasta=fecha_fin,
            detalles=detalles
        )
    
    async def get_tipo_cambio_actual(
        self, 
        moneda_origen: str = "USD", 
        moneda_destino: str = "PEN"
    ) -> Optional[ExchangeRate]:
        """Obtiene el tipo de cambio más actual disponible"""
        try:
            # Intentar obtener el tipo de cambio de hoy
            hoy = date.today()
            resultado = await self.repository.get_exchange_rate_by_date(hoy, moneda_origen, moneda_destino)
            
            if resultado:
                return resultado
            
            # Si no existe para hoy, intentar consultarlo
            logger.info(f"No existe tipo de cambio para hoy ({hoy}), consultando API externa")
            await self.actualizar_tipo_cambio_dia(hoy)
            
            # Intentar obtenerlo nuevamente
            resultado = await self.repository.get_exchange_rate_by_date(hoy, moneda_origen, moneda_destino)
            
            if resultado:
                return resultado
            
            # Si aún no existe, obtener el más reciente
            logger.info("No se pudo obtener para hoy, obteniendo el más reciente")
            return await self.repository.get_latest_exchange_rate(moneda_origen, moneda_destino)
            
        except Exception as e:
            logger.error(f"Error obteniendo tipo de cambio actual: {e}")
            raise
    
    async def calcular_conversion(
        self, 
        request: ExchangeRateCalculationRequest
    ) -> ExchangeRateCalculationResponse:
        """Calcula la conversión entre monedas"""
        try:
            fecha = request.fecha or date.today()
            
            # Obtener tipo de cambio para la fecha
            exchange_rate = await self.repository.get_exchange_rate_by_date(
                fecha, 
                request.moneda_origen, 
                request.moneda_destino
            )
            
            if not exchange_rate:
                # Intentar obtener el más reciente
                exchange_rate = await self.repository.get_latest_exchange_rate(
                    request.moneda_origen, 
                    request.moneda_destino
                )
                
                if not exchange_rate:
                    raise ValueError(f"No se encontró tipo de cambio para {request.moneda_origen} -> {request.moneda_destino}")
            
            # Seleccionar tipo de cambio (compra o venta)
            tipo_cambio_usado = exchange_rate.compra if request.tipo_cambio == "compra" else exchange_rate.venta
            
            # Calcular conversión
            cantidad_convertida = request.cantidad * tipo_cambio_usado
            
            return ExchangeRateCalculationResponse(
                cantidad_original=request.cantidad,
                moneda_origen=request.moneda_origen,
                cantidad_convertida=cantidad_convertida,
                moneda_destino=request.moneda_destino,
                tipo_cambio_usado=tipo_cambio_usado,
                fecha_tipo_cambio=exchange_rate.fecha,
                tipo=request.tipo_cambio
            )
            
        except Exception as e:
            logger.error(f"Error calculando conversión: {e}")
            raise
    
    async def actualizar_tipos_cambio_automatico(self) -> ActualizarTiposCambioResponse:
        """Actualización automática diaria (para usar en tareas programadas)"""
        hoy = date.today()
        return await self.poblar_datos_historicos(hoy, hoy, forzar_actualizacion=True)
    
    async def verificar_estado_servicio(self) -> Dict[str, Any]:
        """Verifica el estado del servicio de tipos de cambio"""
        try:
            # Probar consulta a la API
            test_date = date.today() - timedelta(days=1)  # Ayer para asegurar que existe
            test_result = await self.consultar_tipo_cambio_dia(test_date)
            
            api_disponible = test_result is not None
            
            # Verificar base de datos
            latest_rate = await self.repository.get_latest_exchange_rate()
            
            return {
                "api_externa_disponible": api_disponible,
                "base_datos_disponible": True,  # Si llega aquí, la BD está disponible
                "ultimo_tipo_cambio": latest_rate.fecha if latest_rate else None,
                "total_registros": await self._count_total_records(),
                "fuente_principal": "eApiPeru",
                "url_api": self.api_base_url
            }
            
        except Exception as e:
            logger.error(f"Error verificando estado del servicio: {e}")
            return {
                "api_externa_disponible": False,
                "base_datos_disponible": False,
                "error": str(e)
            }
    
    async def _count_total_records(self) -> int:
        """Cuenta el total de registros de tipos de cambio"""
        try:
            from ..schemas import ExchangeRateQuery
            query = ExchangeRateQuery(es_activo=True)
            _, total = await self.repository.list_exchange_rates(query, 1, 1)
            return total
        except Exception:
            return 0
