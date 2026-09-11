"""
Catálogo de servicios Web API de SUNAT SIRE — Ventas (RVIE).

Verificado contra el "Manual del Servicio API del Registro de Ventas e
Información Electrónica" (RVIE, v30.0, SUNAT/CANVIA). Cada función lleva su
número de servicio.

Lo que hay que tener presente al venir de Compras, porque **no** se puede
extrapolar:

  - `codLibro` es `140000`, no `080000`.
  - El recurso de aceptar propuesta se llama `aceptapropuesta` (sin la "r" de
    `aceptarpropuesta`) y cuelga de `rvie/`, no de `rvierce/`.
  - `codTipoArchivo` **invierte** dos códigos: aquí 1 es excel y 2 es csv; en
    Compras 1 era csv y 2 excel.
  - `codProceso` del reemplazo de propuesta es 3, no 61.
  - 5.9, 5.15 y 5.36 pueden responder **sin** `numTicket`: eso significa que el
    proceso terminó bien de forma síncrona.

Los servicios de ticket (5.16/5.17), resumen (5.20) y padrón de periodos (5.2)
comparten URL con Compras y viven en `sunat_endpoints`; aquí solo cambia el
`codLibro` que se les pasa.
"""

from typing import Final

from .sunat_endpoints import _LIBROS

#: Rama específica de ventas. Ojo: conviven `rvie/` y `rvierce/` según servicio.
_RVIE: Final = f"{_LIBROS}/rvie"
_RVIERCE: Final = f"{_LIBROS}/rvierce"


# ---------------------------------------------------------------------------
# Códigos propios de Ventas
# ---------------------------------------------------------------------------

class CodTipoArchivoRvie:
    """
    Anexo IV del manual de Ventas.

    Los códigos 1 y 2 están **intercambiados** respecto a Compras. Usar la clase
    de Compras aquí produce un excel donde se esperaba un csv, sin ningún error
    que lo delate.
    """
    TXT: Final = "0"
    EXCEL: Final = "1"
    CSV: Final = "2"


class CodProcesoRvie:
    """Anexo I, valores que usa Ventas en las cargas TUS."""
    IMPORTAR_CP_PROPUESTA: Final = "1"        # 5.4
    REEMPLAZO_PROPUESTA: Final = "3"          # 5.3 — en Compras es 61
    IMPORTAR_CP_PRELIMINAR: Final = "4"       # 5.5
    GENERAR_REPORTE_LIBRO: Final = "23"       # 5.27–5.30
    AJUSTES_POSTERIORES: Final = "87"         # 5.6
    AJUSTES_PERIODOS_ANTERIORES: Final = "88" # 5.7


class CodTipoCorrelativo:
    """Anexo II del manual de Ventas (en Compras ese anexo era otra cosa)."""
    ENVIOS_MASIVOS: Final = "01"
    OPERACION_GENERACION: Final = "02"
    SOLICITUD_ARCHIVO: Final = "03"
    CARGA_COMPARACION: Final = "04"


class ErrorNegocioRvie:
    """
    §4.3 — errores de negocio que solo existen en Ventas.

    Son los que permiten distinguir «te has equivocado de paso» de «SUNAT ya
    sabe algo que tú no», y reconciliar el estado local en vez de fallar.
    """
    # 5.9 registrar preliminar
    AUN_EN_PROPUESTA: Final = "2293"
    YA_EN_PRELIMINAR_REGISTRADO: Final = "2294"
    YA_GENERADO_DESDE_PORTAL: Final = "2295"
    # 5.36 eliminar preliminar registrado
    NO_REGISTRADO_AUN: Final = "2296"
    REGISTRO_YA_GENERADO: Final = "2297"
    # 5.15 eliminar reemplazo
    SIN_REEMPLAZO_QUE_ELIMINAR: Final = "2298"
    EN_PRELIMINAR_REGISTRADO: Final = "2299"
    GENERADO_DESDE_PORTAL: Final = "2300"
    # general
    LIBRO_NO_EXISTE: Final = "1010"


# ---------------------------------------------------------------------------
# Bloque A — Flujo principal (5.3–5.9)
# ---------------------------------------------------------------------------

#: 5.3 y 5.4 — carga TUS que afecta a la propuesta.
UPLOAD_PROPUESTA: Final = f"{_RVIERCE}/receptorpropuesta/web/propuesta/upload"

#: 5.5 — carga TUS que afecta al preliminar.
UPLOAD_PRELIMINAR: Final = f"{_RVIERCE}/receptorpreliminar/web/preliminar/upload"

#: 5.6 y 5.7 — carga TUS de ajustes posteriores.
UPLOAD_AJUSTES_POSTERIORES: Final = (
    f"{_RVIERCE}/receptorajustesposteriores/web/ajustesposteriores/upload"
)


def aceptar_propuesta(per_tributario: str) -> str:
    """
    5.8 Aceptar la propuesta del RVIE. Sin cuerpo. Devuelve `numTicket`.

    Cuelga de `rvie/` y el recurso es `aceptapropuesta`: dos diferencias con el
    equivalente de Compras que es fácil arrastrar por copia.
    """
    return f"{_RVIE}/propuesta/web/propuesta/{per_tributario}/aceptapropuesta"


def registrar_preliminar(per_tributario: str) -> str:
    """
    5.9 Registrar el preliminar. Sin cuerpo.

    Puede responder vacío (terminó bien) o con un `numTicket` opcional que hay
    que seguir con 5.16 hasta el estado 06.
    """
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/{per_tributario}/registrapreliminar"


# ---------------------------------------------------------------------------
# Bloque B — Ajustes de propuesta propios de Ventas (5.10–5.12)
# ---------------------------------------------------------------------------

def retirar_comprobante(per_tributario: str) -> str:
    """
    5.10 Exclusión **definitiva e irreversible** de notas de crédito y facturas.

    Query: codCar, codSituacion (0 inactivo, 1 activo). No tiene vuelta atrás:
    conviene exigir confirmación explícita antes de llamarlo.
    """
    return f"{_RVIE}/propuesta/web/propuesta/{per_tributario}/retiracomprobante"


def tipo_cambio_masivo(per_tributario: str) -> str:
    """5.11 Agregar tipo de cambio masivo. Body: array de fecEmision/codMoneda/mtoTipoCambio."""
    return f"{_RVIE}/propuesta/web/masivo/{per_tributario}/guardacomplementomasivo"


def tipo_cambio_individual(per_tributario: str) -> str:
    """5.12 Editar el tipo de cambio de un comprobante (PUT)."""
    return f"{_RVIE}/propuesta/web/propuesta/{per_tributario}/complementoindividual"


# ---------------------------------------------------------------------------
# Bloque C — Eliminación (5.13–5.15)
# ---------------------------------------------------------------------------

def eliminar_comprobante_propuesta(per_tributario: str) -> str:
    """
    5.13 Eliminar comprobantes de la propuesta (DELETE).

    En la v24 pasó de POST a DELETE para admitir eliminación masiva.
    """
    return f"{_RVIE}/propuesta/web/propuesta/{per_tributario}/eliminacomprobante"


def eliminar_comprobante_preliminar(per_tributario: str) -> str:
    """5.14 Eliminar comprobantes del preliminar (POST)."""
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/{per_tributario}/comprobantepreliminar"


def eliminar_reemplazo(per_tributario: str) -> str:
    """
    5.15 Eliminar el preliminar **no registrado** y los datos del reemplazo (PUT).

    Query: codLibro. No confundir con 5.36, que es para el ya registrado.
    """
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/{per_tributario}/eliminarreemplazo"


# ---------------------------------------------------------------------------
# Bloque E — Descargas (5.18–5.22)
# ---------------------------------------------------------------------------

def descargar_propuesta(per_tributario: str) -> str:
    """5.18 Descargar la propuesta. Query: codTipoArchivo y filtros. Devuelve numTicket."""
    return f"{_RVIE}/propuesta/web/propuesta/{per_tributario}/exportapropuesta"


def descargar_no_incluidos(per_tributario: str) -> str:
    """5.19 Descargar los comprobantes no incluidos del periodo vigente."""
    return f"{_RVIE}/propuesta/web/noincluidos/{per_tributario}/exportanoincluidos"


def resumen_inconsistencias(per_tributario: str) -> str:
    """5.21 Resumen de inconsistencias. Query: codTipoResumen, codLibro."""
    return f"{_RVIERCE}/resumen/web/resumeninconsistencias/{per_tributario}"


def exportar_preliminar(per_tributario: str) -> str:
    """5.22 Exportar el preliminar del registro de ventas. Devuelve numTicket."""
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/{per_tributario}/reportepreliminar"


# ---------------------------------------------------------------------------
# Bloque F — Casillas e inconsistencias (5.23–5.25, 5.32)
# ---------------------------------------------------------------------------

def reporte_casillas(per_tributario: str, tipo_reporte: str, tipo_descarga: str) -> str:
    """
    5.23 Reporte de casillas. Descarga directa.

    `tipo_reporte`: 1 preliminar, 2 comparada. `tipo_descarga`: 0 txt, 1 xls,
    2 pdf — el pdf solo está documentado en Ventas.
    """
    return (
        f"{_RVIERCE}/casillas/e/casillaspropuestas/"
        f"{per_tributario}/reporte/{tipo_reporte}/{tipo_descarga}"
    )


def inconsistencias_preliminar_registrado(per_tributario: str, num_cas: str) -> str:
    """
    5.24 Inconsistencias del preliminar registrado. Descarga directa.

    `num_cas` es el número de casilla del Anexo V, exclusivo de Ventas.
    """
    return (
        f"{_RVIERCE}/casillas/inconsistenciaslibros/"
        f"{per_tributario}/{num_cas}/reporteinconsistencia"
    )


def inconsistencias_por_comprobante(per_tributario: str) -> str:
    """5.25 Inconsistencias por comprobante de pago. Devuelve numTicket."""
    return f"{_RVIE}/inconsistencias/web/periodoinconsistencias/{per_tributario}/exporta"


def reporte_car(per_tributario: str) -> str:
    """5.32 Reporte CAR. Query: codOrigenEnvio, codLibro, codFase. Devuelve numTicket."""
    return f"{_RVIERCE}/gestionlibro/web/comprobanteslibros/{per_tributario}/reportecar"


# ---------------------------------------------------------------------------
# Bloque G — Constancia y descargas consolidadas (5.26–5.31)
# ---------------------------------------------------------------------------

def constancia_recepcion() -> str:
    """5.26 Constancia de recepción. Query: nomArchivo. Devuelve el PDF en Base64."""
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/constancia/archivo"


def descargar_registro() -> str:
    """
    5.27–5.30 Descargas consolidadas: los cuatro servicios comparten URL.

    Lo único que los distingue es el `codProceso` que se envía. Query:
    perTributario, codOrigenEnvio, codTipoArchivo, codProceso, codLibro.
    """
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/descarga"


def reporte_inconsistencias_periodo(cod_registro_libro: str) -> str:
    """
    5.31 Reporte de inconsistencias del periodo.

    Única excepción del bloque: se dirige por `codRegistroLibro`, un id interno,
    en vez de por periodo.
    """
    return f"{_RVIE}/inconsistencias/web/inconsistencia/{cod_registro_libro}/exporta"


# ---------------------------------------------------------------------------
# Bloque H — Estadísticos y exportadores (5.33–5.35)
# ---------------------------------------------------------------------------

def reporte_estadistico() -> str:
    """
    5.33 Reporte estadístico. Descarga directa.

    `codTipoReporte`: 1 montos por adquiriente, 2 montos por NC-ND.

    El ejemplo del manual escribe el dominio como `api.sire.sunat.gob.pe` en vez
    de `api-sire.sunat.gob.pe`. Se usa el dominio bueno, que es el de todos los
    demás servicios; si fallara en pruebas reales, es el primer sospechoso.
    """
    return f"{_RVIERCE}/estadistica/web/resumenestadistico/exportarvie"


def reporte_cumplimiento(per_tributario: str, cod_libro: str) -> str:
    """5.34 Reporte de cumplimiento. Devuelve archivoPdf en Base64."""
    return (
        f"{_RVIERCE}/cumplimiento/web/omisos/"
        f"{per_tributario}/{cod_libro}/consultaReporteCumplimiento/exportardocumento"
    )


def reporte_exportadores() -> str:
    """
    5.35 Reporte de exportadores. Exclusivo de Ventas.

    Query: codRegistroLibro, perTributario. Devuelve el archivo directamente.
    """
    return f"{_RVIERCE}/gestionlibro/web/exportadores/reporte"


# ---------------------------------------------------------------------------
# Bloque I — Preliminar registrado (5.36–5.37)
# ---------------------------------------------------------------------------

def eliminar_preliminar_registrado(per_tributario: str) -> str:
    """
    5.36 Eliminar el preliminar **ya registrado** (PUT). Query: codLibro.

    Body: `{id, codTipoRegistro: 14}`, donde `id` sale del servicio 5.37.
    """
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/{per_tributario}/eliminapreliminar"


def consultar_preliminares_registrados() -> str:
    """
    5.37 Consultar los preliminares registrados.

    Query: page, perPage, perIni, perFin. Es quien da el `id` que necesita 5.36.
    """
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/consultapreliminaresregistro"
