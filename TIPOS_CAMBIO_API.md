# API de Tipos de Cambio

## Descripción

La API de tipos de cambio proporciona acceso a una base de datos persistente de tipos de cambio diarios USD/PEN obtenidos desde eApiPeru. Permite consultar, actualizar y poblar automáticamente los tipos de cambio para uso en otros módulos del sistema.

## Endpoints Disponibles

### 1. Listar Tipos de Cambio
```
GET /api/v1/consultas/tipos-cambio
```

**Parámetros de consulta:**
- `page` (opcional): Número de página (default: 1)
- `size` (opcional): Tamaño de página (default: 10, máximo: 100)
- `moneda_origen` (opcional): Filtrar por moneda origen (default: USD)
- `moneda_destino` (opcional): Filtrar por moneda destino (default: PEN)

**Respuesta:**
```json
{
  "tipos_cambio": [
    {
      "id": "68ac67ed866098126644b329",
      "fecha": "2025-08-25",
      "moneda_origen": "USD",
      "moneda_destino": "PEN",
      "compra": 3.518,
      "venta": 3.526,
      "oficial": 3.522,
      "fuente": "eApiPeru",
      "es_oficial": true,
      "es_activo": true,
      "created_at": "2025-08-25T13:41:01.040000",
      "updated_at": "2025-08-25T13:41:01.040000",
      "notas": "Consultado automáticamente desde eApiPeru"
    }
  ],
  "total": 6,
  "page": 1,
  "size": 10,
  "total_pages": 1
}
```

### 2. Obtener Tipo de Cambio por Fecha
```
GET /api/v1/consultas/tipos-cambio/{fecha}
```

**Parámetros:**
- `fecha`: Fecha en formato YYYY-MM-DD

**Ejemplo:**
```bash
GET /api/v1/consultas/tipos-cambio/2025-01-24
```

### 3. Obtener Tipo de Cambio Actual (Más Reciente)
```
GET /api/v1/consultas/tipos-cambio/actual
```

**Respuesta:**
```json
{
  "id": "68ac67ed866098126644b329",
  "fecha": "2025-08-25",
  "moneda_origen": "USD",
  "moneda_destino": "PEN",
  "compra": 3.518,
  "venta": 3.526,
  "oficial": 3.522,
  "fuente": "eApiPeru",
  "es_oficial": true,
  "es_activo": true,
  "created_at": "2025-08-25T13:41:01.040000",
  "updated_at": "2025-08-25T13:41:01.040000",
  "notas": "Consultado automáticamente desde eApiPeru"
}
```

### 4. Actualizar Tipo de Cambio
```
POST /api/v1/consultas/tipos-cambio/actualizar
```

**Body:**
```json
{
  "fecha": "2025-01-24",
  "compra": 3.720,
  "venta": 3.730,
  "oficial": 3.725
}
```

### 5. Poblar Tipos de Cambio Históricos
```
POST /api/v1/consultas/tipos-cambio/poblar-historicos
```

**Parámetros de consulta:**
- `fecha_inicio`: Fecha de inicio en formato YYYY-MM-DD
- `fecha_fin`: Fecha de fin en formato YYYY-MM-DD
- `forzar_actualizacion` (opcional): true/false (default: false)

**Ejemplo:**
```bash
POST /api/v1/consultas/tipos-cambio/poblar-historicos?fecha_inicio=2025-01-20&fecha_fin=2025-01-24&forzar_actualizacion=false
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Procesados 5 registros. Creados: 5, Actualizados: 0, Errores: 0. Tasa de éxito: 100.0%",
  "registros_procesados": 5,
  "registros_creados": 5,
  "registros_actualizados": 0,
  "registros_error": 0,
  "fecha_desde": "2025-01-20",
  "fecha_hasta": "2025-01-24",
  "detalles": [
    "✓ 2025-01-20: Creado exitosamente",
    "✓ 2025-01-21: Creado exitosamente",
    "✓ 2025-01-22: Creado exitosamente",
    "✓ 2025-01-23: Creado exitosamente",
    "✓ 2025-01-24: Creado exitosamente"
  ]
}
```

### 6. Estado del Servicio
```
GET /api/v1/consultas/tipos-cambio/estado
```

**Respuesta:**
```json
{
  "servicio": "Tipos de Cambio",
  "estado": "Disponible",
  "api_externa": "Disponible",
  "base_datos": "Conectada",
  "ultimo_tipo_cambio": "2025-08-25",
  "total_registros": 6
}
```

## Uso en Otros Módulos

### 1. Consulta Simple por Fecha
```python
import httpx

async def obtener_tipo_cambio(fecha: str):
    """Obtiene el tipo de cambio para una fecha específica"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/api/v1/consultas/tipos-cambio/{fecha}")
        if response.status_code == 200:
            return response.json()
        return None

# Uso
tipo_cambio = await obtener_tipo_cambio("2025-01-24")
if tipo_cambio:
    tasa_oficial = tipo_cambio["oficial"]  # 3.721
    tasa_compra = tipo_cambio["compra"]    # 3.718
    tasa_venta = tipo_cambio["venta"]      # 3.724
```

### 2. Obtener Tipo de Cambio Actual
```python
async def obtener_tipo_cambio_actual():
    """Obtiene el tipo de cambio más reciente disponible"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/v1/consultas/tipos-cambio/actual")
        if response.status_code == 200:
            return response.json()
        return None

# Uso
tipo_cambio_actual = await obtener_tipo_cambio_actual()
```

### 3. Consulta con Validación de Disponibilidad
```python
async def obtener_tipo_cambio_con_fallback(fecha: str):
    """Obtiene tipo de cambio con fallback al más reciente si no existe"""
    # Intentar obtener por fecha específica
    tipo_cambio = await obtener_tipo_cambio(fecha)
    
    if tipo_cambio:
        return tipo_cambio
    
    # Si no existe, obtener el más reciente
    return await obtener_tipo_cambio_actual()
```

### 4. Asegurar Disponibilidad de Datos
```python
async def asegurar_tipo_cambio(fecha_inicio: str, fecha_fin: str):
    """Asegura que los tipos de cambio estén disponibles para un rango de fechas"""
    async with httpx.AsyncClient() as client:
        url = f"http://localhost:8000/api/v1/consultas/tipos-cambio/poblar-historicos"
        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "forzar_actualizacion": False
        }
        response = await client.post(url, params=params)
        return response.json()
```

## Estructuras de Datos

### ExchangeRate
```python
{
    "id": str,                    # ID único del registro
    "fecha": str,                 # Fecha en formato YYYY-MM-DD
    "moneda_origen": str,         # Moneda origen (USD)
    "moneda_destino": str,        # Moneda destino (PEN)
    "compra": float,              # Tasa de compra
    "venta": float,               # Tasa de venta
    "oficial": float,             # Tasa oficial
    "fuente": str,                # Fuente de datos (eApiPeru)
    "es_oficial": bool,           # Si es tasa oficial
    "es_activo": bool,            # Si está activo
    "created_at": str,            # Timestamp de creación
    "updated_at": str,            # Timestamp de última actualización
    "notas": str                  # Notas adicionales
}
```

## Consideraciones Técnicas

1. **Persistencia**: Los datos se almacenan en MongoDB con conversión automática de tipos
2. **Fuente**: Los datos provienen de eApiPeru (API externa confiable)
3. **Timezone**: Todos los timestamps están en UTC
4. **Validación**: Fechas deben estar en formato YYYY-MM-DD
5. **Paginación**: La API soporta paginación para consultas grandes
6. **Error Handling**: Respuestas consistentes con códigos HTTP apropiados

## Ejemplos de Uso en Módulos

### Módulo de Facturación
```python
# Convertir monto USD a PEN usando tipo de cambio del día
async def convertir_usd_a_pen(monto_usd: float, fecha: str) -> float:
    tipo_cambio = await obtener_tipo_cambio(fecha)
    if tipo_cambio:
        return monto_usd * tipo_cambio["venta"]  # Usar tasa de venta
    raise ValueError(f"No se encontró tipo de cambio para {fecha}")
```

### Módulo de Reportes
```python
# Obtener tipos de cambio para un período de reportes
async def obtener_tipos_cambio_periodo(fecha_inicio: str, fecha_fin: str):
    async with httpx.AsyncClient() as client:
        params = {
            "page": 1,
            "size": 100,
            "fecha_desde": fecha_inicio,
            "fecha_hasta": fecha_fin
        }
        response = await client.get(
            "http://localhost:8000/api/v1/consultas/tipos-cambio",
            params=params
        )
        return response.json()["tipos_cambio"]
```

### Módulo de Contabilidad
```python
# Validar y obtener tipo de cambio para asientos contables
async def obtener_tipo_cambio_contable(fecha: str, tipo: str = "oficial"):
    tipo_cambio = await obtener_tipo_cambio(fecha)
    if not tipo_cambio:
        raise ValueError(f"Tipo de cambio no disponible para {fecha}")
    
    return {
        "oficial": tipo_cambio["oficial"],
        "compra": tipo_cambio["compra"],
        "venta": tipo_cambio["venta"]
    }[tipo]
```
