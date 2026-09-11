"""
Cargas de archivos al RCE (servicios 5.3 y 5.5–5.9 del manual).

Los seis comparten protocolo (tus.io), metadata y lista de errores 422; lo único
que cambia entre ellos es el `codProceso` y si el destino es la propuesta o el
preliminar. Por eso aquí se describen como datos, en `OPERACIONES`, en vez de
como seis funciones casi idénticas.

La regla de estados sale sola del manual: lo que modifica la **propuesta** exige
que el periodo siga en propuesta, y lo que modifica el **preliminar** exige que
ya se haya pasado a preliminar.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.rce_periodo import EstadoPeriodo, PeriodoRce
from ..repositories.rce_periodo_repository import RcePeriodoRepository
from ..utils.exceptions import SireBusinessException, SireValidationException
from . import sunat_endpoints as ep
from .api_client import SunatApiClient
from .auth_service import SireAuthService
from .sunat_endpoints import CodLibro, CodProceso

logger = logging.getLogger(__name__)

#: Tamaño máximo que se acepta en memoria antes de subir. SUNAT parte los
#: archivos grandes por su cuenta; esto solo evita que una petición del ERP
#: reviente el proceso.
MAX_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class OperacionCarga:
    """Una de las cargas del manual, descrita como datos."""

    servicio: str
    nombre: str
    url: str
    cod_proceso: str
    #: Estado en el que debe estar el periodo para que la carga tenga sentido.
    estado_requerido: EstadoPeriodo
    #: Estado al que pasa el periodo después, si la carga lo hace avanzar.
    estado_resultante: Optional[EstadoPeriodo] = None


OPERACIONES: Dict[str, OperacionCarga] = {
    "reemplazar-propuesta": OperacionCarga(
        servicio="5.3",
        nombre="Reemplazar la propuesta",
        url=ep.UPLOAD_PROPUESTA,
        cod_proceso=CodProceso.REEMPLAZO_PROPUESTA,
        estado_requerido=EstadoPeriodo.PROPUESTA,
        # Es el otro camino hacia el preliminar, junto con el 5.2.
        estado_resultante=EstadoPeriodo.PRELIMINAR,
    ),
    "no-domiciliados": OperacionCarga(
        servicio="5.5",
        nombre="Cargar registro de compras no domiciliados",
        url=ep.UPLOAD_PRELIMINAR,
        cod_proceso=CodProceso.CARGAR_NO_DOMICILIADOS,
        estado_requerido=EstadoPeriodo.PRELIMINAR,
    ),
    "complementar-propuesta": OperacionCarga(
        servicio="5.6",
        nombre="Importar datos complementarios de la propuesta",
        url=ep.UPLOAD_PROPUESTA,
        cod_proceso=CodProceso.COMPLEMENTAR_PROPUESTA,
        estado_requerido=EstadoPeriodo.PROPUESTA,
    ),
    "importar-preliminar": OperacionCarga(
        servicio="5.7",
        nombre="Importar nuevos comprobantes al preliminar",
        url=ep.UPLOAD_PRELIMINAR,
        cod_proceso=CodProceso.IMPORTAR_CP_PRELIMINAR,
        estado_requerido=EstadoPeriodo.PRELIMINAR,
    ),
    "incluir-excluir": OperacionCarga(
        servicio="5.8",
        nombre="Incluir o excluir comprobantes de la propuesta",
        url=ep.UPLOAD_PROPUESTA,
        cod_proceso=CodProceso.INCLUIR_EXCLUIR,
        estado_requerido=EstadoPeriodo.PROPUESTA,
    ),
    "importar-propuesta": OperacionCarga(
        servicio="5.9",
        nombre="Importar comprobantes no propuestos por SUNAT",
        url=ep.UPLOAD_PROPUESTA,
        cod_proceso=CodProceso.IMPORTAR_CP_PROPUESTA,
        estado_requerido=EstadoPeriodo.PROPUESTA,
    ),
}


@dataclass
class ResultadoCargaRce:
    """Lo que se devuelve tras una carga."""

    operacion: OperacionCarga
    num_ticket: Optional[str]
    bytes_enviados: int
    periodo: PeriodoRce


class RceCargaService:
    """Sube archivos al RCE validando antes que la operación tenga sentido."""

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        api_client: SunatApiClient,
        auth_service: SireAuthService,
    ):
        self.db = database
        self.api_client = api_client
        self.auth_service = auth_service
        self.periodos = RcePeriodoRepository(database)

    @staticmethod
    def operacion(clave: str) -> OperacionCarga:
        """Buscar la operación por su clave, con un error legible si no existe."""
        if clave not in OPERACIONES:
            raise SireValidationException(
                f"'{clave}' no es una carga conocida. Disponibles: "
                + ", ".join(sorted(OPERACIONES)),
                field="operacion",
                value=clave,
            )
        return OPERACIONES[clave]

    async def cargar(
        self,
        ruc: str,
        periodo: str,
        clave_operacion: str,
        nombre_archivo: str,
        contenido: bytes,
        cod_libro: str = CodLibro.RCE,
    ) -> ResultadoCargaRce:
        """
        Subir un archivo a SUNAT y registrar el resultado en el periodo.

        Args:
            clave_operacion: una de las claves de `OPERACIONES`.
            contenido: el `.txt` sin comprimir; el cliente lo zipea.

        Raises:
            SireValidationException: archivo vacío, demasiado grande o periodo
                mal formado.
            SireBusinessException: el periodo no está en el estado que la
                operación necesita.
            SunatValidationException: SUNAT rechazó el archivo, con una fila por
                cada error encontrado.
        """
        operacion = self.operacion(clave_operacion)

        if not (len(periodo) == 6 and periodo.isdigit()):
            raise SireValidationException(
                f"El periodo '{periodo}' no tiene el formato yyyymm que exige SUNAT",
                field="periodo",
                value=periodo,
            )

        if not contenido:
            raise SireValidationException(
                "El archivo está vacío", field="archivo", value=nombre_archivo
            )

        if len(contenido) > MAX_BYTES:
            raise SireValidationException(
                f"El archivo pesa {len(contenido) // 1024 // 1024} MB y el límite "
                f"admitido son {MAX_BYTES // 1024 // 1024} MB",
                field="archivo",
                value=nombre_archivo,
            )

        actual = await self.periodos.obtener_o_crear(ruc, periodo)
        if actual.estado != operacion.estado_requerido:
            raise SireBusinessException(
                f"«{operacion.nombre}» ({operacion.servicio}) necesita que el periodo "
                f"{periodo} esté en {operacion.estado_requerido.value}, y está en "
                f"{actual.estado.value}",
                business_rule="estado_incompatible_con_carga",
                details={
                    "estado_actual": actual.estado.value,
                    "estado_requerido": operacion.estado_requerido.value,
                    "servicio": operacion.servicio,
                },
            )

        token = await self.auth_service.obtener_token_valido(ruc)

        resultado = await self.api_client.subir_archivo(
            token,
            operacion.url,
            ruc=ruc,
            per_tributario=periodo,
            cod_proceso=operacion.cod_proceso,
            nombre_archivo=nombre_archivo,
            contenido=contenido,
            cod_libro=cod_libro,
        )

        # El estado solo avanza si la operación lo hace avanzar (5.3). El resto
        # modifican el contenido sin cambiar de fase, pero se dejan en el
        # historial para poder auditar qué se subió y cuándo.
        nuevo_estado = operacion.estado_resultante or actual.estado

        periodo_actualizado = await self.periodos.registrar_transicion(
            ruc,
            periodo,
            nuevo_estado,
            operacion=f"{operacion.servicio} {operacion.nombre}",
            num_ticket=resultado.num_ticket,
            detalle=f"{nombre_archivo} ({resultado.bytes_enviados} bytes)",
        )

        return ResultadoCargaRce(
            operacion=operacion,
            num_ticket=resultado.num_ticket,
            bytes_enviados=resultado.bytes_enviados,
            periodo=periodo_actualizado,
        )
