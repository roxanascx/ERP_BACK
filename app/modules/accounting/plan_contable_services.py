"""Servicios del módulo Contabilidad
Implementación ligera que adapta partes del prototipo PlanContableService.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.modules.accounting.plan_contable_repository import AccountingRepository
from app.models.plan_contable import (
    CuentaContableCreate,
    CuentaContableUpdate,
    CuentaContableResponse,
    EstadisticasPlanContable,
    ClaseContable,
)


def _calcular_nivel_y_clase(codigo: str) -> "tuple[int, int]":
    """
    Nivel y clase se deducen de la longitud/primer dígito del código, nunca de
    lo que mande el cliente: el backend es la única fuente de verdad, porque
    antes solo lo calculaba el frontend (`CuentaModal.tsx`) y cualquiera podía
    mandar un `nivel`/`clase_contable` inconsistente con el código.
    """
    codigo = (codigo or "").strip()
    nivel = min(len(codigo), 9) if codigo else 1
    clase_contable = int(codigo[0]) if codigo and codigo[0].isdigit() else 1
    return nivel, clase_contable


def _validar_flags_cuenta(datos: Dict[str, Any]) -> None:
    """
    Reglas de negocio sobre los flags nuevos de Centro de Costos y Caja/Bancos.

    Solo una cuenta hoja que acepta movimiento puede exigir centro de costo o
    representar una caja/banco, y una cuenta de caja/banco solo tiene sentido
    en la clase 1 (Activo) del PCGE, donde vive "Efectivo y equivalentes".
    """
    acepta_movimiento = datos.get("acepta_movimiento", True)
    clase_contable = datos.get("clase_contable")

    if datos.get("requiere_centro_costo") and not acepta_movimiento:
        raise ValueError(
            "Solo una cuenta que acepta movimiento puede requerir centro de costo"
        )
    if (datos.get("es_cuenta_caja") or datos.get("es_cuenta_bancaria")) and not acepta_movimiento:
        raise ValueError(
            "Solo una cuenta que acepta movimiento puede ser cuenta de caja o bancaria"
        )
    if (datos.get("es_cuenta_caja") or datos.get("es_cuenta_bancaria")) and clase_contable != 1:
        raise ValueError(
            "Solo las cuentas de la clase 1 (Activo) pueden ser cuenta de caja o bancaria"
        )


class PlanContableServiceAdapter:
    def __init__(self, repository: Optional[AccountingRepository] = None):
        self.repo = repository or AccountingRepository()

    async def list_cuentas(self, activos_solo: bool = True, clase_contable: Optional[int] = None, nivel: Optional[int] = None, empresa_id: str = None, tipo_plan: str = "estandar") -> List[CuentaContableResponse]:
        filtros = {}
        if activos_solo:
            filtros["activa"] = True
        if clase_contable:
            filtros["clase_contable"] = clase_contable
        if nivel:
            filtros["nivel"] = nivel
            
        # Filtros para empresa y tipo de plan
        if empresa_id and tipo_plan == "personalizado":
            filtros["empresa_id"] = empresa_id
            filtros["tipo_plan"] = "personalizado"
        else:
            # Plan estándar: sin empresa_id o tipo_plan = "estandar"
            filtros["$or"] = [
                {"tipo_plan": "estandar"},
                {"empresa_id": {"$exists": False}},
                {"empresa_id": None}
            ]

        docs = await self.repo.list_cuentas(filtros)
        return [self._doc_to_response(d) for d in docs]

    async def get_cuenta(self, codigo: str) -> Optional[CuentaContableResponse]:
        doc = await self.repo.find_by_codigo(codigo)
        if not doc:
            return None
        return self._doc_to_response(doc)

    async def crear_cuenta(self, payload: CuentaContableCreate) -> CuentaContableResponse:
        # Validaciones básicas
        existe = await self.repo.find_by_codigo(payload.codigo)
        if existe:
            raise ValueError(f"Ya existe una cuenta con el código {payload.codigo}")

        documento = payload.dict()
        nivel, clase_contable = _calcular_nivel_y_clase(payload.codigo)
        documento["nivel"] = nivel
        documento["clase_contable"] = clase_contable
        documento["fecha_creacion"] = datetime.now()
        documento["naturaleza"] = self._determinar_naturaleza(clase_contable)
        _validar_flags_cuenta(documento)

        result = await self.repo.insert_cuenta(documento)
        created = await self.repo.find_by_codigo(documento["codigo"])
        return self._doc_to_response(created)

    async def obtener_estructura_jerarquica(self, empresa_id: str = None, tipo_plan: str = "estandar") -> Dict[str, Any]:
        # Filtros para empresa y tipo de plan (sin restringir nivel: se trae todo el plan de una vez)
        filtros = {"activa": True}

        if empresa_id and tipo_plan == "personalizado":
            filtros["empresa_id"] = empresa_id
            filtros["tipo_plan"] = "personalizado"
        else:
            # Plan estándar: sin empresa_id o tipo_plan = "estandar"
            filtros["$or"] = [
                {"tipo_plan": "estandar"},
                {"empresa_id": {"$exists": False}},
                {"empresa_id": None}
            ]

        # Una sola consulta a Mongo y armado del árbol en memoria.
        # Antes se hacía una consulta por cada nodo del árbol (recursiva), lo que con
        # Mongo local pasaba desapercibido pero con MongoDB Atlas (latencia de red por
        # consulta) hacía que este endpoint tardara minutos con un plan de ~3000 cuentas.
        todas = await self.repo.list_cuentas(filtros)

        por_codigo = {cuenta["codigo"]: cuenta for cuenta in todas}
        hijos_por_padre: Dict[str, List[Dict[str, Any]]] = {}
        for cuenta in todas:
            codigo = cuenta["codigo"]
            if len(codigo) <= 1:
                continue
            codigo_padre = codigo[:-1]
            if codigo_padre in por_codigo:
                hijos_por_padre.setdefault(codigo_padre, []).append(cuenta)

        def construir_hijos(codigo_padre: str) -> List[Dict[str, Any]]:
            hijos = sorted(hijos_por_padre.get(codigo_padre, []), key=lambda c: c["codigo"])
            return [
                {
                    "codigo": hijo["codigo"],
                    "descripcion": hijo["descripcion"],
                    "nivel": hijo["nivel"],
                    "es_hoja": hijo.get("es_hoja", True),
                    "hijos": construir_hijos(hijo["codigo"]),
                }
                for hijo in hijos
            ]

        clases = sorted((c for c in todas if c["nivel"] == 1), key=lambda c: c["codigo"])
        estructura = [
            {
                "codigo": clase["codigo"],
                "descripcion": clase["descripcion"],
                "nivel": clase["nivel"],
                "hijos": construir_hijos(clase["codigo"]),
            }
            for clase in clases
        ]

        return {"estructura": estructura, "total_clases": len(estructura)}

    async def obtener_estadisticas(self) -> EstadisticasPlanContable:
        total = await self.repo.count_documents({})
        activas = await self.repo.count_documents({"activa": True})
        inactivas = total - activas

        pipeline_clase = [
            {"$match": {"activa": True}},
            {"$group": {"_id": "$clase_contable", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        stats_clase = await self.repo.aggregate(pipeline_clase)
        descripciones = {1: "ACTIVO", 2: "ACTIVO REALIZABLE", 3: "ACTIVO INMOVILIZADO", 4: "PASIVO", 5: "PATRIMONIO", 6: "GASTOS", 7: "VENTAS", 8: "SALDOS", 9: "ANALITICA"}
        por_clase = [ClaseContable(clase=s["_id"], descripcion=descripciones.get(s["_id"], str(s["_id"])), total_cuentas=s["total"]) for s in stats_clase]

        pipeline_nivel = [
            {"$match": {"activa": True}},
            {"$group": {"_id": "$nivel", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        stats_nivel = await self.repo.aggregate(pipeline_nivel)
        por_nivel = [{"nivel": s["_id"], "nombre": f"Nivel {s['_id']}", "descripcion": "", "total_cuentas": s["total"]} for s in stats_nivel]

        return EstadisticasPlanContable(total_cuentas=total, cuentas_activas=activas, cuentas_inactivas=inactivas, por_clase=por_clase, por_nivel=por_nivel)

    async def actualizar_cuenta(self, codigo: str, payload: CuentaContableUpdate) -> Optional[CuentaContableResponse]:
        """Actualizar una cuenta contable"""
        # Verificar que la cuenta existe
        cuenta_existente = await self.repo.find_by_codigo(codigo)
        if not cuenta_existente:
            raise ValueError(f"No existe una cuenta con el código {codigo}")

        # Preparar datos de actualización (solo lo que el cliente mandó)
        update_data = payload.dict(exclude_none=True)
        update_data["fecha_modificacion"] = datetime.now()

        # Validar los flags nuevos contra el estado resultante (existente + cambios)
        _validar_flags_cuenta({**cuenta_existente, **update_data})

        # Actualizar
        result = await self.repo.update_cuenta(codigo, update_data)
        
        if result.modified_count > 0:
            cuenta_actualizada = await self.repo.find_by_codigo(codigo)
            return self._doc_to_response(cuenta_actualizada)
        
        return None

    async def eliminar_cuenta(self, codigo: str) -> bool:
        """Eliminar una cuenta contable (soft delete)"""
        # Verificar que la cuenta existe
        cuenta_existente = await self.repo.find_by_codigo(codigo)
        if not cuenta_existente:
            raise ValueError(f"No existe una cuenta con el código {codigo}")
        
        # Verificar que no tiene cuentas hijas activas
        tiene_hijos = await self.repo.list_cuentas({
            "cuenta_padre": codigo,
            "activa": True
        })
        
        if tiene_hijos:
            raise ValueError(f"No se puede eliminar la cuenta {codigo} porque tiene cuentas hijas activas")
        
        # Soft delete
        result = await self.repo.update_cuenta(codigo, {"activa": False, "fecha_modificacion": datetime.now()})
        
        return result.modified_count > 0

    def _determinar_naturaleza(self, clase_contable: int) -> str:
        clases_deudoras = [1, 2, 3, 6, 8, 9]
        clases_acreedoras = [4, 5, 7]
        if clase_contable in clases_deudoras:
            return "DEUDORA"
        if clase_contable in clases_acreedoras:
            return "ACREEDORA"
        return "DEUDORA"

    def _doc_to_response(self, documento: Dict[str, Any]) -> CuentaContableResponse:
        return CuentaContableResponse(
            id=str(documento.get("_id") or documento.get("id")),
            codigo=documento.get("codigo"),
            descripcion=documento.get("descripcion"),
            nivel=documento.get("nivel"),
            clase_contable=documento.get("clase_contable"),
            grupo=documento.get("grupo"),
            subgrupo=documento.get("subgrupo"),
            cuenta_padre=documento.get("cuenta_padre"),
            es_hoja=documento.get("es_hoja", True),
            acepta_movimiento=documento.get("acepta_movimiento", True),
            naturaleza=documento.get("naturaleza", "DEUDORA"),
            moneda=documento.get("moneda", "MN"),
            activa=documento.get("activa", True),
            tipo_plan=documento.get("tipo_plan", "estandar"),
            empresa_id=documento.get("empresa_id"),
            archivo_origen=documento.get("archivo_origen"),
            requiere_centro_costo=documento.get("requiere_centro_costo", False),
            es_cuenta_caja=documento.get("es_cuenta_caja", False),
            es_cuenta_bancaria=documento.get("es_cuenta_bancaria", False),
            fecha_creacion=documento.get("fecha_creacion"),
            fecha_modificacion=documento.get("fecha_modificacion"),
        )


class AccountingService:
    def __init__(self):
        self.plan_service = PlanContableServiceAdapter()

    async def get_plan_estructura(self, empresa_id: str = None, tipo_plan: str = "estandar") -> Dict[str, Any]:
        """Obtiene la estructura jerárquica del plan contable, filtrado por empresa y tipo"""
        return await self.plan_service.obtener_estructura_jerarquica(empresa_id, tipo_plan)

    async def list_cuentas(self, activos_solo: bool = True, empresa_id: str = None, tipo_plan: str = "estandar"):
        """Lista cuentas filtradas por empresa y tipo de plan"""
        return await self.plan_service.list_cuentas(activos_solo, empresa_id=empresa_id, tipo_plan=tipo_plan)

    async def list_cuentas_filtradas(
        self, 
        activos_solo: bool = True,
        clase_contable: Optional[int] = None,
        nivel: Optional[int] = None,
        busqueda: Optional[str] = None,
        limit: Optional[int] = None,
        empresa_id: str = None,
        tipo_plan: str = "estandar"
    ):
        """Método optimizado para obtener cuentas con filtros múltiples"""
        filtros = {}
        
        if activos_solo:
            filtros["activa"] = True
        if clase_contable:
            filtros["clase_contable"] = clase_contable
        if nivel:
            filtros["nivel"] = nivel
            
        # Filtros para empresa y tipo de plan
        if empresa_id and tipo_plan == "personalizado":
            filtros["empresa_id"] = empresa_id
            filtros["tipo_plan"] = "personalizado"
        else:
            # Plan estándar: sin empresa_id o tipo_plan = "estandar"
            filtros["$or"] = [
                {"tipo_plan": "estandar"},
                {"empresa_id": {"$exists": False}},
                {"empresa_id": None}
            ]
        
        # Si hay búsqueda, usar búsqueda de texto
        if busqueda and busqueda.strip():
            return await self.buscar_cuentas_rapido(busqueda.strip(), activos_solo, limit or 100, empresa_id, tipo_plan)
        
        # Si no hay búsqueda, usar filtros normales
        docs = await self.plan_service.repo.list_cuentas(filtros, limit=limit)
        return [self.plan_service._doc_to_response(d) for d in docs]

    async def buscar_cuentas_rapido(self, termino: str, activos_solo: bool = True, limit: int = 50, empresa_id: str = None, tipo_plan: str = "estandar"):
        """Búsqueda optimizada con índices de texto, filtrada por empresa y tipo"""
        # Crear filtro base
        filtros = {}
        if activos_solo:
            filtros["activa"] = True
            
        # Filtros para empresa y tipo de plan
        if empresa_id and tipo_plan == "personalizado":
            filtros["empresa_id"] = empresa_id
            filtros["tipo_plan"] = "personalizado"
        else:
            # Plan estándar
            filtros["$or"] = [
                {"tipo_plan": "estandar"},
                {"empresa_id": {"$exists": False}},
                {"empresa_id": None}
            ]
        
        # Búsqueda por texto en MongoDB (requiere índice de texto)
        docs = await self.plan_service.repo.buscar_texto(termino, filtros, limit)
        return [self.plan_service._doc_to_response(d) for d in docs]
