"""
PLEZipGenerator - Generador de Archivos ZIP Conforme SUNAT
=========================================================

Generador especializado para crear archivos ZIP que cumplen exactamente
con los requerimientos de compresión de SUNAT para envío de PLE.

Especificaciones SUNAT para ZIP:
- Compresión obligatoria para archivos PLE
- Método de compresión: ZIP estándar
- Nivel de compresión: Óptimo (no máximo para compatibilidad)
- Estructura interna: Un solo archivo TXT por ZIP
- Nomenclatura: Mismo nombre base que archivo TXT
- Codificación: Compatible con sistemas SUNAT

Características implementadas:
- Validación previa del archivo TXT
- Compresión con nivel óptimo
- Verificación integridad ZIP resultante
- Metadatos de archivo incluidos
- Logs detallados del proceso

Autor: Sistema ERP - Implementación SUNAT V3
Fecha: Agosto 2025
"""

import os
import zipfile
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PLEZipMetadata:
    """Metadatos del archivo ZIP generado"""
    nombre_archivo_zip: str
    nombre_archivo_txt_interno: str
    tamaño_txt_bytes: int
    tamaño_zip_bytes: int
    ratio_compresion: float
    hash_md5_txt: str
    hash_md5_zip: str
    fecha_creacion: datetime
    metodo_compresion: str
    nivel_compresion: int
    es_valido: bool
    errores: List[str]


@dataclass
class PLEZipValidationResult:
    """Resultado de validación del ZIP generado"""
    zip_valido: bool
    puede_extraer: bool
    archivo_txt_integro: bool
    tamaño_correcto: bool
    estructura_correcta: bool
    errores: List[str]
    warnings: List[str]


class PLEZipGenerator:
    """Generador de archivos ZIP conforme a normativa SUNAT"""
    
    def __init__(self):
        """Inicializar generador con configuración SUNAT"""
        self.logger = logging.getLogger(__name__)
        
        # Configuración según mejores prácticas SUNAT
        self.metodo_compresion = zipfile.ZIP_DEFLATED
        self.nivel_compresion = 6  # Óptimo: balance entre tamaño y compatibilidad
        self.buffer_size = 8192    # Tamaño buffer para I/O eficiente
        
        # Validaciones según normativa
        self.tamaño_maximo_txt = 50 * 1024 * 1024  # 50MB máximo archivo TXT
        self.tamaño_maximo_zip = 10 * 1024 * 1024  # 10MB máximo archivo ZIP
        
    def generar_zip_desde_contenido(
        self,
        contenido_txt: str,
        nombre_archivo_base: str,
        directorio_salida: Optional[str] = None
    ) -> PLEZipMetadata:
        """
        Generar archivo ZIP desde contenido TXT en memoria
        
        Args:
            contenido_txt: Contenido del archivo TXT a comprimir
            nombre_archivo_base: Nombre base (sin extensión) para los archivos
            directorio_salida: Directorio donde guardar ZIP (opcional)
            
        Returns:
            PLEZipMetadata: Metadatos completos del archivo ZIP generado
        """
        errores = []
        
        try:
            # 1. Validar entrada
            if not contenido_txt or not contenido_txt.strip():
                errores.append("Contenido TXT vacío o inválido")
                return self._crear_metadata_error(errores)
            
            if not nombre_archivo_base:
                errores.append("Nombre de archivo base requerido")
                return self._crear_metadata_error(errores)
            
            # 2. Preparar nombres de archivos
            nombre_txt = f"{nombre_archivo_base}.TXT"
            nombre_zip = f"{nombre_archivo_base}.ZIP"
            
            # 3. Validar tamaños
            tamaño_txt = len(contenido_txt.encode('utf-8'))
            if tamaño_txt > self.tamaño_maximo_txt:
                errores.append(f"Archivo TXT demasiado grande: {tamaño_txt} bytes (máximo: {self.tamaño_maximo_txt})")
                return self._crear_metadata_error(errores)
            
            # 4. Calcular hash MD5 del contenido TXT
            hash_txt = hashlib.md5(contenido_txt.encode('utf-8')).hexdigest()
            
            # 5. Crear ZIP en memoria
            buffer_zip = BytesIO()
            
            with zipfile.ZipFile(
                buffer_zip, 
                'w', 
                compression=self.metodo_compresion,
                compresslevel=self.nivel_compresion
            ) as zip_file:
                # Agregar archivo TXT al ZIP
                zip_file.writestr(
                    nombre_txt,
                    contenido_txt.encode('utf-8'),
                    compress_type=self.metodo_compresion
                )
                
                self.logger.info(f"Archivo {nombre_txt} agregado al ZIP exitosamente")
            
            # 6. Obtener contenido ZIP
            contenido_zip = buffer_zip.getvalue()
            tamaño_zip = len(contenido_zip)
            
            # 7. Validar tamaño ZIP
            if tamaño_zip > self.tamaño_maximo_zip:
                errores.append(f"Archivo ZIP demasiado grande: {tamaño_zip} bytes (máximo: {self.tamaño_maximo_zip})")
                # Continuar para reportar metadata, pero marcar como error
            
            # 8. Calcular hash MD5 del ZIP
            hash_zip = hashlib.md5(contenido_zip).hexdigest()
            
            # 9. Calcular ratio de compresión
            ratio_compresion = (1 - (tamaño_zip / tamaño_txt)) * 100 if tamaño_txt > 0 else 0
            
            # 10. Guardar archivo ZIP si se especifica directorio
            ruta_zip_completa = None
            if directorio_salida:
                try:
                    # Crear directorio si no existe
                    Path(directorio_salida).mkdir(parents=True, exist_ok=True)
                    
                    # Escribir archivo ZIP
                    ruta_zip_completa = os.path.join(directorio_salida, nombre_zip)
                    with open(ruta_zip_completa, 'wb') as f:
                        f.write(contenido_zip)
                    
                    self.logger.info(f"Archivo ZIP guardado en: {ruta_zip_completa}")
                    
                except Exception as e:
                    errores.append(f"Error guardando archivo ZIP: {str(e)}")
            
            # 11. Validar integridad del ZIP creado
            validacion = self._validar_zip_creado(contenido_zip, contenido_txt, nombre_txt)
            if not validacion.zip_valido:
                errores.extend(validacion.errores)
            
            # 12. Crear metadata del resultado
            metadata = PLEZipMetadata(
                nombre_archivo_zip=nombre_zip,
                nombre_archivo_txt_interno=nombre_txt,
                tamaño_txt_bytes=tamaño_txt,
                tamaño_zip_bytes=tamaño_zip,
                ratio_compresion=round(ratio_compresion, 2),
                hash_md5_txt=hash_txt,
                hash_md5_zip=hash_zip,
                fecha_creacion=datetime.utcnow(),
                metodo_compresion=self._obtener_nombre_metodo_compresion(),
                nivel_compresion=self.nivel_compresion,
                es_valido=len(errores) == 0,
                errores=errores
            )
            
            if metadata.es_valido:
                self.logger.info(
                    f"ZIP generado exitosamente: {nombre_zip} "
                    f"(Compresión: {ratio_compresion:.1f}%, "
                    f"Tamaño: {tamaño_txt} → {tamaño_zip} bytes)"
                )
            else:
                self.logger.error(f"ZIP generado con errores: {errores}")
            
            return metadata
            
        except Exception as e:
            errores.append(f"Error crítico generando ZIP: {str(e)}")
            self.logger.error(f"Error crítico en generación ZIP: {str(e)}")
            return self._crear_metadata_error(errores)
    
    def generar_zip_desde_archivo(
        self,
        ruta_archivo_txt: str,
        directorio_salida: Optional[str] = None
    ) -> PLEZipMetadata:
        """
        Generar archivo ZIP desde archivo TXT existente
        
        Args:
            ruta_archivo_txt: Ruta completa al archivo TXT
            directorio_salida: Directorio donde guardar ZIP (opcional)
            
        Returns:
            PLEZipMetadata: Metadatos completos del archivo ZIP generado
        """
        try:
            # Validar que archivo TXT existe
            if not os.path.exists(ruta_archivo_txt):
                return self._crear_metadata_error([f"Archivo TXT no encontrado: {ruta_archivo_txt}"])
            
            # Leer contenido del archivo
            with open(ruta_archivo_txt, 'r', encoding='utf-8') as f:
                contenido_txt = f.read()
            
            # Obtener nombre base del archivo (sin extensión)
            nombre_base = os.path.splitext(os.path.basename(ruta_archivo_txt))[0]
            
            # Usar método principal
            return self.generar_zip_desde_contenido(
                contenido_txt, 
                nombre_base, 
                directorio_salida
            )
            
        except Exception as e:
            self.logger.error(f"Error leyendo archivo TXT: {str(e)}")
            return self._crear_metadata_error([f"Error leyendo archivo TXT: {str(e)}"])
    
    def validar_zip_conforme_sunat(self, ruta_archivo_zip: str) -> PLEZipValidationResult:
        """
        Validar que un archivo ZIP cumple con los requerimientos SUNAT
        
        Args:
            ruta_archivo_zip: Ruta al archivo ZIP a validar
            
        Returns:
            PLEZipValidationResult: Resultado detallado de validación
        """
        errores = []
        warnings = []
        
        try:
            # 1. Verificar que archivo existe
            if not os.path.exists(ruta_archivo_zip):
                errores.append(f"Archivo ZIP no encontrado: {ruta_archivo_zip}")
                return PLEZipValidationResult(
                    zip_valido=False,
                    puede_extraer=False,
                    archivo_txt_integro=False,
                    tamaño_correcto=False,
                    estructura_correcta=False,
                    errores=errores,
                    warnings=warnings
                )
            
            # 2. Verificar tamaño del archivo
            tamaño_zip = os.path.getsize(ruta_archivo_zip)
            tamaño_correcto = tamaño_zip <= self.tamaño_maximo_zip
            
            if not tamaño_correcto:
                errores.append(f"ZIP demasiado grande: {tamaño_zip} bytes (máximo: {self.tamaño_maximo_zip})")
            
            # 3. Intentar abrir y validar estructura ZIP
            puede_extraer = True
            estructura_correcta = True
            archivo_txt_integro = True
            
            try:
                with zipfile.ZipFile(ruta_archivo_zip, 'r') as zip_file:
                    # Verificar que ZIP no está corrupto
                    resultado_test = zip_file.testzip()
                    if resultado_test:
                        errores.append(f"ZIP corrupto, archivo problemático: {resultado_test}")
                        puede_extraer = False
                    
                    # Obtener lista de archivos
                    lista_archivos = zip_file.namelist()
                    
                    # Validar estructura (debe contener exactamente 1 archivo TXT)
                    archivos_txt = [f for f in lista_archivos if f.upper().endswith('.TXT')]
                    
                    if len(archivos_txt) != 1:
                        errores.append(f"ZIP debe contener exactamente 1 archivo TXT, encontrados: {len(archivos_txt)}")
                        estructura_correcta = False
                    
                    if len(lista_archivos) != 1:
                        warnings.append(f"ZIP contiene {len(lista_archivos)} archivos, se recomienda solo 1")
                    
                    # Validar contenido del archivo TXT interno
                    if archivos_txt:
                        try:
                            contenido_txt = zip_file.read(archivos_txt[0]).decode('utf-8')
                            if not contenido_txt.strip():
                                errores.append("Archivo TXT interno está vacío")
                                archivo_txt_integro = False
                        except Exception as e:
                            errores.append(f"Error leyendo TXT interno: {str(e)}")
                            archivo_txt_integro = False
                            
            except zipfile.BadZipFile:
                errores.append("Archivo no es un ZIP válido")
                puede_extraer = False
                estructura_correcta = False
                archivo_txt_integro = False
            except Exception as e:
                errores.append(f"Error validando ZIP: {str(e)}")
                puede_extraer = False
            
            # 4. Determinar resultado final
            zip_valido = (
                len(errores) == 0 and 
                puede_extraer and 
                estructura_correcta and 
                archivo_txt_integro and 
                tamaño_correcto
            )
            
            return PLEZipValidationResult(
                zip_valido=zip_valido,
                puede_extraer=puede_extraer,
                archivo_txt_integro=archivo_txt_integro,
                tamaño_correcto=tamaño_correcto,
                estructura_correcta=estructura_correcta,
                errores=errores,
                warnings=warnings
            )
            
        except Exception as e:
            errores.append(f"Error crítico validando ZIP: {str(e)}")
            return PLEZipValidationResult(
                zip_valido=False,
                puede_extraer=False,
                archivo_txt_integro=False,
                tamaño_correcto=False,
                estructura_correcta=False,
                errores=errores,
                warnings=warnings
            )
    
    # ================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ================================
    
    def _validar_zip_creado(
        self, 
        contenido_zip: bytes, 
        contenido_txt_original: str, 
        nombre_txt_esperado: str
    ) -> PLEZipValidationResult:
        """Validar integridad del ZIP recién creado"""
        errores = []
        warnings = []
        
        try:
            # Crear ZIP temporal en memoria para validación
            buffer_zip = BytesIO(contenido_zip)
            
            with zipfile.ZipFile(buffer_zip, 'r') as zip_file:
                # Verificar integridad
                resultado_test = zip_file.testzip()
                if resultado_test:
                    errores.append(f"ZIP creado está corrupto: {resultado_test}")
                
                # Verificar contenido
                lista_archivos = zip_file.namelist()
                if nombre_txt_esperado not in lista_archivos:
                    errores.append(f"Archivo esperado {nombre_txt_esperado} no encontrado en ZIP")
                else:
                    # Verificar contenido TXT extraído
                    contenido_extraido = zip_file.read(nombre_txt_esperado).decode('utf-8')
                    if contenido_extraido != contenido_txt_original:
                        errores.append("Contenido TXT extraído no coincide con original")
            
            return PLEZipValidationResult(
                zip_valido=len(errores) == 0,
                puede_extraer=True,
                archivo_txt_integro=len(errores) == 0,
                tamaño_correcto=True,
                estructura_correcta=len(errores) == 0,
                errores=errores,
                warnings=warnings
            )
            
        except Exception as e:
            errores.append(f"Error validando ZIP creado: {str(e)}")
            return PLEZipValidationResult(
                zip_valido=False,
                puede_extraer=False,
                archivo_txt_integro=False,
                tamaño_correcto=False,
                estructura_correcta=False,
                errores=errores,
                warnings=warnings
            )
    
    def _crear_metadata_error(self, errores: List[str]) -> PLEZipMetadata:
        """Crear metadata de error"""
        return PLEZipMetadata(
            nombre_archivo_zip="",
            nombre_archivo_txt_interno="",
            tamaño_txt_bytes=0,
            tamaño_zip_bytes=0,
            ratio_compresion=0.0,
            hash_md5_txt="",
            hash_md5_zip="",
            fecha_creacion=datetime.utcnow(),
            metodo_compresion="",
            nivel_compresion=0,
            es_valido=False,
            errores=errores
        )
    
    def _obtener_nombre_metodo_compresion(self) -> str:
        """Obtener nombre legible del método de compresión"""
        metodos = {
            zipfile.ZIP_STORED: "Sin compresión",
            zipfile.ZIP_DEFLATED: "Deflate",
            zipfile.ZIP_BZIP2: "BZIP2",
            zipfile.ZIP_LZMA: "LZMA"
        }
        return metodos.get(self.metodo_compresion, "Desconocido")
