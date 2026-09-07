import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, CheckCircle2, FileText, Loader2 } from 'lucide-react'
import { api } from '@/services/api'
import { PageAmbientBackground, PageHeader } from '@/components/brand/VisualSystem'
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, MetricCard, StatusChip } from '@/components/ui'
import { CampaignContextHeader } from '@/components/campaigns/CampaignContextHeader'
import { formatINR } from '@/utils'
import type { Campaign, CampaignWorkflow, Contract, MetricCard as MetricCardType } from '@/types'

function deriveMetrics(items: Contract[]): MetricCardType[] {
  const approved = items.filter((c) => c.status === 'APPROVED' || c.status === 'signed').length
  const changes = items.filter((c) => c.status === 'CHANGES_REQUESTED').length
  const pending = items.filter((c) => c.status === 'pending_signature' || c.status === 'READY_FOR_REVIEW').length

  return [
    {
      id: 'total',
      label: 'Total Contracts',
      value: String(items.length),
      context: `${formatINR(items.reduce((s, c) => s + (c.value || 0), 0), true)} total committed`,
    },
    {
      id: 'approved',
      label: 'Approved Agreements',
      value: String(approved),
      context: items.length > 0 ? `${Math.round((approved / items.length) * 100)}% of pipeline` : '0 approved',
      trend: approved > 0 ? { value: 'Verified', positive: true } : undefined,
    },
    {
      id: 'pending',
      label: 'Pending Human Review',
      value: String(pending),
      context: changes > 0 ? `${changes} changes requested` : 'Awaiting sign-off',
    },
  ]
}

function riskVariant(risk?: string): 'success' | 'warning' | 'danger' | 'default' {
  const r = risk ? risk.toLowerCase() : 'low'
  if (r === 'low') return 'success'
  if (r === 'medium') return 'warning'
  if (r === 'high') return 'danger'
  return 'default'
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function ContractsPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const campaignId = searchParams.get('campaignId') || undefined

  const [contractsList, setContractsList] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [workflow, setWorkflow] = useState<CampaignWorkflow | null>(null)

  useEffect(() => {
    if (!campaignId) {
      setCampaign(null)
      setWorkflow(null)
      return
    }
    let mounted = true
    Promise.all([
      api.campaigns.get(campaignId).catch(() => null),
      api.campaigns.getWorkflow(campaignId).catch(() => null),
    ]).then(([camp, wf]) => {
      if (mounted) {
        if (camp) setCampaign(camp)
        if (wf) setWorkflow(wf)
      }
    })
    return () => {
      mounted = false
    }
  }, [campaignId])

  useEffect(() => {
    let mounted = true
    api.contracts
      .list(statusFilter, campaignId)
      .then((data) => {
        if (mounted && data) {
          setContractsList(data)
        }
      })
      .catch(() => {
        setContractsList([])
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [statusFilter, campaignId])

  const metrics = useMemo(() => deriveMetrics(contractsList), [contractsList])

  const filterTabs = [
    { id: 'all', label: 'All Contracts' },
    { id: 'APPROVED', label: 'Approved' },
    { id: 'pending_signature', label: 'Pending Review' },
    { id: 'CHANGES_REQUESTED', label: 'Changes Requested' },
    { id: 'REJECTED', label: 'Rejected' },
  ]

  const hasApprovedContract = useMemo(
    () => contractsList.some((c) => c.status === 'APPROVED' || c.status === 'signed'),
    [contractsList]
  )

  return (
    <div className="relative space-y-5 animate-fade-in">
      <PageAmbientBackground variant="contract" className="h-[340px]" />

      {campaign && (
        <CampaignContextHeader
          campaign={campaign}
          workflow={workflow}
          currentStageName="Contracts"
          currentTab="contracts"
        />
      )}

      {campaignId && hasApprovedContract && (
        <div className="rounded-xl border border-success/30 bg-success/5 p-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="h-5 w-5 text-success shrink-0" />
            <div>
              <h4 className="text-sm font-semibold text-text">Contract Stage Completed</h4>
              <p className="text-xs text-text-secondary">
                Influencer agreement has been approved. Proceed to campaign tracking and performance analysis.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="primary"
            className="text-xs gap-1.5 shrink-0"
            onClick={() => navigate(`/app/campaigns/${campaignId}?tab=performance`)}
          >
            Continue to Performance <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      <PageHeader
        eyebrow={campaign ? campaign.name : 'Contracts'}
        title="Contracts & Legal Verification"
        description={
          campaign
            ? `Reviewing creator agreements and verified terms for ${campaign.name}.`
            : 'Review AI agreement analyses, verify commercial term matches, and sign off creator contracts.'
        }
        actions={
          <div className="flex items-center gap-2 text-xs text-text-secondary bg-surface px-3 py-1.5 rounded-xl border border-border">
            <FileText className="h-4 w-4 text-primary" />
            <span>Document workspace</span>
          </div>
        }
      />

      <div className="relative grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="relative flex items-center gap-2 overflow-x-auto pb-1">
        {filterTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setStatusFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all border ${
              statusFilter === tab.id
                ? 'bg-primary-soft border-primary/30 text-primary font-semibold'
                : 'bg-surface border-border text-text-secondary hover:bg-muted hover:text-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <Card className="relative">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Creator Collaboration Agreements</CardTitle>
              <p className="text-xs text-text-secondary mt-0.5">
                Click any agreement row to open the full analysis, clause comparison, and sign-off tools
              </p>
            </div>
            <span className="text-xs text-text-secondary font-mono">
              {contractsList.length} agreement{contractsList.length === 1 ? '' : 's'}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>Loading contract portfolio...</span>
            </div>
          )}

          {!loading && contractsList.length === 0 && (
            <div className="text-center py-12 text-text-secondary">
              <FileText className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
              <p className="font-semibold text-text">No contracts found</p>
              <p className="text-xs mt-1">
                Contracts are synthesized automatically when creator outreach negotiations reach ACCEPTED state.
              </p>
            </div>
          )}

          {!loading && contractsList.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-[11px] text-text-secondary border-b border-border">
                    <th className="pb-3 font-semibold">Creator</th>
                    <th className="pb-3 font-semibold">Campaign</th>
                    <th className="pb-3 font-semibold">Agreed Fee</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Flight Window</th>
                    <th className="pb-3 font-semibold">Payment Terms</th>
                    <th className="pb-3 font-semibold">AI Risk</th>
                    <th className="pb-3 font-semibold w-10" />
                  </tr>
                </thead>
                <tbody>
                  {contractsList.map((contract) => (
                    <tr
                      key={contract.id}
                      onClick={() =>
                        navigate(
                          `/app/contracts/${contract.id}${campaignId ? `?campaignId=${campaignId}` : ''}`
                        )
                      }
                      className="border-b border-border last:border-0 hover:bg-page/80 cursor-pointer transition-colors"
                    >
                      <td className="py-3.5 pr-3">
                        <div className="flex items-center gap-2">
                          <div>
                            <p className="font-semibold text-text text-xs">{contract.creator}</p>
                            <p className="text-[11px] text-text-secondary">@{contract.username}</p>
                          </div>
                          {contract.version && contract.version > 1 && (
                            <Badge variant="neutral" className="text-[10px] font-mono px-1.5 py-0">
                              v{contract.version}
                            </Badge>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 pr-3 max-w-[180px]">
                        <span className="line-clamp-2 font-medium text-text">{contract.campaign}</span>
                      </td>
                      <td className="py-3.5 pr-3 font-semibold text-text">
                        {formatINR(contract.value)}
                      </td>
                      <td className="py-3.5 pr-3">
                        <StatusChip status={contract.status} />
                      </td>
                      <td className="py-3.5 pr-3 text-text-secondary">
                        {formatDate(contract.startDate || contract.start_date)} – {formatDate(contract.endDate || contract.end_date)}
                      </td>
                      <td className="py-3.5 pr-3 text-text-secondary">
                        {contract.paymentDue || contract.payment_due || 'Net 30'}
                      </td>
                      <td className="py-3.5 pr-3">
                        <Badge variant={riskVariant(contract.risk)} className="text-[10px]">
                          {contract.risk.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3.5 text-right">
                        <Link
                          to={`/app/contracts/${contract.id}${campaignId ? `?campaignId=${campaignId}` : ''}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-primary-soft text-primary hover:bg-primary hover:text-white transition shadow-xs"
                          aria-label={`View ${contract.creator} contract`}
                        >
                          <span>Review & PDF</span>
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

