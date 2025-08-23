"""
Utilidades para validación de documentos peruanos
"""

import re
from typing import Tuple

def validar_ruc(ruc: str) -> Tuple[bool, str]:
    """
    Valida que el RUC tenga el formato correcto
    
    Args:
        ruc: RUC a validar
        
    Returns:
        Tuple[bool, str]: (es_valido, mensaje_error)
    """
    if not ruc:
        return False, "RUC no puede estar vacío"
    
    # Limpiar RUC
    ruc_clean = re.sub(r'[^0-9]', '', ruc)
    
    if len(ruc_clean) != 11:
        return False, f"RUC debe tener 11 dígitos, tiene {len(ruc_clean)}"
    
    if not ruc_clean.isdigit():
        return False, "RUC debe contener solo números"
    
    # Los primeros dos dígitos deben ser válidos para tipo de contribuyente
    tipo_contrib = ruc_clean[:2]
    tipos_validos = ["10", "15", "17", "20"]
    
    if tipo_contrib not in tipos_validos:
        return False, f"RUC debe empezar con 10, 15, 17 o 20, empieza con {tipo_contrib}"
    
    return True, "RUC válido"

def validar_dni(dni: str) -> Tuple[bool, str]:
    """
    Valida que el DNI tenga el formato correcto
    
    Args:
        dni: DNI a validar
        
    Returns:
        Tuple[bool, str]: (es_valido, mensaje_error)
    """
    if not dni:
        return False, "DNI no puede estar vacío"
    
    # Limpiar DNI
    dni_clean = re.sub(r'[^0-9]', '', dni)
    
    if len(dni_clean) != 8:
        return False, f"DNI debe tener 8 dígitos, tiene {len(dni_clean)}"
    
    if not dni_clean.isdigit():
        return False, "DNI debe contener solo números"
    
    # Verificar que no sean todos números iguales
    if len(set(dni_clean)) == 1:
        return False, "DNI no puede tener todos los dígitos iguales"
    
    return True, "DNI válido"

def limpiar_documento(documento: str) -> str:
    """
    Limpia un documento eliminando caracteres no numéricos
    
    Args:
        documento: Documento a limpiar
        
    Returns:
        str: Documento limpio solo con números
    """
    if not documento:
        return ""
    
    return re.sub(r'[^0-9]', '', documento)

def determinar_tipo_documento(documento: str) -> str:
    """
    Determina el tipo de documento basado en su longitud
    
    Args:
        documento: Documento a analizar
        
    Returns:
        str: Tipo de documento (RUC, DNI, CE, DESCONOCIDO)
    """
    documento_clean = limpiar_documento(documento)
    
    if len(documento_clean) == 11:
        return "RUC"
    elif len(documento_clean) == 8:
        return "DNI"
    elif 8 <= len(documento_clean) <= 12:
        return "CE"
    else:
        return "DESCONOCIDO"
