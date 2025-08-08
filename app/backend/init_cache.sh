#!/bin/bash

# Script para inicializar el cache de Hugging Face con permisos correctos

echo "🔧 Inicializando cache de Hugging Face..."

# Crear directorios necesarios
mkdir -p /home/appuser/.cache/huggingface/hub
mkdir -p /home/appuser/.cache/huggingface/transformers

# Establecer permisos correctos (solo si tenemos privilegios)
if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /home/appuser/.cache
    chmod -R 755 /home/appuser/.cache
else
    echo "⚠️  Running as non-root user, skipping permission changes"
fi

# Limpiar archivos de lock si existen
find /home/appuser/.cache -name "*.lock" -delete 2>/dev/null || true

echo "✅ Cache inicializado correctamente" 