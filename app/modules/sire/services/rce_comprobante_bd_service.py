"""
Servicio para gestión de comprobantes RCE en base de datos
Capa de lógica de negocio entre las rutas y el repositorio
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from ..repositories.rce_comprobante_bd_repository import RceComprobanteBDRepository
from ..models.rce_comprobante_bd import (
    RceComprobanteBDCreate,
    RceComprobanteBDResponse,
    RceGuardarResponse,
    RceEstadisticasBD
)
from ..services.rce_compras_service import RceComprasService
from ....shared.exceptions import SireException


class RceComprobanteBDService:
    """Servicio para gestión de comprobantes en BD"""
    
    def __init__(self, repository: RceComprobanteBDRepository, rce_service: RceComprasService):
        self.repository = repository
        self.rce_service = rce_service
    
    async def guardar_comprobantes_desde_sunat(
        self,
        ruc: str,
        periodo: str,
        comprobantes_sunat: List[Dict[str, Any]]
    ) -> RceGuardarResponse:
        """Convertir datos de SUNAT y guardar en BD"""
        
        try:
            # Convertir datos de SUNAT a modelo interno
            comprobantes_bd = []
            
            for comp_sunat in comprobantes_sunat:
                comprobante_bd = self._convertir_sunat_a_bd(ruc, periodo, comp_sunat)
                comprobantes_bd.append(comprobante_bd)
            
            # Guardar en base de datos
            resultado = await self.repository.guardar_comprobantes(comprobantes_bd)
            
            return resultado
            
        except Exception as e:
            raise SireException(f"Error guardando comprobantes desde SUNAT: {str(e)}")
    
    def _convertir_sunat_a_bd(
        self, 
        ruc: str, 
        periodo: str, 
        comp_sunat: Dict[str, Any]
    ) -> RceComprobanteBDCreate:
        """Convertir datos de SUNAT al modelo de BD"""
        
        return RceComprobanteBDCreate(
            ruc=ruc,
            periodo=periodo,
            ruc_proveedor=comp_sunat.get("ruc_proveedor", ""),
            razon_social_proveedor=comp_sunat.get("razon_social_proveedor", ""),
            tipo_documento=comp_sunat.get("tipo_documento", "01"),
            serie_comprobante=comp_sunat.get("serie_comprobante", ""),
            numero_comprobante=comp_sunat.get("numero_comprobante", ""),
            fecha_emision=self._normalizar_fecha(comp_sunat.get("fecha_emision", "")),
            fecha_vencimiento=self._normalizar_fecha(comp_sunat.get("fecha_vencimiento", "")) if comp_sunat.get("fecha_vencimiento") else None,
            moneda=comp_sunat.get("moneda", "PEN"),
            tipo_cambio=Decimal(str(comp_sunat.get("tipo_cambio", 1.0))),
            base_imponible_gravada=Decimal(str(comp_sunat.get("base_imponible_gravada", 0))),
            igv=Decimal(str(comp_sunat.get("igv", 0))),
            valor_adquisicion_no_gravada=Decimal(str(comp_sunat.get("valor_adquisicion_no_gravada", 0))),
            isc=Decimal(str(comp_sunat.get("isc", 0))),
            icbper=Decimal(str(comp_sunat.get("icbper", 0))),
            otros_tributos=Decimal(str(comp_sunat.get("otros_tributos", 0))),
            importe_total=Decimal(str(comp_sunat.get("importe_total", 0))),
            car_sunat=comp_sunat.get("car_sunat"),
            numero_dua=comp_sunat.get("numero_dua"),
            observaciones=comp_sunat.get("observaciones")
        )
    
    async def consultar_comprobantes(
        self,
        ruc: str,
        periodo: Optional[str] = None,
        ruc_proveedor: Optional[str] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        estado: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 50
    ) -> Dict[str, Any]:
        """Consultar comprobantes con filtros y paginación"""
        
        skip = (pagina - 1) * por_pagina
        
        comprobantes, total = await self.repository.consultar_comprobantes(
            ruc=ruc,
            periodo=periodo,
            ruc_proveedor=ruc_proveedor,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=estado,
            skip=skip,
            limit=por_pagina
        )
        
        return {
            "exitoso": True,
            "comprobantes": comprobantes,
            "total": total,
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_paginas": (total + por_pagina - 1) // por_pagina
        }
    
    async def obtener_estadisticas(
        self,
        ruc: str,
        periodo: Optional[str] = None
    ) -> RceEstadisticasBD:
        """Obtener estadísticas de comprobantes guardados"""
        
        return await self.repository.obtener_estadisticas(ruc, periodo)
    
    async def eliminar_comprobantes(
        self,
        ruc: str,
        periodo: Optional[str] = None,
        comprobante_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Eliminar comprobantes por período o IDs específicos"""
        
        resultado = await self.repository.eliminar_comprobantes(ruc, periodo, comprobante_ids)
        
        return {
            "exitoso": True,
            **resultado
        }
    
    async def sincronizar_con_sunat(
        self,
        ruc: str,
        periodo: str
    ) -> Dict[str, Any]:
        """Comparar BD local con datos de SUNAT y sincronizar"""
        
        try:
            # Obtener datos de SUNAT
            response_sunat = await self.rce_service.obtener_comprobantes_detallados(ruc, periodo)
            
            if not response_sunat.exitoso:
                raise SireException(f"Error obteniendo datos de SUNAT: {response_sunat.mensaje}")
            
            comprobantes_sunat = response_sunat.comprobantes
            
            # Obtener datos locales
            comprobantes_locales, _ = await self.repository.consultar_comprobantes(
                ruc=ruc,
                periodo=periodo,
                limit=10000  # Sin límite para sincronización
            )
            
            # Comparar y encontrar diferencias
            diferencias = self._comparar_datos(comprobantes_locales, comprobantes_sunat)
            
            # Guardar nuevos comprobantes de SUNAT
            if diferencias["faltantes_local"]:
                resultado_guardado = await self.guardar_comprobantes_desde_sunat(
                    ruc, periodo, diferencias["faltantes_local"]
                )
                diferencias["nuevos_guardados"] = resultado_guardado.comprobantes_guardados
            else:
                diferencias["nuevos_guardados"] = 0
            
            return {
                "exitoso": True,
                "total_sunat": len(comprobantes_sunat),
                "total_local": len(comprobantes_locales),
                "sincronizado": True,
                **diferencias
            }
            
        except Exception as e:
            raise SireException(f"Error sincronizando con SUNAT: {str(e)}")
    
    def _comparar_datos(
        self, 
        locales: List[RceComprobanteBDResponse], 
        sunat: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Comparar datos locales vs SUNAT"""
        
        # Crear sets para comparación rápida
        locales_keys = set()
        for comp in locales:
            key = f"{comp.ruc_proveedor}|{comp.tipo_documento}|{comp.serie_comprobante}|{comp.numero_comprobante}"
            locales_keys.add(key)
        
        sunat_keys = set()
        sunat_dict = {}
        for comp in sunat:
            key = f"{comp.get('ruc_proveedor')}|{comp.get('tipo_documento')}|{comp.get('serie_comprobante')}|{comp.get('numero_comprobante')}"
            sunat_keys.add(key)
            sunat_dict[key] = comp
        
        # Encontrar diferencias
        faltantes_local = []
        faltantes_sunat = []
        
        # Comprobantes en SUNAT pero no en BD local
        for key in sunat_keys - locales_keys:
            faltantes_local.append(sunat_dict[key])
        
        # Comprobantes en BD local pero no en SUNAT
        for comp in locales:
            key = f"{comp.ruc_proveedor}|{comp.tipo_documento}|{comp.serie_comprobante}|{comp.numero_comprobante}"
            if key not in sunat_keys:
                faltantes_sunat.append({
                    "ruc_proveedor": comp.ruc_proveedor,
                    "serie_comprobante": comp.serie_comprobante,
                    "numero_comprobante": comp.numero_comprobante,
                    "importe_total": comp.importe_total
                })
        
        return {
            "faltantes_local": faltantes_local,
            "faltantes_sunat": faltantes_sunat,
            "coincidencias": len(locales_keys & sunat_keys)
        }
    
    async def verificar_salud_datos(
        self,
        ruc: str,
        periodo: str
    ) -> Dict[str, Any]:
        """Verificar salud e integridad de datos"""
        
        try:
            # Verificar integridad local
            salud_local = await self.repository.verificar_salud_datos(ruc, periodo)
            
            # Intentar comparar con SUNAT si es posible
            try:
                # Obtener resumen de SUNAT
                response_sunat = await self.rce_service.obtener_resumen(ruc, periodo)
                
                if response_sunat.exitoso:
                    total_sunat = response_sunat.datos.get("total_documentos", 0)
                    importe_sunat = float(response_sunat.datos.get("total_cp", 0))
                    
                    salud_local["comparacion_sunat"] = {
                        "total_sunat": total_sunat,
                        "total_local": salud_local["total_comprobantes"],
                        "diferencia_cantidad": salud_local["total_comprobantes"] - total_sunat,
                        "coincide_cantidad": salud_local["total_comprobantes"] == total_sunat
                    }
                else:
                    salud_local["comparacion_sunat"] = {"error": "No se pudo obtener datos de SUNAT"}
                    
            except Exception as e:
                salud_local["comparacion_sunat"] = {"error": f"Error consultando SUNAT: {str(e)}"}
            
            return {
                "exitoso": True,
                **salud_local
            }
            
        except Exception as e:
            raise SireException(f"Error verificando salud de datos: {str(e)}")
    
    async def guardar_comprobantes_desde_cache(
        self,
        ruc: str,
        periodo: str,
        comprobantes_data: List[Dict[str, Any]]
    ) -> RceGuardarResponse:
        """
        Guardar comprobantes que ya están en cache/vista (evita consulta a SUNAT)
        
        Args:
            ruc: RUC de la empresa
            periodo: Período YYYYMM
            comprobantes_data: Lista de comprobantes ya consultados
            
        Returns:
            RceGuardarResponse: Resultado del guardado
        """
        try:
            if not comprobantes_data:
                return RceGuardarResponse(
                    exitoso=True,
                    mensaje="No hay comprobantes para guardar",
                    total_procesados=0,
                    total_nuevos=0,
                    total_actualizados=0,
                    total_errores=0
                )
            
            # 🔍 LOG: Ver estructura de datos que llegan
            print(f"🔍 DEBUG: Estructura de comprobantes_data:")
            if comprobantes_data:
                print(f"📊 Total comprobantes: {len(comprobantes_data)}")
                print(f"🔍 Primer comprobante (muestra): {comprobantes_data[0] if comprobantes_data else 'N/A'}")
            
            # Convertir datos a modelos de BD
            comprobantes_bd = []
            errores = []
            
            for comp_data in comprobantes_data:
                try:
                    comprobante_bd = self._convertir_comprobante_a_bd(ruc, periodo, comp_data)
                    comprobantes_bd.append(comprobante_bd)
                except Exception as e:
                    errores.append(f"Error procesando comprobante: {str(e)}")
            
            # Guardar en BD
            if comprobantes_bd:
                resultado = await self.repository.guardar_comprobantes(comprobantes_bd)
                resultado.mensaje = f"Guardado desde cache: {resultado.mensaje}"
                if errores:
                    resultado.errores = errores
                    resultado.total_errores = len(errores)
                return resultado
            else:
                return RceGuardarResponse(
                    exitoso=False,
                    mensaje="No se pudo procesar ningún comprobante",
                    total_procesados=len(comprobantes_data),
                    total_nuevos=0,
                    total_actualizados=0,
                    total_errores=len(errores),
                    errores=errores
                )
                
        except Exception as e:
            raise SireException(f"Error guardando comprobantes desde cache: {str(e)}")
    
    def _normalizar_fecha(self, fecha_str: str) -> str:
        """
        Normalizar fecha a formato YYYY-MM-DD
        
        Args:
            fecha_str: Fecha en cualquier formato
            
        Returns:
            str: Fecha en formato YYYY-MM-DD o cadena vacía si es inválida
        """
        if not fecha_str or fecha_str.strip() == '':
            return ""
            
        try:
            from datetime import datetime
            
            # Limpiar espacios
            fecha_str = fecha_str.strip()
            
            # Si ya está en formato correcto YYYY-MM-DD
            if len(fecha_str) == 10 and fecha_str.count('-') == 2:
                year, month, day = fecha_str.split('-')
                if len(year) == 4 and len(month) == 2 and len(day) == 2:
                    # Validar que sea una fecha válida
                    datetime.strptime(fecha_str, '%Y-%m-%d')
                    return fecha_str
            
            # Intentar diferentes formatos
            formatos = [
                '%Y-%m-%d',      # 2025-07-15
                '%d/%m/%Y',      # 15/07/2025
                '%Y/%m/%d',      # 2025/07/15
                '%Y-%m-%dT%H:%M:%S',  # ISO con tiempo
                '%Y-%m-%dT%H:%M:%S.%f',  # ISO con microsegundos
            ]
            
            for formato in formatos:
                try:
                    fecha_obj = datetime.strptime(fecha_str.split('T')[0] if 'T' in fecha_str else fecha_str, formato.split('T')[0] if 'T' in formato else formato)
                    return fecha_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Si no se pudo convertir, devolver cadena vacía
            print(f"⚠️ Fecha no válida encontrada: {fecha_str}")
            return ""
            
        except Exception as e:
            print(f"❌ Error normalizando fecha {fecha_str}: {str(e)}")
            return ""

    def _convertir_comprobante_a_bd(
        self, 
        ruc: str, 
        periodo: str, 
        comp_data: Dict[str, Any]
    ) -> RceComprobanteBDCreate:
        """
        Convertir datos de comprobante del cache a modelo de BD
        
        Args:
            ruc: RUC de la empresa
            periodo: Período YYYYMM  
            comp_data: Datos del comprobante desde cache
            
        Returns:
            RceComprobanteBDCreate: Modelo listo para BD
        """
        try:
            # 🔍 LOG adicional para debug
            print(f"🔍 DEBUG: Convirtiendo comprobante individual:")
            print(f"📝 Datos recibidos: {comp_data}")
            print(f"📝 Keys disponibles: {list(comp_data.keys())}")
            
            return RceComprobanteBDCreate(
                ruc=ruc,
                periodo=periodo,
                # Mapeo basado en la estructura real observada en el frontend
                ruc_proveedor=(
                    comp_data.get("rucProveedor") or 
                    comp_data.get("ruc_proveedor") or 
                    comp_data.get("ruc") or 
                    ""
                ),
                razon_social_proveedor=(
                    comp_data.get("razonSocial") or 
                    comp_data.get("razon_social_proveedor") or 
                    comp_data.get("proveedor") or 
                    ""
                ),
                tipo_documento=(
                    comp_data.get("tipoDoc") or 
                    comp_data.get("tipo_documento") or 
                    comp_data.get("tipoDocumento") or 
                    comp_data.get("tipo_doc") or 
                    "01"
                ),
                serie_comprobante=(
                    comp_data.get("serie") or 
                    comp_data.get("serieComprobante") or 
                    comp_data.get("serie_comprobante") or 
                    ""
                ),
                numero_comprobante=(
                    comp_data.get("numero") or 
                    comp_data.get("numeroComprobante") or 
                    comp_data.get("numero_comprobante") or 
                    ""
                ),
                fecha_emision=self._normalizar_fecha(
                    comp_data.get("fechaEmision") or 
                    comp_data.get("fecha_emision") or 
                    comp_data.get("fecha") or 
                    ""
                ),
                fecha_vencimiento=self._normalizar_fecha(
                    comp_data.get("fechaVencimiento") or 
                    comp_data.get("fecha_vencimiento") or 
                    ""
                ) if (comp_data.get("fechaVencimiento") or comp_data.get("fecha_vencimiento")) else None,
                moneda=comp_data.get("moneda") or "PEN",
                tipo_cambio=Decimal(str(
                    comp_data.get("tipoCambio") or 
                    comp_data.get("tipo_cambio") or 
                    1.0
                )),
                base_imponible_gravada=Decimal(str(
                    comp_data.get("baseImponible") or 
                    comp_data.get("base_imponible_gravada") or 
                    comp_data.get("base_imponible") or 
                    comp_data.get("baseGravada") or 
                    0.0
                )),
                igv=Decimal(str(
                    comp_data.get("igv") or 
                    comp_data.get("IGV") or 
                    0.0
                )),
                valor_adquisicion_no_gravada=Decimal(str(
                    comp_data.get("valorNoGravado") or 
                    comp_data.get("valor_adquisicion_no_gravada") or 
                    comp_data.get("valor_no_gravado") or 
                    comp_data.get("valorAdquisicionNoGravada") or 
                    0.0
                )),
                isc=Decimal(str(comp_data.get("isc") or comp_data.get("ISC") or 0.0)),
                icbper=Decimal(str(comp_data.get("icbper") or comp_data.get("ICBPER") or 0.0)),
                otros_tributos=Decimal(str(
                    comp_data.get("otrosTributos") or 
                    comp_data.get("otros_tributos") or 
                    0.0
                )),
                importe_total=Decimal(str(
                    comp_data.get("total") or 
                    comp_data.get("importeTotal") or 
                    comp_data.get("importe_total") or 
                    comp_data.get("valorNoGravado") or  # A veces el total está aquí
                    0.0
                ))
            )
        except Exception as e:
            print(f"❌ ERROR en conversión: {str(e)}")
            print(f"📝 Datos que causaron error: {comp_data}")
            raise ValueError(f"Error convirtiendo comprobante a BD: {str(e)}")
    
    async def verificar_datos_existentes(self, ruc: str, periodo: str) -> bool:
        """
        Verificar si ya existen datos para un RUC y período
        
        Args:
            ruc: RUC de la empresa
            periodo: Período YYYYMM
            
        Returns:
            bool: True si existen datos
        """
        try:
            resultado = await self.consultar_comprobantes(ruc=ruc, periodo=periodo)
            return len(resultado.get('comprobantes', [])) > 0
        except Exception:
            return False
