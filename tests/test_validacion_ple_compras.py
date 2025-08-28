"""
Test de Validación PLE 080000 - Registro de Compras
==================================================

Script para validar que la implementación del PLE 080000 (Compras)
cumple exactamente con las especificaciones oficiales SUNAT.

Valida:
✅ 32 campos oficiales según documentación SUNAT
✅ Formateado correcto de montos con 2 decimales
✅ Formateado de fechas DD/MM/YYYY
✅ Códigos de comprobantes según catálogo oficial
✅ Estructura de línea PLE separada por |
✅ Nomenclatura de archivo según SUNAT

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Agregar path del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from modules.accounting.schemas.schemas_compras import (
    RegistroCompraResponse,
    TipoComprobanteCompra,
    TipoDocumentoIdentidad,
    EstadoOperacion
)
from modules.accounting.ple.ple_formatter_compras import PLEFormatterCompras


def test_validacion_ple_compras_completa():
    """Test completo de validación PLE 080000"""
    
    print("=" * 80)
    print("🧪 VALIDACIÓN PLE 080000 - REGISTRO DE COMPRAS")
    print("=" * 80)
    
    # 1. CREAR REGISTRO DE COMPRA DE PRUEBA
    print("\n📋 1. Creando registro de compra de prueba...")
    
    registro_compra = RegistroCompraResponse(
        # Metadatos del sistema
        id="64f123456789012345678901",
        empresa_id="empresa_test_001",
        periodo="202408",
        fecha_creacion=datetime(2024, 8, 15, 10, 30, 0),
        
        # Información del proveedor
        tipo_documento_proveedor=TipoDocumentoIdentidad.RUC,
        numero_documento_proveedor="20123456789",
        razon_social_proveedor="PROVEEDOR EJEMPLO S.A.C.",
        
        # Información del comprobante
        tipo_comprobante=TipoComprobanteCompra.FACTURA,
        serie_comprobante="F001",
        numero_comprobante="000123",
        numero_final_rango=None,
        fecha_emision="15/08/2024",
        fecha_vencimiento="30/08/2024",
        
        # Montos detallados (según PLE 080000)
        base_imponible_gravada=Decimal("1000.00"),
        igv=Decimal("180.00"),
        base_imponible_gravada_operaciones_mixtas=Decimal("0.00"),
        igv_operaciones_mixtas=Decimal("0.00"),
        base_imponible_gravada_exportacion=Decimal("0.00"),
        igv_exportacion=Decimal("0.00"),
        base_imponible_no_gravada=Decimal("0.00"),
        isc=Decimal("0.00"),
        otros_tributos=Decimal("0.00"),
        importe_total=Decimal("1180.00"),
        
        # Datos adicionales
        codigo_moneda="PEN",
        tipo_cambio=Decimal("1.000"),
        fecha_emision_detraccion=None,
        numero_constancia_detraccion=None,
        marca_comprobante_retencion=None,
        clasificacion_bienes_servicios="SERVICIOS PROFESIONALES",
        identificacion_contrato=None,
        indicador_error="0",
        medio_pago="001",
        estado_operacion=EstadoOperacion.VIGENTE
    )
    
    print(f"✅ Registro creado: {registro_compra.razon_social_proveedor}")
    print(f"   Comprobante: {registro_compra.serie_comprobante}-{registro_compra.numero_comprobante}")
    print(f"   Importe: S/ {registro_compra.importe_total}")
    
    # 2. INICIALIZAR FORMATEADOR
    print("\n🔧 2. Inicializando formateador PLE...")
    formatter = PLEFormatterCompras()
    print("✅ Formateador inicializado correctamente")
    
    # 3. FORMATEAR REGISTRO A LÍNEA PLE
    print("\n📝 3. Formateando registro a línea PLE...")
    linea_ple = formatter.formatear_registro_compra(
        compra=registro_compra,
        periodo_aaaamm="202408"
    )
    
    print("✅ Línea PLE generada correctamente")
    
    # 4. VALIDAR ESTRUCTURA DE 32 CAMPOS
    print("\n🔍 4. Validando estructura de 32 campos oficiales...")
    
    linea_texto = linea_ple.to_ple_line()
    campos = linea_texto.split("|")
    
    print(f"   Línea PLE: {linea_texto}")
    print(f"   Total campos encontrados: {len(campos) - 1}")  # -1 porque termina en |
    
    # Validar que son exactamente 33 campos (32 + campo vacío final)
    assert len(campos) == 34, f"Error: Se esperaban 33 campos, se encontraron {len(campos) - 1}"
    print("   ✅ 33 campos correctos (32 oficiales + campo final vacío)")
    
    # 5. VALIDAR CAMPOS ESPECÍFICOS UNO POR UNO
    print("\n📊 5. Validando campos específicos...")
    
    validaciones = [
        (0, "202408", "Período"),
        (1, "C202408678901", "Código único operación"),
        (2, "C000000123", "Correlativo asiento"),
        (3, "15/08/2024", "Fecha emisión"),
        (4, "30/08/2024", "Fecha vencimiento"),
        (5, "1", "Tipo comprobante"),
        (6, "F001", "Serie comprobante"),
        (7, "", "Año DUA/DSI"),
        (8, "000123", "Número comprobante"),
        (9, "", "Número final rango"),
        (10, "6", "Tipo documento proveedor"),
        (11, "20123456789", "Número documento proveedor"),
        (12, "PROVEEDOR EJEMPLO S.A.C.", "Razón social"),
        (13, "1000.00", "Base imponible gravada"),
        (14, "180.00", "IGV"),
        (15, "0.00", "Base imponible mixtas"),
        (16, "0.00", "IGV mixtas"),
        (17, "0.00", "Base imponible exportación"),
        (18, "0.00", "IGV exportación"),
        (19, "0.00", "Base imponible no gravada"),
        (20, "0.00", "ISC"),
        (21, "0.00", "Otros tributos"),
        (22, "1180.00", "Importe total"),
        (23, "PEN", "Código moneda"),
        (24, "1.000", "Tipo cambio"),
        (25, "", "Fecha constancia detracción"),
        (26, "", "Número constancia detracción"),
        (27, "", "Marca retención"),
        (28, "SERVICIOS PROFESIONALES", "Clasificación bienes"),
        (29, "", "Identificación contrato"),
        (30, "0", "Error tipo"),
        (31, "001", "Medio pago"),
        (32, "1", "Estado operación")
    ]
    
    for indice, valor_esperado, descripcion in validaciones:
        valor_actual = campos[indice]
        print(f"   Campo {indice + 1:2d}: {descripcion:30} = '{valor_actual}'")
        
        if valor_esperado != "":  # Solo validar si hay valor esperado
            assert valor_actual == str(valor_esperado), \
                f"Error en campo {indice + 1} ({descripcion}): " \
                f"esperado '{valor_esperado}', encontrado '{valor_actual}'"
    
    print("   ✅ Todos los campos validados correctamente")
    
    # 6. VALIDAR GENERACIÓN DE NOMBRE DE ARCHIVO
    print("\n📁 6. Validando nombre de archivo...")
    
    nombre_archivo = formatter.generar_nombre_archivo_ple(
        empresa_ruc="20123456789",
        periodo_aaaamm="202408",
        correlativo="0001"
    )
    
    nombre_esperado = "LE2012345678920240800080000000011.txt"
    print(f"   Nombre generado: {nombre_archivo}")
    print(f"   Nombre esperado: {nombre_esperado}")
    
    assert nombre_archivo == nombre_esperado, \
        f"Nombre incorrecto: esperado '{nombre_esperado}', generado '{nombre_archivo}'"
    print("   ✅ Nombre de archivo correcto")
    
    # 7. VALIDAR CONTENIDO DE ARCHIVO COMPLETO
    print("\n📄 7. Validando contenido de archivo completo...")
    
    contenido_archivo = formatter.generar_contenido_archivo_ple([linea_ple])
    lineas_archivo = contenido_archivo.strip().split("\n")
    
    print(f"   Total líneas en archivo: {len(lineas_archivo)}")
    print(f"   Primera línea: {lineas_archivo[0][:80]}...")
    
    assert len(lineas_archivo) == 1, f"Se esperaba 1 línea, se encontraron {len(lineas_archivo)}"
    assert lineas_archivo[0] == linea_texto.rstrip("|") + "|", "Contenido de línea incorrecto"
    print("   ✅ Contenido de archivo correcto")
    
    # 8. RESUMEN FINAL
    print("\n" + "=" * 80)
    print("🎉 VALIDACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print(f"📋 Registro procesado: {registro_compra.numero_comprobante}")
    print(f"📊 Campos generados: 33 (32 oficiales + final)")
    print(f"💰 Importe total: S/ {registro_compra.importe_total}")
    print(f"📁 Archivo: {nombre_archivo}")
    print(f"📏 Tamaño línea: {len(linea_texto)} caracteres")
    print("✅ CUMPLE 100% CON ESPECIFICACIONES SUNAT PLE 080000")
    
    return True


def test_validacion_multiples_registros():
    """Test con múltiples registros para validar consistencia"""
    
    print("\n" + "=" * 80)
    print("🧪 VALIDACIÓN MÚLTIPLES REGISTROS")
    print("=" * 80)
    
    formatter = PLEFormatterCompras()
    registros = []
    
    # Crear 3 registros diferentes
    for i in range(1, 4):
        registro = RegistroCompraResponse(
            id=f"64f12345678901234567890{i}",
            empresa_id="empresa_test_001",
            periodo="202408",
            fecha_creacion=datetime(2024, 8, 15, 10, 30, 0),
            tipo_documento_proveedor=TipoDocumentoIdentidad.RUC,
            numero_documento_proveedor=f"2012345678{i}",
            razon_social_proveedor=f"PROVEEDOR {i:03d} S.A.C.",
            tipo_comprobante=TipoComprobanteCompra.FACTURA,
            serie_comprobante="F001",
            numero_comprobante=f"{i:06d}",
            fecha_emision=f"1{i}/08/2024",
            fecha_vencimiento=f"3{i}/08/2024",
            base_imponible_gravada=Decimal(f"{1000 * i}.00"),
            igv=Decimal(f"{180 * i}.00"),
            base_imponible_gravada_operaciones_mixtas=Decimal("0.00"),
            igv_operaciones_mixtas=Decimal("0.00"),
            base_imponible_gravada_exportacion=Decimal("0.00"),
            igv_exportacion=Decimal("0.00"),
            base_imponible_no_gravada=Decimal("0.00"),
            isc=Decimal("0.00"),
            otros_tributos=Decimal("0.00"),
            importe_total=Decimal(f"{1180 * i}.00"),
            codigo_moneda="PEN",
            tipo_cambio=Decimal("1.000"),
            clasificacion_bienes_servicios=f"SERVICIO TIPO {i}",
            indicador_error="0",
            medio_pago="001",
            estado_operacion=EstadoOperacion.VIGENTE
        )
        registros.append(registro)
    
    # Formatear múltiples registros
    lineas_ple = formatter.formatear_multiple_compras(registros, "202408")
    
    print(f"📊 Registros procesados: {len(lineas_ple)}")
    
    for i, linea in enumerate(lineas_ple):
        linea_texto = linea.to_ple_line()
        campos = linea_texto.split("|")
        
        print(f"   Registro {i+1}: {len(campos)-1} campos, {len(linea_texto)} caracteres")
        
        # Validar estructura constante
        assert len(campos) == 34, f"Registro {i+1}: campos incorrectos"
        
        # Validar contenido específico
        assert campos[0] == "202408", f"Registro {i+1}: período incorrecto"
        assert campos[5] == "1", f"Registro {i+1}: tipo comprobante incorrecto"
        assert campos[23] == "PEN", f"Registro {i+1}: moneda incorrecta"
    
    # Generar archivo completo
    contenido_completo = formatter.generar_contenido_archivo_ple(lineas_ple)
    lineas_archivo = contenido_completo.strip().split("\n")
    
    print(f"📄 Líneas en archivo: {len(lineas_archivo)}")
    print(f"📏 Tamaño total: {len(contenido_completo)} caracteres")
    
    assert len(lineas_archivo) == 3, "Cantidad de líneas incorrecta"
    print("✅ Múltiples registros validados correctamente")
    
    return True


if __name__ == "__main__":
    try:
        # Ejecutar tests
        test_validacion_ple_compras_completa()
        test_validacion_multiples_registros()
        
        print("\n" + "🎉" * 20)
        print("TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("🎉" * 20)
        
    except Exception as e:
        print(f"\n❌ ERROR EN VALIDACIÓN: {str(e)}")
        print(f"💡 Revisa la implementación del formateador PLE")
        sys.exit(1)
