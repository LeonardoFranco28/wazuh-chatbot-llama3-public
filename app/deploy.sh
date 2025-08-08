#!/bin/bash

# Configuración del servidor
SERVER_IP="YOUR_WAZUH_SERVER_IP"
SERVER_USER="YOUR_SERVER_USER"
SERVER_PATH="/home/YOUR_SERVER_USER/backend"
LOCAL_PATH="backend/"
SSH_PRIVATE_KEY="~/.ssh/YOUR_SERVER_USER_KEY"

# Función para mostrar ayuda
show_help() {
    echo -e "📋 Uso del script de despliegue:"
    echo -e "  $0 [opción]"
    echo -e ""
    echo -e "Opciones disponibles:"
    echo -e "  docker      - Despliegue con Docker (recomendado)"
    echo -e "  ssh         - Enviar carpeta .ssh al servidor"
    echo -e "  help         - Mostrar esta ayuda"
    echo -e "Ejemplos:"
    echo -e "  $0 docker"
    echo -e "  $0 ssh"
}



# Función para limpiar archivos temporales
cleanup_temp() {
    if [ ! -z "$1" ] && [ -d "$1" ]; then
        rm -rf "$1"
        echo -e "🧹 Archivos temporales limpiados${NC}"
    fi
}



# Función para despliegue con Docker
deploy_docker() {
    echo -e "🐳 Iniciando despliegue con Docker..."

    # Verificar que existe la carpeta local
    if [ ! -d "$LOCAL_PATH" ]; then
        echo -e "❌ Error: No se encuentra la carpeta $LOCAL_PATH"
        exit 1
    fi

   

    # Verificar que Docker está instalado en el servidor
    echo -e "🔍 Verificando Docker en el servidor..."
    if ! ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "command -v docker &> /dev/null"; then
        echo -e "💡 Instalando Docker en el servidor..."
        ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo snap install docker"
    fi

  
    # Crear directorio en el servidor
    echo -e "📁 Creando directorio en el servidor..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "mkdir -p $SERVER_PATH"

    # Subir archivos usando scp
    echo -e "📤 Subiendo archivos al servidor.."
    scp -i $SSH_PRIVATE_KEY -r $LOCAL_PATH/* $SERVER_USER@$SERVER_IP:$SERVER_PATH/

    if [ $? -eq 0 ]; then
        echo -e "✅ Archivos subidos exitosamente"
    else
        echo -e "❌ Error al subir archivos"
        exit 1
    fi

    # Construir imagen Docker en el servidor
    echo -e "🔨 Construyendo imagen Docker..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "cd $SERVER_PATH && sudo docker build  -t ia-networking-api ."

    # Detener contenedor existente si existe
    echo -e "🛑 Deteniendo contenedor existente..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo docker stop ia-api 2>/dev/null || true"
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo docker rm ia-api 2>/dev/null || true"

    # Ejecutar nuevo contenedor
    echo -e "🚀 Iniciando contenedor Docker..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo docker run -d --name ia-api --network=bridge -p 8000:8000 --restart unless-stopped ia-networking-api"

    # Configurar nginx con timeouts extendidos
    echo -e "🔧 Configurando nginx..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo apt-get update && sudo apt-get install -y nginx"
    
    # Copiar configuración de nginx
    scp -i $SSH_PRIVATE_KEY backend/nginx.conf $SERVER_USER@$SERVER_IP:/tmp/nginx.conf
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo cp /tmp/nginx.conf /etc/nginx/sites-available/ia-networking && sudo ln -sf /etc/nginx/sites-available/ia-networking /etc/nginx/sites-enabled/ && sudo rm /etc/nginx/sites-enabled/default && sudo systemctl restart nginx"

    # Verificar que el contenedor está ejecutándose
    echo -e "🔍 Verificando estado del contenedor..."
    if ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo docker ps | grep ia-api"; then
        echo -e "✅ Contenedor ejecutándose correctamente"
    else
        echo -e "❌ Error: El contenedor no se inició correctamente"
        echo -e "📋 Logs del contenedor:"
        ssh  -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "sudo docker logs ia-api"
        exit 1
    fi

    echo -e "🎉 Despliegue con Docker completado!"
    echo -e "📋 Información del despliegue:"
    echo -e "  🌐 URL: http://$SERVER_IP:8000"
    echo -e "  📊 Health Check: http://$SERVER_IP:8000/health"
    echo -e "  🐳 Contenedor: ia-api"
    echo -e ""
    echo -e "Comandos útiles:"
    echo -e "  Ver logs: ssh  -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP 'sudo docker logs -f ia-api'"
    echo -e "  Reiniciar: ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP 'sudo docker restart ia-api'"
    echo -e "  Detener: ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP 'sudo docker stop ia-api'"
}

# Función para enviar carpeta .ssh
deploy_ssh() {
    echo -e "🔑 Enviando carpeta .ssh al servidor..."
    
    # Verificar que existe la carpeta .ssh local
    if [ ! -d "backend/.ssh" ]; then
        echo -e "❌ Error: No se encuentra la carpeta ~/.ssh"
        exit 1
    fi
    
    # Crear directorio .ssh en el servidor
    echo -e "📁 Creando directorio .ssh en el servidor..."
    ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "mkdir -p ~/.ssh"
    
    # Subir archivos .ssh usando scp
    echo -e "📤 Subiendo archivos .ssh al servidor..."
    scp -i $SSH_PRIVATE_KEY -r backend/.ssh/* $SERVER_USER@$SERVER_IP:$SERVER_PATH/.ssh
    
    if [ $? -eq 0 ]; then
        echo -e "✅ Carpeta .ssh enviada exitosamente"
        echo -e "🔧 Configurando permisos..."
        ssh -i $SSH_PRIVATE_KEY $SERVER_USER@$SERVER_IP "chmod 700 backend/.ssh/ && chmod 600 backend/.ssh/*"
        echo -e "✅ Permisos configurados correctamente"
    else
        echo -e "❌ Error al enviar carpeta .ssh"
        exit 1
    fi
    
    echo -e "🎉 Configuración SSH completada!"
}

# Verificar argumentos
if [ $# -eq 0 ]; then
    echo -e "⚠️  No se especificó método de despliegue"
    show_help
    exit 1
fi

case $1 in
    "traditional")
        deploy_traditional
        ;;
    "docker")
        deploy_docker
        ;;
    "ssh")
        deploy_ssh
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "❌ Opción inválida: $1"
        show_help
        exit 1
        ;;
esac 