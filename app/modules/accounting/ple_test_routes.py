from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime, date

router = APIRouter()

class PLEGeneracionRequest(BaseModel):
    ejercicio: int
    mes: int
    ruc: str
    razon_social: str
    formato: Optional[str] = "TXT"
    incluir_cabecera: Optional[bool] = True
    validar_antes_generar: Optional[bool] = True
    observaciones: Optional[str] = ""

class PLEArchivo(BaseModel):
    id: str
    ejercicio: int
    mes: int
    ruc: str
    razonSocial: str
    fechaGeneracion: str
    fechaInicio: str
    fechaFin: str
    estado: str = "generado"
    nombreArchivo: str
    tamanoArchivo: int = 1024
    totalRegistros: int = 0
    observaciones: Optional[str] = ""
    errores: Optional[List[str]] = []

class PLEGeneracionResponse(BaseModel):
    success: bool
    archivo_nombre: str
    archivo_id: str
    mensaje: str
    contenido_txt: Optional[str] = None
    contenido_zip: Optional[bytes] = None

@router.post("/ple/generar", response_model=PLEGeneracionResponse)
async def generar_ple_test(request: PLEGeneracionRequest):
    """
    Endpoint de prueba para generar PLE
    """
    try:
        # Simular generación de PLE
        archivo_nombre = f"LE{request.ruc}{request.ejercicio}{request.mes:02d}00140100001111.txt"
        archivo_id = f"ple_{request.ruc}_{request.ejercicio}_{request.mes}"
        
        # Generar contenido de prueba
        contenido_txt = f"""20231201|001|M0001|{request.ruc}|{request.razon_social}|Asiento de prueba|101|10121|Caja y bancos|100.00|0.00|PEN|1.00|1|01/12/2023|001-123456|1|0|1|01|
20231201|002|M0002|{request.ruc}|{request.razon_social}|Asiento de prueba 2|401|40111|Ventas|0.00|100.00|PEN|1.00|1|01/12/2023|001-123457|1|0|1|01|"""
        
        return PLEGeneracionResponse(
            success=True,
            archivo_nombre=archivo_nombre,
            archivo_id=archivo_id,
            mensaje="Archivo PLE generado exitosamente (modo prueba)",
            contenido_txt=contenido_txt
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PLE: {str(e)}")

@router.get("/ple/archivos", response_model=List[PLEArchivo])
async def obtener_archivos_ple_test():
    """
    Endpoint de prueba para obtener lista de archivos PLE
    """
    try:
        # Archivos de prueba
        archivos = [
            PLEArchivo(
                id="ple_12345678901_2024_8",
                ejercicio=2024,
                mes=8,
                ruc="12345678901",
                razonSocial="Empresa de Prueba S.A.C.",
                fechaGeneracion=datetime.now().isoformat(),
                fechaInicio="2024-08-01",
                fechaFin="2024-08-31",
                estado="generado",
                nombreArchivo="LE123456789012024080014010000111.txt",
                tamanoArchivo=2048,
                totalRegistros=150,
                observaciones="Archivo generado correctamente"
            ),
            PLEArchivo(
                id="ple_12345678901_2024_7",
                ejercicio=2024,
                mes=7,
                ruc="12345678901",
                razonSocial="Empresa de Prueba S.A.C.",
                fechaGeneracion=datetime.now().isoformat(),
                fechaInicio="2024-07-01",
                fechaFin="2024-07-31",
                estado="validado",
                nombreArchivo="LE123456789012024070014010000111.txt",
                tamanoArchivo=1856,
                totalRegistros=132,
                observaciones="Validado por SUNAT"
            )
        ]
        
        return archivos
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo archivos: {str(e)}")

@router.delete("/ple/archivos/{archivo_id}")
async def eliminar_archivo_ple_test(archivo_id: str):
    """
    Endpoint de prueba para eliminar archivo PLE
    """
    return {
        "success": True,
        "message": f"Archivo {archivo_id} eliminado exitosamente (modo prueba)"
    }

@router.get("/ple/configuracion")
async def obtener_configuracion_ple_test():
    """
    Endpoint de prueba para obtener configuración PLE
    """
    return {
        "general": {
            "empresaDefecto": "12345678901",
            "formatoDefecto": "TXT",
            "validarAntesGenerar": True
        },
        "validacion": {
            "verificarPlanContable": True,
            "validarCorrelativo": True,
            "verificarBalance": True
        },
        "exportacion": {
            "incluirCabecera": True,
            "comprimirArchivos": False,
            "generarMetadatos": True
        }
    }

@router.post("/ple/validar")
async def validar_ple_test(request: PLEGeneracionRequest):
    """
    Endpoint de prueba para validar datos PLE
    """
    resultados = [
        {
            "tipo": "info",
            "campo": "ruc",
            "mensaje": "RUC válido",
            "detalle": f"RUC {request.ruc} está correctamente formateado"
        },
        {
            "tipo": "success", 
            "campo": "periodo",
            "mensaje": "Período válido",
            "detalle": f"Período {request.ejercicio}-{request.mes:02d} es válido"
        }
    ]
    
    estadisticas = {
        "total_validaciones": 2,
        "exitosas": 2,
        "con_warnings": 0,
        "con_errores": 0
    }
    
    return {
        "success": True,
        "resultados": resultados,
        "estadisticas": estadisticas
    }
