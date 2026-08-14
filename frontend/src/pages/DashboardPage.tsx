import { useEffect, useState } from 'react'
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
import {
  Activity,
  ArrowRight,
  Clock,
  FolderPlus,
  Plus,
  Sparkles,
  Zap,
} from 'lucide-react'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricCard,
} from '@/components/ui'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/services/api'
import { formatINR, getGreeting, cn } from '@/utils'
import type { CampaignActivity, DashboardSummary, MetricCard as MetricCardType } from '@/types'

const ranges = ['7 Days', '30 Days', '90 Days', 'Custom']

export function DashboardPage() {
  const { user } = useAuth()
  const [range, setRange] = useState('30 Days')
  const [summary, setSummary] = useState<DashboardSummary>({
    total_campaigns: 0,
    active_campaigns: 0,
    pending_campaigns: 0,
    completed_campaigns: 0,
    total_spend: 0,
    total_revenue: 0,
    average_roas: 0,
    pending_approvals: 0,
  })
  const [activities, setActivities] = useState<CampaignActivity[]>([])
  const [chartData, setChartData] = useState<{ month: string; spend: number; revenue: number }[]>([])

  const displayName = user?.full_name ? user.full_name.split(' ')[0] : 'there'

  useEffect(() => {
    let mounted = true

    Promise.all([
      api.dashboard.getSummary().catch(() => null),
      api.activities.list().catch(() => []),
      api.analytics.get().catch(() => null),
    ])
      .then(([summaryData, activitiesData, analyticsData]) => {
        if (!mounted) return
        if (summaryData) {
          setSummary(summaryData)
        }
        if (activitiesData) {
          setActivities(activitiesData)
        }
        if (analyticsData?.revenueSpendData && analyticsData.revenueSpendData.length > 0) {
          setChartData(analyticsData.revenueSpendData)
        } else {
          setChartData([])
        }
      })

    return () => {
      mounted = false
    }
  }, [])


  const metricCards: MetricCardType[] = [
    {
      id: 'active',
      label: 'Active Campaigns',
      value: String(summary.active_campaigns),
      context: `${summary.total_campaigns} total campaigns`,
      trend: summary.active_campaigns > 0 ? { value: `+${summary.active_campaigns}`, positive: true } : undefined,
    },
    {
      id: 'total_campaigns',
      label: 'Total Campaigns',
      value: String(summary.total_campaigns),
      context: `${summary.completed_campaigns} completed`,
    },
    {
      id: 'spend',
      label: 'Total Spend',
      value: summary.total_spend >= 100000 ? `₹${(summary.total_spend / 100000).toFixed(1)}L` : formatINR(summary.total_spend),
      context: 'Allocated campaign budget',
      trend: summary.total_spend > 0 ? { value: 'Active spend', positive: true } : undefined,
    },
    {
      id: 'revenue',
      label: 'Revenue Generated',
      value: summary.total_revenue >= 100000 ? `₹${(summary.total_revenue / 100000).toFixed(1)}L` : formatINR(summary.total_revenue),
      context: 'Direct & attributed',
      trend: summary.total_revenue > 0 ? { value: '+100%', positive: true } : undefined,
    },
    {
      id: 'roas',
      label: 'Average ROAS',
      value: `${summary.average_roas.toFixed(2)}x`,
      context: 'Target: 2.50x',
      trend: summary.average_roas > 0 ? { value: `${summary.average_roas.toFixed(2)}x`, positive: summary.average_roas >= 2.0 } : undefined,
    },
    {
      id: 'approvals',
      label: 'Pending Approvals',
      value: String(summary.pending_approvals),
      context: summary.pending_approvals > 0 ? 'Action required' : 'All caught up',
      trend: summary.pending_approvals > 0 ? { value: 'Needs review', positive: false } : undefined,
    },
  ]

  const formatActivityTime = (isoString: string) => {
    try {
      const date = new Date(isoString)
      const now = new Date()
      const diffMs = now.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      if (diffMins < 1) return 'Just now'
      if (diffMins < 60) return `${diffMins}m ago`
      const diffHours = Math.floor(diffMins / 60)
      if (diffHours < 24) return `${diffHours}h ago`
      return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    } catch {
      return 'Recently'
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">
            {getGreeting()}, {displayName}
          </h1>
          <p className="text-text-secondary mt-1">
            {summary.total_campaigns > 0
              ? `Managing ${summary.total_campaigns} campaign${summary.total_campaigns !== 1 ? 's' : ''} on InfluenceOS.`
              : 'Welcome to InfluenceOS. Create your first campaign to get started.'}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link to="/app/campaigns/new">
            <Button size="lg" className="gap-2">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 sm:gap-4">
        {metricCards.map((card) => (
          <MetricCard key={card.id} metric={card} />
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Revenue vs Influencer Spend</CardTitle>
              <p className="text-xs text-text-secondary mt-1">
                Attributed revenue generated across your campaigns
              </p>
            </div>
            <div className="flex gap-1 bg-page p-1 rounded-[10px] border border-border">
              {ranges.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={cn(
                    'px-2.5 py-1 text-xs rounded-md transition font-medium',
                    range === r ? 'bg-white shadow-xs text-text font-semibold' : 'text-text-secondary hover:text-text',
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="h-72 w-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-border rounded-xl bg-page/40">
                <Activity className="h-10 w-10 text-text-secondary/40 mb-3" />
                <p className="text-sm font-semibold text-text">No performance data yet</p>
                <p className="text-xs text-text-secondary mt-1 max-w-sm">
                  Revenue and spend tracking will activate once your campaigns begin live tracking.
                </p>
                <Link to="/app/campaigns/new" className="mt-4">
                  <Button size="sm" variant="soft" className="gap-1.5">
                    <Plus className="h-3.5 w-3.5" /> Start First Campaign
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis
                      stroke="#94a3b8"
                      fontSize={11}
                      tickLine={false}
                      tickFormatter={(v) => `₹${v / 100000}L`}
                    />
                    <Tooltip
                      formatter={(v: any) => formatINR(Number(v))}
                      contentStyle={{
                        backgroundColor: '#ffffff',
                        borderColor: '#e2e8f0',
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="spend"
                      name="Spend"
                      stroke="#4F46E5"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#spendGrad)"
                    />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      name="Revenue"
                      stroke="#10B981"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#revGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Campaign Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {summary.total_campaigns === 0 ? (
              <div className="text-center py-10">
                <div className="h-12 w-12 rounded-full bg-primary-soft text-primary flex items-center justify-center mx-auto mb-3">
                  <FolderPlus className="h-6 w-6" />
                </div>
                <p className="text-sm font-semibold text-text">No campaigns active</p>
                <p className="text-xs text-text-secondary mt-1">
                  Campaign health metrics will appear as you launch campaigns.
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-secondary">Active Campaigns</span>
                    <span className="text-sm font-bold text-success">{summary.active_campaigns}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-secondary">Pending / Planning</span>
                    <span className="text-sm font-bold text-primary">{summary.pending_campaigns}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-text-secondary">Completed</span>
                    <span className="text-sm font-bold text-text">{summary.completed_campaigns}</span>
                  </div>
                </div>
                <div className="pt-3 border-t border-border">
                  <Link to="/app/campaigns" className="text-xs font-semibold text-primary hover:underline flex items-center gap-1">
                    Manage all campaigns <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Activity</CardTitle>
              <p className="text-xs text-text-secondary mt-0.5">Real events from your campaigns and workflows</p>
            </div>
            {activities.length > 0 && (
              <Link to="/app/campaigns" className="text-xs font-semibold text-primary hover:underline">
                View campaigns →
              </Link>
            )}
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <div className="text-center py-10 text-text-secondary">
                <Clock className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
                <p className="font-semibold text-text">No recent activity</p>
                <p className="text-xs mt-1">Your campaign activity will appear here as you create and manage campaigns.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {activities.slice(0, 6).map((act) => (
                  <div
                    key={act.id}
                    className="flex items-start gap-3 p-3 rounded-xl border border-border bg-page/40 hover:bg-page transition"
                  >
                    <div className="h-8 w-8 rounded-lg bg-primary-soft text-primary flex items-center justify-center shrink-0 mt-0.5">
                      <Zap className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-text truncate">{act.title}</p>
                        <span className="text-[11px] text-text-secondary shrink-0 font-mono">
                          {formatActivityTime(act.created_at)}
                        </span>
                      </div>
                      {act.description && (
                        <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{act.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-ai" />
              <CardTitle>AI Strategic Insights</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {summary.total_campaigns === 0 ? (
              <div className="text-center py-8 text-text-secondary">
                <Sparkles className="h-8 w-8 mx-auto text-ai/40 mb-2" />
                <p className="text-sm font-semibold text-text">No strategic insights yet</p>
                <p className="text-xs mt-1">AI agent insights will generate as your campaigns collect live metrics.</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 rounded-xl border border-border bg-violet-50/50">
                  <p className="text-xs font-semibold text-ai mb-1">Active Optimization</p>
                  <p className="text-xs text-text leading-relaxed">
                    Strategy Agent is monitoring your active campaign budget allocation for maximum ROAS.
                  </p>
                </div>
                <div className="p-3 rounded-xl border border-border bg-green-50/50">
                  <p className="text-xs font-semibold text-success mb-1">Workflow Ready</p>
                  <p className="text-xs text-text leading-relaxed">
                    Discovery and Outreach Agents are standing by to process new campaign briefs.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
