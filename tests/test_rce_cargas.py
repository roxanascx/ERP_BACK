"""
Tests de las cargas de archivos al RCE (5.3, 5.5–5.9).

No hay forma de probar esto contra SUNAT sin subir un archivo de verdad, así que
la red de seguridad son estos tests contra un servidor tus.io simulado que sigue
el protocolo: POST crea, PATCH envía trozos, y ambos pueden fallar con un 422.

Lo que más importa comprobar es que un 422 durante la carga llegue con su lista
de errores intacta: recuperar ese cuerpo es la única razón por la que el manual
exigía escribir estos servicios en Java.

Ejecutar:  python -m pytest tests/test_rce_cargas.py -v
"""

import io
import zipfile

import httpx
import pytest

from app.modules.sire.models.rce_periodo import EstadoPeriodo, PeriodoRce
from app.modules.sire.services import sunat_endpoints as ep
from app.modules.sire.services.api_client import SunatApiClient
from app.modules.sire.services.rce_carga_service import OPERACIONES, RceCargaService
from app.modules.sire.services.tus_uploader import (
    codificar_metadata,
    comprimir_txt,
)
from app.modules.sire.utils.exceptions import (
    SireApiException,
    SireBusinessException,
    SireValidationException,
    SunatValidationException,
)

RUC = "20612969125"
PERIODO = "202607"
TXT = b"20240115|F001|00000123|20100047218|1180.00\n"


# ---------------------------------------------------------------------------
# 1. Metadata y compresión
# ---------------------------------------------------------------------------

def test_metadata_se_codifica_en_base64_segun_el_protocolo():
    """El formato de `Upload-Metadata` es `clave <base64>` separado por comas."""
    cabecera = codificar_metadata({"filename": "a.zip", "numRuc": RUC})
    assert cabecera == "filename YS56aXA=,numRuc MjA2MTI5NjkxMjU="


def test_metadata_omite_los_nulos_y_deja_las_claves_vacias():
    cabecera = codificar_metadata({"a": "1", "b": None, "c": ""})
    assert cabecera == "a MQ==,c"


def test_metadata_de_carga_lleva_los_nueve_campos_del_manual():
    meta = SunatApiClient.metadata_carga(RUC, PERIODO, "61", "archivo.zip")
    assert set(meta) == {
        "filename", "filetype", "numRuc", "perTributario", "codOrigenEnvio",
        "codProceso", "codTipoCorrelativo", "nomArchivoImportacion", "codLibro",
    }
    assert meta["codOrigenEnvio"] == "2"       # el API se identifica con 2
    assert meta["codTipoCorrelativo"] == "01"
    assert meta["codLibro"] == "080000"        # RCE


def test_comprimir_txt_produce_un_zip_legible():
    contenido = comprimir_txt("datos.txt", TXT)
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        assert z.namelist() == ["datos.txt"]
        assert z.read("datos.txt") == TXT


# ---------------------------------------------------------------------------
# Servidor tus.io simulado
# ---------------------------------------------------------------------------

class ServidorTusFalso:
    """
    Implementa lo justo del protocolo para poder probar el cliente.

    `fallo_en` permite hacer que reviente en la creación o en un PATCH concreto.
    """

    def __init__(self, location="/upload/abc123", fallo_en=None, respuesta_final=None,
                 omitir_offset=False):
        self.location = location
        self.fallo_en = fallo_en or {}
        self.respuesta_final = respuesta_final if respuesta_final is not None else {"numTicket": "T-903"}
        self.omitir_offset = omitir_offset
        self.recibido = b""
        self.peticiones = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.peticiones.append(req)

        if req.method == "POST":
            if "crear" in self.fallo_en:
                return self.fallo_en["crear"]
            assert req.headers["Tus-Resumable"] == "1.0.0"
            assert int(req.headers["Upload-Length"]) > 0
            assert "Upload-Metadata" in req.headers
            cabeceras = {} if self.location is None else {"Location": self.location}
            return httpx.Response(201, headers=cabeceras)

        if req.method == "PATCH":
            n = len([p for p in self.peticiones if p.method == "PATCH"])
            if f"patch{n}" in self.fallo_en:
                return self.fallo_en[f"patch{n}"]

            assert req.headers["Content-Type"] == "application/offset+octet-stream"
            assert int(req.headers["Upload-Offset"]) == len(self.recibido)

            self.recibido += req.content
            if self.omitir_offset:
                return httpx.Response(204)
            return httpx.Response(
                204,
                headers={"Upload-Offset": str(len(self.recibido))},
                json=self.respuesta_final,
            )

        if req.method == "HEAD":
            return httpx.Response(200, headers={"Upload-Offset": str(len(self.recibido))})

        raise AssertionError(f"Método inesperado: {req.method}")


def cliente_con(servidor) -> SunatApiClient:
    cliente = SunatApiClient()
    cliente.client = httpx.AsyncClient(transport=httpx.MockTransport(servidor))
    return cliente


# ---------------------------------------------------------------------------
# 2. Carga completa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_carga_completa_devuelve_el_ticket():
    servidor = ServidorTusFalso()
    cliente = cliente_con(servidor)

    resultado = await cliente.subir_archivo(
        "tok", ep.UPLOAD_PROPUESTA,
        ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
        nombre_archivo="propuesta.txt", contenido=TXT,
    )

    assert resultado.num_ticket == "T-903"
    metodos = [p.method for p in servidor.peticiones]
    assert metodos == ["POST", "PATCH"]

    # Lo que llega a SUNAT es el zip, no el txt suelto
    with zipfile.ZipFile(io.BytesIO(servidor.recibido)) as z:
        assert z.read("propuesta.txt") == TXT


@pytest.mark.asyncio
async def test_archivo_grande_se_envia_por_trozos_y_en_orden():
    servidor = ServidorTusFalso()
    cliente = cliente_con(servidor)

    # Un zip de contenido aleatorio no comprime, así que el tamaño se conserva
    import os
    grande = os.urandom(300 * 1024)

    from app.modules.sire.services.tus_uploader import TusUploader
    uploader = TusUploader(cliente.client, cliente._levantar_error_sunat, tamano_trozo=100 * 1024)
    resultado = await uploader.subir(ep.UPLOAD_PROPUESTA, "tok", grande, {"filename": "g.zip"})

    patches = [p for p in servidor.peticiones if p.method == "PATCH"]
    assert len(patches) == 3
    assert [int(p.headers["Upload-Offset"]) for p in patches] == [0, 102400, 204800]
    assert servidor.recibido == grande
    assert resultado.bytes_enviados == len(grande)


@pytest.mark.asyncio
async def test_location_relativa_se_resuelve_a_absoluta():
    servidor = ServidorTusFalso(location="/files/xyz")
    cliente = cliente_con(servidor)

    await cliente.subir_archivo(
        "tok", ep.UPLOAD_PROPUESTA,
        ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
        nombre_archivo="p.txt", contenido=TXT,
    )

    patch = [p for p in servidor.peticiones if p.method == "PATCH"][0]
    assert str(patch.url) == "https://api-sire.sunat.gob.pe/files/xyz"


# ---------------------------------------------------------------------------
# 3. Errores: la razón de ser de este módulo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_422_al_crear_conserva_los_errores_del_archivo():
    """
    Es el caso por el que el manual pedía Java: sin recuperar este cuerpo, el
    usuario solo vería «error 422» y no qué línea de su archivo está mal.
    """
    cuerpo = {
        "cod": "422",
        "msg": "Unprocessable Entity - Se presentaron errores de validacion",
        "errors": [
            {"cod": "0301", "msg": "La fila 5 tiene un tipo de comprobante no válido"},
            {"cod": "0310", "msg": "La fila 12 tiene un RUC de proveedor inexistente"},
        ],
    }
    servidor = ServidorTusFalso(fallo_en={"crear": httpx.Response(422, json=cuerpo)})
    cliente = cliente_con(servidor)

    with pytest.raises(SunatValidationException) as exc:
        await cliente.subir_archivo(
            "tok", ep.UPLOAD_PROPUESTA,
            ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
            nombre_archivo="p.txt", contenido=TXT,
        )

    assert len(exc.value.errors) == 2
    assert "fila 5" in str(exc.value)


@pytest.mark.asyncio
async def test_422_a_mitad_de_la_carga_tambien_conserva_los_errores():
    cuerpo = {"cod": "422", "msg": "Rechazado", "errors": [{"cod": "0400", "msg": "Archivo corrupto"}]}
    servidor = ServidorTusFalso(fallo_en={"patch1": httpx.Response(422, json=cuerpo)})
    cliente = cliente_con(servidor)

    with pytest.raises(SunatValidationException) as exc:
        await cliente.subir_archivo(
            "tok", ep.UPLOAD_PROPUESTA,
            ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
            nombre_archivo="p.txt", contenido=TXT,
        )

    assert exc.value.errors[0]["cod"] == "0400"


@pytest.mark.asyncio
async def test_sin_location_no_se_intenta_enviar_a_ciegas():
    servidor = ServidorTusFalso(location=None)
    cliente = cliente_con(servidor)

    with pytest.raises(SireApiException, match="Location"):
        await cliente.subir_archivo(
            "tok", ep.UPLOAD_PROPUESTA,
            ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
            nombre_archivo="p.txt", contenido=TXT,
        )

    assert not any(p.method == "PATCH" for p in servidor.peticiones)


@pytest.mark.asyncio
async def test_sin_upload_offset_se_detiene_en_vez_de_corromper_el_archivo():
    """Sin saber qué aceptó SUNAT, seguir enviando escribiría basura."""
    servidor = ServidorTusFalso(omitir_offset=True)
    cliente = cliente_con(servidor)

    with pytest.raises(SireApiException, match="Upload-Offset"):
        await cliente.subir_archivo(
            "tok", ep.UPLOAD_PROPUESTA,
            ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
            nombre_archivo="p.txt", contenido=TXT,
        )


@pytest.mark.asyncio
async def test_archivo_vacio_no_sale_del_erp():
    cliente = cliente_con(ServidorTusFalso())
    with pytest.raises(SireApiException, match="vacío"):
        await cliente.subir_archivo(
            "tok", ep.UPLOAD_PROPUESTA,
            ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
            nombre_archivo="p.txt", contenido=b"",
        )


@pytest.mark.asyncio
async def test_carga_sin_ticket_no_revienta_pero_lo_deja_a_none():
    """Si SUNAT no devuelve numTicket hay que enterarse, no fingir que fue bien."""
    servidor = ServidorTusFalso(respuesta_final={})
    cliente = cliente_con(servidor)

    resultado = await cliente.subir_archivo(
        "tok", ep.UPLOAD_PROPUESTA,
        ruc=RUC, per_tributario=PERIODO, cod_proceso="61",
        nombre_archivo="p.txt", contenido=TXT,
    )
    assert resultado.num_ticket is None


# ---------------------------------------------------------------------------
# 4. El catálogo de operaciones contra el manual
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("clave,servicio,cod_proceso,destino", [
    ("reemplazar-propuesta",    "5.3", "61", ep.UPLOAD_PROPUESTA),
    ("no-domiciliados",         "5.5", "56", ep.UPLOAD_PRELIMINAR),
    ("complementar-propuesta",  "5.6", "54", ep.UPLOAD_PROPUESTA),
    ("importar-preliminar",     "5.7", "4",  ep.UPLOAD_PRELIMINAR),
    ("incluir-excluir",         "5.8", "55", ep.UPLOAD_PROPUESTA),
    ("importar-propuesta",      "5.9", "1",  ep.UPLOAD_PROPUESTA),
])
def test_operaciones_coinciden_con_el_anexo_i(clave, servicio, cod_proceso, destino):
    op = OPERACIONES[clave]
    assert op.servicio == servicio
    assert op.cod_proceso == cod_proceso
    assert op.url == destino


def test_solo_el_53_hace_avanzar_el_periodo():
    """Reemplazar la propuesta es el otro camino al preliminar; el resto no cambian de fase."""
    avanzan = [c for c, op in OPERACIONES.items() if op.estado_resultante]
    assert avanzan == ["reemplazar-propuesta"]
    assert OPERACIONES["reemplazar-propuesta"].estado_resultante == EstadoPeriodo.PRELIMINAR


# ---------------------------------------------------------------------------
# 5. Validación de estado en el servicio
# ---------------------------------------------------------------------------

class RepositorioFalso:
    def __init__(self, estado):
        self.periodo = PeriodoRce(ruc=RUC, periodo=PERIODO, estado=estado)

    async def obtener_o_crear(self, ruc, periodo):
        return self.periodo

    async def registrar_transicion(self, ruc, periodo, nuevo_estado, operacion,
                                   num_ticket=None, detalle=None):
        self.periodo.estado = nuevo_estado
        return self.periodo


class ClienteFalso:
    def __init__(self):
        self.llamadas = []

    async def subir_archivo(self, token, url, **kwargs):
        self.llamadas.append((url, kwargs.get("cod_proceso")))
        from app.modules.sire.services.tus_uploader import ResultadoCarga
        return ResultadoCarga(url_subida=url, bytes_enviados=10,
                              respuesta_final={"numTicket": "T-1"})


class AuthFalso:
    async def obtener_token_valido(self, ruc):
        return "tok"


class DbFalsa:
    def __getitem__(self, nombre):
        return None


def servicio(estado):
    svc = RceCargaService(DbFalsa(), ClienteFalso(), AuthFalso())
    svc.periodos = RepositorioFalso(estado)
    return svc


@pytest.mark.asyncio
async def test_carga_de_propuesta_exige_estado_propuesta():
    svc = servicio(EstadoPeriodo.PRELIMINAR)

    with pytest.raises(SireBusinessException) as exc:
        await svc.cargar(RUC, PERIODO, "incluir-excluir", "a.txt", TXT)

    assert svc.api_client.llamadas == [], "no debe subirse nada si el estado no cuadra"
    assert "PROPUESTA" in str(exc.value)


@pytest.mark.asyncio
async def test_carga_de_preliminar_exige_estado_preliminar():
    svc = servicio(EstadoPeriodo.PROPUESTA)

    with pytest.raises(SireBusinessException):
        await svc.cargar(RUC, PERIODO, "no-domiciliados", "a.txt", TXT)

    assert svc.api_client.llamadas == []


@pytest.mark.asyncio
async def test_reemplazar_propuesta_lleva_el_periodo_a_preliminar():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    resultado = await svc.cargar(RUC, PERIODO, "reemplazar-propuesta", "a.txt", TXT)

    assert resultado.num_ticket == "T-1"
    assert resultado.periodo.estado == EstadoPeriodo.PRELIMINAR
    assert svc.api_client.llamadas == [(ep.UPLOAD_PROPUESTA, "61")]


@pytest.mark.asyncio
async def test_operacion_desconocida_se_explica():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    with pytest.raises(SireValidationException, match="no es una carga conocida"):
        await svc.cargar(RUC, PERIODO, "inventada", "a.txt", TXT)


@pytest.mark.asyncio
async def test_archivo_demasiado_grande_se_rechaza_antes_de_subir():
    svc = servicio(EstadoPeriodo.PROPUESTA)
    enorme = b"x" * (51 * 1024 * 1024)

    with pytest.raises(SireValidationException, match="límite"):
        await svc.cargar(RUC, PERIODO, "reemplazar-propuesta", "a.txt", enorme)

    assert svc.api_client.llamadas == []
