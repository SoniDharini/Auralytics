import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Check,
  Edit3,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  X,
} from 'lucide-react'
import { Badge, Button, Card, CardContent, CardHeader, Input, Modal, Select, useToast } from '@/components/ui'
import { cn } from '@/utils'
import { api } from '@/services/api'
import type { Campaign, OptimizationPlan, OptimizationRecommendation } from '@/types'

export function OptimizationPage() {
  const { toast } = useToast()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('')
  const [optimizationPlan, setOptimizationPlan] = useState<OptimizationPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})

  // Modification dialog state
  const [modifyModalOpen, setModifyModalOpen] = useState(false)
  const [modifyingApprovalId, setModifyingApprovalId] = useState<string | null>(null)
  const [modifyNote, setModifyNote] = useState<string>('')

  const loadCampaignsAndPlan = useCallback(async () => {
    setLoading(true)
    try {
      const camps = await api.campaigns.list()
      setCampaigns(camps || [])
      if (camps && camps.length > 0) {
        const campId = selectedCampaignId || camps[0].id
        setSelectedCampaignId(campId)
        const plan = await api.content.getLatestOptimization(campId)
        setOptimizationPlan(plan)
      }
    } catch (err) {
      console.error('Failed to load optimization plan', err)
    } finally {
      setLoading(false)
    }
  }, [selectedCampaignId])

  useEffect(() => {
    loadCampaignsAndPlan()
  }, [loadCampaignsAndPlan])

  const handleCampaignChange = async (newCampId: string) => {
    setSelectedCampaignId(newCampId)
    setLoading(true)
    try {
      const plan = await api.content.getLatestOptimization(newCampId)
      setOptimizationPlan(plan)
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (approvalId: string, action: 'approved' | 'rejected' | 'modified', reason?: string) => {
    if (!selectedCampaignId) return
    setActionLoading((prev) => ({ ...prev, [approvalId]: true }))
    try {
      const updatedPlan = await api.content.decideOptimization(selectedCampaignId, {
        approval_id: approvalId,
        decision: action,
        reason,
      })
      setOptimizationPlan(updatedPlan)
      const messages = {
        approved: {
          title: 'Recommendation approved',
          description: 'Synced with Approval Center. Next actions approved.',
          type: 'success' as const,
        },
        rejected: {
          title: 'Recommendation rejected',
          description: 'Marked as rejected in Approval Center.',
          type: 'info' as const,
        },
        modified: {
          title: 'Modification recorded',
          description: 'Your changes have been saved to Approval Center.',
          type: 'warning' as const,
        },
      }
      toast(messages[action])
    } catch (err: any) {
      toast({ title: 'Action failed', description: err?.message || 'Could not record decision.', type: 'error' })
    } finally {
      setActionLoading((prev) => ({ ...prev, [approvalId]: false }))
    }
  }

  const recommendations: OptimizationRecommendation[] = optimizationPlan?.recommendations || []


  return (
    <div className="space-y-6 animate-fade-in">
      <header className="relative overflow-hidden rounded-[20px] border border-border bg-surface px-5 py-5 shadow-[0_8px_30px_rgba(17,24,39,0.04)] sm:px-6">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(1200px_circle_at_0%_-20%,rgba(91,95,239,0.10),transparent_45%),radial-gradient(800px_circle_at_100%_0%,rgba(139,92,246,0.08),transparent_40%)]" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Optimization Agent</p>
            <h1 className="mt-1 text-[28px] font-bold tracking-tight sm:text-[32px]">What should we change?</h1>
            <p className="mt-1 text-text-secondary">
              AI recommends budget and creator adjustments. You decide before anything is applied.
            </p>
          </div>
          <Link to="/app/analytics">
            <Button variant="secondary" className="gap-2">
              View Analytics <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </header>

      <Card className="border-l-4 border-l-warning bg-amber-50/40">
        <CardContent className="py-4 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-start gap-3 flex-1">
            <div className="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text">AI recommends. You decide.</p>
              <p className="text-sm text-text-secondary mt-1 leading-relaxed">
                All budget reallocations, rate adjustments, and spend modifications require your explicit approval
                before the Optimization Agent executes changes. No financial actions are applied automatically.
              </p>
            </div>
          </div>
          <Link to="/app/approvals">
            <Button variant="secondary" className="gap-2 shrink-0">
              Approval Center <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </CardContent>
      </Card>

      {/* Campaign Selector */}
      {campaigns.length > 1 && (
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-text-secondary uppercase">Campaign:</span>
          <div className="w-64">
            <Select
              value={selectedCampaignId}
              onChange={(e) => handleCampaignChange(e.target.value)}
              options={campaigns.map((c) => ({ value: c.id, label: c.name }))}
            />
          </div>
        </div>
      )}

      {loading ? (
        <Card>
          <CardContent className="py-16 text-center space-y-3">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-sm text-text-secondary">Loading campaign optimization plan...</p>
          </CardContent>
        </Card>
      ) : recommendations.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-violet-50 text-ai flex items-center justify-center">
              <Sparkles className="h-7 w-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-text">No optimization recommendations yet</h3>
              <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                Track campaign content on the Analytics page and run the Performance Agent first. The Optimization Agent will produce up to 3 prioritized, evidence-based recommendations for your review.
              </p>
            </div>
            <Link to={`/app/analytics?campaignId=${selectedCampaignId}`} className="inline-block mt-2">
              <Button size="lg" className="gap-2">
                <Sparkles className="h-4 w-4" /> Open Analytics & Content Tracking
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {recommendations.map((rec, index) => {
            const apprId = rec.approval_id || rec.id || `opt-${index}`
            const status = rec.status || 'pending'
            const isPending = status === 'pending'
            const isApproved = status === 'approved'
            const isRejected = status === 'rejected'
            const isModified = status === 'modified'

            return (
              <Card
                key={apprId}
                className={cn(
                  'overflow-hidden transition-all',
                  isApproved && 'border-emerald-200/60 bg-emerald-50/10',
                  isRejected && 'opacity-60 bg-page/30',
                )}
              >
                <CardHeader className="border-b border-border bg-page/50">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-xl ai-gradient-bg text-white flex items-center justify-center">
                        <TrendingUp className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge
                            variant={
                              rec.priority === 'HIGH'
                                ? 'danger'
                                : rec.priority === 'MEDIUM'
                                ? 'warning'
                                : 'default'
                            }
                          >
                            {rec.priority} PRIORITY
                          </Badge>
                          <Badge variant="outline">{rec.category}</Badge>
                          <Badge
                            variant={
                              isApproved ? 'success' : isRejected ? 'danger' : isModified ? 'ai' : 'warning'
                            }
                          >
                            {status.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-xs text-text-secondary mt-1">Requires human approval before execution</p>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-5 space-y-4">
                  <div>
                    <h3 className="text-base font-bold text-text">{rec.action}</h3>
                    <p className="mt-1 text-sm text-text-secondary leading-relaxed">{rec.reason}</p>
                  </div>

                  {rec.evidence?.length > 0 && (
                    <div className="rounded-lg bg-surface/80 border border-border p-3">
                      <p className="text-xs font-semibold text-text-secondary uppercase mb-1.5">
                        Supporting Evidence
                      </p>
                      <ul className="space-y-1 text-xs text-text-secondary">
                        {rec.evidence.map((ev, evIdx) => (
                          <li key={evIdx} className="flex items-start gap-1.5">
                            <span className="text-primary">•</span>
                            <span>{ev}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border">
                    {isPending ? (
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="primary"
                          disabled={actionLoading[apprId]}
                          onClick={() => handleAction(apprId, 'approved')}
                          className="gap-1"
                        >
                          <Check className="h-3.5 w-3.5" /> Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={actionLoading[apprId]}
                          onClick={() => {
                            setModifyingApprovalId(apprId)
                            setModifyNote('')
                            setModifyModalOpen(true)
                          }}
                          className="gap-1"
                        >
                          <Edit3 className="h-3.5 w-3.5" /> Modify
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={actionLoading[apprId]}
                          onClick={() => handleAction(apprId, 'rejected')}
                          className="text-danger hover:bg-danger-soft/20 gap-1"
                        >
                          <X className="h-3.5 w-3.5" /> Reject
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                        {isApproved && '✓ Approved in Approval Center'}
                        {isRejected && '✕ Rejected'}
                        {isModified && '✎ Modified'}
                      </span>
                    )}

                    <Link to="/app/approvals" className="text-xs text-primary hover:underline">
                      View in Approval Center →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Modify Modal */}
      <Modal
        open={modifyModalOpen}
        onClose={() => setModifyModalOpen(false)}
        title="Modify Recommendation"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setModifyModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!modifyNote.trim()}
              onClick={() => {
                if (modifyingApprovalId) {
                  handleAction(modifyingApprovalId, 'modified', modifyNote)
                  setModifyModalOpen(false)
                }
              }}
            >
              Submit Modification
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <p className="text-xs text-text-secondary">
            Note your adjusted instructions or budget cap. This will be updated on the approval item in Approval Center.
          </p>
          <Input
            placeholder="e.g. Approved with 10% budget adjustment."
            value={modifyNote}
            onChange={(e) => setModifyNote(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  )
}

