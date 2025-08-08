import { useEffect, useRef, useState, useCallback } from 'react'

interface WebSocketMessage {
    type: 'message' | 'system' | 'error'
    message: string
    role: 'user' | 'assistant'
    timestamp: string
    id: string
}

interface UseWebSocketProps {
    url: string
    headers?: Record<string, string>
    onMessage?: (message: WebSocketMessage) => void
    onConnect?: () => void
    onDisconnect?: () => void
    onError?: (error: Event) => void
}

export const useWebSocket = ({
    url,
    headers = {},
    onMessage,
    onConnect,
    onDisconnect,
    onError
}: UseWebSocketProps) => {
    const [isConnected, setIsConnected] = useState(false)
    const [isConnecting, setIsConnecting] = useState(false)
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
    const reconnectAttempts = useRef(0)
    const maxReconnectAttempts = 5

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        setIsConnecting(true)
        
        // Create WebSocket with headers
        const wsUrl = new URL(url)
        wsRef.current = new WebSocket(wsUrl.toString())

        wsRef.current.onopen = () => {
            console.log('WebSocket conectado')
            setIsConnected(true)
            setIsConnecting(false)
            reconnectAttempts.current = 0
            onConnect?.()
        }

        wsRef.current.onmessage = (event) => {
            console.log('WebSocket message:', event.data)
            try {
                const data: WebSocketMessage = JSON.parse(event.data)
                onMessage?.(data)
            } catch (error) {
                console.error('Error parsing WebSocket message:', error)
            }
        }

        wsRef.current.onclose = (event) => {
            console.log('WebSocket desconectado:', event.code, event.reason)
            setIsConnected(false)
            setIsConnecting(false)
            onDisconnect?.()

            // Reconnection logic
            if (reconnectAttempts.current < maxReconnectAttempts) {
                reconnectAttempts.current++
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000)
                
                reconnectTimeoutRef.current = setTimeout(() => {
                    console.log(`Reintentando conexión (${reconnectAttempts.current}/${maxReconnectAttempts})`)
                    connect()
                }, delay)
            }
        }

        wsRef.current.onerror = (error) => {
            console.error('WebSocket error:', error)
            onError?.(error)
        }
    }, [])

    //url, headers, onMessage, onConnect, onDisconnect, onError
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = null
        }
        
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }
        
        setIsConnected(false)
        setIsConnecting(false)
    }, [])

    const sendMessage = useCallback((message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            const fullMessage: WebSocketMessage = {
                ...message,
                id: Date.now().toString(),
                timestamp: new Date().toISOString()
            }
            wsRef.current.send(JSON.stringify(fullMessage))
            return true
        }
        return false
    }, [])

    useEffect(() => {
        connect()

        return () => {
            disconnect()
        }
    }, [connect, disconnect])

    return {
        isConnected,
        isConnecting,
        sendMessage,
        disconnect,
        connect
    }
} 