"""
Lectura del resumen de un periodo (servicio 5.35 en Compras, 5.20 en Ventas).

SUNAT devuelve un TXT con una fila de cabecera, una fila por tipo de documento y
una fila `TOTAL` con los acumulados. Es la forma más barata de saber qué hay en
un periodo antes de operar sobre él: una sola llamada, sin ticket.

**Las columnas se localizan por nombre, nunca por posición.** Los dos libros no
tienen el mismo número de columnas —Compras trae 13 y Ventas 15— ni las mismas:
«Total CP» es la 12 en Compras y la 14 en Ventas. Buscar por índice devuelve
cero sin dar ningún error, que es la peor forma de fallar.
"""

from typing import Any, Dict, List, Optional

#: Columnas comunes a los dos libros.
COL_DOCUMENTOS = "Total Documentos"
COL_TOTAL = "Total CP"

#: La base imponible y el IGV se llaman distinto en cada libro; se prueba por
#: orden hasta encontrar una que exista.
ALIAS_BASE_IMPONIBLE = (
    "BI Gravado DG",                            # Compras
    "Base imponible de la operación gravada",   # Ventas
)
ALIAS_IGV = (
    "IGV / IPM DG",        # Compras
    "Monto Total del IGV",  # Ventas
)


def _indice(cabeceras: List[str], *nombres: str) -> Optional[int]:
    """Posición de la primera columna que coincida con alguno de los nombres."""
    limpias = [c.strip() for c in cabeceras]
    for nombre in nombres:
        if nombre in limpias:
            return limpias.index(nombre)
    return None


def _numero(campos: List[str], i: Optional[int]) -> Optional[float]:
    if i is None or len(campos) <= i:
        return None
    try:
        return float(campos[i].strip())
    except ValueError:
        return None


def _entero(campos: List[str], i: Optional[int]) -> Optional[int]:
    if i is None or len(campos) <= i:
        return None
    crudo = campos[i].strip()
    return int(crudo) if crudo.isdigit() else None


def parsear_resumen(contenido: str) -> Dict[str, Any]:
    """
    Extraer de un resumen lo que hace falta para decidir.

    Devuelve siempre las mismas claves, aunque el archivo venga vacío o con otra
    forma: quien lo consume necesita poder pintar algo sin comprobar diez casos.
    Un `None` significa «no se pudo determinar», que es distinto de cero.
    """
    lineas = [l for l in (contenido or "").strip().splitlines() if l.strip()]

    resultado: Dict[str, Any] = {
        "total_comprobantes": None,
        "total_importe": None,
        "total_base_imponible": None,
        "total_igv": None,
        "por_tipo": [],
        "total_lineas": len(lineas),
    }

    if len(lineas) < 2:
        return resultado

    cabeceras = lineas[0].split("|")
    i_docs = _indice(cabeceras, COL_DOCUMENTOS)
    i_total = _indice(cabeceras, COL_TOTAL)
    i_base = _indice(cabeceras, *ALIAS_BASE_IMPONIBLE)
    i_igv = _indice(cabeceras, *ALIAS_IGV)

    for linea in lineas[1:]:
        campos = linea.split("|")
        etiqueta = campos[0].strip()

        if etiqueta.upper() == "TOTAL":
            resultado["total_comprobantes"] = _entero(campos, i_docs)
            resultado["total_importe"] = _numero(campos, i_total)
            resultado["total_base_imponible"] = _numero(campos, i_base)
            resultado["total_igv"] = _numero(campos, i_igv)
            continue

        # Filas por tipo de documento: el desglose que se enseña antes de aceptar.
        if etiqueta:
            resultado["por_tipo"].append({
                "tipo": etiqueta,
                "documentos": _entero(campos, i_docs) or 0,
                "importe": _numero(campos, i_total) or 0.0,
            })

    resultado["columnas"] = [c.strip() for c in cabeceras]
    return resultado
