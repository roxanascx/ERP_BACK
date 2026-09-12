"""
Cifrado simétrico de secretos almacenados en MongoDB.

Las claves SOL y los `client_secret` de SIRE se guardaban en texto plano en la
colección `companies`. Este módulo los cifra con Fernet (AES-128-CBC + HMAC)
usando la clave de `SIRE_ENCRYPTION_KEY`.

Los valores cifrados llevan el prefijo `enc:v1:`, lo que permite tres cosas:
distinguir un secreto cifrado de uno heredado en texto plano, migrar la base sin
downtime, y versionar el esquema si en el futuro se rota el algoritmo.
"""

from typing import Optional
import logging

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

logger = logging.getLogger(__name__)

# Marca de los valores cifrados. Todo lo que no la lleve se considera un secreto
# heredado en texto plano, pendiente de migrar.
ENCRYPTION_PREFIX = "enc:v1:"

# Campos de la colección `companies` que contienen secretos.
SECRET_FIELDS = (
    "sire_client_secret",
    "sunat_clave",
    "sunat_clave_secundaria",
    "banco_clave",
    "pdt_clave",
    "plame_clave",
)

_fernet_instance: Optional[Fernet] = None


class EncryptionKeyMissing(RuntimeError):
    """No hay SIRE_ENCRYPTION_KEY configurada y se intentó cifrar un secreto."""

    def __init__(self) -> None:
        super().__init__(
            "SIRE_ENCRYPTION_KEY no está configurada. Genera una clave con:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"\n'
            "y añádela al archivo .env como SIRE_ENCRYPTION_KEY=<clave>.\n"
            "Guarda una copia: sin esa clave los secretos ya cifrados son "
            "irrecuperables."
        )


def _get_fernet() -> Fernet:
    """Instancia Fernet cacheada, construida a partir de la clave del entorno."""
    global _fernet_instance

    if _fernet_instance is None:
        key = (settings.SIRE_ENCRYPTION_KEY or "").strip()
        if not key:
            raise EncryptionKeyMissing()
        try:
            _fernet_instance = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                "SIRE_ENCRYPTION_KEY no es una clave Fernet válida "
                "(debe ser base64 url-safe de 32 bytes). Genera una nueva con "
                "Fernet.generate_key()."
            ) from exc

    return _fernet_instance


def encryption_available() -> bool:
    """Indica si hay una clave de cifrado utilizable, sin lanzar excepción."""
    try:
        _get_fernet()
        return True
    except Exception:
        return False


def is_encrypted(value: Optional[str]) -> bool:
    """True si el valor ya está cifrado por este módulo."""
    return isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX)


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """
    Cifra un secreto. Los valores vacíos y los ya cifrados se devuelven intactos,
    de modo que la operación es idempotente y puede aplicarse a cualquier
    documento sin comprobar antes su estado.
    """
    if not value:
        return value

    if is_encrypted(value):
        return value

    token = _get_fernet().encrypt(value.encode())
    return ENCRYPTION_PREFIX + token.decode()


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    """
    Descifra un secreto.

    Un valor sin el prefijo es un secreto heredado en texto plano: se devuelve
    tal cual para que la aplicación siga funcionando mientras no se ejecute la
    migración `scripts/encrypt_company_secrets.py`.
    """
    if not value:
        return value

    if not is_encrypted(value):
        return value

    token = value[len(ENCRYPTION_PREFIX):]
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError(
            "No se pudo descifrar un secreto: la SIRE_ENCRYPTION_KEY actual no "
            "corresponde con la que se usó para cifrarlo."
        ) from exc


def encrypt_secret_fields(data: dict) -> dict:
    """Cifra, sobre una copia, los campos secretos presentes en el diccionario."""
    result = dict(data)
    for field in SECRET_FIELDS:
        if field in result:
            result[field] = encrypt_secret(result[field])
    return result


def decrypt_secret_fields(data: dict) -> dict:
    """Descifra, sobre una copia, los campos secretos presentes en el diccionario."""
    result = dict(data)
    for field in SECRET_FIELDS:
        if field in result:
            result[field] = decrypt_secret(result[field])
    return result
