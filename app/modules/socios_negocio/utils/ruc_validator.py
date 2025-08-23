"""
Utilidades para validación de RUC peruano
Basado en el algoritmo oficial de SUNAT
"""

import re
from typing import Tuple

class RucValidator:
    """Validador de RUC peruano con algoritmo oficial"""
    
    # Factores de verificación para RUC
    FACTORES = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    
    @staticmethod
    def validar_formato(ruc: str) -> Tuple[bool, str]:
        """
        Valida el formato básico del RUC
        
        Args:
            ruc: Número de RUC como string
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if not ruc:
            return False, "RUC no puede estar vacío"
        
        # Limpiar espacios y caracteres no numéricos
        ruc_clean = re.sub(r'[^0-9]', '', ruc)
        
        # Verificar longitud
        if len(ruc_clean) != 11:
            return False, f"RUC debe tener 11 dígitos, tiene {len(ruc_clean)}"
        
        # Verificar que sea solo números
        if not ruc_clean.isdigit():
            return False, "RUC debe contener solo números"
        
        # Verificar primer dígito (tipo de contribuyente)
        primer_digito = ruc_clean[0]
        if primer_digito not in ['1', '2']:
            return False, f"RUC debe empezar con 1 o 2, empieza con {primer_digito}"
        
        return True, ""
    
    @staticmethod
    def calcular_digito_verificador(ruc: str) -> int:
        """
        Calcula el dígito verificador del RUC
        
        Args:
            ruc: RUC sin el dígito verificador (10 dígitos)
            
        Returns:
            int: Dígito verificador calculado
        """
        if len(ruc) != 10:
            raise ValueError("RUC debe tener 10 dígitos para calcular verificador")
        
        suma = 0
        for i, digito in enumerate(ruc):
            suma += int(digito) * RucValidator.FACTORES[i]
        
        resto = suma % 11
        
        if resto < 2:
            return resto
        else:
            return 11 - resto
    
    @staticmethod
    def validar_digito_verificador(ruc: str) -> Tuple[bool, str]:
        """
        Valida el dígito verificador del RUC
        
        Args:
            ruc: RUC completo (11 dígitos)
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if len(ruc) != 11:
            return False, "RUC debe tener 11 dígitos para validar"
        
        try:
            ruc_sin_verificador = ruc[:10]
            digito_verificador_actual = int(ruc[10])
            digito_verificador_calculado = RucValidator.calcular_digito_verificador(ruc_sin_verificador)
            
            if digito_verificador_actual == digito_verificador_calculado:
                return True, ""
            else:
                return False, f"Dígito verificador incorrecto. Esperado: {digito_verificador_calculado}, Actual: {digito_verificador_actual}"
        
        except (ValueError, IndexError) as e:
            return False, f"Error al validar dígito verificador: {str(e)}"
    
    @staticmethod
    def validar_ruc_completo(ruc: str) -> Tuple[bool, str]:
        """
        Validación completa del RUC peruano
        
        Args:
            ruc: Número de RUC
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        # Limpiar RUC
        ruc_clean = re.sub(r'[^0-9]', '', ruc)
        
        # Validar formato
        formato_valido, mensaje_formato = RucValidator.validar_formato(ruc_clean)
        if not formato_valido:
            return False, mensaje_formato
        
        # Validar dígito verificador
        verificador_valido, mensaje_verificador = RucValidator.validar_digito_verificador(ruc_clean)
        if not verificador_valido:
            return False, mensaje_verificador
        
        return True, "RUC válido"
    
    @staticmethod
    def obtener_tipo_contribuyente(ruc: str) -> str:
        """
        Obtiene el tipo de contribuyente basado en el primer dígito del RUC
        
        Args:
            ruc: Número de RUC
            
        Returns:
            str: Tipo de contribuyente
        """
        if not ruc or len(ruc) < 1:
            return "Desconocido"
        
        primer_digito = ruc[0]
        
        tipos = {
            '1': 'Persona Natural',
            '2': 'Persona Jurídica'
        }
        
        return tipos.get(primer_digito, 'Desconocido')
    
    @staticmethod
    def limpiar_ruc(ruc: str) -> str:
        """
        Limpia y normaliza el RUC
        
        Args:
            ruc: RUC con posibles caracteres extra
            
        Returns:
            str: RUC limpio solo con números
        """
        if not ruc:
            return ""
        
        return re.sub(r'[^0-9]', '', ruc)
    
    @staticmethod
    def formatear_ruc(ruc: str) -> str:
        """
        Formatea el RUC para visualización
        
        Args:
            ruc: RUC sin formato
            
        Returns:
            str: RUC formateado (ej: 20123456789)
        """
        ruc_clean = RucValidator.limpiar_ruc(ruc)
        
        if len(ruc_clean) == 11:
            return ruc_clean
        
        return ruc_clean


class DniValidator:
    """Validador de DNI peruano"""
    
    @staticmethod
    def validar_dni(dni: str) -> Tuple[bool, str]:
        """
        Valida DNI peruano
        
        Args:
            dni: Número de DNI
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if not dni:
            return False, "DNI no puede estar vacío"
        
        # Limpiar DNI
        dni_clean = re.sub(r'[^0-9]', '', dni)
        
        # Verificar longitud
        if len(dni_clean) != 8:
            return False, f"DNI debe tener 8 dígitos, tiene {len(dni_clean)}"
        
        # Verificar que sea solo números
        if not dni_clean.isdigit():
            return False, "DNI debe contener solo números"
        
        # Verificar que no sean todos números iguales
        if len(set(dni_clean)) == 1:
            return False, "DNI no puede tener todos los dígitos iguales"
        
        return True, "DNI válido"


class CeValidator:
    """Validador de Carnet de Extranjería"""
    
    @staticmethod
    def validar_ce(ce: str) -> Tuple[bool, str]:
        """
        Valida Carnet de Extranjería
        
        Args:
            ce: Número de CE
            
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if not ce:
            return False, "CE no puede estar vacío"
        
        # Limpiar CE (puede tener letras y números)
        ce_clean = re.sub(r'[^A-Za-z0-9]', '', ce)
        
        # Verificar longitud
        if len(ce_clean) < 8 or len(ce_clean) > 12:
            return False, f"CE debe tener entre 8 y 12 caracteres, tiene {len(ce_clean)}"
        
        return True, "CE válido"


def validar_documento(tipo_documento: str, numero_documento: str) -> Tuple[bool, str]:
    """
    Función principal para validar documentos según el tipo
    
    Args:
        tipo_documento: Tipo de documento (RUC, DNI, CE)
        numero_documento: Número del documento
        
    Returns:
        Tuple[bool, str]: (es_valido, mensaje_error)
    """
    if tipo_documento == 'RUC':
        return RucValidator.validar_ruc_completo(numero_documento)
    elif tipo_documento == 'DNI':
        return DniValidator.validar_dni(numero_documento)
    elif tipo_documento == 'CE':
        return CeValidator.validar_ce(numero_documento)
    else:
        return False, f"Tipo de documento no válido: {tipo_documento}"
