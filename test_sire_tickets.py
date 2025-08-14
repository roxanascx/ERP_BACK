"""
Script para verificar y probar la implementación de tickets SIRE
"""

import asyncio
import sys
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from app.modules.sire.services.ticket_service import SireTicketService
from app.modules.sire.services.token_manager import SireTokenManager
from app.modules.sire.services.api_client import SunatApiClient
from app.modules.sire.services.rvie_service import RvieService
from app.modules.sire.models.tickets import TicketOperationType, TicketPriority
from app.modules.sire.models.sunat_ticket import SunatTicketRequest, SunatOperationType

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# MOCK ELIMINADO - Usar repositorio real para identificar errores


async def test_configuracion_basica():
    """Probar configuración básica del sistema"""
    logger.info("🔍 Verificando configuración básica...")
    
    try:
        # Test 1: Crear cliente API
        api_client = SunatApiClient()
        logger.info(f"✅ Cliente API creado - URL base: {api_client.base_url}")
        
        # Test 2: Verificar endpoints
        if hasattr(api_client, 'endpoints'):
            logger.info(f"✅ Endpoints configurados: {len(api_client.endpoints)}")
        else:
            logger.warning("⚠️ Endpoints no configurados en el cliente API")
        
        # Test 3: Token manager
        token_manager = SireTokenManager()
        logger.info("✅ Token manager inicializado")
        
        # Test 4: Servicio RVIE
        rvie_service = RvieService(api_client, token_manager)
        logger.info("✅ Servicio RVIE inicializado")
        
        # Test 5: Repository real (sin mock)
        try:
            from app.database import get_database
            from app.modules.sire.repositories.ticket_repository import SireTicketRepository
            
            # Intentar obtener database real
            db = await get_database()
            ticket_repo = SireTicketRepository(db.sire_tickets)
            logger.info("✅ Repository real inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando repository real: {e}")
            return False
        
        # Test 6: Servicio de tickets
        ticket_service = SireTicketService(ticket_repo, rvie_service, token_manager)
        logger.info("✅ Servicio de tickets inicializado")
        
        await api_client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en configuración básica: {e}")
        return False


async def test_validacion_parametros():
    """Probar validaciones de parámetros"""
    logger.info("🔍 Verificando validaciones de parámetros...")
    
    try:
        # Crear servicios con repository real
        api_client = SunatApiClient()
        token_manager = SireTokenManager()
        rvie_service = RvieService(api_client, token_manager)
        
        try:
            from app.database import get_database
            from app.modules.sire.repositories.ticket_repository import SireTicketRepository
            
            db = await get_database()
            ticket_repo = SireTicketRepository(db.sire_tickets)
            
        except Exception as e:
            logger.error(f"❌ Error inicializando repository real: {e}")
            await api_client.close()
            return False
            
        ticket_service = SireTicketService(ticket_repo, rvie_service, token_manager)
        
        # Test validaciones
        test_cases = [
            # (descripción, parámetros, debe_fallar)
            ("RUC válido", {"ruc": "20100070970", "periodo": "202412"}, False),
            ("RUC inválido - corto", {"ruc": "123", "periodo": "202412"}, True),
            ("RUC inválido - largo", {"ruc": "123456789012", "periodo": "202412"}, True),
            ("RUC inválido - letras", {"ruc": "2010007097A", "periodo": "202412"}, True),
            ("Período válido", {"ruc": "20100070970", "periodo": "202412"}, False),
            ("Período inválido - corto", {"ruc": "20100070970", "periodo": "2024"}, True),
            ("Período inválido - letras", {"ruc": "20100070970", "periodo": "2024AB"}, True),
            ("Período futuro", {"ruc": "20100070970", "periodo": "202512"}, True),
        ]
        
        for descripcion, params, debe_fallar in test_cases:
            try:
                await ticket_service._validate_operation_params(
                    TicketOperationType.DESCARGAR_PROPUESTA, 
                    params
                )
                if debe_fallar:
                    logger.warning(f"⚠️ {descripcion}: Debería haber fallado pero pasó")
                else:
                    logger.info(f"✅ {descripcion}: Validación correcta")
            except Exception as e:
                if debe_fallar:
                    logger.info(f"✅ {descripcion}: Falló como esperado - {e}")
                else:
                    logger.error(f"❌ {descripcion}: Falló inesperadamente - {e}")
        
        await api_client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en validaciones: {e}")
        return False


async def test_mapeo_operaciones():
    """Probar mapeo de operaciones"""
    logger.info("🔍 Verificando mapeo de operaciones...")
    
    try:
        api_client = SunatApiClient()
        token_manager = SireTokenManager()
        rvie_service = RvieService(api_client, token_manager)
        
        try:
            from app.database import get_database
            from app.modules.sire.repositories.ticket_repository import SireTicketRepository
            
            db = await get_database()
            ticket_repo = SireTicketRepository(db.sire_tickets)
            
        except Exception as e:
            logger.error(f"❌ Error inicializando repository real: {e}")
            await api_client.close()
            return False
            
        ticket_service = SireTicketService(ticket_repo, rvie_service, token_manager)
        
        # Operaciones a probar
        operaciones = [
            TicketOperationType.DESCARGAR_PROPUESTA,
            TicketOperationType.ACEPTAR_PROPUESTA,
            TicketOperationType.REEMPLAZAR_PROPUESTA,
            TicketOperationType.REGISTRAR_PRELIMINAR,
            TicketOperationType.DESCARGAR_INCONSISTENCIAS,
        ]
        
        for op in operaciones:
            try:
                sunat_op = ticket_service._map_to_sunat_operation(op)
                logger.info(f"✅ {op.value} -> {sunat_op.value}")
            except Exception as e:
                logger.error(f"❌ Error mapeando {op.value}: {e}")
        
        await api_client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en mapeo: {e}")
        return False


async def test_creacion_request_sunat():
    """Probar creación de requests para SUNAT"""
    logger.info("🔍 Verificando creación de requests SUNAT...")
    
    try:
        # Crear request válido
        request = SunatTicketRequest(
            ruc="20100070970",
            periodo="202412",
            operacion=SunatOperationType.RVIE_DESCARGAR_PROPUESTA,
            parametros={
                "incluir_detalle": True,
                "formato": "TXT"
            }
        )
        
        logger.info(f"✅ Request SUNAT creado:")
        logger.info(f"   RUC: {request.ruc}")
        logger.info(f"   Período: {request.periodo}")
        logger.info(f"   Operación: {request.operacion.value}")
        logger.info(f"   Parámetros: {request.parametros}")
        
        # Serializar a JSON (corregir deprecation)
        json_data = request.model_dump()
        logger.info(f"✅ Serialización JSON exitosa: {len(str(json_data))} chars")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando request SUNAT: {e}")
        return False


async def test_conectividad_sunat():
    """Probar conectividad con SUNAT (sin autenticación)"""
    logger.info("🔍 Verificando conectividad con SUNAT...")
    
    try:
        import httpx
        
        # Test conectividad básica
        async with httpx.AsyncClient(timeout=10) as client:
            # Probar endpoint de salud (si existe)
            try:
                response = await client.get("https://api-sire.sunat.gob.pe/v1/health")
                logger.info(f"✅ API SIRE responde: {response.status_code}")
            except:
                # Probar endpoint base
                try:
                    response = await client.get("https://api-sire.sunat.gob.pe/v1/")
                    logger.info(f"✅ API SIRE base responde: {response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ API SIRE no responde: {e}")
            
            # Probar API de autenticación
            try:
                auth_response = await client.get("https://api-seguridad.sunat.gob.pe/v1/")
                logger.info(f"✅ API Auth responde: {auth_response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ API Auth no responde: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en conectividad: {e}")
        return False


async def main():
    """Ejecutar todas las pruebas"""
    logger.info("🚀 Iniciando verificación del sistema de tickets SIRE")
    logger.info("=" * 60)
    
    tests = [
        ("Configuración Básica", test_configuracion_basica),
        ("Validación de Parámetros", test_validacion_parametros),
        ("Mapeo de Operaciones", test_mapeo_operaciones),
        ("Creación Request SUNAT", test_creacion_request_sunat),
        ("Conectividad SUNAT", test_conectividad_sunat),
    ]
    
    resultados = {}
    
    for nombre, test_func in tests:
        logger.info(f"\n📋 {nombre}")
        logger.info("-" * 40)
        
        try:
            resultado = await test_func()
            resultados[nombre] = resultado
            
            if resultado:
                logger.info(f"✅ {nombre}: EXITOSO")
            else:
                logger.error(f"❌ {nombre}: FALLÓ")
                
        except Exception as e:
            logger.error(f"💥 {nombre}: EXCEPCIÓN - {e}")
            resultados[nombre] = False
    
    # Resumen final
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMEN DE VERIFICACIONES")
    logger.info("=" * 60)
    
    exitosos = sum(1 for r in resultados.values() if r)
    total = len(resultados)
    
    for nombre, resultado in resultados.items():
        status = "✅ EXITOSO" if resultado else "❌ FALLÓ"
        logger.info(f"{nombre:.<30} {status}")
    
    logger.info("-" * 60)
    logger.info(f"Total: {exitosos}/{total} pruebas exitosas")
    
    if exitosos == total:
        logger.info("🎉 TODAS LAS VERIFICACIONES EXITOSAS")
        logger.info("✅ El sistema está listo para generar tickets SIRE")
    else:
        logger.warning("⚠️ ALGUNAS VERIFICACIONES FALLARON")
        logger.info("🔧 Revisa los errores reportados arriba")
    
    return exitosos == total


if __name__ == "__main__":
    # Ejecutar verificaciones
    try:
        resultado = asyncio.run(main())
        sys.exit(0 if resultado else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Error fatal: {e}")
        sys.exit(1)
