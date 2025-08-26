"""
Servicio de negocio para Libro Diario
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.modules.accounting.libro_diario_repository import LibroDiarioRepository
from app.modules.accounting.schemas import (
    LibroDiarioCreate,
    LibroDiarioUpdate, 
    LibroDiarioResponse,
    LibroDiarioCreateV2,
    LibroDiarioResponseV2,
    AsientoContableCreate,
    AsientoContableUpdate,
    AsientoContableResponse,
    AsientoContableCreateV2,
    AsientoContableResponseV2,
    FiltrosLibroDiario,
    ResumenLibroDiario,
    ValidationResult,
    ExportOptions
)

logger = logging.getLogger(__name__)


class LibroDiarioService:
    """Servicio de lógica de negocio para Libro Diario"""
    
    def __init__(self):
        self.repository = LibroDiarioRepository()
    
    # =====================================
    # OPERACIONES DE LIBRO DIARIO V2 (FRONTEND-ALIGNED)
    # =====================================
    
    async def crear_libro_diario_v2(
        self, 
        libro_data: LibroDiarioCreateV2,
        usuario_id: Optional[str] = None
    ) -> LibroDiarioResponseV2:
        """Crear un nuevo libro diario v2 (alineado con frontend)"""
        try:
            # Obtener información de la empresa
            empresa_info = await self._obtener_info_empresa(libro_data.empresaId)
            
            # Preparar datos del libro
            libro_dict = libro_data.dict()
            libro_dict.update({
                "ruc": empresa_info.get("ruc", ""),
                "razonSocial": empresa_info.get("razonSocial", ""),
                "usuarioCreacion": usuario_id,
                "totalDebe": 0.0,
                "totalHaber": 0.0,
                "asientos": []  # Inicializar lista vacía
            })
            
            # Crear libro
            libro_creado = await self.repository.crear_libro(libro_dict)
            
            logger.info(f"Libro diario V2 creado: {libro_creado['id']} para empresa {libro_data.empresaId}")
            
            return LibroDiarioResponseV2(**libro_creado)
            
        except Exception as e:
            logger.error(f"Error al crear libro diario: {str(e)}")
            raise
    
    async def listar_libros_por_empresa_v2(
        self, 
        empresa_id: str, 
        filtros: Optional[FiltrosLibroDiario] = None
    ) -> List[LibroDiarioResponseV2]:
        """Listar libros diario por empresa v2 (alineado con frontend)"""
        try:
            filtros_dict = filtros.dict() if filtros else {}
            libros = await self.repository.listar_libros_por_empresa(empresa_id, filtros_dict)
            
            # Transformar datos para Pydantic V2
            libros_response = []
            for libro in libros:
                # Asegurar que los campos requeridos existan
                libro_data = {
                    "id": libro.get("id", ""),
                    "empresaId": libro.get("empresaId", empresa_id),
                    "descripcion": libro.get("descripcion", ""),
                    "periodo": libro.get("periodo", ""),
                    "ruc": libro.get("ruc", ""),
                    "razonSocial": libro.get("razonSocial", ""),
                    "estado": libro.get("estado", "borrador"),
                    "asientos": [],  # Lista vacía para evitar problemas de validación
                    "totalDebe": float(libro.get("totalDebe", 0.0)),
                    "totalHaber": float(libro.get("totalHaber", 0.0)),
                    "fechaCreacion": libro.get("fechaCreacion"),
                    "fechaModificacion": libro.get("fechaModificacion"),
                    "usuarioCreacion": libro.get("usuarioCreacion"),
                    "usuarioModificacion": libro.get("usuarioModificacion"),
                    "moneda": libro.get("moneda", "PEN"),
                    "tipoLibro": libro.get("tipoLibro", "5.1")
                }
                
                libros_response.append(LibroDiarioResponseV2(**libro_data))
            
            return libros_response
            
        except Exception as e:
            logger.error(f"Error al listar libros de empresa {empresa_id}: {str(e)}")
            raise
    
    # =====================================
    # OPERACIONES DE LIBRO DIARIO (LEGACY)
    # =====================================
    
    async def crear_libro_diario(
        self, 
        libro_data: LibroDiarioCreate,
        usuario_id: Optional[str] = None
    ) -> LibroDiarioResponse:
        """Crear un nuevo libro diario"""
        try:
            # Obtener información de la empresa
            empresa_info = await self._obtener_info_empresa(libro_data.empresaId)
            
            # Preparar datos del libro
            libro_dict = libro_data.dict()
            libro_dict.update({
                "ruc": empresa_info.get("ruc", ""),
                "razonSocial": empresa_info.get("razonSocial", ""),
                "usuarioCreacion": usuario_id,
                "totalDebe": 0.0,
                "totalHaber": 0.0
            })
            
            # Crear libro
            libro_creado = await self.repository.crear_libro(libro_dict)
            
            logger.info(f"Libro diario creado: {libro_creado['id']} para empresa {libro_data.empresaId}")
            
            return LibroDiarioResponse(**libro_creado)
            
        except Exception as e:
            logger.error(f"Error al crear libro diario: {str(e)}")
            raise
    
    async def obtener_libro_diario(self, libro_id: str) -> Optional[LibroDiarioResponse]:
        """Obtener un libro diario por ID"""
        try:
            libro = await self.repository.obtener_libro(libro_id)
            if not libro:
                return None
            
            return LibroDiarioResponse(**libro)
            
        except Exception as e:
            logger.error(f"Error al obtener libro diario {libro_id}: {str(e)}")
            raise
    
    async def actualizar_libro_diario(
        self, 
        libro_id: str, 
        libro_data: LibroDiarioUpdate,
        usuario_id: Optional[str] = None
    ) -> Optional[LibroDiarioResponse]:
        """Actualizar un libro diario"""
        try:
            # Preparar datos de actualización
            update_dict = {
                k: v for k, v in libro_data.dict().items() 
                if v is not None
            }
            update_dict["usuarioModificacion"] = usuario_id
            
            # Actualizar libro
            libro_actualizado = await self.repository.actualizar_libro(libro_id, update_dict)
            if not libro_actualizado:
                return None
            
            logger.info(f"Libro diario actualizado: {libro_id}")
            
            return LibroDiarioResponse(**libro_actualizado)
            
        except Exception as e:
            logger.error(f"Error al actualizar libro diario {libro_id}: {str(e)}")
            raise
    
    async def eliminar_libro_diario(self, libro_id: str) -> bool:
        """Eliminar un libro diario"""
        try:
            # Verificar que existe
            libro = await self.repository.obtener_libro(libro_id)
            if not libro:
                return False
            
            # No permitir eliminar libros finalizados o enviados
            if libro.get("estado") in ["finalizado", "enviado"]:
                raise ValueError("No se puede eliminar un libro finalizado o enviado")
            
            # Eliminar
            resultado = await self.repository.eliminar_libro(libro_id)
            
            if resultado:
                logger.info(f"Libro diario eliminado: {libro_id}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al eliminar libro diario {libro_id}: {str(e)}")
            raise
    
    async def listar_libros_por_empresa(
        self, 
        empresa_id: str, 
        filtros: Optional[FiltrosLibroDiario] = None
    ) -> List[LibroDiarioResponse]:
        """Listar libros diario de una empresa con filtros"""
        try:
            # Convertir filtros a dict
            filtros_dict = None
            if filtros:
                filtros_dict = {
                    k: v for k, v in filtros.dict().items() 
                    if v is not None and k != "empresaId"
                }
            
            # Obtener libros
            libros = await self.repository.listar_libros_por_empresa(empresa_id, filtros_dict)
            
            return [LibroDiarioResponse(**libro) for libro in libros]
            
        except Exception as e:
            logger.error(f"Error al listar libros de empresa {empresa_id}: {str(e)}")
            raise
    
    # =====================================
    # OPERACIONES DE ASIENTOS CONTABLES
    # =====================================
    
    async def agregar_asiento(
        self, 
        libro_id: str, 
        asiento_data: AsientoContableCreate,
        usuario_id: Optional[str] = None
    ) -> AsientoContableResponse:
        """Agregar un asiento contable a un libro"""
        try:
            # Validar asiento
            await self._validar_asiento(asiento_data)
            
            # Preparar datos del asiento
            asiento_dict = asiento_data.dict()
            asiento_dict["usuarioCreacion"] = usuario_id
            
            # Si no tiene número correlativo, generarlo
            if not asiento_dict.get("numeroCorrelativo"):
                periodo = self._extraer_periodo_fecha(asiento_dict["fecha"])
                correlativo = await self.repository.obtener_siguiente_correlativo(
                    asiento_data.empresaId, 
                    periodo
                )
                asiento_dict["numeroCorrelativo"] = correlativo
            
            # Agregar asiento
            asiento_creado = await self.repository.agregar_asiento(libro_id, asiento_dict)
            
            logger.info(f"Asiento agregado: {asiento_creado['id']} al libro {libro_id}")
            
            return AsientoContableResponse(**asiento_creado)
            
        except Exception as e:
            logger.error(f"Error al agregar asiento al libro {libro_id}: {str(e)}")
            raise
    
    async def actualizar_asiento(
        self, 
        libro_id: str, 
        asiento_id: str, 
        asiento_data: AsientoContableUpdate,
        usuario_id: Optional[str] = None
    ) -> Optional[AsientoContableResponse]:
        """Actualizar un asiento contable"""
        try:
            # Preparar datos de actualización
            update_dict = {
                k: v for k, v in asiento_data.dict().items() 
                if v is not None
            }
            update_dict["usuarioModificacion"] = usuario_id
            
            # Actualizar asiento
            asiento_actualizado = await self.repository.actualizar_asiento(
                libro_id, asiento_id, update_dict
            )
            
            if not asiento_actualizado:
                return None
            
            logger.info(f"Asiento actualizado: {asiento_id}")
            
            return AsientoContableResponse(**asiento_actualizado)
            
        except Exception as e:
            logger.error(f"Error al actualizar asiento {asiento_id}: {str(e)}")
            raise
    
    async def eliminar_asiento(self, libro_id: str, asiento_id: str) -> bool:
        """Eliminar un asiento contable"""
        try:
            resultado = await self.repository.eliminar_asiento(libro_id, asiento_id)
            
            if resultado:
                logger.info(f"Asiento eliminado: {asiento_id}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al eliminar asiento {asiento_id}: {str(e)}")
            raise
    
    # =====================================
    # OPERACIONES DE VALIDACIÓN Y CONSULTA
    # =====================================
    
    async def validar_libro_diario(self, libro_id: str) -> ValidationResult:
        """Validar un libro diario completo"""
        try:
            resultado = await self.repository.validar_libro(libro_id)
            return ValidationResult(**resultado)
            
        except Exception as e:
            logger.error(f"Error al validar libro {libro_id}: {str(e)}")
            raise
    
    async def obtener_resumen(
        self, 
        empresa_id: str, 
        periodo: Optional[str] = None
    ) -> ResumenLibroDiario:
        """Obtener resumen estadístico"""
        try:
            resumen = await self.repository.obtener_resumen(empresa_id, periodo)
            return ResumenLibroDiario(**resumen)
            
        except Exception as e:
            logger.error(f"Error al obtener resumen para empresa {empresa_id}: {str(e)}")
            raise
    
    async def buscar_cuentas_contables(
        self, 
        busqueda: str, 
        empresa_id: str, 
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """Buscar cuentas contables para autocompletado"""
        try:
            return await self.repository.buscar_cuentas_contables(busqueda, empresa_id, limite)
            
        except Exception as e:
            logger.error(f"Error al buscar cuentas: {str(e)}")
            raise
    
    async def obtener_siguiente_correlativo(self, empresa_id: str, periodo: str) -> str:
        """Obtener siguiente número correlativo"""
        try:
            return await self.repository.obtener_siguiente_correlativo(empresa_id, periodo)
            
        except Exception as e:
            logger.error(f"Error al obtener correlativo: {str(e)}")
            raise
    
    # =====================================
    # OPERACIONES DE EXPORTACIÓN
    # =====================================
    
    async def exportar_libro_diario(
        self, 
        libro_id: str, 
        opciones: ExportOptions
    ) -> bytes:
        """Exportar libro diario en el formato especificado"""
        try:
            libro = await self.repository.obtener_libro(libro_id)
            if not libro:
                raise ValueError("Libro diario no encontrado")
            
            if opciones.formato == "excel":
                return await self._exportar_excel(libro, opciones)
            elif opciones.formato == "pdf":
                return await self._exportar_pdf(libro, opciones)
            elif opciones.formato == "txt":
                return await self._exportar_txt(libro, opciones)
            else:
                raise ValueError(f"Formato no soportado: {opciones.formato}")
            
        except Exception as e:
            logger.error(f"Error al exportar libro {libro_id}: {str(e)}")
            raise
    
    async def generar_reporte_empresa(
        self, 
        empresa_id: str, 
        filtros: FiltrosLibroDiario, 
        formato: str
    ) -> bytes:
        """Generar reporte consolidado por empresa"""
        try:
            # Obtener libros según filtros
            libros = await self.listar_libros_por_empresa(empresa_id, filtros)
            
            if formato == "excel":
                return await self._generar_reporte_excel(libros, filtros)
            elif formato == "pdf":
                return await self._generar_reporte_pdf(libros, filtros)
            else:
                raise ValueError(f"Formato no soportado: {formato}")
            
        except Exception as e:
            logger.error(f"Error al generar reporte para empresa {empresa_id}: {str(e)}")
            raise
    
    # =====================================
    # MÉTODOS PRIVADOS DE UTILIDAD
    # =====================================
    
    async def _obtener_info_empresa(self, empresa_id: str) -> Dict[str, Any]:
        """Obtener información básica de la empresa"""
        # TODO: Integrar con el módulo de empresas
        # Por ahora retornamos datos mock
        return {
            "ruc": "20123456789",
            "razonSocial": "Empresa de Prueba S.A.C."
        }
    
    async def _validar_asiento(self, asiento: AsientoContableCreate) -> None:
        """Validar reglas de negocio para asientos"""
        # Validar que no tenga debe y haber al mismo tiempo
        if asiento.debe > 0 and asiento.haber > 0:
            raise ValueError("Un asiento no puede tener valores en Debe y Haber simultáneamente")
        
        # Validar que tenga al menos un valor
        if asiento.debe == 0 and asiento.haber == 0:
            raise ValueError("Un asiento debe tener valor en Debe o Haber")
        
        # Validar valores no negativos
        if asiento.debe < 0 or asiento.haber < 0:
            raise ValueError("Los valores no pueden ser negativos")
        
        # Validar formato de fecha
        try:
            datetime.strptime(asiento.fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD")
    
    def _extraer_periodo_fecha(self, fecha: str) -> str:
        """Extraer período (año-mes) de una fecha"""
        return fecha[:7]  # YYYY-MM
    
    async def _exportar_excel(self, libro: Dict[str, Any], opciones: ExportOptions) -> bytes:
        """Exportar libro a Excel (implementación pendiente)"""
        # TODO: Implementar exportación a Excel
        raise NotImplementedError("Exportación a Excel pendiente de implementación")
    
    async def _exportar_pdf(self, libro: Dict[str, Any], opciones: ExportOptions) -> bytes:
        """Exportar libro a PDF (implementación pendiente)"""
        # TODO: Implementar exportación a PDF
        raise NotImplementedError("Exportación a PDF pendiente de implementación")
    
    async def _exportar_txt(self, libro: Dict[str, Any], opciones: ExportOptions) -> bytes:
        """Exportar libro a TXT (implementación pendiente)"""
        # TODO: Implementar exportación a TXT
        raise NotImplementedError("Exportación a TXT pendiente de implementación")
    
    async def _generar_reporte_excel(
        self, 
        libros: List[LibroDiarioResponse], 
        filtros: FiltrosLibroDiario
    ) -> bytes:
        """Generar reporte consolidado en Excel (implementación pendiente)"""
        # TODO: Implementar reporte consolidado en Excel
        raise NotImplementedError("Reporte consolidado en Excel pendiente de implementación")
    
    async def _generar_reporte_pdf(
        self, 
        libros: List[LibroDiarioResponse], 
        filtros: FiltrosLibroDiario
    ) -> bytes:
        """Generar reporte consolidado en PDF (implementación pendiente)"""
        # TODO: Implementar reporte consolidado en PDF
        raise NotImplementedError("Reporte consolidado en PDF pendiente de implementación")
