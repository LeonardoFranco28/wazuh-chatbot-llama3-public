#!/bin/bash

# Script de inicialización para actualizar la máquina sin interacción
# Este script se ejecuta automáticamente al crear el droplet

set -e  # Salir inmediatamente si ocurre un error

# Configurar variables de entorno para modo no interactivo
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

# Función para esperar a que apt esté disponible
wait_for_apt() {
    while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
          sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || \
          sudo fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do
        echo "Esperando a que apt esté disponible..."
        sleep 5
    done
}

echo "=== Iniciando actualización del sistema ==="

# Actualizar la lista de paquetes
echo "Actualizando lista de paquetes..."
wait_for_apt
apt-get update -y -qq

# Actualizar todos los paquetes instalados
echo "Actualizando paquetes instalados..."
wait_for_apt
apt-get upgrade -y -qq

# Actualizar distribución (si es necesario)
echo "Actualizando distribución..."
wait_for_apt
apt-get dist-upgrade -y -qq

# Limpiar paquetes obsoletos
echo "Limpiando paquetes obsoletos..."
wait_for_apt
apt-get autoremove -y -qq
apt-get autoclean -y -qq

# Instalar herramientas básicas útiles
echo "Instalando herramientas básicas..."
wait_for_apt
apt-get install -y -qq \
    curl \
    wget \
    htop \
    vim \
    unzip \
    git \
    ufw \
    fail2ban


# Reiniciar servicios críticos si es necesario
systemctl daemon-reload

echo "Inicialización completada. El sistema está listo."
