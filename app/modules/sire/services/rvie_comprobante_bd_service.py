"""
Servicio para gestión de comprobantes RVIE (Ventas) en base de datos
Maneja la lógica de negocio para el almacenamiento local de datos SUNAT
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.rvie_comprobante_bd import (
    RvieComprobanteBD,
    RvieComprobanteBDCreate,
    RvieComprobanteBDResponse,
    RvieEstadisticas
)
from ..repositories.rvie_comprobante_bd_repository import RvieComprobanteBDRepository
from ....shared.exceptions import SireException, SireValidationException


class RvieComprobanteBDService:
    """Servicio para gestión de comprobantes RVIE en BD"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repository = RvieComprobanteBDRepository(db)
    
    async def inicializar(self):
        """Inicializar índices de la base de datos"""
        await self.repository.inicializar_indices()
    
    async def guardar_comprobantes_desde_consulta(self, ruc: str, periodo: str, 
                                                 comprobantes_sunat: List[Dict]) -> Dict[str, Any]:
        """
        Guardar comprobantes desde una consulta SUNAT exitosa
        Este método se llamará después de obtener datos de SUNAT
        """
        try:
            if not comprobantes_sunat:
                return {
                    "success": True,
                    "message": "No hay comprobantes para guardar",
                    "guardados": 0,
                    "actualizados": 0,
                    "errores": [],
                    "total_procesados": 0
                }
            
            # Validar datos de entrada
            self._validar_ruc(ruc)
            self._validar_periodo(periodo)
            
            # Delegar al repositorio
            resultado = await self.repository.guardar_comprobantes_desde_sunat(
                ruc, periodo, comprobantes_sunat
            )
            
            # El repositorio ya incluye un mensaje descriptivo
            if "mensaje" not in resultado:
                # Fallback por si no viene el mensaje del repositorio
                mensaje = f"Procesados {resultado['total_procesados']} comprobantes: "
                mensaje += f"{resultado['guardados']} guardados"
                if resultado.get('reemplazados', 0) > 0:
                    mensaje += f", {resultado['reemplazados']} reemplazados"
                if resultado.get('errores'):
                    mensaje += f", {len(resultado['errores'])} errores"
                resultado["message"] = mensaje
            
            return resultado
            
        except Exception as e:
            raise SireException(f"Error guardando comprobantes RVIE: {str(e)}")
    
    async def consultar_comprobantes(self, ruc: str, periodo: str, skip: int = 0, 
                                   limit: int = 50, filtros: Optional[Dict] = None) -> Dict[str, Any]:
        """Consultar comprobantes guardados en BD"""
        try:
            # Validar parámetros
            self._validar_ruc(ruc)
            self._validar_periodo(periodo)
            self._validar_paginacion(skip, limit)
            
            # Obtener comprobantes y total
            comprobantes, total = await self.repository.consultar_comprobantes(
                ruc, periodo, skip, limit, filtros
            )
            
            # Calcular información de paginación
            total_paginas = (total + limit - 1) // limit
            pagina_actual = (skip // limit) + 1
            
            return {
                "success": True,
                "comprobantes": comprobantes,
                "paginacion": {
                    "total": total,
                    "pagina_actual": pagina_actual,
                    "total_paginas": total_paginas,
                    "por_pagina": limit,
                    "desde": skip + 1 if total > 0 else 0,
                    "hasta": min(skip + limit, total)
                },
                "filtros_aplicados": filtros or {}
            }
            
        except Exception as e:
            raise SireException(f"Error consultando comprobantes RVIE: {str(e)}")
    
    async def obtener_estadisticas(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """Obtener estadísticas de comprobantes guardados"""
        try:
            # Validar parámetros
            self._validar_ruc(ruc)
            self._validar_periodo(periodo)
            
            # Obtener estadísticas
            stats = await self.repository.obtener_estadisticas(ruc, periodo)
            
            return {
                "success": True,
                "estadisticas": stats.dict(),
                "ruc": ruc,
                "periodo": periodo,
                "fecha_consulta": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise SireException(f"Error obteniendo estadísticas RVIE: {str(e)}")
    
    async def obtener_comprobante(self, comprobante_id: str) -> Dict[str, Any]:
        """Obtener un comprobante específico por ID"""
        try:
            comprobante = await self.repository.obtener_por_id(comprobante_id)
            
            if not comprobante:
                raise SireValidationException(f"Comprobante no encontrado: {comprobante_id}")
            
            return {
                "success": True,
                "comprobante": comprobante
            }
            
        except Exception as e:
            raise SireException(f"Error obteniendo comprobante RVIE: {str(e)}")
    
    async def eliminar_comprobante(self, comprobante_id: str) -> Dict[str, Any]:
        """Eliminar un comprobante de la BD"""
        try:
            eliminado = await self.repository.eliminar_comprobante(comprobante_id)
            
            if not eliminado:
                raise SireValidationException(f"Comprobante no encontrado: {comprobante_id}")
            
            return {
                "success": True,
                "message": "Comprobante eliminado exitosamente"
            }
            
        except Exception as e:
            raise SireException(f"Error eliminando comprobante RVIE: {str(e)}")
    
    async def verificar_estado_bd(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """Verificar el estado de la BD para un RUC y período"""
        try:
            # Obtener estadísticas básicas
            stats = await self.repository.obtener_estadisticas(ruc, periodo)
            
            # Verificar si hay datos
            tiene_datos = stats.total_comprobantes > 0
            
            return {
                "success": True,
                "tiene_datos": tiene_datos,
                "total_comprobantes": stats.total_comprobantes,
                "total_monto": stats.total_monto,
                "resumen": {
                    "por_tipo": stats.por_tipo,
                    "por_estado": stats.por_estado
                },
                "ruc": ruc,
                "periodo": periodo
            }
            
        except Exception as e:
            raise SireException(f"Error verificando estado BD RVIE: {str(e)}")
    
    def _validar_ruc(self, ruc: str):
        """Validar formato de RUC"""
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise SireValidationException("RUC debe tener 11 dígitos numéricos")
    
    def _validar_periodo(self, periodo: str):
        """Validar formato de período YYYYMM"""
        if not periodo or len(periodo) != 6 or not periodo.isdigit():
            raise SireValidationException("Período debe tener formato YYYYMM")
        
        año = int(periodo[:4])
        mes = int(periodo[4:])
        
        if año < 2020 or año > 2030:
            raise SireValidationException("Año debe estar entre 2020 y 2030")
        
        if mes < 1 or mes > 12:
            raise SireValidationException("Mes debe estar entre 01 y 12")
    
    def _validar_paginacion(self, skip: int, limit: int):
        """Validar parámetros de paginación"""
        if skip < 0:
            raise SireValidationException("Skip debe ser mayor o igual a 0")
        
        if limit <= 0 or limit > 2000:
            raise SireValidationException("Limit debe estar entre 1 y 2000")
    
    async def limpiar_periodo(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """Limpiar todos los comprobantes de un período específico"""
        try:
            # Validar parámetros
            self._validar_ruc(ruc)
            self._validar_periodo(periodo)
            
            # Contar comprobantes antes de eliminar
            comprobantes, total = await self.repository.consultar_comprobantes(
                ruc, periodo, 0, 1
            )
            
            if total == 0:
                return {
                    "success": True,
                    "message": "No hay comprobantes para eliminar",
                    "eliminados": 0
                }
            
            # Eliminar comprobantes del período
            from bson import ObjectId
            resultado = await self.repository.collection.delete_many({
                "ruc": ruc,
                "periodo": periodo
            })
            
            return {
                "success": True,
                "message": f"Se eliminaron {resultado.deleted_count} comprobantes del período {periodo}",
                "eliminados": resultado.deleted_count
            }
            
        except Exception as e:
            raise SireException(f"Error limpiando período RVIE: {str(e)}")
