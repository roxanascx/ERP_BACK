"""
Tests unitarios básicos para el módulo de contabilidad
"""
import pytest
import sys
import os
from datetime import datetime

# Añadir backend al path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.accounting.services import PlanContableServiceAdapter
from app.modules.accounting.repositories import AccountingRepository
from app.models.plan_contable import CuentaContableCreate, CuentaContableUpdate, CuentaContableResponse


class MockRepository:
    """Mock repository para tests"""
    def __init__(self):
        self.data = {
            "101": {
                "_id": "test_id_101",
                "codigo": "101",
                "descripcion": "Caja",
                "nivel": 3,
                "clase_contable": 1,
                "cuenta_padre": "10",
                "es_hoja": True,
                "acepta_movimiento": True,
                "naturaleza": "DEUDORA",
                "moneda": "MN",
                "activa": True,
                "fecha_creacion": datetime.now()
            },
            "10": {
                "_id": "test_id_10",
                "codigo": "10",
                "descripcion": "Efectivo y equivalentes",
                "nivel": 2,
                "clase_contable": 1,
                "cuenta_padre": "1",
                "es_hoja": False,
                "acepta_movimiento": False,
                "naturaleza": "DEUDORA",
                "moneda": "MN",
                "activa": True,
                "fecha_creacion": datetime.now()
            }
        }

    async def find_by_codigo(self, codigo: str):
        return self.data.get(codigo)

    @staticmethod
    def _cumple(cuenta, key, value):
        """Una condicion suelta del filtro, como la evaluaria Mongo."""
        if key == "$or":
            return any(
                all(MockRepository._cumple(cuenta, k, v) for k, v in sub.items())
                for sub in value
            )
        if isinstance(value, dict) and "$exists" in value:
            return (key in cuenta) == value["$exists"]
        return cuenta.get(key) == value

    async def list_cuentas(self, filtros=None):
        """
        Filtrado al estilo Mongo, lo justo para lo que usa el servicio.

        Antes comparaba todo por igualdad, asi que el `$or` que el servicio
        anade para separar el plan estandar del personalizado no casaba con
        nada y este mock devolvia siempre una lista vacia.
        """
        filtros = filtros or {}
        result = []
        for cuenta in self.data.values():
            if all(self._cumple(cuenta, k, v) for k, v in filtros.items()
                   if k != "$regex"):
                result.append(cuenta)
        return result

    async def insert_cuenta(self, documento):
        self.data[documento["codigo"]] = documento
        return type('Result', (), {'inserted_id': 'mock_id'})

    async def update_cuenta(self, codigo, update_data):
        if codigo in self.data:
            self.data[codigo].update(update_data)
            return type('Result', (), {'modified_count': 1})
        return type('Result', (), {'modified_count': 0})

    async def count_documents(self, filtros=None):
        return len(await self.list_cuentas(filtros))

    async def aggregate(self, pipeline):
        # Mock simple para estadísticas
        return [{"_id": 1, "total": 2}]


@pytest.mark.asyncio
async def test_get_cuenta_existente():
    """Test obtener cuenta existente"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    cuenta = await service.get_cuenta("101")
    
    assert cuenta is not None
    assert cuenta.codigo == "101"
    assert cuenta.descripcion == "Caja"
    assert cuenta.naturaleza == "DEUDORA"


@pytest.mark.asyncio
async def test_get_cuenta_inexistente():
    """Test obtener cuenta que no existe"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    cuenta = await service.get_cuenta("999")
    
    assert cuenta is None


@pytest.mark.asyncio
async def test_crear_cuenta_nueva():
    """Test crear nueva cuenta"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    nueva_cuenta = CuentaContableCreate(
        codigo="102",
        descripcion="Fondos fijos",
        nivel=3,
        clase_contable=1
    )
    
    resultado = await service.crear_cuenta(nueva_cuenta)
    
    assert resultado.codigo == "102"
    assert resultado.descripcion == "Fondos fijos"
    assert resultado.naturaleza == "DEUDORA"  # Auto-determinada por clase_contable=1


@pytest.mark.asyncio
async def test_crear_cuenta_duplicada():
    """Test crear cuenta con código duplicado"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    cuenta_duplicada = CuentaContableCreate(
        codigo="101",  # Ya existe en mock
        descripcion="Test duplicado",
        nivel=3,
        clase_contable=1
    )
    
    with pytest.raises(ValueError, match="Ya existe una cuenta con el código 101"):
        await service.crear_cuenta(cuenta_duplicada)


@pytest.mark.asyncio
async def test_list_cuentas_activas():
    """Test listar cuentas activas"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    cuentas = await service.list_cuentas(activos_solo=True)
    
    assert len(cuentas) == 2
    assert all(cuenta.activa for cuenta in cuentas)


@pytest.mark.asyncio
async def test_determinar_naturaleza():
    """Test determinación automática de naturaleza"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    # Clase 1 = DEUDORA
    assert service._determinar_naturaleza(1) == "DEUDORA"
    # Clase 4 = ACREEDORA (pasivos)
    assert service._determinar_naturaleza(4) == "ACREEDORA"
    # Clase 7 = ACREEDORA (ventas)
    assert service._determinar_naturaleza(7) == "ACREEDORA"


def test_doc_to_response():
    """Test conversión de documento a response"""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    
    doc = {
        "_id": "test_id",
        "codigo": "101",
        "descripcion": "Test",
        "nivel": 3,
        "clase_contable": 1,
        "naturaleza": "DEUDORA",
        "activa": True,
        "fecha_creacion": datetime.now()
    }
    
    response = service._doc_to_response(doc)
    
    assert isinstance(response, CuentaContableResponse)
    assert response.codigo == "101"
    assert response.descripcion == "Test"
    assert response.naturaleza == "DEUDORA"


# ---------------------------------------------------------------------------
# Cuentas autogeneradas (cargo/abono destino)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crear_cuenta_con_destino_valido():
    """La cuenta cargo/abono existe y acepta movimiento: se crea sin problema."""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)

    nueva_cuenta = CuentaContableCreate(
        codigo="102",
        descripcion="Fondos fijos",
        nivel=3,
        clase_contable=1,
        cuenta_cargo_destino={"codigo": "101", "denominacion": "Caja"},
    )

    resultado = await service.crear_cuenta(nueva_cuenta)
    assert resultado.cuenta_cargo_destino == {"codigo": "101", "denominacion": "Caja"}


@pytest.mark.asyncio
async def test_crear_cuenta_destino_inexistente_falla():
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)

    nueva_cuenta = CuentaContableCreate(
        codigo="102",
        descripcion="Fondos fijos",
        nivel=3,
        clase_contable=1,
        cuenta_abono_destino={"codigo": "999", "denominacion": "No existe"},
    )

    with pytest.raises(ValueError, match="no existe en el Plan de Cuentas"):
        await service.crear_cuenta(nueva_cuenta)


@pytest.mark.asyncio
async def test_crear_cuenta_destino_que_no_acepta_movimiento_falla():
    """"10" es una cuenta agrupadora (acepta_movimiento=False) en el mock."""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)

    nueva_cuenta = CuentaContableCreate(
        codigo="102",
        descripcion="Fondos fijos",
        nivel=3,
        clase_contable=1,
        cuenta_cargo_destino={"codigo": "10", "denominacion": "Efectivo y equivalentes"},
    )

    with pytest.raises(ValueError, match="no acepta movimientos"):
        await service.crear_cuenta(nueva_cuenta)


@pytest.mark.asyncio
async def test_crear_cuenta_destino_autorreferencia_falla():
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)

    nueva_cuenta = CuentaContableCreate(
        codigo="102",
        descripcion="Fondos fijos",
        nivel=3,
        clase_contable=1,
        cuenta_cargo_destino={"codigo": "102", "denominacion": "Fondos fijos"},
    )

    with pytest.raises(ValueError, match="no puede ser la misma cuenta"):
        await service.crear_cuenta(nueva_cuenta)


@pytest.mark.asyncio
async def test_actualizar_cuenta_permite_limpiar_destino():
    """Enviar `null` explicito (exclude_unset, no exclude_none) borra el destino."""
    mock_repo = MockRepository()
    service = PlanContableServiceAdapter(mock_repo)
    mock_repo.data["101"]["cuenta_cargo_destino"] = {"codigo": "10", "denominacion": "x"}
    mock_repo.data["101"]["acepta_movimiento"] = True

    cambios = CuentaContableUpdate(cuenta_cargo_destino=None)
    # `exclude_unset` solo conserva lo que el modelo marca como set: al venir
    # de un dict con la clave presente, pydantic lo cuenta como set.
    assert "cuenta_cargo_destino" in cambios.model_fields_set

    resultado = await service.actualizar_cuenta("101", cambios)
    assert resultado.cuenta_cargo_destino is None


if __name__ == "__main__":
    # Ejecutar tests básicos sin pytest
    import asyncio
    
    async def run_basic_tests():
        print("🧪 Ejecutando tests básicos...")
        
        # Test 1: Get cuenta existente
        mock_repo = MockRepository()
        service = PlanContableServiceAdapter(mock_repo)
        cuenta = await service.get_cuenta("101")
        assert cuenta.codigo == "101"
        print("✅ Test get_cuenta_existente: OK")
        
        # Test 2: Get cuenta inexistente
        cuenta_none = await service.get_cuenta("999")
        assert cuenta_none is None
        print("✅ Test get_cuenta_inexistente: OK")
        
        # Test 3: Crear cuenta nueva
        nueva = CuentaContableCreate(codigo="102", descripcion="Test", nivel=3, clase_contable=1)
        resultado = await service.crear_cuenta(nueva)
        assert resultado.codigo == "102"
        print("✅ Test crear_cuenta_nueva: OK")
        
        # Test 4: Naturaleza
        assert service._determinar_naturaleza(1) == "DEUDORA"
        assert service._determinar_naturaleza(4) == "ACREEDORA"
        print("✅ Test determinar_naturaleza: OK")
        
        print("\n🎉 Todos los tests básicos pasaron!")
    
    asyncio.run(run_basic_tests())
