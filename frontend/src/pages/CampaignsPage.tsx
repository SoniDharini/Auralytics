import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Calendar,
  Filter,
  FolderPlus,
  Loader2,
  Plus,
  Search,
  Trash2,
  Users,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Button,
  Card,
  CardContent,
  Modal,
  ProgressBar,
  StatusChip,
  useToast,
} from '@/components/ui'
import { PageAmbientBackground, PageHeader } from '@/components/brand/VisualSystem'
import type { Campaign, CampaignStatus, CampaignWorkflow } from '@/types'
import { cn, formatINR } from '@/utils'

const statusFilters: { value: CampaignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'planning', label: 'Planning' },
  { value: 'draft', label: 'Draft' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'needs_attention', label: 'Needs Attention' },
]

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
  return a || b || null
}

export function CampaignsPage() {
  const { toast } = useToast()

  const [campaignsList, setCampaignsList] = useState<Campaign[]>([])
  const [workflows, setWorkflows] = useState<Record<string, CampaignWorkflow>>({})
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all')

  const [deleteTarget, setDeleteTarget] = useState<Campaign | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadCampaigns = () => {
    setLoading(true)
    api.campaigns
      .list()
      .then(async (data) => {
        const list = data ?? []
        setCampaignsList(list)
        const entries = await Promise.all(
          list.map(async (c) => {
            const wf = await api.campaigns.getWorkflow(c.id).catch(() => null)
            return wf ? ([c.id, wf] as const) : null
          }),
        )
        const map: Record<string, CampaignWorkflow> = {}
        entries.forEach((entry) => {
          if (entry) map[entry[0]] = entry[1]
        })
        setWorkflows(map)
      })
      .catch(() => {
        setCampaignsList([])
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    loadCampaigns()
  }, [])

  const filtered = useMemo(() => {
    return campaignsList.filter((c) => {
      const matchesSearch =
        !search ||
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.brand.toLowerCase().includes(search.toLowerCase())
      const matchesStatus = statusFilter === 'all' || c.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [campaignsList, search, statusFilter])

  const totals = useMemo(() => {
    const active = campaignsList.filter((c) => c.status === 'active').length
    const budget = campaignsList.reduce((s, c) => s + (c.budget || 0), 0)
    const spend = campaignsList.reduce((s, c) => s + (c.spend || 0), 0)
    const revenue = campaignsList.reduce((s, c) => s + (c.revenue || 0), 0)
    const avgRoas = spend > 0 ? revenue / spend : 0
    return { active, budget, spend, revenue, avgRoas }
  }, [campaignsList])

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.campaigns.delete(deleteTarget.id)
      setCampaignsList((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      toast({
        type: 'success',
        title: 'Campaign deleted',
        description: `Campaign '${deleteTarget.name}' was successfully deleted.`,
      })
      setDeleteTarget(null)
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Deletion failed',
        description: err.message || 'Could not delete campaign.',
      })
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="relative space-y-5 animate-fade-in">
      <PageAmbientBackground variant="campaigns" className="h-[360px]" />

      <PageHeader
        eyebrow="Workspace"
        title="Campaigns"
        description="Manage and monitor influencer marketing campaigns."
        actions={
          <Link to="/app/campaigns/new">
            <Button size="lg" className="gap-2 w-full sm:w-auto">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </Link>
        }
      />

      <div className="relative grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-3.5">
          <p className="text-[11px] text-text-secondary font-medium">Active</p>
          <p className="text-[22px] font-bold mt-1 text-text">{totals.active}</p>
          <p className="text-[11px] text-text-secondary mt-1">{campaignsList.length} total</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[11px] text-text-secondary font-medium">Allocated</p>
          <p className="text-[22px] font-bold mt-1 text-text">{formatINR(totals.budget)}</p>
          <p className="text-[11px] text-text-secondary mt-1">{formatINR(totals.spend)} spent</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[11px] text-text-secondary font-medium">Revenue</p>
          <p className="text-[22px] font-bold mt-1 text-success">{formatINR(totals.revenue)}</p>
          <p className="text-[11px] text-text-secondary mt-1">From campaign records</p>
        </Card>
        <Card className="p-3.5">
          <p className="text-[11px] text-text-secondary font-medium">Avg ROAS</p>
          <p className="text-[22px] font-bold mt-1 text-primary">{totals.avgRoas.toFixed(2)}x</p>
          <p className="text-[11px] text-text-secondary mt-1">Revenue ÷ spend</p>
        </Card>
      </div>

      <div className="relative flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns by name or brand..."
            className="w-full h-10 pl-10 pr-4 rounded-[12px] border border-border bg-surface text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 text-text transition"
          />
        </div>
      </div>

      <div className="relative flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-text-secondary mr-1 flex items-center gap-1">
          <Filter className="h-3.5 w-3.5" /> Status
        </span>
        {statusFilters.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              'px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200',
              statusFilter === f.value
                ? 'bg-primary-soft border-primary/30 text-primary font-semibold shadow-xs'
                : 'bg-surface border-border text-text-secondary hover:bg-muted',
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="relative py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span>Loading campaigns...</span>
        </div>
      )}

      {!loading && campaignsList.length === 0 && (
        <div className="relative py-14 text-center border border-dashed border-border rounded-[18px] bg-surface/80 p-8 space-y-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
            <FolderPlus className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text">No campaigns yet</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Create your first campaign to start discovering creators with Auralytics.
            </p>
          </div>
          <Link to="/app/campaigns/new">
            <Button size="lg" className="gap-2 mt-2">
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </Link>
        </div>
      )}

      {!loading && campaignsList.length > 0 && filtered.length === 0 && (
        <div className="relative py-12 text-center text-text-secondary">
          <p className="font-semibold text-text">No campaigns found</p>
          <p className="text-xs mt-1">No campaigns matched your current search and filter criteria.</p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="relative grid md:grid-cols-2 xl:grid-cols-3 gap-3.5">
          {filtered.map((c) => {
            const dates = formatDateRange(c.startDate, c.endDate)
            const stage =
              workflows[c.id]?.steps?.find((s) => s.status === 'CURRENT' || s.status === 'NEXT')?.label ||
              workflows[c.id]?.next_action?.label
            return (
              <Card
                key={c.id}
                className="ui-card-hover overflow-hidden relative group"
              >
                <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-primary via-accent to-primary/40 opacity-80" />
                <CardContent className="p-4 pl-5 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] text-text-secondary font-medium truncate">{c.brand}</p>
                      <Link
                        to={`/app/campaigns/${c.id}`}
                        className="font-semibold text-sm text-text hover:text-primary transition truncate block mt-0.5"
                      >
                        {c.name}
                      </Link>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <StatusChip status={c.status} />
                      <button
                        onClick={() => setDeleteTarget(c)}
                        className="text-text-secondary hover:text-danger p-1 rounded-lg transition"
                        title="Delete Campaign"
                        aria-label={`Delete ${c.name}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-text-secondary">
                    {dates && (
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {dates}
                      </span>
                    )}
                    {typeof c.budget === 'number' && c.budget > 0 && (
                      <>
                        {dates && <span>·</span>}
                        <span>{formatINR(c.budget)}</span>
                      </>
                    )}
                    <span>·</span>
                    <span className="inline-flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      {c.influencers || 0}
                    </span>
                  </div>

                  {stage && (
                    <p className="text-[11px] font-medium text-primary/90 truncate">Stage · {stage}</p>
                  )}

                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="text-text-secondary">Budget used</span>
                      <span className="font-semibold text-text">
                        {formatINR(c.spend)} / {formatINR(c.budget)}
                      </span>
                    </div>
                    <ProgressBar
                      value={Math.round((c.spend / (c.budget || 1)) * 100 || 0)}
                      size="sm"
                    />
                  </div>

                  <div className="pt-2 border-t border-border flex items-center justify-between text-xs">
                    <span className="text-text-secondary font-medium">Next</span>
                    <Link
                      to={workflows[c.id]?.next_action.route || `/app/campaigns/${c.id}`}
                      className="font-semibold text-primary hover:underline truncate max-w-[70%] text-right"
                    >
                      {workflows[c.id]?.next_action.label || 'View details'} →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Modal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete Campaign?"
        className="max-w-md"
      >
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            Are you sure you want to delete{' '}
            <span className="font-semibold text-text">{deleteTarget?.name}</span>? This action cannot
            be undone and all campaign activities will be permanently removed.
          </p>
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>
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
