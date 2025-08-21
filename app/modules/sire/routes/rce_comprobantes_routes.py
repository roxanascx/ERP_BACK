"""
RCE Comprobantes Routes - Endpoints para gestión de comprobantes RCE
Basado en Manual SUNAT SIRE Compras v27.0
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import io
import httpx
import logging

from ....database import get_database
from ....shared.exceptions import SireException, SireValidationException
from ..services.api_client import SunatApiClient
from ..services.auth_service import SireAuthService
from ..services.rce_compras_service import RceComprasService
from ..schemas.rce_schemas import (
    RceComprobanteCreateRequest, RceComprobanteResponse,
    RceConsultaRequest, RceConsultaResponse,
    RceApiResponse, RceErrorResponse,
    RceComprobanteDetallado, RceComprobantesDetalladosResponse
)

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter()


def get_rce_compras_service(db=Depends(get_database)) -> RceComprasService:
    """Dependency para obtener el servicio de comprobantes RCE"""
    from ..services.token_manager import SireTokenManager
    
    api_client = SunatApiClient()
    token_manager = SireTokenManager(mongo_collection=db.sire_sessions)  # Usar misma colección que funciona
    auth_service = SireAuthService(api_client, token_manager)
    return RceComprasService(db, api_client, auth_service)


# ===== ENDPOINT DE RESUMEN (DEBE IR ANTES DE /comprobantes/{correlativo}) =====

@router.get(
    "/resumen-sunat",
    summary="Resumen de período RCE desde SUNAT",
    description="Obtener resumen del período RCE consultando directamente SUNAT"
)
async def obtener_resumen_periodo(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Período en formato YYYYMM"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener resumen del período RCE consultando directamente SUNAT
    """
    logger.info(f"Consultando resumen RCE para RUC {ruc}, período {periodo}")
    
    try:
        # Obtener token válido para SUNAT
        token = await service.auth_service.token_manager.get_valid_token(ruc)
        if not token:
            logger.error(f"No se pudo obtener token SUNAT para RUC {ruc}")
            return {"error": "No se pudo obtener token SUNAT", "ruc": ruc}

        # Parámetros según el manual v27 - EXACTAMENTE como el script exitoso
        resumen_params = {
            'codLibro': '080000'  # RCE según manual v27
        }
        
        # URL según Manual SIRE Compras v27 - EXACTAMENTE como el script exitoso
        cod_tipo_resumen = '1'  # Resumen de propuesta
        cod_tipo_archivo = '0'  # TXT
        
        resumen_url = f'https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/resumen/web/resumencomprobantes/{periodo}/{cod_tipo_resumen}/{cod_tipo_archivo}/exporta'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resumen_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            resumen_response = await client.get(
                resumen_url, 
                headers=resumen_headers, 
                params=resumen_params
            )
            
            if resumen_response.status_code == 200:
                content = resumen_response.text
                
                # Parsear como lo hace el script exitoso
                lineas = content.strip().split('\n')
                
                # Buscar línea TOTAL
                datos_total = None
                for linea in lineas:
                    if linea.startswith('TOTAL '):
                        campos = linea.split('|')
                        if len(campos) >= 12:
                            datos_total = {
                                "tipo": "TOTAL",
                                "total_documentos": int(campos[1]) if campos[1].isdigit() else 0,
                                "total_cp": float(campos[12]) if len(campos) > 12 and campos[12].replace('.','').isdigit() else 0.0,
                                "valor_adq_ng": float(campos[8]) if len(campos) > 8 and campos[8].replace('.','').isdigit() else 0.0,
                                "contenido_raw": linea
                            }
                            break
                
                return {
                    "exitoso": True,
                    "mensaje": "Resumen obtenido desde SUNAT correctamente",
                    "ruc": ruc,
                    "periodo": periodo,
                    "datos": datos_total,
                    "total_lineas": len(lineas),
                    "contenido_completo": content
                }
            else:
                return {
                    "exitoso": False,
                    "mensaje": f"Error SUNAT {resumen_response.status_code}",
                    "detalle": resumen_response.text
                }
                
    except Exception as e:
        logger.error(f"💥 [DEBUG] Error: {str(e)}")
        return {
            "exitoso": False,
            "error": str(e),
            "mensaje": "Error en endpoint personalizado"
        }

# ===== FIN ENDPOINT DE RESUMEN =====


# ===== ENDPOINT DE COMPROBANTES DETALLADOS =====

@router.get(
    "/comprobantes-detallados",
    summary="Comprobantes detallados desde propuesta SUNAT",
    description="Obtener lista detallada de comprobantes individuales con datos de proveedor"
)
async def obtener_comprobantes_detallados(
    ruc: str = Query(..., description="RUC del contribuyente"),
    periodo: str = Query(..., description="Período en formato YYYYMM"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener comprobantes detallados descargando la propuesta SUNAT
    Incluye RUC y razón social del proveedor para cada comprobante
    """
    logger.info(f"Consultando comprobantes detallados para RUC {ruc}, período {periodo}")
    
    try:
        # Obtener token válido para SUNAT
        token = await service.auth_service.token_manager.get_valid_token(ruc)
        if not token:
            logger.error(f"No se pudo obtener token SUNAT para RUC {ruc}")
            return {"error": "No se pudo obtener token SUNAT", "ruc": ruc}

        # PASO 1: Solicitar generación de propuesta
        propuesta_url = f'https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rce/propuesta/web/propuesta/{periodo}/exportacioncomprobantepropuesta'
        
        propuesta_params = {
            'codTipoArchivo': '0',  # 0: txt, 1: csv
            'codOrigenEnvio': '2'   # 2: Servicio API
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            propuesta_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            propuesta_response = await client.get(
                propuesta_url, 
                headers=propuesta_headers, 
                params=propuesta_params
            )
            
            if propuesta_response.status_code != 200:
                return {
                    "exitoso": False,
                    "mensaje": f"Error obteniendo propuesta SUNAT {propuesta_response.status_code}",
                    "detalle": propuesta_response.text
                }
            
            response_json = propuesta_response.json()
            
            if 'numTicket' not in response_json:
                return {
                    "exitoso": False,
                    "mensaje": "No se recibió ticket de SUNAT",
                    "detalle": response_json
                }
            
            ticket = response_json['numTicket']
            
            # PASO 2: Esperar un momento y consultar estado del ticket
            import asyncio
            await asyncio.sleep(2)  # Dar tiempo a SUNAT para procesar
            
            # PASO 3: Consultar estado del ticket y archivos disponibles
            consulta_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"
            
            consulta_params = {
                'perIni': periodo,
                'perFin': periodo,
                'page': 1,
                'perPage': 20,
                'codLibro': '080000',
                'codOrigenEnvio': '2'
            }
            
            consulta_response = await client.get(
                consulta_url,
                headers=propuesta_headers,
                params=consulta_params
            )
            
            if consulta_response.status_code != 200:
                return {
                    "exitoso": False,
                    "mensaje": f"Error consultando estado {consulta_response.status_code}",
                    "ticket": ticket
                }
            
            consulta_data = consulta_response.json()
            
            # PASO 4: Buscar el archivo correspondiente al ticket
            archivo_info = None
            for registro in consulta_data.get('registros', []):
                if (registro.get('numTicket') == ticket and 
                    registro.get('desEstadoProceso') == 'Terminado'):
                    
                    archivos = registro.get('archivoReporte', [])
                    if archivos:
                        archivo_info = {
                            'ticket': ticket,
                            'periodo': periodo,
                            'proceso': registro.get('codProceso'),
                            'archivo': archivos[0].get('nomArchivoReporte'),
                            'tipo': archivos[0].get('codTipoAchivoReporte')
                        }
                        break
            
            if not archivo_info:
                return {
                    "exitoso": False,
                    "mensaje": "Archivo aún no está listo o no se encontró",
                    "ticket": ticket,
                    "nota": "Intente nuevamente en unos minutos"
                }
            
            # PASO 5: Descargar el archivo
            descarga_url = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros/rvierce/gestionprocesosmasivos/web/masivo/archivoreporte"
            
            descarga_params = {
                'nomArchivoReporte': archivo_info['archivo'],
                'codTipoArchivoReporte': archivo_info['tipo'],
                'perTributario': archivo_info['periodo'],
                'codProceso': archivo_info['proceso'],
                'numTicket': archivo_info['ticket'],
                'codLibro': '080000'
            }
            
            descarga_response = await client.get(
                descarga_url,
                headers=propuesta_headers,
                params=descarga_params
            )
            
            if descarga_response.status_code != 200:
                return {
                    "exitoso": False,
                    "mensaje": f"Error descargando archivo {descarga_response.status_code}",
                    "archivo_info": archivo_info
                }
            
            # PASO 6: Parsear el contenido del archivo
            contenido_archivo = descarga_response.content  # Usar .content en lugar de .text para archivos binarios
            
            # PASO 7: Descomprimir ZIP si es necesario
            contenido_texto = ""
            if archivo_info['archivo'].endswith('.zip'):
                import zipfile
                import io
                
                try:
                    with zipfile.ZipFile(io.BytesIO(contenido_archivo), 'r') as zip_file:
                        # Listar archivos en el ZIP
                        archivos_zip = zip_file.namelist()
                        
                        # Buscar el archivo TXT
                        archivo_txt = None
                        for archivo in archivos_zip:
                            if archivo.endswith('.txt'):
                                archivo_txt = archivo
                                break
                        
                        if archivo_txt:
                            with zip_file.open(archivo_txt) as txt_file:
                                contenido_texto = txt_file.read().decode('utf-8')
                        else:
                            return {
                                "exitoso": False,
                                "mensaje": "No se encontró archivo TXT en el ZIP",
                                "archivos_zip": archivos_zip
                            }
                except Exception as e:
                    return {
                        "exitoso": False,
                        "mensaje": f"Error descomprimiendo ZIP: {str(e)}",
                        "archivo": archivo_info['archivo']
                    }
            else:
                # Si no es ZIP, asumir que es texto plano
                contenido_texto = contenido_archivo.decode('utf-8')
            
            # PASO 8: Parsear las líneas del archivo de propuesta
            lineas = contenido_texto.strip().split('\n')
            
            if len(lineas) < 2:
                return {
                    "exitoso": False,
                    "mensaje": "Archivo no contiene datos suficientes",
                    "total_lineas": len(lineas)
                }
            
            # PASO 9: Parsear headers y datos
            headers = lineas[0].split('|')
            comprobantes_data = []
            
            # Mapear índices de campos importantes
            indices = {}
            campos_importantes = {
                'ruc_proveedor': 'Nro Doc Identidad',
                'razon_social_proveedor': 'Apellidos Nombres/ Razón  Social',
                'fecha_emision': 'Fecha de emisión',
                'tipo_documento': 'Tipo CP/Doc.',
                'serie': 'Serie del CDP',
                'numero': 'Nro CP o Doc. Nro Inicial (Rango)',
                'total_cp': 'Total CP',
                'moneda': 'Moneda',
                'tipo_cambio': 'Tipo de Cambio',
                'bi_gravado': 'BI Gravado DG',
                'igv': 'IGV / IPM DG',
                'valor_no_gravado': 'Valor Adq. NG',
                'isc': 'ISC',
                'icbper': 'ICBPER',
                'otros_tributos': 'Otros Trib/ Cargos'
            }
            
            # Encontrar índices de los campos
            for campo, header_name in campos_importantes.items():
                try:
                    indices[campo] = headers.index(header_name)
                except ValueError:
                    logger.warning(f"⚠️  Campo '{header_name}' no encontrado en headers")
                    indices[campo] = -1
            
            # Procesar cada línea de datos (omitir header)
            for i, linea in enumerate(lineas[1:], 1):
                campos = linea.split('|')
                
                # Asegurarse de que la línea tenga suficientes campos
                if len(campos) < len(headers):
                    logger.warning(f"⚠️  Línea {i} incompleta: {len(campos)} campos vs {len(headers)} esperados")
                    continue
                
                try:
                    # Extraer datos del comprobante
                    comprobante = {
                        'ruc_proveedor': campos[indices['ruc_proveedor']] if indices['ruc_proveedor'] >= 0 else '',
                        'razon_social_proveedor': campos[indices['razon_social_proveedor']] if indices['razon_social_proveedor'] >= 0 else '',
                        'fecha_emision': campos[indices['fecha_emision']] if indices['fecha_emision'] >= 0 else '',
                        'tipo_documento': campos[indices['tipo_documento']] if indices['tipo_documento'] >= 0 else '',
                        'serie_comprobante': campos[indices['serie']] if indices['serie'] >= 0 else '',
                        'numero_comprobante': campos[indices['numero']] if indices['numero'] >= 0 else '',
                        'moneda': campos[indices['moneda']] if indices['moneda'] >= 0 else 'PEN',
                        'tipo_cambio': float(campos[indices['tipo_cambio']]) if indices['tipo_cambio'] >= 0 and campos[indices['tipo_cambio']] else 1.0,
                        'base_imponible_gravada': float(campos[indices['bi_gravado']]) if indices['bi_gravado'] >= 0 and campos[indices['bi_gravado']] else 0.0,
                        'igv': float(campos[indices['igv']]) if indices['igv'] >= 0 and campos[indices['igv']] else 0.0,
                        'valor_adquisicion_no_gravada': float(campos[indices['valor_no_gravado']]) if indices['valor_no_gravado'] >= 0 and campos[indices['valor_no_gravado']] else 0.0,
                        'isc': float(campos[indices['isc']]) if indices['isc'] >= 0 and campos[indices['isc']] else 0.0,
                        'icbper': float(campos[indices['icbper']]) if indices['icbper'] >= 0 and campos[indices['icbper']] else 0.0,
                        'otros_tributos': float(campos[indices['otros_tributos']]) if indices['otros_tributos'] >= 0 and campos[indices['otros_tributos']] else 0.0,
                        'importe_total': float(campos[indices['total_cp']]) if indices['total_cp'] >= 0 and campos[indices['total_cp']] else 0.0,
                        'periodo': periodo
                    }
                    
                    comprobantes_data.append(comprobante)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"⚠️  Error procesando línea {i}: {str(e)}")
                    continue
            
            # PASO 10: Calcular totales
            total_base_imponible = sum(comp['base_imponible_gravada'] for comp in comprobantes_data)
            total_igv = sum(comp['igv'] for comp in comprobantes_data)
            total_general = sum(comp['importe_total'] for comp in comprobantes_data)
            
            return {
                "exitoso": True,
                "mensaje": f"{len(comprobantes_data)} comprobantes procesados correctamente",
                "ruc": ruc,
                "periodo": periodo,
                "ticket": ticket,
                "archivo": archivo_info['archivo'],
                "total_comprobantes": len(comprobantes_data),
                "comprobantes": comprobantes_data,
                "totales": {
                    "total_base_imponible": total_base_imponible,
                    "total_igv": total_igv,
                    "total_general": total_general
                },
                "debug": {
                    "headers_encontrados": len(headers),
                    "campos_mapeados": {k: v for k, v in indices.items() if v >= 0}
                }
            }
                
    except Exception as e:
        logger.error(f"💥 [DEBUG] Error comprobantes detallados: {str(e)}")
        return {
            "exitoso": False,
            "error": str(e),
            "mensaje": "Error en endpoint comprobantes detallados"
        }

# ===== FIN ENDPOINT DE COMPROBANTES DETALLADOS =====


@router.post(
    "/comprobantes",
    response_model=RceApiResponse,
    summary="Crear comprobante RCE",
    description="Crear un nuevo comprobante de compra RCE"
)
async def crear_comprobante(
    ruc: str,
    request: RceComprobanteCreateRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Crear un nuevo comprobante RCE
    
    - **ruc**: RUC del contribuyente
    - **request**: Datos del comprobante a crear
    """
    try:
        comprobante = await service.crear_comprobante(ruc, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante creado exitosamente",
            datos=comprobante
        )
        
    except SireValidationException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="VALIDATION_ERROR"
        )
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put(
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Actualizar comprobante RCE",
    description="Actualizar un comprobante RCE existente"
)
async def actualizar_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    request: RceComprobanteCreateRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Actualizar un comprobante RCE existente
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    - **request**: Nuevos datos del comprobante
    """
    try:
        comprobante = await service.actualizar_comprobante(ruc, correlativo, periodo, request)
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante actualizado exitosamente",
            datos=comprobante
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Obtener comprobante RCE",
    description="Obtener un comprobante RCE específico"
)
async def obtener_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener un comprobante RCE específico
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    """
    try:
        comprobante = await service.obtener_comprobante(ruc, correlativo, periodo)
        
        if not comprobante:
            return RceApiResponse(
                exitoso=False,
                mensaje="Comprobante no encontrado",
                codigo="NOT_FOUND"
            )
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Comprobante encontrado",
            datos=comprobante
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete(
    "/comprobantes/{correlativo}",
    response_model=RceApiResponse,
    summary="Eliminar comprobante RCE",
    description="Eliminar un comprobante RCE"
)
async def eliminar_comprobante(
    ruc: str,
    correlativo: str,
    periodo: str,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Eliminar un comprobante RCE
    
    - **ruc**: RUC del contribuyente
    - **correlativo**: Correlativo del comprobante
    - **periodo**: Periodo del comprobante (YYYYMM)
    """
    try:
        eliminado = await service.eliminar_comprobante(ruc, correlativo, periodo)
        
        return RceApiResponse(
            exitoso=eliminado,
            mensaje="Comprobante eliminado exitosamente" if eliminado else "No se pudo eliminar el comprobante"
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/comprobantes/consultar",
    response_model=RceConsultaResponse,
    summary="Consultar comprobantes RCE",
    description="Consultar comprobantes RCE con filtros y paginación"
)
async def consultar_comprobantes(
    ruc: str,
    request: RceConsultaRequest,
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Consultar comprobantes RCE con filtros avanzados
    
    - **ruc**: RUC del contribuyente
    - **request**: Filtros de consulta y parámetros de paginación
    """
    try:
        resultado = await service.consultar_comprobantes(ruc, request)
        return resultado
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post(
    "/comprobantes/validar-lote",
    response_model=RceApiResponse,
    summary="Validar lote de comprobantes",
    description="Validar un lote de comprobantes RCE y devolver válidos e inconsistencias"
)
async def validar_lote_comprobantes(
    ruc: str,
    comprobantes: List[RceComprobanteCreateRequest],
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Validar un lote de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **comprobantes**: Lista de comprobantes a validar
    """
    try:
        comprobantes_validos, inconsistencias = await service.validar_comprobantes_lote(ruc, comprobantes)
        
        return RceApiResponse(
            exitoso=True,
            mensaje=f"Validación completada: {len(comprobantes_validos)} válidos, {len(inconsistencias)} inconsistencias",
            datos={
                "comprobantes_validos": len(comprobantes_validos),
                "total_comprobantes": len(comprobantes),
                "inconsistencias": [inc.dict() for inc in inconsistencias],
                "comprobantes_validos_detalle": [comp.dict() for comp in comprobantes_validos]
            }
        )
        
    except SireException as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=str(e),
            codigo="SIRE_ERROR"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/comprobantes/exportar/csv",
    summary="Exportar comprobantes a CSV",
    description="Exportar comprobantes RCE a formato CSV"
)
async def exportar_comprobantes_csv(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo YYYYMM"),
    periodo_inicio: Optional[str] = Query(None, description="Periodo inicio YYYYMM"),
    periodo_fin: Optional[str] = Query(None, description="Periodo fin YYYYMM"),
    tipo_comprobante: Optional[List[str]] = Query(None, description="Tipos de comprobante"),
    solo_con_credito_fiscal: Optional[bool] = Query(None, description="Solo con crédito fiscal"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Exportar comprobantes RCE a formato CSV
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **periodo_inicio**: Periodo inicio para rango (opcional)
    - **periodo_fin**: Periodo fin para rango (opcional)
    - **tipo_comprobante**: Filtrar por tipos de comprobante (opcional)
    - **solo_con_credito_fiscal**: Solo comprobantes con crédito fiscal (opcional)
    """
    try:
        # Importar desde consulta service para evitar dependencia circular
        from ..services.rce_consulta_service import RceConsultaService
        from ..models.rce import RceTipoComprobante
        
        # Crear servicio de consulta
        api_client = SunatApiClient()
        auth_service = SireAuthService(service.db, api_client)
        consulta_service = RceConsultaService(service.db, api_client, auth_service, service)
        
        # Preparar request de consulta
        tipos_enum = None
        if tipo_comprobante:
            tipos_enum = [RceTipoComprobante(tc) for tc in tipo_comprobante]
        
        consulta_request = RceConsultaRequest(
            ruc=ruc,
            periodo=periodo,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            tipo_comprobante=tipos_enum,
            solo_con_credito_fiscal=solo_con_credito_fiscal,
            registros_por_pagina=10000  # Exportar hasta 10k registros
        )
        
        # Generar CSV
        csv_content = await consulta_service.exportar_comprobantes_csv(ruc, consulta_request)
        
        # Crear respuesta de descarga
        return StreamingResponse(
            io.BytesIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=comprobantes_rce_{ruc}_{periodo or 'varios'}.csv"
            }
        )
        
    except SireException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get(
    "/comprobantes/estadisticas",
    response_model=RceApiResponse,
    summary="Estadísticas de comprobantes",
    description="Obtener estadísticas generales de comprobantes RCE"
)
async def obtener_estadisticas_comprobantes(
    ruc: str,
    periodo: Optional[str] = Query(None, description="Periodo YYYYMM"),
    año: Optional[int] = Query(None, description="Año para estadísticas anuales"),
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Obtener estadísticas de comprobantes RCE
    
    - **ruc**: RUC del contribuyente
    - **periodo**: Periodo específico (opcional)
    - **año**: Año para estadísticas anuales (opcional)
    """
    try:
        filtros = {"numero_documento_adquiriente": ruc}
        
        if periodo:
            filtros["periodo"] = periodo
        elif año:
            filtros["periodo"] = {"$regex": f"^{año}"}
        
        # Pipeline de agregación para estadísticas
        pipeline = [
            {"$match": filtros},
            {"$group": {
                "_id": {
                    "tipo_comprobante": "$tipo_comprobante",
                    "sustenta_credito_fiscal": "$sustenta_credito_fiscal"
                },
                "cantidad": {"$sum": 1},
                "total_importe": {"$sum": "$importe_total"},
                "total_igv": {"$sum": "$igv"},
                "promedio_importe": {"$avg": "$importe_total"}
            }}
        ]
        
        estadisticas = await service.collection.aggregate(pipeline).to_list(length=None)
        
        # Procesar estadísticas
        resumen = {
            "total_comprobantes": 0,
            "total_importe": 0,
            "total_igv": 0,
            "total_credito_fiscal": 0,
            "por_tipo": {},
            "con_credito_fiscal": 0,
            "sin_credito_fiscal": 0
        }
        
        for stat in estadisticas:
            tipo = stat["_id"]["tipo_comprobante"]
            con_credito = stat["_id"]["sustenta_credito_fiscal"]
            
            resumen["total_comprobantes"] += stat["cantidad"]
            resumen["total_importe"] += stat["total_importe"]
            resumen["total_igv"] += stat["total_igv"]
            
            if con_credito:
                resumen["total_credito_fiscal"] += stat["total_igv"]
                resumen["con_credito_fiscal"] += stat["cantidad"]
            else:
                resumen["sin_credito_fiscal"] += stat["cantidad"]
            
            if tipo not in resumen["por_tipo"]:
                resumen["por_tipo"][tipo] = {
                    "cantidad": 0,
                    "total_importe": 0,
                    "total_igv": 0,
                    "credito_fiscal": 0
                }
            
            resumen["por_tipo"][tipo]["cantidad"] += stat["cantidad"]
            resumen["por_tipo"][tipo]["total_importe"] += stat["total_importe"]
            resumen["por_tipo"][tipo]["total_igv"] += stat["total_igv"]
            
            if con_credito:
                resumen["por_tipo"][tipo]["credito_fiscal"] += stat["total_igv"]
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Estadísticas generadas exitosamente",
            datos=resumen
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# Endpoint para verificar salud del módulo RCE
@router.get(
    "/health",
    response_model=RceApiResponse,
    summary="Verificar salud del módulo RCE",
    description="Verificar que el módulo RCE esté funcionando correctamente"
)
async def health_check(
    service: RceComprasService = Depends(get_rce_compras_service)
):
    """
    Verificar salud del módulo RCE
    """
    try:
        # Verificar conexión a base de datos
        await service.db.command("ping")
        
        # Verificar API de SUNAT
        api_disponible = await service.api_client.health_check()
        
        return RceApiResponse(
            exitoso=True,
            mensaje="Módulo RCE funcionando correctamente",
            datos={
                "base_datos": "OK",
                "api_sunat": "OK" if api_disponible else "NO_DISPONIBLE",
                "timestamp": str(service.db.command("serverStatus")["localTime"])
            }
        )
        
    except Exception as e:
        return RceApiResponse(
            exitoso=False,
            mensaje=f"Error en módulo RCE: {str(e)}",
            codigo="HEALTH_ERROR"
        )
