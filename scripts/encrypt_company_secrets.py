"""
Migración: cifra los secretos en texto plano de la colección `companies`.

Hasta la Fase 00 las claves SOL, los `client_secret` de SIRE y las demás claves
de cada empresa se guardaban legibles en MongoDB. Este script los cifra con la
clave de `SIRE_ENCRYPTION_KEY`.

Es idempotente: los valores que ya llevan el prefijo `enc:v1:` se saltan, así que
puede ejecutarse las veces que haga falta.

Uso:
    python scripts/encrypt_company_secrets.py           # simulacro, no escribe
    python scripts/encrypt_company_secrets.py --apply   # aplica los cambios
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Permitir ejecutar el script directamente desde back/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.crypto import (  # noqa: E402
    SECRET_FIELDS,
    encrypt_secret,
    encryption_available,
    is_encrypted,
)
from app.database import get_database  # noqa: E402


async def migrar(aplicar: bool) -> int:
    if not encryption_available():
        print(
            "ERROR: no hay SIRE_ENCRYPTION_KEY configurada en el .env.\n"
            "Genera una con:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
        return 1

    db = get_database()
    total_empresas = 0
    total_campos = 0
    empresas_tocadas = 0

    async for empresa in db.companies.find({}):
        total_empresas += 1
        ruc = empresa.get("ruc", "<sin ruc>")

        cambios = {}
        for campo in SECRET_FIELDS:
            valor = empresa.get(campo)
            if valor and isinstance(valor, str) and not is_encrypted(valor):
                cambios[campo] = encrypt_secret(valor)

        if not cambios:
            continue

        empresas_tocadas += 1
        total_campos += len(cambios)
        print(f"  {ruc}: {', '.join(sorted(cambios))}")

        if aplicar:
            await db.companies.update_one({"_id": empresa["_id"]}, {"$set": cambios})

    print()
    print(f"Empresas revisadas : {total_empresas}")
    print(f"Empresas afectadas : {empresas_tocadas}")
    print(f"Campos a cifrar    : {total_campos}")

    if not aplicar and total_campos:
        print("\nSimulacro: no se escribió nada. Repite con --apply para aplicarlo.")
    elif aplicar and total_campos:
        print("\nHecho. Los secretos quedaron cifrados en MongoDB.")
    elif not total_campos:
        print("\nNo hay nada que migrar: todos los secretos ya estaban cifrados.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los cambios. Sin este flag solo muestra qué se cifraría.",
    )
    args = parser.parse_args()

    modo = "APLICANDO CAMBIOS" if args.apply else "SIMULACRO (no escribe)"
    print(f"Cifrado de secretos de `companies` — {modo}\n")

    return asyncio.run(migrar(args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
