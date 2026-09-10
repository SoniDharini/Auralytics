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
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  Clapperboard,
  DollarSign,
  Edit3,
  ExternalLink,
  Eye,
  Heart,
  MessageSquare,
  Plus,
  RefreshCw,
  Sparkles,
  X,
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
  Input,
  Modal,
  PlatformIcon,
  ProgressBar,
  Select,
  StatusChip,
  useToast,
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
  CampaignContent,
  PerformanceAnalysis,
  OptimizationPlan,
} from '@/types'

function Youtube({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
    </svg>
  )
}

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


function pickString(record: Record<string, unknown> | null, keys: string[]): string | undefined {
  if (!record) return undefined
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return undefined
}

function formatStamp(iso?: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  })
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

  const { toast } = useToast()
  const [trackedContents, setTrackedContents] = useState<CampaignContent[]>([])
  const [selectedContentId, setSelectedContentId] = useState<string | null>(null)
  const [performanceAnalysis, setPerformanceAnalysis] = useState<PerformanceAnalysis | null>(null)
  const [optimizationPlan, setOptimizationPlan] = useState<OptimizationPlan | null>(null)
  const [loadingContent, setLoadingContent] = useState(false)
  const [loadingPerformance, setLoadingPerformance] = useState(false)
  const [loadingOptimization, setLoadingOptimization] = useState(false)
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [completeModalOpen, setCompleteModalOpen] = useState(false)
  const [completing, setCompleting] = useState(false)

  // Content tracking form state
  const [trackingInfluencerId, setTrackingInfluencerId] = useState<string>('')
  const [trackingUrl, setTrackingUrl] = useState<string>('')
  const trackingContentType = 'auto'
  const [isTrackingSubmitting, setIsTrackingSubmitting] = useState(false)
  const [trackingError, setTrackingError] = useState<string | null>(null)

  // Business attribution modal state
  const [attributionModalOpen, setAttributionModalOpen] = useState(false)
  const [attrMethod, setAttrMethod] = useState<'direct' | 'orders_aov'>('direct')
  const [attrRevenue, setAttrRevenue] = useState<string>('')
  const [attrOrders, setAttrOrders] = useState<string>('')
  const [attrAov, setAttrAov] = useState<string>('')
  const [attrMargin, setAttrMargin] = useState<string>('')

  // Modification dialog state
  const [modifyModalOpen, setModifyModalOpen] = useState(false)
  const [modifyingApprovalId, setModifyingApprovalId] = useState<string | null>(null)
  const [modifyNote, setModifyNote] = useState<string>('')

  const [loadingCore, setLoadingCore] = useState(true)
  const [loadingCreators, setLoadingCreators] = useState(false)
  const [campaignsError, setCampaignsError] = useState<string | null>(null)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)
  const [activitiesError, setActivitiesError] = useState<string | null>(null)
  const [creatorsError, setCreatorsError] = useState<string | null>(null)

  const campaignCompleted =
    campaigns.find((c) => c.id === campaignId)?.status === 'completed' || workflow?.is_completed === true

  const handleCompleteCampaign = async () => {
    if (!campaignId) return
    setCompleting(true)
    try {
      const updated = await api.campaigns.complete(campaignId)
      setCampaigns((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      const wf = await api.campaigns.getWorkflow(campaignId).catch(() => null)
      if (wf) setWorkflow(wf)
      setCompleteModalOpen(false)
      toast({
        title: 'Campaign completed',
        description: 'Performance and Optimization results remain available as campaign history.',
        type: 'success',
      })
    } catch (err: any) {
      toast({
        title: 'Could not complete campaign',
        description: err?.message || 'Complete the required workflow steps first.',
        type: 'error',
      })
    } finally {
      setCompleting(false)
    }
  }

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
      const camps = campsResult.value || []
      setCampaigns(camps)
      if (!campaignId && camps.length > 0) {
        setSearchParams({ campaignId: camps[0].id })
      }
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
  }, [campaignId, setSearchParams])

  const loadTrackedContent = useCallback(async (activeId?: string) => {
    if (!campaignId) {
      setTrackedContents([])
      setSelectedContentId(null)
      setPerformanceAnalysis(null)
      setOptimizationPlan(null)
      return
    }
    setLoadingContent(true)
    try {
      const items = await api.content.list(campaignId)
      setTrackedContents(items || [])
      if (items && items.length > 0) {
        const targetId = activeId || (selectedContentId && items.some((c) => c.id === selectedContentId) ? selectedContentId : items[0].id)
        setSelectedContentId(targetId)
        const [perf, opt] = await Promise.all([
          api.content.getLatestPerformance(campaignId, targetId),
          api.content.getLatestOptimization(campaignId, targetId),
        ])
        setPerformanceAnalysis(perf)
        setOptimizationPlan(opt)
      } else {
        setSelectedContentId(null)
        setPerformanceAnalysis(null)
        setOptimizationPlan(null)
      }
    } catch (err) {
      console.error('Failed to load tracked content', err)
    } finally {
      setLoadingContent(false)
    }
  }, [campaignId, selectedContentId])

  useEffect(() => {
    loadTrackedContent()
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

  useEffect(() => {
    if (creators.length > 0 && !trackingInfluencerId) {
      setTrackingInfluencerId(creators[0].creator.id)
    }
  }, [creators, trackingInfluencerId])

  const selectedContent = useMemo(
    () => trackedContents.find((c) => c.id === selectedContentId) || trackedContents[0] || null,
    [trackedContents, selectedContentId],
  )

  const handleSelectContent = async (contentId: string) => {
    setSelectedContentId(contentId)
    setLoadingPerformance(true)
    setLoadingOptimization(true)
    try {
      const [perf, opt] = await Promise.all([
        api.content.getLatestPerformance(campaignId, contentId),
        api.content.getLatestOptimization(campaignId, contentId),
      ])
      setPerformanceAnalysis(perf)
      setOptimizationPlan(opt)
    } finally {
      setLoadingPerformance(false)
      setLoadingOptimization(false)
    }
  }

  const handleRefreshContent = async (contentId: string) => {
    setActionLoading((prev) => ({ ...prev, [`refresh-${contentId}`]: true }))
    try {
      const updated = await api.content.refresh(campaignId, contentId)
      setTrackedContents((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      toast({ title: 'Metrics refreshed', description: 'Updated live statistics from YouTube Data API.', type: 'success' })
    } catch (err: any) {
      toast({ title: 'Refresh failed', description: err?.message || 'Could not fetch metrics.', type: 'error' })
    } finally {
      setActionLoading((prev) => ({ ...prev, [`refresh-${contentId}`]: false }))
    }
  }

  const handleStartTracking = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!trackingInfluencerId || !trackingUrl.trim()) {
      toast({ title: 'Missing information', description: 'Please select a creator and enter a YouTube URL.', type: 'warning' })
      return
    }
    setIsTrackingSubmitting(true)
    setTrackingError(null)
    try {
      const newContent = await api.content.track(campaignId, {
        influencer_id: trackingInfluencerId,
        content_url: trackingUrl.trim(),
        content_type: trackingContentType !== 'auto' ? trackingContentType : undefined,
      })
      setTrackedContents((prev) => [newContent, ...prev])
      setSelectedContentId(newContent.id)
      setTrackingUrl('')
      setTrackingError(null)
      toast({
        title: 'Content tracking registered',
        description: `Tracking '${newContent.title || 'YouTube Content'}' with live metrics & baseline.`,
        type: 'success',
      })
      const [perf, opt] = await Promise.all([
        api.content.getLatestPerformance(campaignId, newContent.id),
        api.content.getLatestOptimization(campaignId, newContent.id),
      ])
      setPerformanceAnalysis(perf)
      setOptimizationPlan(opt)
    } catch (err: any) {
      const msg = err?.message || 'Unable to register YouTube URL.'
      setTrackingError(msg)
      toast({ title: 'Tracking failed', description: msg, type: 'error' })
    } finally {
      setIsTrackingSubmitting(false)
    }
  }

  const handleRunPerformance = async (contentId: string) => {
    if (campaignCompleted) {
      toast({ title: 'Campaign completed', description: 'Agents do not rerun on completed campaigns.', type: 'info' })
      return
    }
    setLoadingPerformance(true)
    try {
      const analysis = await api.content.analyzePerformance(campaignId, contentId)
      setPerformanceAnalysis(analysis)
      toast({
        title: 'Performance Analysis Generated',
        description: `Performance Agent evaluated content. Status: ${analysis.status}`,
        type: 'success',
      })
    } catch (err: any) {
      toast({ title: 'Analysis failed', description: err?.message || 'Performance Agent failed.', type: 'error' })
    } finally {
      setLoadingPerformance(false)
    }
  }

  const handleRunOptimization = async (contentId: string) => {
    if (campaignCompleted) {
      toast({ title: 'Campaign completed', description: 'Agents do not rerun on completed campaigns.', type: 'info' })
      return
    }
    setLoadingOptimization(true)
    try {
      const plan = await api.content.generateOptimization(campaignId, contentId)
      setOptimizationPlan(plan)
      const recCount = plan.recommendations.length
      toast({
        title: recCount ? 'Optimization Recommendations Generated' : 'Optimization complete',
        description: recCount
          ? `${recCount} recommendation(s) created & sent to Approval Center.`
          : plan.overall_assessment === 'NO_ACTION_NEEDED'
            ? 'No campaign change is justified. Continue monitoring.'
            : 'Optimization finished. Campaign remains active.',
        type: 'success',
      })
    } catch (err: any) {
      toast({ title: 'Optimization failed', description: err?.message || 'Optimization Agent failed.', type: 'error' })
    } finally {
      setLoadingOptimization(false)
    }
  }

  const handleDecideRecommendation = async (approvalId: string, decision: 'approved' | 'modified' | 'rejected', reason?: string) => {
    setActionLoading((prev) => ({ ...prev, [`decide-${approvalId}`]: true }))
    try {
      const updatedPlan = await api.content.decideOptimization(campaignId, {
        approval_id: approvalId,
        decision,
        reason,
      })
      setOptimizationPlan(updatedPlan)
      toast({
        title: `Recommendation ${decision.charAt(0).toUpperCase() + decision.slice(1)}`,
        description: `Updated in Approval Center.`,
        type: decision === 'approved' ? 'success' : decision === 'rejected' ? 'info' : 'warning',
      })
    } catch (err: any) {
      toast({ title: 'Decision failed', description: err?.message || 'Could not record decision.', type: 'error' })
    } finally {
      setActionLoading((prev) => ({ ...prev, [`decide-${approvalId}`]: false }))
    }
  }

  const openAttributionModal = (content: CampaignContent) => {
    setAttrRevenue(content.attributed_revenue != null ? String(content.attributed_revenue) : '')
    setAttrOrders(content.attributed_orders != null ? String(content.attributed_orders) : '')
    setAttrAov(content.average_order_value != null ? String(content.average_order_value) : '')
    setAttrMargin(content.gross_margin_percent != null ? String(content.gross_margin_percent) : '')
    setAttrMethod(content.attributed_orders && content.average_order_value ? 'orders_aov' : 'direct')
    setAttributionModalOpen(true)
  }

  const handleSaveAttribution = async () => {
    if (!selectedContent) return
    setActionLoading((prev) => ({ ...prev, saveAttribution: true }))
    try {
      let rev = attrRevenue !== '' ? parseFloat(attrRevenue) : undefined
      const orders = attrOrders !== '' ? parseInt(attrOrders, 10) : undefined
      const aov = attrAov !== '' ? parseFloat(attrAov) : undefined
      const margin = attrMargin !== '' ? parseFloat(attrMargin) : undefined

      if (attrMethod === 'orders_aov' && orders && aov) {
        rev = orders * aov
      }

      const updated = await api.content.updateAttribution(campaignId, selectedContent.id, {
        attributed_revenue: rev,
        attributed_orders: orders,
        average_order_value: aov,
        gross_margin_percent: margin,
        attribution_source: 'BUSINESS ATTRIBUTION',
      })
      setTrackedContents((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      setAttributionModalOpen(false)
      toast({ title: 'Attribution saved', description: 'Business KPIs & ROAS recalculated deterministically.', type: 'success' })
    } catch (err: any) {
      toast({ title: 'Failed to save', description: err?.message || 'Error updating attribution.', type: 'error' })
    } finally {
      setActionLoading((prev) => ({ ...prev, saveAttribution: false }))
    }
  }

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

  const optimizationRun = useMemo(
    () => agentRuns.find((run) => run.agentName === 'optimization') || null,
    [agentRuns],
  )

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
                  <>
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
                  {chartData.length === 1 && (
                    <p className="mt-3 text-center text-xs text-text-secondary">
                      Tracking recently started. Trend will develop over time as more snapshots are captured.
                    </p>
                  )}
                </>
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

          {/* SECTION 1: TRACK CAMPAIGN CONTENT */}
          <section className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <SectionHeading
                eyebrow="Content Tracking"
                title="Track Campaign Content"
                description="Register live YouTube videos or Shorts to track real-time audience response, engagement lift, and unit economics."
              />
              {selectedContent && (
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleRefreshContent(selectedContent.id)}
                    disabled={actionLoading[`refresh-${selectedContent.id}`]}
                    className="gap-1.5"
                  >
                    <RefreshCw className={cn('h-3.5 w-3.5', actionLoading[`refresh-${selectedContent.id}`] && 'animate-spin')} />
                    Refresh Metrics
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => openAttributionModal(selectedContent)}
                    className="gap-1.5"
                  >
                    <DollarSign className="h-3.5 w-3.5" />
                    Business Attribution
                  </Button>
                </div>
              )}
            </div>

            {/* Live Creator Verification Banner */}
            <div className="flex items-start sm:items-center gap-3 rounded-[14px] border border-border bg-page/60 px-4 py-3 text-xs sm:text-sm text-text">
              <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5 sm:mt-0" />
              <div>
                <span className="font-semibold text-text">Live Creator Verification:</span> Performance metrics are fetched directly from the YouTube Data API v3 and strictly matched against the selected shortlisted creator's verified YouTube channel.
              </div>
            </div>

            {/* Registration Form */}
            {selectedCampaign && (
              <SectionCard>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Plus className="h-4 w-4 text-primary" /> Register New YouTube Content
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-2 space-y-3">
                  {trackingError && (
                    <div className="flex items-start gap-2.5 rounded-[12px] border border-danger/30 bg-danger-soft/40 p-3 text-xs text-danger">
                      <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-danger" />
                      <span className="font-medium leading-relaxed">{trackingError}</span>
                    </div>
                  )}
                  <form onSubmit={handleStartTracking} className="grid gap-3 sm:grid-cols-12 items-end">
                    <div className="sm:col-span-4">
                      <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1.5">
                        Creator
                      </label>
                      <Select
                        value={trackingInfluencerId}
                        onChange={(e) => {
                          setTrackingInfluencerId(e.target.value)
                          if (trackingError) setTrackingError(null)
                        }}
                        options={
                          creators.length > 0
                            ? creators.map((c) => ({
                                value: c.creator.id,
                                label: `${c.creator.name} (@${c.creator.username})`,
                              }))
                            : [{ value: '', label: 'No creators attached' }]
                        }
                      />
                    </div>
                    <div className="sm:col-span-5">
                      <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1.5">
                        YouTube Video or Short URL
                      </label>
                      <Input
                        placeholder="https://www.youtube.com/watch?v=... or shorts/..."
                        value={trackingUrl}
                        onChange={(e) => {
                          setTrackingUrl(e.target.value)
                          if (trackingError) setTrackingError(null)
                        }}
                      />
                    </div>
                    <div className="sm:col-span-3 flex gap-2">
                      <Button
                        type="submit"
                        disabled={isTrackingSubmitting || !trackingUrl.trim() || !trackingInfluencerId}
                        className="w-full gap-1.5"
                      >
                        {isTrackingSubmitting ? (
                          <>
                            <RefreshCw className="h-4 w-4 animate-spin" /> Tracking...
                          </>
                        ) : (
                          <>
                            <Youtube className="h-4 w-4" /> Start Tracking
                          </>
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </SectionCard>
            )}

            {/* Tracked Content Grid / List */}
            {loadingContent ? (
              <RowSkeleton />
            ) : trackedContents.length > 0 ? (
              <div className="space-y-3">
                {trackedContents.map((content) => {
                  const isSelected = selectedContent?.id === content.id
                  return (
                    <div
                      key={content.id}
                      onClick={() => handleSelectContent(content.id)}
                      className={cn(
                        'cursor-pointer rounded-[16px] border p-4 transition-all duration-200',
                        isSelected
                          ? 'border-primary ring-2 ring-primary/20 bg-surface shadow-md'
                          : 'border-border bg-page/60 hover:bg-surface/80 hover:border-border/80',
                      )}
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-start gap-3.5 min-w-0">
                          {content.thumbnail_url ? (
                            <div className="relative shrink-0 w-24 h-16 rounded-lg overflow-hidden bg-muted border border-border">
                              <img
                                src={content.thumbnail_url}
                                alt={content.title || 'YouTube thumbnail'}
                                className="w-full h-full object-cover"
                              />
                              {content.duration_seconds ? (
                                <span className="absolute bottom-1 right-1 bg-black/80 text-[10px] text-white px-1 py-0.5 rounded font-mono">
                                  {Math.floor(content.duration_seconds / 60)}:
                                  {String(content.duration_seconds % 60).padStart(2, '0')}
                                </span>
                              ) : null}
                            </div>
                          ) : (
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                              <Youtube className="h-6 w-6" />
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant={content.content_type === 'SHORT' ? 'ai' : 'outline'}>
                                {content.content_type || 'VIDEO'}
                              </Badge>
                              {content.performance_status && (
                                <Badge
                                  variant={
                                    content.performance_status === 'STRONG' || content.performance_status === 'OVERPERFORMING'
                                      ? 'success'
                                      : content.performance_status === 'NEEDS_ATTENTION' || content.performance_status === 'UNDERPERFORMING'
                                      ? 'danger'
                                      : 'primary'
                                  }
                                >
                                  {content.performance_status}
                                </Badge>
                              )}
                              {content.momentum && (
                                <Badge variant="outline" className="text-[11px]">
                                  {content.momentum === 'RISING' && '🔥 '}
                                  {content.momentum} MOMENTUM
                                </Badge>
                              )}
                            </div>
                            <h4 className="mt-1 font-semibold text-text truncate max-w-lg text-sm sm:text-base">
                              {content.title || content.content_url}
                            </h4>
                            <p className="text-xs text-text-secondary mt-0.5 flex items-center gap-1.5">
                              <span>Channel: {content.channel_title || 'YouTube'}</span>
                              <span>·</span>
                              <span>Creator: {content.influencer_name || 'Assigned'}</span>
                              {content.content_age_hours != null && (
                                <>
                                  <span>·</span>
                                  <span>{content.content_age_hours < 24 ? `${content.content_age_hours.toFixed(1)}h old` : `${content.content_age_days?.toFixed(0)}d old`}</span>
                                </>
                              )}
                            </p>
                          </div>
                        </div>

                        {/* Snapshot KPIs & Actions */}
                        <div className="flex items-center gap-4 shrink-0 flex-wrap sm:flex-nowrap justify-between md:justify-end">
                          <div className="text-right">
                            <p className="text-xs text-text-secondary uppercase">Views</p>
                            <p className="font-bold text-sm sm:text-base text-text">
                              {formatCompactCount(content.current_views)}
                            </p>
                            {content.performance_lift_percent != null && (
                              <p
                                className={cn(
                                  'text-[11px] font-semibold',
                                  content.performance_lift_percent >= 0 ? 'text-success' : 'text-danger',
                                )}
                              >
                                {content.performance_lift_percent > 0 ? '+' : ''}
                                {content.performance_lift_percent.toFixed(1)}% lift
                              </p>
                            )}
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-text-secondary uppercase">Engagement</p>
                            <p className="font-bold text-sm sm:text-base text-text">
                              {content.engagement_rate != null ? `${content.engagement_rate.toFixed(2)}%` : '—'}
                            </p>
                            <p className="text-[11px] text-text-secondary">
                              {formatCompactCount(content.current_likes)} likes
                            </p>
                          </div>

                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              variant={isSelected ? 'primary' : 'secondary'}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSelectContent(content.id)
                              }}
                            >
                              {isSelected ? 'Selected' : 'Select'}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleRefreshContent(content.id)
                              }}
                              disabled={actionLoading[`refresh-${content.id}`]}
                              title="Refresh metrics from YouTube"
                            >
                              <RefreshCw
                                className={cn('h-3.5 w-3.5', actionLoading[`refresh-${content.id}`] && 'animate-spin')}
                              />
                            </Button>
                            <a
                              href={content.content_url}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center justify-center h-8 w-8 text-text-secondary hover:text-text rounded-md hover:bg-muted"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <SectionCard>
                <CardContent className="py-8 text-center space-y-3">
                  <div className="mx-auto h-12 w-12 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
                    <Clapperboard className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="font-semibold text-text">No YouTube content tracked yet</p>
                    <p className="text-xs text-text-secondary mt-1 max-w-md mx-auto">
                      Paste a public YouTube video or Short URL above to instantly pull real-time views, likes, comments, and calculate creator baseline lifts.
                    </p>
                  </div>
                </CardContent>
              </SectionCard>
            )}
          </section>

          {/* SECTION 2: VIDEO PERFORMANCE (REAL YOUTUBE DATA) */}
          {selectedContent && (
            <section className="space-y-4 animate-fade-in">
              <SectionHeading
                eyebrow="Factual Video Metrics"
                title={`Video Performance: ${selectedContent.title || selectedContent.content_url}`}
                description="Live metrics fetched directly from YouTube Data API and deterministically calculated by Auralytics."
                action={
                  <div className="flex items-center gap-2">
                    <Badge variant="primary">REAL YOUTUBE DATA</Badge>
                    <Badge variant="success">CALCULATED BY AURALYTICS</Badge>
                  </div>
                }
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* 1. Views */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Current Views</p>
                      <Badge variant="primary" className="text-[10px] py-0 px-1.5">REAL YOUTUBE DATA</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.current_views.toLocaleString()}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary flex items-center gap-1">
                      <Eye className="h-3 w-3 text-primary" /> Verified live from YouTube API
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 2. Likes & Comments */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Audience Reactions</p>
                      <Badge variant="primary" className="text-[10px] py-0 px-1.5">REAL YOUTUBE DATA</Badge>
                    </div>
                    <p className="mt-2 text-[24px] font-bold tracking-tight text-text">
                      {formatCompactCount(selectedContent.current_likes)} · {formatCompactCount(selectedContent.current_comments)}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary flex items-center gap-2">
                      <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-rose-500" /> {selectedContent.current_likes.toLocaleString()} likes</span>
                      <span className="flex items-center gap-1"><MessageSquare className="h-3 w-3 text-blue-500" /> {selectedContent.current_comments.toLocaleString()} comments</span>
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 3. Engagement Rate */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Engagement Rate</p>
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">CALCULATED BY AURALYTICS</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.engagement_rate != null ? `${selectedContent.engagement_rate.toFixed(2)}%` : '—'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Formula: (Likes + Comments) / Views × 100
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 4. Creator Baseline */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Creator Baseline</p>
                      <Badge variant="primary" className="text-[10px] py-0 px-1.5">REAL YOUTUBE DATA</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.baseline_median_views != null
                        ? formatCompactCount(selectedContent.baseline_median_views)
                        : 'N/A'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Median of last {selectedContent.baseline_sample_size || 0} public channel videos
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 5. Performance Lift */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Performance Lift</p>
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">CALCULATED BY AURALYTICS</Badge>
                    </div>
                    <p className={cn('mt-2 text-[28px] font-bold tracking-tight', (selectedContent.performance_lift_percent || 0) >= 0 ? 'text-success' : 'text-danger')}>
                      {selectedContent.performance_lift_percent != null
                        ? `${selectedContent.performance_lift_percent > 0 ? '+' : ''}${selectedContent.performance_lift_percent.toFixed(1)}%`
                        : 'N/A'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Lift vs creator's historical median views
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 6. Momentum & Stage */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Momentum & Stage</p>
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">CALCULATED BY AURALYTICS</Badge>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={selectedContent.momentum === 'RISING' ? 'success' : selectedContent.momentum === 'SLOWING' ? 'warning' : 'outline'}>
                        {selectedContent.momentum || 'STABLE'}
                      </Badge>
                      <span className="text-xs font-medium text-text-secondary">
                        Stage: {selectedContent.content_stage || 'EARLY_STAGE'}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-text-secondary">
                      {selectedContent.snapshots && selectedContent.snapshots.length > 1
                        ? `${selectedContent.snapshots[0].views_per_hour?.toFixed(0) || 0} views/hour recently`
                        : 'Tracking snapshot baseline established'}
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 7. Cost Per View (CPV) */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Cost Per View (CPV)</p>
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">CALCULATED BY AURALYTICS</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.cost_per_view != null ? formatINR(selectedContent.cost_per_view) : '—'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Agreed cost ({formatINR(selectedContent.agreed_cost || 0)}) / Views
                    </p>
                  </CardContent>
                </SectionCard>

                {/* 8. Cost Per Engagement (CPE) */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Cost Per Engagement</p>
                      <Badge variant="success" className="text-[10px] py-0 px-1.5">CALCULATED BY AURALYTICS</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.cost_per_engagement != null ? formatINR(selectedContent.cost_per_engagement) : '—'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Agreed cost / (Likes + Comments)
                    </p>
                  </CardContent>
                </SectionCard>
              </div>
            </section>
          )}

          {/* SECTION 3: BUSINESS PERFORMANCE (ATTRIBUTION) */}
          {selectedContent && (
            <section className="space-y-4 animate-fade-in">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <SectionHeading
                  eyebrow="Business Attribution"
                  title="Business Performance & Financial Returns"
                  description="Financial return metrics deterministically calculated from campaign spend and attributed conversions."
                />
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => openAttributionModal(selectedContent)}
                  className="gap-1.5"
                >
                  <DollarSign className="h-3.5 w-3.5" />
                  {selectedContent.attributed_revenue != null ? 'Update Business Attribution' : 'Enter Business Attribution'}
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* Spend */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Deliverable Spend</p>
                      <Badge variant="outline" className="text-[10px] py-0 px-1.5">CONTRACT RECORD</Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {formatINR(selectedContent.agreed_cost || selectedCampaign?.spend || 0)}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Fixed contracted deliverable cost
                    </p>
                  </CardContent>
                </SectionCard>

                {/* Attributed Revenue */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Attributed Revenue</p>
                      <Badge
                        variant={selectedContent.attributed_revenue != null ? 'success' : 'outline'}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {selectedContent.attributed_revenue != null
                          ? (selectedContent.attribution_source || 'ATTRIBUTED BUSINESS DATA')
                          : 'NOT TRACKED'}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.attributed_revenue != null ? formatINR(selectedContent.attributed_revenue) : 'N/A'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      {selectedContent.attributed_orders != null
                        ? `${selectedContent.attributed_orders} orders @ ${formatINR(selectedContent.average_order_value || 0)} AOV`
                        : selectedContent.attributed_revenue != null
                        ? 'Direct revenue entered'
                        : 'No direct revenue attribution recorded'}
                    </p>
                  </CardContent>
                </SectionCard>

                {/* ROAS */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Return on Ad Spend (ROAS)</p>
                      <Badge
                        variant={selectedContent.roas != null ? 'success' : 'outline'}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {selectedContent.roas != null ? 'CALCULATED BY AURALYTICS' : 'NOT TRACKED'}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.roas != null ? `${selectedContent.roas.toFixed(2)}x` : 'N/A'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Formula: Attributed Revenue / Deliverable Spend
                    </p>
                  </CardContent>
                </SectionCard>

                {/* ROI */}
                <SectionCard>
                  <CardContent className="pt-5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase text-text-secondary">Return on Investment (ROI)</p>
                      <Badge
                        variant={selectedContent.roi != null ? 'success' : 'outline'}
                        className="text-[10px] py-0 px-1.5"
                      >
                        {selectedContent.roi != null ? 'CALCULATED BY AURALYTICS' : 'NOT AVAILABLE'}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[28px] font-bold tracking-tight text-text">
                      {selectedContent.roi != null
                        ? `${selectedContent.roi > 0 ? '+' : ''}${selectedContent.roi.toFixed(1)}%`
                        : 'N/A'}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      {selectedContent.attributed_profit != null
                        ? `Profit: ${formatINR(selectedContent.attributed_profit)} (${selectedContent.gross_margin_percent || 0}% margin)`
                        : 'Requires gross profit margin to calculate'}
                    </p>
                  </CardContent>
                </SectionCard>
              </div>
            </section>
          )}

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

          {/* SECTION 4: PERFORMANCE AGENT (AI INTERPRETATION) */}
          <section className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <SectionHeading
                eyebrow="Performance Agent"
                title="Why did this happen?"
                description="AI interpretation explaining what factual YouTube metrics and financial attribution mean for the marketer."
              />
              {selectedContent && (
                <Button
                  onClick={() => handleRunPerformance(selectedContent.id)}
                  disabled={loadingPerformance || campaignCompleted}
                  className="gap-2 shrink-0"
                >
                  <Bot className={cn('h-4 w-4', loadingPerformance && 'animate-spin')} />
                  {loadingPerformance ? 'Analyzing Performance...' : 'Analyze Performance'}
                </Button>
              )}
            </div>

            <SectionCard>
              <CardHeader>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-ai">
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle>Performance Agent Interpretation</CardTitle>
                      <p className="text-xs text-text-secondary">
                        Explains factual data — never performs mathematical guessing or fabrication.
                      </p>
                    </div>
                  </div>
                  {performanceAnalysis && (
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant={
                          performanceAnalysis.status === 'STRONG' || performanceAnalysis.status === 'ON_TRACK'
                            ? 'success'
                            : performanceAnalysis.status === 'NEEDS_ATTENTION' || performanceAnalysis.status === 'UNDERPERFORMING'
                            ? 'danger'
                            : 'ai'
                        }
                      >
                        {performanceAnalysis.status}
                      </Badge>
                      <Badge variant="outline">{performanceAnalysis.content_stage}</Badge>
                      <span className="text-xs text-text-secondary">
                        {(performanceAnalysis.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {!selectedCampaign ? (
                  <SectionEmpty
                    title="Select a campaign to view agent analysis"
                    description="Performance Agent output is stored per campaign run."
                  />
                ) : !selectedContent ? (
                  <SectionEmpty
                    title="No content selected for performance analysis"
                    description="Register or select tracked YouTube content above to run the Performance Agent."
                  />
                ) : !performanceAnalysis ? (
                  <div className="py-8 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-2xl bg-violet-50 text-ai flex items-center justify-center">
                      <Sparkles className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="font-semibold text-text">Performance Agent has not analyzed this content yet</p>
                      <p className="text-xs text-text-secondary mt-1 max-w-md mx-auto">
                        Click "Analyze Performance" to generate an executive interpretation of views, baseline lift, audience engagement, and financial attribution.
                      </p>
                    </div>
                    <Button
                      onClick={() => handleRunPerformance(selectedContent.id)}
                      disabled={loadingPerformance || campaignCompleted}
                      className="gap-2 mt-2"
                    >
                      <Bot className="h-4 w-4" /> Analyze Performance Now
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Summary */}
                    <div className="rounded-[14px] border border-border bg-page/60 p-4 sm:p-5">
                      <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1.5">
                        Marketer Summary
                      </p>
                      <p className="text-sm sm:text-base leading-relaxed text-text font-medium">
                        {performanceAnalysis.summary}
                      </p>
                    </div>

                    {/* What's Working & Needs Attention */}
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="rounded-[14px] border border-emerald-200/60 bg-emerald-50/20 p-4 dark:border-emerald-500/20 dark:bg-emerald-500/5">
                        <div className="flex items-center gap-2 mb-3">
                          <CheckCircle2 className="h-4 w-4 text-success" />
                          <h4 className="text-sm font-semibold text-text">What's Working</h4>
                        </div>
                        {performanceAnalysis.what_is_working?.length > 0 ? (
                          <ul className="space-y-2 text-xs sm:text-sm text-text-secondary">
                            {performanceAnalysis.what_is_working.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="text-success shrink-0 mt-0.5">•</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-text-secondary">No strong positive signals identified yet.</p>
                        )}
                      </div>

                      <div className="rounded-[14px] border border-amber-200/60 bg-amber-50/20 p-4 dark:border-amber-500/20 dark:bg-amber-500/5">
                        <div className="flex items-center gap-2 mb-3">
                          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                          <h4 className="text-sm font-semibold text-text">Needs Attention</h4>
                        </div>
                        {performanceAnalysis.needs_attention?.length > 0 ? (
                          <ul className="space-y-2 text-xs sm:text-sm text-text-secondary">
                            {performanceAnalysis.needs_attention.map((item, idx) => (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="text-amber-500 shrink-0 mt-0.5">•</span>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-text-secondary">No major risks or issues identified.</p>
                        )}
                      </div>
                    </div>

                    {/* Financial Interpretation */}
                    {performanceAnalysis.financial_interpretation && (
                      <div className="rounded-[14px] border border-border bg-page/40 p-4 flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-soft text-primary">
                          <DollarSign className="h-4 w-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                            Financial Interpretation
                          </h4>
                          <p className="text-sm text-text mt-1 leading-relaxed">
                            {performanceAnalysis.financial_interpretation}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Recommended Next Step */}
                    {performanceAnalysis.next_step && (
                      <div className="rounded-[14px] border border-primary/20 bg-primary-soft/30 p-4 flex items-start gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-white">
                          <ArrowRight className="h-4 w-4" />
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold uppercase tracking-wider text-primary">
                            Recommended Next Step
                          </h4>
                          <p className="text-sm font-medium text-text mt-1 leading-relaxed">
                            {performanceAnalysis.next_step}
                          </p>
                        </div>
                      </div>
                    )}

                    <div className="text-right text-[11px] text-text-secondary">
                      Last analyzed {formatRelativeTime(performanceAnalysis.updated_at || performanceAnalysis.created_at)}
                    </div>
                  </div>
                )}
              </CardContent>
            </SectionCard>
          </section>

          {/* SECTION 5: OPTIMIZATION AGENT (ACTIONABLE RECOMMENDATIONS) */}
          <section className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <SectionHeading
                eyebrow="Optimization Agent"
                title="What should we change?"
                description="Maximum 3 evidence-based recommendations connected directly to Approval Center."
              />
              {selectedContent && (
                <Button
                  onClick={() => handleRunOptimization(selectedContent.id)}
                  disabled={loadingOptimization || !performanceAnalysis || campaignCompleted}
                  className="gap-2 shrink-0"
                  variant="primary"
                >
                  <Sparkles className={cn('h-4 w-4', loadingOptimization && 'animate-spin')} />
                  {loadingOptimization
                    ? 'Generating...'
                    : campaignCompleted
                      ? 'Optimization history'
                      : optimizationPlan?.is_stale
                        ? 'Refresh Optimization'
                        : optimizationPlan
                          ? 'Re-run Optimization'
                          : 'Run Optimization Agent'}
                </Button>
              )}
            </div>

            <SectionCard>
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl ai-gradient-bg text-white">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle>Optimization Recommendations</CardTitle>
                      <HumanInTheLoopNote />
                    </div>
                  </div>
                  <Link to="/app/approvals">
                    <Button variant="secondary" size="sm" className="gap-1.5">
                      Approval Center <ArrowRight className="h-3.5 w-3.5" />
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {!performanceAnalysis ? (
                  <div className="py-6 text-center text-xs sm:text-sm text-text-secondary">
                    Run Performance Agent analysis first. The Optimization Agent produces actions based only on verified performance findings.
                  </div>
                ) : !optimizationPlan ? (
                  <div className="py-8 text-center space-y-3">
                    <div className="mx-auto h-12 w-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center">
                      <Sparkles className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="font-semibold text-text">No optimization recommendations yet</p>
                      <p className="text-xs text-text-secondary mt-1 max-w-md mx-auto">
                        Run the Optimization Agent to synthesize at most 3 actionable next steps for budget, format, creator selection, or timing.
                      </p>
                    </div>
                    <Button
                      onClick={() => handleRunOptimization(selectedContent!.id)}
                      disabled={loadingOptimization || campaignCompleted}
                      className="gap-2 mt-2"
                    >
                      <Sparkles className="h-4 w-4" /> Run Optimization Agent
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex flex-col gap-1 text-xs text-text-secondary">
                      {formatStamp(optimizationPlan.optimization_generated_at || optimizationPlan.created_at) && (
                        <p>
                          Optimization Updated:{' '}
                          <span className="font-medium text-text">
                            {formatStamp(optimizationPlan.optimization_generated_at || optimizationPlan.created_at)}
                          </span>
                        </p>
                      )}
                      {formatStamp(optimizationPlan.performance_updated_at || performanceAnalysis.created_at) && (
                        <p>
                          Performance Updated:{' '}
                          <span className="font-medium text-text">
                            {formatStamp(optimizationPlan.performance_updated_at || performanceAnalysis.created_at)}
                          </span>
                        </p>
                      )}
                      {optimizationPlan.overall_assessment && (
                        <p>
                          Assessment:{' '}
                          <span className="font-medium text-text">{optimizationPlan.overall_assessment.replace(/_/g, ' ')}</span>
                          {optimizationPlan.data_quality ? ` · Data ${optimizationPlan.data_quality}` : ''}
                        </p>
                      )}
                    </div>
                    {optimizationPlan.is_stale && !campaignCompleted && (
                      <div className="rounded-[12px] border border-warning/30 bg-amber-50/50 px-3 py-2.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <p className="text-sm text-text">
                          {optimizationPlan.stale_reason || 'New performance data available. Optimization should be refreshed.'}
                        </p>
                        <Button
                          size="sm"
                          onClick={() => handleRunOptimization(selectedContent!.id)}
                          disabled={loadingOptimization}
                          className="gap-1.5 shrink-0"
                        >
                          <RefreshCw className={cn('h-3.5 w-3.5', loadingOptimization && 'animate-spin')} />
                          Refresh Optimization
                        </Button>
                      </div>
                    )}
                    {optimizationPlan.recommendations.length === 0 ? (
                      <p className="text-sm text-text-secondary">
                        Current performance does not justify a campaign change. Continue monitoring.
                      </p>
                    ) : (
                      optimizationPlan.recommendations.slice(0, 3).map((rec, index) => {
                      const apprId = rec.approval_id || rec.id || `opt-${index}`
                      const isPending = rec.status === 'pending'
                      const isApproved = rec.status === 'approved'
                      const isRejected = rec.status === 'rejected'
                      const isModified = rec.status === 'modified'

                      return (
                        <div
                          key={apprId}
                          className={cn(
                            'rounded-[16px] border p-4 sm:p-5 transition-all duration-200',
                            isApproved
                              ? 'border-emerald-200/60 bg-emerald-50/15'
                              : isRejected
                              ? 'border-border/60 bg-page/30 opacity-60'
                              : 'border-border bg-page/60',
                          )}
                        >
                          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                            <div className="flex flex-wrap items-center gap-2">
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
                                {rec.status.toUpperCase()}
                              </Badge>
                            </div>

                            {/* Human Decision Controls */}
                            {isPending ? (
                              <div className="flex items-center gap-2 shrink-0">
                                <Button
                                  size="sm"
                                  variant="primary"
                                  disabled={actionLoading[`decide-${apprId}`]}
                                  onClick={() => handleDecideRecommendation(apprId, 'approved')}
                                  className="gap-1"
                                >
                                  <Check className="h-3.5 w-3.5" /> Approve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  disabled={actionLoading[`decide-${apprId}`]}
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
                                  disabled={actionLoading[`decide-${apprId}`]}
                                  onClick={() => handleDecideRecommendation(apprId, 'rejected')}
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
                          </div>

                          <h4 className="mt-3 text-base font-bold text-text">{rec.action}</h4>
                          <p className="mt-1 text-sm text-text-secondary leading-relaxed">{rec.reason}</p>

                          {rec.evidence?.length > 0 && (
                            <div className="mt-3 rounded-lg bg-surface/80 border border-border p-3">
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
                        </div>
                      )
                    })
                    )}
                    <p className="text-center text-xs text-text-secondary mt-2">
                      Decisions are synced immediately to the Approval Center. Changes are never applied automatically.
                    </p>
                    {!campaignCompleted && (
                      <div className="flex flex-wrap items-center justify-end gap-2 pt-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setCompleteModalOpen(true)}
                        >
                          Complete Campaign
                        </Button>
                      </div>
                    )}
                  </div>
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

      {/* Business Attribution Modal */}
      <Modal
        open={attributionModalOpen}
        onClose={() => setAttributionModalOpen(false)}
        title="Edit Campaign Business Attribution"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setAttributionModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={actionLoading.saveAttribution}
              onClick={handleSaveAttribution}
            >
              {actionLoading.saveAttribution ? 'Saving...' : 'Save & Calculate KPIs'}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-text-secondary">
            Provide business outcomes for this sponsored deliverable. All ROAS and ROI figures are calculated using deterministic Python formulas.
          </p>

          <div className="flex rounded-lg border border-border p-1 bg-muted">
            <button
              type="button"
              onClick={() => setAttrMethod('direct')}
              className={cn(
                'flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors',
                attrMethod === 'direct' ? 'bg-surface shadow text-text' : 'text-text-secondary hover:text-text',
              )}
            >
              Method A: Direct Revenue
            </button>
            <button
              type="button"
              onClick={() => setAttrMethod('orders_aov')}
              className={cn(
                'flex-1 py-1.5 text-xs font-semibold rounded-md transition-colors',
                attrMethod === 'orders_aov' ? 'bg-surface shadow text-text' : 'text-text-secondary hover:text-text',
              )}
            >
              Method B: Orders × AOV
            </button>
          </div>

          {attrMethod === 'direct' ? (
            <div>
              <label className="text-xs font-semibold text-text-secondary block mb-1">
                Attributed Revenue (₹)
              </label>
              <Input
                type="number"
                placeholder="e.g. 250000"
                value={attrRevenue}
                onChange={(e) => setAttrRevenue(e.target.value)}
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-text-secondary block mb-1">
                  Attributed Orders
                </label>
                <Input
                  type="number"
                  placeholder="e.g. 150"
                  value={attrOrders}
                  onChange={(e) => setAttrOrders(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-text-secondary block mb-1">
                  Average Order Value (₹)
                </label>
                <Input
                  type="number"
                  placeholder="e.g. 1200"
                  value={attrAov}
                  onChange={(e) => setAttrAov(e.target.value)}
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-text-secondary block mb-1">
              Gross Margin % (Optional, required for ROI)
            </label>
            <Input
              type="number"
              placeholder="e.g. 40"
              value={attrMargin}
              onChange={(e) => setAttrMargin(e.target.value)}
            />
            <p className="text-[11px] text-text-secondary mt-1">
              Used to deterministically calculate Gross Profit and true Return on Investment (ROI).
            </p>
          </div>
        </div>
      </Modal>

      {/* Modify Recommendation Modal */}
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
                  handleDecideRecommendation(modifyingApprovalId, 'modified', modifyNote)
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
            Note your adjusted instructions, budget cap, or creator specifications. This will be updated on the approval item.
          </p>
          <Input
            placeholder="e.g. Approved with 15% budget cap instead of 25%."
            value={modifyNote}
            onChange={(e) => setModifyNote(e.target.value)}
          />
        </div>
      </Modal>

      <Modal
        open={completeModalOpen}
        onClose={() => setCompleteModalOpen(false)}
        title="Complete Campaign?"
        className="max-w-md"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            The latest Performance and Optimization results will remain available as the final campaign history.
            You can still review this campaign after completion.
          </p>
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setCompleteModalOpen(false)} disabled={completing}>
              Cancel
            </Button>
            <Button onClick={handleCompleteCampaign} disabled={completing} className="gap-2">
              {completing && <RefreshCw className="h-4 w-4 animate-spin" />}
              Complete Campaign
            </Button>
          </div>
        </div>
      </Modal>
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

export function AgentNarrative({
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
