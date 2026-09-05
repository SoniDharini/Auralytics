import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  ArrowRight,
  Bot,
  Clapperboard,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { api } from '@/services/api'
import type { DashboardAnalyticsData } from '@/services/api'
import { PageAmbientBackground } from '@/components/brand/VisualSystem'
import {
  Avatar,
  Badge,
  Button,
  CardContent,
  CardHeader,
  CardTitle,
  Drawer,
  PlatformIcon,
  ProgressBar,
  Select,
  StatusChip,
} from '@/components/ui'
import {
  AnalyticsKpiCard,
  AnalyticsKpiSkeleton,
  ChartSkeleton,
  HumanInTheLoopNote,
  InfoTip,
  RowSkeleton,
  SectionCard,
  SectionEmpty,
  SectionError,
  SectionHeading,
  SourceLabel,
  TransparencyBanner,
  aggregateHealthLabel,
  campaignHasTrackedTotals,
  formatCompactCount,
  formatExactMoney,
  formatMoney,
  formatRelativeTime,
  formatRoas,
  healthCopy,
  statusDotClass,
} from '@/components/analytics'
import { cn, formatINR, statusLabel } from '@/utils'
import type {
  AgentRun,
  Campaign,
  CampaignActivity,
  CampaignCreator,
  CampaignWorkflow,
  Platform,
} from '@/types'

type ChartMetric = 'spend' | 'revenue' | 'roas'

const chartMetricOptions: { id: ChartMetric; label: string }[] = [
  { id: 'spend', label: 'Spend' },
  { id: 'revenue', label: 'Revenue' },
  { id: 'roas', label: 'ROAS' },
]

const BAR_COLORS = ['#5B5FEF', '#7C3AED', '#8B5CF6', '#A78BFA', '#6366F1', '#4F46E5']

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (typeof item === 'string') return item
      const record = asRecord(item)
      if (!record) return null
      if (typeof record.text === 'string') return record.text
      if (typeof record.title === 'string') return record.title
      if (typeof record.detail === 'string') return record.detail
      return null
    })
    .filter((item): item is string => Boolean(item))
}

function pickString(record: Record<string, unknown> | null, keys: string[]): string | undefined {
  if (!record) return undefined
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return undefined
}

export function AnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const campaignId = searchParams.get('campaignId') || ''

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [analytics, setAnalytics] = useState<DashboardAnalyticsData | null>(null)
  const [activities, setActivities] = useState<CampaignActivity[]>([])
  const [creators, setCreators] = useState<CampaignCreator[]>([])
  const [workflow, setWorkflow] = useState<CampaignWorkflow | null>(null)
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([])
  const [platformFilter, setPlatformFilter] = useState('all')
  const [chartMetric, setChartMetric] = useState<ChartMetric>('spend')
  const [selectedCreator, setSelectedCreator] = useState<CampaignCreator | null>(null)

  const [loadingCore, setLoadingCore] = useState(true)
  const [loadingCreators, setLoadingCreators] = useState(false)
  const [campaignsError, setCampaignsError] = useState<string | null>(null)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)
  const [activitiesError, setActivitiesError] = useState<string | null>(null)
  const [creatorsError, setCreatorsError] = useState<string | null>(null)

  const loadCore = useCallback(async () => {
    setLoadingCore(true)
    setCampaignsError(null)
    setAnalyticsError(null)
    setActivitiesError(null)

    const [campsResult, analyticsResult, activitiesResult] = await Promise.allSettled([
      api.campaigns.list(),
      api.analytics.get(campaignId || undefined),
      api.activities.list(campaignId || undefined, 12),
    ])

    if (campsResult.status === 'fulfilled') {
      setCampaigns(campsResult.value || [])
    } else {
      setCampaigns([])
      setCampaignsError(campsResult.reason?.message || 'Campaigns unavailable')
    }

    if (analyticsResult.status === 'fulfilled') {
      setAnalytics(analyticsResult.value)
    } else {
      setAnalytics(null)
      setAnalyticsError(analyticsResult.reason?.message || 'Performance metrics unavailable')
    }

    if (activitiesResult.status === 'fulfilled') {
      setActivities(activitiesResult.value || [])
    } else {
      setActivities([])
      setActivitiesError(activitiesResult.reason?.message || 'Activity unavailable')
    }

    if (campaignId) {
      const [workflowResult, runsResult] = await Promise.allSettled([
        api.campaigns.getWorkflow(campaignId),
        api.agents.listCampaignRuns(campaignId),
      ])
      setWorkflow(workflowResult.status === 'fulfilled' ? workflowResult.value : null)
      setAgentRuns(runsResult.status === 'fulfilled' ? runsResult.value || [] : [])
    } else {
      setWorkflow(null)
      setAgentRuns([])
    }

    setLoadingCore(false)
  }, [campaignId])

  const loadCreators = useCallback(async () => {
    if (!campaignId) {
      setCreators([])
      setCreatorsError(null)
      setLoadingCreators(false)
      return
    }
    setLoadingCreators(true)
    setCreatorsError(null)
    try {
      const result = await api.discovery.listCreators(campaignId, { limit: 50 })
      setCreators(result.creators || [])
    } catch (error: any) {
      setCreators([])
      setCreatorsError(error?.message || 'Creator roster unavailable')
    } finally {
      setLoadingCreators(false)
    }
  }, [campaignId])

  useEffect(() => {
    let mounted = true
    loadCore().then(() => {
      if (!mounted) return
    })
    return () => {
      mounted = false
    }
  }, [loadCore])

  useEffect(() => {
    loadCreators()
  }, [loadCreators])

  const selectedCampaign = useMemo(
    () => campaigns.find((campaign) => campaign.id === campaignId) || null,
    [campaigns, campaignId],
  )

  const scopedCampaigns = selectedCampaign ? [selectedCampaign] : campaigns
  const hasCampaigns = campaigns.length > 0
  const hasTrackedTotals = scopedCampaigns.some(campaignHasTrackedTotals)

  const totals = useMemo(() => {
    const spend = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.spend || 0), 0)
    const revenue = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.revenue || 0), 0)
    const conversions = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.conversions || 0), 0)
    const reach = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.reach || 0), 0)
    const budget = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.budget || 0), 0)
    const influencers = scopedCampaigns.reduce((sum, campaign) => sum + (campaign.influencers || 0), 0)
    const storedRoas = selectedCampaign
      ? selectedCampaign.roas || 0
      : scopedCampaigns.length === 0
        ? 0
        : scopedCampaigns.reduce((sum, campaign) => sum + (campaign.roas || 0), 0) / scopedCampaigns.length
    return { spend, revenue, conversions, reach, budget, influencers, roas: Number.isFinite(storedRoas) ? storedRoas : 0 }
  }, [scopedCampaigns, selectedCampaign])

  const health = selectedCampaign
    ? healthCopy(selectedCampaign.health)
    : aggregateHealthLabel(campaigns)

  const lastUpdated = selectedCampaign?.updated_at || selectedCampaign?.created_at || campaigns[0]?.updated_at
  const topCampaign = useMemo(() => {
    if (selectedCampaign) return selectedCampaign
    return [...campaigns].sort((a, b) => (b.spend || 0) - (a.spend || 0))[0] || null
  }, [campaigns, selectedCampaign])

  const chartData = useMemo(() => {
    const points = analytics?.revenueSpendData || []
    const meaningful = points.filter((point) => (point.spend || 0) > 0 || (point.revenue || 0) > 0 || (point.roas || 0) > 0)
    return meaningful
  }, [analytics])

  const campaignSpendBars = useMemo(
    () =>
      scopedCampaigns
        .filter((campaign) => (campaign.spend || 0) > 0 || (campaign.revenue || 0) > 0)
        .map((campaign) => ({
          name: campaign.name,
          spend: campaign.spend || 0,
          revenue: campaign.revenue || 0,
        })),
    [scopedCampaigns],
  )

  const visibleCreators = useMemo(() => {
    if (platformFilter === 'all') return creators
    return creators.filter((row) => String(row.creator.platform) === platformFilter)
  }, [creators, platformFilter])

  const platformOptions = useMemo(() => {
    const values = Array.from(new Set(creators.map((row) => String(row.creator.platform)).filter(Boolean)))
    return [{ value: 'all', label: 'All Platforms' }, ...values.map((value) => ({ value, label: statusLabel(value) }))]
  }, [creators])

  const performanceRun = useMemo(
    () => agentRuns.find((run) => run.agentName === 'performance') || null,
    [agentRuns],
  )
  const optimizationRun = useMemo(
    () => agentRuns.find((run) => run.agentName === 'optimization') || null,
    [agentRuns],
  )

  const performanceNarrative = useMemo(() => {
    const output = asRecord(performanceRun?.outputJson)
    return {
      health: pickString(output, ['health', 'campaign_health', 'status']),
      strengths: stringList(output?.strengths ?? output?.whats_working ?? output?.top_strengths),
      weaknesses: stringList(output?.weaknesses ?? output?.needs_attention),
      observations: stringList(output?.observations ?? output?.insights ?? output?.key_observations),
      risks: stringList(output?.risks),
      insight: pickString(output, ['key_insight', 'summary', 'message']),
    }
  }, [performanceRun])

  const optimizationActions = useMemo(() => {
    const output = asRecord(optimizationRun?.outputJson)
    const raw = output?.recommendations ?? output?.actions ?? output?.proposals
    if (!Array.isArray(raw)) return []
    return raw
      .map((item, index) => {
        const record = asRecord(item)
        if (!record) return null
        const title = pickString(record, ['title', 'action', 'suggested_action'])
        if (!title) return null
        return {
          id: typeof record.id === 'string' ? record.id : `opt-${index}`,
          title,
          impact: pickString(record, ['impact', 'priority']) || 'Not specified',
          category: pickString(record, ['category', 'type']) || 'Optimization',
          reason: pickString(record, ['reason', 'detail', 'summary']) || 'No reason provided.',
        }
      })
      .filter((item): item is NonNullable<typeof item> => Boolean(item))
  }, [optimizationRun])

  const kpis = useMemo(() => {
    const budgetShare = totals.budget > 0 ? `${Math.round((totals.spend / totals.budget) * 100)}% of budget` : 'No budget recorded'
    const analyticsRoas = !selectedCampaign
      ? analytics?.metrics.find((metric) => metric.id === 'roas')?.value
      : null
    const cards = [
      {
        id: 'spend',
        label: 'Total Spend',
        value: formatMoney(totals.spend),
        context: budgetShare,
        tip: 'Stored campaign spend from campaign records.',
        source: 'Campaign records',
      },
      {
        id: 'revenue',
        label: 'Revenue',
        value: formatMoney(totals.revenue),
        context: totals.revenue > 0 ? 'Attributed in campaign records' : 'No attributed revenue yet',
        tip: 'Stored campaign revenue. Not inferred from social metrics.',
        source: 'Campaign records',
      },
      {
        id: 'roas',
        label: 'ROAS',
        value: analyticsRoas || formatRoas(totals.roas),
        context: selectedCampaign?.target_roas ? `Target ${formatRoas(selectedCampaign.target_roas)}` : 'Stored campaign ROAS',
        tip: 'Return on ad spend stored on the campaign, or the analytics average when viewing all campaigns.',
        source: 'Backend Calculated',
      },
      {
        id: 'reach',
        label: 'Reach',
        value: formatCompactCount(totals.reach),
        context: 'Unique impressions in campaign records',
        tip: 'Reach stored on the campaign. This is not live video view tracking.',
        source: 'Campaign records',
      },
    ]
    cards.push({
      id: 'conversions',
      label: 'Conversions',
      value: formatCompactCount(totals.conversions),
      context: 'Tracked orders / leads',
      tip: 'Conversions stored on the campaign.',
      source: 'Campaign records',
    })
    if (totals.conversions > 0) {
      cards.push({
        id: 'cpa',
        label: 'Cost / Conversion',
        value: formatINR(Math.round(totals.spend / totals.conversions)),
        context: 'Spend ÷ conversions',
        tip: 'Campaign spend divided by tracked conversions.',
        source: 'Backend fields',
      })
    } else {
      cards.push({
        id: 'creators',
        label: 'Creators',
        value: String(totals.influencers),
        context: selectedCampaign ? 'Linked to this campaign' : 'Across selected campaigns',
        tip: 'Creator count stored on the campaign.',
        source: 'Campaign records',
      })
    }
    return cards
  }, [totals, selectedCampaign, analytics])

  const setCampaignFilter = (value: string) => {
    setPlatformFilter('all')
    const next = new URLSearchParams(searchParams)
    if (value) next.set('campaignId', value)
    else next.delete('campaignId')
    setSearchParams(next, { replace: true })
  }

  const refreshAll = () => {
    loadCore()
    loadCreators()
  }

  const workflowLabel = workflow?.current_step ? statusLabel(workflow.current_step) : null
  const liveCampaign = selectedCampaign?.status === 'active'

  return (
    <div className="relative space-y-8 animate-fade-in">
      <PageAmbientBackground variant="analytics" className="h-[400px]" />
      <header className="relative overflow-hidden rounded-[20px] border border-border bg-surface px-5 py-5 shadow-[0_8px_30px_rgba(17,24,39,0.04)] sm:px-6">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(1200px_circle_at_0%_-20%,color-mix(in_srgb,var(--auralytics-primary)_12%,transparent),transparent_45%),radial-gradient(800px_circle_at_100%_0%,color-mix(in_srgb,var(--auralytics-accent)_10%,transparent),transparent_40%)]" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Auralytics Analytics</p>
            <h1 className="mt-1 text-[28px] font-bold tracking-tight text-text sm:text-[32px]">
              {selectedCampaign?.name || 'Campaign performance'}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-text-secondary">
              {selectedCampaign ? (
                <span className="inline-flex items-center gap-2 rounded-full bg-page/80 px-2.5 py-1 ring-1 ring-border">
                  <span className={cn('h-2 w-2 rounded-full', statusDotClass(selectedCampaign.status))} />
                  <span className="font-medium text-text">{statusLabel(selectedCampaign.status)}</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-full bg-page/80 px-2.5 py-1 ring-1 ring-border">
                  All campaigns
                </span>
              )}
              {workflowLabel && <Badge variant="ai">{workflowLabel}</Badge>}
              <span>Updated {formatRelativeTime(lastUpdated)}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto] lg:w-[420px]">
            <Select
              aria-label="Campaign"
              value={campaignId}
              onChange={(event) => setCampaignFilter(event.target.value)}
              options={[
                { value: '', label: 'All Campaigns' },
                ...campaigns.map((campaign) => ({ value: campaign.id, label: campaign.name })),
              ]}
            />
            <Button variant="secondary" className="gap-2" onClick={refreshAll}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </Button>
          </div>
        </div>
      </header>

      {hasCampaigns && (
        <div className="sticky top-16 z-10 -mx-1 rounded-[14px] border border-border bg-surface/90 px-3 py-2.5 shadow-sm backdrop-blur">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs sm:text-sm">
            <span>
              <span className="text-text-secondary">Health</span>{' '}
              <span className="font-semibold text-text">{health.label}</span>
            </span>
            <span>
              <span className="text-text-secondary">Spend</span>{' '}
              <span className="font-semibold text-text">{formatMoney(totals.spend)}</span>
            </span>
            <span>
              <span className="text-text-secondary">Revenue</span>{' '}
              <span className="font-semibold text-text">{formatMoney(totals.revenue)}</span>
            </span>
            {topCampaign && (
              <span className="truncate">
                <span className="text-text-secondary">Focus</span>{' '}
                <span className="font-semibold text-text">{topCampaign.name}</span>
              </span>
            )}
            <span className="sm:ml-auto">
              <span className="text-text-secondary">Recommendations</span>{' '}
              <span className="font-semibold text-text">{optimizationActions.length}</span>
            </span>
          </div>
        </div>
      )}

      <TransparencyBanner />

      {loadingCore && (
        <div className="space-y-8">
          <SkeletonBlock />
        </div>
      )}

      {!loadingCore && !hasCampaigns && (
        <SectionCard>
          <CardContent className="py-16">
            <SectionEmpty
              title="No performance data yet"
              description="Performance tracking will appear here once a campaign exists and campaign totals are recorded."
              actionLabel="Create campaign"
              to="/app/campaigns/new"
            />
          </CardContent>
        </SectionCard>
      )}

      {!loadingCore && hasCampaigns && (
        <>
          <section className="space-y-4">
            <SectionHeading eyebrow="Campaign health" title="How is this campaign doing?" />
            <SectionCard className="overflow-hidden">
              <div
                className={cn(
                  'h-1.5',
                  health.tone === 'excellent' && 'bg-success',
                  health.tone === 'needs_attention' && 'bg-danger',
                  health.tone === 'healthy' && 'bg-gradient-to-r from-primary to-accent',
                  health.tone === 'unknown' && 'bg-border',
                )}
              />
              <CardContent className="grid gap-6 py-6 sm:grid-cols-[1.3fr_0.7fr]">
                <div>
                  <Badge variant={health.badge}>{health.label}</Badge>
                  <p className="mt-3 max-w-xl text-sm leading-relaxed text-text-secondary">{health.summary}</p>
                  {selectedCampaign && (
                    <p className="mt-3 text-sm text-text">
                      {selectedCampaign.brand} · {statusLabel(selectedCampaign.objective || 'Campaign')}
                    </p>
                  )}
                </div>
                <div className="rounded-[14px] border border-border bg-elevated p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">Recorded totals</p>
                  <div className="mt-3 space-y-2 text-sm">
                    <div className="flex justify-between gap-3">
                      <span className="text-text-secondary">Spend</span>
                      <span className="font-semibold">{formatMoney(totals.spend)}</span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span className="text-text-secondary">Revenue</span>
                      <span className="font-semibold">{formatMoney(totals.revenue)}</span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span className="text-text-secondary">ROAS</span>
                      <span className="font-semibold">{formatRoas(totals.roas)}</span>
                    </div>
                  </div>
                  <p className="mt-3 text-[11px] text-text-secondary">No separate health score is stored. Status only.</p>
                </div>
              </CardContent>
            </SectionCard>
          </section>

          <section className="space-y-4">
            <SectionHeading
              eyebrow="Top KPIs"
              title="What are the numbers?"
              description="Only metrics already stored on campaigns or returned by analytics are shown."
            />
            {analyticsError && (
              <SectionError
                title="Performance metrics unavailable"
                description={analyticsError}
                onRetry={loadCore}
              />
            )}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map((kpi) => (
                <AnalyticsKpiCard key={kpi.id} {...kpi} />
              ))}
            </div>
          </section>

          {(totals.budget > 0 || totals.conversions > 0) && (
            <section className="space-y-4">
              <SectionHeading
                eyebrow="Cost efficiency"
                title="How efficiently is budget being used?"
                action={<SourceLabel>Campaign records</SourceLabel>}
              />
              <div className="grid gap-4 md:grid-cols-3">
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center gap-1">
                      <p className="text-sm text-text-secondary">Budget used</p>
                      <InfoTip label="About budget used" text="Campaign spend divided by allocated budget." />
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight">
                      {totals.budget > 0 ? `${Math.round((totals.spend / totals.budget) * 100)}%` : '—'}
                    </p>
                    <p className="mt-2 text-xs text-text-secondary">
                      {formatMoney(totals.spend)} of {formatMoney(totals.budget)}
                    </p>
                    <div className="mt-4">
                      <ProgressBar
                        value={totals.budget > 0 ? (totals.spend / totals.budget) * 100 : 0}
                        barClassName="bg-gradient-to-r from-primary to-accent"
                      />
                    </div>
                  </CardContent>
                </SectionCard>
                <SectionCard>
                  <CardContent className="pt-5">
                    <p className="text-sm text-text-secondary">Cost / conversion</p>
                    <p className="mt-2 text-[28px] font-bold tracking-tight">
                      {totals.conversions > 0 ? formatINR(Math.round(totals.spend / totals.conversions)) : '—'}
                    </p>
                    <p className="mt-2 text-xs text-text-secondary">
                      {totals.conversions > 0 ? 'Spend divided by tracked conversions' : 'No conversions recorded yet'}
                    </p>
                  </CardContent>
                </SectionCard>
                <SectionCard>
                  <CardContent className="pt-5">
                    <p className="text-sm text-text-secondary">Cost / reach</p>
                    <p className="mt-2 text-[28px] font-bold tracking-tight">
                      {totals.reach > 0 ? formatExactMoney(totals.spend / totals.reach) : '—'}
                    </p>
                    <p className="mt-2 text-xs text-text-secondary">
                      {totals.reach > 0 ? 'Spend divided by recorded reach' : 'No reach recorded yet'}
                    </p>
                  </CardContent>
                </SectionCard>
              </div>
            </section>
          )}

          <section className="space-y-4">
            <SectionHeading
              eyebrow="Performance trend"
              title="Performance over time"
              description="Charted from analytics spend, revenue, and ROAS. Views, likes, and comments are not tracked yet."
              action={
                <div className="flex rounded-[10px] border border-border bg-surface p-1">
                  {chartMetricOptions.map((option) => (
                    <button
                      key={option.id}
                      type="button"
                      onClick={() => setChartMetric(option.id)}
                      className={cn(
                        'rounded-[8px] px-3 py-1.5 text-xs font-semibold transition',
                        chartMetric === option.id ? 'bg-primary text-white' : 'text-text-secondary hover:text-text',
                      )}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              }
            />
            <SectionCard>
              <CardContent className="pt-5">
                {analyticsError ? (
                  <SectionError title="Trend unavailable" description={analyticsError} onRetry={loadCore} />
                ) : chartData.length === 0 ? (
                  <SectionEmpty
                    title={liveCampaign ? 'No campaign content is being tracked yet' : 'No performance trend yet'}
                    description={
                      liveCampaign
                        ? 'This campaign is live, but analytics only has stored campaign totals so far. A trend chart will appear when spend or revenue snapshots exist.'
                        : 'A trend will appear here once campaign spend or revenue is recorded.'
                    }
                    actionLabel={selectedCampaign ? 'Return to campaign' : undefined}
                    to={selectedCampaign ? `/app/campaigns/${selectedCampaign.id}` : undefined}
                  />
                ) : (
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      {chartData.length === 1 ? (
                        <BarChart data={chartData} barSize={48}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                          <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                          <YAxis
                            tick={{ fontSize: 11, fill: '#6B7280' }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(value) =>
                              chartMetric === 'roas' ? `${Number(value).toFixed(1)}x` : formatMoney(Number(value))
                            }
                          />
                          <Tooltip content={<TrendTooltip metric={chartMetric} />} />
                          <Bar dataKey={chartMetric} fill="#5B5FEF" radius={[8, 8, 0, 0]} />
                        </BarChart>
                      ) : (
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient id="analytics-metric" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#5B5FEF" stopOpacity={0.28} />
                              <stop offset="100%" stopColor="#5B5FEF" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                          <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                          <YAxis
                            tick={{ fontSize: 11, fill: '#6B7280' }}
                            axisLine={false}
                            tickLine={false}
                            tickFormatter={(value) =>
                              chartMetric === 'roas' ? `${Number(value).toFixed(1)}x` : formatMoney(Number(value))
                            }
                          />
                          <Tooltip content={<TrendTooltip metric={chartMetric} />} />
                          <Area
                            type="monotone"
                            dataKey={chartMetric}
                            stroke="#5B5FEF"
                            fill="url(#analytics-metric)"
                            strokeWidth={2}
                          />
                        </AreaChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </SectionCard>
          </section>

          {campaignSpendBars.length > 1 && (
            <section className="space-y-4">
              <SectionHeading eyebrow="Campaign comparison" title="Spend by campaign" />
              <SectionCard>
                <CardContent className="pt-5">
                  <div className="h-[240px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={campaignSpendBars} layout="vertical" margin={{ left: 16, right: 16 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                        <XAxis
                          type="number"
                          tick={{ fontSize: 11, fill: '#6B7280' }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(value) => formatMoney(Number(value))}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={120}
                          tick={{ fontSize: 11, fill: '#6B7280' }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip formatter={(value) => formatINR(Number(value))} />
                        <Bar dataKey="spend" radius={[0, 8, 8, 0]}>
                          {campaignSpendBars.map((entry, index) => (
                            <Cell key={entry.name} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </SectionCard>
            </section>
          )}

          <section className="space-y-4">
            <SectionHeading
              eyebrow="Campaign content"
              title="Campaign content performance"
              description="Sponsored videos, Shorts, and Reels will appear here once content tracking is registered."
            />
            <SectionCard>
              <CardContent className="py-4">
                <div className="flex items-start gap-3 rounded-[14px] bg-page px-4 py-5">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                    <Clapperboard className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-text">
                      {liveCampaign ? 'No campaign content is being tracked yet.' : 'No tracked campaign content'}
                    </p>
                    <p className="mt-1 text-sm text-text-secondary">
                      {liveCampaign
                        ? 'The campaign is live, but this workspace does not yet store individual video or Short performance. Register content from the campaign when tracking becomes available.'
                        : 'Content-level views, likes, comments, and baseline lift are not stored yet.'}
                    </p>
                    {selectedCampaign && (
                      <Link to={`/app/campaigns/${selectedCampaign.id}`} className="mt-3 inline-flex">
                        <Button size="sm" variant="secondary" className="gap-1.5">
                          Return to campaign <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              </CardContent>
            </SectionCard>
          </section>

          <section className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <SectionHeading
                eyebrow="Influencer performance"
                title="Who is on this campaign?"
                description="Creator roster and campaign status. Channel profile metrics are not campaign content results."
              />
              {selectedCampaign && platformOptions.length > 1 && (
                <Select
                  aria-label="Platform"
                  className="lg:w-48"
                  value={platformFilter}
                  onChange={(event) => setPlatformFilter(event.target.value)}
                  options={platformOptions}
                />
              )}
            </div>
            <SectionCard>
              <CardContent className="pt-5">
                {!selectedCampaign ? (
                  <CampaignHealthTable
                    rows={analytics?.campaignHealth || scopedCampaigns.map((campaign) => ({
                      id: campaign.id,
                      name: campaign.name,
                      health: campaign.health,
                      roas: campaign.roas,
                      spend: campaign.spend,
                      progress: campaign.progress,
                    }))}
                  />
                ) : loadingCreators ? (
                  <RowSkeleton />
                ) : creatorsError ? (
                  <SectionError title="Creator roster unavailable" description={creatorsError} onRetry={loadCreators} />
                ) : visibleCreators.length === 0 ? (
                  <SectionEmpty
                    title="No creators linked yet"
                    description="Discover and shortlist creators to see who is attached to this campaign."
                    actionLabel="Open campaign creators"
                    to={`/app/campaigns/${selectedCampaign.id}?tab=influencers`}
                  />
                ) : (
                  <CreatorRosterTable rows={visibleCreators} onSelect={setSelectedCreator} />
                )}
              </CardContent>
            </SectionCard>
          </section>

          {(analytics?.funnel?.length || 0) > 0 && (
            <section className="space-y-4">
              <SectionHeading
                eyebrow="Pipeline"
                title="Creator funnel"
                action={<SourceLabel>Backend Calculated</SourceLabel>}
              />
              <SectionCard>
                <CardContent className="space-y-4 pt-5">
                  {analytics!.funnel.map((stage) => {
                    const max = Math.max(...analytics!.funnel.map((item) => item.value), 1)
                    return (
                      <div key={stage.label} className="space-y-1.5">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium text-text">{stage.label}</span>
                          <span className="text-text-secondary">{stage.value}</span>
                        </div>
                        <ProgressBar value={(stage.value / max) * 100} size="sm" />
                      </div>
                    )
                  })}
                </CardContent>
              </SectionCard>
            </section>
          )}

          <section className="space-y-4">
            <SectionHeading
              eyebrow="Performance Agent"
              title="Why did this happen?"
              description="Readable analysis from a Performance Agent run, when one exists."
            />
            <SectionCard>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-ai">
                    <Bot className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle>AI performance analysis</CardTitle>
                    <p className="text-xs text-text-secondary">What is happening — not what to change.</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {!selectedCampaign ? (
                  <SectionEmpty
                    title="Select a campaign to view agent analysis"
                    description="Performance Agent output is stored per campaign run."
                  />
                ) : !performanceRun ? (
                  <SectionEmpty
                    title="Performance Agent has not analyzed this campaign yet"
                    description="There is no Performance Agent run to display. Campaign health and KPIs above still come from stored campaign records."
                    actionLabel="View campaigns"
                    to="/app/campaigns"
                  />
                ) : (
                  <AgentNarrative
                    health={performanceNarrative.health || health.label}
                    strengths={performanceNarrative.strengths}
                    weaknesses={performanceNarrative.weaknesses}
                    observations={performanceNarrative.observations}
                    risks={performanceNarrative.risks}
                    insight={performanceNarrative.insight}
                    updatedAt={performanceRun.completedAt || performanceRun.createdAt}
                    status={performanceRun.status}
                    errorMessage={performanceRun.errorMessage}
                  />
                )}
              </CardContent>
            </SectionCard>
          </section>

          <section className="space-y-4">
            <SectionHeading
              eyebrow="Optimization Agent"
              title="What should we change?"
              description="Recommended actions stay pending until a person approves them."
            />
            <SectionCard>
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl ai-gradient-bg text-white">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle>Optimization opportunities</CardTitle>
                      <HumanInTheLoopNote />
                    </div>
                  </div>
                  <Link to="/app/optimization">
                    <Button variant="secondary" size="sm" className="gap-1.5">
                      Optimization Center <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {optimizationActions.length > 0 ? (
                  <div className="space-y-3">
                    {optimizationActions.map((action) => (
                      <div key={action.id} className="rounded-[14px] border border-border bg-page/60 p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="ai">{action.impact}</Badge>
                          <Badge variant="outline">{action.category}</Badge>
                        </div>
                        <p className="mt-2 text-sm font-semibold text-text">{action.title}</p>
                        <p className="mt-1 text-sm text-text-secondary">{action.reason}</p>
                        <p className="mt-3 text-xs text-text-secondary">
                          Approve, modify, or reject from Optimization Center. Changes are not applied automatically.
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <SectionEmpty
                    title="No optimization recommendations yet"
                    description="The Optimization Agent has not produced actionable recommendations for this view. Budget changes still require human approval when they appear."
                    actionLabel="Open Optimization Center"
                    to="/app/optimization"
                  />
                )}
              </CardContent>
            </SectionCard>
          </section>

          <section className="space-y-4">
            <SectionHeading eyebrow="Recent activity" title="Tracking information" />
            <SectionCard>
              <CardContent className="pt-5">
                {activitiesError ? (
                  <SectionError title="Activity unavailable" description={activitiesError} onRetry={loadCore} />
                ) : activities.length === 0 ? (
                  <SectionEmpty
                    title="No tracking events yet"
                    description="Campaign and agent activity will appear here when events are recorded."
                  />
                ) : (
                  <ul className="space-y-3">
                    {activities.slice(0, 8).map((activity) => (
                      <li key={activity.id} className="flex items-start justify-between gap-3 rounded-[12px] border border-border bg-page/50 px-3 py-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-text">{activity.title}</p>
                          {activity.description && (
                            <p className="mt-0.5 text-sm text-text-secondary">{activity.description}</p>
                          )}
                        </div>
                        <span className="shrink-0 text-xs text-text-secondary">
                          {formatRelativeTime(activity.created_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </SectionCard>
          </section>
        </>
      )}

      {campaignsError && hasCampaigns && (
        <SectionError title="Some campaign data failed to load" description={campaignsError} onRetry={loadCore} />
      )}

      {!hasTrackedTotals && hasCampaigns && !loadingCore && (
        <p className="text-center text-xs text-text-secondary">
          Campaign totals are currently zero. Empty charts are hidden instead of showing fabricated series.
        </p>
      )}

      <Drawer
        open={Boolean(selectedCreator)}
        onClose={() => setSelectedCreator(null)}
        title="Creator details"
        subtitle="Campaign roster and public profile — not sponsored content tracking"
        footer={
          selectedCreator ? (
            <Link to={`/app/discovery/${selectedCreator.creator.id}`} className="block">
              <Button className="w-full">View creator profile</Button>
            </Link>
          ) : null
        }
      >
        {selectedCreator && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Avatar
                name={selectedCreator.creator.name}
                src={selectedCreator.creator.avatar || selectedCreator.creator.thumbnail_url}
                size="lg"
              />
              <div>
                <p className="font-semibold text-text">{selectedCreator.creator.name}</p>
                <p className="text-sm text-text-secondary">@{selectedCreator.creator.username}</p>
              </div>
            </div>
            <DetailRow label="Platform" value={statusLabel(String(selectedCreator.creator.platform))} />
            <DetailRow label="Campaign status" value={statusLabel(selectedCreator.status)} />
            {typeof selectedCreator.match_score === 'number' && (
              <DetailRow label="Discovery fit" value={`${Math.round(selectedCreator.match_score)}`} />
            )}
            <DetailRow
              label="Subscribers / followers"
              value={formatCompactCount(selectedCreator.creator.followers || 0)}
            />
            <DetailRow
              label="Typical views (profile)"
              value={formatCompactCount(selectedCreator.creator.avgViews || 0)}
            />
            <p className="text-xs text-text-secondary">
              Profile metrics come from creator records, usually YouTube. They are not views of campaign-sponsored
              content.
            </p>
          </div>
        )}
      </Drawer>
    </div>
  )
}

function SkeletonBlock() {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <AnalyticsKpiSkeleton key={index} />
        ))}
      </div>
      <SectionCard>
        <CardContent className="pt-5">
          <ChartSkeleton />
        </CardContent>
      </SectionCard>
      <SectionCard>
        <CardContent className="pt-5">
          <RowSkeleton />
        </CardContent>
      </SectionCard>
    </>
  )
}

function TrendTooltip({
  active,
  payload,
  label,
  metric,
}: {
  active?: boolean
  payload?: { payload: { spend: number; revenue: number; roas: number; month: string } }[]
  label?: string
  metric: ChartMetric
}) {
  if (!active || !payload?.[0]) return null
  const point = payload[0].payload
  return (
    <div className="rounded-[12px] border border-border bg-surface px-3 py-2.5 shadow-lg">
      <p className="text-xs font-semibold text-text">{label}</p>
      <div className="mt-2 space-y-1 text-xs">
        <p>Spend: {formatINR(point.spend)}</p>
        <p>Revenue: {formatINR(point.revenue)}</p>
        <p>ROAS: {formatRoas(point.roas)}</p>
      </div>
      <p className="mt-2 text-[10px] uppercase tracking-wide text-text-secondary">Showing {metric}</p>
    </div>
  )
}

function CampaignHealthTable({
  rows,
}: {
  rows: { id: string; name: string; health: string; roas: number; spend: number; progress: number }[]
}) {
  if (rows.length === 0) {
    return (
      <SectionEmpty
        title="No campaign health rows"
        description="Campaign health will appear from analytics once campaigns exist."
      />
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-border text-xs uppercase tracking-wide text-text-secondary">
            <th className="pb-3 font-semibold">Campaign</th>
            <th className="pb-3 font-semibold">Health</th>
            <th className="pb-3 font-semibold">Spend</th>
            <th className="pb-3 font-semibold">ROAS</th>
            <th className="pb-3 font-semibold">Progress</th>
            <th className="pb-3 font-semibold" />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const copy = healthCopy(row.health)
            return (
              <tr key={row.id} className="border-b border-border/70 last:border-0">
                <td className="py-3 font-medium text-text">{row.name}</td>
                <td className="py-3">
                  <Badge variant={copy.badge}>{copy.label}</Badge>
                </td>
                <td className="py-3 text-text-secondary">{formatMoney(row.spend || 0)}</td>
                <td className="py-3 text-text-secondary">{formatRoas(row.roas || 0)}</td>
                <td className="py-3 w-40">
                  <ProgressBar value={row.progress || 0} size="sm" />
                </td>
                <td className="py-3 text-right">
                  <Link to={`/app/analytics?campaignId=${row.id}`} className="text-xs font-semibold text-primary">
                    View
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CreatorRosterTable({
  rows,
  onSelect,
}: {
  rows: CampaignCreator[]
  onSelect: (row: CampaignCreator) => void
}) {
  return (
    <>
      <div className="mb-4 hidden overflow-x-auto md:block">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs uppercase tracking-wide text-text-secondary">
              <th className="pb-3 font-semibold">Influencer</th>
              <th className="pb-3 font-semibold">Platform</th>
              <th className="pb-3 font-semibold">Status</th>
              <th className="pb-3 font-semibold">Discovery fit</th>
              <th className="pb-3 font-semibold" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.link_id} className="border-b border-border/70 last:border-0">
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={row.creator.name} src={row.creator.avatar || row.creator.thumbnail_url} size="sm" />
                    <div>
                      <p className="font-medium text-text">{row.creator.name}</p>
                      <p className="text-xs text-text-secondary">@{row.creator.username}</p>
                    </div>
                  </div>
                </td>
                <td className="py-3">
                  <SafePlatformIcon platform={String(row.creator.platform)} showLabel />
                </td>
                <td className="py-3">
                  <StatusChip status={row.status} />
                </td>
                <td className="py-3 text-text-secondary">
                  {typeof row.match_score === 'number' ? Math.round(row.match_score) : '—'}
                </td>
                <td className="py-3 text-right">
                  <Button size="sm" variant="secondary" onClick={() => onSelect(row)}>
                    Details
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="space-y-3 md:hidden">
        {rows.map((row) => (
          <button
            key={row.link_id}
            type="button"
            onClick={() => onSelect(row)}
            className="w-full rounded-[14px] border border-border bg-page/60 p-4 text-left"
          >
            <div className="flex items-center gap-3">
              <Avatar name={row.creator.name} src={row.creator.avatar || row.creator.thumbnail_url} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-text">{row.creator.name}</p>
                <p className="text-xs text-text-secondary">{statusLabel(row.status)}</p>
              </div>
              <SafePlatformIcon platform={String(row.creator.platform)} />
            </div>
          </button>
        ))}
      </div>
    </>
  )
}

function AgentNarrative({
  health,
  strengths,
  weaknesses,
  observations,
  risks,
  insight,
  updatedAt,
  status,
  errorMessage,
}: {
  health?: string
  strengths: string[]
  weaknesses: string[]
  observations: string[]
  risks: string[]
  insight?: string
  updatedAt?: string | null
  status: string
  errorMessage?: string | null
}) {
  const hasStructured =
    strengths.length + weaknesses.length + observations.length + risks.length > 0 || Boolean(insight)
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="ai">Campaign health: {health || 'Recorded'}</Badge>
        <Badge variant="outline">{statusLabel(status)}</Badge>
        <span className="text-xs text-text-secondary">{formatRelativeTime(updatedAt)}</span>
      </div>
      {errorMessage && <p className="text-sm text-danger">{errorMessage}</p>}
      {hasStructured ? (
        <div className="grid gap-4 md:grid-cols-2">
          <NarrativeList title="What's working" items={strengths} />
          <NarrativeList title="Needs attention" items={weaknesses} />
          <NarrativeList title="Key observations" items={observations} />
          <NarrativeList title="Risks" items={risks} />
        </div>
      ) : (
        <p className="text-sm text-text-secondary">
          A Performance Agent run exists, but it did not include a structured analysis to display.
        </p>
      )}
      {insight && (
        <div className="rounded-[14px] border border-violet-100 bg-violet-50/50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-ai">Key insight</p>
          <p className="mt-1 text-sm leading-relaxed text-text">{insight}</p>
        </div>
      )}
    </div>
  )
}

function NarrativeList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="rounded-[14px] border border-border bg-page/50 p-4">
      <p className="text-sm font-semibold text-text">{title}</p>
      <ul className="mt-2 space-y-1.5 text-sm text-text-secondary">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SafePlatformIcon({ platform, showLabel }: { platform: string; showLabel?: boolean }) {
  const known: Platform[] = ['instagram', 'youtube', 'tiktok', 'x', 'linkedin']
  if (known.includes(platform as Platform)) {
    return <PlatformIcon platform={platform as Platform} showLabel={showLabel} />
  }
  return <span className="text-xs font-semibold text-text-secondary">{statusLabel(platform)}</span>
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border py-2 last:border-0">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium text-text">{value}</span>
    </div>
  )
}
