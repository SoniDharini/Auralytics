import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowUpRight, FileText, Loader2 } from 'lucide-react'
import { api } from '@/services/api'
import { Badge, Card, CardContent, CardHeader, CardTitle, MetricCard, StatusChip } from '@/components/ui'
import { formatINR } from '@/utils'
import type { Contract, MetricCard as MetricCardType } from '@/types'

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
  const [contractsList, setContractsList] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    let mounted = true
    api.contracts
      .list(statusFilter)
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
  }, [statusFilter])

  const metrics = useMemo(() => deriveMetrics(contractsList), [contractsList])

  const filterTabs = [
    { id: 'all', label: 'All Contracts' },
    { id: 'APPROVED', label: 'Approved' },
    { id: 'pending_signature', label: 'Pending Review' },
    { id: 'CHANGES_REQUESTED', label: 'Changes Requested' },
    { id: 'REJECTED', label: 'Rejected' },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Contracts & Legal Verification</h1>
          <p className="text-text-secondary mt-1">
            Review AI agreement analyses, verify commercial term matches, and sign off creator contracts.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-secondary bg-white px-3 py-1.5 rounded-xl border border-border">
          <FileText className="h-4 w-4 text-primary" />
          <span>Supervised by Contract Agent</span>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {filterTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setStatusFilter(tab.id)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all ${
              statusFilter === tab.id
                ? 'bg-primary text-white shadow-sm'
                : 'bg-white text-text-secondary border border-border hover:bg-page hover:text-text'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <Card>
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
                      onClick={() => navigate(`/app/contracts/${contract.id}`)}
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
                          to={`/app/contracts/${contract.id}`}
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

