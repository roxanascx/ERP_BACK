"""
Tests de contrato del cliente SUNAT SIRE.

Cubren las dos cosas que se rompieron en silencio antes: que las URLs dejen de
coincidir con el manual, y que el detalle de un error 422 se pierda por el
camino. No tocan la red: usan `httpx.MockTransport` con respuestas grabadas con
la forma que documenta el manual v22.

Ejecutar:  python -m pytest tests/test_sire_api_client.py -v
"""

import io
import zipfile

import httpx
import pytest

from app.modules.sire.models.auth import SireCredentials
from app.modules.sire.services import sunat_endpoints as ep
from app.modules.sire.services.api_client import (
    DESCRIPCION_ESTADO,
    EstadoTicket,
    SunatApiClient,
)
from app.modules.sire.services.sunat_endpoints import CodLibro, CodTipoResumen
from app.modules.sire.utils.exceptions import (
    SireApiException,
    SireAuthException,
    SunatValidationException,
)

SIRE = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros"
PERIODO = "202607"
TICKET = "20240315000123"


# ---------------------------------------------------------------------------
# 1. El catálogo contra el manual
# ---------------------------------------------------------------------------

# Cada fila sale del "Manual de Servicios Web Api SIRE Compras" v22, sección 5.
# Si SUNAT publica una revisión, este test es el que debe fallar primero.
URLS_DEL_MANUAL = [
    ("5.2  aceptar propuesta",
     ep.aceptar_propuesta(PERIODO),
     f"{SIRE}/rce/propuesta/web/registroslibros/{PERIODO}/aceptarpropuesta"),

    ("5.4  registrar preliminar",
     ep.registrar_preliminar(PERIODO),
     f"{SIRE}/rce/preliminar/web/registroslibros/{PERIODO}/registrapreliminares"),

    ("5.17 eliminar preliminar",
     ep.eliminar_preliminar(PERIODO, "1"),
     f"{SIRE}/rce/preliminar/web/registroslibros/{PERIODO}/1/eliminapreliminar"),

    ("5.31 consultar estado ticket",
     ep.consultar_estado_tickets(),
     f"{SIRE}/rvierce/gestionprocesosmasivos/web/masivo/consultaestadotickets"),

    ("5.32 descargar archivo",
     ep.descargar_archivo_reporte(),
     f"{SIRE}/rvierce/gestionprocesosmasivos/web/masivo/archivoreporte"),

    ("5.33 periodos habilitados",
     ep.periodos_habilitados(CodLibro.RCE),
     f"{SIRE}/rvierce/padron/web/omisos/080000/periodos"),

    ("5.34 descargar propuesta",
     ep.descargar_propuesta(PERIODO),
     f"{SIRE}/rce/propuesta/web/propuesta/{PERIODO}/exportacioncomprobantepropuesta"),

    ("5.35 descargar resumen",
     ep.descargar_resumen(PERIODO, CodTipoResumen.PROPUESTA, "0"),
     f"{SIRE}/rvierce/resumen/web/resumencomprobantes/{PERIODO}/1/0/exporta"),

    ("5.37 descargar excluidos",
     ep.descargar_excluidos(PERIODO),
     f"{SIRE}/rce/propuesta/web/excluidos/{PERIODO}/exportaexcluidos"),

    ("5.40 exportar preliminar",
     ep.exportar_preliminar(PERIODO),
     f"{SIRE}/rce/preliminar/web/registroslibros/{PERIODO}/exportareportepreliminar"),

    ("5.1  token",
     ep.token("abc-123"),
     "https://api-seguridad.sunat.gob.pe/v1/clientessol/abc-123/oauth2/token/"),
]


@pytest.mark.parametrize("servicio,obtenida,esperada", URLS_DEL_MANUAL,
                         ids=[f[0] for f in URLS_DEL_MANUAL])
def test_url_coincide_con_el_manual(servicio, obtenida, esperada):
    assert obtenida == esperada, f"{servicio}: la URL ya no coincide con el manual v22"


def test_codigos_fijos_del_manual():
    """codLibro y codTipoArchivo son los que más se equivocaron a mano."""
    assert CodLibro.RCE == "080000"
    assert CodLibro.RVIE == "140000"
    assert ep.CodOrigenEnvio.SERVICIO_API == "2"
    assert ep.CodTipoArchivo.TXT == "0"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def cliente_con(handler) -> SunatApiClient:
    """Un cliente cuyo transporte responde con `handler`, sin salir a la red."""
    cliente = SunatApiClient()
    cliente.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return cliente


def zip_con(nombre: str, contenido: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(nombre, contenido)
    return buffer.getvalue()


def registro_ticket(cod_estado: str, con_archivo: bool = True) -> dict:
    """Un registro de 5.31 con la forma que documenta el manual."""
    registro = {
        "numTicket": TICKET,
        "codEstadoProceso": cod_estado,
        # SUNAT manda su propia descripcion; se usa la del Anexo III
        "desEstadoProceso": DESCRIPCION_ESTADO[cod_estado],
        "codProceso": "17",
        "perTributario": PERIODO,
        "detalleTicket": {"cantFilas": 3, "cantFilasError": 0},
    }
    if con_archivo and cod_estado == EstadoTicket.TERMINADO:
        # SUNAT escribe esta clave sin la 'r': codTipoAchivoReporte
        registro["archivoReporte"] = [
            {"nomArchivoReporte": "LE20612969125202607.zip", "codTipoAchivoReporte": "00"}
        ]
    return registro


# ---------------------------------------------------------------------------
# 2. Traducción de errores
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_error_422_conserva_la_lista_de_validaciones():
    """El detalle del 422 es lo único que dice qué corregir; no puede perderse."""
    cuerpo = {
        "cod": "422",
        "msg": "Unprocessable Entity - Se presentaron errores de validacion",
        "errors": [
            {"cod": "1001", "msg": 'El campo "numRuc" no enviado o es vacío'},
            {"cod": "1006", "msg": 'El campo "perTributario" debe tener formato yyyymm'},
        ],
    }
    cliente = cliente_con(lambda req: httpx.Response(422, json=cuerpo))

    with pytest.raises(SunatValidationException) as exc:
        await cliente.get_json(ep.descargar_propuesta(PERIODO), "tok")

    error = exc.value
    assert error.status_code == 422
    assert len(error.errors) == 2
    assert error.errors[0]["cod"] == "1001"
    # El __str__ debe llevar los códigos a la vista, no esconderlos
    assert "1001" in str(error) and "1006" in str(error)


@pytest.mark.asyncio
async def test_error_401_es_de_autenticacion():
    cliente = cliente_con(
        lambda req: httpx.Response(401, json={"error_description": "Token expirado"})
    )
    with pytest.raises(SireAuthException, match="Token expirado"):
        await cliente.get_json(ep.descargar_propuesta(PERIODO), "tok")


@pytest.mark.asyncio
async def test_error_500_no_se_reintenta_y_conserva_el_codigo():
    llamadas = []

    def handler(req):
        llamadas.append(req)
        return httpx.Response(500, json={"msg": "Internal Server Error"})

    cliente = cliente_con(handler)
    with pytest.raises(SireApiException) as exc:
        await cliente.get_json(ep.descargar_propuesta(PERIODO), "tok")

    assert exc.value.status_code == 500
    assert len(llamadas) == 1, "un error de SUNAT no debe reintentarse"


# ---------------------------------------------------------------------------
# 3. Autenticación (5.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticate_concatena_ruc_y_usuario_sin_separador():
    """El manual exige username = {RUC}{USUARIO}, sin espacio entre medias."""
    capturado = {}

    def handler(req):
        capturado["url"] = str(req.url)
        capturado["body"] = req.content.decode()
        return httpx.Response(200, json={
            "access_token": "eyJhb.token", "token_type": "Bearer", "expires_in": 3600,
        })

    cliente = cliente_con(handler)
    creds = SireCredentials(
        ruc="20612969125", sunat_usuario="USUARIO1", sunat_clave="clave",
        client_id="cid-1", client_secret="secreto",
    )
    token = await cliente.authenticate(creds)

    assert token.access_token == "eyJhb.token"
    assert "username=20612969125USUARIO1" in capturado["body"]
    assert capturado["url"] == "https://api-seguridad.sunat.gob.pe/v1/clientessol/cid-1/oauth2/token/"
    assert "scope=https%3A%2F%2Fapi-sire.sunat.gob.pe" in capturado["body"]


@pytest.mark.asyncio
async def test_authenticate_con_credenciales_malas():
    cliente = cliente_con(
        lambda req: httpx.Response(400, json={"error_description": "invalid_grant"})
    )
    creds = SireCredentials(
        ruc="20612969125", sunat_usuario="U", sunat_clave="mala",
        client_id="cid", client_secret="sec",
    )
    with pytest.raises(SireAuthException, match="invalid_grant"):
        await cliente.authenticate(creds)


# ---------------------------------------------------------------------------
# 4. El patrón de ticket completo (5.34 → 5.31 → 5.32)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_operacion_con_ticket_de_principio_a_fin():
    """Lanzar, sondear hasta 'Terminado', descargar y descomprimir."""
    contenido = b"20240115|F001|00000123|20100047218|1180.00\n"
    consultas = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)

        if "exportacioncomprobantepropuesta" in url:
            assert req.url.params["codOrigenEnvio"] == "2"
            return httpx.Response(200, json={"numTicket": TICKET})

        if "consultaestadotickets" in url:
            consultas["n"] += 1
            assert req.url.params["numTicket"] == TICKET
            assert req.url.params["codLibro"] == "080000"
            # La primera consulta pilla el proceso aún corriendo
            estado = EstadoTicket.VALIDANDO if consultas["n"] == 1 else EstadoTicket.TERMINADO
            return httpx.Response(200, json={"registros": [registro_ticket(estado)]})

        if "archivoreporte" in url:
            assert req.url.params["nomArchivoReporte"] == "LE20612969125202607.zip"
            assert req.url.params["perTributario"] == PERIODO
            return httpx.Response(200, content=zip_con("LE20612969125202607.txt", contenido))

        raise AssertionError(f"URL inesperada: {url}")

    cliente = cliente_con(handler)
    resultado = await cliente.descargar_propuesta(
        "tok", PERIODO, espera_inicial=0.01, espera_maxima=0.01,
    )

    assert resultado.exitoso
    assert resultado.num_ticket == TICKET
    assert consultas["n"] == 2, "debe sondear hasta que el estado sea terminal"
    assert len(resultado.archivos) == 1
    assert resultado.archivos[0].nombre == "LE20612969125202607.txt"
    assert "20100047218" in resultado.texto


@pytest.mark.asyncio
async def test_operacion_sin_num_ticket_falla_claro():
    cliente = cliente_con(lambda req: httpx.Response(200, json={"mensaje": "ok"}))
    with pytest.raises(SireApiException, match="no devolvió numTicket"):
        await cliente.descargar_propuesta("tok", PERIODO, espera_inicial=0.01)


@pytest.mark.asyncio
async def test_ticket_que_termina_en_error_no_se_da_por_bueno():
    def handler(req):
        if "consultaestadotickets" in str(req.url):
            return httpx.Response(200, json={
                "registros": [registro_ticket(EstadoTicket.PROCESADO_CON_ERRORES)]
            })
        return httpx.Response(200, json={"numTicket": TICKET})

    cliente = cliente_con(handler)
    with pytest.raises(SireApiException, match="estado"):
        await cliente.descargar_propuesta("tok", PERIODO, espera_inicial=0.01)


@pytest.mark.asyncio
async def test_sondeo_se_rinde_y_lo_dice():
    """Si SUNAT nunca termina, hay que fallar con un mensaje accionable."""
    def handler(req):
        if "consultaestadotickets" in str(req.url):
            return httpx.Response(200, json={
                "registros": [registro_ticket(EstadoTicket.VALIDANDO)]
            })
        return httpx.Response(200, json={"numTicket": TICKET})

    cliente = cliente_con(handler)
    with pytest.raises(SireApiException, match="5.31"):
        await cliente.descargar_propuesta(
            "tok", PERIODO, espera_inicial=0.01, espera_maxima=0.01, timeout_total=0.05,
        )


@pytest.mark.asyncio
async def test_aceptar_propuesta_no_descarga_archivo():
    """5.2 devuelve ticket pero no genera archivo: no debe intentar bajarlo."""
    urls = []

    def handler(req):
        urls.append(str(req.url))
        if "consultaestadotickets" in str(req.url):
            return httpx.Response(200, json={
                "registros": [registro_ticket(EstadoTicket.TERMINADO)]
            })
        return httpx.Response(200, json={"numTicket": TICKET})

    cliente = cliente_con(handler)
    resultado = await cliente.aceptar_propuesta("tok", PERIODO, espera_inicial=0.01)

    assert resultado.exitoso
    assert not any("archivoreporte" in u for u in urls)
    assert any("aceptarpropuesta" in u for u in urls)


# ---------------------------------------------------------------------------
# 5. Descompresión
# ---------------------------------------------------------------------------

def test_extraer_archivos_descomprime_el_zip():
    contenido = zip_con("parte1.txt", b"linea A")
    archivos = SunatApiClient._extraer_archivos("reporte.zip", contenido)
    assert [a.nombre for a in archivos] == ["parte1.txt"]
    assert archivos[0].texto == "linea A"


def test_extraer_archivos_deja_pasar_lo_que_no_es_zip():
    archivos = SunatApiClient._extraer_archivos("reporte.txt", b"texto plano")
    assert len(archivos) == 1
    assert archivos[0].texto == "texto plano"


def test_extraer_archivos_con_descarga_vacia():
    assert SunatApiClient._extraer_archivos("x.zip", b"") == []


def test_extraer_archivos_soporta_zip_particionado():
    """Los reportes grandes vienen partidos en varios archivos dentro del zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("parte1.txt", b"A")
        z.writestr("parte2.txt", b"B")
    archivos = SunatApiClient._extraer_archivos("r.zip", buffer.getvalue())
    assert sorted(a.nombre for a in archivos) == ["parte1.txt", "parte2.txt"]


# ---------------------------------------------------------------------------
# 6. Resumen (5.35): descarga directa, sin ticket
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_descargar_resumen_no_pasa_por_ticket():
    urls = []

    def handler(req):
        urls.append(str(req.url))
        assert req.url.params["codLibro"] == "080000"
        return httpx.Response(200, content=b"TOTAL |3|1180.00|180.00\n")

    cliente = cliente_con(handler)
    texto = await cliente.descargar_resumen("tok", PERIODO)

    assert "TOTAL" in texto
    assert len(urls) == 1, "5.35 responde directo; no debe consultar tickets"
    assert "/resumencomprobantes/202607/1/0/exporta" in urls[0]

def test_texto_se_decodifica_como_utf8():
    """
    Las columnas con tilde ("Razón social", "Fecha de emisión") son las que el
    parser busca por nombre. Decodificar en latin-1 no da error: simplemente
    deja esos campos vacíos en pantalla, que es como se coló la primera vez.
    """
    cabecera = "Nro Doc Identidad|Apellidos Nombres/ Razón  Social|Fecha de emisión"
    archivos = SunatApiClient._extraer_archivos("p.txt", cabecera.encode("utf-8"))
    assert archivos[0].texto == cabecera
    assert "Razón" in archivos[0].texto


def test_texto_cae_a_latin1_si_no_es_utf8():
    """Algunos reportes antiguos vienen en latin-1; no deben perderse."""
    archivos = SunatApiClient._extraer_archivos("p.txt", "Razón".encode("latin-1"))
    assert archivos[0].texto == "Razón"

@pytest.mark.asyncio
async def test_estado_04_es_exito_no_fallo():
    """
    «04 Procesado sin errores» es un final correcto (Anexo III del manual de
    Ventas v30). El mapeo heredado lo trataba como error, asi que una operacion
    que habia salido bien se reportaba como fallida.
    """
    def handler(req):
        if "consultaestadotickets" in str(req.url):
            return httpx.Response(200, json={
                "registros": [registro_ticket(EstadoTicket.PROCESADO_SIN_ERRORES, con_archivo=False)]
            })
        return httpx.Response(200, json={"numTicket": TICKET})

    cliente = cliente_con(handler)
    resultado = await cliente.aceptar_propuesta("tok", PERIODO, espera_inicial=0.01)

    assert resultado.cod_estado == "04"
    assert resultado.descripcion == "Procesado sin errores"


def test_estados_terminales_y_fallidos_del_anexo_iii():
    from app.modules.sire.services.api_client import ESTADOS_FALLIDOS, ESTADOS_TERMINALES
    # Se deja de sondear en 03, 04 y 06; solo el 03 es un fallo
    assert ESTADOS_TERMINALES == frozenset({"03", "04", "06"})
    assert ESTADOS_FALLIDOS == frozenset({"03"})
