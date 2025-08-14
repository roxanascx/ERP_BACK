"""
Rutas para gestión de tickets SIRE
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import io
import logging

from ..models.tickets import (
    TicketOperationType, TicketPriority, TicketStatus,
    TicketResponse, TicketSummary, TicketOperationRequest
)
from ..services.ticket_service import SireTicketService
from ..services.token_manager import SireTokenManager
from ..repositories.ticket_repository import SireTicketRepository
from ....database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

# Router
router = APIRouter()

# Logger
logger = logging.getLogger(__name__)


# ==================== DEPENDENCIAS ====================

async def get_ticket_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> SireTicketService:
    """Obtener servicio de tickets con dependencias"""
    try:
        # Repositorio de tickets
        ticket_collection = db.sire_tickets
        ticket_repo = SireTicketRepository(ticket_collection)
        
        # Token manager
        token_collection = db.sire_sessions
        token_manager = SireTokenManager(mongodb_collection=token_collection)
        
        # Servicio RVIE (importar aquí para evitar circular import)
        from ..services.rvie_service import RvieService
        rvie_service = RvieService(token_manager)
        
        # Crear servicio de tickets
        return SireTicketService(
            ticket_repository=ticket_repo,
            rvie_service=rvie_service,
            token_manager=token_manager
        )
        
    except Exception as e:
        logger.error(f"Error creando servicio de tickets: {e}")
        # Fallback: crear sin dependencias para evitar 500
        from ..services.rvie_service import RvieService
        
        token_manager = SireTokenManager()  # In-memory
        rvie_service = RvieService(token_manager)
        
        # Mock repository
        class MockTicketRepository:
            async def create_ticket(self, ticket): return ticket.ticket_id
            async def get_ticket(self, ticket_id): return None
            async def update_ticket_status(self, *args): return True
            async def get_tickets_by_ruc(self, *args): return []
            async def get_ticket_stats(self, ruc=None): return {"total": 0, "by_status": {}}
        
        return SireTicketService(
            ticket_repository=MockTicketRepository(),
            rvie_service=rvie_service,
            token_manager=token_manager
        )


# ==================== ENDPOINTS DE TICKETS ====================

@router.post("/ticket/rvie/descargar", 
             response_model=TicketResponse,
             summary="Crear ticket para descarga RVIE",
             description="Crea un ticket para descarga asíncrona de propuesta RVIE")
async def create_rvie_download_ticket(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Período en formato YYYYMM"),
    priority: TicketPriority = Query(TicketPriority.NORMAL, description="Prioridad del ticket"),
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Crear ticket para descarga de propuesta RVIE"""
    try:
        logger.info(f"Creando ticket de descarga RVIE para RUC: {ruc}, período: {periodo}")
        
        ticket = await ticket_service.create_rvie_download_ticket(
            ruc=ruc,
            periodo=periodo,
            priority=priority
        )
        
        logger.info(f"Ticket creado exitosamente: {ticket.ticket_id}")
        return ticket
        
    except ValueError as e:
        logger.warning(f"Error de validación creando ticket RVIE: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno creando ticket RVIE: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/ticket/rvie/aceptar",
             response_model=TicketResponse,
             summary="Crear ticket para aceptación RVIE",
             description="Crea un ticket para aceptación asíncrona de propuesta RVIE")
async def create_rvie_accept_ticket(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Período en formato YYYYMM"),
    priority: TicketPriority = Query(TicketPriority.NORMAL, description="Prioridad del ticket"),
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Crear ticket para aceptación de propuesta RVIE"""
    try:
        logger.info(f"Creando ticket de aceptación RVIE para RUC: {ruc}, período: {periodo}")
        
        ticket = await ticket_service.create_rvie_accept_ticket(
            ruc=ruc,
            periodo=periodo,
            priority=priority
        )
        
        logger.info(f"Ticket de aceptación creado exitosamente: {ticket.ticket_id}")
        return ticket
        
    except ValueError as e:
        logger.warning(f"Error de validación creando ticket de aceptación RVIE: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error interno creando ticket de aceptación RVIE: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/ticket/{ticket_id}",
            response_model=TicketResponse,
            summary="Consultar estado de ticket",
            description="Obtiene el estado actual y progreso de un ticket")
async def get_ticket_status(
    ticket_id: str,
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Consultar estado de un ticket"""
    try:
        logger.info(f"Consultando estado de ticket: {ticket_id}")
        
        ticket = await ticket_service.get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"Ticket no encontrado: {ticket_id}")
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
        logger.info(f"Estado de ticket {ticket_id}: {ticket.status}")
        return ticket
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/tickets",
            response_model=List[TicketSummary],
            summary="Listar tickets por RUC",
            description="Lista los tickets de un RUC con filtros opcionales")
async def list_tickets(
    ruc: str = Query(..., description="RUC del contribuyente"),
    status: Optional[TicketStatus] = Query(None, description="Filtrar por estado"),
    limit: int = Query(20, le=100, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Listar tickets de un RUC"""
    try:
        logger.info(f"Listando tickets para RUC: {ruc}")
        
        tickets = await ticket_service.get_tickets_by_ruc(
            ruc=ruc,
            limit=limit,
            offset=offset,
            status_filter=status
        )
        
        logger.info(f"Encontrados {len(tickets)} tickets para RUC {ruc}")
        return tickets
        
    except Exception as e:
        logger.error(f"Error listando tickets para RUC {ruc}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/tickets/stats",
            summary="Estadísticas de tickets",
            description="Obtiene estadísticas generales o por RUC")
async def get_ticket_stats(
    ruc: Optional[str] = Query(None, description="RUC específico (opcional)"),
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Obtener estadísticas de tickets"""
    try:
        logger.info(f"Obteniendo estadísticas de tickets{' para RUC: ' + ruc if ruc else ''}")
        
        stats = await ticket_service.get_ticket_stats(ruc)
        
        logger.info(f"Estadísticas obtenidas: {stats.get('total', 0)} tickets totales")
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de tickets: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/ticket/{ticket_id}/download",
            summary="Descargar archivo de ticket",
            description="Descarga el archivo generado por un ticket completado")
async def download_ticket_file(
    ticket_id: str,
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Descargar archivo generado por un ticket"""
    try:
        logger.info(f"Descargando archivo de ticket: {ticket_id}")
        
        # Verificar estado del ticket
        ticket = await ticket_service.get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"Ticket no encontrado para descarga: {ticket_id}")
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
        if ticket.status != TicketStatus.TERMINADO:
            logger.warning(f"Ticket {ticket_id} no está completado: {ticket.status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Ticket no completado. Estado actual: {ticket.status.value}"
            )
        
        if not ticket.output_file_name:
            logger.warning(f"Ticket {ticket_id} no tiene archivo asociado")
            raise HTTPException(status_code=404, detail="No hay archivo disponible")
        
        # Descargar archivo
        file_name, file_content = await ticket_service.download_file(ticket_id)
        
        if not file_name or not file_content:
            logger.error(f"No se pudo obtener archivo de ticket {ticket_id}")
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Determinar tipo de contenido
        content_type = "text/plain"
        if file_name.endswith('.xlsx'):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif file_name.endswith('.pdf'):
            content_type = "application/pdf"
        elif file_name.endswith('.zip'):
            content_type = "application/zip"
        
        # Crear stream de respuesta
        file_stream = io.BytesIO(file_content)
        
        logger.info(f"Archivo descargado exitosamente: {file_name} ({len(file_content)} bytes)")
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_name}",
                "Content-Length": str(len(file_content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error descargando archivo de ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/ticket/{ticket_id}",
               summary="Cancelar ticket",
               description="Cancela un ticket pendiente o en procesamiento")
async def cancel_ticket(
    ticket_id: str,
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Cancelar un ticket"""
    try:
        logger.info(f"Cancelando ticket: {ticket_id}")
        
        # Verificar que el ticket existe
        ticket = await ticket_service.get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"Ticket no encontrado para cancelar: {ticket_id}")
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        
        # Verificar que se puede cancelar
        if ticket.status not in [TicketStatus.PENDIENTE, TicketStatus.PROCESANDO]:
            logger.warning(f"Ticket {ticket_id} no se puede cancelar: {ticket.status}")
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cancelar ticket en estado: {ticket.status.value}"
            )
        
        # Actualizar estado a cancelado
        success = await ticket_service.ticket_repo.update_ticket_status(
            ticket_id,
            TicketStatus.CANCELADO,
            "Ticket cancelado por el usuario"
        )
        
        if not success:
            logger.error(f"No se pudo cancelar ticket {ticket_id}")
            raise HTTPException(status_code=500, detail="Error cancelando ticket")
        
        logger.info(f"Ticket cancelado exitosamente: {ticket_id}")
        return {"message": "Ticket cancelado exitosamente", "ticket_id": ticket_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ==================== ENDPOINTS DE MANTENIMIENTO ====================

@router.post("/tickets/cleanup",
             summary="Limpiar tickets expirados",
             description="Marca como expirados los tickets que superaron su tiempo límite")
async def cleanup_expired_tickets(
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Limpiar tickets expirados"""
    try:
        logger.info("Iniciando limpieza de tickets expirados")
        
        expired_count = await ticket_service.cleanup_expired_tickets()
        
        logger.info(f"Limpieza completada: {expired_count} tickets marcados como expirados")
        return {
            "message": "Limpieza completada",
            "expired_count": expired_count
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de tickets: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ==================== ENDPOINTS DE COMPATIBILIDAD ====================

@router.post("/rvie/descargar-propuesta-ticket",
             response_model=TicketResponse,
             summary="[COMPAT] Descargar propuesta RVIE con tickets",
             description="Endpoint de compatibilidad que usa el sistema de tickets")
async def download_rvie_proposal_ticket(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Período en formato YYYYMM"),
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Endpoint de compatibilidad para descarga RVIE usando tickets"""
    return await create_rvie_download_ticket(ruc, periodo, TicketPriority.NORMAL, ticket_service)


# ==================== ENDPOINTS DE TESTING ====================

@router.get("/tickets/test/create-sample",
            summary="[TEST] Crear ticket de ejemplo",
            description="Crea un ticket de ejemplo para testing")
async def create_sample_ticket(
    ticket_service: SireTicketService = Depends(get_ticket_service)
):
    """Crear ticket de ejemplo para testing"""
    try:
        logger.info("Creando ticket de ejemplo para testing")
        
        sample_ruc = "20100070970"  # RUC de ejemplo
        sample_periodo = "202312"
        
        ticket = await ticket_service.create_rvie_download_ticket(
            ruc=sample_ruc,
            periodo=sample_periodo,
            priority=TicketPriority.BAJA
        )
        
        logger.info(f"Ticket de ejemplo creado: {ticket.ticket_id}")
        return ticket
        
    except Exception as e:
        logger.error(f"Error creando ticket de ejemplo: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
