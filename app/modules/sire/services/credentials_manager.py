"""
Gestor de credenciales SIRE
Resuelve las credenciales SUNAT de cada RUC desde MongoDB.
"""

from typing import Optional
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....core.crypto import decrypt_secret_fields
from ....database import get_database
from ..models.auth import SireCredentials

logger = logging.getLogger(__name__)

# Campos que la empresa debe tener completos para poder autenticarse con SUNAT.
REQUIRED_FIELDS = (
    "sunat_usuario",
    "sunat_clave",
    "sire_client_id",
    "sire_client_secret",
)


class SireCredentialsManager:
    """Gestor de credenciales SIRE por RUC desde MongoDB"""

    def __init__(self):
        """Inicializar gestor con acceso a MongoDB"""
        self.db: AsyncIOMotorDatabase = get_database()

    async def get_credentials(self, ruc: str) -> Optional[SireCredentials]:
        """
        Obtener las credenciales SIRE de un RUC.

        Args:
            ruc: RUC del contribuyente

        Returns:
            SireCredentials si la empresa existe, tiene SIRE activo y todas sus
            credenciales configuradas; None en cualquier otro caso.
        """
        try:
            empresa = await self.db.companies.find_one({"ruc": ruc})
        except Exception as exc:
            logger.error(f"[CREDENCIALES] Error consultando la empresa {ruc}: {exc}")
            return None

        if not empresa:
            logger.warning(f"[CREDENCIALES] No existe la empresa con RUC {ruc}")
            return None

        if not empresa.get("sire_activo"):
            logger.warning(f"[CREDENCIALES] La empresa {ruc} no tiene SIRE activo")
            return None

        # Los secretos se guardan cifrados; descifrarlos antes de usarlos.
        empresa = decrypt_secret_fields(empresa)

        faltantes = [campo for campo in REQUIRED_FIELDS if not empresa.get(campo)]
        if faltantes:
            logger.warning(
                f"[CREDENCIALES] A la empresa {ruc} le faltan credenciales: "
                f"{', '.join(faltantes)}"
            )
            return None

        return SireCredentials(
            ruc=ruc,
            sunat_usuario=empresa["sunat_usuario"],
            sunat_clave=empresa["sunat_clave"],
            client_id=empresa["sire_client_id"],
            client_secret=empresa["sire_client_secret"],
        )


# Instancia global del gestor
credentials_manager = SireCredentialsManager()
