import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ArrowDown, ArrowUp, Sparkles } from 'lucide-react'
import {
  campaignFunnel,
  campaigns,
  conversionsOverTime,
  creatorPerformance,
  performanceInsights,
  platformPerformance,
  revenueSpendData,
  roasOverTime,
} from '@/mock-data'
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InsightCard,
  MetricCard,
  ProgressBar,
} from '@/components/ui'
import { cn, formatINR, formatNumber, formatPercent } from '@/utils'
import type { MetricCard as MetricCardType } from '@/types'

type SortKey = 'roas' | 'revenue' | 'conversions' | 'spend'
type SortDir = 'asc' | 'desc'

const performanceStyles = {
  excellent: { label: 'Excellent', badge: 'success' as const, bar: '#16a34a' },
  healthy: { label: 'Healthy', badge: 'primary' as const, bar: '#5B5FEF' },
  needs_attention: { label: 'Needs Attention', badge: 'danger' as const, bar: '#ef4444' },
}

export function AnalyticsPage() {
  const [sortKey, setSortKey] = useState<SortKey>('roas')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const activeCampaigns = useMemo(() => campaigns.filter((c) => c.status === 'active'), [])

  const totals = useMemo(() => {
    const spend = activeCampaigns.reduce((s, c) => s + c.spend, 0)
    const revenue = activeCampaigns.reduce((s, c) => s + c.revenue, 0)
    const conversions = activeCampaigns.reduce((s, c) => s + c.conversions, 0)
    const reach = activeCampaigns.reduce((s, c) => s + c.reach, 0)
    const budget = activeCampaigns.reduce((s, c) => s + c.budget, 0)
    return {
      spend,
      revenue,
      roas: spend > 0 ? revenue / spend : 0,
      cpa: conversions > 0 ? spend / conversions : 0,
      conversions,
      reach,
      budget,
      engagementRate: 5.8,
    }
  }, [activeCampaigns])

  const kpis: MetricCardType[] = [
    {
      id: 'spend',
      label: 'Spend',
      value: formatINR(totals.spend, true),
      context: `${Math.round((totals.spend / totals.budget) * 100)}% of budget`,
      sparkline: [45, 58, 72, 87, 95, 110, totals.spend / 1000],
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value: formatINR(totals.revenue, true),
      context: '+23.8% vs last period',
      trend: { value: '+23.8%', positive: true },
      sparkline: [89, 120, 180, 245, 312, 368, totals.revenue / 1000],
    },
    {
      id: 'roas',
      label: 'ROAS',
      value: `${totals.roas.toFixed(2)}x`,
      context: 'Across active campaigns',
      trend: { value: '+0.31x', positive: true },
      sparkline: [1.8, 2.0, 2.2, 2.4, 2.6, 2.7, totals.roas],
    },
    {
      id: 'cpa',
      label: 'CPA',
      value: formatINR(Math.round(totals.cpa)),
      context: 'Cost per acquisition',
    },
    {
      id: 'conversions',
      label: 'Conversions',
      value: formatNumber(totals.conversions),
      context: 'Last 30 days',
      trend: { value: '+18%', positive: true },
    },
    {
      id: 'reach',
      label: 'Reach',
      value: formatNumber(totals.reach),
      context: 'Unique impressions',
    },
    {
      id: 'engagement',
      label: 'Engagement Rate',
      value: formatPercent(totals.engagementRate, 1),
      context: 'Campaign average',
      trend: { value: '+0.4%', positive: true },
    },
  ]

  const sortedCreators = useMemo(() => {
    return [...creatorPerformance].sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      return sortDir === 'desc' ? bv - av : av - bv
    })
  }, [sortKey, sortDir])

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <button
      onClick={() => toggleSort(field)}
      className="inline-flex items-center gap-1 font-semibold hover:text-primary transition"
    >
      {label}
      {sortKey === field &&
        (sortDir === 'desc' ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
    </button>
  )

  const budgetUtilization = Math.round((totals.spend / totals.budget) * 100)
  const funnelMax = Math.max(...campaignFunnel.map((s) => s.value))

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-[32px] font-bold tracking-tight">Analytics</h1>
        <p className="text-text-secondary mt-1">
          Campaign performance, creator efficiency, and platform breakdowns.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {kpis.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Revenue vs Spend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={revenueSpendData}>
                  <defs>
                    <linearGradient id="analytics-rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5B5FEF" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#5B5FEF" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="analytics-spend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v / 1000}k`}
                  />
                  <Tooltip formatter={(value) => formatINR(Number(value))} />
                  <Area type="monotone" dataKey="revenue" stroke="#5B5FEF" fill="url(#analytics-rev)" strokeWidth={2} />
                  <Area type="monotone" dataKey="spend" stroke="#8B5CF6" fill="url(#analytics-spend)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>ROAS over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={roasOverTime}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `${v}x`}
                    domain={[0, 'auto']}
                  />
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}x`, 'ROAS']} />
                  <Line type="monotone" dataKey="roas" stroke="#5B5FEF" strokeWidth={2.5} dot={{ fill: '#5B5FEF', r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conversions over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={conversionsOverTime}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Bar dataKey="conversions" fill="#5B5FEF" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Creator Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={creatorPerformance} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}x`} />
                  <YAxis type="category" dataKey="influencer" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} width={90} />
                  <Tooltip formatter={(value) => [`${Number(value).toFixed(2)}x`, 'ROAS']} />
                  <Bar dataKey="roas" radius={[0, 6, 6, 0]}>
                    {creatorPerformance.map((entry) => (
                      <Cell key={entry.influencer} fill={performanceStyles[entry.performance].bar} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Platform Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={platformPerformance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                  <XAxis dataKey="platform" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v / 1000}k`} />
                  <Tooltip formatter={(value, name) => [name === 'roas' ? `${Number(value).toFixed(2)}x` : formatINR(Number(value)), name === 'roas' ? 'ROAS' : name === 'revenue' ? 'Revenue' : 'Spend']} />
                  <Bar dataKey="revenue" fill="#5B5FEF" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="spend" fill="#8B5CF6" radius={[6, 6, 0, 0]} opacity={0.7} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Budget Utilization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-3xl font-bold text-primary">{budgetUtilization}%</p>
                <p className="text-sm text-text-secondary mt-1">
                  {formatINR(totals.spend, true)} of {formatINR(totals.budget, true)} allocated
                </p>
              </div>
            </div>
            <ProgressBar value={budgetUtilization} showLabel barClassName="bg-gradient-to-r from-primary to-accent" />
            {activeCampaigns.slice(0, 4).map((c) => (
              <div key={c.id} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="font-medium truncate pr-2">{c.name}</span>
                  <span className="text-text-secondary shrink-0">{c.progress}%</span>
                </div>
                <ProgressBar value={c.progress} size="sm" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Campaign Funnel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {campaignFunnel.map((stage, i) => {
                const pct = (stage.value / funnelMax) * 100
                const dropoff =
                  i > 0 ? Math.round(((campaignFunnel[i - 1].value - stage.value) / campaignFunnel[i - 1].value) * 100) : null
                return (
                  <div key={stage.label} className="flex items-center gap-4">
                    <span className="text-xs font-semibold text-text-secondary w-24 shrink-0">{stage.label}</span>
                    <div className="flex-1 h-8 rounded-lg bg-muted overflow-hidden relative">
                      <div
                        className="h-full rounded-lg bg-primary/80 flex items-center px-3 transition-all duration-700"
                        style={{ width: `${Math.max(pct, 8)}%` }}
                      >
                        <span className="text-xs font-bold text-white">{stage.value}</span>
                      </div>
                    </div>
                    {dropoff !== null && (
                      <span className="text-[10px] text-text-secondary w-12 text-right">-{dropoff}%</span>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid xl:grid-cols-[1.5fr_1fr] gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Creator Performance Table</CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">Click column headers to sort</p>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-secondary border-b border-border">
                  <th className="pb-3 font-semibold">Creator</th>
                  <th className="pb-3 font-semibold">Performance</th>
                  <th className="pb-3"><SortHeader label="Spend" field="spend" /></th>
                  <th className="pb-3"><SortHeader label="Revenue" field="revenue" /></th>
                  <th className="pb-3"><SortHeader label="ROAS" field="roas" /></th>
                  <th className="pb-3"><SortHeader label="Conversions" field="conversions" /></th>
                  <th className="pb-3 font-semibold">Reach</th>
                  <th className="pb-3 font-semibold">CPA</th>
                </tr>
              </thead>
              <tbody>
                {sortedCreators.map((row) => {
                  const style = performanceStyles[row.performance]
                  return (
                    <tr key={row.influencer} className="border-b border-border last:border-0 hover:bg-page/80">
                      <td className="py-3.5 pr-3 font-semibold">@{row.influencer}</td>
                      <td className="py-3.5 pr-3">
                        <Badge variant={style.badge}>{style.label}</Badge>
                      </td>
                      <td className="py-3.5 pr-3">{formatINR(row.spend, true)}</td>
                      <td className="py-3.5 pr-3">{formatINR(row.revenue, true)}</td>
                      <td className={cn('py-3.5 pr-3 font-semibold', row.roas >= 3 ? 'text-success' : row.roas < 1.5 ? 'text-danger' : 'text-primary')}>
                        {row.roas}x
                      </td>
                      <td className="py-3.5 pr-3">{row.conversions}</td>
                      <td className="py-3.5 pr-3 text-text-secondary">{formatNumber(row.reach)}</td>
                      <td className="py-3.5 pr-3 text-text-secondary">{formatINR(row.cpa)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <div className="flex items-center gap-2 px-1">
            <Sparkles className="h-4 w-4 text-ai" />
            <h2 className="text-base font-semibold">Performance Agent Insights</h2>
          </div>
          {performanceInsights.map((insight) => (
            <InsightCard
              key={insight.id}
              insight={insight}
              primaryLabel={insight.action}
              secondaryLabel="Dismiss"
              onPrimary={() => {}}
              onSecondary={() => {}}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
