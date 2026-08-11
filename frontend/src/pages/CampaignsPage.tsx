import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Filter, Loader2, Plus, Search, Users } from 'lucide-react'
import { api } from '@/services/api'
import { campaigns as fallbackCampaigns } from '@/mock-data'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  ProgressBar,
  StatusChip,
} from '@/components/ui'
import type { Campaign, CampaignStatus } from '@/types'
import { cn, formatINR } from '@/utils'

const statusFilters: { value: CampaignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'planning', label: 'Planning' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'needs_attention', label: 'Needs Attention' },
]

export function CampaignsPage() {
  const [campaignsList, setCampaignsList] = useState<Campaign[]>(fallbackCampaigns)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all')

  useEffect(() => {
    let mounted = true
    api.campaigns
      .list()
      .then((data) => {
        if (mounted && data && data.length > 0) {
          setCampaignsList(data)
        }
      })
      .catch(() => {
        // keep fallback
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
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
    const budget = campaignsList.reduce((s, c) => s + c.budget, 0)
    const spend = campaignsList.reduce((s, c) => s + c.spend, 0)
    const revenue = campaignsList.reduce((s, c) => s + c.revenue, 0)
    const avgRoas = spend > 0 ? revenue / spend : 0
    return { active, budget, spend, revenue, avgRoas }
  }, [campaignsList])

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
        <div className="py-8 flex justify-center items-center gap-2 text-text-secondary text-sm">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <span>Loading campaigns...</span>
        </div>
      )}

      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
        {filtered.map((c) => (
          <Card key={c.id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs text-text-secondary font-medium">{c.brand}</p>
                  <Link
                    to={`/app/campaigns/${c.id}`}
                    className="font-bold text-base text-text hover:text-primary transition truncate block mt-0.5"
                  >
                    {c.name}
                  </Link>
                </div>
                <StatusChip status={c.status} />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-text-secondary font-medium">Budget Spent</span>
                  <span className="font-semibold text-text">
                    {formatINR(c.spend)} / {formatINR(c.budget)} ({Math.round((c.spend / c.budget) * 100 || 0)}%)
                  </span>
                </div>
                <ProgressBar value={Math.round((c.spend / c.budget) * 100 || 0)} size="sm" />
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border text-center">
                <div>
                  <p className="text-[11px] text-text-secondary">ROAS</p>
                  <p className={cn('text-sm font-bold mt-0.5', c.roas >= 2.5 ? 'text-success' : 'text-text')}>
                    {c.roas.toFixed(2)}x
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-text-secondary">Revenue</p>
                  <p className="text-sm font-bold text-text mt-0.5">{formatINR(c.revenue)}</p>
                </div>
                <div>
                  <p className="text-[11px] text-text-secondary">Creators</p>
                  <p className="text-sm font-bold text-text mt-0.5 flex items-center justify-center gap-1">
                    <Users className="h-3.5 w-3.5 text-text-secondary" />
                    {c.influencers}
                  </p>
                </div>
              </div>

              <div className="pt-2 border-t border-border flex items-center justify-between text-xs text-text-secondary">
                <span>{c.objective}</span>
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
    </div>
  )
}
