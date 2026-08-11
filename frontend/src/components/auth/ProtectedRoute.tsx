import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Loader2 } from 'lucide-react'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-page flex flex-col items-center justify-center gap-3">
        <div className="h-10 w-10 rounded-xl ai-gradient-bg flex items-center justify-center text-white font-bold animate-pulse">
          A
        </div>
        <div className="flex items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <span>Restoring session...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
