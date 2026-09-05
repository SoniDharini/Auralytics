import { formatINR, formatNumber, statusLabel } from '@/utils'
import type { Campaign } from '@/types'

export function formatCompactCount(n: number): string {
  if (!Number.isFinite(n)) return '—'
  const abs = Math.abs(n)
  if (abs >= 1_000_000) {
    const millions = n / 1_000_000
    return `${millions >= 10 ? millions.toFixed(1) : millions.toFixed(2).replace(/\.?0+$/, '')}M`
  }
  if (abs >= 1_000) {
    const thousands = n / 1_000
    return `${thousands >= 100 ? thousands.toFixed(0) : thousands.toFixed(thousands % 1 === 0 ? 0 : 1)}K`
  }
  return formatNumber(n)
}

export function formatMoney(amount: number): string {
  return formatINR(amount || 0, true)
}

export function formatExactMoney(amount: number): string {
  if (!Number.isFinite(amount)) return '—'
  const digits = Math.abs(amount) >= 1 ? 0 : 2
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(amount)
}

export function formatRoas(value: number): string {
  if (!Number.isFinite(value)) return '—'
  return `${value.toFixed(2)}x`
}

export function formatRelativeTime(iso?: string | null): string {
  if (!iso) return 'Not available'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'Not available'
  const diffMs = Date.now() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function campaignHasTrackedTotals(campaign: Pick<Campaign, 'spend' | 'revenue' | 'conversions' | 'reach'>): boolean {
  return (
    (campaign.spend || 0) > 0 ||
    (campaign.revenue || 0) > 0 ||
    (campaign.conversions || 0) > 0 ||
    (campaign.reach || 0) > 0
  )
}

export type HealthTone = 'excellent' | 'healthy' | 'needs_attention' | 'unknown'

export function normalizeHealth(health?: string | null): HealthTone {
  const key = (health || '').toLowerCase().replace(/\s+/g, '_')
  if (key === 'excellent') return 'excellent'
  if (key === 'needs_attention') return 'needs_attention'
  if (key === 'healthy') return 'healthy'
  return key ? 'healthy' : 'unknown'
}

export function healthCopy(health?: string | null): {
  tone: HealthTone
  label: string
  summary: string
  badge: 'success' | 'primary' | 'danger' | 'default'
} {
  const tone = normalizeHealth(health)
  if (tone === 'excellent') {
    return {
      tone,
      label: 'Excellent',
      summary: 'Campaign records mark overall health as excellent.',
      badge: 'success',
    }
  }
  if (tone === 'needs_attention') {
    return {
      tone,
      label: 'Needs Attention',
      summary: 'Campaign records flag this campaign as needing attention.',
      badge: 'danger',
    }
  }
  if (tone === 'healthy') {
    return {
      tone,
      label: 'Healthy',
      summary: 'Campaign records mark overall health as healthy.',
      badge: 'primary',
    }
  }
  return {
    tone,
    label: statusLabel(health || 'Unknown'),
    summary: 'Health is shown from stored campaign records. No separate health score is available.',
    badge: 'default',
  }
}

export function aggregateHealthLabel(campaigns: Pick<Campaign, 'health'>[]): {
  label: string
  summary: string
  badge: 'success' | 'primary' | 'danger' | 'default'
  tone: HealthTone
} {
  if (campaigns.length === 0) {
    return {
      label: 'No campaigns',
      summary: 'Create a campaign to start tracking performance.',
      badge: 'default',
      tone: 'unknown',
    }
  }
  const counts = campaigns.reduce(
    (acc, campaign) => {
      const tone = normalizeHealth(campaign.health)
      acc[tone] += 1
      return acc
    },
    { excellent: 0, healthy: 0, needs_attention: 0, unknown: 0 } as Record<HealthTone, number>,
  )
  const parts = [
    counts.excellent ? `${counts.excellent} excellent` : null,
    counts.healthy ? `${counts.healthy} healthy` : null,
    counts.needs_attention ? `${counts.needs_attention} need attention` : null,
  ].filter(Boolean)

  if (counts.needs_attention > 0) {
    return {
      label: 'Needs Attention',
      summary: `Across ${campaigns.length} campaigns: ${parts.join(', ')}.`,
      badge: 'danger',
      tone: 'needs_attention',
    }
  }
  if (counts.excellent === campaigns.length) {
    return {
      label: 'Excellent',
      summary: `All ${campaigns.length} campaigns are marked excellent in campaign records.`,
      badge: 'success',
      tone: 'excellent',
    }
  }
  return {
    label: 'Healthy',
    summary: `Across ${campaigns.length} campaigns: ${parts.join(', ') || 'health recorded'}.`,
    badge: 'primary',
    tone: 'healthy',
  }
}

export function statusDotClass(status: Campaign['status'] | string): string {
  if (status === 'active') return 'bg-success'
  if (status === 'paused' || status === 'needs_attention') return 'bg-warning'
  if (status === 'completed') return 'bg-primary'
  return 'bg-text-secondary'
}
