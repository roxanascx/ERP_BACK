#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de propuestas RVIE en base de datos
Verificar qué propuestas están guardadas y qué muestra la gestión de ventas
"""

import asyncio
import json
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING

async def diagnosticar_propuestas():
    """Diagnosticar propuestas RVIE en la base de datos"""
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.erp_db
    
    print("=" * 70)
    print("🔍 DIAGNÓSTICO DE PROPUESTAS RVIE")
    print("=" * 70)
    
    try:
        # 1. Verificar colecciones existentes
        print("\n📊 1. COLECCIONES EN BASE DE DATOS:")
        collections = await db.list_collection_names()
        sire_collections = [c for c in collections if 'sire' in c.lower()]
        
        for collection in sire_collections:
            count = await db[collection].count_documents({})
            print(f"   • {collection}: {count} documentos")
        
        # 2. Verificar tickets SIRE
        print(f"\n🎫 2. TICKETS SIRE:")
        tickets = await db.sire_tickets.find().sort("fecha_creacion", DESCENDING).limit(10).to_list(length=10)
        
        if not tickets:
            print("   ❌ No hay tickets en la base de datos")
        else:
            print(f"   📊 Encontrados {len(tickets)} tickets (últimos 10):")
            
            for ticket in tickets:
                ruc = ticket.get("ruc", "N/A")
                operacion = ticket.get("operacion", "N/A")
                estado = ticket.get("estado", "N/A")
                fecha = ticket.get("fecha_creacion", "N/A")
                
                # Buscar período en resultado si existe
                periodo = "N/A"
                resultado = ticket.get("resultado", {})
                if isinstance(resultado, dict):
                    periodo = resultado.get("periodo", "N/A")
                
                print(f"     • RUC: {ruc} | Op: {operacion} | Estado: {estado} | Período: {periodo}")
                print(f"       Fecha: {fecha}")
                
                # Si es propuesta, mostrar más detalles
                if operacion == "descargar-propuesta" and estado == "TERMINADO":
                    print(f"       📋 Resultado keys: {list(resultado.keys()) if resultado else []}")
                    if resultado:
                        comprobantes = resultado.get("comprobantes", [])
                        total_comp = resultado.get("cantidad_comprobantes", 0)
                        total_imp = resultado.get("total_importe", 0)
                        print(f"       💰 Comprobantes: {total_comp} | Total: S/ {total_imp}")
                        print(f"       🔢 Tipo comprobantes: {type(comprobantes)} | Longitud: {len(comprobantes) if isinstance(comprobantes, list) else 'N/A'}")
                print()
        
        # 3. Buscar propuestas específicas para RUC actual
        print(f"\n🔍 3. PROPUESTAS PARA RUC 20612969125:")
        ruc_test = "20612969125"
        tickets_ruc = await db.sire_tickets.find({
            "ruc": ruc_test,
            "operacion": "descargar-propuesta"
        }).sort("fecha_creacion", DESCENDING).to_list(length=5)
        
        if not tickets_ruc:
            print(f"   ❌ No hay propuestas para RUC {ruc_test}")
        else:
            print(f"   📊 Encontradas {len(tickets_ruc)} propuestas:")
            for ticket in tickets_ruc:
                estado = ticket.get("estado", "N/A")
                resultado = ticket.get("resultado", {})
                periodo = resultado.get("periodo", "N/A") if isinstance(resultado, dict) else "N/A"
                fecha = ticket.get("fecha_creacion", "N/A")
                
                print(f"     • Período: {periodo} | Estado: {estado} | Fecha: {fecha}")
                
                if estado == "TERMINADO" and resultado:
                    comprobantes = resultado.get("comprobantes", [])
                    total_comp = resultado.get("cantidad_comprobantes", 0)
                    total_imp = resultado.get("total_importe", 0)
                    print(f"       📊 Comprobantes: {total_comp} | Total: S/ {total_imp}")
                    print(f"       🔧 Estructura: {type(comprobantes)} {len(comprobantes) if isinstance(comprobantes, list) else ''}")
                    
                    # Mostrar algunos comprobantes de ejemplo
                    if isinstance(comprobantes, list) and len(comprobantes) > 0:
                        print(f"       📋 Ejemplo comprobante: {list(comprobantes[0].keys()) if len(comprobantes) > 0 and isinstance(comprobantes[0], dict) else comprobantes[0] if len(comprobantes) > 0 else 'N/A'}")
                print()
        
        # 4. Buscar propuestas para el período actual (agosto 2025)
        print(f"\n📅 4. PROPUESTAS PARA PERÍODO 202508:")
        periodo_actual = "202508"
        tickets_periodo = await db.sire_tickets.find({
            "operacion": "descargar-propuesta",
            "estado": "TERMINADO",
            "resultado.periodo": periodo_actual
        }).to_list(length=10)
        
        if not tickets_periodo:
            print(f"   ❌ No hay propuestas para período {periodo_actual}")
            
            # Buscar cualquier propuesta terminada
            print(f"\n   🔍 Buscando CUALQUIER propuesta terminada...")
            any_propuesta = await db.sire_tickets.find({
                "operacion": "descargar-propuesta", 
                "estado": "TERMINADO"
            }).limit(3).to_list(length=3)
            
            if any_propuesta:
                print(f"   📊 Encontradas {len(any_propuesta)} propuestas terminadas:")
                for ticket in any_propuesta:
                    resultado = ticket.get("resultado", {})
                    periodo = resultado.get("periodo", "N/A") if isinstance(resultado, dict) else "N/A"
                    ruc = ticket.get("ruc", "N/A")
                    fecha = ticket.get("fecha_creacion", "N/A")
                    print(f"     • RUC: {ruc} | Período: {periodo} | Fecha: {fecha}")
            else:
                print("   ❌ No hay NINGUNA propuesta terminada en la base de datos")
        else:
            print(f"   ✅ Encontradas {len(tickets_periodo)} propuestas para período {periodo_actual}")
            for ticket in tickets_periodo:
                ruc = ticket.get("ruc", "N/A")
                resultado = ticket.get("resultado", {})
                comprobantes = resultado.get("comprobantes", []) if isinstance(resultado, dict) else []
                total_comp = resultado.get("cantidad_comprobantes", 0) if isinstance(resultado, dict) else 0
                print(f"     • RUC: {ruc} | Comprobantes: {total_comp}")
        
        # 5. Verificar autenticación SIRE
        print(f"\n🔐 5. ESTADO AUTENTICACIÓN SIRE:")
        auth_docs = await db.sire_auth.find().limit(5).to_list(length=5)
        
        if not auth_docs:
            print("   ❌ No hay tokens de autenticación guardados")
        else:
            print(f"   📊 Encontrados {len(auth_docs)} registros de autenticación:")
            for auth in auth_docs:
                ruc = auth.get("ruc", "N/A")
                estado = "VÁLIDO" if auth.get("token_valido", False) else "INVÁLIDO"
                expira = auth.get("expira_en", "N/A")
                fecha = auth.get("fecha_creacion", "N/A")
                print(f"     • RUC: {ruc} | Estado: {estado} | Expira: {expira} | Fecha: {fecha}")
        
        print(f"\n✅ Diagnóstico completado - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error durante diagnóstico: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(diagnosticar_propuestas())
