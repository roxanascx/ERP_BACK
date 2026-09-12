"""
Asientos automáticos "cargo/abono" del Plan de Cuentas.

Cuando una cuenta tiene configurada `cuenta_cargo_destino`/`cuenta_abono_destino`
(ver `app/models/plan_contable.py`, sección "Cuentas autogeneradas de forma
automática" del CONPCC02 de referencia), cualquier movimiento contra ella debe
generar además, en el mismo momento, una línea espejo en cada una de esas
cuentas por el mismo importe: la de cargo al debe, la de abono al haber.

Esta es la pieza compartida que consulta cada punto que escribe asientos
(hoy: `LibroDiarioService.agregar_asiento`, el único conectado). No dispara en
cascada sobre las cuentas destino -si 201 o 611 tuvieran a su vez su propio
cargo/abono, no se encadena- para no arriesgar un ciclo si dos cuentas
terminan apuntándose entre sí.
"""

from typing import Any, Dict, List

from app.modules.accounting.plan_contable_repository import AccountingRepository


async def lineas_automaticas_por_destino(
    plan_contable_repo: AccountingRepository,
    codigo_cuenta: str,
    monto: float,
) -> List[Dict[str, Any]]:
    """
    Las líneas espejo que corresponde generar al postear `monto` en
    `codigo_cuenta`, según su configuración de cuentas autogeneradas.

    Devuelve como mucho 2 líneas ({cuentaContable, debe, haber}); una lista
    vacía si la cuenta no tiene nada configurado o si `monto` no es positivo.
    """
    if monto <= 0:
        return []

    cuentas = await plan_contable_repo.list_cuentas({"codigo": codigo_cuenta}, limit=1)
    if not cuentas:
        return []

    cuenta = cuentas[0]
    lineas: List[Dict[str, Any]] = []

    cargo = cuenta.get("cuenta_cargo_destino")
    if cargo and cargo.get("codigo"):
        lineas.append({"cuentaContable": cargo, "debe": monto, "haber": 0.0})

    abono = cuenta.get("cuenta_abono_destino")
    if abono and abono.get("codigo"):
        lineas.append({"cuentaContable": abono, "debe": 0.0, "haber": monto})

    return lineas
