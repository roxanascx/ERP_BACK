"""
Ciclo de vida de un periodo RCE.

Implementa la secuencia mínima del manual (§3.1): aceptar la propuesta (5.2) y
registrar el preliminar (5.4), más la consulta de periodos habilitados (5.33) y
la marcha atrás (5.17).

Antes de esta fase el módulo solo sabía *leer* de SUNAT. Aquí es donde empieza a
escribir, así que cada operación valida primero contra la máquina de estados:
si la transición no es legal no se gasta una petición en SUNAT.
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
from ..repositories.rce_periodo_repository import RcePeriodoRepository
from ..utils.exceptions import (
    SireApiException,
    SireBusinessException,
    SireValidationException,
    SunatValidationException,
)
from .api_client import SunatApiClient
from .auth_service import SireAuthService
from ..utils.resumen import parsear_resumen
from .sunat_endpoints import (
    COD_SIN_COMPROBANTES,
    CodLibro,
    CodTipoResumen,
    IndEliminarPreliminar,
)

logger = logging.getLogger(__name__)


#: Códigos que el manual v22 añadió al servicio 5.4. Los devuelve SUNAT cuando
#: el periodo está más avanzado de lo que creíamos, casi siempre porque alguien
#: operó desde el portal web sin pasar por aquí.
COD_YA_EN_PRELIMINAR = "1008"
COD_YA_GENERADO = "1009"


class RceCicloService:
    """Operaciones que hacen avanzar (o retroceder) un periodo RCE."""

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
        mes = int(periodo[4:])
        if not 1 <= mes <= 12:
            raise SireValidationException(
                f"El periodo '{periodo}' tiene un mes fuera de rango",
                field="periodo",
                value=periodo,
            )

    async def consultar_periodos_habilitados(self, ruc: str) -> List[Dict[str, Any]]:
        """
        5.33 Periodos que SUNAT tiene habilitados para este contribuyente.

        Es la primera llamada del ciclo: evita ofrecer en pantalla meses que
        SUNAT va a rechazar. Antes se consultaba con `codLibro=140000`, que es
        el de ventas.
        """
        token = await self.auth_service.obtener_token_valido(ruc)
        datos = await self.api_client.periodos_habilitados(token, cod_libro=CodLibro.RCE)

        return self._aplanar_periodos(datos, ruc)

    @staticmethod
    def _aplanar_periodos(datos: Any, ruc: str) -> List[Dict[str, Any]]:
        """
        Aplanar la respuesta del 5.33 a una lista de periodos.

        SUNAT los devuelve agrupados por ejercicio:
            [{"numEjercicio": "2026", "lisPeriodos": [
                {"perTributario": "202609", "codEstado": "03",
                 "desEstado": "No Presentado"}, ...]}]

        La UI necesita una lista plana y ordenada del más reciente al más
        antiguo, que es como se eligen los periodos en pantalla.
        """
        if isinstance(datos, dict):
            for clave in ("registros", "periodos", "data"):
                if isinstance(datos.get(clave), list):
                    datos = datos[clave]
                    break

        if not isinstance(datos, list):
            logger.warning(f"[RCE] 5.33 devolvió una forma inesperada para {ruc}: {type(datos)}")
            return []

        planos: List[Dict[str, Any]] = []
        for ejercicio in datos:
            if not isinstance(ejercicio, dict):
                continue

            sub = ejercicio.get("lisPeriodos")
            if not isinstance(sub, list):
                # Algún ejercicio puede venir ya como periodo suelto.
                if ejercicio.get("perTributario"):
                    planos.append(dict(ejercicio))
                continue

            for periodo in sub:
                if not isinstance(periodo, dict):
                    continue
                planos.append({
                    "perTributario": periodo.get("perTributario"),
                    "codEstado": periodo.get("codEstado"),
                    "desEstado": periodo.get("desEstado"),
                    "numEjercicio": ejercicio.get("numEjercicio"),
                })

        return sorted(planos, key=lambda p: p.get("perTributario") or "", reverse=True)

    async def obtener_resumen_propuesta(self, ruc: str, periodo: str) -> dict:
        """
        5.35 Resumen de la propuesta: cuántos comprobantes y por cuánto.

        Es lo que hay que poder enseñar antes de aceptar: sin esto, el usuario
        confirma una escritura en SUNAT sin saber qué está aceptando.
        """
        self._validar_periodo(periodo)
        token = await self.auth_service.obtener_token_valido(ruc)

        try:
            contenido = await self.api_client.descargar_resumen(
                token, per_tributario=periodo, cod_tipo_resumen=CodTipoResumen.PROPUESTA
            )
        except SunatValidationException as e:
            if COD_SIN_COMPROBANTES in {str(err.get("cod")) for err in e.errors}:
                # No es un fallo: SUNAT dice que el periodo no tiene comprobantes,
                # asi que todavia no hay propuesta que aceptar.
                return {**parsear_resumen(""), "sin_datos": True, "motivo": str(e)}
            raise

        return {**parsear_resumen(contenido), "sin_datos": False}

    async def obtener_estado(self, ruc: str, periodo: str) -> PeriodoRce:
        """Estado local del periodo, con las operaciones que admite ahora mismo."""
        self._validar_periodo(periodo)
        return await self.periodos.obtener_o_crear(ruc, periodo)

    async def consultar_estado_en_sunat(self, ruc: str, periodo: str) -> Optional[Dict[str, Any]]:
        """
        Qué dice SUNAT del periodo, según el 5.33.

        El estado local solo conoce las operaciones hechas desde aquí; si
        alguien trabajó en el portal web, SUNAT sabe más que nosotros. Devolver
        ambas versiones deja la discrepancia a la vista en lugar de dejar que el
        usuario la descubra con un error a mitad del ciclo.
        """
        self._validar_periodo(periodo)
        try:
            for candidato in await self.consultar_periodos_habilitados(ruc):
                if candidato.get("perTributario") == periodo:
                    return candidato
        except SireApiException as e:
            # No poder preguntar a SUNAT no debe impedir leer el estado local.
            logger.warning(f"[RCE] No se pudo consultar el estado de {ruc}/{periodo} en SUNAT: {e}")
        return None

    async def listar_estados(self, ruc: str, limite: int = 24) -> List[PeriodoRce]:
        """Periodos sobre los que ya se ha operado."""
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
                business_rule="transicion_periodo_rce",
                details={
                    "estado_actual": actual.estado.value,
                    "estado_solicitado": destino.value,
                    "operaciones_disponibles": disponibles,
                },
            )

        return actual

    #: `desEstado` del 5.33 que significa que el periodo sigue abierto. Cualquier
    #: otro valor quiere decir que SUNAT ya lo dio por presentado.
    ESTADO_SUNAT_ABIERTO = "No Presentado"

    async def _exigir_periodo_abierto_en_sunat(self, ruc: str, periodo: str) -> None:
        """
        Negarse a escribir sobre un periodo que SUNAT ya da por presentado.

        El estado local solo sabe de lo hecho desde el ERP. Si alguien cerró el
        periodo desde el portal SOL, aceptar la propuesta no tiene sentido y
        SUNAT lo rechazaría de todas formas; mejor no gastar la llamada y
        explicar por qué.
        """
        en_sunat = await self.consultar_estado_en_sunat(ruc, periodo)

        if en_sunat is None:
            # No se pudo preguntar (SUNAT caído, rate limit). No se bloquea por
            # ello: el propio servicio rechazará la operación si no procede.
            return

        des_estado = (en_sunat.get("desEstado") or "").strip()
        if des_estado and des_estado != self.ESTADO_SUNAT_ABIERTO:
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
        5.2 Aceptar la propuesta de SUNAT: el libro pasa a preliminar.

        Es uno de los dos caminos hacia el preliminar; el otro es reemplazar la
        propuesta con un archivo propio (5.3), que necesita la carga TUS.

        Antes de escribir se comprueba contra SUNAT que el periodo siga abierto.
        """
        self._validar_periodo(periodo)
        await self._exigir_transicion(ruc, periodo, EstadoPeriodo.PRELIMINAR)
        await self._exigir_periodo_abierto_en_sunat(ruc, periodo)

        token = await self.auth_service.obtener_token_valido(ruc)
        resultado = await self.api_client.aceptar_propuesta(token, per_tributario=periodo)

        return await self.periodos.registrar_transicion(
            ruc,
            periodo,
            EstadoPeriodo.PRELIMINAR,
            operacion="5.2 aceptar propuesta",
            num_ticket=resultado.num_ticket,
            detalle=resultado.descripcion,
        )

    async def registrar_preliminar(self, ruc: str, periodo: str) -> PeriodoRce:
        """
        5.4 Registrar el preliminar. Último paso del ciclo por API.

        Si SUNAT contesta 1008 o 1009 es que el periodo ya estaba más avanzado
        —normalmente porque se operó desde el portal web—, así que en vez de
        propagar el error se reconcilia el estado local con la realidad.
        """
        self._validar_periodo(periodo)
        await self._exigir_transicion(ruc, periodo, EstadoPeriodo.REGISTRADO)

        token = await self.auth_service.obtener_token_valido(ruc)

        try:
            resultado = await self.api_client.registrar_preliminar(token, per_tributario=periodo)
        except SunatValidationException as e:
            codigos = {str(err.get("cod")) for err in e.errors}

            if COD_YA_GENERADO in codigos:
                logger.info(
                    f"[RCE] SUNAT informa que {ruc}/{periodo} ya estaba generado; "
                    f"se reconcilia el estado local a REGISTRADO"
                )
                return await self.periodos.registrar_transicion(
                    ruc, periodo, EstadoPeriodo.REGISTRADO,
                    operacion="5.4 registrar preliminar (ya registrado en SUNAT)",
                    detalle=str(e),
                )

            if COD_YA_EN_PRELIMINAR in codigos:
                raise SireBusinessException(
                    f"SUNAT informa que el periodo {periodo} ya está en preliminar: {e}",
                    business_rule="preliminar_ya_registrado",
                    details={"errores_sunat": e.errors},
                )

            raise

        return await self.periodos.registrar_transicion(
            ruc,
            periodo,
            EstadoPeriodo.REGISTRADO,
            operacion="5.4 registrar preliminar",
            num_ticket=resultado.num_ticket,
            detalle=resultado.descripcion,
        )

    # ------------------------------------------------------------------
    # Marcha atrás
    # ------------------------------------------------------------------

    async def eliminar_preliminar(
        self,
        ruc: str,
        periodo: str,
        solo_no_domiciliados: bool = False,
    ) -> PeriodoRce:
        """
        5.17 Eliminar el preliminar. Es la única marcha atrás que da el API.

        Con `solo_no_domiciliados` se borra únicamente esa parte y el periodo se
        queda donde está; en otro caso vuelve a propuesta.
        """
        self._validar_periodo(periodo)

        ind = (
            IndEliminarPreliminar.SOLO_NO_DOMICILIADOS
            if solo_no_domiciliados
            else IndEliminarPreliminar.TODO
        )

        actual = await self.periodos.obtener_o_crear(ruc, periodo)

        if actual.estado == EstadoPeriodo.PROPUESTA and not solo_no_domiciliados:
            raise SireBusinessException(
                f"El periodo {periodo} está en propuesta: no hay preliminar que eliminar",
                business_rule="sin_preliminar_que_eliminar",
                details={"estado_actual": actual.estado.value},
            )

        token = await self.auth_service.obtener_token_valido(ruc)
        await self.api_client.eliminar_preliminar(token, per_tributario=periodo, ind_eliminar=ind)

        if solo_no_domiciliados:
            # El libro no cambia de fase; solo se registra la operación.
            return await self.periodos.registrar_transicion(
                ruc, periodo, actual.estado,
                operacion="5.17 eliminar preliminar (solo no domiciliados)",
            )

        return await self.periodos.registrar_transicion(
            ruc, periodo, EstadoPeriodo.PROPUESTA,
            operacion="5.17 eliminar preliminar",
        )
