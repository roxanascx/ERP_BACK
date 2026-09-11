"""
Tests del ciclo de un periodo RVIE (ventas) y del catálogo del manual v30.

Las diferencias con Compras son sutiles y silenciosas —un código de archivo
invertido, una "r" de más en el nombre del recurso, otro codLibro— así que la
mayor parte de estos tests existe para que ninguna de ellas se pierda al copiar
código del lado de compras.

Ejecutar:  python -m pytest tests/test_rvie_ciclo.py -v
"""

import httpx
import pytest

from app.modules.sire.models.rce_periodo import EstadoPeriodo, PeriodoRce
from app.modules.sire.services import sunat_endpoints as ep
from app.modules.sire.services import sunat_endpoints_rvie as ep_rvie
from app.modules.sire.services.api_client import EstadoTicket, ResultadoTicket, SunatApiClient
from app.modules.sire.services.rvie_ciclo_service import RvieCicloService
from app.modules.sire.services.sunat_endpoints import CodLibro, CodTipoArchivo
from app.modules.sire.services.sunat_endpoints_rvie import (
    CodProcesoRvie,
    CodTipoArchivoRvie,
    ErrorNegocioRvie,
)
from app.modules.sire.utils.exceptions import (
    SireApiException,
    SireBusinessException,
    SunatValidationException,
)

LIBROS = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros"
RUC = "20612969125"
PERIODO = "202607"


# ---------------------------------------------------------------------------
# 1. El catálogo contra el manual de Ventas v30
# ---------------------------------------------------------------------------

URLS_DEL_MANUAL = [
    ("5.8  aceptar propuesta",
     ep_rvie.aceptar_propuesta(PERIODO),
     f"{LIBROS}/rvie/propuesta/web/propuesta/{PERIODO}/aceptapropuesta"),

    ("5.9  registrar preliminar",
     ep_rvie.registrar_preliminar(PERIODO),
     f"{LIBROS}/rvierce/gestionlibro/web/registroslibros/{PERIODO}/registrapreliminar"),

    ("5.15 eliminar reemplazo",
     ep_rvie.eliminar_reemplazo(PERIODO),
     f"{LIBROS}/rvierce/gestionlibro/web/registroslibros/{PERIODO}/eliminarreemplazo"),

    ("5.18 descargar propuesta",
     ep_rvie.descargar_propuesta(PERIODO),
     f"{LIBROS}/rvie/propuesta/web/propuesta/{PERIODO}/exportapropuesta"),

    ("5.19 descargar no incluidos",
     ep_rvie.descargar_no_incluidos(PERIODO),
     f"{LIBROS}/rvie/propuesta/web/noincluidos/{PERIODO}/exportanoincluidos"),

    ("5.10 retirar comprobante",
     ep_rvie.retirar_comprobante(PERIODO),
     f"{LIBROS}/rvie/propuesta/web/propuesta/{PERIODO}/retiracomprobante"),

    ("5.36 eliminar preliminar registrado",
     ep_rvie.eliminar_preliminar_registrado(PERIODO),
     f"{LIBROS}/rvierce/gestionlibro/web/registroslibros/{PERIODO}/eliminapreliminar"),

    ("5.37 consultar preliminares",
     ep_rvie.consultar_preliminares_registrados(),
     f"{LIBROS}/rvierce/gestionlibro/web/registroslibros/consultapreliminaresregistro"),

    ("5.35 reporte exportadores",
     ep_rvie.reporte_exportadores(),
     f"{LIBROS}/rvierce/gestionlibro/web/exportadores/reporte"),
]


@pytest.mark.parametrize("servicio,obtenida,esperada", URLS_DEL_MANUAL,
                         ids=[f[0] for f in URLS_DEL_MANUAL])
def test_url_coincide_con_el_manual_v30(servicio, obtenida, esperada):
    assert obtenida == esperada, f"{servicio}: la URL ya no coincide con el manual de Ventas v30"


def test_aceptar_propuesta_no_lleva_la_erre_de_compras():
    """
    Compras usa `aceptarpropuesta` y Ventas `aceptapropuesta`. Copiar la de
    Compras da un 404 que parece un problema de permisos.
    """
    url = ep_rvie.aceptar_propuesta(PERIODO)
    assert url.endswith("/aceptapropuesta")
    assert "aceptarpropuesta" not in url
    # Y cuelga de rvie/, no de rvierce/
    assert "/libros/rvie/propuesta/" in url


def test_cod_tipo_archivo_esta_invertido_respecto_a_compras():
    """
    Anexo IV: en Ventas 1 es excel y 2 csv; en Compras es al revés. Usar la
    clase equivocada no da error, solo devuelve otro formato.
    """
    assert CodTipoArchivoRvie.EXCEL == "1"
    assert CodTipoArchivoRvie.CSV == "2"
    assert CodTipoArchivo.CSV == "1"
    assert CodTipoArchivo.EXCEL == "2"
    assert CodTipoArchivoRvie.TXT == CodTipoArchivo.TXT == "0"


def test_cod_proceso_del_reemplazo_es_3_no_61():
    """En Compras el reemplazo de propuesta es 61; en Ventas es 3."""
    from app.modules.sire.services.sunat_endpoints import CodProceso
    assert CodProcesoRvie.REEMPLAZO_PROPUESTA == "3"
    assert CodProceso.REEMPLAZO_PROPUESTA == "61"


def test_cod_libro_de_ventas():
    assert CodLibro.RVIE == "140000"


# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------

class RepositorioFalso:
    def __init__(self, estado):
        self.periodo = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=estado)
        self.transiciones = []

    async def obtener_o_crear(self, ruc, periodo):
        return self.periodo

    async def obtener(self, ruc, periodo):
        return self.periodo

    async def registrar_transicion(self, ruc, periodo, nuevo_estado, operacion,
                                   num_ticket=None, detalle=None):
        self.transiciones.append((nuevo_estado, operacion))
        self.periodo.estado = nuevo_estado
        return self.periodo

    async def listar_por_ruc(self, ruc, limite=24):
        return [self.periodo]


class ClienteFalso:
    def __init__(self, error=None, registros=None):
        self.llamadas = []
        self.error = error
        self.registros = registros if registros is not None else []

    async def rvie_aceptar_propuesta(self, token, per_tributario, **kw):
        self.llamadas.append(("5.8", per_tributario))
        if self.error:
            raise self.error
        return ResultadoTicket(num_ticket="T-58", cod_estado=EstadoTicket.TERMINADO)

    async def rvie_registrar_preliminar(self, token, per_tributario, **kw):
        self.llamadas.append(("5.9", per_tributario))
        if self.error:
            raise self.error
        return ResultadoTicket(num_ticket="", cod_estado=EstadoTicket.TERMINADO)

    async def rvie_eliminar_reemplazo(self, token, per_tributario, **kw):
        self.llamadas.append(("5.15", per_tributario))
        if self.error:
            raise self.error
        return ResultadoTicket(num_ticket="", cod_estado=EstadoTicket.TERMINADO)

    #: Lo que SUNAT reporta del periodo. Por defecto, abierto.
    periodos_sunat = None

    async def rvie_periodos_habilitados(self, token):
        self.llamadas.append(("5.2", None))
        return self.periodos_sunat if self.periodos_sunat is not None else [
            {"numEjercicio": "2026", "lisPeriodos": [
                {"perTributario": PERIODO, "codEstado": "03", "desEstado": "No Presentado"}
            ]}
        ]

    async def get_json(self, url, token, params=None):
        self.llamadas.append(("5.37", params))
        return {"registros": self.registros}

    async def put_json(self, url, token, data=None, params=None):
        self.llamadas.append(("5.36", data))
        return {}


class AuthFalso:
    async def obtener_token_valido(self, ruc):
        return "tok"


class DbFalsa:
    def __getitem__(self, nombre):
        return None


def servicio(estado=EstadoPeriodo.PROPUESTA, error=None, registros=None):
    svc = RvieCicloService(DbFalsa(), ClienteFalso(error, registros), AuthFalso())
    svc.periodos = RepositorioFalso(estado)
    return svc


# ---------------------------------------------------------------------------
# 2. Avance del ciclo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aceptar_propuesta_avanza_a_preliminar():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    resultado = await svc.aceptar_propuesta(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.PRELIMINAR
    # Antes de escribir se pregunta a SUNAT por el estado del periodo (5.2)
    assert [ll[0] for ll in svc.api_client.llamadas] == ["5.2", "5.8"]


@pytest.mark.asyncio
async def test_no_se_acepta_una_propuesta_de_un_periodo_ya_presentado():
    """Mismo criterio que en compras: SUNAT manda sobre el estado local."""
    svc = servicio(EstadoPeriodo.PROPUESTA)
    svc.api_client.periodos_sunat = [
        {"perTributario": PERIODO, "codEstado": "01", "desEstado": "Presentado"}
    ]

    with pytest.raises(SireBusinessException) as exc:
        await svc.aceptar_propuesta(RUC, PERIODO)

    assert [ll[0] for ll in svc.api_client.llamadas] == ["5.2"], "no debe llegar a escribir"
    assert "Presentado" in str(exc.value)


@pytest.mark.asyncio
async def test_registrar_preliminar_sin_ticket_es_exito():
    """El 5.9 puede responder sin numTicket: significa que terminó bien."""
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    resultado = await svc.registrar_preliminar(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.REGISTRADO


@pytest.mark.asyncio
async def test_no_se_puede_registrar_desde_propuesta():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    with pytest.raises(SireBusinessException):
        await svc.registrar_preliminar(RUC, PERIODO)
    assert svc.api_client.llamadas == []


@pytest.mark.parametrize("codigo", [
    ErrorNegocioRvie.YA_EN_PRELIMINAR_REGISTRADO,   # 2294
    ErrorNegocioRvie.YA_GENERADO_DESDE_PORTAL,      # 2295
])
@pytest.mark.asyncio
async def test_2294_y_2295_reconcilian_el_estado(codigo):
    """SUNAT va por delante: el estado local estaba desfasado, no la petición."""
    error = SunatValidationException("Rechazado", errors=[{"cod": codigo, "msg": "ya registrado"}])
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    resultado = await svc.registrar_preliminar(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.REGISTRADO
    assert "ya registrado en SUNAT" in svc.periodos.transiciones[-1][1]


@pytest.mark.asyncio
async def test_2293_dice_que_falta_aceptar_la_propuesta():
    error = SunatValidationException(
        "Rechazado",
        errors=[{"cod": ErrorNegocioRvie.AUN_EN_PROPUESTA, "msg": "está en etapa propuesta"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    with pytest.raises(SireBusinessException, match="sigue en propuesta"):
        await svc.registrar_preliminar(RUC, PERIODO)


# ---------------------------------------------------------------------------
# 3. Las dos marchas atrás, que Ventas separa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_5_15_devuelve_el_periodo_a_propuesta():
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    resultado = await svc.eliminar_preliminar(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.PROPUESTA
    assert svc.api_client.llamadas == [("5.15", PERIODO)]


@pytest.mark.asyncio
async def test_sobre_un_periodo_registrado_el_5_15_remite_al_5_36():
    """Es el error que más tiempo haría perder si solo dijera «no se puede»."""
    svc = servicio(EstadoPeriodo.REGISTRADO)

    with pytest.raises(SireBusinessException, match="5.36"):
        await svc.eliminar_preliminar(RUC, PERIODO)

    assert svc.api_client.llamadas == []


@pytest.mark.asyncio
async def test_2299_tambien_remite_al_5_36():
    """Si es SUNAT quien lo detecta, el mensaje debe llevar al mismo sitio."""
    error = SunatValidationException(
        "Rechazado",
        errors=[{"cod": ErrorNegocioRvie.EN_PRELIMINAR_REGISTRADO, "msg": "preliminar registrado"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    with pytest.raises(SireBusinessException, match="5.36"):
        await svc.eliminar_preliminar(RUC, PERIODO)


@pytest.mark.asyncio
async def test_2298_reconcilia_a_propuesta():
    error = SunatValidationException(
        "Rechazado",
        errors=[{"cod": ErrorNegocioRvie.SIN_REEMPLAZO_QUE_ELIMINAR, "msg": "sigue en propuesta"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    resultado = await svc.eliminar_preliminar(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.PROPUESTA


@pytest.mark.asyncio
async def test_5_36_compone_la_consulta_5_37_para_obtener_el_id():
    svc = servicio(
        EstadoPeriodo.REGISTRADO,
        registros=[{"perTributario": PERIODO, "id": "6463788755ff7605f43b6a0a"}],
    )

    resultado = await svc.eliminar_preliminar_registrado(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.PROPUESTA
    servicios = [ll[0] for ll in svc.api_client.llamadas]
    assert servicios == ["5.37", "5.36"], "hay que consultar el id antes de eliminar"
    # El body del 5.36 lleva el id que dio el 5.37 y el tipo de registro fijo
    cuerpo = svc.api_client.llamadas[-1][1]
    assert cuerpo == {"id": "6463788755ff7605f43b6a0a", "codTipoRegistro": 14}


@pytest.mark.asyncio
async def test_5_36_sin_id_no_intenta_eliminar_a_ciegas():
    svc = servicio(EstadoPeriodo.REGISTRADO, registros=[])

    with pytest.raises(SireApiException, match="5.37"):
        await svc.eliminar_preliminar_registrado(RUC, PERIODO)

    assert [ll[0] for ll in svc.api_client.llamadas] == ["5.37"]


@pytest.mark.asyncio
async def test_5_36_sobre_un_periodo_no_registrado():
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    with pytest.raises(SireBusinessException, match="5.15"):
        await svc.eliminar_preliminar_registrado(RUC, PERIODO)


# ---------------------------------------------------------------------------
# 4. El cliente: ticket opcional y libro correcto
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_operacion_sin_ticket_no_falla_si_es_opcional():
    """5.9 y 5.15 responden vacío cuando terminan de forma síncrona."""
    def handler(req):
        return httpx.Response(200, json={})

    cliente = SunatApiClient()
    cliente.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    resultado = await cliente.rvie_registrar_preliminar("tok", PERIODO, espera_inicial=0.01)

    assert resultado.cod_estado == EstadoTicket.TERMINADO
    assert resultado.num_ticket == ""


@pytest.mark.asyncio
async def test_las_llamadas_de_ventas_usan_el_libro_140000():
    urls = []

    def handler(req):
        urls.append(req.url)
        if "consultaestadotickets" in str(req.url):
            return httpx.Response(200, json={"registros": [
                {"numTicket": "T-1", "codEstadoProceso": EstadoTicket.TERMINADO}
            ]})
        return httpx.Response(200, json={"numTicket": "T-1"})

    cliente = SunatApiClient()
    cliente.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await cliente.rvie_aceptar_propuesta("tok", PERIODO, espera_inicial=0.01)

    consulta = next(u for u in urls if "consultaestadotickets" in str(u))
    assert consulta.params["codLibro"] == "140000"


@pytest.mark.asyncio
async def test_periodos_habilitados_de_ventas_usa_su_libro():
    urls = []

    def handler(req):
        urls.append(str(req.url))
        return httpx.Response(200, json=[])

    cliente = SunatApiClient()
    cliente.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    await cliente.rvie_periodos_habilitados("tok")

    assert urls[0] == ep.periodos_habilitados(CodLibro.RVIE)
    assert "/omisos/140000/periodos" in urls[0]
