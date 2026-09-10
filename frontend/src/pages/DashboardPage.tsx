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
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Calendar,
  Clock,
  FolderPlus,
  Layers,
  LineChart,
  Plus,
  Sparkles,
  Wallet,
  Zap,
} from 'lucide-react'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ProgressBar,
  StatusChip,
} from '@/components/ui'
import { PageAmbientBackground } from '@/components/brand/VisualSystem'
import { OverviewHeroMomentum } from '@/components/brand/PremiumVisuals'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { api } from '@/services/api'
import { formatINR, getGreeting, cn } from '@/utils'
import type { Campaign, CampaignActivity, DashboardSummary } from '@/types'

function formatActivityTime(isoString: string) {
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

function formatDateRange(start?: string, end?: string) {
  const fmt = (value?: string) => {
    if (!value) return null
    const d = new Date(value)
    if (Number.isNaN(d.getTime())) return null
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
  }
  const a = fmt(start)
  const b = fmt(end)
  if (a && b) return `${a} – ${b}`
  return a || b || '—'
}

export function DashboardPage() {
  const { user } = useAuth()
  const { theme } = useTheme()
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
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [chartData, setChartData] = useState<{ month: string; spend: number; revenue: number }[]>([])
  const [loading, setLoading] = useState(true)

  const displayName = user?.full_name ? user.full_name.split(' ')[0] : 'there'

  useEffect(() => {
    let mounted = true
    setLoading(true)

    Promise.all([
      api.dashboard.getSummary().catch(() => null),
      api.activities.list().catch(() => []),
      api.analytics.get().catch(() => null),
      api.campaigns.list().catch(() => []),
    ])
      .then(([summaryData, activitiesData, analyticsData, campaignsData]) => {
        if (!mounted) return
        if (summaryData) setSummary(summaryData)
        setActivities(activitiesData || [])
        setCampaigns(campaignsData || [])
        if (analyticsData?.revenueSpendData && analyticsData.revenueSpendData.length > 0) {
          setChartData(analyticsData.revenueSpendData)
        } else {
          setChartData([])
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  const recentCampaigns = useMemo(() => campaigns.slice(0, 3), [campaigns])

  const summaryCards = [
    {
      id: 'campaigns',
      label: 'Campaigns',
      value: String(summary.total_campaigns),
      context: `${summary.active_campaigns} active · ${summary.pending_campaigns} pending`,
      icon: Layers,
      iconClass: 'bg-primary-soft text-primary',
      href: '/app/campaigns',
    },
    {
      id: 'spend',
      label: 'Spend',
      value:
        summary.total_spend >= 100000
          ? `₹${(summary.total_spend / 100000).toFixed(1)}L`
          : formatINR(summary.total_spend),
      context: 'From campaign records',
      icon: Wallet,
      iconClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400',
      href: '/app/analytics',
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value:
        summary.total_revenue >= 100000
          ? `₹${(summary.total_revenue / 100000).toFixed(1)}L`
          : formatINR(summary.total_revenue),
      context: `${summary.completed_campaigns} completed`,
      icon: BarChart3,
      iconClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
      href: '/app/analytics',
    },
    {
      id: 'roas',
      label: 'Avg ROAS',
      value: `${summary.average_roas.toFixed(2)}x`,
      context:
        summary.pending_approvals > 0
          ? `${summary.pending_approvals} pending approvals`
          : 'Stored campaign ROAS',
      icon: LineChart,
      iconClass: 'bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400',
      href: '/app/analytics',
    },
  ]

  const chartStroke = theme === 'dark' ? '#818cf8' : '#5b5fef'
  const chartStrokeAlt = theme === 'dark' ? '#34d399' : '#10b981'

  return (
    <div className="relative space-y-5 animate-fade-in">
      <PageAmbientBackground variant="overview" className="h-[520px]" />

      <section className="relative overflow-hidden rounded-[22px] border border-primary/18 dark:border-white/10 shadow-[0_14px_40px_rgba(91,95,239,0.1)] dark:shadow-[0_14px_40px_rgba(0,0,0,0.4)]">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,#fcfbff_0%,#f6f3ff_46%,#eef2ff_100%)] dark:bg-[linear-gradient(135deg,#12162a_0%,#18162e_48%,#14182a_100%)]" />
        <div className="absolute right-[-8%] top-[-30%] h-56 w-56 rounded-full bg-primary/16 dark:bg-primary/22 blur-3xl pointer-events-none hero-glow-shift" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent dark:via-white/15 pointer-events-none" />
        <div
          className="absolute inset-0 opacity-[0.07] dark:opacity-[0.08] pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, color-mix(in srgb, var(--auralytics-primary) 55%, transparent) 1px, transparent 0)',
            backgroundSize: '22px 22px',
          }}
        />
        <svg
          viewBox="0 0 960 220"
          className="absolute inset-0 h-full w-full pointer-events-none text-primary opacity-[0.07] dark:opacity-[0.12]"
          preserveAspectRatio="none"
          aria-hidden
        >
          <path d="M40 190 C 220 40, 380 210, 560 80 S 820 40, 940 150" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <path d="M80 40 C 260 160, 420 20, 640 130 S 860 180, 960 70" fill="none" stroke="currentColor" strokeWidth="0.8" />
        </svg>
        <div className="absolute -right-10 -bottom-12 h-32 w-40 rotate-[18deg] rounded-[28px] border border-primary/12 bg-primary/[0.04] dark:bg-primary/[0.07] pointer-events-none" />

        <div className="relative px-5 py-5 sm:px-7 sm:py-6 lg:px-8 flex flex-col lg:flex-row lg:items-center gap-5 lg:gap-8">
          <div className="min-w-0 flex-[1.7] max-w-xl">
            <p className="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-white/70 dark:bg-white/10 px-2.5 py-[5px] text-[10px] font-semibold uppercase tracking-[0.18em] text-primary backdrop-blur-sm shadow-[0_0_18px_rgba(91,95,239,0.12)]">
              Welcome back <Sparkles className="h-3 w-3" />
            </p>
            <h1 className="mt-3 text-[26px] sm:text-[32px] font-bold tracking-tight text-text leading-[1.18]">
              {getGreeting()}, <span className="text-primary">{displayName}</span>
            </h1>
            <p className="text-sm text-text-secondary mt-2 leading-relaxed max-w-md">
              Manage campaigns, creators and performance from one place.
            </p>
            <div className="mt-5 flex flex-wrap gap-2.5">
              <Link to="/app/campaigns/new">
                <Button className="gap-2 shadow-[0_10px_24px_rgba(91,95,239,0.32)] hover:-translate-y-px hover:shadow-[0_14px_28px_rgba(91,95,239,0.38)] motion-reduce:hover:translate-y-0">
                  <Plus className="h-4 w-4" /> Create Campaign
                </Button>
              </Link>
              <Link to="/app/discovery" className="group">
                <Button
                  variant="secondary"
                  className="gap-2 bg-white/85 dark:bg-elevated/90 border-primary/20 hover:bg-white dark:hover:bg-elevated hover:border-primary/35 hover:-translate-y-px motion-reduce:hover:translate-y-0"
                >
                  Discover creators{' '}
                  <ArrowUpRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5 motion-reduce:group-hover:translate-x-0" />
                </Button>
              </Link>
            </div>
          </div>

          <div className="w-full lg:flex-1 lg:max-w-[38%] flex justify-start sm:justify-center lg:justify-end">
            <OverviewHeroMomentum className="w-[220px] sm:w-[248px] lg:w-[268px] scale-[0.92] sm:scale-100 origin-left lg:origin-right" />
          </div>
        </div>
      </section>

      <section className="relative grid grid-cols-2 xl:grid-cols-4 gap-3 stagger-in">
        {summaryCards.map((card) => {
          const Icon = card.icon
          return (
            <Link key={card.id} to={card.href} className="block group">
              <Card className="ui-card-hover ui-card-accent p-3.5 h-full relative overflow-hidden">
                <div className="absolute -right-6 -top-6 h-16 w-16 rounded-full bg-primary/[0.06] dark:bg-primary/10 pointer-events-none" />
                <ArrowUpRight className="absolute top-3 right-3 h-3.5 w-3.5 text-text-secondary/40 group-hover:text-primary transition-colors" />
                <div className="flex items-start gap-3">
                  <span className={cn('h-9 w-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs', card.iconClass)}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-[11px] font-medium text-text-secondary">{card.label}</p>
                    <p className="mt-0.5 text-[22px] font-bold tracking-tight text-text">
                      {loading ? '—' : card.value}
                    </p>
                    <p className="mt-1 text-[11px] text-text-secondary line-clamp-1">{card.context}</p>
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </section>

      <section className="relative grid lg:grid-cols-5 gap-4">
        <Card className="lg:col-span-3">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Recent campaigns</CardTitle>
                <p className="text-xs text-text-secondary mt-0.5">Open a campaign for full details</p>
              </div>
              <Link to="/app/campaigns" className="text-xs font-semibold text-primary hover:underline shrink-0">
                View all
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-14 rounded-[12px] skeleton" />
                ))}
              </div>
            ) : recentCampaigns.length === 0 ? (
              <div className="py-8 text-center">
                <div className="mx-auto h-11 w-11 rounded-2xl bg-primary-soft text-primary flex items-center justify-center mb-3">
                  <FolderPlus className="h-5 w-5" />
                </div>
                <p className="text-sm font-semibold text-text">No campaigns yet</p>
                <p className="text-xs text-text-secondary mt-1 max-w-sm mx-auto">
                  Create your first campaign to begin discovery, outreach, and tracking.
                </p>
                <Link to="/app/campaigns/new" className="inline-block mt-4">
                  <Button size="sm" className="gap-1.5">
                    <Plus className="h-3.5 w-3.5" /> Create Campaign
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {recentCampaigns.map((campaign) => (
                  <Link
                    key={campaign.id}
                    to={`/app/campaigns/${campaign.id}`}
                    className={cn(
                      'group flex items-center gap-3 rounded-[12px] border border-border bg-page/40 px-3 py-2.5',
                      'transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:bg-surface hover:shadow-[0_8px_20px_rgba(91,95,239,0.08)] dark:hover:bg-elevated',
                    )}
                  >
                    <div className="h-9 w-9 rounded-xl bg-primary-soft text-primary flex items-center justify-center text-xs font-bold shrink-0">
                      {(campaign.name || 'C').slice(0, 1).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-text truncate">{campaign.name}</p>
                        <StatusChip status={campaign.status} className="shrink-0" />
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-text-secondary">
                        <span className="truncate">{campaign.brand}</span>
                        <span>·</span>
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatDateRange(campaign.startDate, campaign.endDate)}
                        </span>
                        <span>·</span>
                        <span>{campaign.influencers || 0} creators</span>
                      </div>
                    </div>
                    <div className="hidden sm:flex w-20 flex-col gap-1 shrink-0">
                      <ProgressBar value={campaign.progress || 0} size="sm" />
                      <span className="text-[10px] text-text-secondary text-right">{campaign.progress || 0}%</span>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <CardTitle>Revenue vs Spend</CardTitle>
                <p className="text-xs text-text-secondary mt-0.5">From analytics records</p>
              </div>
              <span className="text-[10px] font-medium text-text-secondary rounded-full border border-border px-2 py-0.5">
                Existing data
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="h-[180px] flex flex-col items-center justify-center text-center px-4 rounded-[12px] border border-dashed border-border bg-page/40 relative overflow-hidden">
                <div className="absolute inset-x-6 bottom-8 flex items-end gap-1.5 h-16 opacity-[0.12] pointer-events-none" aria-hidden>
                  {[40, 55, 35, 70, 50, 65, 45, 58].map((h, i) => (
                    <div key={i} className="flex-1 rounded-t bg-primary" style={{ height: `${h}%` }} />
                  ))}
                </div>
                <Activity className="h-7 w-7 text-text-secondary/40 mb-2 relative" />
                <p className="text-sm font-semibold text-text relative">No analytics data yet</p>
                <p className="text-xs text-text-secondary mt-1 max-w-[220px] relative">
                  Data will appear here once your campaigns start getting results.
                </p>
              </div>
            ) : (
              <div className="h-[180px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                    <defs>
                      <linearGradient id="dash-spend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartStroke} stopOpacity={0.28} />
                        <stop offset="95%" stopColor={chartStroke} stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="dash-rev" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartStrokeAlt} stopOpacity={0.22} />
                        <stop offset="95%" stopColor={chartStrokeAlt} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--auralytics-chart-grid)" vertical={false} />
                    <XAxis dataKey="month" stroke="var(--auralytics-chart-axis)" fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis
                      stroke="var(--auralytics-chart-axis)"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => (Number(v) >= 100000 ? `₹${Number(v) / 100000}L` : `₹${Number(v)}`)}
                    />
                    <Tooltip
                      formatter={(v) => formatINR(Number(v))}
                      contentStyle={{
                        backgroundColor: 'var(--auralytics-tooltip-bg)',
                        borderColor: 'var(--auralytics-tooltip-border)',
                        borderRadius: 12,
                        fontSize: 12,
                        color: 'var(--auralytics-text)',
                      }}
                    />
                    <Area type="monotone" dataKey="spend" name="Spend" stroke={chartStroke} strokeWidth={2} fillOpacity={1} fill="url(#dash-spend)" />
                    <Area type="monotone" dataKey="revenue" name="Revenue" stroke={chartStrokeAlt} strokeWidth={2} fillOpacity={1} fill="url(#dash-rev)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="relative">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Recent activity</CardTitle>
                <p className="text-xs text-text-secondary mt-0.5">Real events from your campaigns</p>
              </div>
              {activities.length > 0 && (
                <Link to="/app/campaigns" className="text-xs font-semibold text-primary hover:underline">
                  View campaigns →
                </Link>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <div className="py-8 text-center text-text-secondary">
                <Clock className="h-8 w-8 mx-auto text-text-secondary/40 mb-2" />
                <p className="font-semibold text-text text-sm">No recent activity</p>
                <p className="text-xs mt-1">Campaign activity will appear here as you work.</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {activities.slice(0, 6).map((act) => (
                  <div
                    key={act.id}
                    className="flex items-start gap-3 px-3 py-2.5 rounded-[12px] border border-transparent hover:border-border hover:bg-page/50 dark:hover:bg-elevated/60 transition-colors"
                  >
                    <div className="h-8 w-8 rounded-xl bg-primary-soft text-primary flex items-center justify-center shrink-0">
                      <Zap className="h-3.5 w-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-text truncate">{act.title}</p>
                        <span className="text-[11px] text-text-secondary shrink-0">
                          {formatActivityTime(act.created_at)}
                        </span>
                      </div>
                      {act.description && (
                        <p className="text-xs text-text-secondary mt-0.5 line-clamp-1">{act.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
