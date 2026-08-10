import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Filter, Plus, Search, TrendingUp, Users, Wallet } from 'lucide-react'
import { campaigns } from '@/mock-data'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ProgressBar,
  StatusChip,
} from '@/components/ui'
import type { CampaignStatus } from '@/types'
import { cn, formatINR, formatNumber } from '@/utils'

const statusFilters: { value: CampaignStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'planning', label: 'Planning' },
  { value: 'paused', label: 'Paused' },
  { value: 'completed', label: 'Completed' },
  { value: 'needs_attention', label: 'Needs Attention' },
]

const objectiveFilters = ['All', 'Product Launch', 'Awareness', 'Conversions', 'UGC']

export function CampaignsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | 'all'>('all')
  const [objectiveFilter, setObjectiveFilter] = useState('All')

  const filtered = useMemo(() => {
    return campaigns.filter((c) => {
      const matchesSearch =
        !search ||
        c.name.toLowerCase().includes(search.toLowerCase()) ||
        c.brand.toLowerCase().includes(search.toLowerCase())
      const matchesStatus = statusFilter === 'all' || c.status === statusFilter
      const matchesObjective = objectiveFilter === 'All' || c.objective === objectiveFilter
      return matchesSearch && matchesStatus && matchesObjective
    })
  }, [search, statusFilter, objectiveFilter])

  const totals = useMemo(() => {
    const active = campaigns.filter((c) => c.status === 'active').length
    const budget = campaigns.reduce((s, c) => s + c.budget, 0)
    const spend = campaigns.reduce((s, c) => s + c.spend, 0)
    const revenue = campaigns.reduce((s, c) => s + c.revenue, 0)
    const avgRoas = spend > 0 ? revenue / spend : 0
    return { active, budget, spend, revenue, avgRoas }
  }, [])

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
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> Create Campaign
          </Button>
        </Link>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          {
            label: 'Active Campaigns',
            value: totals.active.toString(),
            icon: TrendingUp,
            color: 'text-success',
            bg: 'bg-green-50',
          },
          {
            label: 'Total Budget',
            value: formatINR(totals.budget, true),
            icon: Wallet,
            color: 'text-primary',
            bg: 'bg-primary-soft',
          },
          {
            label: 'Total Spend',
            value: formatINR(totals.spend, true),
            icon: Wallet,
            color: 'text-accent',
            bg: 'bg-violet-50',
          },
          {
            label: 'Avg. ROAS',
            value: totals.avgRoas ? `${totals.avgRoas.toFixed(2)}x` : '—',
            icon: Users,
            color: 'text-ai',
            bg: 'bg-violet-50',
          },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
                    {stat.label}
                  </p>
                  <p className="text-2xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className={cn('h-10 w-10 rounded-xl flex items-center justify-center', stat.bg)}>
                  <stat.icon className={cn('h-5 w-5', stat.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-text-secondary" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
            <input
              type="search"
              placeholder="Search campaigns or brands..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-[10px] border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
            />
          </div>
          <div>
            <p className="text-xs font-semibold text-text-secondary mb-2 uppercase tracking-wide">Status</p>
            <div className="flex flex-wrap gap-2">
              {statusFilters.map((f) => (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setStatusFilter(f.value)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                    statusFilter === f.value
                      ? 'bg-primary-soft border-primary/30 text-primary'
                      : 'bg-white border-border text-text-secondary hover:border-primary/30',
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-text-secondary mb-2 uppercase tracking-wide">Objective</p>
            <div className="flex flex-wrap gap-2">
              {objectiveFilters.map((o) => (
                <button
                  key={o}
                  type="button"
                  onClick={() => setObjectiveFilter(o)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                    objectiveFilter === o
                      ? 'bg-primary-soft border-primary/30 text-primary'
                      : 'bg-white border-border text-text-secondary hover:border-primary/30',
                  )}
                >
                  {o}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>All Campaigns</CardTitle>
            <p className="text-sm text-text-secondary mt-0.5">
              {filtered.length} of {campaigns.length} campaigns
            </p>
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-text-secondary border-b border-border">
                <th className="pb-3 font-semibold">Campaign</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold">Objective</th>
                <th className="pb-3 font-semibold">Budget</th>
                <th className="pb-3 font-semibold">Spend</th>
                <th className="pb-3 font-semibold">Revenue</th>
                <th className="pb-3 font-semibold">ROAS</th>
                <th className="pb-3 font-semibold">Creators</th>
                <th className="pb-3 font-semibold">Progress</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-border last:border-0 hover:bg-page/80 transition-colors"
                >
                  <td className="py-4 pr-3">
                    <Link to={`/app/campaigns/${c.id}`} className="group block min-w-[180px]">
                      <span className="font-semibold group-hover:text-primary transition-colors">
                        {c.name}
                      </span>
                      <p className="text-xs text-text-secondary mt-0.5">{c.brand}</p>
                      <p className="text-[11px] text-text-secondary mt-0.5">
                        {new Date(c.startDate).toLocaleDateString('en-IN', {
                          month: 'short',
                          day: 'numeric',
                        })}{' '}
                        –{' '}
                        {new Date(c.endDate).toLocaleDateString('en-IN', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </p>
                    </Link>
                  </td>
                  <td className="py-4 pr-3">
                    <StatusChip status={c.status} />
                  </td>
                  <td className="py-4 pr-3">
                    <span className="text-xs font-medium bg-muted px-2 py-1 rounded-md">{c.objective}</span>
                  </td>
                  <td className="py-4 pr-3 font-medium">{formatINR(c.budget, true)}</td>
                  <td className="py-4 pr-3">{formatINR(c.spend, true)}</td>
                  <td className="py-4 pr-3">{c.revenue ? formatINR(c.revenue, true) : '—'}</td>
                  <td className="py-4 pr-3">
                    <span
                      className={cn(
                        'font-semibold',
                        c.roas >= 2.5 ? 'text-success' : c.roas >= 1.5 ? 'text-primary' : c.roas > 0 ? 'text-danger' : 'text-text-secondary',
                      )}
                    >
                      {c.roas ? `${c.roas}x` : '—'}
                    </span>
                  </td>
                  <td className="py-4 pr-3">
                    <span className="font-medium">{c.influencers}</span>
                    <p className="text-xs text-text-secondary">{formatNumber(c.reach)} reach</p>
                  </td>
                  <td className="py-4 min-w-[120px]">
                    <ProgressBar value={c.progress} size="sm" />
                    <span className="text-xs font-semibold text-text-secondary mt-1 inline-block">
                      {c.progress}%
                    </span>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-text-secondary">
                    No campaigns match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
