#!/usr/bin/env python3
"""
Script para limpiar el cache de Hugging Face y resolver problemas de permisos
"""

import os
import shutil
import sys

def clean_cache():
    """Limpia el cache de Hugging Face"""
    cache_dirs = [
        "/home/appuser/.cache/huggingface",
        "/root/.cache/huggingface",
        os.path.expanduser("~/.cache/huggingface")
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                print(f"🧹 Limpiando cache en: {cache_dir}")
                # Force remove with sudo if needed
                import subprocess
                try:
                    subprocess.run(["rm", "-rf", cache_dir], check=True)
                    print(f"✅ Cache limpiado en: {cache_dir}")
                except subprocess.CalledProcessError:
                    # Try with sudo
                    subprocess.run(["sudo", "rm", "-rf", cache_dir], check=True)
                    print(f"✅ Cache limpiado con sudo en: {cache_dir}")
            except Exception as e:
                print(f"❌ Error limpiando {cache_dir}: {e}")

def create_cache_dirs():
    """Crea los directorios de cache necesarios"""
    cache_dirs = [
        "/home/appuser/.cache/huggingface/hub",
        "/home/appuser/.cache/huggingface/transformers"
    ]
    
    for cache_dir in cache_dirs:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            print(f"✅ Directorio creado: {cache_dir}")
        except Exception as e:
            print(f"❌ Error creando {cache_dir}: {e}")

if __name__ == "__main__":
    print("🔧 Limpiando cache de Hugging Face...")
    clean_cache()
    print("📁 Creando directorios de cache...")
    create_cache_dirs()
    print("✅ Proceso completado") 