#!/usr/bin/env bash
# Script de build para Render
set -o errexit   # aborta el deploy si algo falla

echo "🚀 Iniciando build del backend ERP..."

python -m pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "✅ Backend build completado!"
