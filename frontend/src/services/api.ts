/**
 * InfluenceOS Centralized API Client
 * Connects React frontend to FastAPI REST backend.
 */

import type {
  Agent,
  ApprovalItem,
  Campaign,
  Contract,
  Influencer,
  OutreachStatus,
  TimelineEvent,
} from '@/types'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export interface UserProfile {
  id: string
  full_name: string
  email: string
  company_name?: string | null
  role: string
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserProfile
}

export interface DashboardAnalyticsData {
  metrics: {
    id: string
    label: string
    value: string
    context: string
    trend?: { value: string; positive: boolean }
    sparkline?: number[]
  }[]
  revenueSpendData: {
    month: string
    spend: number
    revenue: number
    roas: number
  }[]
  funnel: { label: string; value: number }[]
  campaignHealth: {
    id: string
    name: string
    health: string
    roas: number
    spend: number
    progress: number
  }[]
}

// Single-flight refresh lock to avoid concurrent refresh storms
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      })
      if (!res.ok) {
        setAccessToken(null)
        return null
      }
      const data: AuthResponse = await res.json()
      setAccessToken(data.access_token)
      return data.access_token
    } catch {
      setAccessToken(null)
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

export async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include', // Always send HttpOnly refresh cookie
  })

  if (res.status === 401 && !isRetry && !path.includes('/auth/login') && !path.includes('/auth/register')) {
    // Attempt automatic refresh once
    const newToken = await refreshAccessToken()
    if (newToken) {
      return request<T>(path, init, true)
    }
  }

  if (!res.ok) {
    let errorDetail = `API Error ${res.status}: ${res.statusText}`
    try {
      const errJson = await res.json()
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail)
      }
    } catch {
      // Keep default error text
    }
    const err = new Error(errorDetail)
    ;(err as any).status = res.status
    throw err
  }

  if (res.status === 204) {
    return {} as T
  }

  return res.json() as Promise<T>
}

export const api = {
  // Auth API
  auth: {
    register: (body: {
      full_name: string
      email: string
      password: string
      company_name?: string
      role?: string
    }) => request<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(body) }),

    login: (body: { email: string; password: string }) =>
      request<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(body) }),

    refresh: () => request<AuthResponse>('/auth/refresh', { method: 'POST' }),

    logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),

    getMe: () => request<UserProfile>('/auth/me'),

    updateProfile: (body: { full_name?: string; company_name?: string; role?: string }) =>
      request<UserProfile>('/users/me', { method: 'PATCH', body: JSON.stringify(body) }),
  },

  // Campaigns API
  campaigns: {
    list: (status?: string) => request<Campaign[]>(`/campaigns${status ? `?status=${status}` : ''}`),
    get: (id: string) => request<Campaign>(`/campaigns/${id}`),
    create: (body: any) => request<Campaign>('/campaigns', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: any) =>
      request<Campaign>(`/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/campaigns/${id}`, { method: 'DELETE' }),
  },

  // Influencers API
  influencers: {
    list: (query?: string) => request<Influencer[]>(`/influencers${query ? `?${query}` : ''}`),
    get: (id: string) => request<Influencer>(`/influencers/${id}`),
    toggleShortlist: (id: string) => request<Influencer>(`/influencers/${id}/shortlist`, { method: 'POST' }),
  },

  // Approvals API
  approvals: {
    list: (status?: string) => request<ApprovalItem[]>(`/approvals${status ? `?status=${status}` : ''}`),
    decide: (id: string, decision: 'approve' | 'reject' | 'edit', reason?: string) =>
      request<ApprovalItem>(`/approvals/${id}`, {
        method: 'POST',
        body: JSON.stringify({ decision, reason }),
      }),
  },

  // Agents API
  agents: {
    list: () => request<Agent[]>('/agents'),
    getTimeline: () => request<TimelineEvent[]>('/agents/timeline'),
  },

  // Contracts API
  contracts: {
    list: (status?: string) => request<Contract[]>(`/contracts${status ? `?status=${status}` : ''}`),
    get: (id: string) => request<Contract>(`/contracts/${id}`),
  },

  // Outreach API
  outreach: {
    list: (status?: string) => request<any[]>(`/outreach${status ? `?status=${status}` : ''}`),
    updateStatus: (id: string, status: OutreachStatus, reply?: string) =>
      request<any>(`/outreach/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status, reply }),
      }),
  },

  // Analytics API
  analytics: {
    get: (campaignId?: string) =>
      request<DashboardAnalyticsData>(`/analytics${campaignId ? `?campaignId=${campaignId}` : ''}`),
  },
}
