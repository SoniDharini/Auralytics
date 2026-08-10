import { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowUpRight, FileText } from 'lucide-react'
import { contracts } from '@/mock-data'
import { Badge, Card, CardContent, CardHeader, CardTitle, MetricCard, StatusChip } from '@/components/ui'
import { cn, formatINR } from '@/utils'
import type { Contract, MetricCard as MetricCardType } from '@/types'

const REFERENCE_DATE = new Date('2026-08-10')

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr)
  return Math.ceil((target.getTime() - REFERENCE_DATE.getTime()) / (1000 * 60 * 60 * 24))
}

function deriveMetrics(items: Contract[]): MetricCardType[] {
  const signed = items.filter((c) => c.status === 'signed').length
  const pending = items.filter((c) => c.status === 'pending_signature').length
  const expiringSoon = items.filter((c) => {
    if (c.status === 'expired') return false
    const days = daysUntil(c.endDate)
    return days >= 0 && days <= 30
  }).length
  const paymentsDue = items.filter((c) => {
    if (c.status === 'expired') return false
    const days = daysUntil(c.paymentDue)
    return days <= 14
  }).length

  return [
    {
      id: 'total',
      label: 'Total Contracts',
      value: String(items.length),
      context: `${formatINR(items.reduce((s, c) => s + c.value, 0), true)} total value`,
    },
    {
      id: 'signed',
      label: 'Signed',
      value: String(signed),
      context: `${Math.round((signed / items.length) * 100)}% of portfolio`,
      trend: { value: 'Active', positive: true },
    },
    {
      id: 'pending',
      label: 'Pending',
      value: String(pending),
      context: 'Awaiting signature',
    },
    {
      id: 'expiring',
      label: 'Expiring Soon',
      value: String(expiringSoon),
      context: 'Within 30 days',
      trend: expiringSoon > 0 ? { value: 'Review', positive: false } : undefined,
    },
    {
      id: 'payments',
      label: 'Payments Due',
      value: String(paymentsDue),
      context: 'Due within 14 days',
      trend: paymentsDue > 0 ? { value: 'Action needed', positive: false } : undefined,
    },
  ]
}

function riskVariant(risk: string): 'success' | 'warning' | 'danger' | 'default' {
  const r = risk.toLowerCase()
  if (r === 'low') return 'success'
  if (r === 'medium') return 'warning'
  if (r === 'high') return 'danger'
  return 'default'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function ContractsPage() {
  const navigate = useNavigate()
  const metrics = useMemo(() => deriveMetrics(contracts), [])

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

      <div className="grid sm:grid-cols-2 xl:grid-cols-5 gap-4">
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
        <CardContent className="overflow-x-auto">
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
              {contracts.map((contract) => (
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
                  <td className="py-3.5 pr-3">
                    <span
                      className={cn(
                        daysUntil(contract.paymentDue) < 0 && contract.status !== 'expired'
                          ? 'text-danger font-semibold'
                          : 'text-text-secondary',
                      )}
                    >
                      {formatDate(contract.paymentDue)}
                    </span>
                  </td>
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
        </CardContent>
      </Card>
    </div>
  )
}
