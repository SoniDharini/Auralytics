import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  LayoutGrid,
  List,
  Search,
  SlidersHorizontal,
  Sparkles,
  Bookmark,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { influencers as allInfluencers } from '@/mock-data'
import {
  Button,
  Card,
  CardContent,
  EmptyState,
  InfluencerCard,
  Input,
  Select,
} from '@/components/ui'
import { cn, formatINR, formatNumber } from '@/utils'
import type { Influencer } from '@/types'

type ViewMode = 'grid' | 'table'

interface Filters {
  platform: string
  niche: string
  followersMin: string
  followersMax: string
  location: string
  engagementMin: string
  priceMin: string
  priceMax: string
  aiMatchMin: string
  roasMin: string
}

const defaultFilters: Filters = {
  platform: 'all',
  niche: 'all',
  followersMin: '',
  followersMax: '',
  location: 'all',
  engagementMin: '',
  priceMin: '',
  priceMax: '',
  aiMatchMin: '',
  roasMin: '',
}

const platformOptions = [
  { value: 'all', label: 'All platforms' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'x', label: 'X' },
]

const nicheOptions = [
  { value: 'all', label: 'All niches' },
  { value: 'Beauty', label: 'Beauty' },
  { value: 'Skincare', label: 'Skincare' },
  { value: 'Lifestyle', label: 'Lifestyle' },
  { value: 'Fashion', label: 'Fashion' },
  { value: 'Fitness', label: 'Fitness' },
  { value: 'Wellness', label: 'Wellness' },
  { value: 'Food', label: 'Food' },
  { value: 'Technology', label: 'Technology' },
]

const locationOptions = [
  { value: 'all', label: 'All locations' },
  { value: 'Mumbai', label: 'Mumbai' },
  { value: 'Delhi', label: 'Delhi' },
  { value: 'Bangalore', label: 'Bangalore' },
  { value: 'Pune', label: 'Pune' },
  { value: 'Hyderabad', label: 'Hyderabad' },
  { value: 'Goa', label: 'Goa' },
  { value: 'Ahmedabad', label: 'Ahmedabad' },
  { value: 'Kochi', label: 'Kochi' },
]

function applyFilters(list: Influencer[], query: string, filters: Filters): Influencer[] {
  return list.filter((inf) => {
    const q = query.trim().toLowerCase()
    if (q && !`${inf.name} ${inf.username} ${inf.niches.join(' ')}`.toLowerCase().includes(q)) {
      return false
    }
    if (filters.platform !== 'all' && inf.platform !== filters.platform) return false
    if (filters.niche !== 'all' && !inf.niches.some((n) => n.toLowerCase() === filters.niche.toLowerCase())) {
      return false
    }
    if (filters.location !== 'all' && !inf.location.toLowerCase().includes(filters.location.toLowerCase())) {
      return false
    }
    if (filters.followersMin && inf.followers < Number(filters.followersMin)) return false
    if (filters.followersMax && inf.followers > Number(filters.followersMax)) return false
    if (filters.engagementMin && inf.engagementRate < Number(filters.engagementMin)) return false
    if (filters.priceMin && inf.estimatedCost < Number(filters.priceMin)) return false
    if (filters.priceMax && inf.estimatedCost > Number(filters.priceMax)) return false
    if (filters.aiMatchMin && inf.aiMatchScore < Number(filters.aiMatchMin)) return false
    if (filters.roasMin && inf.predictedRoas < Number(filters.roasMin)) return false
    return true
  })
}

export function DiscoveryPage() {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [showFilters, setShowFilters] = useState(true)
  const [view, setView] = useState<ViewMode>('grid')
  const [shortlisted, setShortlisted] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(allInfluencers.map((i) => [i.id, !!i.shortlisted])),
  )

  const filtered = useMemo(
    () => applyFilters(allInfluencers, query, filters),
    [query, filters],
  )

  const enriched = useMemo(
    () => filtered.map((inf) => ({ ...inf, shortlisted: shortlisted[inf.id] ?? false })),
    [filtered, shortlisted],
  )

  const shortlistCount = Object.values(shortlisted).filter(Boolean).length

  const toggleShortlist = (id: string) => {
    setShortlisted((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const resetFilters = () => {
    setFilters(defaultFilters)
    setQuery('')
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight">Influencer Discovery</h1>
          <p className="text-text-secondary mt-1">
            AI-ranked creators for GlowNaturals Summer Launch
          </p>
        </div>
        <Link to="/app/shortlist">
          <Button variant="secondary" className="gap-2">
            <Bookmark className="h-4 w-4" />
            View Shortlist ({shortlistCount})
          </Button>
        </Link>
      </div>

      <div className="flex items-center gap-2 rounded-[10px] border border-indigo-100 bg-primary-soft/60 px-4 py-2.5 text-sm text-primary">
        <Sparkles className="h-4 w-4 shrink-0 animate-pulse" />
        <span>
          <span className="font-semibold">Discovery Agent is analyzing…</span>
          <span className="text-primary/80"> 487 creators scanned, {filtered.length} match your criteria</span>
        </span>
      </div>

      <Card>
        <CardContent className="pt-5 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
              <Input
                placeholder="Search by name, handle, or niche…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="gap-2"
                onClick={() => setShowFilters((v) => !v)}
              >
                <SlidersHorizontal className="h-4 w-4" />
                Filters
                {showFilters ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </Button>
              <div className="flex rounded-[10px] border border-border overflow-hidden">
                <button
                  onClick={() => setView('grid')}
                  className={cn(
                    'px-3 py-2 transition',
                    view === 'grid' ? 'bg-primary text-white' : 'bg-white text-text-secondary hover:bg-muted',
                  )}
                  aria-label="Grid view"
                >
                  <LayoutGrid className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setView('table')}
                  className={cn(
                    'px-3 py-2 transition border-l border-border',
                    view === 'table' ? 'bg-primary text-white' : 'bg-white text-text-secondary hover:bg-muted',
                  )}
                  aria-label="Table view"
                >
                  <List className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {showFilters && (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-3 pt-2 border-t border-border">
              <Select
                label="Platform"
                options={platformOptions}
                value={filters.platform}
                onChange={(e) => updateFilter('platform', e.target.value)}
              />
              <Select
                label="Niche"
                options={nicheOptions}
                value={filters.niche}
                onChange={(e) => updateFilter('niche', e.target.value)}
              />
              <Input
                label="Min followers"
                type="number"
                placeholder="e.g. 50000"
                value={filters.followersMin}
                onChange={(e) => updateFilter('followersMin', e.target.value)}
              />
              <Input
                label="Max followers"
                type="number"
                placeholder="e.g. 500000"
                value={filters.followersMax}
                onChange={(e) => updateFilter('followersMax', e.target.value)}
              />
              <Select
                label="Location"
                options={locationOptions}
                value={filters.location}
                onChange={(e) => updateFilter('location', e.target.value)}
              />
              <Input
                label="Min engagement %"
                type="number"
                placeholder="e.g. 4"
                value={filters.engagementMin}
                onChange={(e) => updateFilter('engagementMin', e.target.value)}
              />
              <Input
                label="Min price (₹)"
                type="number"
                placeholder="e.g. 10000"
                value={filters.priceMin}
                onChange={(e) => updateFilter('priceMin', e.target.value)}
              />
              <Input
                label="Max price (₹)"
                type="number"
                placeholder="e.g. 50000"
                value={filters.priceMax}
                onChange={(e) => updateFilter('priceMax', e.target.value)}
              />
              <Input
                label="Min AI match %"
                type="number"
                placeholder="e.g. 70"
                value={filters.aiMatchMin}
                onChange={(e) => updateFilter('aiMatchMin', e.target.value)}
              />
              <Input
                label="Min predicted ROAS"
                type="number"
                step="0.1"
                placeholder="e.g. 2.0"
                value={filters.roasMin}
                onChange={(e) => updateFilter('roasMin', e.target.value)}
              />
              <div className="flex items-end">
                <Button variant="ghost" size="sm" onClick={resetFilters}>
                  Reset filters
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {enriched.length === 0 ? (
        <Card>
          <EmptyState
            icon={Search}
            title="No creators match your filters"
            description="Try adjusting your search or filter criteria. Discovery Agent can also expand the search to adjacent niches."
            actionLabel="Reset filters"
            onAction={resetFilters}
          />
        </Card>
      ) : view === 'grid' ? (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {enriched.map((inf) => (
            <InfluencerCard
              key={inf.id}
              influencer={inf}
              onShortlist={toggleShortlist}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="pt-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-text-secondary border-b border-border">
                  <th className="pb-3 font-semibold">Influencer</th>
                  <th className="pb-3 font-semibold">Platform</th>
                  <th className="pb-3 font-semibold">Followers</th>
                  <th className="pb-3 font-semibold">Engagement</th>
                  <th className="pb-3 font-semibold">AI Match</th>
                  <th className="pb-3 font-semibold">Pred. ROAS</th>
                  <th className="pb-3 font-semibold">Est. Cost</th>
                  <th className="pb-3 font-semibold">Location</th>
                  <th className="pb-3 font-semibold" />
                </tr>
              </thead>
              <tbody>
                {enriched.map((inf) => (
                  <tr key={inf.id} className="border-b border-border last:border-0 hover:bg-page/80">
                    <td className="py-3.5 pr-3">
                      <Link to={`/app/discovery/${inf.id}`} className="font-semibold hover:text-primary">
                        {inf.name}
                      </Link>
                      <p className="text-xs text-text-secondary">@{inf.username}</p>
                    </td>
                    <td className="py-3.5 pr-3 capitalize">{inf.platform}</td>
                    <td className="py-3.5 pr-3">{formatNumber(inf.followers)}</td>
                    <td className="py-3.5 pr-3">{inf.engagementRate}%</td>
                    <td className="py-3.5 pr-3 font-semibold text-ai">{inf.aiMatchScore}%</td>
                    <td className="py-3.5 pr-3 font-semibold text-primary">{inf.predictedRoas}x</td>
                    <td className="py-3.5 pr-3">{formatINR(inf.estimatedCost, true)}</td>
                    <td className="py-3.5 pr-3 text-text-secondary">{inf.location}</td>
                    <td className="py-3.5">
                      <Button
                        size="sm"
                        variant={inf.shortlisted ? 'soft' : 'primary'}
                        onClick={() => toggleShortlist(inf.id)}
                      >
                        {inf.shortlisted ? 'Shortlisted' : 'Shortlist'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
