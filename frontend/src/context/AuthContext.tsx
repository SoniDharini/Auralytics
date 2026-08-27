import React, { createContext, useContext, useEffect, useState } from 'react'
import { api, setAccessToken, type UserProfile } from '@/services/api'

interface AuthContextType {
  user: UserProfile | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<UserProfile>
  register: (data: {
    full_name: string
    email: string
    password: string
    company_name?: string
    role?: string
  }) => Promise<UserProfile>
  logout: () => Promise<void>
  refreshSession: () => Promise<boolean>
  updateUser: (data: Partial<UserProfile>) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const restore = async () => {
      try {
        const authData = await api.auth.refresh()
        if (cancelled) return
        if (authData?.access_token && authData?.user) {
          setAccessToken(authData.access_token)
          setUser(authData.user)
        } else {
          setUser(null)
          setAccessToken(null)
        }
      } catch {
        if (!cancelled) {
          setUser(null)
          setAccessToken(null)
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    restore()
    return () => {
      cancelled = true
    }
  }, [])

  const login = async (email: string, password: string): Promise<UserProfile> => {
    const res = await api.auth.login({ email, password })
    setAccessToken(res.access_token)
    setUser(res.user)
    return res.user
  }

  const register = async (data: {
    full_name: string
    email: string
    password: string
    company_name?: string
    role?: string
  }): Promise<UserProfile> => {
    const res = await api.auth.register(data)
    setAccessToken(res.access_token)
    setUser(res.user)
    return res.user
  }

  const logout = async () => {
    try {
      await api.auth.logout()
    } catch {
      // Continue client-side teardown even if server logout errored
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }

  const refreshSession = async (): Promise<boolean> => {
    try {
      const res = await api.auth.refresh()
      if (res?.access_token && res?.user) {
        setAccessToken(res.access_token)
        setUser(res.user)
        return true
      }
      return false
    } catch {
      setAccessToken(null)
      setUser(null)
      return false
    }
  }

  const updateUser = (data: Partial<UserProfile>) => {
    if (user) {
      setUser({ ...user, ...data })
    }
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshSession,
    updateUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
