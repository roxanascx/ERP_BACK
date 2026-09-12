"""
Importación de las ventas de SIRE al registro de ventas de contabilidad.

Es el primero de los dos pasos del puente SIRE → contabilidad: aquí solo se
crean los registros de venta. El asiento del libro diario se genera después, en
un paso aparte y reversible, para poder revisar antes de tocar la contabilidad.

**De dónde salen los datos.** SUNAT expone
`/rvie/propuesta/web/propuesta/{periodo}/comprobantes`, que devuelve JSON
paginado con los campos uno a uno —y coinciden con los del PLE 140000—. No se
usa lo que hay guardado en `rvie_comprobantes` porque ese modelo descarta ISC,
IVAP, ICBPER, descuentos y exportación: importando desde ahí el PLE saldría
incompleto sin que nadie se diera cuenta.
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...sire.services.api_client import SunatApiClient
from ...sire.services.auth_service import SireAuthService
from ...sire.services.sunat_endpoints import API_SIRE
from ...socios_negocio.repositories import SocioNegocioRepository
from ...socios_negocio.sincronizacion_sire import SincronizacionSociosSireService
from .subdiario_service import SubdiarioService

logger = logging.getLogger(__name__)

#: Endpoint de comprobantes de la propuesta. Devuelve JSON paginado en vez de un
#: ticket, así que no hace falta el ciclo asíncrono del manual. No aparece en el
#: manual de Ventas v30, pero es el que usa el portal y el que ya funcionaba en
#: la pantalla de Ventas del ERP.
URL_COMPROBANTES = (
    f"{API_SIRE}/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta"
    "/{periodo}/comprobantes"
)

#: Cuántos comprobantes pedir por página.
POR_PAGINA = 100

#: Tope de páginas, por si la paginación de SUNAT no terminara nunca.
MAX_PAGINAS = 200

#: Tipos de documento de identidad que admite el PLE (`TipoDocumentoCliente`).
#: En las boletas al público SUNAT manda `-`, que no es ninguno de estos: se
#: normaliza a «sin documento» en vez de dejarlo pasar y que reviente al leerlo.
TIPOS_DOC_VALIDOS = {"0", "1", "4", "6", "7", "11", "A"}

# De estos campos sale el asiento contable. Si uno cambia en un comprobante
# que ya se contabilizó, el asiento del libro quedaría desfasado.
CAMPOS_DEL_ASIENTO = ("importe_total", "igv_ipm")
DOC_SIN_IDENTIFICAR = "0"


def _decimal(valor: Any) -> Decimal:
    """A Decimal, tolerando None, texto y enteros."""
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _tipo_documento(valor: Any) -> str:
    """
    Normalizar el tipo de documento del cliente al dominio del PLE.

    SUNAT usa `-` en las boletas sin identificar, y ese valor no existe en la
    tabla de tipos: guardarlo tal cual hace que el registro no se pueda ni leer
    después.
    """
    codigo = str(valor or "").strip()
    return codigo if codigo in TIPOS_DOC_VALIDOS else DOC_SIN_IDENTIFICAR


def _fecha_iso(valor: Any) -> str:
    """
    Pasar la fecha de SUNAT (`31/07/2026`) al ISO que guarda contabilidad.

    Si llega en otro formato se devuelve tal cual: mejor guardar lo que vino que
    inventarse una fecha.
    """
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return texto


class ImportacionSireService:
    """Trae los comprobantes de venta de SUNAT al registro de ventas."""

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        api_client: Optional[SunatApiClient] = None,
        auth_service: Optional[SireAuthService] = None,
    ):
        self.db = database
        self.collection = database.registro_ventas
        self.api_client = api_client
        self.auth_service = auth_service
        self.subdiarios = SubdiarioService(database)
        self.socios_sync = SincronizacionSociosSireService(SocioNegocioRepository(database))

    # ------------------------------------------------------------------
    # Lectura desde SUNAT
    # ------------------------------------------------------------------

    async def obtener_de_sunat(self, ruc: str, periodo: str) -> List[Dict[str, Any]]:
        """
        Todos los comprobantes de la propuesta del periodo.

        Recorre la paginación hasta agotarla. El tope de páginas es una red de
        seguridad: sin él, una respuesta que nunca marque el final dejaría el
        proceso dando vueltas.
        """
        token = await self.auth_service.obtener_token_valido(ruc)
        url = URL_COMPROBANTES.format(periodo=periodo)

        comprobantes: List[Dict[str, Any]] = []
        pagina = 1

        while pagina <= MAX_PAGINAS:
            datos = await self.api_client.get_json(
                url, token, params={"page": pagina, "perPage": POR_PAGINA}
            )

            registros = datos.get("registros") or []
            comprobantes.extend(registros)

            paginacion = datos.get("paginacion") or {}
            total = paginacion.get("totalRegistros")
            if len(registros) < POR_PAGINA or (total and len(comprobantes) >= total):
                break

            pagina += 1

        logger.info(f"[IMPORTACION] {len(comprobantes)} comprobantes de {ruc}/{periodo}")
        return comprobantes

    # ------------------------------------------------------------------
    # Traducción al modelo de contabilidad
    # ------------------------------------------------------------------

    @staticmethod
    def a_registro_venta(comprobante: Dict[str, Any], periodo: str) -> Dict[str, Any]:
        """
        Traducir un comprobante de SUNAT al registro de venta.

        Los nombres de SUNAT se mapean uno a uno con los campos del PLE 140000,
        así que no se pierde ningún importe. Los códigos de tipo de comprobante,
        documento de identidad y estado ya vienen en el mismo dominio que los
        enums de contabilidad.
        """
        return {
            # Cliente
            "tipo_documento_cliente": _tipo_documento(comprobante.get("codTipoDocIdentidad")),
            "numero_documento_cliente": str(comprobante.get("numDocIdentidad") or "-"),
            "razon_social_cliente": (
                comprobante.get("nomRazonSocialCliente") or "SIN IDENTIFICAR"
            ),
            # Comprobante
            "tipo_comprobante": str(comprobante.get("codTipoCDP") or ""),
            "serie_comprobante": comprobante.get("numSerieCDP") or "",
            "numero_comprobante": str(comprobante.get("numCDP") or ""),
            "fecha_emision": _fecha_iso(comprobante.get("fecEmision")),
            # Importes (PLE 140000)
            "valor_facturado_exportacion": _decimal(comprobante.get("mtoValFactExpo")),
            "base_imponible_gravada": _decimal(comprobante.get("mtoBIGravada")),
            "descuento_base_imponible": _decimal(comprobante.get("mtoDsctoBI")),
            "igv_ipm": _decimal(comprobante.get("mtoIGV")),
            "descuento_igv_ipm": _decimal(comprobante.get("mtoDsctoIGV")),
            "importe_exonerado": _decimal(comprobante.get("mtoExonerado")),
            "importe_inafecto": _decimal(comprobante.get("mtoInafecto")),
            "isc": _decimal(comprobante.get("mtoISC")),
            "base_imponible_ivap": _decimal(comprobante.get("mtoBIIvap")),
            "ivap": _decimal(comprobante.get("mtoIvap")),
            "icbper": _decimal(comprobante.get("mtoIcbp")),
            "otros_tributos_cargos": _decimal(comprobante.get("mtoOtrosTrib")),
            "importe_total": _decimal(comprobante.get("mtoTotalCP")),
            # Moneda
            "codigo_moneda": comprobante.get("codMoneda") or "PEN",
            "tipo_cambio": _decimal(comprobante.get("mtoTipoCambio") or 1),
            # Estado: SUNAT usa 1 ACTIVO, 8/9 anulado
            "estado_operacion": int(comprobante.get("codEstadoComprobante") or 1),
            # Trazabilidad
            "periodo": periodo,
            "origen": "SIRE",
            "car_sunat": comprobante.get("codCar"),
            "tipo_operacion_sunat": comprobante.get("indTipoOperacion"),
            "id_sunat": comprobante.get("id"),
        }

    @staticmethod
    def clave(registro: Dict[str, Any]) -> tuple:
        """
        Identidad de un comprobante dentro de un periodo.

        Es la misma con la que el registro de ventas impide duplicados, así que
        importar dos veces actualiza en vez de duplicar.
        """
        return (
            registro.get("tipo_comprobante"),
            registro.get("serie_comprobante"),
            registro.get("numero_comprobante"),
            registro.get("periodo"),
        )

    # ------------------------------------------------------------------
    # Previsualización e importación
    # ------------------------------------------------------------------

    async def _clasificar(self, ruc: str, registros: List[Dict[str, Any]]) -> None:
        """Asignar a cada registro su subdiario, según la naturaleza de sus importes."""
        cache: Dict[str, Optional[Dict[str, Any]]] = {}

        for r in registros:
            importes = {
                "exportacion": r["valor_facturado_exportacion"],
                "base_gravada": r["base_imponible_gravada"],
                "exonerado": r["importe_exonerado"],
                "inafecto": r["importe_inafecto"],
            }
            naturaleza = SubdiarioService.deducir_naturaleza(importes)

            if naturaleza.value not in cache:
                cache[naturaleza.value] = await self.subdiarios.subdiario_para_venta(
                    ruc, importes
                )

            subdiario = cache[naturaleza.value]
            r["naturaleza"] = naturaleza.value
            r["subdiario"] = subdiario["codigo"] if subdiario else None
            r["subdiario_nombre"] = subdiario["nombre"] if subdiario else None
            r["subdiario_listo"] = bool(subdiario and subdiario.get("listo"))

    async def _existentes(self, empresa_id: str, periodo: str) -> Dict[tuple, Dict[str, Any]]:
        """Lo que ya hay guardado del periodo, indexado por su identidad."""
        cursor = self.collection.find({"empresa_id": empresa_id, "periodo": periodo})
        return {
            self.clave(doc): doc
            async for doc in cursor
        }

    @staticmethod
    def _ya_contabilizado(previo: Optional[Dict[str, Any]]) -> bool:
        """Si el comprobante ya generó su asiento en el libro diario."""
        return bool(previo and previo.get("lote_contabilizacion"))

    @staticmethod
    def _cambia_el_asiento(previo: Dict[str, Any], nuevo: Dict[str, Any]) -> bool:
        """
        Si los datos nuevos harían un asiento distinto al que ya está en el
        libro. Solo miran los campos de los que sale el asiento: que cambie
        el nombre del cliente es irrelevante, que cambie el importe no.
        """
        for campo in CAMPOS_DEL_ASIENTO:
            anterior = float(previo.get(campo) or 0)
            actual = float(nuevo.get(campo) or 0)
            # Se redondea antes de comparar: sin esto una diferencia de un
            # céntimo justo (1180.01 - 1180.00) da 0.00999... y se escapa.
            if round(abs(anterior - actual), 2) >= 0.01:
                return True

        # 1 es el estado normal: un registro viejo sin el campo era normal, y
        # tratarlo como distinto bloquearía la reimportación sin motivo.
        return int(previo.get("estado_operacion") or 1) != int(
            nuevo.get("estado_operacion") or 1
        )

    async def previsualizar(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """
        Qué pasaría al importar, sin escribir nada.

        Distingue tres cosas: los que se crearían, los que ya están y se
        actualizarían, y los que existen pero fueron capturados a mano —esos no
        se tocan sin avisar—.
        """
        comprobantes = await self.obtener_de_sunat(ruc, periodo)
        registros = [self.a_registro_venta(c, periodo) for c in comprobantes]
        await self._clasificar(ruc, registros)

        existentes = await self._existentes(ruc, periodo)

        nuevos, actualizables, manuales, contabilizados = [], [], [], []
        for r in registros:
            previo = existentes.get(self.clave(r))
            if previo is None:
                nuevos.append(r)
            elif self._ya_contabilizado(previo) and self._cambia_el_asiento(previo, r):
                # Ya tiene asiento en el libro y los datos de SUNAT cambiaron:
                # sobrescribirlo dejaría el asiento contradiciendo a la venta.
                contabilizados.append({**r, "_lote": previo.get("lote_contabilizacion")})
            elif previo.get("origen") == "SIRE":
                actualizables.append(r)
            else:
                manuales.append(r)

        # Reparto por subdiario, que es lo que se revisa de un vistazo
        por_subdiario: Dict[str, Dict[str, Any]] = {}
        for r in registros:
            codigo = r.get("subdiario") or "sin asignar"
            entrada = por_subdiario.setdefault(codigo, {
                "codigo": codigo,
                "nombre": r.get("subdiario_nombre") or "Sin subdiario configurado",
                "listo": r.get("subdiario_listo", False),
                "comprobantes": 0,
                "importe": Decimal("0"),
            })
            entrada["comprobantes"] += 1
            entrada["importe"] += r["importe_total"]

        return {
            "ruc": ruc,
            "periodo": periodo,
            "total_sunat": len(registros),
            "nuevos": len(nuevos),
            "actualizables": len(actualizables),
            "capturados_a_mano": len(manuales),
            "bloqueados_por_contabilizados": len(contabilizados),
            "detalle_contabilizados": [
                {
                    "comprobante": f"{r['serie_comprobante']}-{r['numero_comprobante']}",
                    "lote": r.get("_lote"),
                }
                for r in contabilizados
            ],
            "importe_total": sum((r["importe_total"] for r in registros), Decimal("0")),
            "por_subdiario": sorted(por_subdiario.values(), key=lambda x: x["codigo"]),
            "sin_subdiario": sum(1 for r in registros if not r.get("subdiario")),
            "detalle_manuales": [
                {
                    "tipo": r["tipo_comprobante"],
                    "serie": r["serie_comprobante"],
                    "numero": r["numero_comprobante"],
                }
                for r in manuales
            ],
        }

    async def importar(
        self, ruc: str, periodo: str, sobrescribir_manuales: bool = False
    ) -> Dict[str, Any]:
        """
        Traer los comprobantes al registro de ventas.

        Es idempotente: reimportar el mismo periodo actualiza los que ya vinieron
        de SIRE en vez de duplicarlos. Los capturados a mano se respetan salvo
        que se pida lo contrario explícitamente.
        """
        comprobantes = await self.obtener_de_sunat(ruc, periodo)
        registros = [self.a_registro_venta(c, periodo) for c in comprobantes]
        await self._clasificar(ruc, registros)

        existentes = await self._existentes(ruc, periodo)

        creados = actualizados = respetados = 0
        bloqueados: List[Dict[str, Any]] = []
        ahora = datetime.utcnow()

        for r in registros:
            previo = existentes.get(self.clave(r))

            if previo is not None and previo.get("origen") != "SIRE" and not sobrescribir_manuales:
                respetados += 1
                continue

            # Si ya tiene asiento y SUNAT cambió el importe, no se toca: el
            # asiento del libro dejaría de corresponder con la venta y nadie
            # se enteraría. Hay que deshacer el lote primero.
            if self._ya_contabilizado(previo) and self._cambia_el_asiento(previo, r):
                bloqueados.append({
                    "comprobante": f"{r['serie_comprobante']}-{r['numero_comprobante']}",
                    "lote": previo.get("lote_contabilizacion"),
                })
                continue

            documento = {
                **r,
                "empresa_id": ruc,
                "fecha_actualizacion": ahora,
                "importado_en": ahora,
            }
            # Los Decimal no viajan a Mongo: se guardan como float, que es lo que
            # ya hace el resto del módulo de ventas.
            for campo, valor in list(documento.items()):
                if isinstance(valor, Decimal):
                    documento[campo] = float(valor)

            if previo is None:
                documento["fecha_creacion"] = ahora
                await self.collection.insert_one(documento)
                creados += 1
            else:
                await self.collection.update_one(
                    {"_id": previo["_id"]}, {"$set": documento}
                )
                actualizados += 1

            # El cliente del comprobante se sincroniza como Socio de Negocio:
            # si no existe se crea, y si existe se actualiza solo cuando el
            # dato nuevo es mejor (ver `SincronizacionSociosSireService`). Sin
            # esto, un RUC con facturas importadas podía no aparecer en
            # ningún buscador de socio (p.ej. al aplicar un pago en Caja/Bancos).
            await self.socios_sync.sincronizar_uno(
                ruc,
                r.get("tipo_documento_cliente"),
                r.get("numero_documento_cliente"),
                r.get("razon_social_cliente"),
                "cliente",
            )

        if bloqueados:
            logger.warning(
                f"[IMPORTACION] {ruc}/{periodo}: {len(bloqueados)} comprobantes "
                f"no se actualizaron por estar ya contabilizados"
            )

        logger.info(
            f"[IMPORTACION] {ruc}/{periodo}: {creados} creados, "
            f"{actualizados} actualizados, {respetados} respetados"
        )

        return {
            "ruc": ruc,
            "periodo": periodo,
            "creados": creados,
            "actualizados": actualizados,
            "respetados_por_ser_manuales": respetados,
            "bloqueados_por_contabilizados": len(bloqueados),
            "detalle_bloqueados": bloqueados,
            "total_procesados": len(registros),
        }
