import { cn, statusLabel } from '@/utils'
import type { CampaignStatus, ContractStatus, HealthStatus, OutreachStatus } from '@/types'
import { Badge } from './Badge'

type Status = CampaignStatus | ContractStatus | HealthStatus | OutreachStatus | string

const map: Record<string, { variant: 'primary' | 'success' | 'warning' | 'danger' | 'default' | 'ai' | 'outline'; label?: string }> = {
  active: { variant: 'success' },
  draft: { variant: 'default' },
  planning: { variant: 'ai' },
  paused: { variant: 'warning' },
  completed: { variant: 'primary' },
  needs_attention: { variant: 'danger', label: 'Needs Attention' },
  excellent: { variant: 'success' },
  healthy: { variant: 'primary' },
  signed: { variant: 'success' },
  pending_signature: { variant: 'warning', label: 'Pending Signature' },
  expired: { variant: 'default' },
  at_risk: { variant: 'danger', label: 'At Risk' },
  not_contacted: { variant: 'default', label: 'Not Contacted' },
  draft_ready: { variant: 'ai', label: 'Draft Ready' },
  awaiting_approval: { variant: 'warning', label: 'Awaiting Approval' },
  sent: { variant: 'primary' },
  replied: { variant: 'primary' },
  negotiating: { variant: 'warning' },
  accepted: { variant: 'success' },
  rejected: { variant: 'danger' },
  pending: { variant: 'warning' },
  approved: { variant: 'success' },
  edited: { variant: 'ai' },
}

export function StatusChip({ status, className }: { status: Status; className?: string }) {
  const config = map[status] || { variant: 'default' as const }
  return (
    <Badge variant={config.variant} className={cn(className)} pulse={status === 'active'}>
      {config.label || statusLabel(status)}
    </Badge>
  )
}
