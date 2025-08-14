"""
Script de prueba para verificar endpoints SIRE/RVIE
"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_endpoint(session, method, endpoint, data=None, headers=None):
    """Prueba un endpoint específico"""
    url = f"{BASE_URL}{endpoint}"
    
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    try:
        print(f"\n🔗 {method} {endpoint}")
        print(f"📊 Data: {json.dumps(data, indent=2) if data else 'None'}")
        
        if method.upper() == "GET":
            async with session.get(url, headers=headers) as response:
                result = await response.text()
                print(f"📈 Status: {response.status}")
                print(f"📝 Response: {result[:500]}...")
                return response.status, result
        
        elif method.upper() == "POST":
            async with session.post(url, json=data, headers=headers) as response:
                result = await response.text()
                print(f"📈 Status: {response.status}")
                print(f"📝 Response: {result[:500]}...")
                return response.status, result
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, str(e)

async def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de endpoints SIRE/RVIE")
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Verificar que el backend esté corriendo
        print("\n" + "="*50)
        print("📍 1. VERIFICANDO BACKEND")
        print("="*50)
        await test_endpoint(session, "GET", "/")
        
        # 2. Verificar endpoints de SIRE
        print("\n" + "="*50)
        print("📍 2. VERIFICANDO ENDPOINTS SIRE")
        print("="*50)
        
        # Listar tickets
        await test_endpoint(session, "GET", "/api/v1/sire/rvie/tickets/10426346082")
        
        # Descargar propuesta
        await test_endpoint(session, "POST", "/api/v1/sire/rvie/descargar-propuesta", {
            "ruc": "10426346082",
            "periodo": "202507",
            "forzar_descarga": False,
            "incluir_detalle": True
        })
        
        # Verificar auth - URL CORREGIDA
        await test_endpoint(session, "GET", "/api/v1/sire/status/10426346082")
        
        # 3. Verificar endpoints de empresas
        print("\n" + "="*50)
        print("📍 3. VERIFICANDO ENDPOINTS EMPRESAS")
        print("="*50)
        
        await test_endpoint(session, "GET", "/api/v1/companies/")
        
    print("\n✅ Pruebas completadas")

if __name__ == "__main__":
    asyncio.run(main())
