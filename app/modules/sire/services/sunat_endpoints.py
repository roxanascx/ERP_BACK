"""
Catálogo de servicios Web API de SUNAT SIRE — Compras (RCE).

Fuente única de verdad para URLs y códigos. Cada función lleva el número de
servicio del "Manual de Servicios Web Api SIRE Compras" v22 (SUNAT/CANVIA,
05/03/2024) para que cualquiera pueda contrastarla contra el documento.

Antes de este módulo las URLs estaban repartidas entre un diccionario de
`api_client.py` que nadie usaba (y cuyas rutas no coincidían con el manual) y
copias literales dentro de las rutas: `consultaestadotickets` aparecía en cinco
archivos y `exportacioncomprobantepropuesta` en cuatro. Aquí viven una sola vez.

Convenciones del manual que se repiten en casi todos los servicios:
  - `perTributario` siempre en formato `yyyymm`.
  - `codLibro` es `080000` para RCE y `140000` para RVIE.
  - `codOrigenEnvio` vale `2` cuando la operación entra por el API (en v22 este
    parámetro cambió de 1 a 2 en varios servicios).
  - Las operaciones asíncronas devuelven `numTicket`; el resultado se recoge
    con 5.31 (estado) y 5.32 (descarga). Ver `SunatApiClient.ejecutar_operacion_con_ticket`.
"""

from typing import Final

# ---------------------------------------------------------------------------
# Dominios base
# ---------------------------------------------------------------------------

API_SEGURIDAD: Final = "https://api-seguridad.sunat.gob.pe/v1"
API_SIRE: Final = "https://api-sire.sunat.gob.pe/v1"

# Raíz común de los servicios de libros. El manual alterna dos espacios:
# `rce/...` para lo específico de Compras y `rvierce/...` para lo compartido
# entre Compras y Ventas (tickets, resúmenes, padrón, estadísticas).
_LIBROS: Final = f"{API_SIRE}/contribuyente/migeigv/libros"
_RCE: Final = f"{_LIBROS}/rce"
_RVIERCE: Final = f"{_LIBROS}/rvierce"


# ---------------------------------------------------------------------------
# Códigos (Anexos I, II y III del manual)
# ---------------------------------------------------------------------------

class CodLibro:
    """Libro electrónico sobre el que opera el servicio."""
    RCE: Final = "080000"   # Registro de Compras Electrónico
    RVIE: Final = "140000"  # Registro de Ventas e Ingresos Electrónico


class CodOrigenEnvio:
    """Origen de la operación. El API siempre se identifica con 2."""
    PORTAL_WEB: Final = "1"
    SERVICIO_API: Final = "2"


class CodTipoArchivo:
    """Anexo III — extensión del archivo a descargar."""
    TXT: Final = "0"
    CSV: Final = "1"
    EXCEL: Final = "2"


#: SUNAT lo devuelve en un 422 cuando el periodo no tiene comprobantes. No es
#: un fallo: significa que todavia no hay propuesta que aceptar.
COD_SIN_COMPROBANTES = "1070"


class CodTipoResumen:
    """Tipos de resumen aceptados por el servicio 5.35."""
    PROPUESTA: Final = "1"
    PRELIMINAR: Final = "2"
    INCLUIDOS_EXCLUIDOS: Final = "3"
    REGISTRO: Final = "4"
    PRELIMINAR_REGISTRADO: Final = "5"
    AJUSTES_POSTERIORES: Final = "6"
    NO_DOMICILIADOS: Final = "7"


class CodProceso:
    """
    Anexo I — código de proceso de las cargas masivas (servicios TUS).

    Se usan en la metadata de subida; el endpoint destino apenas cambia, lo que
    distingue una operación de otra es este código. Pendientes de la Fase 03.
    """
    IMPORTAR_CP_PROPUESTA: Final = "1"        # 5.9
    IMPORTAR_CP_PRELIMINAR: Final = "4"       # 5.7
    CARGAR_AJUSTES_POSTERIORES: Final = "6"   # 5.18 y 5.24
    COMPLEMENTAR_PROPUESTA: Final = "54"      # 5.6
    INCLUIR_EXCLUIR: Final = "55"             # 5.8
    CARGAR_NO_DOMICILIADOS: Final = "56"      # 5.5
    AJUSTES_NO_DOMICILIADOS: Final = "60"     # 5.21 y 5.27
    REEMPLAZO_PROPUESTA: Final = "61"         # 5.3


class IndEliminarPreliminar:
    """Alcance del servicio 5.17."""
    TODO: Final = "1"
    SOLO_NO_DOMICILIADOS: Final = "2"


class IndTipoAjustePosterior:
    """Anexo II — tipo de ajuste posterior."""
    AJUSTE: Final = "1"
    AJUSTE_NO_DOMICILIADOS: Final = "2"
    PERIODOS_ANTERIORES_GENERAL: Final = "3"
    PERIODOS_ANTERIORES_SIMPLIFICADO: Final = "4"
    PERIODOS_ANTERIORES_NO_DOMICILIADOS: Final = "5"


# ---------------------------------------------------------------------------
# Bloque A — Seguridad y flujo principal (5.1–5.4)
# ---------------------------------------------------------------------------

def token(client_id: str) -> str:
    """5.1 Api Seguridad — obtiene el token Bearer."""
    return f"{API_SEGURIDAD}/clientessol/{client_id}/oauth2/token/"


def aceptar_propuesta(per_tributario: str) -> str:
    """5.2 Aceptar propuesta — pasa el libro a preliminar. Devuelve numTicket."""
    return f"{_RCE}/propuesta/web/registroslibros/{per_tributario}/aceptarpropuesta"


def registrar_preliminar(per_tributario: str) -> str:
    """5.4 Registrar preliminar — paso final antes de la generación."""
    return f"{_RCE}/preliminar/web/registroslibros/{per_tributario}/registrapreliminares"


# ---------------------------------------------------------------------------
# Bloque B — Cargas TUS (5.3, 5.5–5.9). Pendientes de la Fase 03.
# ---------------------------------------------------------------------------

#: Destino de las cargas que afectan a la propuesta (5.3, 5.6, 5.8, 5.9).
UPLOAD_PROPUESTA: Final = f"{_RVIERCE}/receptorpropuesta/web/propuesta/upload"

#: Destino de las cargas que afectan al preliminar (5.5, 5.7).
UPLOAD_PRELIMINAR: Final = f"{_RVIERCE}/receptorpreliminar/web/preliminar/upload"

#: Destino de las cargas de ajustes posteriores (5.18, 5.21, 5.24, 5.27).
UPLOAD_AJUSTES_POSTERIORES: Final = (
    f"{_RVIERCE}/receptorajustesposteriores/web/ajustesposteriores/upload"
)


# ---------------------------------------------------------------------------
# Bloque D — Eliminación de comprobantes y del preliminar (5.15–5.17)
# ---------------------------------------------------------------------------

def eliminar_comprobante_propuesta(per_tributario: str) -> str:
    """5.15 Eliminar comprobante de la propuesta (DELETE)."""
    return f"{_RCE}/propuesta/web/propuestarce/{per_tributario}"


def eliminar_comprobante_preliminar(per_tributario: str) -> str:
    """5.16 Eliminar comprobante del preliminar (POST)."""
    return (
        f"{_RCE}/preliminar/web/comprobanteslibroscompras/"
        f"{per_tributario}/eliminacomprobante"
    )


def eliminar_preliminar(per_tributario: str, ind_eliminar: str) -> str:
    """5.17 Eliminar preliminar (PUT). Marcha atrás del 5.4."""
    return (
        f"{_RCE}/preliminar/web/registroslibros/"
        f"{per_tributario}/{ind_eliminar}/eliminapreliminar"
    )


# ---------------------------------------------------------------------------
# Bloque F — Tickets y descarga de archivos (5.31–5.32)
# ---------------------------------------------------------------------------

def consultar_estado_tickets() -> str:
    """
    5.31 Consultar estado de ticket.

    Parámetros de query: perIni, perFin, page, perPage, numTicket, codLibro.
    """
    return f"{_RVIERCE}/gestionprocesosmasivos/web/masivo/consultaestadotickets"


def descargar_archivo_reporte() -> str:
    """
    5.32 Descargar archivo generado.

    Parámetros de query: nomArchivoReporte y codTipoArchivoReporte, ambos
    tomados de la salida del 5.31.
    """
    return f"{_RVIERCE}/gestionprocesosmasivos/web/masivo/archivoreporte"


# ---------------------------------------------------------------------------
# Bloque G — Consultas y descargas (5.33–5.40)
# ---------------------------------------------------------------------------

def periodos_habilitados(cod_libro: str) -> str:
    """5.33 Consultar año y mes: periodos habilitados para el contribuyente."""
    return f"{_RVIERCE}/padron/web/omisos/{cod_libro}/periodos"


def descargar_propuesta(per_tributario: str) -> str:
    """
    5.34 Descargar propuesta. Devuelve numTicket.

    Query: codTipoArchivo, codOrigenEnvio y filtros opcionales (fecEmisionIni,
    fecEmisionFin, codTipoCDP, numSerieCDP, numCDP, codInconsistencia, codCar,
    numDocAdquiriente, mtoDesde, mtoHasta).
    """
    return (
        f"{_RCE}/propuesta/web/propuesta/"
        f"{per_tributario}/exportacioncomprobantepropuesta"
    )


def descargar_resumen(per_tributario: str, cod_tipo_resumen: str, cod_tipo_archivo: str) -> str:
    """5.35 Descargar resumen. Query: codLibro. Ver `CodTipoResumen`."""
    return (
        f"{_RVIERCE}/resumen/web/resumencomprobantes/"
        f"{per_tributario}/{cod_tipo_resumen}/{cod_tipo_archivo}/exporta"
    )


def resumen_inconsistencias(per_tributario: str) -> str:
    """5.36 Descargar resumen de inconsistencias (POST). Query: codTipoResumen, codLibro."""
    return f"{_RVIERCE}/resumen/web/resumeninconsistencias/{per_tributario}"


def descargar_excluidos(per_tributario: str) -> str:
    """5.37 Descargar comprobantes excluidos del periodo. Devuelve numTicket."""
    return f"{_RCE}/propuesta/web/excluidos/{per_tributario}/exportaexcluidos"


def eliminar_comprobante_no_domiciliado(per_tributario: str) -> str:
    """5.38 Eliminar comprobante no domiciliado del preliminar (PUT)."""
    return (
        f"{_RCE}/libronodomiciliado/web/nodomiciliados/"
        f"{per_tributario}/eliminarcomprobantepreliminarnd"
    )


def exportar_preliminar_no_domiciliados(per_tributario: str) -> str:
    """5.39 Exportar preliminar de compras no domiciliados. Devuelve numTicket."""
    return f"{_RCE}/preliminar/web/nodomiciliados/{per_tributario}/exportapreliminarnd"


def exportar_preliminar(per_tributario: str) -> str:
    """5.40 Exportar preliminar del registro de compras. Devuelve numTicket."""
    return (
        f"{_RCE}/preliminar/web/registroslibros/"
        f"{per_tributario}/exportareportepreliminar"
    )


# ---------------------------------------------------------------------------
# Bloque H — Casillas e inconsistencias (5.41–5.44)
# ---------------------------------------------------------------------------

def reporte_casillas(per_tributario: str, tipo_reporte: str, tipo_descarga: str) -> str:
    """
    5.41 Reporte de casillas. `tipo_reporte`: 1 Preliminar, 2 Comparada.

    Descarga directa: devuelve el binario, sin pasar por ticket.
    """
    return (
        f"{_RVIERCE}/casillas/e/casillaspropuestas/"
        f"{per_tributario}/reporte/{tipo_reporte}/{tipo_descarga}"
    )


def inconsistencias_preliminar_registrado(per_tributario: str, cod_tipo_archivo: str) -> str:
    """5.42 Inconsistencias del preliminar registrado. Descarga directa. Query: cntlimite."""
    return (
        f"{_RVIERCE}/casillas/inconsistenciaslibros/"
        f"{per_tributario}/reporteinconsistencia/{cod_tipo_archivo}"
    )


def inconsistencias_por_totales(per_tributario: str) -> str:
    """5.43 Inconsistencias por montos totales. Query: codTipoArchivo, codLibro."""
    return (
        f"{_RCE}/inconsistencias/web/periodoinconsistencias/"
        f"{per_tributario}/exportarinconsistenciasportotales"
    )


def inconsistencias_por_comprobante(per_tributario: str, cod_libro: str) -> str:
    """5.44 Inconsistencias por comprobante de pago. Devuelve numTicket."""
    return (
        f"{_RCE}/inconsistencias/web/periodoinconsistencias/"
        f"{per_tributario}/{cod_libro}/exportarinconsistenciasporcomprobantes"
    )


# ---------------------------------------------------------------------------
# Bloque I — Constancias y reportes (5.49, 5.52–5.58)
# ---------------------------------------------------------------------------

def constancia_recepcion() -> str:
    """5.49 Constancia de recepción. Query: nomConstanciaRecepcion. Devuelve PDF en bytes."""
    return f"{_RVIERCE}/gestionlibro/web/registroslibros/constancia/constanciarecepcion"


def reporte_descarga_periodo(per_tributario: str) -> str:
    """
    5.50 / 5.51 Reporte consolidado y descarga del RCE por periodo.

    Query: codTipoArchivo, codMoneda, codProceso, codOrigen, lisPeriodos.
    """
    return (
        f"{_RCE}/ajustesposteriores/web/ajustesposteriores/"
        f"{per_tributario}/solicitardescarga"
    )


def reporte_inconsistencias_periodo() -> str:
    """5.52 Reporte de inconsistencias por periodo. Query: nomArchivo, codTipoArchivoReporte, codOrigen."""
    return f"{_RVIERCE}/gestionconsultas/web/registrolibro/archivoreporte"


def reporte_car(per_tributario: str) -> str:
    """5.53 Reporte CAR por periodo y fase. Query: codOrigenEnvio, codLibro, codFase."""
    return f"{_RVIERCE}/gestionlibro/web/comprobanteslibros/{per_tributario}/reportecar"


def reporte_estadistico() -> str:
    """
    5.54–5.57 Reportes estadísticos. Descarga directa, sin ticket.

    Comparten URL y se distinguen por `codTipoReporte`: 1 compras por proveedor,
    2 notas de crédito/débito por proveedor, 3 compras por día, 4 compras por CIIU.
    Query: numRuc, perTributario, fechaini, fechafin, numRucproveedor, codTipoCDP,
    codTipoArchivo, codTipoReporte, codLibro.
    """
    return f"{_RVIERCE}/estadistica/web/resumenestadistico/exporta"


def reporte_cumplimiento(per_tributario: str, cod_libro: str) -> str:
    """5.58 Reporte de cumplimiento. Devuelve archivoPdf en Base64."""
    return (
        f"{_RVIERCE}/cumplimiento/web/omisos/"
        f"{per_tributario}/{cod_libro}/consultaReporteCumplimiento/exportardocumento"
    )
