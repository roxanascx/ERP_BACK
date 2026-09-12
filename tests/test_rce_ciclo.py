"""
Tests del ciclo de vida de un periodo RCE.

Estas son las primeras operaciones del módulo que escriben en SUNAT y no hay
entorno de pruebas, así que lo que más importa comprobar es lo contrario de lo
habitual: que **no** se llame a SUNAT cuando la operación no toca.

Ejecutar:  python -m pytest tests/test_rce_ciclo.py -v
"""

import pytest

from app.modules.sire.models.rce_periodo import (
    EstadoPeriodo,
    PeriodoRce,
    transicion_permitida,
)
from app.modules.sire.services.rce_ciclo_service import RceCicloService
from app.modules.sire.services.api_client import ResultadoTicket
from app.modules.sire.utils.exceptions import (
    SireBusinessException,
    SireValidationException,
    SunatValidationException,
)

RUC = "20612969125"
PERIODO = "202607"


# ---------------------------------------------------------------------------
# Máquina de estados (sin dependencias)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("desde,hasta,permitida", [
    (EstadoPeriodo.PROPUESTA,  EstadoPeriodo.PRELIMINAR, True),   # 5.2
    (EstadoPeriodo.PRELIMINAR, EstadoPeriodo.REGISTRADO, True),   # 5.4
    (EstadoPeriodo.PRELIMINAR, EstadoPeriodo.PROPUESTA,  True),   # 5.17
    (EstadoPeriodo.REGISTRADO, EstadoPeriodo.PROPUESTA,  True),   # 5.17
    # Saltarse el preliminar es justo lo que el manual no permite
    (EstadoPeriodo.PROPUESTA,  EstadoPeriodo.REGISTRADO, False),
    (EstadoPeriodo.REGISTRADO, EstadoPeriodo.PRELIMINAR, False),
    (EstadoPeriodo.PROPUESTA,  EstadoPeriodo.PROPUESTA,  False),
])
def test_transiciones_del_manual(desde, hasta, permitida):
    assert transicion_permitida(desde, hasta) is permitida


def test_operaciones_disponibles_por_estado():
    en_propuesta = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=EstadoPeriodo.PROPUESTA)
    assert en_propuesta.operaciones_disponibles() == ["aceptar la propuesta (5.2)"]

    en_preliminar = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=EstadoPeriodo.PRELIMINAR)
    assert sorted(en_preliminar.operaciones_disponibles()) == [
        "eliminar el preliminar (5.17)",
        "registrar el preliminar (5.4)",
    ]

    registrado = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=EstadoPeriodo.REGISTRADO)
    assert registrado.operaciones_disponibles() == ["eliminar el preliminar (5.17)"]


# ---------------------------------------------------------------------------
# Dobles de prueba
# ---------------------------------------------------------------------------

class RepositorioFalso:
    """Repositorio en memoria con la misma interfaz que el real."""

    def __init__(self, estado=EstadoPeriodo.PROPUESTA):
        self.periodo = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=estado)
        self.transiciones = []

    async def obtener_o_crear(self, ruc, periodo):
        return self.periodo

    async def obtener(self, ruc, periodo):
        return self.periodo

    async def registrar_transicion(self, ruc, periodo, nuevo_estado, operacion,
                                   num_ticket=None, detalle=None):
        self.transiciones.append((nuevo_estado, operacion, num_ticket))
        self.periodo.estado = nuevo_estado
        self.periodo.num_ticket_ultimo = num_ticket or self.periodo.num_ticket_ultimo
        return self.periodo

    async def listar_por_ruc(self, ruc, limite=24):
        return [self.periodo]


class ClienteFalso:
    """Cliente SUNAT que cuenta las llamadas y puede fallar a voluntad."""

    def __init__(self, error=None):
        self.llamadas = []
        self.error = error

    async def aceptar_propuesta(self, token, per_tributario, **kwargs):
        self.llamadas.append(("5.2", per_tributario))
        if self.error:
            raise self.error
        return ResultadoTicket(num_ticket="T-52", cod_estado="06", descripcion="Terminado")

    async def registrar_preliminar(self, token, per_tributario, **kwargs):
        self.llamadas.append(("5.4", per_tributario))
        if self.error:
            raise self.error
        return ResultadoTicket(num_ticket="T-54", cod_estado="06", descripcion="Terminado")

    async def eliminar_preliminar(self, token, per_tributario, ind_eliminar):
        self.llamadas.append(("5.17", per_tributario, ind_eliminar))
        if self.error:
            raise self.error
        return {}

    #: Lo que SUNAT reporta del periodo. Por defecto, abierto.
    periodos_sunat = None
    error_periodos = None

    async def periodos_habilitados(self, token, cod_libro):
        self.llamadas.append(("5.33", cod_libro))
        if self.error_periodos:
            raise self.error_periodos
        return self.periodos_sunat if self.periodos_sunat is not None else [
            {"perTributario": "202607", "codEstado": "03", "desEstado": "No Presentado"},
            {"perTributario": "202606", "codEstado": "03", "desEstado": "No Presentado"},
        ]


class AuthFalso:
    async def obtener_token_valido(self, ruc):
        return "token-de-prueba"


class DbFalsa:
    """Lo mínimo que `RcePeriodoRepository` toca al construirse."""

    def __getitem__(self, nombre):
        return None


def servicio(estado=EstadoPeriodo.PROPUESTA, error=None):
    svc = RceCicloService(
        database=DbFalsa(), api_client=ClienteFalso(error), auth_service=AuthFalso()
    )
    # El repositorio real se cambia por el de memoria: aquí se prueba la lógica
    # del ciclo, no la persistencia.
    svc.periodos = RepositorioFalso(estado)
    return svc


# ---------------------------------------------------------------------------
# Validación del periodo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("periodo", ["2026-07", "20267", "abcdef", "202613", "202600"])
@pytest.mark.asyncio
async def test_periodo_mal_formado_no_llega_a_sunat(periodo):
    svc = servicio()
    with pytest.raises(SireValidationException):
        await svc.aceptar_propuesta(RUC, periodo)
    assert svc.api_client.llamadas == [], "no debe llamarse a SUNAT con un periodo inválido"


# ---------------------------------------------------------------------------
# 5.2 aceptar propuesta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aceptar_propuesta_avanza_a_preliminar():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    resultado = await svc.aceptar_propuesta(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.PRELIMINAR
    assert resultado.num_ticket_ultimo == "T-52"
    # Antes de escribir se pregunta a SUNAT por el estado del periodo (5.33)
    assert [ll[0] for ll in svc.api_client.llamadas] == ["5.33", "5.2"]


@pytest.mark.asyncio
async def test_no_se_acepta_una_propuesta_de_un_periodo_ya_presentado():
    """
    Si SUNAT dice que el periodo ya esta presentado, aceptar la propuesta no
    tiene sentido: se rechaza antes de escribir, con el motivo que da SUNAT.
    """
    svc = servicio(EstadoPeriodo.PROPUESTA)
    svc.api_client.periodos_sunat = [
        {"perTributario": PERIODO, "codEstado": "01", "desEstado": "Presentado"}
    ]

    with pytest.raises(SireBusinessException) as exc:
        await svc.aceptar_propuesta(RUC, PERIODO)

    assert [ll[0] for ll in svc.api_client.llamadas] == ["5.33"], "no debe llegar a escribir"
    assert "Presentado" in str(exc.value)


@pytest.mark.asyncio
async def test_si_sunat_no_contesta_no_se_bloquea_la_operacion():
    """
    No poder preguntar no es motivo para impedir trabajar: el propio servicio
    rechazara la operacion si de verdad no procede.
    """
    from app.modules.sire.utils.exceptions import SireApiException

    svc = servicio(EstadoPeriodo.PROPUESTA)
    svc.api_client.error_periodos = SireApiException("SUNAT no responde")

    resultado = await svc.aceptar_propuesta(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.PRELIMINAR


@pytest.mark.asyncio
async def test_aceptar_dos_veces_no_repite_la_llamada():
    """Un periodo ya en preliminar no vuelve a aceptarse."""
    svc = servicio(EstadoPeriodo.PRELIMINAR)

    with pytest.raises(SireBusinessException) as exc:
        await svc.aceptar_propuesta(RUC, PERIODO)

    assert svc.api_client.llamadas == []
    assert "PRELIMINAR" in str(exc.value)


# ---------------------------------------------------------------------------
# 5.4 registrar preliminar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registrar_preliminar_desde_preliminar():
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    resultado = await svc.registrar_preliminar(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.REGISTRADO
    assert svc.api_client.llamadas == [("5.4", PERIODO)]


@pytest.mark.asyncio
async def test_no_se_puede_registrar_saltandose_el_preliminar():
    """El caso que más caro sale: 5.4 solo se deshace con 5.17."""
    svc = servicio(EstadoPeriodo.PROPUESTA)

    with pytest.raises(SireBusinessException) as exc:
        await svc.registrar_preliminar(RUC, PERIODO)

    assert svc.api_client.llamadas == []
    assert "aceptar la propuesta" in str(exc.value)


@pytest.mark.asyncio
async def test_error_1009_reconcilia_el_estado_en_vez_de_fallar():
    """
    Si alguien registró el periodo desde el portal web, SUNAT responde 1009.
    El estado local estaba desfasado, no equivocada la petición.
    """
    error = SunatValidationException(
        "Unprocessable Entity",
        errors=[{"cod": "1009", "msg": "El registro ya fue generado"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    resultado = await svc.registrar_preliminar(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.REGISTRADO
    assert "ya registrado en SUNAT" in svc.periodos.transiciones[-1][1]


@pytest.mark.asyncio
async def test_error_1008_se_explica_como_conflicto():
    error = SunatValidationException(
        "Unprocessable Entity",
        errors=[{"cod": "1008", "msg": "El registro ya se encuentra en preliminar"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    with pytest.raises(SireBusinessException, match="ya está en preliminar"):
        await svc.registrar_preliminar(RUC, PERIODO)


@pytest.mark.asyncio
async def test_otros_422_se_propagan_tal_cual():
    """Un error de validación normal no debe confundirse con un desfase de estado."""
    error = SunatValidationException(
        "Unprocessable Entity",
        errors=[{"cod": "1006", "msg": "perTributario con formato incorrecto"}],
    )
    svc = servicio(EstadoPeriodo.PRELIMINAR, error=error)

    with pytest.raises(SunatValidationException):
        await svc.registrar_preliminar(RUC, PERIODO)


# ---------------------------------------------------------------------------
# 5.17 eliminar preliminar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eliminar_preliminar_vuelve_a_propuesta():
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    resultado = await svc.eliminar_preliminar(RUC, PERIODO)

    assert resultado.estado == EstadoPeriodo.PROPUESTA
    assert svc.api_client.llamadas == [("5.17", PERIODO, "1")]


@pytest.mark.asyncio
async def test_eliminar_preliminar_de_un_periodo_registrado():
    svc = servicio(EstadoPeriodo.REGISTRADO)
    resultado = await svc.eliminar_preliminar(RUC, PERIODO)
    assert resultado.estado == EstadoPeriodo.PROPUESTA


@pytest.mark.asyncio
async def test_eliminar_sin_preliminar_no_llama_a_sunat():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    with pytest.raises(SireBusinessException, match="no hay preliminar"):
        await svc.eliminar_preliminar(RUC, PERIODO)
    assert svc.api_client.llamadas == []


@pytest.mark.asyncio
async def test_eliminar_solo_no_domiciliados_no_cambia_de_fase():
    svc = servicio(EstadoPeriodo.PRELIMINAR)
    resultado = await svc.eliminar_preliminar(RUC, PERIODO, solo_no_domiciliados=True)

    assert resultado.estado == EstadoPeriodo.PRELIMINAR
    assert svc.api_client.llamadas == [("5.17", PERIODO, "2")]


# ---------------------------------------------------------------------------
# 5.33 periodos habilitados
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_periodos_habilitados_usa_el_libro_de_compras():
    """Se consultaba con 140000, que es el libro de ventas."""
    svc = servicio()
    periodos = await svc.consultar_periodos_habilitados(RUC)

    assert svc.api_client.llamadas == [("5.33", "080000")]
    assert len(periodos) == 2


# ---------------------------------------------------------------------------
# Resumen del periodo: las columnas se localizan por nombre, no por posicion
# ---------------------------------------------------------------------------

CABECERA_COMPRAS = (
    "Tipo de Documento|Total Documentos|BI Gravado DG|IGV / IPM DG|BI Gravado DGNG|"
    "IGV / IPM DGNG|BI Gravado DNG|IGV / IPM DNG|Valor Adq. NG|ISC|ICBPER|"
    "Otros Trib/ Cargos|Total CP"
)

CABECERA_VENTAS = (
    "Tipo de Documento|Total Documentos|Valor facturado la exportacion|"
    "Base imponible de la operación gravada|Dscto. de la Base Imponible|"
    "Monto Total del IGV|Dscto. del IGV|Importe total de la operación exonerada|"
    "Importe total de la operación inafecta|ISC|"
    "Base imponible de la operación gravada con el Impuesto a las Ventas del Arroz Pilado|"
    "Impuesto a las Ventas del Arroz Pilado|ICBPER|Otros Trib/ Cargos|Total CP"
)


def test_resumen_de_compras_lee_el_total():
    from app.modules.sire.utils.resumen import parsear_resumen
    texto = CABECERA_COMPRAS + "\nTOTAL |2|60.09|10.81|0.00|0.00|0.00|0.00|5.30|0.00|0.00|0.00|76.20"
    r = parsear_resumen(texto)
    assert r["total_comprobantes"] == 2
    assert r["total_importe"] == 76.20
    assert r["total_base_imponible"] == 60.09
    assert r["total_igv"] == 10.81


def test_resumen_de_ventas_lee_el_total_pese_a_tener_otras_columnas():
    """
    Ventas trae 15 columnas y Compras 13: «Total CP» pasa de la 12 a la 14.
    Buscar por posicion devolvia 0.00 sin dar ningun error.
    """
    from app.modules.sire.utils.resumen import parsear_resumen
    texto = (
        CABECERA_VENTAS
        + "\n01-Factura|1|0|0.000|0|0.000|0|1800.000|0|0.000|0|0|0.000|0.000|1800.00"
        + "\n03-Boleta de Venta|3|0|0.000|0|0.000|0|1200.000|0|0.000|0|0|0.000|0.000|1200.00"
        + "\nTOTAL |4|0.00|0.00|0.00|0.00|0.00|3000.00|0.00|0.00|0.00|0.00|0.00|0.00|3000.00"
    )
    r = parsear_resumen(texto)
    assert r["total_comprobantes"] == 4
    assert r["total_importe"] == 3000.00
    assert [t["tipo"] for t in r["por_tipo"]] == ["01-Factura", "03-Boleta de Venta"]
    assert [t["importe"] for t in r["por_tipo"]] == [1800.00, 1200.00]


def test_resumen_vacio_no_revienta():
    from app.modules.sire.utils.resumen import parsear_resumen
    r = parsear_resumen("")
    assert r["total_comprobantes"] is None
    assert r["por_tipo"] == []


def test_resumen_sin_la_columna_esperada_devuelve_none_no_cero():
    """None significa «no se pudo saber»; cero seria una mentira."""
    from app.modules.sire.utils.resumen import parsear_resumen
    r = parsear_resumen("Columna A|Columna B\nTOTAL |9")
    assert r["total_importe"] is None
