#!/usr/bin/env python3
"""Importador sencillo para el Plan Contable.

Lee un archivo de texto con líneas que comienzan con código seguido de descripción
(ej: "101    Caja") y construye documentos para la colección `plan_contable`.

Uso:
  python import_plan_contable.py path/to/plan_contable_unificado.txt --dry-run
  python import_plan_contable.py path/to/plan_contable_unificado.txt --commit

El modo --dry-run solo muestra el conteo y ejemplos.
"""
from __future__ import annotations
import re
import argparse
from datetime import datetime
from typing import Dict, List
import sys

import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from app.database import get_database


CODE_RE = re.compile(r"^\s*([0-9]{1,10})\s+(.+?)\s*$")


def parse_file(path: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.rstrip("\n\r")
            m = CODE_RE.match(ln)
            if not m:
                continue
            code = m.group(1)
            desc = m.group(2).strip()
            if code and desc:
                # normalize multiple spaces inside description
                desc = re.sub(r"\s+", " ", desc)
                parsed[code] = desc
    return parsed


def infer_parent(code: str, codes_set: set) -> str | None:
    # Find the longest existing prefix shorter than code
    for L in range(len(code) - 1, 0, -1):
        prefix = code[:L]
        if prefix in codes_set:
            return prefix
    return None


def determine_naturaleza(clase: int) -> str:
    clases_deudoras = [1, 2, 3, 6, 8, 9]
    clases_acreedoras = [4, 5, 7]
    if clase in clases_deudoras:
        return "DEUDORA"
    if clase in clases_acreedoras:
        return "ACREEDORA"
    return "DEUDORA"


def build_documents(parsed: Dict[str, str]) -> List[Dict]:
    docs = []
    codes_set = set(parsed.keys())
    for code, desc in parsed.items():
        nivel = len(code)
        try:
            clase = int(code[0]) if len(code) >= 1 else 0
        except Exception:
            clase = 0
        padre = infer_parent(code, codes_set)
        doc = {
            "codigo": code,
            "descripcion": desc,
            "nivel": nivel,
            "clase_contable": clase,
            "grupo": None,
            "subgrupo": None,
            "cuenta_padre": padre,
            "es_hoja": True,  # ajustaremos después si se detectan hijos
            "acepta_movimiento": True,
            "naturaleza": determine_naturaleza(clase),
            "moneda": "MN",
            "activa": True,
            "fecha_creacion": datetime.now(),
        }
        docs.append(doc)

    # marcar es_hoja = False para aquellos que tienen hijos
    codigo_map = {d["codigo"]: d for d in docs}
    for d in docs:
        padre = d.get("cuenta_padre")
        if padre and padre in codigo_map:
            codigo_map[padre]["es_hoja"] = False

    return docs


def commit_documents(docs: List[Dict], collection_name: str = "plan_contable") -> Dict[str, int]:
    db = get_database()
    coll = db[collection_name]
    inserted = 0
    updated = 0
    for d in docs:
        # Upsert by codigo: if exists, skip or update minimal fields
        res = coll.update_one({"codigo": d["codigo"]}, {"$setOnInsert": d}, upsert=True)
        # Note: motor returns a result object, but in synchronous get_database path it's a sync pymongo
        # To support both, use hasattr check
        try:
            if getattr(res, "upserted_id", None):
                inserted += 1
            else:
                # existing doc - we didn't modify anything
                pass
        except Exception:
            # fallback: assume insertion when acknowledged
            inserted += 1
    return {"inserted": inserted, "updated": updated}


def main():
    parser = argparse.ArgumentParser(description="Importar plan contable desde archivo de texto")
    parser.add_argument("file", help="Ruta al archivo de plan contable (texto)")
    parser.add_argument("--commit", action="store_true", help="Insertar los documentos en la DB")
    parser.add_argument("--collection", default="plan_contable", help="Nombre de la colección destino")
    args = parser.parse_args()

    parsed = parse_file(args.file)
    print(f"Líneas parseadas: {len(parsed)}")
    docs = build_documents(parsed)
    print(f"Documentos construidos: {len(docs)}")
    if len(docs) > 0:
        print("Ejemplos:")
        for ex in docs[:5]:
            print(f"  {ex['codigo']} - {ex['descripcion']} (nivel {ex['nivel']}) padre={ex['cuenta_padre']}")

    if args.commit:
        print("Insertando en la colección", args.collection)
        res = commit_documents(docs, collection_name=args.collection)
        print("Resultado:", res)
    else:
        print("Dry-run (no se escribirán datos). Use --commit para insertar en la DB")


if __name__ == '__main__':
    main()
