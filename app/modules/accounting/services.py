"""Servicios del módulo Contabilidad
Implementación ligera que adapta partes del prototipo PlanContableService.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.modules.accounting.repositories import AccountingRepository
from app.models.plan_contable import (
    CuentaContableCreate,
    CuentaContableResponse,
    EstadisticasPlanContable,
    ClaseContable,
)


class PlanContableServiceAdapter:
    def __init__(self, repository: Optional[AccountingRepository] = None):
        self.repo = repository or AccountingRepository()

    async def list_cuentas(self, activos_solo: bool = True, clase_contable: Optional[int] = None, nivel: Optional[int] = None) -> List[CuentaContableResponse]:
        filtros = {}
        if activos_solo:
            filtros["activa"] = True
        if clase_contable:
            filtros["clase_contable"] = clase_contable
        if nivel:
            filtros["nivel"] = nivel

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
        documento["fecha_creacion"] = datetime.now()
        documento["naturaleza"] = self._determinar_naturaleza(payload.clase_contable)

        result = await self.repo.insert_cuenta(documento)
        created = await self.repo.find_by_codigo(documento["codigo"])
        return self._doc_to_response(created)

    async def obtener_estructura_jerarquica(self) -> Dict[str, Any]:
        # Delegar a repository: recuperar nivel 1 y construir árbol recursivo
        clases = await self.repo.list_cuentas({"nivel": 1, "activa": True})
        estructura = []
        for clase in clases:
            hijos = await self._obtener_hijos_recursivo(clase["codigo"])
            estructura.append({
                "codigo": clase["codigo"],
                "descripcion": clase["descripcion"],
                "nivel": clase["nivel"],
                "hijos": hijos,
            })

        return {"estructura": estructura, "total_clases": len(estructura)}

    async def _obtener_hijos_recursivo(self, codigo_padre: str) -> List[Dict[str, Any]]:
        if not codigo_padre:
            return []
        nivel_padre = len(codigo_padre)
        siguiente = nivel_padre + 1
        if siguiente > 8:
            return []
        regex = f"^{codigo_padre}[0-9]$" if siguiente == 2 else f"^{codigo_padre}[0-9]+$"
        hijos = await self.repo.list_cuentas({"codigo": {"$regex": regex}, "nivel": siguiente, "activa": True})
        resultado = []
        for hijo in hijos:
            if len(hijo["codigo"]) == siguiente:
                sub = await self._obtener_hijos_recursivo(hijo["codigo"])
                resultado.append({
                    "codigo": hijo["codigo"],
                    "descripcion": hijo["descripcion"],
                    "nivel": hijo["nivel"],
                    "es_hoja": hijo.get("es_hoja", True),
                    "hijos": sub,
                })
        return resultado

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

    async def actualizar_cuenta(self, codigo: str, payload: dict) -> Optional[CuentaContableResponse]:
        """Actualizar una cuenta contable"""
        # Verificar que la cuenta existe
        cuenta_existente = await self.repo.find_by_codigo(codigo)
        if not cuenta_existente:
            raise ValueError(f"No existe una cuenta con el código {codigo}")
        
        # Preparar datos de actualización
        update_data = {k: v for k, v in payload.items() if v is not None}
        update_data["fecha_modificacion"] = datetime.now()
        
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
            fecha_creacion=documento.get("fecha_creacion"),
            fecha_modificacion=documento.get("fecha_modificacion"),
        )


class AccountingService:
    def __init__(self):
        self.plan_service = PlanContableServiceAdapter()

    async def get_plan_estructura(self) -> Dict[str, Any]:
        return await self.plan_service.obtener_estructura_jerarquica()

    async def list_cuentas(self, activos_solo: bool = True):
        return await self.plan_service.list_cuentas(activos_solo)

    async def list_cuentas_filtradas(
        self, 
        activos_solo: bool = True,
        clase_contable: Optional[int] = None,
        nivel: Optional[int] = None,
        busqueda: Optional[str] = None,
        limit: Optional[int] = None
    ):
        """Método optimizado para obtener cuentas con filtros múltiples"""
        filtros = {}
        
        if activos_solo:
            filtros["activa"] = True
        if clase_contable:
            filtros["clase_contable"] = clase_contable
        if nivel:
            filtros["nivel"] = nivel
        
        # Si hay búsqueda, usar búsqueda de texto
        if busqueda and busqueda.strip():
            return await self.buscar_cuentas_rapido(busqueda.strip(), activos_solo, limit or 100)
        
        # Si no hay búsqueda, usar filtros normales
        docs = await self.plan_service.repo.list_cuentas(filtros, limit=limit)
        return [self.plan_service._doc_to_response(d) for d in docs]

    async def buscar_cuentas_rapido(self, termino: str, activos_solo: bool = True, limit: int = 50):
        """Búsqueda optimizada con índices de texto"""
        # Crear filtro base
        filtros = {}
        if activos_solo:
            filtros["activa"] = True
        
        # Búsqueda por texto en MongoDB (requiere índice de texto)
        docs = await self.plan_service.repo.buscar_texto(termino, filtros, limit)
        return [self.plan_service._doc_to_response(d) for d in docs]

