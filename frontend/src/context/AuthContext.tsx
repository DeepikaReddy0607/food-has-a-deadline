import React, { createContext, useContext, useState, useEffect } from 'react'
import { apiService } from '@/services/api'
import type { UserPublic, TokenResponse } from '@/types'

interface AuthContextType {
  user: UserPublic | null
  token: string | null
  loading: boolean
  login: (tokenData: TokenResponse) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserPublic | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('fhd_token'))
  const [loading, setLoading] = useState<boolean>(true)

  const refreshUser = async () => {
    try {
      if (localStorage.getItem('fhd_token')) {
        const userData = await apiService.getMe()
        setUser(userData)
      } else {
        setUser(null)
      }
    } catch {
      localStorage.removeItem('fhd_token')
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshUser()
  }, [])

  const login = async (tokenData: TokenResponse) => {
    localStorage.setItem('fhd_token', tokenData.access_token)
    setToken(tokenData.access_token)
    await refreshUser()
  }

  const logout = () => {
    localStorage.removeItem('fhd_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
