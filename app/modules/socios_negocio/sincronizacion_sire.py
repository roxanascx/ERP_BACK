"""
Sincronización de Socios de Negocio desde los comprobantes que llegan de
SIRE (Compras/Ventas).

Antes de esto, un RUC podía tener facturas importadas en Registro de Compras
o Ventas sin que existiera ningún `SocioNegocioModel` para él — así que no
aparecía en ningún buscador de socio (p.ej. el de Caja/Bancos al aplicar un
pago). Este módulo crea o actualiza el socio a partir de cada comprobante,
igual que el usuario ya hace a mano en su software de referencia antes de
contabilizar.
"""

import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import SocioNegocioModel
from .repositories import SocioNegocioRepository
from .utils.ruc_validator import validar_documento

logger = logging.getLogger(__name__)

#: Mapeo de la Tabla 2 SUNAT (tipo de documento de identidad) al dominio de
#: `SocioNegocioModel.tipo_documento` ("RUC"/"DNI"/"CE"). Los códigos sin
#: equivalente (pasaporte, partida de nacimiento, cédula diplomática, sin
#: documento) se omiten a propósito: crear un socio con un tipo de documento
#: inventado produciría un registro que ni la propia pantalla de Socios de
#: Negocio sabría validar después.
_TIPO_DOCUMENTO_SUNAT = {
    "1": "DNI",
    "4": "CE",
    "6": "RUC",
}

PLACEHOLDER_RAZON_SOCIAL = "SIN IDENTIFICAR"


def _tipo_documento_valido(codigo_sunat: Any) -> Optional[str]:
    return _TIPO_DOCUMENTO_SUNAT.get(str(codigo_sunat or "").strip())


class SincronizacionSociosSireService:
    """Crea o actualiza un Socio de Negocio a partir de un comprobante SIRE."""

    def __init__(self, repository: SocioNegocioRepository):
        self.repository = repository

    async def sincronizar_uno(
        self,
        empresa_id: str,
        tipo_documento_sunat: Any,
        numero_documento: Any,
        razon_social: Any,
        tipo_socio: str,
    ) -> str:
        """
        Sincroniza un socio a partir de los datos de un comprobante.

        Devuelve `"creado"`, `"actualizado"` u `"omitido"`. Nunca lanza: un
        comprobante con datos raros (documento sin identificar, tipo que no
        mapea a RUC/DNI/CE) no debe tumbar la importación completa, solo
        quedarse sin sincronizar.
        """
        try:
            tipo_documento = _tipo_documento_valido(tipo_documento_sunat)
            numero_documento = str(numero_documento or "").strip()

            if not tipo_documento or not numero_documento or numero_documento == "-":
                return "omitido"

            es_valido, _ = validar_documento(tipo_documento, numero_documento)
            if not es_valido:
                return "omitido"

            razon_social = str(razon_social or "").strip() or PLACEHOLDER_RAZON_SOCIAL

            existente = await self.repository.get_by_documento(empresa_id, numero_documento)

            if existente is None:
                socio = SocioNegocioModel(
                    tipo_documento=tipo_documento,
                    numero_documento=numero_documento,
                    razon_social=razon_social,
                    tipo_socio=tipo_socio,
                    empresa_id=empresa_id,
                )
                await self.repository.create(socio)
                return "creado"

            cambios: Dict[str, Any] = {}

            # Solo se reemplaza la razón social si la nueva es mejor: nunca
            # se pisa un dato real con el placeholder, ni un dato con otro
            # distinto que también sea real (evita pisar una edición manual).
            razon_actual = (existente.razon_social or "").strip()
            if (
                razon_social != PLACEHOLDER_RAZON_SOCIAL
                and razon_social != razon_actual
                and (not razon_actual or razon_actual == PLACEHOLDER_RAZON_SOCIAL)
            ):
                cambios["razon_social"] = razon_social

            # Un socio que aparece como proveedor y como cliente pasa a
            # "ambos", sin perder la clasificación que ya tenía.
            if existente.tipo_socio != tipo_socio and existente.tipo_socio != "ambos":
                cambios["tipo_socio"] = "ambos"

            if not cambios:
                return "omitido"

            await self.repository.update(existente.id, cambios)
            return "actualizado"

        except Exception as e:
            logger.warning(
                f"[SYNC_SOCIOS] No se pudo sincronizar {numero_documento} ({tipo_socio}) "
                f"para {empresa_id}: {e}"
            )
            return "omitido"

    async def sincronizar_backfill(
        self, empresa_id: str, database: AsyncIOMotorDatabase
    ) -> Dict[str, int]:
        """
        Recorre TODO Registro de Compras y Ventas de la empresa y sincroniza
        sus proveedores/clientes. Pensado para correrse una sola vez sobre
        datos ya importados; las próximas importaciones se sincronizan solas
        (ver `ImportacionSireService`/`ImportacionSireComprasService`).
        """
        totales = {"creados": 0, "actualizados": 0, "omitidos": 0}
        etiqueta_a_clave = {"creado": "creados", "actualizado": "actualizados", "omitido": "omitidos"}

        fuentes = (
            (database.registro_compras, "tipo_documento_proveedor", "numero_documento_proveedor",
             "razon_social_proveedor", "proveedor"),
            (database.registro_ventas, "tipo_documento_cliente", "numero_documento_cliente",
             "razon_social_cliente", "cliente"),
        )

        for coleccion, campo_tipo, campo_numero, campo_razon, tipo_socio in fuentes:
            vistos = set()
            cursor = coleccion.find(
                {"empresa_id": empresa_id},
                {campo_tipo: 1, campo_numero: 1, campo_razon: 1},
            )
            async for doc in cursor:
                clave = (doc.get(campo_tipo), doc.get(campo_numero))
                if clave in vistos:
                    continue
                vistos.add(clave)

                resultado = await self.sincronizar_uno(
                    empresa_id,
                    doc.get(campo_tipo),
                    doc.get(campo_numero),
                    doc.get(campo_razon),
                    tipo_socio,
                )
                totales[etiqueta_a_clave[resultado]] += 1

        return totales
