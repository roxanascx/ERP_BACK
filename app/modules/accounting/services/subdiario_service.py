"""
Servicio de subdiarios contables.

Además del mantenimiento, aquí vive la regla que hace posible la
contabilización automática: **deducir el subdiario de venta a partir de los
importes del comprobante**. Es lo que evita que alguien tenga que clasificar a
mano los comprobantes que llegan de SIRE.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..repositories.subdiario_repository import SubdiarioRepository
from ..schemas.schemas_subdiario import (
    NaturalezaCompra,
    NaturalezaVenta,
    SubdiarioBase,
    SubdiarioCreate,
    SubdiarioUpdate,
)
from .catalogo_subdiarios import (
    CATALOGO_ESTANDAR,
    NATURALEZA_COMPRA_POR_SUBDIARIO,
    NATURALEZA_POR_SUBDIARIO,
)

logger = logging.getLogger(__name__)


class SubdiarioNoEncontrado(Exception):
    """El subdiario pedido no existe para esa empresa."""


class SubdiarioDuplicado(Exception):
    """Ya hay un subdiario con ese código en la empresa."""


def _a_decimal(valor: Any) -> Decimal:
    """Convertir a Decimal tolerando None, texto y números."""
    if valor is None or valor == "":
        return Decimal("0")
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal("0")


class SubdiarioService:
    """Mantenimiento del catálogo y clasificación de comprobantes."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.repo = SubdiarioRepository(database)

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------

    async def listar(
        self,
        empresa_id: str,
        solo_activos: bool = False,
        tipo: Optional[str] = None,
        sembrar_si_vacio: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Subdiarios de la empresa.

        La primera vez se siembra el catálogo estándar: entrar en la pantalla y
        encontrarla vacía obligaría a teclear cuarenta filas antes de poder
        hacer nada.
        """
        await self.repo.asegurar_indices()

        if sembrar_si_vacio and await self.repo.contar(empresa_id) == 0:
            creados = await self.repo.sembrar(empresa_id, CATALOGO_ESTANDAR)
            logger.info(f"[SUBDIARIOS] Sembrados {creados} subdiarios para {empresa_id}")

        return [self._enriquecer(d) for d in await self.repo.listar(empresa_id, solo_activos, tipo)]

    async def obtener(self, empresa_id: str, codigo: str) -> Dict[str, Any]:
        doc = await self.repo.obtener(empresa_id, codigo)
        if not doc:
            raise SubdiarioNoEncontrado(
                f"No existe el subdiario {codigo} en la empresa {empresa_id}"
            )
        return self._enriquecer(doc)

    async def crear(
        self, empresa_id: str, datos: SubdiarioCreate, usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        await self.repo.asegurar_indices()

        if await self.repo.obtener(empresa_id, datos.codigo):
            raise SubdiarioDuplicado(
                f"Ya existe el subdiario {datos.codigo} en esta empresa"
            )

        doc = await self.repo.crear(empresa_id, datos.model_dump(mode="json"), usuario)
        return self._enriquecer(doc)

    async def actualizar(
        self,
        empresa_id: str,
        codigo: str,
        cambios: SubdiarioUpdate,
        usuario: Optional[str] = None,
    ) -> Dict[str, Any]:
        # `exclude_unset` es lo que permite modificar un solo campo sin borrar
        # el resto con los valores por defecto del esquema.
        datos = cambios.model_dump(mode="json", exclude_unset=True)

        doc = await self.repo.actualizar(empresa_id, codigo, datos, usuario)
        if not doc:
            raise SubdiarioNoEncontrado(
                f"No existe el subdiario {codigo} en la empresa {empresa_id}"
            )
        return self._enriquecer(doc)

    async def eliminar(self, empresa_id: str, codigo: str) -> bool:
        if not await self.repo.eliminar(empresa_id, codigo):
            raise SubdiarioNoEncontrado(
                f"No existe el subdiario {codigo} en la empresa {empresa_id}"
            )
        return True

    async def restaurar_catalogo(self, empresa_id: str) -> int:
        """
        Volver a sembrar los subdiarios estándar que falten.

        No toca los que ya existen: sirve para recuperar los que se borraron
        sin perder la configuración de cuentas del resto.
        """
        await self.repo.asegurar_indices()
        return await self.repo.sembrar(empresa_id, CATALOGO_ESTANDAR)

    # ------------------------------------------------------------------
    # Clasificación: de los importes al subdiario
    # ------------------------------------------------------------------

    @staticmethod
    def deducir_naturaleza(importes: Dict[str, Any]) -> NaturalezaVenta:
        """
        Qué naturaleza tributaria tiene una venta, mirando sus importes.

        Es la regla que permite clasificar sola la propuesta de SIRE. Se decide
        por cuántas bases distintas trae el comprobante: si hay más de una, es
        mixto; si solo hay una, esa manda.

        Claves esperadas (las que da SUNAT): `exportacion`, `base_gravada`,
        `exonerado`, `inafecto`, `igv`.
        """
        exportacion = _a_decimal(importes.get("exportacion"))
        gravada = _a_decimal(importes.get("base_gravada"))
        exonerado = _a_decimal(importes.get("exonerado"))
        inafecto = _a_decimal(importes.get("inafecto"))

        presentes = [
            (exportacion > 0, NaturalezaVenta.EXPORTACION),
            (gravada > 0, NaturalezaVenta.GRAVADA),
            (exonerado > 0, NaturalezaVenta.EXONERADA),
            (inafecto > 0, NaturalezaVenta.INAFECTA),
        ]
        con_importe = [naturaleza for hay, naturaleza in presentes if hay]

        if len(con_importe) > 1:
            return NaturalezaVenta.MIXTO

        if con_importe:
            return con_importe[0]

        # Un comprobante sin ninguna base (por ejemplo, anulado en cero) se
        # trata como gravado: es el caso general y deja el asiento en cero,
        # que es visible y corregible.
        return NaturalezaVenta.GRAVADA

    @staticmethod
    def deducir_naturaleza_compra(importes: Dict[str, Any]) -> NaturalezaCompra:
        """
        Qué naturaleza tributaria tiene una compra, mirando sus importes.

        Espejo de `deducir_naturaleza`, con una diferencia importante: de las
        seis naturalezas de compra solo tres se pueden deducir de los
        importes. Las otras tres dependen de algo que el comprobante no dice:

        - IMPORTACION lo delata el tipo de documento (DUA/DSI), no el importe.
        - GRAVADA_Y_NO_GRAVADA es un **destino** (a qué ventas se aplicó la
          compra) y solo lo sabe el usuario.
        - SIN_DERECHO_CREDITO también es criterio del usuario.

        Por eso esta función nunca las devuelve: quien quiera esos subdiarios
        tiene que asignarlos a mano. Inventarlos aquí imputaría mal el crédito
        fiscal, que es justo lo que no se puede equivocar.

        Claves esperadas: `base_gravada`, `no_gravada`.
        """
        gravada = _a_decimal(importes.get("base_gravada"))
        no_gravada = _a_decimal(importes.get("no_gravada"))

        if gravada > 0 and no_gravada > 0:
            return NaturalezaCompra.MIXTA

        if no_gravada > 0:
            return NaturalezaCompra.NO_GRAVADA

        # Igual que en ventas, un comprobante sin ninguna base se trata como
        # gravado: deja el asiento en cero, que se ve y se corrige.
        return NaturalezaCompra.GRAVADA

    async def subdiario_para_compra(
        self, empresa_id: str, importes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        El subdiario que le corresponde a un comprobante de compra.

        Igual que en ventas: busca por naturaleza entre los subdiarios de
        compra de la empresa, respetando los códigos que ella haya definido,
        y solo si no encuentra ninguno cae al código estándar.
        """
        naturaleza = self.deducir_naturaleza_compra(importes)

        de_compra = await self.repo.listar(empresa_id, solo_activos=True, tipo="compras")

        for doc in de_compra:
            if doc.get("naturaleza_compra") == naturaleza.value:
                return self._enriquecer(doc)

        codigo = NATURALEZA_COMPRA_POR_SUBDIARIO.get(naturaleza)
        if codigo:
            try:
                return await self.obtener(empresa_id, codigo)
            except Exception:
                return None

        return None

    async def subdiario_para_venta(
        self, empresa_id: str, importes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        El subdiario que le corresponde a un comprobante de venta.

        Busca por naturaleza entre los subdiarios de venta de la empresa, así
        que respeta los códigos que cada una haya definido en vez de dar por
        supuesto el catálogo estándar.
        """
        naturaleza = self.deducir_naturaleza(importes)

        de_venta = await self.repo.listar(empresa_id, solo_activos=True, tipo="ventas")

        for doc in de_venta:
            if doc.get("naturaleza") == naturaleza.value:
                return self._enriquecer(doc)

        # Si la empresa no tiene un subdiario para esa naturaleza, se cae al
        # código estándar por si existe con otra marca.
        codigo = NATURALEZA_POR_SUBDIARIO.get(naturaleza)
        if codigo:
            doc = await self.repo.obtener(empresa_id, codigo)
            if doc:
                return self._enriquecer(doc)

        return None

    async def diagnostico_compras(self, empresa_id: str) -> Dict[str, Any]:
        """Qué falta para poder contabilizar compras. Espejo del de ventas."""
        de_compra = await self.listar(empresa_id, solo_activos=True, tipo="compras")

        pendientes = [
            {
                "codigo": d["codigo"],
                "nombre": d["nombre"],
                "naturaleza": d.get("naturaleza_compra"),
                "falta": self._que_falta(d),
            }
            for d in de_compra
            if not d.get("listo")
        ]

        return {
            "total_subdiarios_compra": len(de_compra),
            "listos": len(de_compra) - len(pendientes),
            "pendientes": pendientes,
            "puede_contabilizar": len(pendientes) < len(de_compra),
        }

    async def diagnostico_ventas(self, empresa_id: str) -> Dict[str, Any]:
        """
        Qué falta para poder contabilizar ventas.

        La pantalla de configuración la usa para decir, en una línea, si el
        módulo está listo o qué subdiarios tienen cuentas sin poner.
        """
        de_venta = await self.listar(empresa_id, solo_activos=True, tipo="ventas")

        pendientes = [
            {
                "codigo": d["codigo"],
                "nombre": d["nombre"],
                "naturaleza": d.get("naturaleza"),
                "falta": self._que_falta(d),
            }
            for d in de_venta
            if not d.get("listo")
        ]

        return {
            "total_subdiarios_venta": len(de_venta),
            "listos": len(de_venta) - len(pendientes),
            "pendientes": pendientes,
            "puede_contabilizar": len(pendientes) < len(de_venta) and len(de_venta) > 0,
        }

    # ------------------------------------------------------------------
    # Ayudas
    # ------------------------------------------------------------------

    @staticmethod
    def _que_falta(doc: Dict[str, Any]) -> List[str]:
        """Qué cuentas hay que completar para que el subdiario sea utilizable."""
        if doc.get("asiento_compras"):
            return SubdiarioService._que_falta_compras(doc)

        cuentas = doc.get("cuentas") or {}
        falta = []

        if not cuentas.get("cuenta_cobro"):
            falta.append("cuenta de cobro (12)")
        if not cuentas.get("cuenta_ingreso"):
            falta.append("cuenta de ingreso (70)")

        naturaleza = doc.get("naturaleza")
        lleva_igv = naturaleza in (
            NaturalezaVenta.GRAVADA.value,
            NaturalezaVenta.GRAVADA_IGV_10.value,
            NaturalezaVenta.MIXTO.value,
        )
        if lleva_igv and not cuentas.get("cuenta_igv"):
            falta.append("cuenta de IGV (40)")

        return falta

    @staticmethod
    def _que_falta_compras(doc: Dict[str, Any]) -> List[str]:
        """Lo mismo para un subdiario de compra."""
        cuentas = doc.get("cuentas") or {}
        falta = []

        if not cuentas.get("cuenta_gasto"):
            falta.append("cuenta de gasto (60 o 63)")
        if not cuentas.get("cuenta_pago"):
            falta.append("cuenta por pagar (42)")

        # SIN_DERECHO_CREDITO y NO_GRAVADA no llevan cuenta de IGV: en la
        # primera el IGV se suma al gasto y en la segunda no hay IGV.
        lleva_igv = doc.get("naturaleza_compra") in (
            NaturalezaCompra.GRAVADA.value,
            NaturalezaCompra.GRAVADA_IGV_10.value,
            NaturalezaCompra.MIXTA.value,
            NaturalezaCompra.IMPORTACION.value,
            NaturalezaCompra.GRAVADA_Y_NO_GRAVADA.value,
        )
        if lleva_igv and not cuentas.get("cuenta_igv"):
            falta.append("cuenta de IGV crédito fiscal (40)")

        return falta

    @staticmethod
    def _enriquecer(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Añadir lo derivado: para qué sirve y si está listo para usarse."""
        try:
            modelo = SubdiarioBase(**{
                k: v for k, v in doc.items()
                if k in SubdiarioBase.model_fields
            })
            tipos = modelo.tipos_de_asiento()
            # Un subdiario puede servir a compras, a ventas o a ambos. Está
            # listo si lo está para alguno de los dos: preguntar solo por
            # ventas dejaba a los de compra marcados como pendientes para
            # siempre, aunque tuvieran todas sus cuentas.
            listo = (
                modelo.listo_para_contabilizar()
                or modelo.listo_para_contabilizar_compras()
            )
        except Exception:
            # Un documento antiguo o incompleto no debe romper el listado.
            tipos, listo = [], False

        return {**doc, "tipos": tipos, "listo": listo}
