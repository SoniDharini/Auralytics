import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
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
  CardHeader,
  Modal,
  ProgressBar,
  StatusChip,
  useToast,
} from '@/components/ui'
import type { Campaign, CampaignStatus } from '@/types'
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

export function CampaignsPage() {
  const { toast } = useToast()

  const [campaignsList, setCampaignsList] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all')

  // Deletion modal state
  const [deleteTarget, setDeleteTarget] = useState<Campaign | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadCampaigns = () => {
    setLoading(true)
    api.campaigns
      .list()
      .then((data) => {
        setCampaignsList(data ?? [])
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
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Campaigns</h1>
          <p className="text-text-secondary mt-1">
            Manage and monitor all influencer marketing campaigns.
          </p>
        </div>
        <Link to="/app/campaigns/new">
          <Button size="lg" className="gap-2 w-full sm:w-auto">
            <Plus className="h-4 w-4" /> Create Campaign
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-xs text-text-secondary font-medium">Active Campaigns</p>
          <p className="text-2xl font-bold mt-1 text-text">{totals.active}</p>
          <p className="text-xs text-text-secondary mt-1">Across all brands</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary font-medium">Total Allocated</p>
          <p className="text-2xl font-bold mt-1 text-text">{formatINR(totals.budget)}</p>
          <p className="text-xs text-text-secondary mt-1">{formatINR(totals.spend)} spent</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary font-medium">Total Revenue</p>
          <p className="text-2xl font-bold mt-1 text-success">{formatINR(totals.revenue)}</p>
          <p className="text-xs text-text-secondary mt-1">Direct & attributed</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-text-secondary font-medium">Average ROAS</p>
          <p className="text-2xl font-bold mt-1 text-primary">{totals.avgRoas.toFixed(2)}x</p>
          <p className="text-xs text-text-secondary mt-1">Target 2.5x</p>
        </Card>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns by name or brand..."
            className="w-full h-10 pl-10 pr-4 rounded-[10px] border border-border bg-white text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-text-secondary mr-1 flex items-center gap-1">
          <Filter className="h-3.5 w-3.5" /> Status:
        </span>
        {statusFilters.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={cn(
              'px-3 py-1.5 rounded-full text-xs font-medium border transition',
              statusFilter === f.value
                ? 'bg-primary-soft border-primary/30 text-primary font-semibold'
                : 'bg-white border-border text-text-secondary hover:bg-muted',
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="py-12 flex justify-center items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span>Loading campaigns...</span>
        </div>
      )}

      {!loading && campaignsList.length === 0 && (
        <div className="py-16 text-center border border-dashed border-border rounded-2xl bg-white p-8 space-y-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
            <FolderPlus className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text">No campaigns yet</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Create your first campaign to start managing influencers with InfluenceOS.
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
        <div className="py-12 text-center text-text-secondary">
          <p className="font-semibold text-text">No campaigns found</p>
          <p className="text-xs mt-1">No campaigns matched your current search and filter criteria.</p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {filtered.map((c) => (
            <Card key={c.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-text-secondary font-medium">{c.brand}</p>
                    <Link
                      to={`/app/campaigns/${c.id}`}
                      className="font-bold text-base text-text hover:text-primary transition truncate block mt-0.5"
                    >
                      {c.name}
                    </Link>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusChip status={c.status} />
                    <button
                      onClick={() => setDeleteTarget(c)}
                      className="text-text-secondary hover:text-danger p-1 rounded transition"
                      title="Delete Campaign"
                      aria-label={`Delete ${c.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-text-secondary font-medium">Budget Spent</span>
                    <span className="font-semibold text-text">
                      {formatINR(c.spend)} / {formatINR(c.budget)} (
                      {Math.round((c.spend / (c.budget || 1)) * 100 || 0)}%)
                    </span>
                  </div>
                  <ProgressBar
                    value={Math.round((c.spend / (c.budget || 1)) * 100 || 0)}
                    size="sm"
                  />
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border text-center">
                  <div>
                    <p className="text-[11px] text-text-secondary">ROAS</p>
                    <p
                      className={cn(
                        'text-sm font-bold mt-0.5',
                        c.roas >= 2.5 ? 'text-success' : 'text-text',
                      )}
                    >
                      {(c.roas || 0).toFixed(2)}x
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] text-text-secondary">Revenue</p>
                    <p className="text-sm font-bold text-text mt-0.5">{formatINR(c.revenue || 0)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] text-text-secondary">Creators</p>
                    <p className="text-sm font-bold text-text mt-0.5 flex items-center justify-center gap-1">
                      <Users className="h-3.5 w-3.5 text-text-secondary" />
                      {c.influencers || 0}
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-border flex items-center justify-between text-xs text-text-secondary">
                  <span className="truncate max-w-[160px]">{c.objective}</span>
                  <Link
                    to={`/app/campaigns/${c.id}`}
                    className="font-semibold text-primary hover:underline"
                  >
                    View details →
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete confirmation modal */}
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
            <Button
              variant="secondary"
              onClick={() => setDeleteTarget(null)}
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
