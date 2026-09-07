import { useEffect, useMemo, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  Loader2,
  Pencil,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Badge,
  Button,
  Card,
  CardContent,
  Modal,
  StatusChip,
  Textarea,
  useToast,
} from '@/components/ui'
import { cn } from '@/utils'
import type { ApprovalItem } from '@/types'

const TAB_TYPES = [
  { id: 'all', label: 'All Items' },
  { id: 'shortlist', label: 'Shortlist' },
  { id: 'contract', label: 'Contracts' },
  { id: 'outreach', label: 'Outreach' },
  { id: 'budget', label: 'Budget & ROI' },
  { id: 'optimization', label: 'Optimization' },
] as const

interface CampaignApprovalsTabProps {
  campaignId: string
  campaignName: string
  onApprovalResolved?: () => void
}

export function CampaignApprovalsTab({
  campaignId,
  campaignName,
  onApprovalResolved,
}: CampaignApprovalsTabProps) {
  const { toast } = useToast()
  const [activeTypeTab, setActiveTypeTab] = useState('all')
  const [items, setItems] = useState<ApprovalItem[]>([])
  const [history, setHistory] = useState<ApprovalItem[]>([])
  const [loading, setLoading] = useState(true)

  // Decision Modal State
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<ApprovalItem | null>(null)
  const [decisionType, setDecisionType] = useState<'approve' | 'reject' | 'edit'>('approve')
  const [decisionReason, setDecisionReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const loadApprovals = async () => {
    if (!campaignId) return
    setLoading(true)
    try {
      const data = await api.approvals.list(undefined, campaignId)
      if (data) {
        setItems(data.filter((a) => a.status === 'pending'))
        setHistory(data.filter((a) => a.status !== 'pending'))
      }
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Could not load approvals',
        description: err?.message || 'Failed to fetch campaign approvals.',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadApprovals()
  }, [campaignId])

  const filteredItems = useMemo(() => {
    if (activeTypeTab === 'all') return items
    return items.filter(
      (a) => a.type.toLowerCase() === activeTypeTab.toLowerCase()
    )
  }, [items, activeTypeTab])

  const handleOpenDecisionModal = (
    item: ApprovalItem,
    type: 'approve' | 'reject' | 'edit'
  ) => {
    setSelectedItem(item)
    setDecisionType(type)
    setDecisionReason('')
    setModalOpen(true)
  }

  const handleConfirmDecision = async () => {
    if (!selectedItem) return
    setSubmitting(true)
    try {
      await api.approvals.decide(
        selectedItem.id,
        decisionType,
        decisionReason.trim() || undefined
      )

      toast({
        type: decisionType === 'reject' ? 'warning' : 'success',
        title: `Approval ${decisionType === 'reject' ? 'Rejected' : 'Approved'}`,
        description: `Decision recorded for "${selectedItem.action}".`,
      })

      setModalOpen(false)
      await loadApprovals()
      onApprovalResolved?.()
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Decision submission failed',
        description: err?.message || 'Please try again.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header card */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-[16px] border border-border bg-surface/80">
        <div>
          <h3 className="text-base font-semibold text-text">
            Campaign Approvals ({items.length} Pending)
          </h3>
          <p className="text-xs text-text-secondary">
            Human-in-the-loop review for shortlist, agreements, and optimization changes in {campaignName}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={loadApprovals} disabled={loading} className="gap-1.5 text-xs">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Refresh Approvals
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-1.5 pb-1 border-b border-border">
        {TAB_TYPES.map((tab) => {
          const count =
            tab.id === 'all'
              ? items.length
              : items.filter((a) => a.type.toLowerCase() === tab.id.toLowerCase()).length
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTypeTab(tab.id)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5',
                activeTypeTab === tab.id
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-surface hover:bg-surface-elevated text-text-secondary border border-border'
              )}
            >
              <span>{tab.label}</span>
              {count > 0 && (
                <span
                  className={cn(
                    'px-1.5 py-0.2 rounded-full text-[10px]',
                    activeTypeTab === tab.id
                      ? 'bg-white/20 text-white'
                      : 'bg-primary-soft text-primary'
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Pending Items List */}
      {loading ? (
        <div className="py-12 text-center text-text-secondary">
          <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-xs">Loading campaign approvals...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-text-secondary space-y-2">
            <ShieldCheck className="h-10 w-10 mx-auto text-success/60" />
            <h4 className="text-base font-semibold text-text">No Pending Approvals</h4>
            <p className="text-xs max-w-md mx-auto">
              All workflow actions for this campaign are approved or moving forward autonomously.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item) => (
            <Card key={item.id} className="p-4 space-y-3 border-primary/20">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2.5">
                  <span className="p-2 rounded-xl bg-primary-soft text-primary">
                    <Bot className="h-4 w-4" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-bold text-text">{item.action}</h4>
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {item.type}
                      </Badge>
                      <Badge variant="neutral" className="text-[10px]">
                        {item.agent}
                      </Badge>
                    </div>
                    <p className="text-xs text-text-secondary mt-0.5">{item.timestamp}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 text-xs gap-1 text-danger hover:bg-danger-soft"
                    onClick={() => handleOpenDecisionModal(item, 'reject')}
                  >
                    <XCircle className="h-3.5 w-3.5" /> Reject
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-8 text-xs gap-1"
                    onClick={() => handleOpenDecisionModal(item, 'edit')}
                  >
                    <Pencil className="h-3.5 w-3.5" /> Modify
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    className="h-8 text-xs gap-1"
                    onClick={() => handleOpenDecisionModal(item, 'approve')}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                  </Button>
                </div>
              </div>

              {/* Reason / Context */}
              <div className="grid sm:grid-cols-3 gap-3 text-xs">
                <div className="sm:col-span-2 rounded-lg border border-border bg-page/50 p-2.5">
                  <p className="text-[10px] font-semibold uppercase text-text-secondary">AI Rationale</p>
                  <p className="text-xs text-text mt-1 leading-relaxed">{item.reason}</p>
                </div>
                <div className="rounded-lg border border-border bg-page/50 p-2.5 space-y-1.5">
                  <div>
                    <span className="text-[10px] font-semibold uppercase text-text-secondary block">
                      Financial Impact
                    </span>
                    <span className="text-xs font-bold text-text">{item.financialImpact}</span>
                  </div>
                  <div>
                    <span className="text-[10px] font-semibold uppercase text-text-secondary block">
                      AI Confidence
                    </span>
                    <span className="text-xs font-bold text-primary">
                      {Math.round((item.confidence || 0.85) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Decision Modal */}
      {modalOpen && selectedItem && (
        <Modal
          open={modalOpen}
          onClose={() => !submitting && setModalOpen(false)}
          title={`${decisionType === 'approve' ? 'Approve' : decisionType === 'reject' ? 'Reject' : 'Modify'} Workflow Action`}
        >
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold text-text">{selectedItem.action}</p>
              <p className="text-xs text-text-secondary mt-1">{selectedItem.reason}</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-text-secondary mb-1">
                {decisionType === 'approve'
                  ? 'Approval Notes (Optional)'
                  : decisionType === 'reject'
                    ? 'Rejection Reason (Required)'
                    : 'Modification Instructions (Required)'}
              </label>
              <Textarea
                rows={3}
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                placeholder={
                  decisionType === 'approve'
                    ? 'Looks good, approved to proceed.'
                    : decisionType === 'reject'
                      ? 'Explain why this action was rejected...'
                      : 'Provide modified parameters or guidance...'
                }
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setModalOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                variant={decisionType === 'reject' ? 'danger' : 'primary'}
                size="sm"
                onClick={handleConfirmDecision}
                disabled={
                  submitting ||
                  (decisionType !== 'approve' && !decisionReason.trim())
                }
              >
                {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                Confirm {decisionType === 'approve' ? 'Approval' : decisionType === 'reject' ? 'Rejection' : 'Modification'}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Decision History Section */}
      {history.length > 0 && (
        <div className="pt-4 border-t border-border space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-text-secondary">
            Resolved Campaign Decisions ({history.length})
          </p>
          <div className="space-y-2">
            {history.slice(0, 5).map((h) => {
              const decisionNote = (h as any).decision_reason || (h as any).decisionReason || h.reason
              return (
                <div
                  key={h.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-xl border border-border/80 bg-surface/60 text-xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text truncate">{h.action}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {h.type}
                      </Badge>
                    </div>
                    {decisionNote && (
                      <p className="text-text-secondary text-[11px] mt-0.5 truncate">
                        Notes: {decisionNote}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusChip status={h.status} />
                    <span className="text-[11px] text-text-secondary">{h.timestamp}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
