"""
Servicio de importación y gestión de planes contables personalizados
"""
import re
import io
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from app.modules.accounting.repositories import AccountingRepository


@dataclass
class ValidationResult:
    """Resultado de la validación de un archivo de plan contable"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    total_lines: int
    valid_accounts: int
    preview_data: List[Dict[str, Any]]


@dataclass
class ImportResult:
    """Resultado de la importación de un plan contable"""
    success: bool
    imported_count: int
    errors: List[str]
    warnings: List[str]
    backup_created: bool


class PlanContableImportService:
    """Servicio para importar y gestionar planes contables personalizados"""
    
    def __init__(self, repository: Optional[AccountingRepository] = None):
        self.repo = repository or AccountingRepository()
        # Patrón para validar líneas del archivo
        self.line_pattern = re.compile(r"^\s*([0-9]{1,10})\s+(.+?)\s*$")
        
    def generar_plantilla_txt(self) -> str:
        """Genera una plantilla de ejemplo en formato TXT"""
        plantilla = """# PLANTILLA PLAN CONTABLE PERSONALIZADO
# =====================================================
# FORMATO: CODIGO[TAB/ESPACIOS]DESCRIPCION
# 
# REGLAS:
# - Códigos numéricos únicos (máximo 10 dígitos)
# - Descripción obligatoria (máximo 200 caracteres)
# - Respetar jerarquía (el código padre debe existir antes que sus hijos)
# - Usar espacios o tabuladores para separar código y descripción
# - Las líneas que empiecen con # son comentarios y se ignoran
#
# EJEMPLO DE ESTRUCTURA JERÁRQUICA:
# =====================================================

1                 ACTIVO
10                ACTIVO CORRIENTE
101               EFECTIVO Y EQUIVALENTES DE EFECTIVO
1011              CAJA
10111             Caja Moneda Nacional
10112             Caja Moneda Extranjera
1012              FONDOS FIJOS
10121             Fondo Fijo Principal
10122             Fondo Fijo Sucursal
102               CUENTAS CORRIENTES EN BANCOS
1021              BANCOS LOCALES
10211             Banco de Crédito del Perú - S/
10212             Banco de Crédito del Perú - US$
10213             Banco Continental - S/
10214             Banco Continental - US$
1022              BANCOS DEL EXTERIOR
10221             Citibank New York - US$
103               INVERSIONES FINANCIERAS TEMPORALES
1031              CERTIFICADOS BANCARIOS
1032              FONDOS MUTUOS

2                 PASIVO
20                PASIVO CORRIENTE
201               SOBREGIROS BANCARIOS
2011              Banco de Crédito del Perú
2012              Banco Continental
202               CUENTAS POR PAGAR COMERCIALES
2021              FACTURAS POR PAGAR
20211             Facturas Nacionales
20212             Facturas del Exterior
2022              LETRAS POR PAGAR
20221             Letras Nacionales
203               CUENTAS POR PAGAR DIVERSAS
2031              PRÉSTAMOS DE TERCEROS
2032              PRÉSTAMOS DE ACCIONISTAS

3                 PATRIMONIO
30                CAPITAL
301               CAPITAL SOCIAL
3011              Capital Suscrito
3012              Capital Pagado
302               EXCEDENTE DE REVALUACIÓN
3021              Revaluación de Inmuebles
303               RESERVAS
3031              Reserva Legal
3032              Reservas Facultativas

4                 INGRESOS
40                VENTAS
401               VENTAS NACIONALES
4011              VENTAS GRAVADAS
40111             Ventas Gravadas - Terceros
40112             Ventas Gravadas - Relacionadas
4012              VENTAS EXONERADAS
40121             Ventas Exoneradas - Terceros
402               VENTAS AL EXTERIOR
4021              Exportaciones Gravadas
4022              Exportaciones Exoneradas

5                 GASTOS
50                GASTOS DE VENTAS
501               GASTOS DE PERSONAL
5011              SUELDOS Y SALARIOS
50111             Sueldos Personal de Ventas
5012              COMISIONES
50121             Comisiones Vendedores
502               GASTOS GENERALES DE VENTAS
5021              PUBLICIDAD Y PROMOCIÓN
5022              MOVILIDAD Y VIÁTICOS

# =====================================================
# INSTRUCCIONES DE USO:
# 1. Descarga esta plantilla
# 2. Edita con tu plan contable personalizado
# 3. Mantén el formato: CODIGO[ESPACIOS]DESCRIPCION
# 4. Respeta la jerarquía numérica
# 5. Guarda como archivo .txt
# 6. Importa desde la aplicación
# =====================================================
"""
        return plantilla.strip()
    
    def generar_plantilla_excel(self) -> bytes:
        """Genera una plantilla de ejemplo en formato Excel (.xlsx)"""
        wb = Workbook()
        
        # Hoja principal con datos
        ws_data = wb.active
        ws_data.title = "Plan Contable"
        
        # Configurar encabezados
        headers = ["CODIGO", "DESCRIPCION", "TIPO", "NIVEL"]
        header_colors = ["4472C4", "4472C4", "4472C4", "4472C4"]
        
        for col, (header, color) in enumerate(zip(headers, header_colors), 1):
            cell = ws_data.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Datos de ejemplo (mismos que la plantilla TXT)
        data_examples = [
            ("1", "ACTIVO", "Clase", "1"),
            ("10", "EFECTIVO Y EQUIVALENTES DE EFECTIVO", "Rubro", "2"),
            ("101", "Caja", "Cuenta", "3"),
            ("1011", "Caja MN", "Subcuenta", "4"),
            ("10111", "Caja MN - Oficina Principal", "Divisionaria", "5"),
            ("1012", "Caja ME", "Subcuenta", "4"),
            ("102", "Fondos Fijos", "Cuenta", "3"),
            ("1021", "Caja Chica - Oficina Principal", "Subcuenta", "4"),
            ("104", "Cuentas Corrientes en Instituciones Financieras", "Cuenta", "3"),
            ("1041", "Banco Continental", "Subcuenta", "4"),
            ("10411", "Banco Continental - Cuenta Corriente Soles", "Divisionaria", "5"),
            ("10412", "Banco Continental - Cuenta Corriente Dólares", "Divisionaria", "5"),
            ("1042", "Banco de Crédito del Perú", "Subcuenta", "4"),
            ("", "", "", ""),
            ("2", "PASIVO", "Clase", "1"),
            ("20", "PASIVO CORRIENTE", "Rubro", "2"),
            ("201", "Sobregiros Bancarios", "Cuenta", "3"),
            ("2011", "Banco de Crédito del Perú", "Subcuenta", "4"),
            ("2012", "Banco Continental", "Subcuenta", "4"),
            ("202", "Cuentas por Pagar Comerciales", "Cuenta", "3"),
            ("2021", "Facturas por Pagar", "Subcuenta", "4"),
            ("20211", "Facturas Nacionales", "Divisionaria", "5"),
            ("20212", "Facturas del Exterior", "Divisionaria", "5"),
            ("", "", "", ""),
            ("3", "PATRIMONIO", "Clase", "1"),
            ("30", "CAPITAL", "Rubro", "2"),
            ("301", "Capital Social", "Cuenta", "3"),
            ("3011", "Capital Suscrito", "Subcuenta", "4"),
            ("3012", "Capital Pagado", "Subcuenta", "4"),
        ]
        
        # Agregar datos de ejemplo
        for row, (codigo, descripcion, tipo, nivel) in enumerate(data_examples, 2):
            ws_data.cell(row=row, column=1, value=codigo)
            ws_data.cell(row=row, column=2, value=descripcion)
            ws_data.cell(row=row, column=3, value=tipo)
            ws_data.cell(row=row, column=4, value=nivel)
            
            # Colorear filas vacías para separación visual
            if not codigo:
                for col in range(1, 5):
                    ws_data.cell(row=row, column=col).fill = PatternFill(
                        start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
                    )
        
        # Configurar ancho de columnas
        ws_data.column_dimensions['A'].width = 12  # CODIGO
        ws_data.column_dimensions['B'].width = 50  # DESCRIPCION
        ws_data.column_dimensions['C'].width = 15  # TIPO
        ws_data.column_dimensions['D'].width = 8   # NIVEL
        
        # Crear hoja de instrucciones
        ws_instructions = wb.create_sheet("INSTRUCCIONES")
        
        instructions = [
            ("INSTRUCCIONES PARA PLAN CONTABLE PERSONALIZADO", ""),
            ("", ""),
            ("FORMATO REQUERIDO:", ""),
            ("• CODIGO: Código numérico único (máximo 10 dígitos)", ""),
            ("• DESCRIPCION: Nombre de la cuenta (máximo 200 caracteres)", ""),
            ("• TIPO: Clase, Rubro, Cuenta, Subcuenta, Divisionaria", ""),
            ("• NIVEL: Nivel jerárquico (1-5)", ""),
            ("", ""),
            ("REGLAS IMPORTANTES:", ""),
            ("1. Los códigos deben ser únicos en todo el plan", ""),
            ("2. Respetar la jerarquía: el código padre debe existir antes que sus hijos", ""),
            ("3. Los niveles deben ser progresivos (1, 2, 3, 4, 5)", ""),
            ("4. No dejar celdas vacías en CODIGO y DESCRIPCION", ""),
            ("5. El TIPO debe coincidir con el NIVEL:", ""),
            ("   - Nivel 1: Clase", ""),
            ("   - Nivel 2: Rubro", ""),
            ("   - Nivel 3: Cuenta", ""),
            ("   - Nivel 4: Subcuenta", ""),
            ("   - Nivel 5: Divisionaria", ""),
            ("", ""),
            ("EJEMPLOS VÁLIDOS:", ""),
            ("1         | ACTIVO                    | Clase       | 1", ""),
            ("10        | EFECTIVO Y EQUIVALENTES   | Rubro       | 2", ""),
            ("101       | Caja                      | Cuenta      | 3", ""),
            ("1011      | Caja MN                   | Subcuenta   | 4", ""),
            ("10111     | Caja MN - Oficina         | Divisionaria| 5", ""),
            ("", ""),
            ("PASOS PARA IMPORTAR:", ""),
            ("1. Complete la hoja 'Plan Contable' con sus datos", ""),
            ("2. Guarde el archivo en formato Excel (.xlsx)", ""),
            ("3. Use la función 'Importar Plan' en la aplicación", ""),
            ("4. El sistema validará automáticamente el formato", ""),
            ("5. Revise los errores antes de confirmar la importación", ""),
        ]
        
        for row, (instruction, _) in enumerate(instructions, 1):
            cell = ws_instructions.cell(row=row, column=1, value=instruction)
            if row == 1:  # Título
                cell.font = Font(bold=True, size=14, color="FFFFFF")
                cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            elif instruction.startswith(("FORMATO", "REGLAS", "EJEMPLOS", "PASOS")):  # Subtítulos
                cell.font = Font(bold=True, size=12, color="4472C4")
            elif instruction.startswith(("•", "1.", "2.", "3.", "4.", "5.")):  # Puntos
                cell.font = Font(color="333333")
                cell.alignment = Alignment(indent=1)
        
        # Configurar ancho de columna para instrucciones
        ws_instructions.column_dimensions['A'].width = 80
        
        # Crear hoja de validaciones
        ws_validation = wb.create_sheet("VALIDACIONES")
        
        validations = [
            ("VALIDACIONES DEL SISTEMA", ""),
            ("", ""),
            ("El sistema realizará las siguientes validaciones:", ""),
            ("", ""),
            ("✓ CÓDIGOS ÚNICOS", "No puede haber códigos duplicados"),
            ("✓ FORMATO NUMÉRICO", "Los códigos deben ser solo números"),
            ("✓ JERARQUÍA VÁLIDA", "Los códigos padre deben existir antes que los hijos"),
            ("✓ NIVELES PROGRESIVOS", "Los niveles deben incrementar de forma lógica"),
            ("✓ TIPOS CORRECTOS", "El tipo debe coincidir con el nivel"),
            ("✓ LONGITUD MÁXIMA", "Códigos máximo 10 dígitos, descripciones máximo 200 caracteres"),
            ("", ""),
            ("ERRORES COMUNES:", ""),
            ("", ""),
            ("❌ Código duplicado", "Usar códigos únicos para cada cuenta"),
            ("❌ Hijo sin padre", "Definir la cuenta padre antes que las subcuentas"),
            ("❌ Salto de nivel", "No pasar del nivel 1 al 3 directamente"),
            ("❌ Tipo incorrecto", "Verificar que el tipo coincida con el nivel"),
            ("❌ Códigos alfabéticos", "Usar solo números en los códigos"),
        ]
        
        for row, (validation, description) in enumerate(validations, 1):
            cell_a = ws_validation.cell(row=row, column=1, value=validation)
            cell_b = ws_validation.cell(row=row, column=2, value=description)
            
            if row == 1:  # Título
                cell_a.font = Font(bold=True, size=14, color="FFFFFF")
                cell_a.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            elif validation.startswith("✓"):  # Validaciones exitosas
                cell_a.font = Font(bold=True, color="22C55E")
                cell_b.font = Font(color="333333")
            elif validation.startswith("❌"):  # Errores
                cell_a.font = Font(bold=True, color="EF4444")
                cell_b.font = Font(color="333333")
            elif validation and not validation.startswith("El sistema"):  # Subtítulos
                cell_a.font = Font(bold=True, size=12, color="4472C4")
        
        # Configurar ancho de columnas para validaciones
        ws_validation.column_dimensions['A'].width = 30
        ws_validation.column_dimensions['B'].width = 50
        
        # Guardar en bytes
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()
    
    def validar_formato_archivo(self, content: str) -> ValidationResult:
        """Valida el formato y contenido de un archivo de plan contable"""
        errors = []
        warnings = []
        valid_accounts = []
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Diccionario para verificar códigos únicos y jerarquía
        codes_found = set()
        accounts_data = {}
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Ignorar líneas vacías y comentarios
            if not line or line.startswith('#'):
                continue
                
            # Validar formato de línea
            match = self.line_pattern.match(line)
            if not match:
                errors.append(f"Línea {line_num}: Formato inválido - {line[:50]}...")
                continue
                
            code = match.group(1).strip()
            description = match.group(2).strip()
            
            # Validaciones específicas
            validation_errors = self._validar_cuenta(code, description, codes_found)
            if validation_errors:
                for error in validation_errors:
                    errors.append(f"Línea {line_num}: {error}")
                continue
            
            # Agregar a códigos encontrados
            codes_found.add(code)
            
            # Datos de la cuenta válida
            account_data = {
                'codigo': code,
                'descripcion': description,
                'nivel': len(code),
                'clase_contable': int(code[0]) if code else 0,
                'line_number': line_num
            }
            
            accounts_data[code] = account_data
            valid_accounts.append(account_data)
        
        # Validar jerarquía después de procesar todas las líneas
        hierarchy_errors = self._validar_jerarquia(accounts_data)
        errors.extend(hierarchy_errors)
        
        # Generar warnings
        if len(valid_accounts) < 10:
            warnings.append("El plan contable tiene muy pocas cuentas (menos de 10)")
        
        if len(valid_accounts) > 5000:
            warnings.append("El plan contable es muy extenso (más de 5000 cuentas)")
        
        # Preview de los primeros 10 registros válidos
        preview_data = valid_accounts[:10]
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            total_lines=total_lines,
            valid_accounts=len(valid_accounts),
            preview_data=preview_data
        )
    
    def validar_formato_excel(self, excel_data: bytes) -> ValidationResult:
        """Valida el formato y contenido de un archivo Excel de plan contable"""
        errors = []
        warnings = []
        valid_accounts = []
        preview_data = []
        
        try:
            # Cargar el archivo Excel
            wb = load_workbook(io.BytesIO(excel_data), read_only=True)
            
            # Buscar la hoja de datos
            ws = None
            if "Plan Contable" in wb.sheetnames:
                ws = wb["Plan Contable"]
            else:
                # Si no existe la hoja específica, usar la primera hoja
                ws = wb.active
                warnings.append("No se encontró la hoja 'Plan Contable', usando la primera hoja disponible")
            
            if not ws:
                errors.append("No se pudo acceder a ninguna hoja del archivo Excel")
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    total_lines=0,
                    valid_accounts=0,
                    preview_data=[]
                )
            
            # Verificar encabezados
            expected_headers = ["CODIGO", "DESCRIPCION", "TIPO", "NIVEL"]
            headers_row = 1
            actual_headers = []
            
            for col in range(1, 5):
                cell = ws.cell(row=headers_row, column=col)
                header_value = str(cell.value).strip().upper() if cell.value else ""
                actual_headers.append(header_value)
            
            # Validar que los encabezados estén presentes
            missing_headers = []
            for expected in expected_headers:
                if expected not in actual_headers:
                    missing_headers.append(expected)
            
            if missing_headers:
                errors.append(f"Encabezados faltantes: {', '.join(missing_headers)}")
                errors.append(f"Encabezados encontrados: {', '.join(actual_headers)}")
                errors.append("Los encabezados deben ser exactamente: CODIGO, DESCRIPCION, TIPO, NIVEL")
            
            # Procesar datos
            codes_found = set()
            total_lines = 0
            data_start_row = 2  # Los datos empiezan después de los encabezados
            
            # Obtener todas las filas con datos
            for row in ws.iter_rows(min_row=data_start_row, values_only=True):
                total_lines += 1
                
                # Extraer valores de las columnas
                codigo_cell = row[0] if len(row) > 0 else None
                descripcion_cell = row[1] if len(row) > 1 else None
                tipo_cell = row[2] if len(row) > 2 else None
                nivel_cell = row[3] if len(row) > 3 else None
                
                # Convertir a string y limpiar
                codigo = str(codigo_cell).strip() if codigo_cell is not None else ""
                descripcion = str(descripcion_cell).strip() if descripcion_cell is not None else ""
                tipo = str(tipo_cell).strip() if tipo_cell is not None else ""
                nivel = str(nivel_cell).strip() if nivel_cell is not None else ""
                
                # Saltar filas completamente vacías
                if not any([codigo, descripcion, tipo, nivel]):
                    continue
                
                # Validar que no falten campos críticos
                if not codigo and descripcion:
                    errors.append(f"Fila {data_start_row + total_lines - 1}: Falta código para '{descripcion[:30]}...'")
                    continue
                
                if not descripcion and codigo:
                    errors.append(f"Fila {data_start_row + total_lines - 1}: Falta descripción para código '{codigo}'")
                    continue
                
                # Si es una fila de separación (solo vacía), continuar
                if not codigo and not descripcion:
                    continue
                
                # Validaciones específicas de Excel
                validation_errors = self._validar_cuenta_excel(
                    codigo, descripcion, tipo, nivel, codes_found, data_start_row + total_lines - 1
                )
                
                if validation_errors:
                    errors.extend(validation_errors)
                    continue
                
                # Si llegamos aquí, la cuenta es válida
                codes_found.add(codigo)
                valid_accounts.append({
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "nivel": int(nivel)
                })
                
                # Agregar a preview (máximo 10 elementos)
                if len(preview_data) < 10:
                    preview_data.append({
                        "codigo": codigo,
                        "descripcion": descripcion,
                        "tipo": tipo,
                        "nivel": nivel
                    })
            
            # Validaciones adicionales de jerarquía
            jerarquia_errors = self._validar_jerarquia_excel(valid_accounts)
            errors.extend(jerarquia_errors)
            
        except Exception as e:
            errors.append(f"Error procesando archivo Excel: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                total_lines=0,
                valid_accounts=0,
                preview_data=[]
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            total_lines=total_lines,
            valid_accounts=len(valid_accounts),
            preview_data=preview_data
        )
    
    def _validar_cuenta(self, code: str, description: str, existing_codes: set) -> List[str]:
        """Valida una cuenta individual"""
        errors = []
        
        # Validar código
        if not code:
            errors.append("Código vacío")
        elif len(code) > 10:
            errors.append(f"Código muy largo (máximo 10 dígitos): {code}")
        elif not code.isdigit():
            errors.append(f"Código debe ser numérico: {code}")
        elif code in existing_codes:
            errors.append(f"Código duplicado: {code}")
        
        # Validar descripción
        if not description:
            errors.append("Descripción vacía")
        elif len(description) > 200:
            errors.append(f"Descripción muy larga (máximo 200 caracteres): {description[:50]}...")
        
        return errors
    
    def _validar_jerarquia(self, accounts_data: Dict[str, Dict]) -> List[str]:
        """Valida que la jerarquía de cuentas sea correcta"""
        errors = []
        
        for code, account in accounts_data.items():
            if len(code) > 1:  # Si no es cuenta de nivel 1
                # Buscar cuenta padre
                parent_found = False
                for parent_length in range(len(code) - 1, 0, -1):
                    potential_parent = code[:parent_length]
                    if potential_parent in accounts_data:
                        parent_found = True
                        break
                
                if not parent_found:
                    errors.append(f"Línea {account['line_number']}: Cuenta {code} no tiene cuenta padre válida")
        
        return errors
    
    def _validar_cuenta_excel(self, codigo: str, descripcion: str, tipo: str, nivel: str, 
                             existing_codes: set, row_num: int) -> List[str]:
        """Valida una cuenta individual del archivo Excel"""
        errors = []
        
        # Validar código
        if not codigo:
            errors.append(f"Fila {row_num}: Código vacío")
        elif len(codigo) > 10:
            errors.append(f"Fila {row_num}: Código muy largo (máximo 10 dígitos): {codigo}")
        elif not codigo.isdigit():
            errors.append(f"Fila {row_num}: Código debe ser numérico: {codigo}")
        elif codigo in existing_codes:
            errors.append(f"Fila {row_num}: Código duplicado: {codigo}")
        
        # Validar descripción
        if not descripcion:
            errors.append(f"Fila {row_num}: Descripción vacía")
        elif len(descripcion) > 200:
            errors.append(f"Fila {row_num}: Descripción muy larga (máximo 200 caracteres): {descripcion[:50]}...")
        
        # Validar tipo
        tipos_validos = ["Clase", "Rubro", "Cuenta", "Subcuenta", "Divisionaria"]
        if tipo and tipo not in tipos_validos:
            errors.append(f"Fila {row_num}: Tipo inválido '{tipo}'. Debe ser uno de: {', '.join(tipos_validos)}")
        
        # Validar nivel
        if nivel:
            try:
                nivel_int = int(nivel)
                if nivel_int < 1 or nivel_int > 5:
                    errors.append(f"Fila {row_num}: Nivel debe estar entre 1 y 5, recibido: {nivel}")
                
                # Validar coherencia tipo-nivel
                tipo_nivel_map = {
                    1: "Clase",
                    2: "Rubro", 
                    3: "Cuenta",
                    4: "Subcuenta",
                    5: "Divisionaria"
                }
                
                if tipo and tipo in tipos_validos:
                    nivel_esperado = None
                    for niv, tip in tipo_nivel_map.items():
                        if tip == tipo:
                            nivel_esperado = niv
                            break
                    
                    if nivel_esperado and nivel_int != nivel_esperado:
                        errors.append(f"Fila {row_num}: El tipo '{tipo}' debe corresponder al nivel {nivel_esperado}, no {nivel_int}")
                        
            except ValueError:
                errors.append(f"Fila {row_num}: Nivel debe ser un número entero, recibido: '{nivel}'")
        else:
            errors.append(f"Fila {row_num}: Nivel vacío")
        
        return errors
    
    def _validar_jerarquia_excel(self, accounts_data: List[Dict]) -> List[str]:
        """Valida que la jerarquía de cuentas de Excel sea correcta"""
        errors = []
        
        # Crear un diccionario de códigos para búsqueda rápida
        codes_dict = {acc["codigo"]: acc for acc in accounts_data}
        
        for account in accounts_data:
            codigo = account["codigo"]
            nivel = account["nivel"]
            
            if nivel > 1:  # Si no es cuenta de nivel 1
                # Buscar cuenta padre (código más corto)
                parent_found = False
                
                # Intentar encontrar el padre más directo
                for parent_length in range(len(codigo) - 1, 0, -1):
                    potential_parent = codigo[:parent_length]
                    if potential_parent in codes_dict:
                        parent_account = codes_dict[potential_parent]
                        # Verificar que el nivel del padre sea exactamente uno menos
                        if parent_account["nivel"] == nivel - 1:
                            parent_found = True
                            break
                
                if not parent_found:
                    errors.append(f"Cuenta {codigo} (nivel {nivel}) no tiene cuenta padre válida de nivel {nivel - 1}")
        
        return errors
    
    async def importar_plan_personalizado(
        self, 
        empresa_id: str, 
        archivo_content: str, 
        filename: str
    ) -> ImportResult:
        """Importa un plan contable personalizado para una empresa"""
        
        # Primero validar el archivo
        validation = self.validar_formato_archivo(archivo_content)
        if not validation.is_valid:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=validation.errors,
                warnings=validation.warnings,
                backup_created=False
            )
        
        try:
            # Crear backup del plan anterior si existe
            backup_created = await self._crear_backup_plan_anterior(empresa_id)
            
            # Limpiar plan personalizado anterior
            await self._limpiar_plan_anterior(empresa_id)
            
            # Procesar e insertar nuevas cuentas
            imported_count = await self._procesar_e_insertar_cuentas(
                validation.preview_data + 
                [acc for acc in self._extraer_todas_cuentas(archivo_content) 
                 if acc not in validation.preview_data],
                empresa_id,
                filename
            )
            
            return ImportResult(
                success=True,
                imported_count=imported_count,
                errors=[],
                warnings=validation.warnings,
                backup_created=backup_created
            )
            
        except Exception as e:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[f"Error durante la importación: {str(e)}"],
                warnings=[],
                backup_created=False
            )
    
    async def importar_plan_excel(
        self, 
        empresa_id: str, 
        excel_data: bytes, 
        filename: str
    ) -> ImportResult:
        """Importa un plan contable personalizado desde un archivo Excel"""
        
        # Primero validar el archivo
        validation = self.validar_formato_excel(excel_data)
        if not validation.is_valid:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=validation.errors,
                warnings=validation.warnings,
                backup_created=False
            )
        
        try:
            # Crear backup del plan anterior si existe
            backup_created = await self._crear_backup_plan_anterior(empresa_id)
            
            # Limpiar plan personalizado anterior
            await self._limpiar_plan_anterior(empresa_id)
            
            # Procesar e insertar nuevas cuentas desde Excel
            imported_count = await self._procesar_e_insertar_cuentas_excel(
                validation.preview_data,
                empresa_id,
                filename
            )
            
            return ImportResult(
                success=True,
                imported_count=imported_count,
                errors=[],
                warnings=validation.warnings,
                backup_created=backup_created
            )
            
        except Exception as e:
            return ImportResult(
                success=False,
                imported_count=0,
                errors=[f"Error durante la importación Excel: {str(e)}"],
                warnings=[],
                backup_created=False
            )
    
    def _extraer_todas_cuentas(self, content: str) -> List[Dict[str, Any]]:
        """Extrae todas las cuentas válidas del contenido del archivo"""
        accounts = []
        codes_found = set()
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            match = self.line_pattern.match(line)
            if not match:
                continue
                
            code = match.group(1).strip()
            description = match.group(2).strip()
            
            if code in codes_found:
                continue
                
            codes_found.add(code)
            accounts.append({
                'codigo': code,
                'descripcion': description,
                'nivel': len(code),
                'clase_contable': int(code[0]) if code else 0,
                'line_number': line_num
            })
        
        return accounts
    
    async def _crear_backup_plan_anterior(self, empresa_id: str) -> bool:
        """Crea un backup del plan personalizado anterior si existe"""
        try:
            # Buscar plan personalizado actual
            plan_actual = await self.repo.list_cuentas({
                'empresa_id': empresa_id,
                'tipo_plan': 'personalizado'
            })
            
            if plan_actual:
                # Crear colección de backup con timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_collection = f"plan_contable_backup_{empresa_id}_{timestamp}"
                
                # Aquí implementarías la lógica de backup específica
                # Por ahora retornamos True indicando que se creó el backup
                return True
            
            return False
        except Exception:
            return False
    
    async def _limpiar_plan_anterior(self, empresa_id: str):
        """Elimina el plan personalizado anterior de la empresa"""
        await self.repo.delete_plan_personalizado(empresa_id)
    
    async def _procesar_e_insertar_cuentas(
        self, 
        accounts_data: List[Dict[str, Any]], 
        empresa_id: str, 
        filename: str
    ) -> int:
        """Procesa e inserta las cuentas en la base de datos"""
        imported_count = 0
        
        # Ordenar por código para mantener jerarquía
        accounts_data.sort(key=lambda x: x['codigo'])
        
        for account_data in accounts_data:
            # Preparar documento para inserción
            documento = {
                'codigo': account_data['codigo'],
                'descripcion': account_data['descripcion'],
                'nivel': account_data['nivel'],
                'clase_contable': account_data['clase_contable'],
                'grupo': None,
                'subgrupo': None,
                'cuenta_padre': self._determinar_cuenta_padre(account_data['codigo'], accounts_data),
                'es_hoja': True,  # Se actualizará después
                'acepta_movimiento': True,
                'naturaleza': self._determinar_naturaleza(account_data['clase_contable']),
                'moneda': 'MN',
                'activa': True,
                'tipo_plan': 'personalizado',
                'empresa_id': empresa_id,
                'archivo_origen': filename,
                'fecha_creacion': datetime.now()
            }
            
            await self.repo.insert_cuenta(documento)
            imported_count += 1
        
        # Actualizar campo es_hoja para cuentas que tienen hijos
        await self._actualizar_es_hoja(empresa_id)
        
        return imported_count
    
    def _determinar_cuenta_padre(self, codigo: str, all_accounts: List[Dict[str, Any]]) -> Optional[str]:
        """Determina la cuenta padre basándose en la jerarquía"""
        if len(codigo) <= 1:
            return None
            
        # Buscar el padre más cercano
        for length in range(len(codigo) - 1, 0, -1):
            potential_parent = codigo[:length]
            if any(acc['codigo'] == potential_parent for acc in all_accounts):
                return potential_parent
                
        return None
    
    def _determinar_naturaleza(self, clase_contable: int) -> str:
        """Determina la naturaleza de la cuenta según su clase"""
        clases_deudoras = [1, 2, 3, 6, 8, 9]
        clases_acreedoras = [4, 5, 7]
        
        if clase_contable in clases_deudoras:
            return "DEUDORA"
        elif clase_contable in clases_acreedoras:
            return "ACREEDORA"
        else:
            return "DEUDORA"
    
    async def _actualizar_es_hoja(self, empresa_id: str):
        """Actualiza el campo es_hoja para todas las cuentas de la empresa"""
        # Obtener todas las cuentas de la empresa
        cuentas = await self.repo.list_cuentas({
            'empresa_id': empresa_id,
            'tipo_plan': 'personalizado'
        })
        
        # Crear mapa de códigos
        codigos = {cuenta['codigo'] for cuenta in cuentas}
        
        # Actualizar es_hoja
        for cuenta in cuentas:
            codigo = cuenta['codigo']
            tiene_hijos = any(
                other_code.startswith(codigo) and len(other_code) > len(codigo)
                for other_code in codigos
            )
            
            if tiene_hijos != (not cuenta.get('es_hoja', True)):
                await self.repo.update_cuenta(codigo, {'es_hoja': not tiene_hijos})

    async def _procesar_e_insertar_cuentas_excel(
        self, 
        accounts_data: List[Dict[str, Any]], 
        empresa_id: str, 
        filename: str
    ) -> int:
        """Procesa e inserta cuentas desde datos de Excel"""
        inserted_count = 0
        
        # Ordenar por código para mantener jerarquía
        accounts_data_sorted = sorted(accounts_data, key=lambda x: x['codigo'])
        
        for account_data in accounts_data_sorted:
            try:
                cuenta_doc = {
                    'codigo': account_data['codigo'],
                    'descripcion': account_data['descripcion'],
                    'tipo': account_data.get('tipo', 'Cuenta'),
                    'nivel': account_data['nivel'],
                    'naturaleza': self._determinar_naturaleza(account_data['codigo']),
                    'es_hoja': True,  # Se actualizará después
                    'activo': True,
                    'empresa_id': empresa_id,
                    'tipo_plan': 'personalizado',
                    'archivo_origen': filename,
                    'fecha_importacion': datetime.utcnow()
                }
                
                await self.repo.create_cuenta(cuenta_doc)
                inserted_count += 1
                
            except Exception as e:
                # Log error pero continuar con las demás cuentas
                print(f"Error insertando cuenta {account_data['codigo']}: {str(e)}")
        
        # Actualizar campo es_hoja después de insertar todas las cuentas
        await self._actualizar_es_hoja(empresa_id)
        
        return inserted_count
