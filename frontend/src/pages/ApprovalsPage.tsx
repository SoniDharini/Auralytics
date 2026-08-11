import { useEffect, useMemo, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  Clock,
  IndianRupee,
  Pencil,
  Sparkles,
  Target,
  XCircle,
} from 'lucide-react'
import { approvals as initialApprovals, approvalHistory } from '@/mock-data'
import { api } from '@/services/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatusChip,
  Tabs,
  useToast,
} from '@/components/ui'
import { cn } from '@/utils'
import type { ApprovalItem, ApprovalStatus } from '@/types'

const TAB_TYPES = [
  { id: 'all', label: 'All' },
  { id: 'outreach', label: 'Outreach' },
  { id: 'negotiation', label: 'Negotiation' },
  { id: 'budget', label: 'Budget' },
  { id: 'campaign', label: 'Campaign' },
  { id: 'contract', label: 'Contract' },
] as const

const typeVariant: Record<ApprovalItem['type'], 'primary' | 'ai' | 'warning' | 'success' | 'danger'> = {
  outreach: 'primary',
  negotiation: 'ai',
  budget: 'warning',
  campaign: 'success',
  contract: 'danger',
}

export function ApprovalsPage() {
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState('all')
  const [items, setItems] = useState<ApprovalItem[]>(initialApprovals)

  useEffect(() => {
    let mounted = true
    api.approvals
      .list()
      .then((data) => {
        if (mounted && data && data.length > 0) {
          setItems(data)
        }
      })
      .catch(() => {})

    return () => {
      mounted = false
    }
  }, [])

  const tabs = useMemo(
    () =>
      TAB_TYPES.map((tab) => ({
        ...tab,
        count:
          tab.id === 'all'
            ? items.filter((a) => a.status === 'pending').length
            : items.filter((a) => a.type === tab.id && a.status === 'pending').length,
      })),
    [items],
  )

  const filtered = useMemo(() => {
    const pending = items.filter((a) => a.status === 'pending')
    if (activeTab === 'all') return pending
    return pending.filter((a) => a.type === activeTab)
  }, [items, activeTab])

  const updateStatus = async (id: string, status: ApprovalStatus) => {
    setItems((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)))
    try {
      const decision = status === 'approved' ? 'approve' : status === 'rejected' ? 'reject' : 'edit'
      await api.approvals.decide(id, decision)
    } catch {
      // Revert if error
    }
  }

  const handleApprove = (item: ApprovalItem) => {
    updateStatus(item.id, 'approved')
    toast({
      type: 'success',
      title: 'Approval confirmed',
      description: `${item.action} has been approved.`,
    })
  }

  const handleReject = (item: ApprovalItem) => {
    updateStatus(item.id, 'rejected')
    toast({
      type: 'warning',
      title: 'Request rejected',
      description: 'The agent will be notified of your decision.',
    })
  }

  const handleEdit = (item: ApprovalItem) => {
    updateStatus(item.id, 'edited')
    toast({
      type: 'info',
      title: 'Marked for edit',
      description: 'You can refine this action before approving.',
    })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-[32px] font-bold tracking-tight">Approvals</h1>
        <p className="text-text-secondary mt-1">
          Review and approve actions proposed by your AI agent team.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-0">
          <div>
            <CardTitle>Pending Approvals</CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">
              {filtered.length} item{filtered.length !== 1 ? 's' : ''} awaiting your decision
            </p>
          </div>
          <Badge variant="warning" pulse>
            {items.filter((a) => a.status === 'pending').length} pending
          </Badge>
        </CardHeader>
        <CardContent className="pt-4">
          <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} className="mb-5" />

          {filtered.length === 0 ? (
            <div className="text-center py-12 text-text-secondary">
              <CheckCircle2 className="h-10 w-10 mx-auto text-success mb-3" />
              <p className="font-semibold text-text">All caught up</p>
              <p className="text-sm mt-1">No pending approvals in this category.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filtered.map((item) => (
                <ApprovalCard
                  key={item.id}
                  item={item}
                  onApprove={() => handleApprove(item)}
                  onReject={() => handleReject(item)}
                  onEdit={() => handleEdit(item)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Approval History</CardTitle>
          <p className="text-sm text-text-secondary mt-0.5">Recent decisions across all agents</p>
        </CardHeader>
        <CardContent className="space-y-3">
          {approvalHistory.map((item) => (
            <div
              key={item.id}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-border bg-page/50"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="text-sm font-semibold">{item.action}</span>
                  <StatusChip status={item.status} />
                </div>
                <p className="text-xs text-text-secondary">
                  {item.agent} · {item.campaign} · {item.timestamp}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-text-secondary shrink-0">
                <Sparkles className="h-3.5 w-3.5 text-ai" />
                {item.confidence}% confidence
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function ApprovalCard({
  item,
  onApprove,
  onReject,
  onEdit,
}: {
  item: ApprovalItem
  onApprove: () => void
  onReject: () => void
  onEdit: () => void
}) {
  return (
    <div className="rounded-xl border border-border p-5 hover:border-primary/25 transition-colors bg-white">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary-soft text-primary flex items-center justify-center">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold">{item.agent}</p>
            <Badge variant={typeVariant[item.type]} className="mt-0.5 capitalize">
              {item.type}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          <Clock className="h-3.5 w-3.5" />
          {item.timestamp}
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary mb-1">
            Recommended action
          </p>
          <p className="text-sm font-medium">{item.action}</p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-text-secondary mb-1">
            Reason
          </p>
          <p className="text-sm text-text-secondary">{item.reason}</p>
        </div>

        <div className="grid sm:grid-cols-3 gap-3 pt-2">
          <MetaField icon={Target} label="Campaign" value={item.campaign} />
          <MetaField icon={IndianRupee} label="Financial impact" value={item.financialImpact} />
          <MetaField
            icon={Sparkles}
            label="Confidence"
            value={`${item.confidence}%`}
            highlight
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-5 pt-4 border-t border-border">
        <Button variant="danger" size="sm" className="gap-1.5" onClick={onReject}>
          <XCircle className="h-3.5 w-3.5" /> Reject
        </Button>
        <Button variant="secondary" size="sm" className="gap-1.5" onClick={onEdit}>
          <Pencil className="h-3.5 w-3.5" /> Edit
        </Button>
        <Button size="sm" className="gap-1.5 ml-auto sm:ml-0" onClick={onApprove}>
          <CheckCircle2 className="h-3.5 w-3.5" /> Approve
        </Button>
      </div>
    </div>
  )
}

function MetaField({
  icon: Icon,
  label,
  value,
  highlight,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2.5">
      <p className="text-[11px] text-text-secondary flex items-center gap-1 mb-0.5">
        <Icon className="h-3 w-3" /> {label}
      </p>
      <p className={cn('text-sm font-semibold truncate', highlight && 'text-primary')}>{value}</p>
    </div>
  )
}
