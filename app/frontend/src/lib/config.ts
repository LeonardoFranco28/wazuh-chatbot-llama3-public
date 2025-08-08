// Configuration file for API keys and settings
export const config = {
    // API Keys
    API_KEY: process.env.NEXT_PUBLIC_API_KEY || "Toor0128#$",
    
    // WebSocket Configuration
    WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/chat",
    
    // Auth Configuration
    AUTH_URL: process.env.NEXT_PUBLIC_AUTH_URL || "http://localhost:3000/api/auth",
    
    // App Configuration
    APP_NAME: "Wazuh Chat",
    APP_DESCRIPTION: "Chat en tiempo real para análisis de seguridad"
}

// Headers for API requests
export const getApiHeaders = () => ({
    'X-API-Key': config.API_KEY,
    'Content-Type': 'application/json'
})

// WebSocket headers
export const getWebSocketHeaders = () => ({
    'X-API-Key': config.API_KEY
}) 