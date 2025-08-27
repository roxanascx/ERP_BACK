import requests
import json

def test_ple_download():
    """Probar descarga directa de PLE"""
    base_url = "http://127.0.0.1:8000/api/v1/accounting"
    libro_id = "68ae3823255bc9585ceec4c6"
    
    print("🔽 Probando descarga directa de PLE...")
    
    # Test 1: Descarga directa via GET
    url = f"{base_url}/ple/descargar/{libro_id}?ejercicio=2025&mes=8"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Verificar que es un archivo ZIP
            if response.headers.get('content-type') == 'application/zip':
                print("✅ Archivo ZIP recibido correctamente")
                print(f"Tamaño del archivo: {len(response.content)} bytes")
                
                # Guardar el archivo para verificar
                with open("test_ple_download.zip", "wb") as f:
                    f.write(response.content)
                print("📁 Archivo guardado como 'test_ple_download.zip'")
                
                # Verificar contenido del ZIP
                import zipfile
                import io
                
                with zipfile.ZipFile(io.BytesIO(response.content), 'r') as zip_file:
                    file_list = zip_file.namelist()
                    print(f"Archivos en el ZIP: {file_list}")
                    
                    if file_list:
                        # Leer el contenido del primer archivo
                        content = zip_file.read(file_list[0]).decode('utf-8')
                        lines = content.split('\n')
                        print(f"Líneas en el archivo PLE: {len(lines)}")
                        if lines:
                            print(f"Primera línea: {lines[0][:100]}...")
                            
            else:
                print(f"❌ Tipo de contenido inesperado: {response.headers.get('content-type')}")
                print(f"Respuesta: {response.text[:500]}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la petición: {str(e)}")
    
    # Test 2: Generación con descarga directa via POST
    print("\n🔄 Probando generación con descarga directa...")
    url = f"{base_url}/ple/generar"
    data = {
        "libro_diario_id": libro_id,
        "ejercicio": 2025,
        "mes": 8,
        "descargar_directo": True
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            if response.headers.get('content-type') == 'application/zip':
                print("✅ Descarga directa via POST funcionando")
                print(f"Tamaño del archivo: {len(response.content)} bytes")
            else:
                print("📄 Respuesta JSON recibida:")
                try:
                    json_response = response.json()
                    print(json.dumps(json_response, indent=2, ensure_ascii=False))
                except:
                    print(response.text[:500])
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la petición: {str(e)}")

if __name__ == "__main__":
    test_ple_download()
