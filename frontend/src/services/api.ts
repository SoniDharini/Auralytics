/**
 * InfluenceOS Centralized API Client
 * Connects React frontend to FastAPI REST backend.
 */

import type {
  Agent,
  ApprovalItem,
  Campaign,
  CampaignActivity,
  CampaignCreator,
  CampaignCreatorListResponse,
  CampaignCreatorStatus,
  CampaignStrategy,
  CampaignWorkflow,
  Contract,
  ContractReadiness,
  ContractTermsPayload,
  DashboardSummary,
  DiscoveryResponse,
  Influencer,
  InfluencerFetchResponse,
  IntegrationStatus,
  AgentRun,
  AIStatus,
  OutreachMessageItem,
  OutreachNegotiateResponse,
  OutreachStatus,
  SupervisorStartResponse,
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

const AUTH_PATHS_SKIP_REFRESH = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout']

// Single-flight refresh lock to avoid concurrent refresh storms / token rotation races.
let refreshPromise: Promise<AuthResponse | null> | null = null

async function refreshSession(): Promise<AuthResponse | null> {
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
      return data
    } catch {
      setAccessToken(null)
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

async function refreshAccessToken(): Promise<string | null> {
  const data = await refreshSession()
  return data?.access_token ?? null
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

  const skipRefresh = AUTH_PATHS_SKIP_REFRESH.some((p) => path.includes(p))
  if (res.status === 401 && !isRetry && !skipRefresh) {
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

    refresh: async () => {
      const data = await refreshSession()
      if (!data) {
        const err = new Error('Session expired or revoked')
        ;(err as any).status = 401
        throw err
      }
      return data
    },

    logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),

    getMe: () => request<UserProfile>('/auth/me'),

    updateProfile: (body: { full_name?: string; company_name?: string; role?: string }) =>
      request<UserProfile>('/users/me', { method: 'PATCH', body: JSON.stringify(body) }),
  },

  // Dashboard API
  dashboard: {
    getSummary: () => request<DashboardSummary>('/dashboard/summary'),
  },

  // Campaigns API
  campaigns: {
    list: (status?: string) => request<Campaign[]>(`/campaigns${status ? `?status=${status}` : ''}`),
    get: (id: string) => request<Campaign>(`/campaigns/${id}`),
    create: (body: any) => request<Campaign>('/campaigns', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: any) =>
      request<Campaign>(`/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/campaigns/${id}`, { method: 'DELETE' }),
    getActivities: (id: string) => request<CampaignActivity[]>(`/campaigns/${id}/activities`),
    getWorkflow: (id: string) => request<CampaignWorkflow>(`/campaigns/${id}/workflow`),
    fetchInfluencers: (
      id: string,
      payload?: { platforms?: string[]; limit?: number; force_refresh?: boolean },
    ) =>
      request<InfluencerFetchResponse>(`/campaigns/${id}/fetch-influencers`, {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
  },

  // Campaign-scoped creator discovery.
  // `discover` is the only call that contacts YouTube; everything else reads PostgreSQL.
  discovery: {
    discover: (campaignId: string, options?: { refresh?: boolean; limit?: number }) => {
      const params = new URLSearchParams()
      if (options?.refresh) params.set('refresh', 'true')
      if (options?.limit) params.set('limit', String(options.limit))
      const qs = params.toString()
      return request<DiscoveryResponse>(
        `/campaigns/${campaignId}/discover-creators${qs ? `?${qs}` : ''}`,
        { method: 'POST' },
      )
    },

    listCreators: (
      campaignId: string,
      params?: {
        page?: number
        limit?: number
        sort?: string
        status?: string
        min_subscribers?: number
        max_subscribers?: number
        min_engagement?: number
        search?: string
      },
    ) => {
      const search = new URLSearchParams()
      Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          search.set(key, String(value))
        }
      })
      const qs = search.toString()
      return request<CampaignCreatorListResponse>(
        `/campaigns/${campaignId}/influencers${qs ? `?${qs}` : ''}`,
      )
    },

    getCreator: (campaignId: string, influencerId: string) =>
      request<CampaignCreator>(`/campaigns/${campaignId}/influencers/${influencerId}`),

    setStatus: (campaignId: string, influencerId: string, status: CampaignCreatorStatus) =>
      request<CampaignCreator>(`/campaigns/${campaignId}/influencers/${influencerId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      }),
  },

  // Activities API
  activities: {
    list: (campaignId?: string, limit = 20) =>
      request<CampaignActivity[]>(`/activities?limit=${limit}${campaignId ? `&campaign_id=${campaignId}` : ''}`),
  },

  // Influencers API
  influencers: {
    list: (query?: string) => request<Influencer[]>(`/influencers${query ? `?${query}` : ''}`),
    get: (id: string) => request<Influencer>(`/influencers/${id}`),
    toggleShortlist: (id: string) => request<Influencer>(`/influencers/${id}/shortlist`, { method: 'POST' }),
    refresh: (id: string) => request<Influencer>(`/influencers/${id}/refresh`, { method: 'POST' }),
  },

  // Integrations API
  integrations: {
    getStatus: () => request<IntegrationStatus>('/integrations/status'),
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
    listRuns: (limit = 50) => request<AgentRun[]>(`/agent-runs?limit=${limit}`),
    getRun: (id: string) => request<AgentRun>(`/agent-runs/${id}`),
    start: (campaignId: string) =>
      request<SupervisorStartResponse>(`/campaigns/${campaignId}/agents/start`, { method: 'POST' }),
    runStrategy: (campaignId: string) =>
      request<SupervisorStartResponse>(`/campaigns/${campaignId}/agents/strategy`, { method: 'POST' }),
    runDiscovery: (campaignId: string) =>
      request<SupervisorStartResponse>(`/campaigns/${campaignId}/agents/discovery`, { method: 'POST' }),
    runOutreach: (campaignId: string, influencerId?: string) =>
      request<SupervisorStartResponse>(
        `/campaigns/${campaignId}/agents/outreach${influencerId ? `?influencer_id=${influencerId}` : ''}`,
        { method: 'POST' },
      ),
    runContract: (campaignId: string, influencerId: string) =>
      request<SupervisorStartResponse>(
        `/campaigns/${campaignId}/agents/contract?influencer_id=${influencerId}`,
        { method: 'POST' },
      ),
    getStrategy: (campaignId: string) =>
      request<CampaignStrategy | null>(`/campaigns/${campaignId}/agents/strategy`),
    listCampaignRuns: (campaignId: string) =>
      request<AgentRun[]>(`/campaigns/${campaignId}/agents/runs`),
  },

  ai: {
    status: (probe = true) => request<AIStatus>(`/ai/status?probe=${probe ? 'true' : 'false'}`),
  },

  // Contracts API
  contracts: {
    list: (status?: string, campaignId?: string, influencerId?: string) => {
      const params = new URLSearchParams()
      if (status && status !== 'all') params.set('status', status)
      if (campaignId) params.set('campaign_id', campaignId)
      if (influencerId) params.set('influencer_id', influencerId)
      const qs = params.toString()
      return request<Contract[]>(`/contracts${qs ? `?${qs}` : ''}`)
    },
    get: (id: string) => request<Contract>(`/contracts/${id}`),
    checkReadiness: (campaignId: string, influencerId: string) =>
      request<ContractReadiness>(`/contracts/readiness?campaign_id=${campaignId}&influencer_id=${influencerId}`),
    listCampaignReadiness: (campaignId: string) =>
      request<ContractReadiness[]>(`/contracts/campaign-readiness/${campaignId}`),
    analyze: (
      campaignId: string,
      payload: { influencer_id: string; contract_text?: string; custom_terms?: Record<string, any>; confirmed_terms?: ContractTermsPayload },
    ) =>
      request<SupervisorStartResponse>(`/contracts/analyze/${campaignId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    approve: (contractId: string, notes?: string) =>
      request<Contract>(`/contracts/${contractId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }),
    requestChanges: (contractId: string, requestedChanges: string, reason: string) =>
      request<Contract>(`/contracts/${contractId}/request-changes`, {
        method: 'POST',
        body: JSON.stringify({ requested_changes: requestedChanges, reason }),
      }),
    reject: (contractId: string, reason: string, notes?: string) =>
      request<Contract>(`/contracts/${contractId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason, notes }),
      }),
    updateBody: (contractId: string, contractBody: string, reanalyze = false) =>
      request<Contract>(`/contracts/${contractId}/body`, {
        method: 'PATCH',
        body: JSON.stringify({ contract_body: contractBody, reanalyze }),
      }),
  },

  // Outreach API
  outreach: {
    list: (campaignId?: string, status?: string) => {
      const params = new URLSearchParams()
      if (campaignId) params.set('campaign_id', campaignId)
      if (status) params.set('status', status)
      const qs = params.toString()
      return request<any[]>(`/outreach${qs ? `?${qs}` : ''}`)
    },
    generate: (campaignId: string, influencerId?: string) =>
      request<SupervisorStartResponse>(`/outreach/generate/${campaignId}`, {
        method: 'POST',
        body: JSON.stringify({ influencer_id: influencerId }),
      }),
    negotiate: (outreachId: string, influencerReply: string, userInstruction?: string) =>
      request<OutreachNegotiateResponse>(`/outreach/${outreachId}/negotiate`, {
        method: 'POST',
        body: JSON.stringify({
          influencer_reply: influencerReply,
          user_instruction: userInstruction,
        }),
      }),
    decide: (outreachId: string, status: string, agreedTerms?: Record<string, any>, note?: string) =>
      request<OutreachMessageItem>(`/outreach/${outreachId}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          status,
          agreed_terms: agreedTerms,
          note,
        }),
      }),
    saveAcceptance: (outreachId: string, payload: import('@/types').OutreachAcceptancePayload) =>
      request<OutreachMessageItem>(`/outreach/${outreachId}/acceptance`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    saveRejection: (outreachId: string, payload: import('@/types').OutreachRejectionPayload) =>
      request<OutreachMessageItem>(`/outreach/${outreachId}/rejection`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    generateContract: (outreachId: string, payload?: { confirmed_terms?: ContractTermsPayload; custom_terms?: Record<string, any>; contract_text?: string }) =>
      request<SupervisorStartResponse>(`/outreach/${outreachId}/generate-contract`, {
        method: 'POST',
        body: payload ? JSON.stringify(payload) : undefined,
      }),
    updateStatus: (
      id: string,
      status: OutreachStatus | string,
      reply?: string,
      body?: string,
      short_dm?: string,
      negotiation_state?: string,
      extracted_terms?: Record<string, any>,
    ) =>
      request<any>(`/outreach/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status, reply, body, short_dm, negotiation_state, extracted_terms }),
      }),
  },

  // Analytics API
  analytics: {
    get: (campaignId?: string) =>
      request<DashboardAnalyticsData>(`/analytics${campaignId ? `?campaignId=${campaignId}` : ''}`),
  },
}
