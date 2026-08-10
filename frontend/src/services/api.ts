/**
 * API client stubs for future FastAPI backend integration.
 * Currently the UI uses mock data from `@/mock-data`.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  getCampaigns: () => request('/campaigns'),
  getCampaign: (id: string) => request(`/campaigns/${id}`),
  createCampaign: (body: unknown) =>
    request('/campaigns', { method: 'POST', body: JSON.stringify(body) }),
  getInfluencers: (query?: string) =>
    request(`/influencers${query ? `?${query}` : ''}`),
  getApprovals: () => request('/approvals'),
  decideApproval: (id: string, decision: 'approve' | 'reject' | 'edit') =>
    request(`/approvals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    }),
  getAgents: () => request('/agents'),
  getAnalytics: (campaignId?: string) =>
    request(`/analytics${campaignId ? `?campaignId=${campaignId}` : ''}`),
}
