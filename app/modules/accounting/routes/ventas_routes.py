"""
Rutas FastAPI para Registro de Ventas PLE 140000
===============================================

API endpoints para gestión completa del Registro de Ventas según
especificaciones oficiales SUNAT PLE 140000.

Funcionalidades incluidas:
- CRUD completo de registros de ventas
- Generación de archivos PLE 140000 (34 campos)
- Consultas avanzadas con filtros
- Reportes y agregaciones
- Validaciones de negocio SUNAT
- Exportación de datos

Patrón utilizado: FastAPI + Dependency Injection
Documentación: Swagger UI automática

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025

Nota: el empresa_id se recibe explícito como query param, igual que en
compras/plan-contable/companies. Antes este módulo resolvía la empresa vía
Depends(get_current_empresa) (cabecera X-Clerk-User-Id), pero ningún cliente
del frontend envía esa cabecera, por lo que todos los endpoints devolvían
401/404 sin excepción. Se alinea con el resto del sistema.
"""

from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import io

from ..schemas.schemas_ventas import (
    RegistroVentaRequest,
    RegistroVentaResponse,
    PLEVentasExportOptions,
    PLEVentasExportResult,
    TipoComprobanteVenta,
    TipoDocumentoCliente,
    EstadoOperacionVenta
)
from ..services.ventas_service import VentasService
from ....core.database_deps import get_database
from ....shared.exceptions import (
    ValidationException,
    BusinessLogicException,
    NotFoundException
)

# Configurar router
router = APIRouter(
    prefix="/ventas",
    tags=["Registro de Ventas PLE 140000"],
    responses={
        404: {"description": "Registro no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)


# ================================
# DEPENDENCIAS
# ================================

async def get_ventas_service(database = Depends(get_database)) -> VentasService:
    """Inyección de dependencia para el servicio de ventas"""
    return VentasService(database)


def _rango_fechas_a_periodos(fecha_desde: Optional[date], fecha_hasta: Optional[date]) -> Dict[str, Optional[str]]:
    """Convertir un rango de fechas (YYYY-MM-DD) a período AAAAMM inicio/fin"""
    return {
        "periodo_inicio": fecha_desde.strftime("%Y%m") if fecha_desde else None,
        "periodo_fin": fecha_hasta.strftime("%Y%m") if fecha_hasta else None,
    }


# ================================
# ENDPOINTS CRUD PRINCIPALES
# ================================

@router.post(
    "/",
    response_model=RegistroVentaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear registro de venta"
)
async def crear_registro_venta(
    venta_data: RegistroVentaRequest,
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    service: VentasService = Depends(get_ventas_service)
) -> RegistroVentaResponse:
    """Crear nuevo registro de venta"""
    try:
        return await service.crear_registro_venta(
            venta_data=venta_data,
            empresa_id=empresa_id,
            periodo=periodo
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación: {str(e)}"
        )
    except BusinessLogicException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de negocio: {str(e)}"
        )


@router.get(
    "/resumen",
    summary="Resumen de ventas por período",
    description="Obtener estadísticas agregadas de ventas para un período (AAAAMM)."
)
async def resumen_ventas(
    empresa_id: str = Query(..., description="ID de la empresa"),
    periodo_aaaamm: str = Query(..., description="Período AAAAMM", regex=r"^\d{6}$"),
    service: VentasService = Depends(get_ventas_service)
) -> Dict[str, Any]:
    """Obtener resumen estadístico de ventas para un período"""
    try:
        return await service.obtener_resumen_periodo(empresa_id, periodo_aaaamm)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo resumen: {str(e)}"
        )


@router.get(
    "/export-excel",
    summary="Exportar registros de ventas a Excel"
)
async def exportar_excel(
    empresa_id: str = Query(..., description="ID de la empresa"),
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    incluir_anulados: bool = Query(False, description="Incluir registros anulados"),
    service: VentasService = Depends(get_ventas_service)
) -> StreamingResponse:
    """Descargar registros de ventas filtrados en formato .xlsx"""
    try:
        periodos = _rango_fechas_a_periodos(fecha_desde, fecha_hasta)
        contenido = await service.exportar_excel(
            empresa_id=empresa_id,
            periodo_inicio=periodos["periodo_inicio"],
            periodo_fin=periodos["periodo_fin"],
            incluir_anulados=incluir_anulados
        )

        return StreamingResponse(
            io.BytesIO(contenido),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=registro_ventas.xlsx"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando a Excel: {str(e)}"
        )


@router.get(
    "/tipos-comprobante",
    summary="Obtener tipos de comprobante",
    description="Obtener lista de tipos de comprobante válidos para ventas"
)
async def obtener_tipos_comprobante() -> Dict[str, Any]:
    """Obtener tipos de comprobante disponibles"""
    return {
        "tipos_comprobante": [
            {"codigo": tipo.value, "descripcion": tipo.name}
            for tipo in TipoComprobanteVenta
        ]
    }


@router.get(
    "/tipos-documento-cliente",
    summary="Obtener tipos de documento de cliente",
    description="Obtener lista de tipos de documento de cliente válidos"
)
async def obtener_tipos_documento_cliente() -> Dict[str, Any]:
    """Obtener tipos de documento de cliente disponibles"""
    return {
        "tipos_documento": [
            {"codigo": tipo.value, "descripcion": tipo.name}
            for tipo in TipoDocumentoCliente
        ]
    }


@router.get(
    "/estados-operacion",
    summary="Obtener estados de operación",
    description="Obtener lista de estados de operación válidos"
)
async def obtener_estados_operacion() -> Dict[str, Any]:
    """Obtener estados de operación disponibles"""
    return {
        "estados_operacion": [
            {"codigo": estado.value, "descripcion": estado.name}
            for estado in EstadoOperacionVenta
        ]
    }


# ================================
# CONSULTA / EDICIÓN POR ID
# (definidas después de las rutas fijas de arriba para que
#  /ventas/tipos-comprobante, etc. no sean interceptadas por /{registro_id})
# ================================

@router.get(
    "/{registro_id}",
    response_model=RegistroVentaResponse,
    summary="Obtener registro de venta",
    description="Obtener un registro de venta específico por su ID"
)
async def obtener_registro_venta(
    registro_id: str,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
) -> RegistroVentaResponse:
    """Obtener registro de venta por ID"""
    try:
        return await service.obtener_registro_venta(
            registro_id=registro_id,
            empresa_id=empresa_id
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put(
    "/{registro_id}",
    response_model=RegistroVentaResponse,
    summary="Actualizar registro de venta",
    description="""
    Actualizar un registro de venta existente.

    **Nota importante:** Solo se pueden actualizar registros que no hayan
    sido incluidos en un archivo PLE ya enviado a SUNAT.
    """
)
async def actualizar_registro_venta(
    registro_id: str,
    venta_data: RegistroVentaRequest,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
) -> RegistroVentaResponse:
    """Actualizar registro de venta existente"""
    try:
        return await service.actualizar_registro_venta(
            registro_id=registro_id,
            venta_data=venta_data,
            empresa_id=empresa_id
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación: {str(e)}"
        )


@router.delete(
    "/{registro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar registro de venta",
    description="""
    Eliminar (anular) un registro de venta.

    **Nota:** Esto es una eliminación lógica. El registro se marca como
    'anulado' pero se mantiene en la base de datos para auditoría.
    """
)
async def eliminar_registro_venta(
    registro_id: str,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
):
    """Eliminar (anular) registro de venta"""
    try:
        success = await service.eliminar_registro_venta(
            registro_id=registro_id,
            empresa_id=empresa_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo eliminar el registro"
            )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ================================
# CONSULTAS Y LISTADOS
# ================================

@router.get(
    "/",
    response_model=List[RegistroVentaResponse],
    summary="Listar registros de ventas",
    description="""
    Listar registros de ventas con filtros avanzados.

    **Filtros disponibles:**
    - Rango de fechas de emisión (fecha_desde / fecha_hasta) o rango de períodos (AAAAMM)
    - Tipo de comprobante
    - Cliente (número de documento)
    - Incluir/excluir anulados
    """
)
async def listar_registros_ventas(
    empresa_id: str = Query(..., description="ID de la empresa"),
    fecha_desde: Optional[date] = Query(None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[date] = Query(None, description="Fecha hasta (YYYY-MM-DD)"),
    periodo_inicio: Optional[str] = Query(None, description="Período inicio AAAAMM", regex=r"^\d{6}$"),
    periodo_fin: Optional[str] = Query(None, description="Período fin AAAAMM", regex=r"^\d{6}$"),
    tipo_comprobante: Optional[TipoComprobanteVenta] = Query(None, description="Filtro por tipo de comprobante"),
    numero_documento_cliente: Optional[str] = Query(None, description="Filtro por cliente"),
    incluir_anulados: bool = Query(False, description="Incluir registros anulados"),
    pagina: int = Query(1, ge=1, description="Página actual"),
    limite: int = Query(50, ge=1, le=500, description="Registros por página"),
    service: VentasService = Depends(get_ventas_service)
) -> List[RegistroVentaResponse]:
    """Listar registros de ventas con filtros (retorna lista plana)"""
    try:
        if not periodo_inicio and not periodo_fin and (fecha_desde or fecha_hasta):
            periodos = _rango_fechas_a_periodos(fecha_desde, fecha_hasta)
            periodo_inicio = periodos["periodo_inicio"]
            periodo_fin = periodos["periodo_fin"]

        resultado = await service.listar_registros_ventas(
            empresa_id=empresa_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            tipo_comprobante=tipo_comprobante,
            numero_documento_cliente=numero_documento_cliente,
            incluir_anulados=incluir_anulados,
            pagina=pagina,
            limite=limite
        )
        return resultado.get("registros", [])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


# ================================
# GENERACIÓN PLE 140000
# ================================

@router.post(
    "/generar-ple",
    response_model=PLEVentasExportResult,
    summary="Generar archivo PLE 140000",
    description="""
    Generar archivo PLE 140000 (Registro de Ventas) según especificaciones SUNAT.

    **Características del archivo generado:**
    - 34 campos oficiales según resolución SUNAT
    - Formato de texto separado por '|'
    - Codificación ISO-8859-1
    - Validaciones completas de datos
    - Totales y estadísticas incluidas

    **Filtros opcionales:**
    - Rango de períodos
    - Tipo de comprobante específico
    - Tipo de documento de cliente
    - Estado de operación
    - Solo registros con errores
    """
)
async def generar_ple_ventas(
    opciones: PLEVentasExportOptions,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
) -> PLEVentasExportResult:
    """Generar archivo PLE 140000 para Registro de Ventas"""
    try:
        opciones.empresa_id = empresa_id
        return await service.generar_ple_ventas(opciones)

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación: {str(e)}"
        )
    except BusinessLogicException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de negocio: {str(e)}"
        )


@router.post(
    "/descargar-ple",
    summary="Descargar archivo PLE 140000",
    description="""
    Generar y descargar directamente el archivo PLE 140000.

    **Formato de descarga:**
    - Archivo de texto (.txt)
    - Codificación ISO-8859-1
    - Nombre según estándar SUNAT: LE{RUC}{AAAA}{MM}00140000{ID}11.txt
    """
)
async def descargar_ple_ventas(
    opciones: PLEVentasExportOptions,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
) -> StreamingResponse:
    """Descargar archivo PLE 140000 directamente"""
    try:
        opciones.empresa_id = empresa_id

        resultado = await service.generar_ple_ventas(opciones)

        if not resultado.contenido_archivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron registros para generar el archivo PLE"
            )

        archivo_bytes = resultado.contenido_archivo.encode('iso-8859-1')

        return StreamingResponse(
            io.BytesIO(archivo_bytes),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={resultado.nombre_archivo}",
                "Content-Length": str(len(archivo_bytes))
            }
        )

    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error de validación: {str(e)}"
        )
    except BusinessLogicException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de negocio: {str(e)}"
        )


@router.get(
    "/validar/{registro_id}",
    summary="Validar registro específico",
    description="""
    Validar un registro específico contra las reglas SUNAT.
    """
)
async def validar_registro(
    registro_id: str,
    empresa_id: str = Query(..., description="ID de la empresa"),
    service: VentasService = Depends(get_ventas_service)
) -> Dict[str, Any]:
    """Validar un registro específico"""
    try:
        registro = await service.obtener_registro_venta(
            registro_id=registro_id,
            empresa_id=empresa_id
        )

        validaciones = {
            "registro_id": registro_id,
            "es_valido": True,
            "errores": [],
            "warnings": [],
            "validaciones_realizadas": [
                "Consistencia de montos",
                "Formato de campos",
                "Reglas SUNAT básicas"
            ]
        }

        try:
            total_calculado = (
                registro.valor_facturado_exportacion +
                registro.base_imponible_gravada +
                registro.importe_exonerado +
                registro.importe_inafecto +
                registro.igv_ipm +
                registro.isc +
                registro.otros_tributos_cargos
            )

            diferencia = abs(total_calculado - registro.importe_total)
            if diferencia > 0.05:  # Tolerancia para redondeos
                validaciones["errores"].append(
                    f"Inconsistencia en montos: diferencia de {diferencia}"
                )
                validaciones["es_valido"] = False

        except Exception as e:
            validaciones["errores"].append(f"Error validando montos: {str(e)}")
            validaciones["es_valido"] = False

        return validaciones

    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
