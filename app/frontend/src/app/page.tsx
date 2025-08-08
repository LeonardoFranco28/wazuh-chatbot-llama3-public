"use client"
import { useSession } from "@/lib/auth.client"
import Login from "./components/auth/Login"
import Chat from "./components/chat/Chat"
import { useEffect, useState } from "react"

export default function Home() {
  const { data: session, isPending } = useSession()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Show loading state while checking authentication
  if (!mounted || isPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Verificando autenticación...</p>
        </div>
      </div>
    )
  }

  // Show login if not authenticated
  if (!session) {
    return <Login />
  }

  // Show chat if authenticated
  return <Chat />
}
