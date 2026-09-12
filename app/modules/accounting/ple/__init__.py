"""
Módulo PLE (Programa de Libros Electrónicos)
===========================================

Sistema completo para la generación de archivos PLE para SUNAT.
Integrado con las 12 tablas SUNAT oficiales implementadas.

Componentes principales:
- PLEAnalyzer: Análisis y preparación de datos contables
- PLEGenerator: Generación de archivos TXT en formato SUNAT
- PLEFormatter: Formateo específico de campos según normativa
- PLESunatValidator: Validación usando tablas SUNAT oficiales

Autor: Sistema ERP
Fecha: Agosto 2025
Versión: 2.0 - Fase 2: Integración con Tablas SUNAT
"""

# Estos imports estuvieron comentados con la nota "temporalmente, para evitar
# errores de importación". Lo que los rompiera ya está arreglado —los seis
# submódulos importan por separado sin problema— pero nadie los restauró,
# así que el módulo prometía en `__all__` nombres que no exportaba y
# `libro_diario_service.exportar_a_ple` moría con ImportError al usarlos.
from .ple_analyzer import PLEDataAnalyzer, PLEAnalysisResult
from .ple_generator import PLEGenerator, PLEArchivo, PLEOptions
from .ple_formatter import PLEFormatter, PLELineFormat
from .ple_sunat_validator import (
    PLESUNATValidator,
    PLEValidationResult,
    SUNATValidationError,
    SUNATValidationWarning,
    SUNATEnrichmentData,
)

__all__ = [
    "PLEDataAnalyzer",
    "PLEAnalysisResult",
    "PLEGenerator", 
    "PLEArchivo",
    "PLEOptions",
    "PLEFormatter",
    "PLELineFormat",
    "PLESUNATValidator",
    "PLEValidationResult",
    "SUNATValidationError",
    "SUNATValidationWarning",
    "SUNATEnrichmentData"
]
