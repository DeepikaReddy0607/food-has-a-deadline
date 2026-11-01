import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import type { UserRole } from '@/types'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles }) => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="max-w-md mx-auto mt-12 p-6 rounded-lg border border-destructive/30 bg-destructive/10 text-center">
        <h2 className="text-lg font-semibold text-destructive">Access Restricted</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your account role (<span className="font-semibold">{user.role}</span>) does not have permission to access this area.
        </p>
      </div>
    )
  }

  return <Outlet />
}
