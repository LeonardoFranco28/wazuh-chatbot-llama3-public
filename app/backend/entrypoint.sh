#!/bin/bash

# Script de entrada para el contenedor Docker
echo "🚀 Iniciando contenedor..."

# Ejecutar script de inicialización del cache
echo "🔧 Inicializando cache..."
./init_cache.sh

# Iniciar la aplicación
echo "📦 Iniciando aplicación..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 300 