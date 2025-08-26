# 📋 PLAN DE TRABAJO DETALLADO: LIBRO DIARIO ELECTRÓNICO SUNAT PLE
## Versión 2.0 - Actualizada con Tablas SUNAT Implementadas

---

## 🎯 OBJETIVO PRINCIPAL
Generar archivos de **Libro Diario en formato PLE** (Programa de Libros Electrónicos) para envío a SUNAT según la **Resolución N° 234-2006/SUNAT**, aprovechando la infraestructura de **12 tablas SUNAT ya implementadas**.

---

## 📊 CONTEXTO ACTUAL DEL SISTEMA

### ✅ **ACTIVOS DISPONIBLES (YA IMPLEMENTADOS)**

#### 🗃️ **Sistema de Tablas SUNAT Completo**
- **12 tablas oficiales SUNAT** cargadas y funcionales
- **API REST completa** con 20+ endpoints
- **Validación automática** de códigos SUNAT
- **Búsqueda y autocompletado** por descripción
- **Estadísticas y monitoreo** del sistema

**Tablas disponibles:**
1. `tipos_documento_identidad` (5 códigos)
2. `tipos_comprobantes_pago` (48 códigos) 
3. `codigos_libros_registros` (31 códigos)
4. `tipos_moneda` (múltiples códigos)
5. `tipos_medio_pago`
6. `cuentas_contables`
7. `codigos_pais`
8. `tipos_documento`
9. `estados_contribuyente`
10. `condicion_domicilio`
11. `tipos_operacion`
12. `clasificacion_bienes_servicios`

#### 🏗️ **Infraestructura Contable Base**
- **MongoDB** configurado para el módulo accounting
- **Modelos básicos** de Libro Diario y Asientos Contables
- **Estructura de servicios** y repositorios implementada
- **API endpoints** base para contabilidad
- **Schemas Pydantic** para validación

#### 🔧 **Arquitectura Técnica**
- **FastAPI** con rutas centralizadas en `/api/v1/accounting/`
- **Patrón Repository** y Service Layer
- **Validación automática** con Pydantic v2
- **Documentación automática** con Swagger
- **Pruebas funcionales** verificadas

---

## 📖 ANÁLISIS NORMATIVO ACTUALIZADO

### 📋 **Estructura del Libro Diario PLE (Formato 5.1)**

| Campo | Descripción | Formato | Obligatorio | **Validación SUNAT** |
|-------|-------------|---------|-------------|----------------------|
| 1 | Período | AAAAMMDD | ✅ | Formato fecha válido |
| 2 | Número correlativo del asiento (CUO) | Alfanumérico (hasta 40) | ✅ | Único por período |
| 3 | Código de cuenta contable | Alfanumérico | ✅ | **Validar con `cuentas_contables`** |
| 4 | Código de cuenta desagregada | Alfanumérico | ❌ | Opcional |
| 5 | Fecha de operación | DD/MM/AAAA | ✅ | Formato y rango válido |
| 6 | Glosa descripción | Alfanumérico | ✅ | Sin caracteres especiales |
| 7 | Movimientos Debe | Numérico (2 decimales) | ✅ | Mayor o igual a 0.00 |
| 8 | Movimientos Haber | Numérico (2 decimales) | ✅ | Mayor o igual a 0.00 |
| 9 | Dato Estructurado | Texto | ❌ | **Validar con tablas SUNAT** |

### 🔄 **Integración con Tablas SUNAT**
- **Campo 3**: Validar códigos contables contra `cuentas_contables`
- **Campo 9**: Validar referencias a comprobantes usando `tipos_comprobantes_pago`
- **Metadatos**: Usar `codigos_libros_registros` para el código "5" (Libro Diario)
- **Moneda**: Validar con `tipos_moneda` (normalmente "PEN")

### 📁 **Nomenclatura del Archivo PLE**
```
LE[RUC][AAAAMMDD][AAAA][MM][00][5][1][00][1][1].TXT
```
**Ejemplo**: `LE20123456789202508312025080051000011.TXT`

Donde:
- `LE`: Prefijo fijo
- `[RUC]`: RUC de la empresa (11 dígitos)
- `[AAAAMMDD]`: Fecha del reporte (20250831)
- `[AAAA][MM]`: Año y mes del período (202508)
- `00`: Código de oportunidad (00=Normal)
- `5`: **Código del libro** (validado con `codigos_libros_registros`)
- `1`: Formato (1=Simplificado)
- `00`: Tipo de moneda (00=Soles, validado con `tipos_moneda`)
- `1`: Operación (1=Cierre mensual)
- `1`: Contenido (1=Con información)

---

## 🏗️ ANÁLISIS DEL MÓDULO ACCOUNTING ACTUAL

### ✅ **LO QUE YA ESTÁ IMPLEMENTADO**

#### 📊 **Sistema de Tablas SUNAT (COMPLETO)**
```python
# Servicios disponibles:
GET /api/v1/accounting/tablas-sunat/inicializar
GET /api/v1/accounting/tablas-sunat/buscar/codigo
GET /api/v1/accounting/tablas-sunat/validar/codigo
GET /api/v1/accounting/tablas-sunat/listados/[tabla]
POST /api/v1/accounting/tablas-sunat/validar/masivo
```

#### 🗃️ **Modelos Base Existentes**
- `LibroDiarioModel` en `libro_diario_models.py`
- `AsientoContableModel` con estructura contable básica
- Repositorio y servicios base implementados

#### 🔧 **Infraestructura Técnica**
- MongoDB configurado y conectado
- Rutas API centralizadas
- Validaciones Pydantic v2
- Estructura modular completa

### ❌ **LO QUE FALTA IMPLEMENTAR**

#### 📁 **Generación de Archivos PLE**
- Exportador de datos a formato TXT SUNAT
- Formateador de campos según especificaciones
- Generador de nombres de archivo con nomenclatura oficial

#### ✅ **Validaciones Específicas SUNAT** 
- Integración con las 12 tablas SUNAT para validación
- Verificación de Plan Contable PCGE
- Validación de balanceo contable
- Verificación de formatos de fecha y montos

#### 📦 **Sistema de Exportación**
- Compresión ZIP (requerido por SUNAT)
- Metadatos y headers del archivo
- Proceso de validación pre-envío

#### 🔄 **Integración con Sistema Existente**
- Conectar Libro Diario con tablas SUNAT
- Enriquecer datos con validaciones automáticas
- API endpoints para exportación

---

## 📅 PLAN DE TRABAJO DETALLADO - FASE POR FASE

### 🚀 **FASE 1: FUNDACIÓN PLE** (2-3 días)
*Crear la base del sistema de exportación PLE*

#### **Task 1.1: Analizador de Datos Contables**
📁 **Archivo**: `app/modules/accounting/ple_analyzer.py`

```python
class PLEDataAnalyzer:
    """Analiza y prepara datos contables para exportación PLE"""
    
    async def analizar_libro_diario(self, libro_id: str) -> PLEAnalysisResult
    async def validar_asientos_contables(self, asientos: List[AsientoContable]) -> ValidationResult
    async def verificar_balanceo(self, asientos: List[AsientoContable]) -> BalanceResult
    async def enriquecer_con_tablas_sunat(self, datos: Dict) -> EnrichedData
```

**Funcionalidades**:
- ✅ Análisis de integridad de datos contables
- ✅ Verificación de balanceo debe/haber
- ✅ Enriquecimiento automático con tablas SUNAT
- ✅ Detección de errores antes de exportación

#### **Task 1.2: Generador de Archivos PLE**
📁 **Archivo**: `app/modules/accounting/ple_generator.py`

```python
class PLEGenerator:
    """Generador de archivos PLE en formato SUNAT"""
    
    async def generar_libro_diario_ple(self, libro_id: str, opciones: PLEOptions) -> PLEArchivo
    async def formatear_linea_asiento(self, asiento: AsientoContable) -> str
    async def generar_nombre_archivo(self, empresa_ruc: str, periodo: date) -> str
    async def crear_archivo_zip(self, archivo_txt: str) -> bytes
```

**Funcionalidades**:
- ✅ Generación de archivos TXT según formato SUNAT
- ✅ Nomenclatura automática de archivos
- ✅ Formateo de campos con precisión requerida
- ✅ Compresión ZIP automática

#### **Task 1.3: Formateador de Datos**
📁 **Archivo**: `app/modules/accounting/ple_formatter.py`

```python
class PLEFormatter:
    """Formateo específico de datos para PLE"""
    
    def formatear_periodo(self, fecha: date) -> str
    def formatear_cuenta_contable(self, codigo: str) -> str  
    def formatear_monto(self, valor: Decimal) -> str
    def formatear_fecha_operacion(self, fecha: date) -> str
    def escapar_caracteres_especiales(self, texto: str) -> str
    def validar_longitud_campos(self, datos: Dict) -> ValidationResult
```

**Funcionalidades**:
- ✅ Formateo de fechas a DD/MM/AAAA
- ✅ Formateo de montos a 2 decimales
- ✅ Escape de caracteres especiales
- ✅ Validación de longitudes de campo

### 🔧 **FASE 2: INTEGRACIÓN CON TABLAS SUNAT** (2 días)
*Conectar el sistema PLE con las 12 tablas SUNAT*

#### **Task 2.1: Validador SUNAT Integrado**
📁 **Archivo**: `app/modules/accounting/ple_sunat_validator.py`

```python
class PLESunatValidator:
    """Validador que usa las 12 tablas SUNAT implementadas"""
    
    def __init__(self):
        self.tablas_service = TablasSUNATService()
    
    async def validar_codigo_cuenta(self, codigo: str) -> ValidationResult
    async def validar_tipo_comprobante(self, tipo: str) -> ValidationResult  
    async def validar_tipo_moneda(self, moneda: str) -> ValidationResult
    async def validar_datos_completos(self, datos_ple: Dict) -> CompleteValidationResult
    async def obtener_sugerencias(self, codigo_invalido: str) -> List[Suggestion]
```

**Integración con tablas existentes**:
- ✅ **`cuentas_contables`**: Validación de códigos de cuenta
- ✅ **`tipos_comprobantes_pago`**: Validación de tipos de comprobante
- ✅ **`tipos_moneda`**: Validación de códigos de moneda
- ✅ **`codigos_libros_registros`**: Validación del código "5" para Libro Diario

#### **Task 2.2: Enriquecedor de Datos**
📁 **Archivo**: `app/modules/accounting/ple_data_enricher.py`

```python
class PLEDataEnricher:
    """Enriquece datos contables con información de tablas SUNAT"""
    
    async def enriquecer_asiento(self, asiento: AsientoContable) -> EnrichedAsiento
    async def validar_y_completar_datos(self, datos: Dict) -> EnrichedData
    async def obtener_descripciones_sunat(self, codigos: List[str]) -> Dict[str, str]
    async def verificar_consistencia(self, datos_enriquecidos: Dict) -> ConsistencyResult
```

**Enriquecimiento automático**:
- ✅ Descripciones automáticas de códigos SUNAT
- ✅ Validación cruzada entre tablas
- ✅ Sugerencias de corrección automática
- ✅ Verificación de consistencia de datos

### 🔄 **FASE 3: SERVICIOS Y API** (1-2 días)
*Integrar con el sistema de servicios existente*

#### **Task 3.1: Extensión del LibroDiarioService**
📁 **Archivo**: `libro_diario_service.py` (actualización)

```python
# Nuevos métodos a agregar:
class LibroDiarioService:
    # ... métodos existentes ...
    
    async def exportar_a_ple(self, libro_id: str, opciones: PLEOptions) -> PLEExportResult
    async def validar_para_ple(self, libro_id: str) -> PLEValidationResult
    async def preview_ple(self, libro_id: str) -> PLEPreview
    async def obtener_estadisticas_ple(self, libro_id: str) -> PLEStats
    async def generar_reporte_validacion(self, libro_id: str) -> ValidationReport
```

#### **Task 3.2: Nuevos Endpoints API**
📁 **Archivo**: `routes.py` (actualización)

```python
# Nuevos endpoints a agregar:
@router.post("/libros-diario/{libro_id}/export-ple")
async def exportar_libro_diario_ple(...)

@router.get("/libros-diario/{libro_id}/validate-ple") 
async def validar_libro_diario_ple(...)

@router.get("/libros-diario/{libro_id}/preview-ple")
async def preview_archivo_ple(...)

@router.get("/libros-diario/{libro_id}/stats-ple")
async def estadisticas_ple(...)
```

#### **Task 3.3: Schemas Actualizados**
📁 **Archivo**: `schemas.py` (actualización)

```python
# Nuevos schemas:
class PLEExportOptions(BaseModel):
    incluir_asientos_cero: bool = True
    validar_con_sunat: bool = True
    formato_fecha: str = "DD/MM/YYYY"
    generar_zip: bool = True

class PLEExportResult(BaseModel):
    archivo_generado: str
    nombre_archivo: str
    tamaño_bytes: int
    total_asientos: int
    errores: List[str]
    warnings: List[str]
    
class PLEValidationResult(BaseModel):
    valido: bool
    errores_criticos: List[ValidationError]
    warnings: List[ValidationWarning]
    estadisticas: PLEStats
```

### 🧪 **FASE 4: VALIDACIONES Y TESTING** (1-2 días)
*Asegurar calidad y conformidad SUNAT*

#### **Task 4.1: Suite de Validaciones Completa**
📁 **Archivo**: `app/modules/accounting/ple_validation_suite.py`

```python
class PLEValidationSuite:
    """Suite completa de validaciones para PLE"""
    
    async def validacion_completa(self, datos_ple: Dict) -> CompleteValidationResult
    async def validar_estructura_archivo(self, contenido: str) -> StructureValidation
    async def validar_balanceo_contable(self, asientos: List) -> BalanceValidation
    async def validar_formatos_sunat(self, datos: Dict) -> FormatValidation
    async def validar_consistencia_temporal(self, datos: Dict) -> TemporalValidation
```

**Validaciones implementadas**:
- ✅ **Estructura**: Verificar formato de archivo TXT
- ✅ **Balanceo**: Debe = Haber por asiento y total
- ✅ **SUNAT**: Códigos válidos según tablas oficiales
- ✅ **Temporal**: Fechas consistentes y dentro del período
- ✅ **Integridad**: Campos obligatorios y formatos

#### **Task 4.2: Tests Unitarios Completos**
📁 **Archivo**: `tests/test_ple_complete.py`

```python
class TestPLESystem:
    """Tests completos del sistema PLE"""
    
    def test_generacion_archivo_ple(self)
    def test_validacion_con_tablas_sunat(self)
    def test_formateo_campos_sunat(self)
    def test_nomenclatura_archivos(self)
    def test_compresion_zip(self)
    def test_casos_edge_contables(self)
    def test_integracion_completa(self)
```

### 🎯 **FASE 5: FUNCIONALIDADES AVANZADAS** (1-2 días)
*Características adicionales para producción*

#### **Task 5.1: Sistema de Auditoría PLE**
📁 **Archivo**: `app/modules/accounting/ple_audit_system.py`

```python
class PLEAuditSystem:
    """Sistema de auditoría y trazabilidad PLE"""
    
    async def registrar_exportacion(self, export_data: PLEExportResult) -> AuditRecord
    async def obtener_historial_exportaciones(self, empresa_id: str) -> List[AuditRecord]
    async def verificar_integridad_archivo(self, archivo_path: str) -> IntegrityCheck
    async def generar_reporte_auditoria(self, periodo: DateRange) -> AuditReport
```

#### **Task 5.2: Optimizaciones y Performance**
📁 **Archivo**: `app/modules/accounting/ple_optimizer.py`

```python
class PLEOptimizer:
    """Optimizaciones de performance para grandes volúmenes"""
    
    async def procesar_en_lotes(self, asientos: List, batch_size: int = 1000)
    async def cache_validaciones_sunat(self, codigos: List[str])
    async def generar_archivo_streaming(self, datos_generator)
    async def comprimir_optimizado(self, archivo_txt: str) -> bytes
```

---

## 🛠️ ESTRUCTURA DE ARCHIVOS A CREAR

```
app/modules/accounting/
├── ple/                              # 📁 Nuevo directorio PLE
│   ├── __init__.py
│   ├── ple_analyzer.py              # 🔍 Análisis de datos
│   ├── ple_generator.py             # 📄 Generación de archivos
│   ├── ple_formatter.py             # ✏️ Formateo de campos
│   ├── ple_sunat_validator.py       # ✅ Validación con tablas SUNAT
│   ├── ple_data_enricher.py         # 🔧 Enriquecimiento de datos
│   ├── ple_validation_suite.py      # 🧪 Suite de validaciones
│   ├── ple_audit_system.py          # 📊 Auditoría y trazabilidad
│   └── ple_optimizer.py             # ⚡ Optimizaciones
├── libro_diario_service.py          # 🔄 Actualizar (métodos PLE)
├── routes.py                        # 🌐 Actualizar (endpoints PLE)
└── schemas.py                       # 📋 Actualizar (schemas PLE)

tests/
├── test_ple_complete.py             # 🧪 Tests completos PLE
├── test_ple_integration.py          # 🔗 Tests de integración
└── fixtures/                       # 📁 Datos de prueba
    ├── sample_libro_diario.json
    ├── expected_ple_output.txt
    └── sample_empresa_data.json
```

---

## 🎯 ENTREGABLES ESPERADOS

### 📄 **Archivos PLE Válidos**
- ✅ Archivo TXT en formato SUNAT 100% conforme
- ✅ Nomenclatura oficial automática
- ✅ Compresión ZIP lista para envío
- ✅ Validación previa completa

### 🌐 **API Endpoints Completos**
```http
POST /api/v1/accounting/libros-diario/{id}/export-ple
GET  /api/v1/accounting/libros-diario/{id}/validate-ple  
GET  /api/v1/accounting/libros-diario/{id}/preview-ple
GET  /api/v1/accounting/libros-diario/{id}/stats-ple
GET  /api/v1/accounting/ple/audit/exportaciones
```

### ✅ **Sistema de Validación Integrado**
- ✅ Validación automática con 12 tablas SUNAT
- ✅ Verificación de balanceo contable
- ✅ Detección de errores pre-exportación
- ✅ Sugerencias de corrección automática

### 📊 **Características Avanzadas**
- ✅ Auditoría completa de exportaciones
- ✅ Historial de archivos generados
- ✅ Estadísticas y métricas de calidad
- ✅ Optimización para grandes volúmenes

### 📚 **Documentación y Testing**
- ✅ Tests unitarios con cobertura >95%
- ✅ Tests de integración con datos reales
- ✅ Documentación API actualizada
- ✅ Ejemplos de uso y casos prácticos

---

## ⚡ PRÓXIMOS PASOS INMEDIATOS

### 🎯 **Paso 1: Validación del Plan**
- [ ] Confirmar prioridades y alcance
- [ ] Revisar estructura de archivos propuesta
- [ ] Validar integración con sistema existente

### 🚀 **Paso 2: Setup del Entorno PLE**
- [ ] Crear directorio `app/modules/accounting/ple/`
- [ ] Configurar imports y dependencias
- [ ] Crear branch específico: `feature/libro-diario-ple`

### 🔧 **Paso 3: Implementación Fase 1**
- [ ] Implementar `PLEAnalyzer` básico
- [ ] Crear `PLEGenerator` con formato básico
- [ ] Desarrollar `PLEFormatter` con validaciones

### 🧪 **Paso 4: Testing Iterativo**
- [ ] Crear datos de prueba representativos
- [ ] Implementar tests básicos
- [ ] Validar con archivos PLE reales

---

## 🏆 VENTAJAS COMPETITIVAS

### 🎯 **Integración Completa con SUNAT**
- ✅ **12 tablas SUNAT** ya implementadas y validadas
- ✅ **Validación automática** en tiempo real
- ✅ **Actualizaciones centralizadas** de códigos oficiales

### ⚡ **Performance y Escalabilidad**
- ✅ **Procesamiento asíncrono** para grandes volúmenes
- ✅ **Cache inteligente** de validaciones SUNAT
- ✅ **Generación streaming** para archivos grandes

### 🔒 **Calidad y Confiabilidad**
- ✅ **Suite de validaciones completa** antes de exportación
- ✅ **Auditoría completa** de todas las operaciones
- ✅ **Testing exhaustivo** con casos reales

### 🎨 **Developer Experience**
- ✅ **API bien documentada** con Swagger
- ✅ **Schemas Pydantic** para validación automática
- ✅ **Mensajes de error** claros y accionables

---

## ❓ PREGUNTAS PARA CONFIRMAR

1. **¿Te parece correcta la estructura propuesta?**
2. **¿Hay alguna prioridad específica de implementación?**
3. **¿Tienes datos reales de Libro Diario para testing?**
4. **¿Qué otras funcionalidades PLE serían útiles?**

---

*Este plan aprovecha al máximo la infraestructura de tablas SUNAT ya implementada, garantizando una integración robusta y un sistema PLE de alta calidad.*
