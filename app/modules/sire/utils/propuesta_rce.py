"""
Lectura del TXT de la propuesta de compras (RCE, servicio 5.34).

La propuesta no llega como JSON: el 5.34 devuelve un `numTicket`, el archivo se
descarga con el 5.32 y lo que sale es un TXT con los campos separados por `|` y
una primera fila con los nombres de columna.

Vivía dentro de `rce_comprobantes_routes.py`, donde solo lo podía usar ese
endpoint. Está aquí porque la importación al registro de compras necesita
exactamente lo mismo, y porque un parser que nadie puede probar por separado es
un parser que nadie prueba.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


#: Nombre de cada columna del TXT de propuesta, tal como lo rotula SUNAT.
#: Se localizan **por nombre y no por posición** porque el orden ha cambiado
#: entre versiones del manual; si SUNAT renombra una, ese campo queda a 0 y el
#: resto del comprobante se sigue leyendo.
COLUMNAS_PROPUESTA: Dict[str, str] = {
    "ruc_proveedor": "Nro Doc Identidad",
    "razon_social_proveedor": "Apellidos Nombres/ Razón  Social",
    "fecha_emision": "Fecha de emisión",
    "tipo_documento": "Tipo CP/Doc.",
    "serie": "Serie del CDP",
    "numero": "Nro CP o Doc. Nro Inicial (Rango)",
    "total_cp": "Total CP",
    "moneda": "Moneda",
    "tipo_cambio": "Tipo de Cambio",
    "bi_gravado": "BI Gravado DG",
    "igv": "IGV / IPM DG",
    "valor_no_gravado": "Valor Adq. NG",
    "isc": "ISC",
    "icbper": "ICBPER",
    "otros_tributos": "Otros Trib/ Cargos",
}

#: Columnas que existen en la propuesta pero no en todas las versiones. No se
#: incluyen en COLUMNAS_PROPUESTA para no ensuciar el aviso de columna ausente.
COLUMNAS_OPCIONALES: Dict[str, str] = {
    "tipo_doc_identidad": "Tipo Doc Identidad",
    "fecha_vencimiento": "Fecha Vcto/Pago",
    "car_sunat": "CAR SUNAT",
    "numero_final": "Nro Final (Rango)",
    "anio_dua": "Año de emisión de la DUA o DSI",
    "constancia_detraccion": "Nro de la Constancia de Depósito de Detracción",
    "fecha_detraccion": "Fecha de emisión de la Constancia de Depósito de Detracción",
    "marca_retencion": "Marca del Comprobante de Pago sujeto a Retención",
    "clasificacion": "Clasif. de Bienes y Servicios",
    "contrato": "Identificación del Contrato o del proyecto",
    "error_tipo": "Error Tipo 1",
    "estado": "Estado",
}


def parsear_propuesta(contenido: str, periodo: str) -> Tuple[List[dict], dict]:
    """
    Convertir el TXT de la propuesta (5.34) en comprobantes.

    Args:
        contenido: el texto del archivo ya descomprimido.
        periodo: AAAAMM, se copia en cada comprobante.

    Returns:
        (comprobantes, metadatos). Si el archivo no es utilizable, la lista va
        vacía y los metadatos llevan la clave `error` explicando por qué.
    """
    lineas = contenido.strip().splitlines()

    if len(lineas) < 2:
        return [], {"error": "El archivo no contiene datos", "total_lineas": len(lineas)}

    cabeceras = lineas[0].split("|")
    todas = {**COLUMNAS_PROPUESTA, **COLUMNAS_OPCIONALES}

    indices: Dict[str, int] = {}
    for campo, nombre in todas.items():
        try:
            indices[campo] = cabeceras.index(nombre)
        except ValueError:
            if campo in COLUMNAS_PROPUESTA:
                logger.warning(
                    f"Columna '{nombre}' no encontrada en la propuesta de {periodo}"
                )
            indices[campo] = -1

    def texto(campos: List[str], campo: str, por_defecto: str = "") -> str:
        i = indices.get(campo, -1)
        return campos[i].strip() if 0 <= i < len(campos) else por_defecto

    def numero(campos: List[str], campo: str, por_defecto: float = 0.0) -> float:
        crudo = texto(campos, campo)
        if not crudo:
            return por_defecto
        try:
            return float(crudo)
        except ValueError:
            return por_defecto

    comprobantes: List[dict] = []
    for n, linea in enumerate(lineas[1:], start=1):
        if not linea.strip():
            continue

        campos = linea.split("|")
        if len(campos) < len(cabeceras):
            logger.warning(
                f"Línea {n} de la propuesta incompleta: "
                f"{len(campos)} campos frente a {len(cabeceras)} esperados"
            )
            continue

        comprobantes.append({
            # Proveedor
            "ruc_proveedor": texto(campos, "ruc_proveedor"),
            "tipo_doc_identidad": texto(campos, "tipo_doc_identidad"),
            "razon_social_proveedor": texto(campos, "razon_social_proveedor"),
            # Comprobante
            "fecha_emision": texto(campos, "fecha_emision"),
            "fecha_vencimiento": texto(campos, "fecha_vencimiento"),
            "tipo_documento": texto(campos, "tipo_documento"),
            "serie_comprobante": texto(campos, "serie"),
            "numero_comprobante": texto(campos, "numero"),
            "numero_final_rango": texto(campos, "numero_final"),
            "anio_emision_dua_dsi": texto(campos, "anio_dua"),
            # Importes
            "moneda": texto(campos, "moneda", "PEN"),
            "tipo_cambio": numero(campos, "tipo_cambio", 1.0),
            "base_imponible_gravada": numero(campos, "bi_gravado"),
            "igv": numero(campos, "igv"),
            "valor_adquisicion_no_gravada": numero(campos, "valor_no_gravado"),
            "isc": numero(campos, "isc"),
            "icbper": numero(campos, "icbper"),
            "otros_tributos": numero(campos, "otros_tributos"),
            "importe_total": numero(campos, "total_cp"),
            # Detracción, retención y clasificación
            "numero_constancia_detraccion": texto(campos, "constancia_detraccion"),
            "fecha_emision_detraccion": texto(campos, "fecha_detraccion"),
            "marca_comprobante_retencion": texto(campos, "marca_retencion"),
            "clasificacion_bienes_servicios": texto(campos, "clasificacion"),
            "identificacion_contrato": texto(campos, "contrato"),
            "indicador_error": texto(campos, "error_tipo"),
            # Trazabilidad
            "car_sunat": texto(campos, "car_sunat"),
            "estado": texto(campos, "estado"),
            "periodo": periodo,
        })

    return comprobantes, {
        "headers_encontrados": len(cabeceras),
        "campos_mapeados": {k: v for k, v in indices.items() if v >= 0},
        "campos_ausentes": [k for k in COLUMNAS_PROPUESTA if indices.get(k, -1) < 0],
        "total_lineas": len(lineas),
    }


def parsear_linea_total(lineas: List[str]) -> Optional[Dict[str, Any]]:
    """
    Extraer la fila TOTAL del resumen (servicio 5.35).

    El resumen es un TXT con campos separados por `|` y una fila que empieza por
    "TOTAL " con los acumulados del periodo. Si SUNAT cambia el número de
    columnas se devuelve None en vez de reventar: el contenido íntegro viaja
    igualmente en `contenido_completo`.
    """
    def numero(campos: List[str], i: int) -> float:
        if len(campos) <= i:
            return 0.0
        try:
            return float(campos[i])
        except ValueError:
            return 0.0

    for linea in lineas:
        if not linea.startswith("TOTAL "):
            continue
        campos = linea.split("|")
        if len(campos) < 12:
            continue
        return {
            "tipo": "TOTAL",
            "total_documentos": int(campos[1]) if campos[1].strip().isdigit() else 0,
            "total_cp": numero(campos, 12),
            "valor_adq_ng": numero(campos, 8),
            "contenido_raw": linea,
        }

    return None
