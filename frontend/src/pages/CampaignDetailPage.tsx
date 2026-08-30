import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Calendar,
  Clock,
  Edit3,
  FileText,
  Loader2,
  Mail,
  Sparkles,
  Target,
  Trash2,
  TrendingUp,
  Users,
  Wallet,
  Zap,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Badge,
  Button,
  CampaignJourney,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InfluencerCard,
  Input,
  Modal,
  NextStepCard,
  ProgressBar,
  Select,
  StatusChip,
  Tabs,
  Textarea,
  useToast,
} from '@/components/ui'
import { formatINR, recommendedCampaignCreators, statusLabel } from '@/utils'
import type {
  Campaign,
  CampaignActivity,
  CampaignCreator,
  CampaignStatus,
  CampaignStrategy,
  CampaignWorkflow,
  CampaignWorkflowStep,
} from '@/types'


const tabIds = [
  'overview',
  'strategy',
  'influencers',
  'outreach',
  'contracts',
  'performance',
  'activities',
] as const

type TabId = (typeof tabIds)[number]

const statusOptions: { value: CampaignStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'planning', label: 'Planning' },
  { value: 'draft', label: 'Draft' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'needs_attention', label: 'Needs Attention' },
]

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [activities, setActivities] = useState<CampaignActivity[]>([])
  const [campaignCreators, setCampaignCreators] = useState<CampaignCreator[]>([])
  const [workflow, setWorkflow] = useState<CampaignWorkflow | null>(null)
  const [loading, setLoading] = useState(true)
  const [discoveringCreators, setDiscoveringCreators] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [strategy, setStrategy] = useState<CampaignStrategy | null>(null)
  const [strategyLoading, setStrategyLoading] = useState(false)
  const [strategyRunning, setStrategyRunning] = useState(false)
  const [outreachMessages, setOutreachMessages] = useState<any[]>([])
  const [outreachRunning, setOutreachRunning] = useState(false)
  const discoveringRef = useRef(false)

  // Edit Modal State
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editName, setEditName] = useState('')
  const [editBrand, setEditBrand] = useState('')
  const [editBudget, setEditBudget] = useState(0)
  const [editStatus, setEditStatus] = useState<CampaignStatus>('active')
  const [editObjective, setEditObjective] = useState('')
  const [editStartDate, setEditStartDate] = useState('')
  const [editEndDate, setEditEndDate] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  // Delete Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const visibleCreators = useMemo(
    () => recommendedCampaignCreators(campaignCreators),
    [campaignCreators],
  )

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    setStrategyLoading(true)

    try {
      const [camp, acts, creatorsRes, strat, outrMsgs, wf] = await Promise.all([
        api.campaigns.get(id),
        api.campaigns.getActivities(id).catch(() => []),
        api.discovery.listCreators(id).catch(() => ({ creators: [] as CampaignCreator[] })),
        api.agents.getStrategy(id).catch(() => null),
        api.outreach.list(id).catch(() => []),
        api.campaigns.getWorkflow(id).catch(() => null),
      ])
      const creators = creatorsRes.creators || []
      setCampaign(camp)
      setActivities(acts)
      setCampaignCreators(creators)
      setStrategy(strat)
      setOutreachMessages(outrMsgs || [])
      setWorkflow(wf)
      setEditName(camp.name)
      setEditBrand(camp.brand)
      setEditBudget(camp.budget)
      setEditStatus(camp.status)
      setEditObjective(camp.objective)
      setEditStartDate(camp.startDate)
      setEditEndDate(camp.endDate)
      setEditDescription(camp.description || '')
    } catch (err: any) {
      setError(err.message || 'Failed to load campaign')
    } finally {
      setLoading(false)
      setStrategyLoading(false)
    }
  }

  const handleGenerateStrategy = async () => {
    if (!id) return
    setStrategyRunning(true)
    try {
      const result = await api.agents.runStrategy(id)
      const strategyFailed = result.agentRun?.status === 'FAILED'
      if (strategyFailed) {
        toast({
          type: 'error',
          title: 'Strategy Agent failed',
          description: result.agentRun?.errorMessage || result.message,
        })
      } else {
        toast({
          type: 'success',
          title: 'Strategy generated',
          description: 'AI strategy is saved. Next, discover influencers for this campaign.',
        })
      }
      const strat = await api.agents.getStrategy(id).catch(() => null)
      setStrategy(strat)
      const camp = await api.campaigns.get(id)
      setCampaign(camp)
      const wf = await api.campaigns.getWorkflow(id).catch(() => null)
      setWorkflow(wf)
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Could not run Strategy Agent',
        description: err?.message || 'Check GROQ_API_KEY and try again.',
      })
    } finally {
      setStrategyRunning(false)
    }
  }

  const handleRunOutreachAgent = async (influencerId?: string) => {
    if (!id) return
    setOutreachRunning(true)
    try {
      const result = await api.agents.runOutreach(id, influencerId)
      if (result.agentRun?.status === 'FAILED') {
        toast({
          type: 'error',
          title: 'Outreach Agent failed',
          description: result.agentRun.errorMessage || result.message,
        })
      } else {
        toast({
          type: 'success',
          title: 'Outreach pitch generated',
          description: result.message,
        })
      }
      const outr = await api.outreach.list(id).catch(() => [])
      setOutreachMessages(outr)
      const camp = await api.campaigns.get(id)
      setCampaign(camp)
      const wf = await api.campaigns.getWorkflow(id).catch(() => null)
      setWorkflow(wf)
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Could not run Outreach Agent',
        description: err?.message || 'Failed to generate outreach pitch.',
      })
    } finally {
      setOutreachRunning(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id])

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab && (tabIds as readonly string[]).includes(tab)) {
      setActiveTab(tab as TabId)
    }
  }, [id, searchParams])

  const handleDiscoverForCampaign = async () => {
    if (!id || !campaign || discoveringRef.current) return
    discoveringRef.current = true
    setDiscoveringCreators(true)
    try {
      const res = await api.discovery.discover(id, { refresh: true, limit: 25 })
      if (res.count > 0) {
        toast({
          type: 'success',
          title: 'Creators discovered',
          description: `Acquired ${res.count} creator profiles from YouTube for "${campaign.name}".`,
        })

        const currentStrategy = strategy ?? (await api.agents.getStrategy(id).catch(() => null))
        if (currentStrategy) {
          try {
            const aiResult = await api.agents.runDiscovery(id)
            if (aiResult.agentRun?.status === 'FAILED') {
              toast({
                type: 'error',
                title: 'AI classification failed',
                description:
                  aiResult.agentRun.errorMessage ||
                  'Creator data was retrieved from YouTube, but AI classification failed.',
              })
            } else {
              toast({
                type: 'success',
                title: 'AI ranking complete',
                description: 'Creators ranked using your campaign strategy.',
              })
            }
          } catch (aiErr: any) {
            toast({
              type: 'error',
              title: 'AI classification failed',
              description: aiErr?.message || 'Creator data was retrieved, but AI classification failed.',
            })
          }
        }
      } else {
        toast({
          type: 'info',
          title: 'Discovery finished',
          description: 'No new creators found for this brief.',
        })
      }
      await loadData()
    } catch (err: any) {
      const unauthorized = err?.status === 401
      toast({
        type: 'error',
        title: unauthorized ? 'Session expired' : 'Discovery failed',
        description: unauthorized
          ? 'Please sign in again, then retry Discover Influencers.'
          : err.message || 'Could not fetch creator data.',
      })
    } finally {
      discoveringRef.current = false
      setDiscoveringCreators(false)
    }
  }

  const handleWorkflowStepClick = (step: CampaignWorkflowStep) => {
    if (step.tab && (tabIds as readonly string[]).includes(step.tab)) {
      setActiveTab(step.tab as TabId)
      return
    }
    if (step.route) {
      navigate(step.route)
    }
  }

  const handleNextAction = async () => {
    if (!workflow) return
    const action = workflow.next_action
    const key = action.key

    if (action.tab && (tabIds as readonly string[]).includes(action.tab)) {
      setActiveTab(action.tab as TabId)
    }

    if (key === 'GENERATE_STRATEGY') {
      await handleGenerateStrategy()
      return
    }
    if (key === 'DISCOVER_INFLUENCERS') {
      if (discoveringCreators || discoveringRef.current) return
      await handleDiscoverForCampaign()
      return
    }
    if (key === 'GENERATE_OUTREACH') {
      await handleRunOutreachAgent()
      return
    }
    if (key === 'APPROVE_SHORTLIST') {
      navigate(action.route || '/app/approvals')
    }
  }

  const handleEditSave = async () => {
    if (!id || !campaign) return
    setSavingEdit(true)
    try {
      const updated = await api.campaigns.update(id, {
        name: editName.trim() || campaign.name,
        brand: editBrand.trim() || campaign.brand,
        budget: Number(editBudget) || campaign.budget,
        status: editStatus,
        objective: editObjective.trim() || campaign.objective,
        start_date: editStartDate || campaign.startDate,
        end_date: editEndDate || campaign.endDate,
        description: editDescription.trim() || undefined,
      })
      setCampaign(updated)
      toast({
        type: 'success',
        title: 'Campaign updated',
        description: 'Changes saved successfully to database.',
      })
      setEditModalOpen(false)
      // Refresh activities
      api.campaigns.getActivities(id).then(setActivities).catch(() => {})
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Update failed',
        description: err.message || 'Could not update campaign.',
      })
    } finally {
      setSavingEdit(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!id) return
    setDeleting(true)
    try {
      await api.campaigns.delete(id)
      toast({
        type: 'success',
        title: 'Campaign deleted',
        description: 'Campaign was permanently removed.',
      })
      navigate('/app/campaigns')
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Delete failed',
        description: err.message || 'Could not delete campaign.',
      })
      setDeleting(false)
    }

  }

  if (loading) {
    return (
      <div className="py-24 flex flex-col justify-center items-center gap-3 text-text-secondary text-sm">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p>Loading campaign details...</p>
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="py-16 text-center space-y-4 max-w-md mx-auto">
        <div className="h-12 w-12 rounded-full bg-red-100 text-danger flex items-center justify-center mx-auto">
          <Target className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold">Campaign Not Found</h2>
        <p className="text-sm text-text-secondary">
          {error || 'The requested campaign does not exist or you do not have permission to view it.'}
        </p>
        <Link to="/app/campaigns">
          <Button variant="secondary" className="gap-2 mt-2">
            <ArrowLeft className="h-4 w-4" /> Back to Campaigns
          </Button>
        </Link>
      </div>
    )
  }

  const budgetUsedPct = campaign.budget > 0 ? (campaign.spend / campaign.budget) * 100 : 0
  const campaignStart =
    campaign.startDate || (campaign as { start_date?: string }).start_date || ''
  const campaignEnd =
    campaign.endDate || (campaign as { end_date?: string }).end_date || ''
  const formatDate = (d: string) => {
    if (!d) return 'N/A'
    const parsed = new Date(d.includes('T') ? d : `${d}T00:00:00`)
    if (Number.isNaN(parsed.getTime())) return d
    return parsed.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })
  }

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
      return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    } catch {
      return 'Recently'
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'strategy', label: 'AI Strategy' },
    { id: 'influencers', label: 'Influencers', count: visibleCreators.length },
    { id: 'outreach', label: 'Outreach', count: 0 },
    { id: 'contracts', label: 'Contracts', count: 0 },
    { id: 'performance', label: 'Performance' },
    { id: 'activities', label: 'Activity History', count: activities.length },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <Link to="/app/campaigns">
            <Button variant="ghost" size="icon" aria-label="Back to campaigns">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl sm:text-[28px] font-bold tracking-tight truncate">
                {campaign.name}
              </h1>
              <StatusChip status={campaign.status} />
              <Badge variant={campaign.health === 'excellent' ? 'success' : campaign.health === 'healthy' ? 'primary' : 'danger'}>
                {statusLabel(campaign.health)}
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-text-secondary">
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                {formatDate(campaignStart)} – {formatDate(campaignEnd)}
              </span>
              <span>{campaign.brand}</span>
              <span className="bg-muted px-2 py-0.5 rounded-md text-xs font-semibold">{campaign.objective}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            className="gap-2"
            onClick={() => setEditModalOpen(true)}
          >
            <Edit3 className="h-4 w-4" /> Edit
          </Button>
          <Button
            variant="danger"
            className="gap-2"
            onClick={() => setDeleteModalOpen(true)}
          >
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-secondary">Total Budget</p>
            <Wallet className="h-4 w-4 text-text-secondary" />
          </div>
          <p className="text-xl font-bold mt-1">{formatINR(campaign.budget)}</p>
          <p className="text-xs text-text-secondary mt-1">{Math.round(budgetUsedPct)}% spent</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-secondary">Spend</p>
            <Wallet className="h-4 w-4 text-text-secondary" />
          </div>
          <p className="text-xl font-bold mt-1 text-text">{formatINR(campaign.spend || 0)}</p>
          <p className="text-xs text-text-secondary mt-1">Live expenditure</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-secondary">Revenue</p>
            <TrendingUp className="h-4 w-4 text-success" />
          </div>
          <p className="text-xl font-bold mt-1 text-success">{formatINR(campaign.revenue || 0)}</p>
          <p className="text-xs text-text-secondary mt-1">Direct & attributed</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-secondary">ROAS</p>
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <p className="text-xl font-bold mt-1 text-primary">{(campaign.roas || 0).toFixed(2)}x</p>
          <p className="text-xs text-text-secondary mt-1">Target {campaign.target_roas || 2.5}x</p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text-secondary">Creators</p>
            <Users className="h-4 w-4 text-text-secondary" />
          </div>
          <p className="text-xl font-bold mt-1 text-text">{campaign.influencers || 0}</p>
          <p className="text-xs text-text-secondary mt-1">Partners active</p>
        </Card>
      </div>

      {workflow && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <div>
                <CardTitle>Campaign Journey</CardTitle>
                <p className="text-xs text-text-secondary mt-1">
                  {workflow.progress_percentage}% of the live workflow complete
                </p>
              </div>
            </CardHeader>
            <CardContent>
              <CampaignJourney steps={workflow.steps} onStepClick={handleWorkflowStepClick} />
            </CardContent>
          </Card>
          <NextStepCard
            workflow={workflow}
            busy={strategyRunning || discoveringCreators || outreachRunning}
            onAction={handleNextAction}
          />
        </div>
      )}

      <Tabs tabs={tabs} active={activeTab} onChange={(id) => setActiveTab(id as TabId)} />

      {activeTab === 'overview' && (
        <div className="grid lg:grid-cols-3 gap-6 animate-fade-in">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Campaign Brief</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Description</p>
                <p className="text-sm text-text mt-1 leading-relaxed">
                  {campaign.description || 'No description provided for this campaign.'}
                </p>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 pt-3 border-t border-border">
                <div>
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Target Audience</p>
                  <p className="text-sm font-medium mt-1">
                    {campaign.target_locations || 'All locations'} · Ages {campaign.target_age_min || 18}–{campaign.target_age_max || 45}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Primary Objective</p>
                  <p className="text-sm font-medium mt-1">{campaign.objective}</p>
                </div>
              </div>

              <div className="pt-3 border-t border-border">
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">Platforms & Channels</p>
                <div className="flex flex-wrap gap-2">
                  {campaign.platforms && campaign.platforms.length > 0 ? (
                    campaign.platforms.map((p) => (
                      <span
                        key={p}
                        className="px-3 py-1 rounded-full text-xs font-semibold bg-primary-soft text-primary border border-primary/20 capitalize"
                      >
                        {p}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-text-secondary">Instagram, YouTube</span>
                  )}
                </div>
              </div>

              {campaign.creator_tiers && campaign.creator_tiers.length > 0 && (
                <div className="pt-3 border-t border-border">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                    User-selected creator tiers
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {campaign.creator_tiers.map((tier) => (
                      <span
                        key={tier}
                        className="px-3 py-1 rounded-full text-xs font-semibold bg-primary-soft text-primary border border-primary/20 capitalize"
                      >
                        {tier}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {campaign.budget_allocation && campaign.budget_allocation.length > 0 && (
                <div className="pt-3 border-t border-border">
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                    Approved Budget Allocation
                  </p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {campaign.budget_allocation.map((b) => (
                      <div key={b.id || b.label} className="p-2.5 rounded-lg border border-border bg-page/40">
                        <div className="flex justify-between text-xs font-semibold">
                          <span>{b.label}</span>
                          <span className="text-primary">{formatINR(b.amount)}</span>
                        </div>
                        {b.rationale && <p className="text-[11px] text-text-secondary mt-0.5">{b.rationale}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Key Performance Indicators</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-border p-4 bg-page/50">
                <p className="text-xs text-text-secondary">Primary KPI</p>
                <p className="text-lg font-bold text-text mt-0.5">{campaign.primary_kpi || 'ROAS'}</p>
                <p className="text-xs text-text-secondary mt-1">
                  Target: {campaign.target_roas || 3.0}x ROAS
                </p>
              </div>

              <div className="space-y-2 pt-2">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary">Budget Utilization</span>
                  <span className="font-semibold">{Math.round(budgetUsedPct)}%</span>
                </div>
                <ProgressBar value={Math.round(budgetUsedPct)} size="sm" />
              </div>

              <div className="space-y-2 pt-2">
                <div className="flex justify-between text-xs">
                  <span className="text-text-secondary">Campaign Progress</span>
                  <span className="font-semibold">{campaign.progress || 0}%</span>
                </div>
                <ProgressBar value={campaign.progress || 0} size="sm" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'strategy' && (
        <Card className="animate-fade-in">
          <CardContent className="py-8 space-y-4">
            {strategyLoading ? (
              <div className="py-8 text-center text-text-secondary">
                <Loader2 className="h-6 w-6 mx-auto animate-spin mb-2" />
                Loading strategy…
              </div>
            ) : strategy?.strategyJson ? (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-ai" />
                      <h3 className="text-base font-semibold text-text">AI Strategy</h3>
                      <Badge variant="ai">v{strategy.version}</Badge>
                    </div>
                    <p className="text-xs text-text-secondary mt-1">
                      {campaign.workflow_state === 'FAILED'
                        ? 'Strategy saved · Generated by Strategy Agent'
                        : `Workflow: ${campaign.workflow_state || campaign.workflowState || 'STRATEGY_COMPLETED'} · Generated by Strategy Agent`}
                    </p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={handleGenerateStrategy} disabled={strategyRunning}>
                    {strategyRunning ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Regenerating…
                      </>
                    ) : (
                      'Regenerate Strategy'
                    )}
                  </Button>
                </div>
                <p className="text-sm text-text">{String(strategy.strategyJson.campaign_summary || '')}</p>
                {(campaign.creator_tiers?.length || strategy.strategyJson.user_selected_creator_tiers) && (
                  <div>
                    <p className="text-xs font-semibold text-text mb-2">User selected</p>
                    <div className="flex flex-wrap gap-2">
                      {(strategy.strategyJson.user_selected_creator_tiers || campaign.creator_tiers || []).map(
                        (tier: string) => (
                          <Badge key={tier} variant="outline" className="capitalize">
                            ✓ {tier}
                          </Badge>
                        ),
                      )}
                    </div>
                  </div>
                )}
                {Array.isArray(strategy.strategyJson.recommended_creator_strategy) &&
                  strategy.strategyJson.recommended_creator_strategy.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-2">AI strategy</p>
                      <div className="flex flex-wrap gap-2">
                        {strategy.strategyJson.recommended_creator_strategy.map((item: any, idx: number) => (
                          <Badge key={idx} variant="ai" className="capitalize">
                            {item.tier}: {item.priority || 'HIGH'}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                {Array.isArray(strategy.strategyJson.budget_strategy?.tier_allocations) &&
                  strategy.strategyJson.budget_strategy.tier_allocations.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-2">Tier budget pools</p>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {strategy.strategyJson.budget_strategy.tier_allocations.map((item: any, idx: number) => (
                          <div key={idx} className="p-2.5 rounded-lg border border-border bg-page/40">
                            <div className="flex justify-between text-xs font-semibold capitalize">
                              <span>{item.tier}</span>
                              <span className="text-primary">
                                {item.percentage}%
                                {typeof item.amount === 'number' ? ` · ${formatINR(item.amount)}` : ''}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                {Array.isArray(strategy.strategyJson.budget_limitations) &&
                  strategy.strategyJson.budget_limitations.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-2">Budget constraints</p>
                      <ul className="list-disc pl-5 text-sm text-text-secondary space-y-1">
                        {strategy.strategyJson.budget_limitations.map((line: string, idx: number) => (
                          <li key={idx}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                {Array.isArray(strategy.strategyJson.optional_recommendations) &&
                  strategy.strategyJson.optional_recommendations.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-2">Optional AI recommendation</p>
                      <ul className="list-disc pl-5 text-sm text-text-secondary space-y-1">
                        {strategy.strategyJson.optional_recommendations.map((item: any, idx: number) => (
                          <li key={idx}>
                            {item.tier ? `${item.tier}: ` : ''}
                            {item.reason || item.type}
                            {item.requires_user_approval ? ' — requires user approval' : ''}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {Array.isArray(strategy.strategyJson.recommended_platform_mix) && (
                  <div>
                    <p className="text-xs font-semibold text-text mb-2">Platform mix</p>
                    <div className="flex flex-wrap gap-2">
                      {strategy.strategyJson.recommended_platform_mix.map((item: any, idx: number) => (
                        <Badge key={idx} variant="outline">
                          {item.platform}: {item.percentage}%
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {Array.isArray(strategy.strategyJson.content_strategy) && strategy.strategyJson.content_strategy.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-text mb-2">Content strategy</p>
                    <ul className="list-disc pl-5 text-sm text-text-secondary space-y-1">
                      {strategy.strategyJson.content_strategy.map((line: string, idx: number) => (
                        <li key={idx}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Array.isArray(strategy.strategyJson.risks) && strategy.strategyJson.risks.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-text mb-2">Risks</p>
                    <ul className="list-disc pl-5 text-sm text-text-secondary space-y-1">
                      {strategy.strategyJson.risks.map((line: string, idx: number) => (
                        <li key={idx}>{line}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {strategy.strategyJson.reasoning && (
                  <p className="text-xs text-text-secondary border-t border-border pt-3">
                    {String(strategy.strategyJson.reasoning)}
                  </p>
                )}
              </div>
            ) : (
              <div className="py-8 text-center text-text-secondary space-y-3">
                <Sparkles className="h-10 w-10 mx-auto text-ai/40" />
                <h3 className="text-base font-semibold text-text">AI strategy not generated yet</h3>
                <p className="text-xs mt-1 max-w-sm mx-auto">
                  Supervisor will run the Strategy Agent using your real campaign brief and Groq. No fabricated metrics.
                </p>
                <Button size="sm" onClick={handleGenerateStrategy} disabled={strategyRunning}>
                  {strategyRunning ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Generating strategy…
                    </>
                  ) : (
                    'Generate Strategy'
                  )}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'influencers' && (
        <div className="space-y-4 animate-fade-in">
          {visibleCreators.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-text-secondary space-y-3">
                <Users className="h-10 w-10 mx-auto text-text-secondary/40" />
                <div>
                  <h3 className="text-base font-semibold text-text">No creators discovered for this campaign yet</h3>
                  <p className="text-xs mt-1 max-w-md mx-auto">
                    Acquire real creator data from YouTube based on this campaign's target niche ({campaign.interests?.join(', ') || campaign.objective || 'Skincare'}).
                  </p>
                </div>
                <div className="pt-2 flex items-center justify-center gap-3">
                  <Button
                    size="sm"
                    onClick={handleDiscoverForCampaign}
                    disabled={discoveringCreators}
                    className="gap-1.5"
                  >
                    {discoveringCreators ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        <span>Discovering YouTube Creators...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>Discover Creators from YouTube</span>
                      </>
                    )}
                  </Button>
                  <Link to="/app/discovery">
                    <Button size="sm" variant="secondary" className="gap-1.5">
                      <Users className="h-3.5 w-3.5" /> Discovery Center
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-text">Discovered Creators ({visibleCreators.length})</h3>
                  <p className="text-xs text-text-secondary">Matching campaign audience and target keywords</p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleDiscoverForCampaign}
                  disabled={discoveringCreators}
                  className="gap-1.5"
                >
                  {discoveringCreators ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  <span>Re-scan YouTube</span>
                </Button>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {visibleCreators.map((link) => (
                    <InfluencerCard
                    key={link.creator.id}
                    influencer={{
                      ...link.creator,
                      shortlisted: link.status === 'SHORTLISTED' || link.creator.shortlisted,
                    }}
                    matchScore={link.match_score}
                    matchReasons={link.match_reasons}
                    shortlistLabel={link.status === 'SHORTLISTED' ? 'Shortlisted' : 'Shortlist'}
                    onShortlist={async (infId) => {
                      if (!id) return
                      const nextStatus = link.status === 'SHORTLISTED' ? 'DISCOVERED' : 'SHORTLISTED'
                      try {
                        await api.discovery.setStatus(id, infId, nextStatus)
                        await loadData()
                      } catch (err: any) {
                        toast({
                          type: 'error',
                          title: 'Could not update shortlist',
                          description: err?.message || 'The change was not saved. Please try again.',
                        })
                      }
                    }}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === 'outreach' && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-text">Outreach Proposals ({outreachMessages.length})</h3>
              <p className="text-xs text-text-secondary">AI-personalized collaboration messages for shortlisted creators</p>
            </div>
            <Button
              size="sm"
              onClick={() => handleRunOutreachAgent()}
              disabled={outreachRunning}
              className="gap-1.5"
            >
              {outreachRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              <span>{outreachMessages.length > 0 ? 'Regenerate Outreach' : 'Run Outreach Agent'}</span>
            </Button>
          </div>

          {outreachMessages.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-text-secondary space-y-3">
                <Mail className="h-10 w-10 mx-auto text-text-secondary/40" />
                <div>
                  <h3 className="text-base font-semibold text-text">No outreach proposals generated yet</h3>
                  <p className="text-xs mt-1 max-w-md mx-auto">
                    Outreach Agent will consume Discovery recommendations and generate personalized email and DM pitches for your shortlisted creators.
                  </p>
                </div>
                <Button
                  size="sm"
                  onClick={() => handleRunOutreachAgent()}
                  disabled={outreachRunning}
                  className="gap-1.5 mt-2"
                >
                  {outreachRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                  <span>Generate Outreach Pitches</span>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {outreachMessages.map((msg) => (
                <Card key={msg.id} className="p-4 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border pb-3">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-full bg-primary-soft text-primary flex items-center justify-center font-bold text-sm">
                        {(msg.influencerName || msg.influencer_name || 'C')[0]}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text text-sm">
                            {msg.influencerName || msg.influencer_name}
                          </span>
                          <Badge variant="outline" className="text-[11px]">
                            @{msg.influencerUsername || msg.influencer_username}
                          </Badge>
                          <StatusChip status={msg.status || 'READY'} />
                        </div>
                        <p className="text-xs text-text-secondary mt-0.5">
                          Channel: <span className="font-medium text-text">{msg.channel || 'EMAIL'}</span>
                        </p>
                      </div>
                    </div>
                    <Link to="/app/outreach">
                      <Button size="sm" variant="secondary" className="gap-1">
                        View in Outreach Hub
                      </Button>
                    </Link>
                  </div>

                  {msg.subject && (
                    <div>
                      <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Subject Line</p>
                      <p className="text-xs font-medium text-text mt-0.5">{msg.subject}</p>
                    </div>
                  )}

                  <div>
                    <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Personalized Pitch</p>
                    <div className="p-3 rounded-lg border border-border bg-page/60 text-xs text-text font-mono whitespace-pre-wrap mt-1 max-h-40 overflow-y-auto leading-relaxed">
                      {msg.body || msg.message}
                    </div>
                  </div>

                  {msg.shortDm && (
                    <div>
                      <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Short Social DM</p>
                      <div className="p-2.5 rounded-lg border border-border bg-page/40 text-xs text-text font-mono mt-1">
                        {msg.shortDm}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'contracts' && (
        <Card className="animate-fade-in">
          <CardContent className="py-12 text-center text-text-secondary">
            <FileText className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
            <h3 className="text-base font-semibold text-text">No contracts generated yet</h3>
            <p className="text-xs mt-1 max-w-sm mx-auto">
              Contract Agent will draft agreements with AI risk protection when creators accept terms.
            </p>
          </CardContent>
        </Card>
      )}

      {activeTab === 'performance' && (
        <Card className="animate-fade-in">
          <CardContent className="py-12 text-center text-text-secondary">
            <TrendingUp className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
            <h3 className="text-base font-semibold text-text">No live performance metrics yet</h3>
            <p className="text-xs mt-1 max-w-sm mx-auto">
              Performance metrics (ROAS, conversions, reel impressions) will be tracked live as creators publish content.
            </p>
          </CardContent>
        </Card>
      )}

      {activeTab === 'activities' && (
        <Card className="animate-fade-in">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Campaign Activity History</CardTitle>
              <span className="text-xs text-text-secondary font-mono">{activities.length} recorded events</span>
            </div>
          </CardHeader>
          <CardContent>
            {activities.length === 0 ? (
              <div className="text-center py-8 text-text-secondary">
                <Clock className="h-8 w-8 mx-auto text-text-secondary/40 mb-2" />
                <p className="text-sm font-semibold text-text">No activity recorded yet</p>
                <p className="text-xs mt-1">Actions performed on this campaign will appear in this timeline.</p>
              </div>
            ) : (
              <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                {activities.map((act) => (
                  <div key={act.id} className="relative flex items-start gap-3">
                    <div className="absolute -left-6 mt-1 h-5 w-5 rounded-full border-2 border-white bg-primary flex items-center justify-center">
                      <Zap className="h-2.5 w-2.5 text-white" />
                    </div>
                    <div className="flex-1 rounded-xl border border-border bg-page/40 p-3 text-xs">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-semibold text-text">{act.title}</span>
                        <span className="text-[11px] text-text-secondary font-mono">
                          {formatActivityTime(act.created_at)}
                        </span>
                      </div>
                      {act.description && <p className="text-text-secondary">{act.description}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Edit Campaign Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Campaign"
        className="max-w-xl"
      >
        <div className="space-y-4 pt-1">
          <Input
            label="Campaign Name"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
          <div className="grid sm:grid-cols-2 gap-3">
            <Input
              label="Brand"
              value={editBrand}
              onChange={(e) => setEditBrand(e.target.value)}
            />
            <Select
              label="Status"
              options={statusOptions}
              value={editStatus}
              onChange={(e) => setEditStatus(e.target.value as CampaignStatus)}
            />
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <Input
              label="Budget (INR)"
              type="number"
              min={0}
              value={editBudget}
              onChange={(e) => setEditBudget(Number(e.target.value) || 0)}
            />
            <Input
              label="Primary Objective"
              value={editObjective}
              onChange={(e) => setEditObjective(e.target.value)}
            />
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <Input
              label="Start Date"
              type="date"
              value={editStartDate}
              onChange={(e) => setEditStartDate(e.target.value)}
            />
            <Input
              label="End Date"
              type="date"
              value={editEndDate}
              onChange={(e) => setEditEndDate(e.target.value)}
            />
          </div>
          <Textarea
            label="Description"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            rows={3}
          />

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
            <Button
              variant="secondary"
              onClick={() => setEditModalOpen(false)}
              disabled={savingEdit}
            >
              Cancel
            </Button>
            <Button
              onClick={handleEditSave}
              disabled={savingEdit}
              className="gap-2"
            >
              {savingEdit && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        title="Delete Campaign?"
        className="max-w-md"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            Are you sure you want to delete <span className="font-semibold text-text">{campaign.name}</span>?
            This action cannot be undone. All recorded campaign activity will also be removed.
          </p>
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => setDeleteModalOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="gap-2"
            >
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete Campaign
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
