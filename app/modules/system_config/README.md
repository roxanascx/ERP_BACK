# System Config Module

## 🎯 Resumen

Módulo completo para gestión de configuraciones del sistema, tipos de cambio y manejo de tiempo con zona horaria de Perú.

## 🚀 Inicio Rápido

### 1. **Probar Hora de Perú**
```bash
curl http://localhost:8000/api/v1/system/time/current-peru
```

### 2. **Health Check**
```bash
curl http://localhost:8000/api/v1/system/health
```

### 3. **Ver Documentación Completa**
Visita: http://localhost:8000/docs

## 📋 Características Implementadas

- ✅ **Gestión de tiempo con zona horaria de Perú (America/Lima)**
- ✅ **Sistema de tipos de cambio con histórico**
- ✅ **Configuraciones del sistema categorizadas**
- ✅ **API REST completa**
- ✅ **Validaciones robustas**
- ✅ **Documentación automática**

## 🗂️ Estructura

```
system_config/
├── models.py      # Modelos de datos
├── schemas.py     # Esquemas API
├── routes.py      # Endpoints
├── services.py    # Lógica de negocio
├── repositories.py # Acceso a datos
└── utils.py       # Utilidades de tiempo
```

## 📖 Documentación Completa

Ver: [SYSTEM_CONFIG_DOCUMENTATION.md](./SYSTEM_CONFIG_DOCUMENTATION.md)

## 🧪 Pruebas

Ejecutar script de prueba:
```bash
python test_system_config.py
```

## 🔗 Endpoints Principales

- `/api/v1/system/time/current-peru` - Hora actual de Perú
- `/api/v1/system/configs` - Configuraciones del sistema
- `/api/v1/system/exchange-rates` - Tipos de cambio
- `/api/v1/system/status` - Estado del sistema

## ✨ Ejemplo de Uso

```python
from app.modules.system_config.utils import PeruTimeUtils

# Obtener hora actual en Perú
current_time = PeruTimeUtils.now_peru()
print(f"Hora en Perú: {current_time}")
```
