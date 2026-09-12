"""
Importación de las compras de SIRE al registro de compras de contabilidad.

Espejo de `importacion_sire_service` (ventas), con una diferencia que condiciona
todo lo demás: **RCE no devuelve JSON**.

En ventas, SUNAT expone un endpoint que responde los comprobantes al momento. En
compras hay que pasar por el ciclo asíncrono del manual —5.34 pide la propuesta
y devuelve un `numTicket`, se sondea con 5.31, se descarga con 5.32 y lo que
llega es un ZIP con un TXT—. `SunatApiClient.descargar_propuesta` resuelve esos
siete pasos, y `utils/propuesta_rce` convierte el TXT en comprobantes. Aquí solo
se traduce al modelo de contabilidad y se guarda.

Consecuencia práctica: importar compras **tarda**, porque hay que esperar a que
SUNAT genere el archivo. La pantalla tiene que contarlo.

Como en ventas, esto no toca el libro diario: crea los registros de compra y
nada más. El asiento se genera en un paso aparte y reversible.
"""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...sire.services.api_client import SunatApiClient
from ...sire.services.auth_service import SireAuthService
from ...sire.services.sunat_endpoints import CodTipoArchivo
from ...socios_negocio.repositories import SocioNegocioRepository
from ...socios_negocio.sincronizacion_sire import SincronizacionSociosSireService
from ...sire.utils.propuesta_rce import parsear_propuesta
from .subdiario_service import SubdiarioService

logger = logging.getLogger(__name__)

#: Tipos de documento de identidad que admite el PLE 080000. La propuesta trae
#: el código en una columna propia, pero no siempre: cuando falta se deduce del
#: largo del número, y si tampoco cuadra se guarda como «sin documento» en vez
#: de dejar pasar un valor que luego impide leer el registro.
TIPOS_DOC_VALIDOS = {"0", "1", "4", "6", "7", "11", "A"}
DOC_SIN_IDENTIFICAR = "0"
DOC_RUC = "6"
DOC_DNI = "1"

#: De estos campos sale el asiento contable. Si uno cambia en un comprobante ya
#: contabilizado, el asiento del libro quedaría desfasado.
CAMPOS_DEL_ASIENTO = ("importe_total", "igv")

#: Estado con el que SUNAT marca un comprobante anulado en la propuesta.
ESTADOS_ANULADOS = {"2", "9"}


def _decimal(valor: Any) -> Decimal:
    """A Decimal, tolerando None, texto y enteros."""
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _fecha_iso(valor: Any) -> Optional[str]:
    """
    Pasar la fecha de SUNAT (`31/07/2026`) al ISO que guarda contabilidad.

    Devuelve None si no hay fecha: el esquema de compras declara las fechas como
    `date`, y una cadena vacía ahí no valida.
    """
    texto = str(valor or "").strip()
    if not texto:
        return None

    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue

    logger.warning(f"[IMPORTACION COMPRAS] fecha no reconocida: {texto!r}")
    return None


def _tipo_documento(valor: Any, numero: Any = None) -> str:
    """
    Normalizar el tipo de documento del proveedor al dominio del PLE.

    La columna puede venir vacía en versiones antiguas de la propuesta, así que
    se deduce del número: 11 dígitos es RUC y 8 es DNI. Es la misma regla que
    aplica SUNAT y evita que el comprobante quede sin tipo.
    """
    codigo = str(valor or "").strip()
    if codigo in TIPOS_DOC_VALIDOS:
        return codigo

    digitos = "".join(c for c in str(numero or "") if c.isdigit())
    if len(digitos) == 11:
        return DOC_RUC
    if len(digitos) == 8:
        return DOC_DNI

    return DOC_SIN_IDENTIFICAR


class ImportacionSireComprasService:
    """Trae los comprobantes de compra de SUNAT al registro de compras."""

    def __init__(
        self,
        database: AsyncIOMotorDatabase,
        api_client: Optional[SunatApiClient] = None,
        auth_service: Optional[SireAuthService] = None,
    ):
        self.db = database
        self.collection = database.registro_compras
        self.api_client = api_client
        self.auth_service = auth_service
        self.subdiarios = SubdiarioService(database)
        self.socios_sync = SincronizacionSociosSireService(SocioNegocioRepository(database))

    # ------------------------------------------------------------------
    # Lectura desde SUNAT
    # ------------------------------------------------------------------

    async def obtener_de_sunat(self, ruc: str, periodo: str) -> List[Dict[str, Any]]:
        """
        Los comprobantes de la propuesta del periodo.

        Esto es lo que tarda: `descargar_propuesta` pide el archivo, espera a que
        SUNAT lo genere y lo descarga. No hay paginación porque el archivo viene
        entero.
        """
        token = await self.auth_service.obtener_token_valido(ruc)

        resultado = await self.api_client.descargar_propuesta(
            token,
            per_tributario=periodo,
            cod_tipo_archivo=CodTipoArchivo.TXT,
        )

        if not resultado.archivos:
            logger.warning(
                f"[IMPORTACION COMPRAS] SUNAT terminó el proceso de {ruc}/{periodo} "
                f"sin devolver archivo (ticket {resultado.num_ticket})"
            )
            return []

        comprobantes, meta = parsear_propuesta(resultado.texto, periodo)

        if meta.get("campos_ausentes"):
            # No es fatal —esos campos quedan en cero— pero sí es la señal de que
            # SUNAT cambió los rótulos y hay que revisar el mapa de columnas.
            logger.warning(
                f"[IMPORTACION COMPRAS] columnas no encontradas en la propuesta "
                f"de {periodo}: {meta['campos_ausentes']}"
            )

        logger.info(f"[IMPORTACION COMPRAS] {len(comprobantes)} comprobantes de {ruc}/{periodo}")
        return comprobantes

    # ------------------------------------------------------------------
    # Traducción al modelo de contabilidad
    # ------------------------------------------------------------------

    @staticmethod
    def a_registro_compra(comprobante: Dict[str, Any], periodo: str) -> Dict[str, Any]:
        """
        Traducir un comprobante de la propuesta al registro de compra.

        Los nombres de las columnas se mapean uno a uno con los campos del PLE
        080000, así que no se pierde ningún importe.

        La propuesta da las adquisiciones no gravadas como **un solo número**
        («Valor Adq. NG»), igual que las pide el PLE. Por eso va directo a
        `base_imponible_no_gravada` y no se reparte entre exonerada e inafecta:
        ese desglose no está en el archivo y repartirlo sería inventarlo.
        """
        numero_doc = str(comprobante.get("ruc_proveedor") or "").strip()

        return {
            # Proveedor
            "tipo_documento_proveedor": _tipo_documento(
                comprobante.get("tipo_doc_identidad"), numero_doc
            ),
            "numero_documento_proveedor": numero_doc or "-",
            "razon_social_proveedor": (
                comprobante.get("razon_social_proveedor") or "SIN IDENTIFICAR"
            ),
            # Comprobante
            "tipo_comprobante": str(comprobante.get("tipo_documento") or ""),
            "serie_comprobante": comprobante.get("serie_comprobante") or "",
            "numero_comprobante": str(comprobante.get("numero_comprobante") or ""),
            "numero_final_rango": comprobante.get("numero_final_rango") or None,
            "fecha_comprobante": _fecha_iso(comprobante.get("fecha_emision")),
            "fecha_vencimiento": _fecha_iso(comprobante.get("fecha_vencimiento")),
            "anio_emision_dua_dsi": comprobante.get("anio_emision_dua_dsi") or None,
            # Importes (PLE 080000)
            "base_imponible_gravada": _decimal(comprobante.get("base_imponible_gravada")),
            "igv": _decimal(comprobante.get("igv")),
            "base_imponible_no_gravada": _decimal(
                comprobante.get("valor_adquisicion_no_gravada")
            ),
            "isc": _decimal(comprobante.get("isc")),
            "icbper": _decimal(comprobante.get("icbper")),
            "otros_tributos": _decimal(comprobante.get("otros_tributos")),
            "importe_total": _decimal(comprobante.get("importe_total")),
            # Moneda
            "moneda": comprobante.get("moneda") or "PEN",
            "tipo_cambio": _decimal(comprobante.get("tipo_cambio") or 1),
            # Detracción y retención
            "numero_constancia_detraccion": (
                comprobante.get("numero_constancia_detraccion") or None
            ),
            "fecha_emision_detraccion": _fecha_iso(
                comprobante.get("fecha_emision_detraccion")
            ),
            "marca_comprobante_retencion": (
                comprobante.get("marca_comprobante_retencion") or None
            ),
            "clasificacion_bienes_servicios": (
                comprobante.get("clasificacion_bienes_servicios") or "1"
            ),
            "identificacion_contrato": comprobante.get("identificacion_contrato") or None,
            "indicador_error": comprobante.get("indicador_error") or "0",
            "estado_operacion": str(comprobante.get("estado") or "1"),
            # Trazabilidad
            "periodo": periodo,
            "origen": "SIRE",
            "car_sunat": comprobante.get("car_sunat") or None,
        }

    @staticmethod
    def clave(registro: Dict[str, Any]) -> tuple:
        """
        Identidad de un comprobante de compra.

        El proveedor entra en la clave, a diferencia de ventas: dos proveedores
        distintos pueden emitir la misma serie y número, y sin el RUC sus
        comprobantes se pisarían entre sí.
        """
        return (
            str(registro.get("tipo_comprobante") or ""),
            str(registro.get("numero_documento_proveedor") or ""),
            str(registro.get("serie_comprobante") or ""),
            str(registro.get("numero_comprobante") or ""),
            str(registro.get("periodo") or ""),
        )

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------

    async def _clasificar(self, ruc: str, registros: List[Dict[str, Any]]) -> None:
        """
        Asignar a cada comprobante el subdiario que le toca.

        Se cachea por naturaleza: todos los comprobantes gravados de un periodo
        van al mismo subdiario, así que no tiene sentido consultarlo una vez por
        comprobante.
        """
        cache: Dict[str, Optional[Dict[str, Any]]] = {}

        for r in registros:
            importes = {
                "base_gravada": r.get("base_imponible_gravada"),
                "no_gravada": r.get("base_imponible_no_gravada"),
            }
            naturaleza = self.subdiarios.deducir_naturaleza_compra(importes)

            if naturaleza.value not in cache:
                cache[naturaleza.value] = await self.subdiarios.subdiario_para_compra(
                    ruc, importes
                )

            subdiario = cache[naturaleza.value]
            r["naturaleza_compra"] = naturaleza.value
            r["subdiario"] = subdiario["codigo"] if subdiario else None
            r["subdiario_nombre"] = subdiario["nombre"] if subdiario else None
            r["subdiario_listo"] = bool(subdiario and subdiario.get("listo"))

    async def _existentes(self, empresa_id: str, periodo: str) -> Dict[tuple, Dict[str, Any]]:
        """Lo que ya hay guardado del periodo, indexado por su identidad."""
        cursor = self.collection.find({"empresa_id": empresa_id, "periodo": periodo})
        return {self.clave(doc): doc async for doc in cursor}

    @staticmethod
    def _ya_contabilizado(previo: Optional[Dict[str, Any]]) -> bool:
        """Si el comprobante ya generó su asiento en el libro diario."""
        return bool(previo and previo.get("lote_contabilizacion"))

    @staticmethod
    def _cambia_el_asiento(previo: Dict[str, Any], nuevo: Dict[str, Any]) -> bool:
        """
        Si los datos nuevos harían un asiento distinto al que ya está en el libro.

        Solo miran los campos de los que sale el asiento: que cambie la razón
        social del proveedor es irrelevante, que cambie el importe no.
        """
        for campo in CAMPOS_DEL_ASIENTO:
            anterior = float(previo.get(campo) or 0)
            actual = float(nuevo.get(campo) or 0)
            # Se redondea antes de comparar: sin esto una diferencia de un
            # céntimo justo se pierde en el float y no se detecta.
            if round(abs(anterior - actual), 2) >= 0.01:
                return True

        return str(previo.get("estado_operacion") or "1") != str(
            nuevo.get("estado_operacion") or "1"
        )

    # ------------------------------------------------------------------
    # Previsualizar e importar
    # ------------------------------------------------------------------

    async def previsualizar(self, ruc: str, periodo: str) -> Dict[str, Any]:
        """
        Qué pasaría al importar, sin escribir nada.

        Distingue los que se crearían, los que se actualizarían, los capturados a
        mano —que no se tocan sin avisar— y los que ya tienen asiento y cambiaron
        de importe, que se bloquean.
        """
        comprobantes = await self.obtener_de_sunat(ruc, periodo)
        registros = [self.a_registro_compra(c, periodo) for c in comprobantes]
        await self._clasificar(ruc, registros)

        existentes = await self._existentes(ruc, periodo)

        nuevos, actualizables, manuales, contabilizados = [], [], [], []
        for r in registros:
            previo = existentes.get(self.clave(r))
            if previo is None:
                nuevos.append(r)
            elif self._ya_contabilizado(previo) and self._cambia_el_asiento(previo, r):
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
            "igv_total": sum((r["igv"] for r in registros), Decimal("0")),
            "por_subdiario": sorted(por_subdiario.values(), key=lambda x: x["codigo"]),
            "sin_subdiario": sum(1 for r in registros if not r.get("subdiario")),
            "detalle_manuales": [
                {
                    "tipo": r["tipo_comprobante"],
                    "serie": r["serie_comprobante"],
                    "numero": r["numero_comprobante"],
                    "proveedor": r["razon_social_proveedor"],
                }
                for r in manuales
            ],
        }

    async def importar(
        self, ruc: str, periodo: str, sobrescribir_manuales: bool = False
    ) -> Dict[str, Any]:
        """
        Traer los comprobantes al registro de compras.

        Es idempotente: reimportar el mismo periodo actualiza los que ya vinieron
        de SIRE en vez de duplicarlos. Los capturados a mano se respetan salvo
        que se pida lo contrario, y los que ya tienen asiento no se tocan.
        """
        comprobantes = await self.obtener_de_sunat(ruc, periodo)
        registros = [self.a_registro_compra(c, periodo) for c in comprobantes]
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
            # asiento del libro dejaría de corresponder con la compra y nadie se
            # enteraría. Hay que deshacer el lote primero.
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
            # Ni los Decimal ni las fechas en texto viajan bien a Mongo: los
            # importes se guardan como float y las fechas como datetime, que es
            # lo que ya hace el resto del módulo.
            documento = self._a_documento(documento)

            if previo is None:
                documento["fecha_creacion"] = ahora
                await self.collection.insert_one(documento)
                creados += 1
            else:
                await self.collection.update_one(
                    {"_id": previo["_id"]}, {"$set": documento}
                )
                actualizados += 1

            # El proveedor del comprobante se sincroniza como Socio de
            # Negocio: ver el mismo bloque en `importacion_sire_service.py`
            # (ventas) para el porqué.
            await self.socios_sync.sincronizar_uno(
                ruc,
                r.get("tipo_documento_proveedor"),
                r.get("numero_documento_proveedor"),
                r.get("razon_social_proveedor"),
                "proveedor",
            )

        if bloqueados:
            logger.warning(
                f"[IMPORTACION COMPRAS] {ruc}/{periodo}: {len(bloqueados)} comprobantes "
                f"no se actualizaron por estar ya contabilizados"
            )

        logger.info(
            f"[IMPORTACION COMPRAS] {ruc}/{periodo}: {creados} creados, "
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

    @staticmethod
    def _a_documento(datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deja el dict listo para Mongo.

        El driver no sabe codificar `Decimal` y aborta la escritura entera; las
        fechas viajan como texto ISO desde el parser y hay que convertirlas a
        `datetime` para poder filtrar por rango después.
        """
        listo: Dict[str, Any] = {}

        for campo, valor in datos.items():
            if isinstance(valor, Decimal):
                listo[campo] = float(valor)
            elif campo.startswith("fecha_") and isinstance(valor, str) and valor:
                try:
                    listo[campo] = datetime.strptime(valor, "%Y-%m-%d")
                except ValueError:
                    listo[campo] = valor
            else:
                listo[campo] = valor

        return listo
