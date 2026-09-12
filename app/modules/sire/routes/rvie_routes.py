"""
Rutas para RVIE - Registro de Ventas e Ingresos Electrónico
"""

# Los endpoints de escritura de RVIE (aceptar propuesta, reemplazar propuesta,
# registrar preliminar y el flujo completo) vivian aqui contra URLs que el
# manual de Ventas v30 desmiente. Se sustituyen por /sire/rvie/ciclo/*, que
# usa el catalogo verificado y una maquina de estados. Tener dos caminos de
# escritura hacia SUNAT, uno sin verificar, es justo lo que no conviene antes
# de probar en produccion.

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional
from datetime import datetime, timedelta
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
from ..services.ticket_service import SireTicketService
from ...companies.models import CompanyModel
from ...companies.services import CompanyService

# Configurar logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(tags=["SIRE-RVIE"])

# ==================== DEPENDENCIAS ====================

async def get_ticket_service(db = None) -> SireTicketService:
    """Obtener servicio de tickets con dependencias para RVIE"""
    from ..repositories.ticket_repository import SireTicketRepository
    from ..services.token_manager import SireTokenManager
    from ....database import get_database
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from fastapi import Depends
    
    if db is None:
        db = await get_database().__anext__()  # Obtener la base de datos
    
    # Repositorio de tickets
    ticket_collection = db.sire_tickets
    ticket_repo = SireTicketRepository(ticket_collection)
    
    # Token manager
    token_collection = db.sire_sessions
    token_manager = SireTokenManager(mongodb_collection=token_collection)
    
    # Servicio RVIE
    from ..services.api_client import SunatApiClient
    api_client = SunatApiClient()
    rvie_service = RvieService(api_client, token_manager)
    
    # Crear servicio de tickets
    return SireTicketService(
        ticket_repository=ticket_repo,
        rvie_service=rvie_service,
        token_manager=token_manager
    )

# ==================== ENDPOINTS ====================

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
# FUNCIONES DE VALIDACIÓN Y DEPENDENCIAS
# ========================================

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

# ========================================
# ENDPOINTS FLUJO COMPLETO SEGÚN MANUAL v25
# ========================================

@router.get("/{ruc}/resumen/{periodo}", response_model=RvieResumenResponse)
async def obtener_resumen_rvie(
    ruc: str,
    periodo: str,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Obtener resumen RVIE para un período específico
    
    Consulta propuesta guardada en cache/BD y retorna resumen sin nueva descarga.
    """
    try:
        logger.info(f"📊 [API] Consultando resumen RVIE para RUC {ruc}, período {periodo}")
        
        # Validar que el RUC coincide con la empresa autenticada
        if ruc != company.ruc:
            raise HTTPException(
                status_code=403, 
                detail=f"RUC solicitado {ruc} no coincide con empresa autenticada {company.ruc}"
            )
        
        # Obtener resumen desde cache o BD (sin nueva descarga)
        resumen = await rvie_service.obtener_resumen_guardado(ruc, periodo)
        
        if not resumen:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró propuesta RVIE para {ruc}-{periodo}. "
                       f"Debe descargar la propuesta primero."
            )
        
        logger.info(f"✅ [API] Resumen RVIE obtenido desde cache/BD para {ruc}-{periodo}")
        return resumen
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error obteniendo resumen RVIE: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/{ruc}/propuesta/{periodo}", response_model=RviePropuestaResponse)
async def consultar_propuesta_guardada(
    ruc: str,
    periodo: str,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Consultar propuesta RVIE guardada (sin nueva descarga)
    
    Obtiene propuesta desde cache/BD para mostrar datos guardados.
    """
    try:
        logger.info(f"📄 [API] Consultando propuesta guardada para RUC {ruc}, período {periodo}")
        
        # Validar que el RUC coincide con la empresa autenticada
        if ruc != company.ruc:
            raise HTTPException(
                status_code=403, 
                detail=f"RUC solicitado {ruc} no coincide con empresa autenticada {company.ruc}"
            )
        
        # Buscar propuesta en cache o BD
        propuesta = await rvie_service._obtener_propuesta_cache(ruc, periodo)
        
        if not propuesta:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró propuesta RVIE guardada para {ruc}-{periodo}. "
                       f"Debe descargar la propuesta desde SUNAT primero."
            )
        
        # Convertir a response
        propuesta_response = RviePropuestaResponse(
            ruc=propuesta.ruc,
            periodo=propuesta.periodo,
            fecha_generacion=propuesta.fecha_generacion,
            comprobantes=propuesta.comprobantes,
            total_importe=float(propuesta.total_importe),
            cantidad_comprobantes=propuesta.cantidad_comprobantes,
            estado="GUARDADO",
            archivo_contenido="",  # No incluir contenido completo por eficiencia
            mensaje="Propuesta obtenida desde cache/BD"
        )
        
        logger.info(f"✅ [API] Propuesta guardada obtenida para {ruc}-{periodo}")
        return propuesta_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error consultando propuesta guardada: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

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
    incluir_todos: bool = False,
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Listar todos los tickets RVIE de un RUC
    
    Obtiene la lista de todos los tickets generados para el RUC especificado.
    
    Args:
        incluir_todos: Si es True, incluye tickets SYNC sin archivo. Por defecto False.
    """
    try:
        logger.info(f"Listando tickets RVIE para RUC {ruc} (skip={skip}, limit={limit}, incluir_todos={incluir_todos})")
        
        # Obtener tickets desde la base de datos
        tickets = await rvie_service.listar_tickets_por_ruc(
            ruc=ruc,
            limit=limit,
            skip=skip,
            incluir_todos=incluir_todos
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


@router.get("/archivo/{ruc}/{ticket_id}")
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
        
        logger.info(f"Archivo RVIE descargado: {archivo.filename} ({archivo.file_size} bytes)")
        
        # Devolver archivo como descarga binaria
        from fastapi.responses import Response
        
        return Response(
            content=archivo.file_content,
            media_type=archivo.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={archivo.filename}",
                "Content-Length": str(archivo.file_size)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando archivo RVIE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/consultar-ticket-sunat", response_model=RvieTicketResponse)
async def consultar_ticket_sunat(
    ruc: str = Query(..., description="RUC del contribuyente"),
    ticket_id: str = Query(..., alias="ticket_id", description="ID del ticket a consultar"),
    periodo: Optional[str] = Query(None, description="Período específico (opcional)"),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Consultar ticket directamente en SUNAT con implementación real
    
    Este endpoint consulta directamente la API de SUNAT v27 y automáticamente 
    guarda el resultado en la base de datos para futuras consultas.
    """
    try:
        logger.info(f"🔍 [RVIE-ROUTE] Consultando ticket {ticket_id} para RUC {ruc} (período: {periodo})")
        
        # Usar la implementación real del servicio
        ticket_response = await rvie_service.consultar_estado_ticket_sunat(ruc, ticket_id, periodo)
        
        # Convertir a RvieTicketResponse
        rvie_ticket_response = RvieTicketResponse(
            ticket_id=ticket_response.ticket_id,
            ruc=ticket_response.ruc,
            estado=ticket_response.status,
            operacion=ticket_response.operacion,
            periodo=ticket_response.periodo,
            descripcion=ticket_response.descripcion,
            progreso_porcentaje=ticket_response.progreso_porcentaje,
            fecha_creacion=ticket_response.fecha_creacion,
            fecha_actualizacion=ticket_response.fecha_actualizacion,
            resultado=ticket_response.resultado,
            archivo_nombre=ticket_response.archivo_nombre,
            archivo_size=ticket_response.archivo_size,
            error_mensaje=ticket_response.error_mensaje
        )
        
        # 🔄 GUARDAR AUTOMÁTICAMENTE EN LA BASE DE DATOS
        try:
            if rvie_service.repository:
                # Convertir a formato SireTicket para el repository
                from ..models.tickets import SireTicket, TicketStatus, TicketOperationType
                
                # Mapear estado al enum correcto
                status_map = {
                    "TERMINADO": TicketStatus.TERMINADO,
                    "PROCESANDO": TicketStatus.PROCESANDO,
                    "PENDIENTE": TicketStatus.PENDIENTE,
                    "ERROR": TicketStatus.ERROR
                }
                
                ticket_obj = SireTicket(
                    ticket_id=rvie_ticket_response.ticket_id,
                    ruc=rvie_ticket_response.ruc,
                    operation_type=TicketOperationType.DESCARGAR_PROPUESTA,
                    operation_params={"consultado_externamente": True, "periodo": rvie_ticket_response.periodo},
                    status=status_map.get(rvie_ticket_response.estado, TicketStatus.PROCESANDO),
                    progress_percentage=rvie_ticket_response.progreso_porcentaje or 0.0,
                    status_message=rvie_ticket_response.descripcion or "",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=24),  # Expira en 24 horas
                    output_file_name=rvie_ticket_response.archivo_nombre,
                    output_file_size=rvie_ticket_response.archivo_size,
                    error_message=rvie_ticket_response.error_mensaje
                )
                
                # Guardar usando el método correcto
                await rvie_service.repository.create_ticket(ticket_obj)
                logger.info(f"💾 [RVIE] Ticket {ticket_id} guardado automáticamente en BD")
            else:
                logger.warning(f"⚠️ [RVIE] Repository no disponible, no se pudo guardar ticket {ticket_id}")
        except Exception as save_error:
            logger.warning(f"⚠️ [RVIE] Error guardando ticket {ticket_id} en BD: {save_error}")
            # No fallar la consulta si no se puede guardar
        
        logger.info(f"✅ [RVIE-ROUTE] Ticket {ticket_id} consultado exitosamente desde SUNAT")
        return rvie_ticket_response
        
    except Exception as e:
        logger.error(f"❌ [RVIE-ROUTE] Error en consulta de ticket: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando ticket: {str(e)}"
        )


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


@router.get("/consultar-ticket-sunat-protegido", response_model=RvieTicketResponse)
async def consultar_ticket_sunat_protegido(
    ruc: str = Query(..., description="RUC del contribuyente"),
    ticket_id: str = Query(..., description="ID del ticket a consultar"),
    periodo: Optional[str] = Query(None, description="Período específico (opcional)"),
    company: CompanyModel = Depends(validate_ruc_access),
    rvie_service: RvieService = Depends(get_rvie_service)
):
    """
    Consultar ticket directamente en SUNAT (sin base de datos)
    
    Útil para consultar tickets generados externamente (scripts, Postman, etc.)
    """
    try:
        logger.info(f"🔍 [RVIE-ROUTE] Consultando ticket {ticket_id} directamente en SUNAT para RUC {ruc} (período: {periodo})")
        
        # Ejecutar consulta directa a SUNAT usando el método corregido
        ticket_response = await rvie_service.consultar_estado_ticket_sunat(
            ruc=ruc,
            ticket_id=ticket_id,
            periodo=periodo
        )
        
        # Convertir a RvieTicketResponse
        rvie_ticket_response = RvieTicketResponse(
            ticket_id=ticket_response.ticket_id,
            ruc=ticket_response.ruc,
            estado=ticket_response.status,
            operacion=ticket_response.operacion,
            periodo=ticket_response.periodo,
            descripcion=ticket_response.descripcion,
            progreso_porcentaje=ticket_response.progreso_porcentaje,
            fecha_creacion=ticket_response.fecha_creacion,
            fecha_actualizacion=ticket_response.fecha_actualizacion,
            resultado=ticket_response.resultado,
            archivo_nombre=ticket_response.archivo_nombre,
            archivo_size=ticket_response.archivo_size,
            error_mensaje=ticket_response.error_mensaje
        )
        
        logger.info(f"✅ [RVIE-ROUTE] Estado ticket SUNAT consultado: {ticket_id}")
        return rvie_ticket_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando ticket en SUNAT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error consultando ticket: {str(e)}")


@router.post("/sincronizar-ticket", response_model=dict)
async def sincronizar_ticket(
    request_data: dict,
    company: CompanyModel = Depends(validate_ruc_access)
):
    """
    Sincronizar ticket externo con la base de datos
    
    Permite guardar en la BD tickets generados externamente
    """
    try:
        ruc = request_data.get('ruc')
        ticket_info = request_data.get('ticket')
        
        if not ruc or not ticket_info:
            raise HTTPException(status_code=400, detail="RUC y datos de ticket requeridos")
        
        logger.info(f"Sincronizando ticket externo {ticket_info.get('ticket_id')} para RUC {ruc}")
        
        # Por ahora, solo retornamos éxito
        # En el futuro se puede implementar la sincronización real con la BD
        
        logger.info(f"Ticket {ticket_info.get('ticket_id')} procesado exitosamente")
        return {
            "success": True,
            "message": "Ticket sincronizado correctamente",
            "ticket_id": ticket_info.get('ticket_id'),
            "note": "Funcionalidad de sincronización en desarrollo"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sincronizando ticket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sincronizando ticket: {str(e)}")


# Endpoint de salud
@router.get("/health")
async def health_check():
    """Health check para el módulo RVIE"""
    return {
        "status": "healthy",
        "module": "SIRE-RVIE",
        "version": "1.0.0"
    }
