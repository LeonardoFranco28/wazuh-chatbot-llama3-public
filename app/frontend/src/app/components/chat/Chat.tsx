"use client"
import { useState, useRef, useEffect } from "react"
import { signOut } from "@/lib/auth.client"
import { useWebSocket } from "../../hooks/useWebSocket"
import { config, getWebSocketHeaders } from "@/lib/config"

interface Message {
    id: string
    message: string | null
    role: "user" | "assistant"
    timestamp: Date
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([
       
    ])
    const [inputValue, setInputValue] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // WebSocket connection
    const { isConnected, isConnecting, sendMessage } = useWebSocket({
        url: config.WS_URL,
        headers: getWebSocketHeaders(),
        onMessage: (wsMessage) => {
            console.log(wsMessage)
            const message: Message = {
                id: wsMessage.id,
                message: wsMessage?.message || "",
                role: wsMessage.role,
                timestamp: new Date(wsMessage?.timestamp || new Date())
            }
            setMessages(prev => [...prev, message])
            setIsLoading(false)
        },
        onConnect: () => {
            console.log('Conectado al chat en tiempo real')
        },
        onDisconnect: () => {
            console.log('Desconectado del chat')
        },
        onError: (error) => {
            console.error('Error en WebSocket:', error)
            setIsLoading(false)
        }
    })

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!inputValue.trim() || isLoading || !isConnected) return

        const userMessage: Message = {
            id: Date.now().toString(),
            message: inputValue,
            role: "user",
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMessage])
        setInputValue("")
        setIsLoading(true)

        // Send message via WebSocket
        const sent = sendMessage({
            type: 'message',
            message: inputValue,
            role: 'user'
        })

        if (!sent) {
            // Fallback if WebSocket is not available
            setTimeout(() => {
                const assistantMessage: Message = {
                    id: (Date.now() + 1).toString(),
                    message: "Lo siento, no puedo procesar tu mensaje en este momento. Verifica tu conexión.",
                    role: "assistant",
                    timestamp: new Date()
                }
                setMessages(prev => [...prev, assistantMessage])
                setIsLoading(false)
            }, 1000)
        }
    }

    const handleLogout = async () => {
        try {
            await signOut()
        } catch (error) {
            console.error("Error al cerrar sesión:", error)
        }
    }

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        })
    }

    const getConnectionStatus = () => {
        if (isConnecting) return { text: "Conectando...", color: "yellow", icon: "connecting" }
        if (isConnected) return { text: "En línea", color: "green", icon: "connected" }
        return { text: "Desconectado", color: "red", icon: "disconnected" }
    }

    const status = getConnectionStatus()

    return (
        <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
            {/* Header */}
            <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                        </div>
                        <div>
                            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {config.APP_NAME}
                            </h1>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                {config.APP_DESCRIPTION}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 bg-${status.color}-500 rounded-full ${
                                status.icon == 'connecting' ? 'animate-pulse' : 
                                status.icon == 'connected' ? 'animate-pulse' : ''
                            }`}></div>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                                {status.text}
                            </span>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                            </svg>
                            <span>Cerrar sesión</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                {messages.map((message, index) => (
                    <div
                        key={index}
                        className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                        <div
                            className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-2xl ${
                                message.role === "user"
                                    ? "bg-blue-600 text-white"
                                    : "bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700"
                            }`}
                        >
                            <p className="text-sm leading-relaxed">{message.message}</p>
                            <p className={`text-xs mt-2 ${
                                message.role === "user" 
                                    ? "text-blue-100" 
                                    : "text-gray-500 dark:text-gray-400"
                            }`}>
                                {formatTime(message.timestamp)}
                            </p>
                        </div>
                    </div>
                ))}
                
                {/* Loading indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-2xl">
                            <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                        </div>
                    </div>
                )}
                
                <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
                <form onSubmit={handleSubmit} className="flex space-x-4">
                    <div className="flex-1 relative">
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder={isConnected ? "Escribe tu mensaje..." : "Conectando..."}
                            disabled={isLoading || !isConnected}
                            className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50"
                        />
                        <button
                            type="submit"
                            disabled={!inputValue.trim() || isLoading || !isConnected}
                            className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                </form>
                
                {/* Connection Status */}
                {!isConnected && (
                    <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <div className="flex items-center">
                            <svg className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            <span className="text-sm text-yellow-700 dark:text-yellow-300">
                                {isConnecting ? "Conectando al servidor..." : "Sin conexión al servidor"}
                            </span>
                        </div>
                    </div>
                )}
                
                {/* Quick Actions */}
                <div className="mt-3 flex flex-wrap gap-2">
                    {["Hola", "¿Cómo estás?", "Ayuda", "Información"].map((suggestion) => (
                        <button
                            key={suggestion}
                            onClick={() => setInputValue(suggestion)}
                            disabled={isLoading || !isConnected}
                            className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                        >
                            {suggestion}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
} 