#!/bin/bash

# Script para verificar el progreso de la instalación de Wazuh

echo "Checking Wazuh installation status..."

# Verificar si el proceso de instalación está ejecutándose
if pgrep -f "wazuh.install.sh" > /dev/null; then
    echo "Wazuh installation is still running..."
    echo "Process ID: $(pgrep -f 'wazuh.install.sh')"
else
    echo "Wazuh installation process is not running."
fi

# Verificar el log de instalación
if [ -f "/root/wazuh_install.log" ]; then
    echo "Installation log exists. Last 20 lines:"
    tail -20 /root/wazuh_install.log
else
    echo "Installation log not found."
fi

# Verificar si Wazuh está instalado
if systemctl is-active --quiet wazuh-manager; then
    echo "Wazuh manager service is running."
elif systemctl is-enabled --quiet wazuh-manager; then
    echo "Wazuh manager service is enabled but not running."
else
    echo "Wazuh manager service not found."
fi

# Verificar puertos de Wazuh
echo "Checking Wazuh ports..."
netstat -tlnp | grep -E ':(1514|1515|514|55000)' || echo "No Wazuh ports found listening." 