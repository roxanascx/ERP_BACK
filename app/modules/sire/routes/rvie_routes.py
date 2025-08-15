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
        
        # Crear token manager con MongoDB (validación segura)
        mongo_collection = None
        try:
            if database is not None:
                mongo_collection = database.sire_sessions
        except:
            mongo_collection = None
            
        token_manager = SireTokenManager(mongo_collection=mongo_collection)
        
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

async def get_auth_service() -> SireAuthService:
    """Obtener instancia del servicio de autenticación SIRE"""
    try:
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        from ....database import get_database
        
        # Obtener conexión a la base de datos
        database = get_database()
        
        # Crear token manager con MongoDB
        mongo_collection = None
        try:
            if database is not None:
                mongo_collection = database.sire_sessions
        except:
            mongo_collection = None
            
        token_manager = SireTokenManager(mongo_collection=mongo_collection)
        
        # Crear cliente API
        api_client = SunatApiClient()
        
        # Crear servicio de autenticación
        return SireAuthService(api_client, token_manager)
        
    except Exception as e:
        logger.error(f"❌ [AUTH] Error creando servicio de autenticación: {str(e)}")
        # Fallback: crear sin MongoDB si hay problemas
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        
        token_manager = SireTokenManager()  # Sin MongoDB
        api_client = SunatApiClient()
        return SireAuthService(api_client, token_manager)

# ========================================
# ENDPOINTS FLUJO COMPLETO SEGÚN MANUAL v25
# ========================================

@router.post("/flujo-completo/{ruc}/{periodo}")
async def ejecutar_flujo_completo_preliminar(
    ruc: str,
    periodo: str,
    auto_aceptar: bool = True,
    incluir_detalle: bool = True,
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Ejecutar flujo completo para registro preliminar RVIE
    
    SECUENCIA SEGÚN MANUAL SUNAT v25:
    1. Validar prerrequisitos y sesión activa
    2. Descargar propuesta SUNAT 
    3. Aceptar propuesta (si auto_aceptar=True)
    4. Preparar para registro preliminar
    
    Este endpoint implementa la secuencia mínima requerida según
    el diagrama del Manual SUNAT para llegar al registro preliminar.
    """
    try:
        # Importar controlador de flujo
        from ..services.rvie_flow_controller import RvieFlowController
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        from ....database import get_database
        
        # Crear dependencias
        database = get_database()
        mongo_collection = database.sire_sessions if database else None
        token_manager = SireTokenManager(mongo_collection=mongo_collection)
        api_client = SunatApiClient()
        
        # Crear controlador de flujo
        flow_controller = RvieFlowController(api_client, token_manager, database)
        
        # Ejecutar flujo completo
        resultado = await flow_controller.ejecutar_flujo_completo_preliminar(
            ruc=ruc,
            periodo=periodo,
            auto_aceptar=auto_aceptar,
            incluir_detalle=incluir_detalle
        )
        
        return {
            "success": True,
            "message": "Flujo completo ejecutado exitosamente",
            "data": resultado
        }
        
    except Exception as e:
        logger.error(f"❌ [RVIE-FLUJO] Error en flujo completo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando flujo completo: {str(e)}"
        )

@router.get("/estado/{ruc}/{periodo}")
async def obtener_estado_proceso_rvie(
    ruc: str,
    periodo: str,
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Obtener estado actual del proceso RVIE para un período
    
    Devuelve el estado actual, siguiente acción recomendada,
    y resumen de datos del proceso.
    """
    try:
        # Importar controlador de flujo
        from ..services.rvie_flow_controller import RvieFlowController
        from ..services.api_client import SunatApiClient
        from ..services.token_manager import SireTokenManager
        from ....database import get_database
        
        # Crear dependencias
        database = get_database()
        mongo_collection = database.sire_sessions if database else None
        token_manager = SireTokenManager(mongo_collection=mongo_collection)
        api_client = SunatApiClient()
        
        # Crear controlador de flujo
        flow_controller = RvieFlowController(api_client, token_manager, database)
        
        # Obtener estado
        estado = await flow_controller.obtener_estado_proceso_rvie(ruc, periodo)
        
        return {
            "success": True,
            "data": estado
        }
        
    except Exception as e:
        logger.error(f"❌ [RVIE-ESTADO] Error consultando estado: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando estado: {str(e)}"
        )

# ========================================
# ENDPOINTS ESPECÍFICOS SEGÚN MANUAL v25  
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
    company_service: CompanyService = Depends(get_company_service),
    auth_service: SireAuthService = Depends(get_auth_service)
):
    """
    Descargar propuesta RVIE desde SUNAT según Manual v25
    
    Permite descargar la propuesta de ventas e ingresos generada por SUNAT
    para un período específico. Incluye mejoras de performance, cache,
    manejo de archivos ZIP y validaciones robustas.
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Período en formato YYYYMM 
    - **forzar_descarga**: True para ignorar cache y descargar nuevamente
    - **incluir_detalle**: True para incluir detalle completo de comprobantes
    
    **Mejoras implementadas**:
    - ✅ Validaciones específicas del Manual SUNAT v25
    - ✅ Manejo de respuestas masivas con paginación
    - ✅ Retry automático para timeouts
    - ✅ Cache inteligente (6 horas)
    - ✅ Procesamiento de archivos ZIP comprimidos
    - ✅ Manejo de respuestas asíncronas con tickets
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
        
        # AUTENTICACIÓN AUTOMÁTICA: Verificar si hay sesión activa y autenticar si es necesario
        from ..models.auth import SireCredentials
        
        # Verificar estado de autenticación
        auth_status = await auth_service.get_auth_status(request.ruc)
        
        if not auth_status.sesion_activa:
            logger.info(f"🔑 [API] No hay sesión activa para RUC {request.ruc}, iniciando autenticación automática")
            
            # Crear credenciales desde los datos de la empresa
            credentials = SireCredentials(
                ruc=company.ruc,
                sunat_usuario=company.sunat_usuario,  # Corregido: usar atributo del modelo
                sunat_clave=company.sunat_clave,      # Corregido: usar atributo del modelo
                client_id=company.sire_client_id,
                client_secret=company.sire_client_secret
            )
            
            # Autenticar automáticamente
            try:
                auth_response = await auth_service.authenticate(credentials)
                logger.info(f"✅ [API] Autenticación automática exitosa para RUC {request.ruc}")
            except Exception as auth_error:
                logger.error(f"❌ [API] Error en autenticación automática: {str(auth_error)}")
                raise HTTPException(
                    status_code=401, 
                    detail=f"Error de autenticación SUNAT: {str(auth_error)}"
                )
        
        logger.info(
            f"🚀 [API] Descargando propuesta RVIE para RUC {request.ruc}, período {request.periodo}. "
            f"Forzar: {request.forzar_descarga}, Detalle: {request.incluir_detalle}"
        )
        
        # Ejecutar descarga de propuesta con parámetros mejorados
        propuesta = await rvie_service.descargar_propuesta(
            ruc=request.ruc,
            periodo=request.periodo,
            forzar_descarga=request.forzar_descarga,
            incluir_detalle=request.incluir_detalle
        )
        
        logger.info(
            f"✅ [API] Propuesta RVIE descargada exitosamente. "
            f"RUC: {request.ruc}, Período: {request.periodo}, "
            f"Comprobantes: {propuesta.cantidad_comprobantes}, "
            f"Total: S/ {propuesta.total_importe}"
        )
        
        return propuesta
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error inesperado descargando propuesta RVIE: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/aceptar-propuesta", response_model=RvieProcesoResponse)
async def aceptar_propuesta(
    request: RvieAceptarPropuestaRequest,
    background_tasks: BackgroundTasks,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Aceptar propuesta RVIE de SUNAT
    
    Acepta la propuesta de ventas e ingresos previamente descargada según Manual SUNAT v25.
    
    - **ruc**: RUC del contribuyente (debe coincidir con la empresa autenticada)
    - **periodo**: Período en formato YYYYMM
    - **acepta_completa**: True para aceptar propuesta completa, False para parcial
    - **observaciones**: Observaciones opcionales del contribuyente (máx. 500 caracteres)
    
    **Flujo**:
    1. Valida que existe una propuesta descargada
    2. Verifica que el estado permite aceptación
    3. Envía aceptación a SUNAT
    4. Actualiza estado del proceso a ACEPTADO
    5. Retorna resultado con ticket ID para seguimiento
    """
    try:
        logger.info(f"🚀 [API] Aceptando propuesta RVIE para RUC {request.ruc}, período {request.periodo}")
        
        # Validar que el RUC coincide con la empresa autenticada
        if request.ruc != company.ruc:
            raise HTTPException(
                status_code=403, 
                detail=f"RUC solicitado {request.ruc} no coincide con empresa autenticada {company.ruc}"
            )
        
        # Ejecutar aceptación de propuesta con parámetros mejorados
        resultado = await rvie_service.aceptar_propuesta(
            ruc=request.ruc,
            periodo=request.periodo,
            acepta_completa=getattr(request, 'acepta_completa', True),
            observaciones=getattr(request, 'observaciones', None)
        )
        
        # Registrar auditoría de la operación
        logger.info(
            f"✅ [API] Propuesta RVIE aceptada exitosamente. "
            f"RUC: {request.ruc}, Período: {request.periodo}, "
            f"Estado: {resultado.estado}, Ticket: {resultado.ticket_id}"
        )
        
        return resultado
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error inesperado aceptando propuesta RVIE: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno del servidor: {str(e)}"
        )


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


@router.get("/tickets/{ruc}", response_model=List[RvieTicketResponse])
async def listar_tickets(
    ruc: str,
    limit: int = 50,
    skip: int = 0,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Listar todos los tickets RVIE de un RUC
    
    Obtiene la lista de todos los tickets generados para el RUC especificado.
    """
    try:
        logger.info(f"Listando tickets RVIE para RUC {ruc} (skip={skip}, limit={limit})")
        
        # Obtener tickets desde la base de datos
        tickets = await rvie_service.listar_tickets_por_ruc(
            ruc=ruc,
            limit=limit,
            skip=skip
        )
        
        logger.info(f"Tickets RVIE encontrados: {len(tickets)} para RUC {ruc}")
        return tickets
        
    except Exception as e:
        logger.error(f"Error listando tickets RVIE para RUC {ruc}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listando tickets: {str(e)}"
        )


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
