"""
Cliente HTTP para la API SUNAT SIRE.

Es la única puerta hacia SUNAT: las URLs salen de `sunat_endpoints` (verificadas
contra el manual v22) y el patrón asíncrono del manual —lanzar la operación,
recoger el `numTicket`, sondear 5.31, descargar con 5.32 y descomprimir— vive
resuelto una sola vez en `ejecutar_operacion_con_ticket`.

Lo que sustituye: un diccionario de 67 endpoints que no usaba nadie, con rutas
que no coincidían con el manual, y 16 métodos `rce_*` que apuntaban a claves
inexistentes de ese mismo diccionario (todos lanzaban `KeyError` si se les
llamaba). Las URLs buenas estaban copiadas a mano dentro de las rutas.
"""

import asyncio
import io
import logging
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..models.auth import SireCredentials, SireTokenData
from ..utils.exceptions import (
    SireApiException,
    SireAuthException,
    SireTimeoutException,
    SunatValidationException,
)
from . import sunat_endpoints as ep
from . import sunat_endpoints_rvie as ep_rvie
from .sunat_endpoints import CodLibro, CodOrigenEnvio, CodTipoArchivo, CodTipoResumen
from .sunat_endpoints_rvie import CodTipoArchivoRvie
from .tus_uploader import ResultadoCarga, TusUploader, comprimir_txt

logger = logging.getLogger(__name__)


class EstadoTicket:
    """
    Códigos de `codEstadoProceso` del servicio de tickets (5.31 en Compras,
    5.16 en Ventas: es el mismo endpoint compartido).

    Estos valores salen del **Anexo III del manual de Ventas v30**, que es el
    único de los dos manuales que los documenta. Antes se heredaban de un mapeo
    escrito a mano en `rvie_service`, y estaba equivocado: daba el 04 por error
    cuando en realidad significa «procesado sin errores», y el 05 por rechazo
    cuando es «en proceso».
    """

    CARGADO = "01"              # Cargado (solicitado)
    VALIDANDO = "02"            # Validando archivo
    PROCESADO_CON_ERRORES = "03"
    PROCESADO_SIN_ERRORES = "04"
    EN_PROCESO = "05"
    TERMINADO = "06"


#: Estados en los que ya no tiene sentido seguir sondeando.
ESTADOS_TERMINALES = frozenset({
    EstadoTicket.PROCESADO_CON_ERRORES,
    EstadoTicket.PROCESADO_SIN_ERRORES,
    EstadoTicket.TERMINADO,
})

#: El único estado terminal que significa que la operación falló.
ESTADOS_FALLIDOS = frozenset({EstadoTicket.PROCESADO_CON_ERRORES})

DESCRIPCION_ESTADO = {
    EstadoTicket.CARGADO: "Cargado",
    EstadoTicket.VALIDANDO: "Validando archivo",
    EstadoTicket.PROCESADO_CON_ERRORES: "Procesado con errores",
    EstadoTicket.PROCESADO_SIN_ERRORES: "Procesado sin errores",
    EstadoTicket.EN_PROCESO: "En proceso",
    EstadoTicket.TERMINADO: "Terminado",
}


@dataclass
class ArchivoTicket:
    """Un archivo devuelto por una operación con ticket, ya descomprimido."""
    nombre: str
    contenido: bytes

    @property
    def texto(self) -> str:
        """
        El contenido como texto.

        SUNAT entrega los TXT en UTF-8, y ahí es donde van las columnas con
        tilde ("Razón social", "Fecha de emisión"), que el parser localiza por
        nombre: decodificarlas mal deja esos campos vacíos sin dar ningún error.
        Se conserva latin-1 de reserva porque algunos reportes vienen así.
        """
        try:
            return self.contenido.decode("utf-8")
        except UnicodeDecodeError:
            return self.contenido.decode("latin-1", errors="replace")


@dataclass
class ResultadoTicket:
    """Resultado completo de una operación asíncrona de SUNAT."""
    num_ticket: str
    cod_estado: str
    descripcion: str = ""
    archivos: List[ArchivoTicket] = field(default_factory=list)
    registro: Dict[str, Any] = field(default_factory=dict)

    @property
    def exitoso(self) -> bool:
        return self.cod_estado == EstadoTicket.TERMINADO

    @property
    def texto(self) -> str:
        """Concatena el contenido de todos los archivos. Lo habitual es que haya uno."""
        return "\n".join(a.texto for a in self.archivos)


class SunatApiClient:
    """Cliente HTTP para comunicación con la API SUNAT SIRE."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Args:
            base_url: sobrescribe el dominio de la API SIRE (para pruebas).
            timeout: tiempo máximo por petición, en segundos.
        """
        self.base_url = base_url or ep.API_SIRE
        self.auth_url = f"{ep.API_SEGURIDAD}/clientessol"

        self.timeout = timeout
        self.max_retries = 3
        self.retry_delay = 1  # segundos

        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ERP-SIRE-Client/1.0.0",
        }

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
        )

    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ==================================================================
    # NÚCLEO HTTP
    # ==================================================================

    def _build_headers(
        self, token: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Construir headers para la petición"""
        headers = self.default_headers.copy()

        if token:
            headers["Authorization"] = f"Bearer {token}"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    @staticmethod
    def _levantar_error_sunat(response: httpx.Response) -> None:
        """
        Traducir una respuesta de error de SUNAT a una excepción del módulo.

        El 422 es el caso que importa: SUNAT devuelve
        `{"cod": "422", "msg": "...", "errors": [{"cod": "1001", "msg": "..."}]}`
        y esa lista es lo único que dice qué hay que corregir. Se conserva entera
        en la excepción en vez de aplastarla a un string.
        """
        cuerpo: Dict[str, Any] = {}
        try:
            cuerpo = response.json()
        except Exception:
            cuerpo = {}

        if response.status_code == 401:
            detalle = cuerpo.get("error_description") or "Token inválido o expirado"
            raise SireAuthException(f"SUNAT rechazó la autenticación: {detalle}")

        if response.status_code == 422:
            raise SunatValidationException(
                message=cuerpo.get("msg") or "SUNAT rechazó la petición por validación",
                errors=cuerpo.get("errors") or [],
                cod=cuerpo.get("cod"),
                response_data=cuerpo,
            )

        mensaje = (
            cuerpo.get("msg")
            or cuerpo.get("message")
            or (response.text[:300] if response.text else "")
            or f"Error HTTP {response.status_code}"
        )
        raise SireApiException(mensaje, status_code=response.status_code, response_data=cuerpo)

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        retry_count: int = 0,
    ) -> httpx.Response:
        """
        Realizar una petición HTTP, con reintentos ante fallos de red.

        Los errores que devuelve SUNAT (4xx/5xx) no se reintentan: se traducen a
        excepción. Solo se reintentan timeouts y errores de conexión.
        """
        request_headers = self._build_headers(token, headers)

        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=data,
                params=params,
            )

            if response.status_code >= 400:
                self._levantar_error_sunat(response)

            return response

        except httpx.TimeoutException:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(
                    method, url, headers, data, params, token, retry_count + 1
                )
            raise SireTimeoutException(
                f"SUNAT no respondió tras {self.max_retries} reintentos: {method} {url}"
            )

        except httpx.RequestError as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(
                    method, url, headers, data, params, token, retry_count + 1
                )
            raise SireApiException(
                f"Error de conexión con SUNAT tras {self.max_retries} reintentos: {e}"
            )

    # ==================================================================
    # AUTENTICACIÓN (5.1)
    # ==================================================================

    async def authenticate(self, credentials: SireCredentials) -> SireTokenData:
        """
        5.1 Obtener el token Bearer.

        El `username` es RUC y usuario SOL concatenados sin separador, tal como
        exige el manual.
        """
        auth_data = {
            "grant_type": "password",
            "scope": ep.API_SIRE.rsplit("/v1", 1)[0],
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "username": f"{credentials.ruc}{credentials.sunat_usuario}",
            "password": credentials.sunat_clave,
        }

        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        try:
            response = await self.client.request(
                method="POST",
                url=ep.token(credentials.client_id),
                headers=auth_headers,
                data=auth_data,  # form-urlencoded, no JSON
            )
        except httpx.RequestError as e:
            raise SireAuthException(f"No se pudo contactar con el servicio de seguridad: {e}")

        if response.status_code >= 400:
            detalle = f"HTTP {response.status_code}"
            try:
                detalle = response.json().get("error_description", detalle)
            except Exception:
                detalle = response.text[:200] or detalle
            raise SireAuthException(f"SUNAT rechazó las credenciales: {detalle}")

        token_data = response.json()

        return SireTokenData(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data["expires_in"],
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
        )

    async def refresh_token(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> SireTokenData:
        """Renovar el token a partir del refresh_token."""
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            response = await self.client.request(
                method="POST",
                url=ep.token(client_id),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data=refresh_data,
            )
            if response.status_code >= 400:
                self._levantar_error_sunat(response)

            token_data = response.json()

            return SireTokenData(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data["expires_in"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                scope=token_data.get("scope"),
            )
        except (SireAuthException, SireApiException):
            raise
        except Exception as e:
            raise SireAuthException(f"Error renovando token: {e}")

    # ==================================================================
    # AYUDANTES CON URL ABSOLUTA
    # ==================================================================

    async def get_json(
        self, url: str, token: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """GET autenticado que devuelve JSON."""
        response = await self._make_request("GET", url, token=token, params=params)
        return response.json()

    async def post_json(
        self,
        url: str,
        token: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST autenticado que devuelve JSON. Tolera respuestas con cuerpo vacío."""
        response = await self._make_request("POST", url, token=token, data=data, params=params)
        return self._json_o_vacio(response)

    async def put_json(
        self,
        url: str,
        token: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """PUT autenticado que devuelve JSON."""
        response = await self._make_request("PUT", url, token=token, data=data, params=params)
        return self._json_o_vacio(response)

    async def delete_json(
        self,
        url: str,
        token: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """DELETE autenticado que devuelve JSON."""
        response = await self._make_request("DELETE", url, token=token, data=data, params=params)
        return self._json_o_vacio(response)

    async def get_bytes(
        self, url: str, token: str, params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """GET autenticado que devuelve el cuerpo en crudo (descargas directas)."""
        response = await self._make_request(
            "GET", url, headers={"Accept": "*/*"}, token=token, params=params
        )
        return response.content

    @staticmethod
    def _json_o_vacio(response: httpx.Response) -> Dict[str, Any]:
        """
        Varios servicios (5.4, 5.11, 5.17…) responden 200 sin cuerpo.
        Devolver `{}` evita que un `json()` reviente en el camino feliz.
        """
        if not response.content:
            return {}
        try:
            return response.json()
        except Exception:
            return {"respuesta": response.text}

    async def health_check(self) -> bool:
        """
        Comprobar que la API de SUNAT responde.

        SUNAT no publica un endpoint de salud: un 401/403 ya demuestra que el
        servidor está vivo y contestando.
        """
        try:
            response = await self.client.request("GET", self.base_url)
            return response.status_code in (200, 401, 403)
        except Exception:
            return False

    # ==================================================================
    # OPERACIONES CON TICKET (5.31 / 5.32)
    # ==================================================================

    async def consultar_ticket(
        self,
        token: str,
        num_ticket: str,
        per_ini: str,
        per_fin: Optional[str] = None,
        cod_libro: str = CodLibro.RCE,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        5.31 Consultar el estado de un ticket.

        Devuelve el registro concreto de `num_ticket`, o `{}` si SUNAT todavía no
        lo lista.
        """
        datos = await self.get_json(
            ep.consultar_estado_tickets(),
            token,
            params={
                "perIni": per_ini,
                "perFin": per_fin or per_ini,
                "page": page,
                "perPage": per_page,
                "numTicket": num_ticket,
                "codLibro": cod_libro,
                "codOrigenEnvio": CodOrigenEnvio.SERVICIO_API,
            },
        )

        for registro in datos.get("registros", []):
            if str(registro.get("numTicket")) == str(num_ticket):
                return registro

        return {}

    async def descargar_archivo_reporte(
        self,
        token: str,
        nom_archivo: str,
        cod_tipo_archivo: str,
        per_tributario: Optional[str] = None,
        cod_proceso: Optional[str] = None,
        num_ticket: Optional[str] = None,
        cod_libro: str = CodLibro.RCE,
    ) -> bytes:
        """
        5.32 Descargar el archivo generado por un ticket.

        El manual solo documenta `nomArchivoReporte` y `codTipoArchivoReporte`,
        pero en la práctica SUNAT necesita además el periodo, el proceso, el
        ticket y el libro; sin ellos responde con un archivo vacío.
        """
        params: Dict[str, Any] = {
            "nomArchivoReporte": nom_archivo,
            "codTipoArchivoReporte": cod_tipo_archivo,
            "codLibro": cod_libro,
        }
        if per_tributario:
            params["perTributario"] = per_tributario
        if cod_proceso:
            params["codProceso"] = cod_proceso
        if num_ticket:
            params["numTicket"] = num_ticket

        return await self.get_bytes(ep.descargar_archivo_reporte(), token, params=params)

    @staticmethod
    def _extraer_archivos(nombre: str, contenido: bytes) -> List[ArchivoTicket]:
        """
        Descomprimir la descarga.

        SUNAT entrega los reportes zipeados (y, cuando son grandes, partidos en
        varios archivos dentro del mismo zip). Si lo que llega no es un zip se
        devuelve tal cual, que es lo que ocurre con algunos TXT pequeños.
        """
        if not contenido:
            return []

        if not contenido[:2] == b"PK":
            return [ArchivoTicket(nombre=nombre, contenido=contenido)]

        archivos: List[ArchivoTicket] = []
        try:
            with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                for interno in z.namelist():
                    if interno.endswith("/"):
                        continue
                    archivos.append(ArchivoTicket(nombre=interno, contenido=z.read(interno)))
        except zipfile.BadZipFile:
            logger.warning(f"[SUNAT] El archivo {nombre} parecía un zip pero no se pudo abrir")
            return [ArchivoTicket(nombre=nombre, contenido=contenido)]

        return archivos

    async def ejecutar_operacion_con_ticket(
        self,
        token: str,
        url: str,
        per_tributario: str,
        *,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        cod_libro: str = CodLibro.RCE,
        descargar: bool = True,
        ticket_opcional: bool = False,
        espera_inicial: float = 2.0,
        espera_maxima: float = 15.0,
        timeout_total: float = 300.0,
    ) -> ResultadoTicket:
        """
        Ejecutar una operación asíncrona de SUNAT de principio a fin.

        Es el patrón que el manual repite en todos los servicios de
        importar/exportar/descargar: lanzar la petición, quedarse con el
        `numTicket`, sondear 5.31 hasta que el proceso termine, descargar con
        5.32 y descomprimir el resultado.

        Args:
            url: endpoint de `sunat_endpoints` que devuelve `numTicket`.
            per_tributario: periodo `yyyymm`, necesario para consultar el ticket.
            descargar: si es False se para al terminar el proceso, sin bajar el
                archivo (útil cuando solo interesa saber si SUNAT aceptó).
            espera_inicial / espera_maxima: sondeo con espera creciente, para no
                castigar a SUNAT en procesos largos.
            timeout_total: tiempo máximo total de sondeo, en segundos.

        Raises:
            SireApiException: si SUNAT no devuelve ticket, si el proceso acaba en
                error o si se agota el tiempo de sondeo.
            SunatValidationException: si SUNAT rechaza la petición con un 422.
        """
        # --- Paso 1: lanzar la operación y quedarse con el ticket ---
        respuesta = await self._make_request(
            method, url, token=token, params=params, data=data
        )
        cuerpo = self._json_o_vacio(respuesta)

        num_ticket = str(cuerpo.get("numTicket") or "").strip()
        if not num_ticket:
            if ticket_opcional:
                # En Ventas, 5.9 y 5.15 responden sin ticket cuando el proceso
                # terminó de forma síncrona. No hay nada que sondear.
                logger.info(
                    f"[SUNAT] {url} terminó sin ticket: proceso síncrono completado"
                )
                return ResultadoTicket(
                    num_ticket="",
                    cod_estado=EstadoTicket.TERMINADO,
                    descripcion="Completado sin ticket",
                )
            raise SireApiException(
                f"SUNAT no devolvió numTicket para la operación {url}. Respuesta: {cuerpo}"
            )

        logger.info(f"[SUNAT] Ticket {num_ticket} generado para el periodo {per_tributario}")

        # --- Paso 2: sondear 5.31 hasta que el proceso termine ---
        espera = espera_inicial
        transcurrido = 0.0
        registro: Dict[str, Any] = {}
        cod_estado = EstadoTicket.EN_PROCESO

        while transcurrido < timeout_total:
            await asyncio.sleep(espera)
            transcurrido += espera

            registro = await self.consultar_ticket(
                token, num_ticket, per_ini=per_tributario, cod_libro=cod_libro
            )
            cod_estado = str(registro.get("codEstadoProceso") or "").strip() or cod_estado

            if cod_estado in ESTADOS_TERMINALES:
                break

            espera = min(espera * 1.5, espera_maxima)

        descripcion = registro.get("desEstadoProceso") or DESCRIPCION_ESTADO.get(cod_estado, "")

        if cod_estado not in ESTADOS_TERMINALES:
            raise SireApiException(
                f"El ticket {num_ticket} seguía en estado '{descripcion or cod_estado}' "
                f"después de {int(transcurrido)} s. Consúltalo más tarde con el servicio 5.31."
            )

        if cod_estado in ESTADOS_FALLIDOS:
            detalle = registro.get("detalleTicket") or {}
            raise SireApiException(
                f"SUNAT terminó el ticket {num_ticket} con estado "
                f"'{descripcion or cod_estado}'. Detalle: {detalle}",
                status_code=200,
                response_data=registro,
            )

        resultado = ResultadoTicket(
            num_ticket=num_ticket,
            cod_estado=cod_estado,
            descripcion=descripcion,
            registro=registro,
        )

        if not descargar:
            return resultado

        # --- Paso 3: descargar con 5.32 y descomprimir ---
        for archivo in registro.get("archivoReporte", []) or []:
            # SUNAT escribe esta clave sin la 'r': 'codTipoAchivoReporte'.
            cod_tipo = archivo.get("codTipoAchivoReporte") or archivo.get("codTipoArchivoReporte")
            nombre = archivo.get("nomArchivoReporte")
            if not nombre:
                continue

            contenido = await self.descargar_archivo_reporte(
                token,
                nom_archivo=nombre,
                cod_tipo_archivo=cod_tipo,
                per_tributario=per_tributario,
                cod_proceso=registro.get("codProceso"),
                num_ticket=num_ticket,
                cod_libro=cod_libro,
            )
            resultado.archivos.extend(self._extraer_archivos(nombre, contenido))

        return resultado

    # ==================================================================
    # SERVICIOS RCE
    # ==================================================================

    async def periodos_habilitados(
        self, token: str, cod_libro: str = CodLibro.RCE
    ) -> Dict[str, Any]:
        """5.33 Periodos habilitados para el contribuyente."""
        return await self.get_json(ep.periodos_habilitados(cod_libro), token)

    async def descargar_propuesta(
        self,
        token: str,
        per_tributario: str,
        cod_tipo_archivo: str = CodTipoArchivo.TXT,
        filtros: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ResultadoTicket:
        """5.34 Descargar la propuesta del periodo. Operación con ticket."""
        params: Dict[str, Any] = {
            "codTipoArchivo": cod_tipo_archivo,
            "codOrigenEnvio": CodOrigenEnvio.SERVICIO_API,
        }
        if filtros:
            params.update({k: v for k, v in filtros.items() if v is not None})

        return await self.ejecutar_operacion_con_ticket(
            token, ep.descargar_propuesta(per_tributario), per_tributario,
            method="GET", params=params, **kwargs,
        )

    async def descargar_resumen(
        self,
        token: str,
        per_tributario: str,
        cod_tipo_resumen: str = CodTipoResumen.PROPUESTA,
        cod_tipo_archivo: str = CodTipoArchivo.TXT,
        cod_libro: str = CodLibro.RCE,
    ) -> str:
        """
        5.35 Descargar un resumen.

        A diferencia del resto de descargas, este servicio responde con el
        contenido directamente, sin pasar por ticket.
        """
        contenido = await self.get_bytes(
            ep.descargar_resumen(per_tributario, cod_tipo_resumen, cod_tipo_archivo),
            token,
            params={"codLibro": cod_libro},
        )
        archivos = self._extraer_archivos(f"resumen_{per_tributario}", contenido)
        return "\n".join(a.texto for a in archivos)

    async def aceptar_propuesta(
        self, token: str, per_tributario: str, cod_libro: str = CodLibro.RCE, **kwargs: Any
    ) -> ResultadoTicket:
        """
        5.2 Aceptar la propuesta de SUNAT: el libro pasa a preliminar.

        No lleva cuerpo. Devuelve `numTicket`; el resultado se recoge por 5.31.
        """
        return await self.ejecutar_operacion_con_ticket(
            token, ep.aceptar_propuesta(per_tributario), per_tributario,
            method="POST", cod_libro=cod_libro, descargar=False, **kwargs,
        )

    async def registrar_preliminar(
        self, token: str, per_tributario: str, cod_libro: str = CodLibro.RCE, **kwargs: Any
    ) -> ResultadoTicket:
        """5.4 Registrar el preliminar. Paso final antes de la generación."""
        return await self.ejecutar_operacion_con_ticket(
            token, ep.registrar_preliminar(per_tributario), per_tributario,
            method="POST", cod_libro=cod_libro, descargar=False, **kwargs,
        )

    async def eliminar_preliminar(
        self, token: str, per_tributario: str, ind_eliminar: str
    ) -> Dict[str, Any]:
        """5.17 Eliminar el preliminar. Marcha atrás del 5.4. Ver `IndEliminarPreliminar`."""
        return await self.put_json(
            ep.eliminar_preliminar(per_tributario, ind_eliminar), token
        )

    # ==================================================================
    # CARGA DE ARCHIVOS (servicios TUS: 5.3, 5.5–5.9, 5.18…)
    # ==================================================================

    @staticmethod
    def metadata_carga(
        ruc: str,
        per_tributario: str,
        cod_proceso: str,
        nombre_archivo: str,
        cod_libro: str = CodLibro.RCE,
    ) -> Dict[str, str]:
        """
        Metadata TUS común a todos los servicios de carga.

        El manual la repite idéntica en los 18 servicios de importación: lo
        único que distingue una operación de otra es `codProceso` y el endpoint
        de destino.
        """
        return {
            "filename": nombre_archivo,
            "filetype": "application/zip",
            "numRuc": ruc,
            "perTributario": per_tributario,
            "codOrigenEnvio": CodOrigenEnvio.SERVICIO_API,
            "codProceso": cod_proceso,
            "codTipoCorrelativo": "01",
            "nomArchivoImportacion": nombre_archivo,
            "codLibro": cod_libro,
        }

    async def subir_archivo(
        self,
        token: str,
        url: str,
        *,
        ruc: str,
        per_tributario: str,
        cod_proceso: str,
        nombre_archivo: str,
        contenido: bytes,
        comprimir: bool = True,
        cod_libro: str = CodLibro.RCE,
    ) -> ResultadoCarga:
        """
        Subir un archivo a SUNAT por tus.io y devolver su ticket.

        Args:
            url: destino de `sunat_endpoints` (UPLOAD_PROPUESTA, UPLOAD_PRELIMINAR
                o UPLOAD_AJUSTES_POSTERIORES).
            cod_proceso: lo que decide la operación. Ver `CodProceso`.
            contenido: el `.txt` en bytes.
            comprimir: SUNAT solo acepta el txt zipeado; ponerlo a False sirve
                para cuando el llamante ya trae el zip hecho.

        Raises:
            SunatValidationException: si SUNAT rechaza el archivo con un 422,
                con una fila por cada error encontrado.
        """
        # Comprobar antes de comprimir: un .txt vacío produce un zip que no lo
        # está, y SUNAT lo aceptaría como si llevara datos.
        if not contenido:
            raise SireApiException(
                f"El archivo {nombre_archivo} está vacío; no se envía a SUNAT"
            )

        if comprimir:
            nombre_txt = nombre_archivo
            if nombre_txt.lower().endswith(".zip"):
                nombre_txt = nombre_txt[:-4] + ".txt"
            elif not nombre_txt.lower().endswith(".txt"):
                nombre_txt = nombre_txt + ".txt"

            contenido = comprimir_txt(nombre_txt, contenido)
            nombre_archivo = nombre_txt[:-4] + ".zip"

        uploader = TusUploader(self.client, self._levantar_error_sunat)

        return await uploader.subir(
            url,
            token,
            contenido,
            self.metadata_carga(ruc, per_tributario, cod_proceso, nombre_archivo, cod_libro),
        )

    # ==================================================================
    # SERVICIOS RVIE (Ventas). Manual v30.
    # ==================================================================

    async def rvie_aceptar_propuesta(
        self, token: str, per_tributario: str, **kwargs: Any
    ) -> ResultadoTicket:
        """5.8 Aceptar la propuesta del RVIE. El libro pasa a preliminar."""
        return await self.ejecutar_operacion_con_ticket(
            token, ep_rvie.aceptar_propuesta(per_tributario), per_tributario,
            method="POST", cod_libro=CodLibro.RVIE, descargar=False, **kwargs,
        )

    async def rvie_registrar_preliminar(
        self, token: str, per_tributario: str, **kwargs: Any
    ) -> ResultadoTicket:
        """
        5.9 Registrar el preliminar del RVIE.

        Puede responder sin ticket: en ese caso el proceso ya terminó bien.
        """
        return await self.ejecutar_operacion_con_ticket(
            token, ep_rvie.registrar_preliminar(per_tributario), per_tributario,
            method="POST", cod_libro=CodLibro.RVIE, descargar=False,
            ticket_opcional=True, **kwargs,
        )

    async def rvie_eliminar_reemplazo(
        self, token: str, per_tributario: str, **kwargs: Any
    ) -> ResultadoTicket:
        """5.15 Eliminar el preliminar no registrado y los datos del reemplazo."""
        return await self.ejecutar_operacion_con_ticket(
            token, ep_rvie.eliminar_reemplazo(per_tributario), per_tributario,
            method="PUT", params={"codLibro": CodLibro.RVIE},
            cod_libro=CodLibro.RVIE, descargar=False, ticket_opcional=True, **kwargs,
        )

    async def rvie_descargar_propuesta(
        self,
        token: str,
        per_tributario: str,
        cod_tipo_archivo: str = CodTipoArchivoRvie.TXT,
        filtros: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ResultadoTicket:
        """
        5.18 Descargar la propuesta de ventas.

        Ojo con `cod_tipo_archivo`: los códigos de Ventas no son los de Compras.
        """
        params: Dict[str, Any] = {"codTipoArchivo": cod_tipo_archivo}
        if filtros:
            params.update({k: v for k, v in filtros.items() if v is not None})

        return await self.ejecutar_operacion_con_ticket(
            token, ep_rvie.descargar_propuesta(per_tributario), per_tributario,
            method="GET", params=params, cod_libro=CodLibro.RVIE, **kwargs,
        )

    async def rvie_periodos_habilitados(self, token: str) -> Dict[str, Any]:
        """5.2 Periodos habilitados para ventas. Mismo servicio que en Compras, otro libro."""
        return await self.get_json(ep.periodos_habilitados(CodLibro.RVIE), token)

    async def rvie_descargar_resumen(
        self,
        token: str,
        per_tributario: str,
        cod_tipo_resumen: str = CodTipoResumen.PROPUESTA,
        cod_tipo_archivo: str = CodTipoArchivoRvie.TXT,
    ) -> str:
        """5.20 Descargar resumen de ventas. Descarga directa, sin ticket."""
        contenido = await self.get_bytes(
            ep.descargar_resumen(per_tributario, cod_tipo_resumen, cod_tipo_archivo),
            token,
            params={"codLibro": CodLibro.RVIE},
        )
        archivos = self._extraer_archivos(f"resumen_rvie_{per_tributario}", contenido)
        return "\n".join(a.texto for a in archivos)
