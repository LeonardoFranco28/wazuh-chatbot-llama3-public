#!/bin/bash

set -e  # Salir inmediatamente si ocurre un error

export DEBIAN_FRONTEND=noninteractive

# Función para esperar a que apt esté disponible
wait_for_apt() {
    while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
          sudo fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || \
          sudo fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do
        echo "Waiting for APT locks to be released..."
        sleep 10
    done
}

# Opciones para evitar prompts de configuración de servicios o cambios
APT_OPTIONS="-y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"

# Esperar a que apt esté disponible antes de comenzar
wait_for_apt

# Actualiza el sistema sin interacción
echo "Updating package lists..."
sudo apt-get update ${APT_OPTIONS}

echo "Upgrading packages..."
sudo apt-get upgrade ${APT_OPTIONS}

echo "Performing dist-upgrade..."
sudo apt-get dist-upgrade ${APT_OPTIONS}

echo "Cleaning up packages..."
sudo apt-get autoremove ${APT_OPTIONS}
sudo apt-get autoclean ${APT_OPTIONS}

# Esperar a que apt esté disponible antes de instalar dependencias
wait_for_apt

echo "Installing dependencies..."
sudo apt-get install ${APT_OPTIONS} curl gnupg apt-transport-https lsb-release

# Descarga e instala Wazuh automáticamente sin interacción
echo "Downloading Wazuh installation script..."
curl -sO https://packages.wazuh.com/4.12/wazuh-install.sh

echo "Installing Wazuh..."
sudo bash ./wazuh-install.sh -a -i

echo "Wazuh installation completed successfully!"
