import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bookmark,
  ChevronDown,
  ChevronUp,
  LayoutGrid,
  List,
  Loader2,
  Plus,
  Search,
  SlidersHorizontal,
  Sparkles,
  Users,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Badge,
  Button,
  Card,
  InfluencerCard,
  Input,
  Select,
  useToast,
} from '@/components/ui'
import { cn, formatNumber } from '@/utils'
import type { Campaign, Influencer, IntegrationStatus } from '@/types'

type ViewMode = 'grid' | 'table'

interface Filters {
  platform: string
  niche: string
  followersMin: string
  followersMax: string
  location: string
  engagementMin: string
}

const defaultFilters: Filters = {
  platform: 'all',
  niche: 'all',
  followersMin: '',
  followersMax: '',
  location: 'all',
  engagementMin: '',
}

const platformOptions = [
  { value: 'all', label: 'All platforms' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
]

const nicheOptions = [
  { value: 'all', label: 'All niches' },
  { value: 'Skincare', label: 'Skincare' },
  { value: 'Beauty', label: 'Beauty' },
  { value: 'Clean Beauty', label: 'Clean Beauty' },
  { value: 'Dermatology', label: 'Dermatology' },
  { value: 'Lifestyle', label: 'Lifestyle' },
  { value: 'Fashion', label: 'Fashion' },
  { value: 'Fitness', label: 'Fitness' },
  { value: 'Technology', label: 'Technology' },
]

const locationOptions = [
  { value: 'all', label: 'All locations' },
  { value: 'India', label: 'India' },
  { value: 'Mumbai', label: 'Mumbai' },
  { value: 'Delhi', label: 'Delhi' },
  { value: 'Bangalore', label: 'Bangalore' },
  { value: 'Global', label: 'Global' },
]

function applyFilters(list: Influencer[], query: string, filters: Filters): Influencer[] {
  return list.filter((inf) => {
    const q = query.trim().toLowerCase()
    if (q) {
      const name = (inf.name || '').toLowerCase()
      const username = (inf.username || '').toLowerCase()
      const niches = (inf.niches || []).join(' ').toLowerCase()
      const desc = (inf.description || '').toLowerCase()
      if (!name.includes(q) && !username.includes(q) && !niches.includes(q) && !desc.includes(q)) {
        return false
      }
    }
    if (filters.platform !== 'all' && (inf.platform || '').toLowerCase() !== filters.platform.toLowerCase()) {
      return false
    }
    if (filters.niche !== 'all') {
      const target = filters.niche.toLowerCase()
      const hasNiche = (inf.niches || []).some((n) => n.toLowerCase().includes(target))
      if (!hasNiche) return false
    }
    if (filters.location !== 'all') {
      const loc = (inf.location || inf.country || '').toLowerCase()
      if (!loc.includes(filters.location.toLowerCase())) return false
    }
    if (filters.followersMin && (inf.followers || 0) < Number(filters.followersMin)) return false
    if (filters.followersMax && (inf.followers || 0) > Number(filters.followersMax)) return false
    if (filters.engagementMin && (inf.engagementRate || 0) < Number(filters.engagementMin)) return false
    return true
  })
}

export function DiscoveryPage() {
  const { toast } = useToast()
  const [influencersData, setInfluencersData] = useState<Influencer[]>([])
  const [campaignsList, setCampaignsList] = useState<Campaign[]>([])
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('')
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)

  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [showFilters, setShowFilters] = useState(true)
  const [view, setView] = useState<ViewMode>('grid')
  const [shortlisted, setShortlisted] = useState<Record<string, boolean>>({})

  const loadData = () => {
    setLoading(true)
    Promise.all([
      api.influencers.list().catch(() => []),
      api.campaigns.list().catch(() => []),
      api.integrations.getStatus().catch(() => null),
    ])
      .then(([infs, camps, status]) => {
        setInfluencersData(infs || [])
        setCampaignsList(camps || [])
        if (camps && camps.length > 0 && !selectedCampaignId) {
          setSelectedCampaignId(camps[0].id)
        }
        if (status) setIntegrationStatus(status)
        setShortlisted(Object.fromEntries((infs || []).map((i) => [i.id, !!i.shortlisted])))
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    loadData()
  }, [])

  const filtered = useMemo(
    () => applyFilters(influencersData, query, filters),
    [influencersData, query, filters],
  )

  const enriched = useMemo(
    () => filtered.map((inf) => ({ ...inf, shortlisted: shortlisted[inf.id] ?? false })),
    [filtered, shortlisted],
  )

  const shortlistCount = Object.values(shortlisted).filter(Boolean).length

  const toggleShortlist = async (id: string) => {
    setShortlisted((prev) => ({ ...prev, [id]: !prev[id] }))
    try {
      await api.influencers.toggleShortlist(id)
    } catch {
      // Revert if failed
    }
  }

  const handleDiscoverCreators = async () => {
    if (!selectedCampaignId) {
      if (campaignsList.length === 0) {
        toast({
          type: 'warning',
          title: 'Create a campaign first',
          description: 'Creator discovery is driven by your campaign requirements and target audience.',
        })
        return
      }
      setSelectedCampaignId(campaignsList[0].id)
    }

    const campaignIdToUse = selectedCampaignId || (campaignsList[0] ? campaignsList[0].id : '')
    if (!campaignIdToUse) return

    setDiscovering(true)
    try {
      const res = await api.campaigns.fetchInfluencers(campaignIdToUse, {
        limit: 25,
        force_refresh: true,
      })

      const youtubeFetched = res.providers?.youtube?.fetched || 0
      const totalCreated = (res.providers?.youtube?.created || 0) + (res.providers?.instagram?.created || 0)

      if (youtubeFetched > 0) {
        toast({
          type: 'success',
          title: 'Discovery completed',
          description: `Acquired ${youtubeFetched} real creator profiles (${totalCreated} new) from YouTube.`,
        })
      } else {
        toast({
          type: 'info',
          title: 'Discovery finished',
          description: 'No new creators found for this specific query.',
        })
      }

      // Refresh list from database
      const updatedList = await api.influencers.list()
      setInfluencersData(updatedList)
      setShortlisted(Object.fromEntries(updatedList.map((i) => [i.id, !!i.shortlisted])))
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Discovery failed',
        description: err.message || 'Could not acquire creator data from external APIs.',
      })
    } finally {
      setDiscovering(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[32px] font-bold tracking-tight">Creator Discovery</h1>
            {integrationStatus?.youtube?.configured ? (
              <Badge variant="success" className="gap-1 text-xs">
                <Sparkles className="h-3 w-3" /> Live API Connected
              </Badge>
            ) : (
              <Badge variant="default" className="text-xs">
                YouTube API Standing By
              </Badge>
            )}
          </div>
          <p className="text-text-secondary mt-1">
            Acquire and analyze real creator data from YouTube and social channels.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {campaignsList.length > 0 && (
            <div className="w-48 sm:w-56">
              <Select
                options={campaignsList.map((c) => ({ value: c.id, label: c.name }))}
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
              />
            </div>
          )}

          <Button
            onClick={handleDiscoverCreators}
            disabled={discovering}
            className="gap-2 shrink-0"
          >
            {discovering ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-white" />
                <span>Fetching Live Creators...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Discover Creators</span>
              </>
            )}
          </Button>

          {shortlistCount > 0 && (
            <Link to="/app/shortlist">
              <Button variant="soft" className="gap-2 shrink-0">
                <Bookmark className="h-4 w-4" /> Shortlist ({shortlistCount})
              </Button>
            </Link>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search creators by channel name, handle, niche, or bio keywords..."
              className="w-full h-10 pl-10 pr-4 rounded-[10px] border border-border bg-white text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
            />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="secondary"
              className="gap-2"
              onClick={() => setShowFilters((v) => !v)}
            >
              <SlidersHorizontal className="h-4 w-4" />
              Filters
              {showFilters ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </Button>
            <div className="flex border border-border rounded-[10px] p-0.5 bg-page">
              <button
                onClick={() => setView('grid')}
                className={cn('p-1.5 rounded-md transition', view === 'grid' ? 'bg-white shadow-xs text-text' : 'text-text-secondary hover:text-text')}
                aria-label="Grid view"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setView('table')}
                className={cn('p-1.5 rounded-md transition', view === 'table' ? 'bg-white shadow-xs text-text' : 'text-text-secondary hover:text-text')}
                aria-label="Table view"
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {showFilters && (
          <Card className="p-4 animate-fade-in bg-white">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <Select
                label="Platform"
                options={platformOptions}
                value={filters.platform}
                onChange={(e) => setFilters((f) => ({ ...f, platform: e.target.value }))}
              />
              <Select
                label="Niche"
                options={nicheOptions}
                value={filters.niche}
                onChange={(e) => setFilters((f) => ({ ...f, niche: e.target.value }))}
              />
              <Select
                label="Location"
                options={locationOptions}
                value={filters.location}
                onChange={(e) => setFilters((f) => ({ ...f, location: e.target.value }))}
              />
              <Input
                label="Min Subscribers"
                type="number"
                placeholder="e.g. 10000"
                value={filters.followersMin}
                onChange={(e) => setFilters((f) => ({ ...f, followersMin: e.target.value }))}
              />
              <Input
                label="Min Engagement %"
                type="number"
                placeholder="e.g. 3.5"
                value={filters.engagementMin}
                onChange={(e) => setFilters((f) => ({ ...f, engagementMin: e.target.value }))}
              />
            </div>
            {(filters.platform !== 'all' || filters.niche !== 'all' || filters.location !== 'all' || filters.followersMin || filters.engagementMin) && (
              <div className="mt-3 flex justify-end">
                <button
                  onClick={() => setFilters(defaultFilters)}
                  className="text-xs font-semibold text-primary hover:underline"
                >
                  Reset all filters
                </button>
              </div>
            )}
          </Card>
        )}
      </div>

      {loading && (
        <div className="py-20 flex flex-col justify-center items-center gap-3 text-text-secondary text-sm">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p>Loading creator catalog...</p>
        </div>
      )}

      {!loading && influencersData.length === 0 && (
        <div className="py-16 text-center border border-dashed border-border rounded-2xl bg-white p-8 space-y-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
            <Users className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text">No creators discovered yet</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Fetch real creator and channel statistics from YouTube based on your campaign requirements.
            </p>
          </div>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            {campaignsList.length === 0 ? (
              <Link to="/app/campaigns/new">
                <Button size="lg" className="gap-2">
                  <Plus className="h-4 w-4" /> Create Campaign to Start Discovery
                </Button>
              </Link>
            ) : (
              <Button
                size="lg"
                onClick={handleDiscoverCreators}
                disabled={discovering}
                className="gap-2"
              >
                {discovering ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Discover Creators from YouTube
              </Button>
            )}
          </div>
        </div>
      )}

      {!loading && influencersData.length > 0 && enriched.length === 0 && (
        <div className="py-12 text-center text-text-secondary">
          <p className="font-semibold text-text">No matching creators found</p>
          <p className="text-xs mt-1">Try broadening your search query or reset your filters.</p>
          <button
            onClick={() => {
              setQuery('')
              setFilters(defaultFilters)
            }}
            className="mt-3 text-xs font-semibold text-primary hover:underline block mx-auto"
          >
            Clear search & filters
          </button>
        </div>
      )}

      {!loading && enriched.length > 0 && (
        <>
          <div className="flex items-center justify-between text-xs text-text-secondary px-1">
            <span>Showing {enriched.length} verified creator profiles</span>
            <span className="font-mono">Live PostgreSQL records</span>
          </div>

          {view === 'grid' ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {enriched.map((inf) => (
                <InfluencerCard
                  key={inf.id}
                  influencer={inf}
                  onShortlist={toggleShortlist}
                />
              ))}
            </div>
          ) : (
            <Card className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-text-secondary border-b border-border">
                    <th className="pb-3 pl-4 pt-3 font-semibold">Creator</th>
                    <th className="pb-3 pt-3 font-semibold">Platform</th>
                    <th className="pb-3 pt-3 font-semibold">Followers / Subs</th>
                    <th className="pb-3 pt-3 font-semibold">Avg Views</th>
                    <th className="pb-3 pt-3 font-semibold">Engagement</th>
                    <th className="pb-3 pt-3 font-semibold">Location</th>
                    <th className="pb-3 pt-3 font-semibold">Source</th>
                    <th className="pb-3 pr-4 pt-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {enriched.map((inf) => (
                    <tr key={inf.id} className="border-b border-border last:border-0 hover:bg-page/60 transition">
                      <td className="py-3 pl-4">
                        <div className="flex items-center gap-3">
                          {inf.avatar ? (
                            <img
                              src={inf.avatar}
                              alt={inf.name}
                              className="h-9 w-9 rounded-full object-cover border border-border"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none'
                              }}
                            />
                          ) : (
                            <div className="h-9 w-9 rounded-full bg-primary-soft text-primary font-bold text-xs flex items-center justify-center">
                              {inf.name[0]}
                            </div>
                          )}
                          <div>
                            <Link to={`/app/discovery/${inf.id}`} className="font-semibold text-text hover:text-primary transition">
                              {inf.name}
                            </Link>
                            <p className="text-xs text-text-secondary">{inf.username}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 capitalize text-text-secondary">{inf.platform}</td>
                      <td className="py-3 font-semibold">{formatNumber(inf.followers || 0)}</td>
                      <td className="py-3 text-text-secondary">{formatNumber(inf.avgViews || 0)}</td>
                      <td className="py-3 font-semibold text-primary">{inf.engagementRate || 0}%</td>
                      <td className="py-3 text-text-secondary">{inf.location || inf.country || 'Global'}</td>
                      <td className="py-3">
                        <Badge variant="outline" className="text-[10px] uppercase font-mono py-0 px-1.5">
                          {inf.data_source || inf.platform}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-right">
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
            </Card>
          )}
        </>
      )}
    </div>
  )
}
