#!/usr/bin/env bash

set -euo pipefail

# Instala Ollama y descarga un modelo (por defecto: llama3)
# Uso:
#   ./install_ollama_llama3.sh               # instala y descarga "llama3"
#   ./install_ollama_llama3.sh llama3:8b     # instala y descarga un tag específico

MODEL_NAME=${1:-llama3}

log_info() { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
log_warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
log_err()  { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
  local uname_s
  uname_s=$(uname -s 2>/dev/null || echo "")
  case "$uname_s" in
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "WSL"
      else
        echo "Linux"
      fi
      ;;
    Darwin)
      echo "macOS"
      ;;
    MINGW*|MSYS*|CYGWIN*)
      echo "Windows"
      ;;
    *)
      # Fallback para shells raros en Windows
      if command -v powershell.exe >/dev/null 2>&1; then
        echo "Windows"
      else
        echo "Unknown"
      fi
      ;;
  esac
}

find_ollama_cmd() {
  # Devuelve la ruta/comando de ollama si existe, o vacío si no
  if command_exists ollama; then
    echo "ollama"
    return 0
  fi
  # Rutas comunes en Windows (Git Bash/WSL)
  local win_paths=(
    "/c/Program Files/Ollama/ollama.exe"
    "/c/Program Files/Ollama/bin/ollama.exe"
    "/mnt/c/Program Files/Ollama/ollama.exe"
    "/mnt/c/Program Files/Ollama/bin/ollama.exe"
  )
  for p in "${win_paths[@]}"; do
    if [ -x "$p" ]; then
      echo "$p"
      return 0
    fi
  done
  echo ""
}

install_ollama_linux() {
  log_info "Instalando Ollama en Linux..."
  if ! command_exists curl; then
    log_err "Se requiere 'curl' para la instalación en Linux. Instálalo y reintenta."
    exit 1
  fi
  curl -fsSL https://ollama.com/install.sh | sh
}

install_ollama_macos() {
  log_info "Instalando Ollama en macOS..."
  if command_exists brew; then
    brew install ollama || brew upgrade ollama || true
  else
    log_warn "Homebrew no está instalado. Intentando instalador oficial..."
    log_warn "Descarga manual: https://ollama.com/download"
    exit 1
  fi
}

install_ollama_windows() {
  log_info "Instalando Ollama en Windows (winget)..."
  local WINGET_CMD="winget.exe"
  if ! command_exists "$WINGET_CMD" && ! command_exists winget; then
    log_err "No se encontró winget. Instala Ollama manualmente desde: https://ollama.com/download"
    exit 1
  fi
  # Ejecuta vía PowerShell para mejor compatibilidad
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\
    try { \
      winget install -e --id Ollama.Ollama --source winget --accept-package-agreements --accept-source-agreements --silent; \
      exit 0 \
    } catch { \
      Write-Host 'Fallo al instalar con winget'; \
      exit 1 \
    }" || {
      log_err "Fallo al instalar Ollama con winget. Puede requerir permisos de administrador."
      exit 1
    }
  # Intenta arrancar el servicio
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\
    try { \
      if (Get-Service -Name 'Ollama' -ErrorAction SilentlyContinue) { \
        Set-Service -Name 'Ollama' -StartupType Automatic; \
        Start-Service -Name 'Ollama' -ErrorAction SilentlyContinue; \
      } \
    } catch { }" >/dev/null 2>&1 || true
}

ensure_ollama_running() {
  local cmd="$1"
  # En muchas plataformas, 'ollama pull' lanza el servidor automáticamente.
  # Aquí solo comprobamos que el binario existe.
  if [ -z "$cmd" ]; then
    log_err "No se encontró el binario de ollama tras la instalación."
    exit 1
  fi
}

pull_model() {
  local cmd="$1"
  log_info "Descargando modelo: ${MODEL_NAME} (esto puede tardar) ..."
  "${cmd}" pull "${MODEL_NAME}"
  log_info "Modelo '${MODEL_NAME}' descargado correctamente."
}

main() {
  local os
  os=$(detect_os)
  log_info "Sistema detectado: ${os}"

  local ollama_cmd
  ollama_cmd=$(find_ollama_cmd || true)

  if [ -n "$ollama_cmd" ]; then
    log_info "Ollama ya está instalado en: ${ollama_cmd}"
  else
    case "$os" in
      Linux|WSL)
        install_ollama_linux
        ;;
      macOS)
        install_ollama_macos
        ;;
      Windows)
        install_ollama_windows
        ;;
      *)
        log_err "Sistema operativo no soportado por este script."
        exit 1
        ;;
    esac
    # Reintenta localizar el binario tras instalar
    ollama_cmd=$(find_ollama_cmd || true)
  fi

  ensure_ollama_running "$ollama_cmd"
  pull_model "$ollama_cmd"

  log_info "Listo. Puedes probar con: \"${ollama_cmd}\" run ${MODEL_NAME}"
}

main "$@"


