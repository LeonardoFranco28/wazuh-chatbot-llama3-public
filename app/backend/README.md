# API Backend - Docker Setup

Esta es la API de FastAPI para el análisis de logs de Wazuh con IA.

## Características del Dockerfile

- **Seguridad**: Ejecuta como usuario no-root
- **Optimización**: Usa Python 3.10 slim para imagen más pequeña
- **Health Check**: Verificación automática de salud del servicio
- **Caching**: Optimizado para mejor rendimiento en builds

## Construir y Ejecutar

### Opción 1: Usando Docker Compose (Recomendado)

## Importante se requiere la generación de la ssh key y agregarla al backend.

```bash
# Construir y ejecutar
docker-compose up --build

# Ejecutar en background
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

### Opción 2: Usando Docker directamente

```bash
# Construir la imagen
docker build -t ia-networking-api .

# Ejecutar el contenedor
docker run -p 8000:8000 --name ia-api ia-networking-api

# Ejecutar en background
docker run -d -p 8000:8000 --name ia-api ia-networking-api

# Ver logs
docker logs -f ia-api

# Detener
docker stop ia-api
docker rm ia-api
```

## Endpoints Disponibles

- `GET /health` - Health check
- `WS /ws/chat` - WebSocket para chat con IA

## Variables de Entorno

Puedes configurar las siguientes variables de entorno:

- `PYTHONUNBUFFERED=1` - Para logs inmediatos
- `PYTHONPATH=/app` - Path de la aplicación

## Volúmenes

El contenedor está configurado para montar logs locales en `/var/ossec/logs` si los tienes disponibles.

## Troubleshooting

1. **Puerto ocupado**: Cambia el puerto en docker-compose.yml
2. **Permisos**: El contenedor ejecuta como usuario no-root por seguridad
3. **Logs**: Revisa los logs con `docker-compose logs` o `docker logs`

## Desarrollo

Para desarrollo local sin Docker:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
``` 