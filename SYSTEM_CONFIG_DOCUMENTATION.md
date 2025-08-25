# Módulo System Config - Configuración del Sistema

## Descripción

El módulo **System Config** proporciona funcionalidades completas para la gestión de configuraciones del sistema, tipos de cambio y manejo de tiempo con zona horaria de Perú. Este módulo es esencial para el correcto funcionamiento del sistema ERP.

## 🚀 Características Principales

### 1. **Gestión de Tiempo con Zona Horaria de Perú**
- ✅ Obtención de fecha/hora actual en zona horaria de Perú (America/Lima)
- ✅ Cálculo de días hábiles (excluyendo fines de semana)
- ✅ Formateo de fechas según configuración personalizable
- ✅ Verificación de horario laboral
- ✅ Funciones para inicio/fin de día
- ✅ Conversión entre zonas horarias

### 2. **Gestión de Tipos de Cambio**
- ✅ Almacenamiento de tipos de cambio por fecha
- ✅ Soporte para múltiples pares de monedas
- ✅ Histórico completo de tipos de cambio
- ✅ Cálculo automático de conversiones
- ✅ Soporte para múltiples fuentes (manual, API, BCRP)
- ✅ Tipos de cambio de compra y venta

### 3. **Configuraciones del Sistema**
- ✅ Configuraciones categorizadas y tipadas
- ✅ Soporte para múltiples tipos de dato (string, number, boolean, json, date, datetime)
- ✅ Configuraciones del sistema protegidas contra modificación
- ✅ Búsqueda y filtrado avanzado
- ✅ Validaciones personalizadas

## 📁 Estructura del Módulo

```
app/modules/system_config/
├── __init__.py          # Exports del módulo
├── models.py            # Modelos Pydantic (SystemConfig, ExchangeRate, TimeConfig)
├── schemas.py           # Esquemas de respuesta API
├── routes.py            # Endpoints de la API REST
├── services.py          # Lógica de negocio
├── repositories.py      # Acceso a datos (MongoDB)
└── utils.py            # Utilidades para tiempo y zona horaria
```

## 🛠 Instalación y Configuración

### 1. Dependencias
Las siguientes dependencias han sido añadidas al proyecto:
```bash
pytz==2023.3           # Manejo de zonas horarias
python-dateutil==2.8.2 # Parsing de fechas avanzado
```

### 2. Configuración en el Router
El módulo se ha integrado en el router principal (`app/core/router.py`):
```python
from ..modules.system_config import routes as system_config_routes

api_router.include_router(
    system_config_routes.router,
    prefix="/system",
    tags=["System Config"]
)
```

## 🌐 API Endpoints

### **Configuraciones del Sistema**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/system/configs` | Crear nueva configuración |
| `GET` | `/api/v1/system/configs` | Listar configuraciones (con filtros) |
| `GET` | `/api/v1/system/configs/{key}` | Obtener configuración por clave |
| `PUT` | `/api/v1/system/configs/{id}` | Actualizar configuración |
| `DELETE` | `/api/v1/system/configs/{id}` | Eliminar configuración |
| `POST` | `/api/v1/system/configs/initialize` | Inicializar configuraciones por defecto |

### **Tipos de Cambio**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/system/exchange-rates` | Crear tipo de cambio |
| `GET` | `/api/v1/system/exchange-rates` | Listar tipos de cambio |
| `GET` | `/api/v1/system/exchange-rates/latest/{from}/{to}` | Obtener tipo de cambio más reciente |
| `POST` | `/api/v1/system/exchange-rates/calculate` | Calcular conversión de moneda |
| `PUT` | `/api/v1/system/exchange-rates/{id}` | Actualizar tipo de cambio |
| `DELETE` | `/api/v1/system/exchange-rates/{id}` | Eliminar tipo de cambio |
| `GET` | `/api/v1/system/exchange-rates/currency-pairs` | Obtener pares de monedas disponibles |
| `POST` | `/api/v1/system/exchange-rates/bulk` | Crear múltiples tipos de cambio |

### **Configuración de Tiempo**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/system/time-config` | Obtener configuración de tiempo |
| `PUT` | `/api/v1/system/time-config` | Actualizar configuración de tiempo |
| `GET` | `/api/v1/system/time/current-peru` | Obtener hora actual de Perú |
| `GET` | `/api/v1/system/time/business-hours` | Verificar horario laboral |

### **Estado del Sistema**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/system/status` | Estado general del sistema |
| `GET` | `/api/v1/system/health` | Health check del módulo |

## 📝 Ejemplos de Uso

### 1. Obtener Hora Actual de Perú
```bash
GET /api/v1/system/time/current-peru
```
**Respuesta:**
```json
{
    "current_time": "2025-08-24T21:14:11.908832-05:00",
    "timezone": "America/Lima",
    "formatted": "2025-08-24 21:14:11 -05"
}
```

### 2. Crear Configuración del Sistema
```bash
POST /api/v1/system/configs
```
**Body:**
```json
{
    "config_key": "business.tax_rate",
    "config_value": "18.0",
    "config_type": "number",
    "description": "Tasa de IGV en Perú (%)",
    "category": "business"
}
```

### 3. Crear Tipo de Cambio
```bash
POST /api/v1/system/exchange-rates
```
**Body:**
```json
{
    "currency_from": "USD",
    "currency_to": "PEN",
    "exchange_rate": 3.75,
    "exchange_date": "2025-08-24",
    "source": "bcrp",
    "is_official": true
}
```

### 4. Calcular Conversión de Moneda
```bash
POST /api/v1/system/exchange-rates/calculate
```
**Body:**
```json
{
    "amount": 100.00,
    "currency_from": "USD",
    "currency_to": "PEN",
    "exchange_date": "2025-08-24"
}
```
**Respuesta:**
```json
{
    "original_amount": 100.00,
    "converted_amount": 375.00,
    "exchange_rate": 3.75,
    "currency_from": "USD",
    "currency_to": "PEN",
    "exchange_date": "2025-08-24",
    "calculation_date": "2025-08-24T21:14:11.908832-05:00"
}
```

## 🧩 Uso en Código Python

### Utilidades de Tiempo de Perú
```python
from app.modules.system_config.utils import PeruTimeUtils

# Obtener hora actual en Perú
current_time = PeruTimeUtils.now_peru()

# Verificar si es día hábil
is_business_day = PeruTimeUtils.is_business_day(current_time)

# Formatear fecha
formatted = PeruTimeUtils.format_peru_datetime(current_time)

# Obtener inicio del día
start_of_day = PeruTimeUtils.start_of_day_peru()
```

### Servicios
```python
from app.modules.system_config.services import (
    SystemConfigService, 
    ExchangeRateService, 
    TimeConfigService
)

# Obtener valor de configuración
config_service = SystemConfigService()
tax_rate = await config_service.get_config_value("business.tax_rate", 18.0)

# Obtener tipo de cambio
exchange_service = ExchangeRateService()
rate = await exchange_service.get_exchange_rate("USD", "PEN")
```

## 🗄️ Modelos de Base de Datos

### SystemConfig Collection
```javascript
{
    "_id": ObjectId,
    "config_key": "business.tax_rate",
    "config_value": "18.0",
    "config_type": "number",
    "description": "Tasa de IGV en Perú (%)",
    "category": "business",
    "is_active": true,
    "is_system": false,
    "created_at": ISODate,
    "updated_at": ISODate,
    "created_by": "user_id",
    "updated_by": "user_id"
}
```

### ExchangeRates Collection
```javascript
{
    "_id": ObjectId,
    "currency_from": "USD",
    "currency_to": "PEN",
    "exchange_rate": 3.75,
    "exchange_date": ISODate,
    "source": "bcrp",
    "buy_rate": 3.74,
    "sell_rate": 3.76,
    "is_active": true,
    "is_official": true,
    "created_at": ISODate,
    "updated_at": ISODate,
    "notes": "Tipo de cambio oficial BCRP"
}
```

### TimeConfigs Collection
```javascript
{
    "_id": ObjectId,
    "timezone": "America/Lima",
    "date_format": "%Y-%m-%d",
    "datetime_format": "%Y-%m-%d %H:%M:%S",
    "time_format": "%H:%M:%S",
    "business_start_time": "09:00",
    "business_end_time": "18:00",
    "business_days": [0, 1, 2, 3, 4],
    "fiscal_year_start": "01-01",
    "fiscal_year_end": "12-31",
    "created_at": ISODate,
    "updated_at": ISODate
}
```

## 📚 Configuraciones por Defecto

Al inicializar el sistema, se crean automáticamente las siguientes configuraciones:

- `system.timezone` → "America/Lima"
- `system.default_currency` → "PEN"
- `business.decimal_places` → "2"
- `business.tax_rate` → "18.0"

## 🔧 Funcionalidades Avanzadas

### 1. **Zona Horaria de Perú**
- Manejo automático de cambios de horario (horario de verano)
- Conversión automática desde/hacia UTC
- Cálculos precisos de días hábiles

### 2. **Tipos de Cambio**
- Soporte para múltiples fuentes de datos
- Validación de fechas (no muy futuras)
- Histórico completo para auditoría

### 3. **Configuraciones**
- Tipado fuerte con validación
- Protección de configuraciones críticas del sistema
- Búsqueda y filtrado avanzado

## 🚀 Próximos Pasos

1. **Integración con API del BCRP** para tipos de cambio automáticos
2. **Configuración de feriados peruanos** para cálculo más preciso de días hábiles
3. **Notificaciones** cuando hay cambios importantes en configuraciones
4. **Cache** para mejorar performance en consultas frecuentes
5. **Backup automático** de configuraciones críticas

## ✅ Estado del Proyecto

El módulo **System Config** ha sido implementado exitosamente con todas las funcionalidades requeridas:

- ✅ **Gestión de fecha/hora con zona horaria de Perú**
- ✅ **Sistema de tipos de cambio completo**
- ✅ **Configuraciones del sistema categorizadas**
- ✅ **API REST completa y documentada**
- ✅ **Validaciones y tipos de dato robustos**
- ✅ **Integración con el sistema ERP existente**

El módulo está listo para ser utilizado en producción y puede ser extendido según las necesidades del negocio.
