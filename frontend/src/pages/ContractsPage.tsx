import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowUpRight, FileText, Loader2 } from 'lucide-react'
import { api } from '@/services/api'
import { Badge, Card, CardContent, CardHeader, CardTitle, MetricCard, StatusChip } from '@/components/ui'
import { formatINR } from '@/utils'
import type { Contract, MetricCard as MetricCardType } from '@/types'


function deriveMetrics(items: Contract[]): MetricCardType[] {
  const signed = items.filter((c) => c.status === 'signed').length
  const pending = items.filter((c) => c.status === 'pending_signature').length

  return [
    {
      id: 'total',
      label: 'Total Contracts',
      value: String(items.length),
      context: `${formatINR(items.reduce((s, c) => s + (c.value || 0), 0), true)} total value`,
    },
    {
      id: 'signed',
      label: 'Signed',
      value: String(signed),
      context: items.length > 0 ? `${Math.round((signed / items.length) * 100)}% of portfolio` : '0 signed',
      trend: signed > 0 ? { value: 'Active', positive: true } : undefined,
    },
    {
      id: 'pending',
      label: 'Pending',
      value: String(pending),
      context: 'Awaiting signature',
    },
  ]
}

function riskVariant(risk: string): 'success' | 'warning' | 'danger' | 'default' {
  const r = risk ? risk.toLowerCase() : 'low'
  if (r === 'low') return 'success'
  if (r === 'medium') return 'warning'
  if (r === 'high') return 'danger'
  return 'default'
}

function formatDate(dateStr: string): string {
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

  useEffect(() => {
    let mounted = true
    api.contracts
      .list()
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
  }, [])

  const metrics = useMemo(() => deriveMetrics(contractsList), [contractsList])

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Contracts</h1>
          <p className="text-text-secondary mt-1">
            Track creator agreements, obligations, and payment timelines.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <FileText className="h-4 w-4 text-primary" />
          Monitored by Contract Agent
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>All Contracts</CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">
              Click a row to view contract details and AI risk analysis
            </p>
          </div>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <span>Loading contracts...</span>
            </div>
          )}

          {!loading && contractsList.length === 0 && (
            <div className="text-center py-12 text-text-secondary">
              <FileText className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
              <p className="font-semibold text-text">No contracts yet</p>
              <p className="text-sm mt-1">Creator agreements will appear here as deals are finalized.</p>
            </div>
          )}

          {!loading && contractsList.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-text-secondary border-b border-border">
                    <th className="pb-3 font-semibold">Creator</th>
                    <th className="pb-3 font-semibold">Campaign</th>
                    <th className="pb-3 font-semibold">Contract Value</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold">Start</th>
                    <th className="pb-3 font-semibold">End</th>
                    <th className="pb-3 font-semibold">Payment Due</th>
                    <th className="pb-3 font-semibold">Risk</th>
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
                        <p className="font-semibold">{contract.creator}</p>
                        <p className="text-xs text-text-secondary">@{contract.username}</p>
                      </td>
                      <td className="py-3.5 pr-3 max-w-[180px]">
                        <span className="line-clamp-2">{contract.campaign}</span>
                      </td>
                      <td className="py-3.5 pr-3 font-semibold">{formatINR(contract.value)}</td>
                      <td className="py-3.5 pr-3">
                        <StatusChip status={contract.status} />
                      </td>
                      <td className="py-3.5 pr-3 text-text-secondary">{formatDate(contract.startDate)}</td>
                      <td className="py-3.5 pr-3 text-text-secondary">{formatDate(contract.endDate)}</td>
                      <td className="py-3.5 pr-3 text-text-secondary">{formatDate(contract.paymentDue)}</td>
                      <td className="py-3.5 pr-3">
                        <Badge variant={riskVariant(contract.risk)}>{contract.risk}</Badge>
                      </td>
                      <td className="py-3.5">
                        <Link
                          to={`/app/contracts/${contract.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary hover:bg-primary-soft hover:text-primary transition"
                          aria-label={`View ${contract.creator} contract`}
                        >
                          <ArrowUpRight className="h-4 w-4" />
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
