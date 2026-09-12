"""
Ciclo de vida de un periodo RVIE (ventas).

Implementa la secuencia mínima del manual de Ventas v30 (§3.1): aceptar la
propuesta (5.8) y registrar el preliminar (5.9), más la consulta de periodos
habilitados (5.2) y las dos marchas atrás, que en Ventas son **dos servicios
distintos** según en qué fase esté el libro:

  - 5.15 elimina el preliminar **no registrado** y los datos del reemplazo.
  - 5.36 elimina el preliminar **ya registrado**, y necesita un `id` que da 5.37.

Comparte la máquina de estados con Compras (`models/rce_periodo`), porque las
fases del libro son las mismas; lo que cambia son las URLs, el `codLibro` y los
códigos de error de negocio.
"""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.rce_periodo import (
    EstadoPeriodo,
    OPERACION_DE_TRANSICION,
    PeriodoRce,
    transicion_permitida,
)
from ..repositories.rce_periodo_repository import RviePeriodoRepository
from ..utils.exceptions import (
    SireApiException,
    SireBusinessException,
    SireValidationException,
    SunatValidationException,
)
from . import sunat_endpoints_rvie as ep_rvie
from .api_client import SunatApiClient
from .auth_service import SireAuthService
from ..utils.resumen import parsear_resumen
from .sunat_endpoints import COD_SIN_COMPROBANTES, CodLibro, CodTipoResumen
from .sunat_endpoints_rvie import ErrorNegocioRvie

logger = logging.getLogger(__name__)

#: `desEstado` del 5.2 que significa que el periodo sigue abierto.
ESTADO_SUNAT_ABIERTO = "No Presentado"


class RvieCicloService:
    """Operaciones que hacen avanzar (o retroceder) un periodo RVIE."""

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        api_client: SunatApiClient,
        auth_service: SireAuthService,
    ):
        self.db = database
        self.api_client = api_client
        self.auth_service = auth_service
        self.periodos = RviePeriodoRepository(database)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    @staticmethod
    def _validar_periodo(periodo: str) -> None:
        """El manual exige `yyyymm` en todos los servicios."""
        if not (len(periodo) == 6 and periodo.isdigit()):
            raise SireValidationException(
                f"El periodo '{periodo}' no tiene el formato yyyymm que exige SUNAT",
                field="periodo",
                value=periodo,
            )
        if not 1 <= int(periodo[4:]) <= 12:
            raise SireValidationException(
                f"El periodo '{periodo}' tiene un mes fuera de rango",
                field="periodo",
                value=periodo,
            )

    async def consultar_periodos_habilitados(self, ruc: str) -> List[Dict[str, Any]]:
        """
        5.2 Periodos habilitados para ventas.

        Mismo servicio que el 5.33 de Compras, con `codLibro=140000`. SUNAT los
        devuelve agrupados por ejercicio, así que se aplanan igual.
        """
        from .rce_ciclo_service import RceCicloService

        token = await self.auth_service.obtener_token_valido(ruc)
        datos = await self.api_client.rvie_periodos_habilitados(token)
        return RceCicloService._aplanar_periodos(datos, ruc)

    async def obtener_resumen_propuesta(self, ruc: str, periodo: str) -> dict:
        """5.20 Resumen de la propuesta de ventas: cuántos comprobantes y por cuánto."""
        self._validar_periodo(periodo)
        token = await self.auth_service.obtener_token_valido(ruc)

        try:
            contenido = await self.api_client.rvie_descargar_resumen(
                token, per_tributario=periodo, cod_tipo_resumen=CodTipoResumen.PROPUESTA
            )
        except SunatValidationException as e:
            if COD_SIN_COMPROBANTES in {str(err.get("cod")) for err in e.errors}:
                return {**parsear_resumen(""), "sin_datos": True, "motivo": str(e)}
            raise

        return {**parsear_resumen(contenido), "sin_datos": False}

    async def obtener_estado(self, ruc: str, periodo: str) -> PeriodoRce:
        """Estado local del periodo de ventas."""
        self._validar_periodo(periodo)
        return await self.periodos.obtener_o_crear(ruc, periodo)

    async def listar_estados(self, ruc: str, limite: int = 24) -> List[PeriodoRce]:
        """Periodos de ventas sobre los que ya se ha operado."""
        return await self.periodos.listar_por_ruc(ruc, limite)

    # ------------------------------------------------------------------
    # Avance del ciclo
    # ------------------------------------------------------------------

    async def _exigir_transicion(
        self, ruc: str, periodo: str, destino: EstadoPeriodo
    ) -> PeriodoRce:
        """Comprobar que la operación es legal antes de molestar a SUNAT."""
        actual = await self.periodos.obtener_o_crear(ruc, periodo)

        if not transicion_permitida(actual.estado, destino):
            operacion = OPERACION_DE_TRANSICION.get((actual.estado, destino), "esa operación")
            disponibles = actual.operaciones_disponibles()
            raise SireBusinessException(
                f"El periodo {periodo} está en estado {actual.estado.value} y no admite "
                f"{operacion}. Ahora mismo puedes: "
                + (", ".join(disponibles) if disponibles else "nada"),
                business_rule="transicion_periodo_rvie",
                details={
                    "estado_actual": actual.estado.value,
                    "estado_solicitado": destino.value,
                    "operaciones_disponibles": disponibles,
                },
            )

        return actual

    async def consultar_estado_en_sunat(self, ruc: str, periodo: str):
        """
        Qué dice SUNAT del periodo, según el 5.2.

        El estado local solo conoce lo hecho desde el ERP; si alguien trabajó en
        el portal SOL, SUNAT sabe más. Devolver ambas versiones deja la
        discrepancia a la vista antes de escribir nada.
        """
        self._validar_periodo(periodo)
        try:
            for candidato in await self.consultar_periodos_habilitados(ruc):
                if candidato.get("perTributario") == periodo:
                    return candidato
        except SireApiException as e:
            logger.warning(
                f"[RVIE] No se pudo consultar el estado de {ruc}/{periodo} en SUNAT: {e}"
            )
        return None

    async def _exigir_periodo_abierto_en_sunat(self, ruc: str, periodo: str) -> None:
        """Negarse a escribir sobre un periodo que SUNAT ya da por presentado."""
        en_sunat = await self.consultar_estado_en_sunat(ruc, periodo)

        if en_sunat is None:
            return

        des_estado = (en_sunat.get("desEstado") or "").strip()
        if des_estado and des_estado != ESTADO_SUNAT_ABIERTO:
            raise SireBusinessException(
                f"SUNAT reporta el periodo {periodo} como «{des_estado}», así que no "
                f"admite aceptar la propuesta. Suele significar que ya se operó desde "
                f"el portal SOL.",
                business_rule="periodo_cerrado_en_sunat",
                details={
                    "estado_sunat": des_estado,
                    "cod_estado_sunat": en_sunat.get("codEstado"),
                },
            )

    async def aceptar_propuesta(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        5.8 Aceptar la propuesta del RVIE: el libro pasa a preliminar.

        Antes de escribir se comprueba contra SUNAT que el periodo siga abierto.
        """
        self._validar_periodo(periodo)
        await self._exigir_transicion(ruc, periodo, EstadoPeriodo.PRELIMINAR)
        await self._exigir_periodo_abierto_en_sunat(ruc, periodo)

        token = await self.auth_service.obtener_token_valido(ruc)
        resultado = await self.api_client.rvie_aceptar_propuesta(token, per_tributario=periodo)

        return await self.periodos.registrar_transicion(
            ruc, periodo, EstadoPeriodo.PRELIMINAR,
            operacion="5.8 aceptar propuesta",
            num_ticket=resultado.num_ticket or None,
            detalle=resultado.descripcion,
        )

    async def registrar_preliminar(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        5.9 Registrar el preliminar del RVIE.

        Ventas define tres errores de negocio propios para este servicio. Los
        dos que significan «SUNAT va por delante» reconcilian el estado local en
        vez de propagarse como fallo; el 2293 sí es un error del usuario.
        """
        self._validar_periodo(periodo)
        await self._exigir_transicion(ruc, periodo, EstadoPeriodo.REGISTRADO)

        token = await self.auth_service.obtener_token_valido(ruc)

        try:
            resultado = await self.api_client.rvie_registrar_preliminar(
                token, per_tributario=periodo
            )
        except SunatValidationException as e:
            codigos = {str(err.get("cod")) for err in e.errors}

            if codigos & {
                ErrorNegocioRvie.YA_EN_PRELIMINAR_REGISTRADO,
                ErrorNegocioRvie.YA_GENERADO_DESDE_PORTAL,
            }:
                logger.info(
                    f"[RVIE] SUNAT informa que {ruc}/{periodo} ya estaba registrado; "
                    f"se reconcilia el estado local"
                )
                return await self.periodos.registrar_transicion(
                    ruc, periodo, EstadoPeriodo.REGISTRADO,
                    operacion="5.9 registrar preliminar (ya registrado en SUNAT)",
                    detalle=str(e),
                )

            if ErrorNegocioRvie.AUN_EN_PROPUESTA in codigos:
                raise SireBusinessException(
                    f"SUNAT informa que el periodo {periodo} sigue en propuesta: hay que "
                    f"aceptarla (5.8) o reemplazarla (5.3) antes de registrar. {e}",
                    business_rule="rvie_aun_en_propuesta",
                    details={"errores_sunat": e.errors},
                )

            raise

        return await self.periodos.registrar_transicion(
            ruc, periodo, EstadoPeriodo.REGISTRADO,
            operacion="5.9 registrar preliminar",
            num_ticket=resultado.num_ticket or None,
            detalle=resultado.descripcion,
        )

    # ------------------------------------------------------------------
    # Marcha atrás
    # ------------------------------------------------------------------

    async def eliminar_preliminar(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        5.15 Eliminar el preliminar no registrado y los datos del reemplazo.

        Si el periodo ya está registrado, SUNAT responde 2299 y hay que usar
        5.36 en su lugar; el error lo dice explícitamente para no dejar al
        usuario adivinando.
        """
        self._validar_periodo(periodo)

        actual = await self.periodos.obtener_o_crear(ruc, periodo)

        if actual.estado == EstadoPeriodo.PROPUESTA:
            raise SireBusinessException(
                f"El periodo {periodo} está en propuesta: no hay preliminar que eliminar",
                business_rule="rvie_sin_preliminar",
                details={"estado_actual": actual.estado.value},
            )

        if actual.estado == EstadoPeriodo.REGISTRADO:
            raise SireBusinessException(
                f"El periodo {periodo} ya está registrado: el 5.15 no sirve aquí. "
                f"Usa «eliminar preliminar registrado» (5.36).",
                business_rule="rvie_usar_5_36",
                details={"estado_actual": actual.estado.value},
            )

        token = await self.auth_service.obtener_token_valido(ruc)

        try:
            await self.api_client.rvie_eliminar_reemplazo(token, per_tributario=periodo)
        except SunatValidationException as e:
            codigos = {str(err.get("cod")) for err in e.errors}

            if ErrorNegocioRvie.SIN_REEMPLAZO_QUE_ELIMINAR in codigos:
                # SUNAT dice que el periodo sigue en propuesta: nuestro estado
                # local iba por delante. Se corrige en vez de fallar.
                logger.info(
                    f"[RVIE] SUNAT dice que {ruc}/{periodo} sigue en propuesta; "
                    f"se reconcilia el estado local"
                )
                return await self.periodos.registrar_transicion(
                    ruc, periodo, EstadoPeriodo.PROPUESTA,
                    operacion="5.15 eliminar reemplazo (SUNAT ya estaba en propuesta)",
                    detalle=str(e),
                )

            if ErrorNegocioRvie.EN_PRELIMINAR_REGISTRADO in codigos:
                raise SireBusinessException(
                    f"SUNAT informa que el periodo {periodo} está en preliminar registrado: "
                    f"usa «eliminar preliminar registrado» (5.36). {e}",
                    business_rule="rvie_usar_5_36",
                    details={"errores_sunat": e.errors},
                )

            raise

        return await self.periodos.registrar_transicion(
            ruc, periodo, EstadoPeriodo.PROPUESTA,
            operacion="5.15 eliminar reemplazo",
        )

    async def consultar_preliminares_registrados(
        self, ruc: str, per_ini: str, per_fin: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        5.37 Consultar los preliminares registrados.

        Es quien da el `id` que necesita el 5.36 para eliminar un preliminar ya
        registrado; sin esta consulta, esa operación no se puede componer.
        """
        self._validar_periodo(per_ini)

        token = await self.auth_service.obtener_token_valido(ruc)
        datos = await self.api_client.get_json(
            ep_rvie.consultar_preliminares_registrados(),
            token,
            params={
                "page": 1,
                "perPage": 20,
                "perIni": per_ini,
                "perFin": per_fin or per_ini,
            },
        )

        if isinstance(datos, list):
            return datos
        return datos.get("registros", []) if isinstance(datos, dict) else []

    async def eliminar_preliminar_registrado(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        5.36 Eliminar un preliminar **ya registrado**.

        Compone 5.37 y 5.36: primero se busca el `id` del registro y después se
        elimina. Sin ese id SUNAT no sabe qué borrar.
        """
        self._validar_periodo(periodo)

        actual = await self.periodos.obtener_o_crear(ruc, periodo)
        if actual.estado != EstadoPeriodo.REGISTRADO:
            raise SireBusinessException(
                f"El periodo {periodo} está en {actual.estado.value}: no hay preliminar "
                f"registrado que eliminar. Para deshacer un reemplazo usa el 5.15.",
                business_rule="rvie_sin_preliminar_registrado",
                details={"estado_actual": actual.estado.value},
            )

        registros = await self.consultar_preliminares_registrados(ruc, periodo)
        registro = next(
            (r for r in registros if str(r.get("perTributario")) == periodo), None
        )

        if not registro or not registro.get("id"):
            raise SireApiException(
                f"SUNAT no devolvió ningún preliminar registrado para {periodo}, así que "
                f"no hay identificador con el que eliminarlo (servicio 5.37)."
            )

        token = await self.auth_service.obtener_token_valido(ruc)

        await self.api_client.put_json(
            ep_rvie.eliminar_preliminar_registrado(periodo),
            token,
            data={"id": registro["id"], "codTipoRegistro": 14},
            params={"codLibro": CodLibro.RVIE},
        )

        return await self.periodos.registrar_transicion(
            ruc, periodo, EstadoPeriodo.PROPUESTA,
            operacion="5.36 eliminar preliminar registrado",
            detalle=f"id {registro['id']}",
        )
