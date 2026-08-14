import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Loader2, Plus, TrendingUp } from 'lucide-react'
import { api } from '@/services/api'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricCard,
  ProgressBar,
} from '@/components/ui'
import { formatINR, formatNumber } from '@/utils'
import type { Campaign, MetricCard as MetricCardType } from '@/types'


export function AnalyticsPage() {
  const [campaignsList, setCampaignsList] = useState<Campaign[]>([])
  const [analyticsData, setAnalyticsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setLoading(true)

    Promise.all([
      api.campaigns.list().catch(() => []),
      api.analytics.get().catch(() => null),
    ])
      .then(([camps, analytics]) => {
        if (!mounted) return
        setCampaignsList(camps || [])
        setAnalyticsData(analytics)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const activeCampaigns = useMemo(
    () => campaignsList.filter((c) => c.status === 'active'),
    [campaignsList],
  )

  const totals = useMemo(() => {
    const spend = campaignsList.reduce((s, c) => s + (c.spend || 0), 0)
    const revenue = campaignsList.reduce((s, c) => s + (c.revenue || 0), 0)
    const conversions = campaignsList.reduce((s, c) => s + (c.conversions || 0), 0)
    const reach = campaignsList.reduce((s, c) => s + (c.reach || 0), 0)
    const budget = campaignsList.reduce((s, c) => s + (c.budget || 0), 0)
    return {
      spend,
      revenue,
      roas: spend > 0 ? revenue / spend : 0,
      cpa: conversions > 0 ? spend / conversions : 0,
      conversions,
      reach,
      budget,
      engagementRate: campaignsList.length > 0 ? 5.8 : 0,
    }
  }, [campaignsList])

  const kpis: MetricCardType[] = [
    {
      id: 'spend',
      label: 'Spend',
      value: formatINR(totals.spend, true),
      context: totals.budget > 0 ? `${Math.round((totals.spend / totals.budget) * 100)}% of budget` : 'No active budget',
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value: formatINR(totals.revenue, true),
      context: totals.revenue > 0 ? 'Direct & attributed' : '₹0 attributed revenue',
    },
    {
      id: 'roas',
      label: 'ROAS',
      value: `${totals.roas.toFixed(2)}x`,
      context: 'Across active campaigns',
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
      context: 'Tracked orders / leads',
    },
    {
      id: 'reach',
      label: 'Reach',
      value: formatNumber(totals.reach),
      context: 'Unique impressions',
    },
  ]

  const chartData = analyticsData?.revenueSpendData || []
  const budgetUtilization = totals.budget > 0 ? Math.round((totals.spend / totals.budget) * 100) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Analytics</h1>
          <p className="text-text-secondary mt-1">
            Campaign performance, creator efficiency, and ROI breakdowns.
          </p>
        </div>
        <Link to="/app/campaigns/new">
          <Button size="lg" className="gap-2">
            <Plus className="h-4 w-4" /> Create Campaign
          </Button>
        </Link>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {kpis.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>

      {loading && (
        <div className="py-16 flex justify-center items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span>Loading analytics...</span>
        </div>
      )}

      {!loading && campaignsList.length === 0 && (
        <Card>
          <CardContent className="py-16 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
              <TrendingUp className="h-7 w-7" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-text">No performance data yet</h3>
              <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
                Analytics and ROAS tracking will appear once your campaigns collect real-time data from influencer content.
              </p>
            </div>
            <Link to="/app/campaigns/new" className="inline-block mt-2">
              <Button size="lg" className="gap-2">
                <Plus className="h-4 w-4" /> Start Your First Campaign
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {!loading && campaignsList.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Revenue vs Spend</CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <p className="text-sm text-text-secondary py-12 text-center">No spend data points yet.</p>
              ) : (
                <div className="h-[240px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
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
                      <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
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
              )}
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
                    <span className="text-text-secondary shrink-0">{c.progress || 0}%</span>
                  </div>
                  <ProgressBar value={c.progress || 0} size="sm" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
