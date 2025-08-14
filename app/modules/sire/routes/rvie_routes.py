"""
Rutas para RVIE - Registro de Ventas e Ingresos Electrónico
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional
import logging

from ..schemas.rvie_schemas import (
    RvieDescargarPropuestaRequest,
    RvieAceptarPropuestaRequest,
    RvieReemplazarPropuestaRequest,
    RvieRegistrarPreliminarRequest,
    RvieConsultarInconsistenciasRequest,
    RvieGenerarTicketRequest,
    RvieConsultarTicketRequest,
    RvieDescargarArchivoRequest,
    RviePropuestaResponse,
    RvieProcesoResponse,
    RvieInconsistenciasResponse,
    RvieTicketResponse,
    RvieArchivoResponse,
    RvieResumenResponse
)
from ..services.rvie_service import RvieService
from ..services.auth_service import SireAuthService
from ...companies.models import CompanyModel
from ...companies.services import CompanyService

# Configurar logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(tags=["SIRE-RVIE"])

@router.get("/test")
async def test_rvie():
    """Endpoint de prueba para verificar que RVIE está funcionando"""
    return {"message": "RVIE endpoints están disponibles", "status": "ok"}

@router.get("/endpoints")
async def listar_endpoints_rvie():
    """Listar todas las operaciones RVIE disponibles"""
    return {
        "rvie_endpoints": [
            {
                "endpoint": "/descargar-propuesta",
                "method": "POST",
                "description": "Descargar propuesta RVIE desde SUNAT",
                "requires": ["ruc", "periodo"]
            },
            {
                "endpoint": "/aceptar-propuesta", 
                "method": "POST",
                "description": "Aceptar propuesta RVIE de SUNAT",
                "requires": ["ruc", "periodo"]
            },
            {
                "endpoint": "/reemplazar-propuesta",
                "method": "POST", 
                "description": "Reemplazar propuesta RVIE con archivo personalizado",
                "requires": ["ruc", "periodo", "archivo_txt"]
            },
            {
                "endpoint": "/registrar-preliminar",
                "method": "POST",
                "description": "Registrar información preliminar RVIE",
                "requires": ["ruc", "periodo", "registros"]
            },
            {
                "endpoint": "/consultar-inconsistencias",
                "method": "POST",
                "description": "Consultar inconsistencias en registros RVIE",
                "requires": ["ruc", "periodo"]
            },
            {
                "endpoint": "/generar-ticket",
                "method": "POST",
                "description": "Generar ticket para operación RVIE asíncrona",
                "requires": ["ruc", "periodo", "operacion"]
            },
            {
                "endpoint": "/consultar-ticket",
                "method": "GET",
                "description": "Consultar estado de ticket RVIE",
                "requires": ["ruc", "ticket_id"]
            },
            {
                "endpoint": "/descargar-archivo",
                "method": "POST",
                "description": "Descargar archivo de resultado RVIE",
                "requires": ["ruc", "periodo", "tipo_archivo"]
            }
        ],
        "base_url": "/api/v1/sire/rvie",
        "authentication": "Requiere credenciales SUNAT válidas (usuario/clave)",
        "status": "disponible"
    }

# Dependencias
async def get_rvie_service() -> RvieService:
    """Obtener instancia del servicio RVIE con dependencias correctas"""
    try:
        # Importar dependencias necesarias
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        from ....database import get_database
        
        # Obtener conexión a la base de datos
        database = get_database()
        
        # Crear token manager con MongoDB
        token_manager = SireTokenManager(
            mongo_collection=database.sire_sessions if database is not None else None
        )
        
        # Crear cliente API
        api_client = SunatApiClient()
        
        # Crear servicio RVIE con dependencias
        return RvieService(api_client, token_manager, database)
        
    except Exception as e:
        logger.error(f"❌ [RVIE] Error creando dependencias: {str(e)}")
        # Fallback: crear sin MongoDB si hay problemas
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        
        token_manager = SireTokenManager()  # Sin MongoDB
        api_client = SunatApiClient()
        return RvieService(api_client, token_manager, None)  # None para database

async def get_company_service() -> CompanyService:
    """Obtener instancia del servicio de empresas"""
    return CompanyService()

# ========================================
# ENDPOINTS GET PARA FRONTEND
# ========================================

@router.get("/{ruc}/resumen/{periodo}")
async def obtener_resumen_rvie(
    ruc: str,
    periodo: str,
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """Obtener resumen RVIE para un período específico"""
    try:
        # Simular datos de resumen por ahora
        return {
            "ruc": ruc,
            "periodo": periodo,
            "total_comprobantes": 150,
            "total_importe": 125000.50,
            "inconsistencias_pendientes": 3,
            "estado_proceso": "En proceso",
            "fecha_ultima_actualizacion": "2025-08-13T10:30:00",
            "tickets_activos": []
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen RVIE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ruc}/inconsistencias/{periodo}")
async def obtener_inconsistencias_rvie(
    ruc: str,
    periodo: str,
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """Obtener inconsistencias RVIE para un período específico"""
    try:
        # Simular datos de inconsistencias por ahora
        return {
            "ruc": ruc,
            "periodo": periodo,
            "inconsistencias": [
                {
                    "linea": 15,
                    "campo": "tipo_documento",
                    "descripcion": "Tipo de documento no válido",
                    "severidad": "ERROR",
                    "valor_esperado": "01, 03, 07, 08"
                },
                {
                    "linea": 32,
                    "campo": "numero_documento",
                    "descripcion": "Formato de número de documento incorrecto",
                    "severidad": "WARNING",
                    "valor_esperado": "Formato: F001-00000001"
                },
                {
                    "linea": 45,
                    "campo": "importe_total",
                    "descripcion": "Importe total no coincide con la suma de líneas",
                    "severidad": "ERROR",
                    "valor_esperado": None
                }
            ],
            "total_inconsistencias": 3,
            "estado": "pendiente"
        }
    except Exception as e:
        logger.error(f"Error obteniendo inconsistencias RVIE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def validate_ruc_access(ruc: str, company_service: CompanyService = Depends(get_company_service)) -> CompanyModel:
    """Validar que el RUC existe y es accesible"""
    try:
        company = await company_service.get_company_model(ruc)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with RUC {ruc} not found")
        
        if not company.tiene_sire():
            raise HTTPException(
                status_code=400, 
                detail="Company does not have SIRE credentials configured"
            )
        
        return company
    except Exception as e:
        logger.error(f"Error validating RUC access for {ruc}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error validating company access")


@router.post("/descargar-propuesta", response_model=RviePropuestaResponse)
async def descargar_propuesta(
    request: RvieDescargarPropuestaRequest,
    background_tasks: BackgroundTasks,
    rvie_service: RvieService = Depends(get_rvie_service),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Descargar propuesta RVIE desde SUNAT
    
    Permite descargar la propuesta de ventas e ingresos generada por SUNAT
    para un período específico.
    """
    try:
        # Validar que la empresa existe y tiene credenciales SIRE
        company = await company_service.get_company_model(request.ruc)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with RUC {request.ruc} not found")
        
        if not company.tiene_sire():
            raise HTTPException(
                status_code=400, 
                detail="Company does not have SIRE credentials configured"
            )
        
        logger.info(f"Descargando propuesta RVIE para RUC {request.ruc}, período {request.periodo}")
        
        # Ejecutar descarga de propuesta
        propuesta = await rvie_service.descargar_propuesta(
            ruc=request.ruc,
            periodo=request.periodo
        )
        
        logger.info(f"Propuesta RVIE descargada exitosamente para {request.ruc}-{request.periodo}")
        return propuesta
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando propuesta RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/aceptar-propuesta", response_model=RvieProcesoResponse)
async def aceptar_propuesta(
    request: RvieAceptarPropuestaRequest,
    background_tasks: BackgroundTasks,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Aceptar propuesta RVIE de SUNAT
    
    Acepta la propuesta de ventas e ingresos previamente descargada.
    """
    try:
        logger.info(f"Aceptando propuesta RVIE para RUC {request.ruc}, período {request.periodo}")
        
        # Ejecutar aceptación de propuesta
        resultado = await rvie_service.aceptar_propuesta(
            ruc=request.ruc,
            periodo=request.periodo
        )
        
        logger.info(f"Propuesta RVIE aceptada exitosamente para {request.ruc}-{request.periodo}")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error aceptando propuesta RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/reemplazar-propuesta", response_model=RvieProcesoResponse)
async def reemplazar_propuesta(
    request: RvieReemplazarPropuestaRequest,
    background_tasks: BackgroundTasks,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Reemplazar propuesta RVIE con archivo personalizado
    
    Permite enviar un archivo TXT personalizado para reemplazar
    la propuesta generada por SUNAT.
    """
    try:
        logger.info(f"Reemplazando propuesta RVIE para RUC {request.ruc}, período {request.periodo}")
        
        # Ejecutar reemplazo de propuesta
        resultado = await rvie_service.reemplazar_propuesta(
            ruc=request.ruc,
            periodo=request.periodo,
            archivo_contenido=request.archivo_contenido,
            nombre_archivo=request.nombre_archivo
        )
        
        logger.info(f"Propuesta RVIE reemplazada exitosamente para {request.ruc}-{request.periodo}")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reemplazando propuesta RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/registrar-preliminar", response_model=RvieProcesoResponse)
async def registrar_preliminar(
    request: RvieRegistrarPreliminarRequest,
    background_tasks: BackgroundTasks,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Registrar información preliminar RVIE
    
    Permite registrar comprobantes de manera preliminar antes
    de la generación de la propuesta por SUNAT.
    """
    try:
        logger.info(f"Registrando preliminar RVIE para RUC {request.ruc}, período {request.periodo} - {len(request.comprobantes)} comprobantes")
        
        # Ejecutar registro preliminar
        resultado = await rvie_service.registrar_preliminar(
            ruc=request.ruc,
            periodo=request.periodo,
            comprobantes=request.comprobantes
        )
        
        logger.info(f"Registro preliminar RVIE completado para {request.ruc}-{request.periodo}")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en registro preliminar RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/inconsistencias/{ruc}/{periodo}", response_model=RvieInconsistenciasResponse)
async def consultar_inconsistencias(
    ruc: str,
    periodo: str,
    fase: Optional[str] = "propuesta",
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Consultar inconsistencias RVIE
    
    Obtiene la lista de inconsistencias detectadas en el proceso RVIE.
    """
    try:
        logger.info(f"Consultando inconsistencias RVIE para RUC {ruc}, período {periodo}, fase {fase}")
        
        # Ejecutar consulta de inconsistencias
        inconsistencias = await rvie_service.descargar_inconsistencias(
            ruc=ruc,
            periodo=periodo,
            fase=fase
        )
        
        logger.info(f"Inconsistencias RVIE consultadas para {ruc}-{periodo}")
        return inconsistencias
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando inconsistencias RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


async def validate_ruc_from_request(request: RvieGenerarTicketRequest, company_service: CompanyService = Depends(get_company_service)) -> CompanyModel:
    """Validar RUC desde el request body"""
    try:
        company = await company_service.get_company_model(request.ruc)
        if not company:
            raise HTTPException(status_code=404, detail=f"RUC {request.ruc} no encontrado")
        return company
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando RUC {request.ruc}: {e}")
        raise HTTPException(status_code=500, detail="Error interno validando RUC")


@router.post("/generar-ticket", response_model=RvieTicketResponse)
async def generar_ticket(
    request: RvieGenerarTicketRequest,
    background_tasks: BackgroundTasks,
    company: CompanyModel = Depends(validate_ruc_from_request),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Generar ticket para operación RVIE asíncrona
    
    Crea un ticket para procesar operaciones RVIE que requieren tiempo de procesamiento.
    """
    try:
        logger.info(f"Generando ticket RVIE {request.operacion} para RUC {request.ruc}")
        
        # Generar ticket usando el servicio
        ticket = await rvie_service.generar_ticket(
            ruc=request.ruc,
            periodo=request.periodo,
            operacion=request.operacion
        )
        
        # Programar procesamiento en background
        background_tasks.add_task(
            procesar_ticket_background,
            ticket_id=ticket["ticket_id"],
            ruc=request.ruc,
            periodo=request.periodo,
            operacion=request.operacion
        )
        
        logger.info(f"Ticket RVIE generado: {ticket['ticket_id']}")
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando ticket RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


async def procesar_ticket_background(ticket_id: str, ruc: str, periodo: str, operacion: str):
    """Procesar ticket en background"""
    try:
        # Obtener servicio
        rvie_service = await get_rvie_service()
        
        # Marcar como procesando
        await rvie_service.actualizar_estado_ticket(
            ticket_id=ticket_id,
            status="PROCESANDO",
            progreso_porcentaje=10
        )
        
        # Simular procesamiento según operación
        if operacion == "descargar-propuesta":
            # Descargar propuesta
            resultado = await rvie_service.descargar_propuesta(ruc=ruc, periodo=periodo)
            
            # Marcar como completado
            await rvie_service.actualizar_estado_ticket(
                ticket_id=ticket_id,
                status="TERMINADO",
                progreso_porcentaje=100,
                resultado=resultado
            )
            
        else:
            # Otras operaciones
            await rvie_service.actualizar_estado_ticket(
                ticket_id=ticket_id,
                status="TERMINADO",
                progreso_porcentaje=100,
                descripcion=f"Operación {operacion} completada"
            )
            
    except Exception as e:
        # Marcar como error
        await rvie_service.actualizar_estado_ticket(
            ticket_id=ticket_id,
            status="ERROR",
            error_mensaje=str(e)
        )
        logger.error(f"Error procesando ticket {ticket_id}: {str(e)}")


@router.get("/ticket/{ruc}/{ticket_id}", response_model=RvieTicketResponse)
async def consultar_ticket(
    ruc: str,
    ticket_id: str,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Consultar estado de ticket RVIE
    
    Verifica el estado de procesamiento de un ticket específico.
    """
    try:
        logger.info(f"Consultando ticket RVIE {ticket_id} para RUC {ruc}")
        
        # Ejecutar consulta de ticket
        estado_ticket = await rvie_service.consultar_estado_ticket(
            ruc=ruc,
            ticket_id=ticket_id
        )
        
        logger.info(f"Estado ticket RVIE consultado: {ticket_id}")
        return estado_ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando ticket RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/archivo/{ruc}/{ticket_id}", response_model=RvieArchivoResponse)
async def descargar_archivo(
    ruc: str,
    ticket_id: str,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Descargar archivo de ticket RVIE
    
    Descarga el archivo resultado de un proceso RVIE completado.
    """
    try:
        logger.info(f"Descargando archivo RVIE del ticket {ticket_id} para RUC {ruc}")
        
        # Ejecutar descarga de archivo
        archivo = await rvie_service.descargar_archivo_ticket(
            ruc=ruc,
            ticket_id=ticket_id
        )
        
        logger.info(f"Archivo RVIE descargado: {ticket_id}")
        return archivo
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando archivo RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/resumen/{ruc}/{periodo}", response_model=RvieResumenResponse)
async def obtener_resumen(
    ruc: str,
    periodo: str,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Obtener resumen RVIE del período
    
    Proporciona un resumen completo del estado RVIE para el período especificado.
    """
    try:
        logger.info(f"Obteniendo resumen RVIE para RUC {ruc}, período {periodo}")
        
        # Ejecutar obtención de resumen
        resumen = await rvie_service.obtener_resumen_periodo(
            ruc=ruc,
            periodo=periodo
        )
        
        logger.info(f"Resumen RVIE obtenido para {ruc}-{periodo}")
        return resumen
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo resumen RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# Endpoint de salud
@router.get("/health")
async def health_check():
    """Health check para el módulo RVIE"""
    return {
        "status": "healthy",
        "module": "SIRE-RVIE",
        "version": "1.0.0"
    }
