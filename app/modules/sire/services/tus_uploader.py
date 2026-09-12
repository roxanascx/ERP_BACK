"""
Cliente del protocolo tus.io 1.0.0 para las cargas de archivos de SUNAT.

**Por qué no se usa una librería.** El Anexo IV del manual exige desarrollar
estos servicios en Java con `tus-java-client`, y explica el motivo: la librería
estándar no recupera bien el cuerpo de los errores, así que SUNAT entrega seis
clases propias (`Http422CodeException`, `TusResponseBody`, `TusClientCustom`…)
cuyo único cometido es rescatar el mensaje de un 422.

Ese es justo el problema que ya está resuelto aquí: `SunatApiClient` traduce el
422 conservando la lista `errors` entera. Envolver ahora el protocolo en una
librería de terceros volvería a esconder esa información. El protocolo son tres
verbos —POST para crear, PATCH para enviar trozos, HEAD para saber por dónde
ibas— así que se implementa directamente y el control de errores se mantiene.

Referencia: https://tus.io/protocols/resumable-upload
"""

import base64
import io
import logging
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx

from ..utils.exceptions import SireApiException

logger = logging.getLogger(__name__)

#: Versión del protocolo que anuncia SUNAT.
TUS_VERSION = "1.0.0"

#: Tamaño de cada trozo. SUNAT parte los archivos grandes; 5 MB es un
#: compromiso razonable entre número de peticiones y memoria.
TAMANO_TROZO = 5 * 1024 * 1024


@dataclass
class ResultadoCarga:
    """Lo que queda de una carga completada."""

    url_subida: str
    bytes_enviados: int
    respuesta_final: Dict[str, Any]

    @property
    def num_ticket(self) -> Optional[str]:
        """
        El ticket que devuelve SUNAT al terminar la carga.

        Los servicios de carga del manual devuelven `numTicket`, pero no
        documenta en qué parte de la respuesta TUS viaja. Se busca en el cuerpo
        y en las cabeceras habituales.
        """
        cuerpo = self.respuesta_final or {}
        for clave in ("numTicket", "num_ticket", "ticket"):
            if cuerpo.get(clave):
                return str(cuerpo[clave])
        return None


def codificar_metadata(metadata: Dict[str, str]) -> str:
    """
    Construir la cabecera `Upload-Metadata`.

    El formato del protocolo es `clave <valor en base64>` separando pares por
    comas. Los valores vacíos se envían como clave suelta, según la norma.
    """
    partes = []
    for clave, valor in metadata.items():
        if valor is None:
            continue
        texto = str(valor)
        if texto == "":
            partes.append(clave)
        else:
            codificado = base64.b64encode(texto.encode("utf-8")).decode("ascii")
            partes.append(f"{clave} {codificado}")
    return ",".join(partes)


def comprimir_txt(nombre_txt: str, contenido: bytes) -> bytes:
    """
    Empaquetar el `.txt` en un zip, que es lo que piden los servicios de carga.

    El manual habla siempre de "archivo .txt zipeado": SUNAT rechaza el txt
    suelto.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(nombre_txt, contenido)
    return buffer.getvalue()


class TusUploader:
    """Sube un archivo a un servidor tus.io conservando los errores de SUNAT."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        traductor_de_errores,
        tamano_trozo: int = TAMANO_TROZO,
    ):
        """
        Args:
            client: cliente httpx compartido con `SunatApiClient`.
            traductor_de_errores: función que convierte una respuesta de error
                en la excepción del módulo. Se inyecta para que un 422 durante
                la carga llegue con su lista de validaciones, que es la razón
                de ser de este módulo.
            tamano_trozo: bytes por PATCH.
        """
        self.client = client
        self._levantar_error = traductor_de_errores
        self.tamano_trozo = tamano_trozo

    def _cabeceras(self, token: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        cabeceras = {
            "Tus-Resumable": TUS_VERSION,
            "Authorization": f"Bearer {token}",
        }
        if extra:
            cabeceras.update(extra)
        return cabeceras

    async def crear(
        self, url: str, token: str, longitud: int, metadata: Dict[str, str]
    ) -> str:
        """
        Paso 1: anunciar la carga y obtener la URL donde enviarla.

        Returns:
            La URL de la carga, resuelta a absoluta si SUNAT la devuelve relativa.
        """
        respuesta = await self.client.post(
            url,
            headers=self._cabeceras(
                token,
                {
                    "Upload-Length": str(longitud),
                    "Upload-Metadata": codificar_metadata(metadata),
                    "Content-Length": "0",
                },
            ),
        )

        if respuesta.status_code >= 400:
            self._levantar_error(respuesta)

        ubicacion = respuesta.headers.get("Location") or respuesta.headers.get("location")
        if not ubicacion:
            raise SireApiException(
                "SUNAT aceptó la creación de la carga pero no devolvió la cabecera "
                f"Location, así que no hay dónde enviar el archivo. Respuesta: "
                f"{respuesta.status_code} {respuesta.text[:200]}",
                status_code=respuesta.status_code,
            )

        # El protocolo permite devolverla relativa.
        return urljoin(str(respuesta.url), ubicacion)

    async def obtener_offset(self, url_subida: str, token: str) -> int:
        """Paso opcional: por qué byte iba la carga, para poder reanudarla."""
        respuesta = await self.client.head(url_subida, headers=self._cabeceras(token))

        if respuesta.status_code >= 400:
            self._levantar_error(respuesta)

        try:
            return int(respuesta.headers.get("Upload-Offset", 0))
        except (TypeError, ValueError):
            return 0

    async def enviar(
        self, url_subida: str, token: str, contenido: bytes, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Paso 2: enviar el archivo por trozos desde `offset`.

        Returns:
            El cuerpo de la última respuesta, que es donde SUNAT devuelve el
            `numTicket`.
        """
        total = len(contenido)
        ultima: Dict[str, Any] = {}

        while offset < total:
            trozo = contenido[offset:offset + self.tamano_trozo]

            respuesta = await self.client.patch(
                url_subida,
                headers=self._cabeceras(
                    token,
                    {
                        "Content-Type": "application/offset+octet-stream",
                        "Upload-Offset": str(offset),
                    },
                ),
                content=trozo,
            )

            if respuesta.status_code >= 400:
                self._levantar_error(respuesta)

            nuevo_offset = respuesta.headers.get("Upload-Offset")
            if nuevo_offset is None:
                # Sin esta cabecera no se puede saber qué aceptó SUNAT; seguir
                # enviando a ciegas corrompería el archivo.
                raise SireApiException(
                    f"SUNAT no devolvió Upload-Offset tras enviar el trozo que "
                    f"empieza en {offset}; la carga no puede continuar de forma segura.",
                    status_code=respuesta.status_code,
                )

            try:
                offset = int(nuevo_offset)
            except ValueError:
                raise SireApiException(
                    f"SUNAT devolvió un Upload-Offset ilegible: {nuevo_offset!r}"
                )

            if respuesta.content:
                try:
                    ultima = respuesta.json()
                except Exception:
                    ultima = {"respuesta": respuesta.text}

        return ultima

    async def subir(
        self,
        url: str,
        token: str,
        contenido: bytes,
        metadata: Dict[str, str],
    ) -> ResultadoCarga:
        """
        Carga completa: crear, enviar y devolver lo que conteste SUNAT.

        Raises:
            SunatValidationException: si SUNAT rechaza el archivo con un 422.
                Es el caso importante: la excepción trae una fila por cada error
                del archivo.
        """
        if not contenido:
            raise SireApiException("No se puede subir un archivo vacío a SUNAT")

        logger.info(
            f"[TUS] Subiendo {len(contenido)} bytes a {url} "
            f"(codProceso={metadata.get('codProceso')})"
        )

        url_subida = await self.crear(url, token, len(contenido), metadata)
        respuesta = await self.enviar(url_subida, token, contenido)

        resultado = ResultadoCarga(
            url_subida=url_subida,
            bytes_enviados=len(contenido),
            respuesta_final=respuesta,
        )

        if resultado.num_ticket:
            logger.info(f"[TUS] Carga completada, ticket {resultado.num_ticket}")
        else:
            logger.warning(
                f"[TUS] Carga completada pero SUNAT no devolvió numTicket. "
                f"Respuesta: {respuesta}"
            )

        return resultado
