import json
import os
import gzip 
from datetime import datetime, timedelta
import asyncio
import traceback
import sys
from paramiko.auth_strategy import PrivateKey
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain.schema.messages import SystemMessage, HumanMessage
import uvicorn
import argparse
import sys
from fastapi import Depends, status, HTTPException
from fastapi.security import HTTPBearer
import secrets


# Classes 
class Prompt(BaseModel):
    question: str


# ===== Globals for caching =====
qa_chain = None
context = None
wazuh_context = None
general_context = None
days_range = 1


app = FastAPI()
security = HTTPBearer()


# ===== CONFIGURACIÓN OLLAMA PARA DOCKER =====
# Si Ollama está en el host, usa host.docker.internal
# Si está en otro contenedor, usa el nombre del servicio
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "YOUR_OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
api_key = os.getenv("API_KEY", "Toor0128#$95")
remote_host = os.getenv("REMOTE_HOST", "143.244.165.32")
ssh_username = os.getenv("SSH_USERNAME", "root")
ssh_private_key = os.getenv("SSH_PRIVATE_KEY", ".ssh/key")


# ===== Functions =====

def isAuth(api_key: str =Depends(security)):
    if api_key.credentials == api_key:
        return True
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")
    

def run_daemon():
    import daemon
    log_file_path = "/var/ossec/logs/threat_hunter.log"
    with daemon.DaemonContext(
        stdout=open(log_file_path, 'a+'),
        stderr=open(log_file_path, 'a+')
    ):
        uvicorn.run(app, host="0.0.0.0", port=8000)


def load_logs_from_remote(host, user, ssh_private_key, past_days):
    import paramiko
    logs = []
    today = datetime.now()

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"🔑 Loading private key from {ssh_private_key}")
        privateKey = paramiko.RSAKey.from_private_key_file(ssh_private_key)
        print(f"🔑 Private key loaded successfully")
        ssh.connect(host, username=user, pkey=privateKey, timeout=20)
        print(f"🔑 SSH connection established")
        sftp = ssh.open_sftp()

        for i in range(past_days):
            day = today - timedelta(days=i)
            year = day.year
            month_name = day.strftime("%b")
            day_num = day.strftime("%d")
            base_path = f"/var/ossec/logs/archives/{year}/{month_name}"
            json_path = f"{base_path}/ossec-archive-{day_num}.json"
            gz_path = f"{base_path}/ossec-archive-{day_num}.json.gz"

            remote_file = None
            try:
                if sftp.stat(json_path).st_size > 0:
                    remote_file = sftp.open(json_path, 'r')
                elif sftp.stat(gz_path).st_size > 0:
                    remote_file = gzip.GzipFile(fileobj=sftp.open(gz_path, 'rb'))
            except IOError:
                print(f"⚠️ Remote log not found or unreadable: {json_path} / {gz_path}")
                continue

            if remote_file:
                try:
                    for line in remote_file:
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='ignore')
                        if line.strip():
                            try:
                                log = json.loads(line.strip())
                                logs.append(log)
                            except json.JSONDecodeError:
                                print(f"⚠️ Skipping invalid JSON line from remote file.")
                except Exception as e:
                    print(f"⚠️ Error reading remote file: {e}")
        sftp.close()
        ssh.close()
    except Exception as e:
        print(f"❌ Remote connection failed: {e}")
    return logs

def load_logs_from_days(past_days=7):
    if remote_host:
        return load_logs_from_remote(remote_host, ssh_username, ssh_private_key, past_days)

    logs = []
    today = datetime.now()
    for i in range(past_days):
        day = today - timedelta(days=i)
        year = day.year
        month_name = day.strftime("%b")
        day_num = day.strftime("%d")

        json_path = f"/var/ossec/logs/archives/{year}/{month_name}/ossec-archive-{day_num}.json"
        gz_path = f"/var/ossec/logs/archives/{year}/{month_name}/ossec-archive-{day_num}.json.gz"

        file_path = None
        open_func = None

        if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
            file_path = json_path
            open_func = open
        elif os.path.exists(gz_path) and os.path.getsize(gz_path) > 0:
            file_path = gz_path
            open_func = gzip.open
        else:
            print(f"⚠️ Log file missing or empty: {json_path} / {gz_path}")
            continue

        try:
            with open_func(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        try:
                            log = json.loads(line.strip())
                            logs.append(log)
                        except json.JSONDecodeError:
                            print(f"⚠️ Skipping invalid JSON line in {file_path}")
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
    return logs


def create_simple_context(logs):
    """Crea un contexto simple sin embeddings"""
    context_parts = []
    for i, log in enumerate(logs[:100]):  # Limitar a 100 logs para no sobrecargar
        log_text = log.get('full_log', '')
        if log_text:
            context_parts.append(f"Log {i+1}: {log_text[:200]}...")  # Limitar longitud
    
    return "\n\n".join(context_parts)

def is_wazuh_related_question(question):
    """Detecta si la pregunta está relacionada con Wazuh/logs de seguridad"""
    wazuh_keywords = [
        'wazuh', 'logs', 'security', 'threat', 'alert', 'event', 'attack',
        'intrusion', 'firewall', 'antivirus', 'malware', 'vulnerability',
        'breach', 'incident', 'monitoring', 'detection', 'siem',
        'ossec', 'archives', 'security logs', 'threat hunting',
        'security events', 'alerts', 'incidents', 'attacks',
        'log analysis', 'security analysis', 'threat analysis'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in wazuh_keywords)


def initialize_assistant_context(logs_context=""):
    base_context = """You are a security analyst performing threat hunting.
Your task is to analyze logs from Wazuh. You have access to the logs provided in the context.
The objective is to identify potential security threats or any other needs from the user.
All queries should be interpreted as asking about security events, patterns or other request from the user using the provided logs. response in spanish"""
    
    if logs_context:
        return f"{base_context}\n\nAvailable logs:\n{logs_context}"
    return base_context

def get_general_context():
    """Contexto general para preguntas no relacionadas con Wazuh"""
    return """You are a helpful AI assistant. You can help with general questions, 
programming, analysis, and various topics. Be informative, accurate, and helpful. response in spanish"""

def setup_chain(past_days=7):
    global qa_chain, context, days_range, wazuh_context, general_context
    days_range = past_days
    print(f"🔄 Initializing QA chain with logs from past {past_days} days...")
    logs = load_logs_from_days(past_days)
    
    # CONFIGURACIÓN MEJORADA DE OLLAMA
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        timeout=60,  # Timeout más largo
        num_predict=512  # Limitar tokens para evitar timeouts
    )
    
    # Crear contexto general
    general_context = get_general_context()
    
    if not logs:
        print("❌ No logs found. Using general context only.")
        wazuh_context = initialize_assistant_context()
    else:
        print(f"✅ {len(logs)} logs loaded from the last {past_days} days.")
        print("📦 Creating simple context without embeddings...")
        
        # Crear contexto simple sin embeddings
        logs_context = create_simple_context(logs)
        wazuh_context = initialize_assistant_context(logs_context)
    
    # Crear una cadena simple sin vectorstore
    qa_chain = llm
    print("✅ QA chain initialized successfully (Ollama only).")
    return True


def get_stats(logs):
    total_logs = len(logs)
    dates = [datetime.strptime(log.get('timestamp', '')[:10], "%Y-%m-%d") for log in logs if 'timestamp' in log and log.get('timestamp')]
    date_range = ""
    if dates:
        earliest = min(dates).strftime("%Y-%m-%d")
        latest = max(dates).strftime("%Y-%m-%d")
        date_range = f" from {earliest} to {latest}"
    return f"Logs loaded: {total_logs}{date_range}"


# ===== API Endpoints =====

@app.get("/health")
async def get():
    return {"message": "Health Check", "ollama_url": OLLAMA_BASE_URL}


# ========= WebSocket Chat MEJORADO =========






@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    global qa_chain, context, wazuh_context, general_context, days_range
    
    # Variables para tracking del estado
    connection_start = datetime.now()
    messages_processed = 0
    last_activity = datetime.now()
    
    try:
        await websocket.accept()
        print(f"🔗 Nueva conexión WebSocket establecida: {connection_start}")
        
        chat_history = []
        
        # Función helper para enviar mensajes con manejo de errores
        async def send_safe_message(message_data: dict, close_on_fail: bool = False):
            try:
                await websocket.send_json(message_data)
                return True
            except Exception as e:
                print(f"❌ Error enviando mensaje WebSocket: {e}")
                if close_on_fail:
                    try:
                        await websocket.close(code=1011, reason=f"Send error: {str(e)[:100]}")
                    except:
                        print(f"❌ Error cerrando conexión WebSocket: {e}")
                        pass
                return False
        
        # Función para diagnosticar el estado del sistema
        async def system_diagnostic():
            diagnostic = {
                "qa_chain_status": "✅ Activo" if qa_chain else "❌ Inactivo",
                "wazuh_context_status": "✅ Cargado" if wazuh_context else "❌ No cargado",
                "general_context_status": "✅ Cargado" if general_context else "❌ No cargado",
                "ollama_url": OLLAMA_BASE_URL,
                "ollama_model": OLLAMA_MODEL,
                "days_range": days_range,
                "connection_duration": str(datetime.now() - connection_start),
                "messages_processed": messages_processed,
                "last_activity": str(datetime.now() - last_activity)
            }
            
            # Test de conectividad con Ollama
            try:
                import requests
                response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    diagnostic["ollama_connection"] = "✅ Conectado"
                    models = response.json().get("models", [])
                    available_models = [m.get("name", "unknown") for m in models]
                    diagnostic["available_models"] = available_models
                    diagnostic["target_model_available"] = OLLAMA_MODEL in str(available_models)
                else:
                    diagnostic["ollama_connection"] = f"⚠️ HTTP {response.status_code}"
            except Exception as e:
                diagnostic["ollama_connection"] = f"❌ Error: {str(e)}"
            
            return diagnostic
        
        # Verificar que el sistema esté listo
        if not qa_chain or not wazuh_context or not general_context:
            await send_safe_message({
                "role": "system", 
                "message": "⚠️ El Asistente no está listo. Iniciando diagnóstico del sistema...",
                "status": "initializing"
            })
            
            # Realizar diagnóstico
            diagnostic = await system_diagnostic()
            
            diagnostic_msg = "🔍 Diagnóstico del Sistema:\n"
            for key, value in diagnostic.items():
                diagnostic_msg += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            await send_safe_message({
                "role": "system", 
                "message": diagnostic_msg,
                "status": "diagnostic"
            })
            
            # Intentar inicializar
            await send_safe_message({
                "role": "system", 
                "message": "🔄 Intentando inicializar el sistema...",
                "status": "initializing"
            })
            
            try:
                success = setup_chain(past_days=days_range)
                if not success:
                    error_msg = (
                        "❌ Error al inicializar el sistema.\n\n"
                        "Posibles causas:\n"
                        "1. No se encontraron logs en el rango especificado\n"
                        "2. Error de conexión con Ollama\n"
                        "3. Problema con el modelo de embeddings\n"
                        "4. Falta de permisos en directorios\n\n"
                        "Usa /diagnostic para más detalles o /reload para reintentar."
                    )
                    await send_safe_message({
                        "role": "system", 
                        "message": error_msg,
                        "status": "error",
                        "diagnostic": diagnostic
                    })
                    # No cerrar la conexión, permitir comandos de diagnóstico
                else:
                    await send_safe_message({
                        "role": "system", 
                        "message": "✅ Sistema inicializado correctamente.",
                        "status": "ready"
                    })
            except Exception as init_error:
                error_details = {
                    "error_type": type(init_error).__name__,
                    "error_message": str(init_error),
                    "traceback": traceback.format_exc()
                }
                
                await send_safe_message({
                    "role": "system", 
                    "message": f"❌ Error crítico durante inicialización:\n{init_error}\n\nUsa /diagnostic para más detalles.",
                    "status": "critical_error",
                    "error_details": error_details
                })
        
        # Mensaje de bienvenida
        welcome_msg = f"👋 ¡Hola! Soy un asistente inteligente.\n"
        welcome_msg += f"🔍 **Modo Wazuh:** Menciona 'logs', 'security', 'wazuh', 'threat' para análisis de seguridad\n"
        welcome_msg += f"💬 **Modo General:** Para cualquier otra pregunta\n"
        welcome_msg += f"📊 Rango de logs: {days_range} días\n"
        welcome_msg += f"🔧 Estado: {'✅ Listo' if qa_chain else '⚠️ Modo diagnóstico'}\n"  
        welcome_msg += f"💡 Escribe /help para ver comandos disponibles"
        
        if qa_chain:
            chat_history = [SystemMessage(content=general_context)]
        
        await send_safe_message({
            "role": "bot", 
            "message": welcome_msg,
            "status": "ready" if qa_chain else "limited"
        })

        # Loop principal con manejo robusto de errores
        while True:
            try:
                # Timeout para recibir mensajes con heartbeat
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=300)  # 5 min timeout
                    last_activity = datetime.now()
                    messages_processed += 1
                except asyncio.TimeoutError:
                    await send_safe_message({
                        "role": "system", 
                        "message": "⏰ Timeout: No se recibió mensaje en 5 minutos. Usa /ping para mantener la conexión activa.",
                        "status": "timeout_warning"
                    })
                    continue  # No cerrar, solo advertir
                
                if not data.strip():
                    continue
                
                # Heartbeat mejorado
                if data.strip() == "/ping":
                    uptime = datetime.now() - connection_start
                    await send_safe_message({
                        "role": "system", 
                        "message": f"🏓 pong - Conexión activa (uptime: {uptime}, mensajes: {messages_processed})",
                        "status": "heartbeat"
                    })
                    continue
                
                # Comando de diagnóstico completo
                if data.lower() == "/diagnostic":
                    diagnostic = await system_diagnostic()
                    
                    diag_msg = "🔍 Diagnóstico Completo del Sistema:\n\n"
                    for key, value in diagnostic.items():
                        diag_msg += f"**{key.replace('_', ' ').title()}:** {value}\n"
                    
                    # Agregar información adicional
                    diag_msg += f"\n**Información de Conexión:**\n"
                    diag_msg += f"- Tiempo de conexión: {datetime.now() - connection_start}\n"
                    diag_msg += f"- Mensajes procesados: {messages_processed}\n"
                    diag_msg += f"- Última actividad: {datetime.now() - last_activity} ago\n"
                    
                    # Test de logs
                    try:
                        test_logs = load_logs_from_days(1)  # Solo 1 día para test rápido
                        diag_msg += f"- Test de logs (1 día): {'✅' if test_logs else '❌'} ({len(test_logs) if test_logs else 0} logs)\n"
                    except Exception as e:
                        diag_msg += f"- Test de logs: ❌ Error: {str(e)}\n"
                    
                    await send_safe_message({
                        "role": "system", 
                        "message": diag_msg,
                        "status": "diagnostic_complete",
                        "raw_diagnostic": diagnostic
                    })
                    continue
                
                # Commands handling existentes
                if data.lower() == "/help":
                    help_msg = (
                        "📋 **Menú de Ayuda:**\n\n"
                        "**Modos de Operación:**\n"
                        "🔍 **Modo Wazuh:** Se activa automáticamente cuando mencionas:\n"
                        "   - 'logs', 'security', 'wazuh', 'threat', 'alert', 'event'\n"
                        "   - 'attack', 'intrusion', 'firewall', 'malware', 'vulnerability'\n"
                        "   - 'breach', 'incident', 'monitoring', 'detection', 'siem'\n\n"
                        "💬 **Modo General:** Para cualquier otra pregunta\n\n"
                        "**Comandos del Sistema:**\n"
                        "/diagnostic - Diagnóstico completo del sistema\n"
                        "/status - Estado rápido del sistema\n"
                        "/reload - Recargar logs con rango actual\n"
                        "/ping - Test de conectividad\n\n"
                        "**Configuración:**\n"
                        "/set days <número> - Establecer días para cargar logs (1-365)\n\n"
                        "**Información:**\n"
                        "/stat - Estadísticas de los logs\n"
                        "/uptime - Información de la sesión\n\n"
                        "**Ejemplos de uso:**\n"
                        "🔍 Wazuh: \"¿Cuáles son los eventos más frecuentes?\"\n"
                        "🔍 Wazuh: \"Muéstrame alertas de seguridad del último día\"\n"
                        "💬 General: \"¿Cómo funciona Python?\"\n"
                        "💬 General: \"Explícame qué es Docker\""
                    )
                    await send_safe_message({"role": "bot", "message": help_msg})
                    continue

                if data.lower() == "/uptime":
                    uptime_info = (
                        f"⏱️ **Información de la Sesión:**\n\n"
                        f"- Conexión establecida: {connection_start.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"- Tiempo activa: {datetime.now() - connection_start}\n"
                        f"- Mensajes procesados: {messages_processed}\n"
                        f"- Última actividad: {last_activity.strftime('%H:%M:%S')}\n"
                        f"- Estado del sistema: {'✅ Operativo' if qa_chain else '⚠️ Modo limitado'}"
                    )
                    await send_safe_message({"role": "bot", "message": uptime_info})
                    continue

                if data.lower() == "/status":
                    try:
                        diagnostic = await system_diagnostic()
                        status_msg = f"🔧 **Estado Rápido del Sistema:**\n\n"
                        status_msg += f"- QA Chain: {diagnostic['qa_chain_status']}\n"
                        status_msg += f"- Contexto Wazuh: {diagnostic['wazuh_context_status']}\n"
                        status_msg += f"- Contexto General: {diagnostic['general_context_status']}\n"
                        status_msg += f"- Ollama: {diagnostic.get('ollama_connection', 'Verificando...')}\n"
                        status_msg += f"- Modelo objetivo: {OLLAMA_MODEL}\n"
                        status_msg += f"- Rango de días: {days_range}\n"
                        status_msg += f"- Mensajes procesados: {messages_processed}"
                        
                        await send_safe_message({
                            "role": "bot", 
                            "message": status_msg,
                            "diagnostic_summary": diagnostic
                        })
                    except Exception as e:
                        await send_safe_message({
                            "role": "bot", 
                            "message": f"❌ Error obteniendo estado: {str(e)}\nUsa /diagnostic para más detalles."
                        })
                    continue

                if data.lower() == "/reload":
                    await send_safe_message({
                        "role": "bot", 
                        "message": f"🔄 Recargando logs de los últimos {days_range} días...",
                        "status": "reloading"
                    })
                    
                    try:
                        success = setup_chain(past_days=days_range)
                        if success and qa_chain:
                            await send_safe_message({
                                "role": "bot", 
                                "message": f"✅ Recarga completada exitosamente.\nAhora usando logs de los últimos {days_range} días.",
                                "status": "reload_success"
                            })
                            chat_history = [SystemMessage(content=general_context)]
                        else:
                            diagnostic = await system_diagnostic()
                            error_msg = (
                                f"❌ Error en la recarga.\n\n"
                                f"Diagnóstico rápido:\n"
                                f"- Ollama: {diagnostic.get('ollama_connection', 'Desconocido')}\n"
                                f"- Logs encontrados: Verificando...\n\n"
                                f"Usa /diagnostic para análisis completo."
                            )
                            await send_safe_message({
                                "role": "bot", 
                                "message": error_msg,
                                "status": "reload_failed"
                            })
                    except Exception as reload_error:
                        error_msg = (
                            f"❌ Error crítico durante recarga:\n"
                            f"**Error:** {str(reload_error)}\n"
                            f"**Tipo:** {type(reload_error).__name__}\n\n"
                            f"Usa /diagnostic para más información."
                        )
                        await send_safe_message({
                            "role": "bot", 
                            "message": error_msg,
                            "status": "reload_critical_error",
                            "error_details": {
                                "error": str(reload_error),
                                "type": type(reload_error).__name__,
                                "traceback": traceback.format_exc()
                            }
                        })
                    continue

                if data.lower().startswith("/set days"):
                    try:
                        parts = data.split()
                        new_days = int(parts[-1])
                        if new_days < 1 or new_days > 365:
                            await send_safe_message({
                                "role": "bot", 
                                "message": "⚠️ Especifica un número entre 1 y 365.\nEjemplo: `/set days 7`"
                            })
                            continue
                        days_range = new_days
                        await send_safe_message({
                            "role": "bot", 
                            "message": f"✅ Rango establecido a {days_range} días.\n💡 Usa `/reload` para aplicar el cambio."
                        })
                    except (ValueError, IndexError):
                        await send_safe_message({
                            "role": "bot", 
                            "message": "⚠️ Formato inválido.\n**Uso correcto:** `/set days <número>`\n**Ejemplo:** `/set days 30`"
                        })
                    except Exception as e:
                        await send_safe_message({
                            "role": "bot", 
                            "message": f"❌ Error inesperado: {str(e)}"
                        })
                    continue

                if data.lower() == "/stat":
                    try:
                        await send_safe_message({
                            "role": "system", 
                            "message": "📊 Cargando estadísticas...",
                            "status": "loading_stats"
                        })
                        
                        logs = load_logs_from_days(days_range)
                        stats = get_stats(logs)
                        
                        # Estadísticas adicionales
                        if logs:
                            sample_log = logs[0] if logs else {}
                            stats += f"\n\n**Detalles adicionales:**\n"
                            stats += f"- Tamaño promedio por log: {sum(len(str(log)) for log in logs[:100]) // min(len(logs), 100)} caracteres\n"
                            stats += f"- Campos disponibles en muestra: {list(sample_log.keys())[:10]}\n"
                            stats += f"- Rango configurado: {days_range} días"
                        
                        await send_safe_message({
                            "role": "bot", 
                            "message": f"📊 **Estadísticas de Logs:**\n\n{stats}",
                            "status": "stats_complete"
                        })
                    except Exception as e:
                        await send_safe_message({
                            "role": "bot", 
                            "message": f"❌ Error obteniendo estadísticas:\n**Error:** {str(e)}\n**Tipo:** {type(e).__name__}"
                        })
                    continue
                
                # Verificar que qa_chain esté disponible antes de procesar pregunta
                if not qa_chain:
                    await send_safe_message({
                        "role": "bot", 
                        "message": (
                            "❌ **Sistema no inicializado correctamente.**\n\n"
                            "**Opciones disponibles:**\n"
                            "- `/reload` - Intentar reinicializar\n"
                            "- `/diagnostic` - Ver diagnóstico completo\n"
                            "- `/status` - Ver estado actual\n\n"
                            "**Nota:** Las consultas de análisis no están disponibles hasta que el sistema esté listo."
                        ),
                        "status": "system_not_ready"
                    })
                    continue
                
                # Procesar pregunta regular con manejo robusto de errores
                chat_history.append(HumanMessage(content=data))
                print(f"🧠 Pregunta recibida ({messages_processed}): {data}")
                
                # Indicar que está procesando
                await send_safe_message({
                    "role": "system", 
                    "message": "🤔 Analizando logs y generando respuesta...",
                    "status": "processing"
                })

                try:
                    # Timeout para la respuesta de Ollama con mejor manejo
                    # Determinar qué contexto usar basado en la pregunta
                    if is_wazuh_related_question(data):
                        print(f"🔍 Pregunta relacionada con Wazuh detectada: {data}")
                        full_message = f"{wazuh_context}\n\nUser question: {data}"
                        mode_info = "🔍 **Modo Wazuh:** Analizando logs de seguridad"
                    else:
                        print(f"💬 Pregunta general detectada: {data}")
                        full_message = f"{general_context}\n\nUser question: {data}"
                        mode_info = "💬 **Modo General:** Asistente general"
                    
                    response = await asyncio.wait_for(
                        asyncio.to_thread(qa_chain.invoke, full_message),
                        timeout=3600  # 2 minutos timeout
                    )
                    
                    answer = response.content.replace("\\n", "\n").strip() if hasattr(response, 'content') else str(response)
                    if not answer:
                        answer = (
                            "⚠️ No pude generar una respuesta para tu consulta.\n\n"
                            "**Sugerencias:**\n"
                            "- Reformula tu pregunta de manera más específica\n"
                            "- Verifica que existan logs en el rango de tiempo configurado\n"
                            "- Usa `/stat` para ver información disponible"
                        )

                    chat_history.append(SystemMessage(content=answer))
                    await send_safe_message({
                        "role": "bot", 
                        "message": f"{mode_info}\n\n{answer}",
                        "status": "response_complete",
                        "processing_time": "< 1 h"
                    })
                    
                except asyncio.TimeoutError:
                    timeout_msg = (
                        "⏰ **Timeout: La consulta tardó más de 1 min.**\n\n"
                        "**Posibles causas:**\n"
                        "- Consulta muy compleja para el modelo\n"
                        "- Problema de conectividad con Ollama\n"
                        "- Volumen de logs muy grande\n\n"
                        "**Sugerencias:**\n"
                        "- Intenta con una pregunta más específica\n"
                        "- Reduce el rango de días con `/set days <número>`\n"
                        "- Verifica el estado con `/diagnostic`"
                    )
                    await send_safe_message({
                        "role": "bot", 
                        "message": timeout_msg,
                        "status": "timeout_error"
                    })
                    # Limpiar el último mensaje del historial
                    if chat_history and isinstance(chat_history[-1], HumanMessage):
                        chat_history.pop()
                        
                except Exception as e:
                    error_details = {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "question": data,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    print(f"❌ Error procesando pregunta: {e}")
                    traceback.print_exc()
                    
                    error_msg = (
                        f"❌ **Error procesando tu consulta:**\n\n"
                        f"**Error:** {str(e)}\n"
                        f"**Tipo:** {type(e).__name__}\n\n"
                        f"**Acciones recomendadas:**\n"
                        f"- Verifica el estado del sistema: `/status`\n"
                        f"- Intenta recargar: `/reload`\n"
                        f"- Si persiste, usa: `/diagnostic`"
                    )
                    
                    await send_safe_message({
                        "role": "bot", 
                        "message": error_msg,
                        "status": "processing_error",
                        "error_details": error_details
                    })
                    
                    # Limpiar el último mensaje del historial
                    if chat_history and isinstance(chat_history[-1], HumanMessage):
                        chat_history.pop()

            except WebSocketDisconnect:
                print(f"⚠️ Cliente desconectado después de {datetime.now() - connection_start}")
                break
                
            except Exception as loop_error:
                error_msg = (
                    f"❌ **Error interno en el bucle de mensajes:**\n\n"
                    f"**Error:** {str(loop_error)}\n"
                    f"**Tipo:** {type(loop_error).__name__}\n\n"
                    f"La conexión se mantendrá activa. Usa `/diagnostic` para más información."
                )
                
                print(f"❌ Error en loop WebSocket: {loop_error}")
                traceback.print_exc()
                
                # Intentar notificar el error sin cerrar la conexión
                success = await send_safe_message({
                    "role": "system", 
                    "message": error_msg,
                    "status": "loop_error",
                    "error_details": {
                        "error": str(loop_error),
                        "type": type(loop_error).__name__,
                        "traceback": traceback.format_exc()
                    }
                })
                
                if not success:
                    print("❌ No se pudo enviar mensaje de error, cerrando conexión")
                    break

    except WebSocketDisconnect:
        print(f"⚠️ Cliente desconectado voluntariamente después de {datetime.now() - connection_start}")
    except Exception as critical_error:
        error_msg = f"❌ Error crítico en WebSocket ({type(critical_error).__name__}): {str(critical_error)}"
        print(error_msg)
        traceback.print_exc()
        
        try:
            await send_safe_message({
                "role": "system", 
                "message": error_msg,
                "status": "critical_error",
                "error_details": {
                    "error": str(critical_error),
                    "type": type(critical_error).__name__,
                    "traceback": traceback.format_exc(),
                    "session_duration": str(datetime.now() - connection_start),
                    "messages_processed": messages_processed
                }
            })
        except:
            print("❌ No se pudo enviar mensaje de error crítico")
    finally:
        session_duration = datetime.now() - connection_start
        print(f"🔌 Cerrando conexión WebSocket - Duración: {session_duration}, Mensajes: {messages_processed}")
        try:
            if not websocket.client_state.DISCONNECTED:
                await websocket.close(code=1000, reason="Session ended normally")
        except:
            pass




@app.on_event("startup")
async def on_startup():
    print("🚀 Iniciando FastAPI y cargando vectorstore...")
    print(f"🔗 Ollama URL configurada: {OLLAMA_BASE_URL}")
    print(f"🤖 Modelo configurado: {OLLAMA_MODEL}")
    success = setup_chain(past_days=days_range)
    if not success:
        print("⚠️ Advertencia: No se pudo inicializar el sistema completamente")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("-H", "--host", type=str, help="Optional remote host IP address to load logs from")
    args = parser.parse_args()
    
    if args.host:
        remote_host = args.host
        
    if args.daemon:
        run_daemon()
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)