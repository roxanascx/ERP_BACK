"""
Validador especializado para cumplimiento SUNAT en Libro Diario
"""
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, date
import re
from .schemas import (
    AsientoContableSunatV3, 
    LibroDiarioSunatV3, 
    TipoAsientoSunat,
    EstadoOperacionSunat
)
from .sunat_config_service import SunatConfigService, SunatLibroConfig


class SunatValidationResult:
    """Resultado de validación SUNAT"""
    def __init__(self):
        self.es_valido: bool = True
        self.errores: List[str] = []
        self.warnings: List[str] = []
        self.recomendaciones: List[str] = []
        self.detalles_validacion: Dict[str, Any] = {}
        self.tiempo_validacion: Optional[datetime] = None
        self.reglas_aplicadas: List[str] = []
    
    def agregar_error(self, mensaje: str, regla: str = ""):
        """Agregar error crítico que impide cumplimiento"""
        self.errores.append(mensaje)
        self.es_valido = False
        if regla:
            self.reglas_aplicadas.append(f"ERROR: {regla}")
    
    def agregar_warning(self, mensaje: str, regla: str = ""):
        """Agregar advertencia que no impide pero requiere atención"""
        self.warnings.append(mensaje)
        if regla:
            self.reglas_aplicadas.append(f"WARNING: {regla}")
    
    def agregar_recomendacion(self, mensaje: str, regla: str = ""):
        """Agregar recomendación para mejorar calidad"""
        self.recomendaciones.append(mensaje)
        if regla:
            self.reglas_aplicadas.append(f"RECOMENDACION: {regla}")
    
    def agregar_detalle(self, clave: str, valor: Any):
        """Agregar detalle específico de validación"""
        self.detalles_validacion[clave] = valor
    
    def finalizar_validacion(self):
        """Marcar validación como finalizada"""
        self.tiempo_validacion = datetime.utcnow()
    
    def puede_enviar_sunat(self) -> bool:
        """Determinar si puede enviarse a SUNAT"""
        return self.es_valido and len(self.warnings) == 0
    
    def resumen(self) -> Dict[str, Any]:
        """Obtener resumen de validación"""
        return {
            "es_valido": self.es_valido,
            "puede_enviar_sunat": self.puede_enviar_sunat(),
            "total_errores": len(self.errores),
            "total_warnings": len(self.warnings),
            "total_recomendaciones": len(self.recomendaciones),
            "tiempo_validacion": self.tiempo_validacion,
            "reglas_aplicadas": len(self.reglas_aplicadas)
        }


class SunatLibroDiarioValidator:
    """Validador especializado para cumplimiento SUNAT"""
    
    def __init__(self, config_service: SunatConfigService):
        self.config_service = config_service
    
    async def validar_libro_completo(
        self, 
        libro: LibroDiarioSunatV3, 
        asientos: List[AsientoContableSunatV3]
    ) -> SunatValidationResult:
        """
        Validación completa de libro diario según SUNAT
        
        Args:
            libro: Datos del libro diario
            asientos: Lista de asientos contables
            
        Returns:
            SunatValidationResult: Resultado completo de validación
        """
        resultado = SunatValidationResult()
        
        try:
            # Obtener configuración SUNAT para la empresa
            config = await self.config_service.obtener_configuracion_empresa(libro.empresaId)
            resultado.agregar_detalle("configuracion_sunat", config.dict())
            
            # 1. Validar estructura del libro
            await self._validar_estructura_libro(libro, config, resultado)
            
            # 2. Validar que existen asientos
            if not asientos:
                resultado.agregar_error(
                    "El libro diario debe contener al menos un asiento contable",
                    "estructura_basica"
                )
                resultado.finalizar_validacion()
                return resultado
            
            # 3. Validar correlatividad estricta
            await self._validar_correlatividad_estricta(asientos, resultado)
            
            # 4. Validar tipos de asientos obligatorios
            await self._validar_tipos_asientos_obligatorios(asientos, config, resultado)
            
            # 5. Validar cada asiento individualmente
            for i, asiento in enumerate(asientos):
                await self._validar_asiento_individual(
                    asiento, config, resultado, posicion=i+1
                )
            
            # 6. Validar consistencia temporal
            await self._validar_consistencia_temporal(asientos, libro.periodo, resultado)
            
            # 7. Validar integridad contable general
            await self._validar_integridad_contable(asientos, resultado)
            
            # 8. Validar preparación para PLE
            await self._validar_preparacion_ple(libro, asientos, config, resultado)
            
        except Exception as e:
            resultado.agregar_error(
                f"Error durante validación: {str(e)}",
                "error_sistema"
            )
        
        resultado.finalizar_validacion()
        return resultado
    
    async def validar_asiento_individual(
        self,
        asiento: AsientoContableSunatV3,
        empresa_id: str
    ) -> SunatValidationResult:
        """
        Validar un asiento individual según reglas SUNAT
        
        Args:
            asiento: Asiento a validar
            empresa_id: ID de la empresa
            
        Returns:
            SunatValidationResult: Resultado de validación del asiento
        """
        resultado = SunatValidationResult()
        
        try:
            config = await self.config_service.obtener_configuracion_empresa(empresa_id)
            await self._validar_asiento_individual(asiento, config, resultado)
        except Exception as e:
            resultado.agregar_error(
                f"Error validando asiento: {str(e)}",
                "error_sistema"
            )
        
        resultado.finalizar_validacion()
        return resultado
    
    # Métodos privados de validación específica
    
    async def _validar_estructura_libro(
        self, 
        libro: LibroDiarioSunatV3, 
        config: SunatLibroConfig,
        resultado: SunatValidationResult
    ):
        """Validar estructura básica del libro"""
        # Validar período
        if not self._es_periodo_valido(libro.periodo):
            resultado.agregar_error(
                f"Período '{libro.periodo}' no tiene formato válido (YYYY o YYYY-MM)",
                "formato_periodo"
            )
        
        # Validar configuración mínima dígitos
        if libro.minDigitosCuenta < config.min_digitos_cuenta:
            resultado.agregar_error(
                f"Empresa requiere mínimo {config.min_digitos_cuenta} dígitos en códigos de cuenta, "
                f"configurado: {libro.minDigitosCuenta}",
                "min_digitos_cuenta"
            )
        
        # Validar moneda
        if libro.moneda not in ["PEN", "USD", "EUR"]:
            resultado.agregar_warning(
                f"Moneda '{libro.moneda}' no es estándar. Se recomienda PEN para SUNAT",
                "moneda_estandar"
            )
        
        # Validar formato PLE
        if config.formato_requerido == "completo" and libro.formatoPLE != "5.1":
            resultado.agregar_error(
                f"Empresa requiere formato PLE completo (5.1), configurado: {libro.formatoPLE}",
                "formato_ple_requerido"
            )
        
        resultado.agregar_detalle("validacion_estructura", {
            "periodo_valido": self._es_periodo_valido(libro.periodo),
            "min_digitos_correcto": libro.minDigitosCuenta >= config.min_digitos_cuenta,
            "formato_ple_correcto": libro.formatoPLE == "5.1"
        })
    
    async def _validar_correlatividad_estricta(
        self, 
        asientos: List[AsientoContableSunatV3],
        resultado: SunatValidationResult
    ):
        """Validar correlatividad estricta sin saltos"""
        # Ordenar asientos por número correlativo
        try:
            asientos_ordenados = sorted(asientos, key=lambda x: int(x.numero))
        except ValueError as e:
            resultado.agregar_error(
                f"Error en numeración de asientos: {str(e)}",
                "numeracion_invalida"
            )
            return
        
        saltos_encontrados = []
        duplicados_encontrados = []
        numeros_usados = set()
        
        for i, asiento in enumerate(asientos_ordenados):
            correlativo_esperado = i + 1
            correlativo_actual = int(asiento.numero)
            
            # Verificar duplicados
            if correlativo_actual in numeros_usados:
                duplicados_encontrados.append(correlativo_actual)
            numeros_usados.add(correlativo_actual)
            
            # Verificar correlatividad
            if correlativo_actual != correlativo_esperado:
                saltos_encontrados.append({
                    "posicion": i + 1,
                    "esperado": correlativo_esperado,
                    "encontrado": correlativo_actual
                })
        
        # Reportar errores
        if duplicados_encontrados:
            resultado.agregar_error(
                f"Números correlativos duplicados: {duplicados_encontrados}",
                "correlativos_duplicados"
            )
        
        if saltos_encontrados:
            detalles_saltos = [
                f"Posición {s['posicion']}: esperado {s['esperado']}, encontrado {s['encontrado']}"
                for s in saltos_encontrados[:3]  # Mostrar solo los primeros 3
            ]
            resultado.agregar_error(
                f"Saltos en correlatividad detectados. {'; '.join(detalles_saltos)}"
                + (f" y {len(saltos_encontrados) - 3} más" if len(saltos_encontrados) > 3 else ""),
                "correlatividad_estricta"
            )
        
        resultado.agregar_detalle("correlatividad", {
            "total_asientos": len(asientos),
            "saltos_encontrados": len(saltos_encontrados),
            "duplicados_encontrados": len(duplicados_encontrados),
            "correlatividad_correcta": len(saltos_encontrados) == 0 and len(duplicados_encontrados) == 0
        })
    
    async def _validar_tipos_asientos_obligatorios(
        self,
        asientos: List[AsientoContableSunatV3],
        config: SunatLibroConfig,
        resultado: SunatValidationResult
    ):
        """Validar presencia de tipos de asientos obligatorios"""
        tipos_presentes = set(a.tipoAsiento for a in asientos)
        tipos_obligatorios = [
            t for t in config.tipos_asientos_obligatorios 
            if t.get("obligatorio", False)
        ]
        
        tipos_faltantes = []
        for tipo_obligatorio in tipos_obligatorios:
            tipo_codigo = tipo_obligatorio["tipo"]
            if tipo_codigo not in tipos_presentes:
                tipos_faltantes.append({
                    "tipo": tipo_codigo,
                    "descripcion": tipo_obligatorio["descripcion"],
                    "fecha_requerida": tipo_obligatorio.get("fecha_requerida")
                })
        
        if tipos_faltantes:
            detalles = [
                f"{t['tipo']} ({t['descripcion']})" + 
                (f" - fecha {t['fecha_requerida']}" if t['fecha_requerida'] else "")
                for t in tipos_faltantes
            ]
            resultado.agregar_warning(
                f"Tipos de asientos recomendados por SUNAT no presentes: {'; '.join(detalles)}",
                "tipos_asientos_obligatorios"
            )
        
        resultado.agregar_detalle("tipos_asientos", {
            "tipos_presentes": list(tipos_presentes),
            "tipos_obligatorios_faltantes": tipos_faltantes,
            "cumple_tipos_minimos": len(tipos_faltantes) == 0
        })
    
    async def _validar_asiento_individual(
        self,
        asiento: AsientoContableSunatV3,
        config: SunatLibroConfig,
        resultado: SunatValidationResult,
        posicion: int = 0
    ):
        """Validar asiento individual según reglas SUNAT"""
        prefijo_error = f"Asiento {asiento.numero}" + (f" (pos. {posicion})" if posicion else "")
        
        # 1. Validar balance (ya incluido en schema, pero verificar)
        total_debe = sum(detalle.debe or 0 for detalle in asiento.detalles)
        total_haber = sum(detalle.haber or 0 for detalle in asiento.detalles)
        diferencia = abs(total_debe - total_haber)
        
        if diferencia > 0.01:
            resultado.agregar_error(
                f"{prefijo_error}: Desbalanceado. Debe: {total_debe:.2f}, Haber: {total_haber:.2f}, "
                f"Diferencia: {diferencia:.2f}",
                "balance_asiento"
            )
        
        # 2. Validar códigos de cuenta según configuración
        cuentas_con_errores = []
        for j, detalle in enumerate(asiento.detalles):
            detalle_prefijo = f"{prefijo_error} línea {j+1}"
            
            # Validar longitud mínima
            if len(detalle.codigoCuenta) < config.min_digitos_cuenta:
                cuentas_con_errores.append({
                    "linea": j+1,
                    "codigo": detalle.codigoCuenta,
                    "error": f"Requiere mínimo {config.min_digitos_cuenta} dígitos"
                })
            
            # Validar denominación si es requerida
            if config.requiere_denominacion_cuenta and not detalle.denominacionCuenta.strip():
                cuentas_con_errores.append({
                    "linea": j+1,
                    "codigo": detalle.codigoCuenta,
                    "error": "Requiere denominación"
                })
            
            # Validar formato código (solo números y puntos)
            if not re.match(r'^[0-9.]+$', detalle.codigoCuenta):
                cuentas_con_errores.append({
                    "linea": j+1,
                    "codigo": detalle.codigoCuenta,
                    "error": "Formato inválido (solo números y puntos)"
                })
            
            # Validar que tenga descripción
            if not detalle.descripcion.strip():
                resultado.agregar_warning(
                    f"{detalle_prefijo}: Cuenta {detalle.codigoCuenta} sin descripción",
                    "descripcion_detalle"
                )
        
        # Reportar errores de cuentas
        if cuentas_con_errores:
            for error_cuenta in cuentas_con_errores:
                resultado.agregar_error(
                    f"{prefijo_error} línea {error_cuenta['linea']}: "
                    f"Cuenta {error_cuenta['codigo']} - {error_cuenta['error']}",
                    "validacion_cuentas"
                )
        
        # 3. Validar estructura mínima
        if len(asiento.detalles) < 2:
            resultado.agregar_error(
                f"{prefijo_error}: Debe tener mínimo 2 líneas de detalle",
                "minimo_lineas"
            )
        
        # 4. Validar fecha dentro de rangos lógicos
        try:
            fecha_asiento = datetime.strptime(asiento.fecha, "%Y-%m-%d").date()
            fecha_actual = date.today()
            
            if fecha_asiento > fecha_actual:
                resultado.agregar_warning(
                    f"{prefijo_error}: Fecha futura ({asiento.fecha})",
                    "fecha_futura"
                )
            
            # Validar que no sea muy antigua (más de 10 años)
            años_diferencia = (fecha_actual - fecha_asiento).days / 365.25
            if años_diferencia > 10:
                resultado.agregar_warning(
                    f"{prefijo_error}: Fecha muy antigua ({asiento.fecha}) - {años_diferencia:.1f} años",
                    "fecha_antigua"
                )
                
        except ValueError:
            resultado.agregar_error(
                f"{prefijo_error}: Fecha inválida ({asiento.fecha})",
                "formato_fecha"
            )
    
    async def _validar_consistencia_temporal(
        self,
        asientos: List[AsientoContableSunatV3],
        periodo: str,
        resultado: SunatValidationResult
    ):
        """Validar consistencia temporal de fechas"""
        fechas_fuera_periodo = []
        fechas_invalidas = []
        
        for asiento in asientos:
            try:
                fecha_asiento = datetime.strptime(asiento.fecha, "%Y-%m-%d").date()
                
                if not self._fecha_en_periodo(fecha_asiento, periodo):
                    fechas_fuera_periodo.append({
                        "asiento": asiento.numero,
                        "fecha": asiento.fecha,
                        "periodo": periodo
                    })
                    
            except ValueError:
                fechas_invalidas.append({
                    "asiento": asiento.numero,
                    "fecha": asiento.fecha
                })
        
        if fechas_invalidas:
            resultado.agregar_error(
                f"Fechas con formato inválido: " + 
                ", ".join([f"Asiento {f['asiento']}: {f['fecha']}" for f in fechas_invalidas[:3]]),
                "formato_fechas"
            )
        
        if fechas_fuera_periodo:
            resultado.agregar_warning(
                f"Asientos con fechas fuera del período {periodo}: " +
                ", ".join([f"Asiento {f['asiento']}: {f['fecha']}" for f in fechas_fuera_periodo[:3]]) +
                (f" y {len(fechas_fuera_periodo) - 3} más" if len(fechas_fuera_periodo) > 3 else ""),
                "fechas_fuera_periodo"
            )
        
        resultado.agregar_detalle("consistencia_temporal", {
            "total_asientos": len(asientos),
            "fechas_fuera_periodo": len(fechas_fuera_periodo),
            "fechas_invalidas": len(fechas_invalidas),
            "periodo": periodo
        })
    
    async def _validar_integridad_contable(
        self,
        asientos: List[AsientoContableSunatV3],
        resultado: SunatValidationResult
    ):
        """Validar integridad contable general"""
        total_debe_libro = sum(
            sum(detalle.debe or 0 for detalle in asiento.detalles)
            for asiento in asientos
        )
        total_haber_libro = sum(
            sum(detalle.haber or 0 for detalle in asiento.detalles)
            for asiento in asientos
        )
        
        diferencia_libro = abs(total_debe_libro - total_haber_libro)
        
        if diferencia_libro > 0.01:
            resultado.agregar_error(
                f"Libro desbalanceado. Total Debe: {total_debe_libro:.2f}, "
                f"Total Haber: {total_haber_libro:.2f}, Diferencia: {diferencia_libro:.2f}",
                "balance_libro"
            )
        
        # Estadísticas adicionales
        cuentas_utilizadas = set()
        for asiento in asientos:
            for detalle in asiento.detalles:
                cuentas_utilizadas.add(detalle.codigoCuenta)
        
        resultado.agregar_detalle("integridad_contable", {
            "total_debe_libro": total_debe_libro,
            "total_haber_libro": total_haber_libro,
            "diferencia": diferencia_libro,
            "libro_balanceado": diferencia_libro <= 0.01,
            "total_cuentas_utilizadas": len(cuentas_utilizadas),
            "total_asientos": len(asientos),
            "total_lineas": sum(len(a.detalles) for a in asientos)
        })
    
    async def _validar_preparacion_ple(
        self,
        libro: LibroDiarioSunatV3,
        asientos: List[AsientoContableSunatV3],
        config: SunatLibroConfig,
        resultado: SunatValidationResult
    ):
        """Validar preparación para generar archivo PLE"""
        # Verificar que todos los campos requeridos para PLE estén presentes
        campos_faltantes = []
        
        if not libro.empresaId:
            campos_faltantes.append("ID de empresa")
        
        if not config.empresa_ruc or len(config.empresa_ruc) != 11:
            campos_faltantes.append("RUC de empresa válido")
        
        # Validar que asientos tengan información mínima para PLE
        asientos_incompletos = []
        for asiento in asientos:
            if not asiento.descripcion.strip():
                asientos_incompletos.append(f"Asiento {asiento.numero}: sin descripción")
        
        if campos_faltantes:
            resultado.agregar_error(
                f"Campos requeridos para PLE faltantes: {', '.join(campos_faltantes)}",
                "preparacion_ple"
            )
        
        if asientos_incompletos:
            resultado.agregar_warning(
                f"Asientos con información incompleta para PLE: {'; '.join(asientos_incompletos[:3])}" +
                (f" y {len(asientos_incompletos) - 3} más" if len(asientos_incompletos) > 3 else ""),
                "asientos_incompletos_ple"
            )
        
        # Calcular nombre de archivo PLE que se generaría
        try:
            nombre_archivo_ple = self._generar_nombre_archivo_ple(
                config.empresa_ruc, libro.periodo
            )
            resultado.agregar_detalle("preparacion_ple", {
                "listo_para_ple": len(campos_faltantes) == 0,
                "nombre_archivo_ple": nombre_archivo_ple,
                "campos_faltantes": campos_faltantes,
                "asientos_incompletos": len(asientos_incompletos)
            })
        except Exception as e:
            resultado.agregar_warning(
                f"Error calculando nombre archivo PLE: {str(e)}",
                "nombre_archivo_ple"
            )
    
    # Métodos auxiliares
    
    def _es_periodo_valido(self, periodo: str) -> bool:
        """Validar formato de período"""
        return bool(re.match(r'^\d{4}(-\d{2})?$', periodo))
    
    def _fecha_en_periodo(self, fecha: date, periodo: str) -> bool:
        """Verificar si fecha está dentro del período"""
        if '-' in periodo:  # YYYY-MM
            year, month = map(int, periodo.split('-'))
            return fecha.year == year and fecha.month == month
        else:  # YYYY
            year = int(periodo)
            return fecha.year == year
    
    def _generar_nombre_archivo_ple(self, ruc: str, periodo: str) -> str:
        """Generar nombre de archivo PLE según nomenclatura SUNAT"""
        if '-' in periodo:  # YYYY-MM
            fecha = datetime.strptime(periodo, "%Y-%m")
        else:  # YYYY
            fecha = datetime.strptime(f"{periodo}-12", "%Y-%m")
        
        ruc_11_digitos = ruc.zfill(11)
        year = fecha.year
        month = fecha.month
        
        return (
            f"LE{ruc_11_digitos}"
            f"{year:04d}{month:02d}00"
            f"05010"  # Libro Diario formato 5.1
            f"01"     # Oportunidad presentación original
            f"01"     # Con información
            f".TXT"
        )
