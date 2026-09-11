"""
Rutas del módulo SIRE.

Este paquete no registra nada por su cuenta: el montaje real vive en
`app/core/router.py`, que importa cada router y le asigna su prefijo.

Antes había aquí una lista `sire_routers` con doce routers que **nadie
consumía**. Era un registro paralelo al de `core/router.py` y no coincidía con
él: mantenía vivos por importación dos routers que no estaban montados
(`diagnostico_routes` y `ticket_routes`), de modo que el grafo de imports los
daba por alcanzables aunque sus endpoints no existieran.
"""
