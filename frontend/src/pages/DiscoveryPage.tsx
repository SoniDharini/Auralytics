import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Bookmark,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  LayoutGrid,
  List,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Users,
} from 'lucide-react'
import { api } from '@/services/api'
import { ManualCreatorSearch } from '@/components/discovery/ManualCreatorSearch'
import {
  Badge,
  Button,
  Card,
  InfluencerCard,
  Input,
  Select,
  Avatar,
  useToast,
} from '@/components/ui'
import { cn, formatNumber, recommendedCampaignCreators } from '@/utils'
import type { Campaign, CampaignCreator, IntegrationStatus } from '@/types'

type ViewMode = 'grid' | 'table'

interface Filters {
  status: string
  followersMin: string
  followersMax: string
  engagementMin: string
  sort: string
}

const defaultFilters: Filters = {
  status: 'all',
  followersMin: '',
  followersMax: '',
  engagementMin: '',
  sort: 'match_score',
}

const statusOptions = [
  { value: 'all', label: 'All statuses' },
  { value: 'DISCOVERED', label: 'Discovered' },
  { value: 'SHORTLISTED', label: 'Shortlisted' },
  { value: 'CONTACTED', label: 'Contacted' },
  { value: 'REJECTED', label: 'Rejected' },
]

const sortOptions = [
  { value: 'match_score', label: 'Best campaign match' },
  { value: 'followers', label: 'Most subscribers' },
  { value: 'engagement', label: 'Highest engagement' },
  { value: 'avg_views', label: 'Highest avg views' },
  { value: 'recent', label: 'Recently discovered' },
]

const NOT_AVAILABLE = 'N/A'

export function DiscoveryPage() {
  const { toast } = useToast()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>('')
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null)

  const [creators, setCreators] = useState<CampaignCreator[]>([])
  const [total, setTotal] = useState(0)

  const [bootstrapping, setBootstrapping] = useState(true)
  const [listLoading, setListLoading] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [query, setQuery] = useState('')
  const [appliedQuery, setAppliedQuery] = useState('')
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [showFilters, setShowFilters] = useState(true)
  const [view, setView] = useState<ViewMode>('grid')
  const [pendingStatusIds, setPendingStatusIds] = useState<Record<string, boolean>>({})

  const selectedCampaign = useMemo(
    () => campaigns.find((c) => c.id === selectedCampaignId) ?? null,
    [campaigns, selectedCampaignId],
  )
  const displayedCreators = useMemo(
    () => recommendedCampaignCreators(creators),
    [creators],
  )

  useEffect(() => {
    let cancelled = false

    Promise.all([
      api.campaigns.list().catch(() => [] as Campaign[]),
      api.integrations.getStatus().catch(() => null),
    ])
      .then(([campaignList, status]) => {
        if (cancelled) return
        setCampaigns(campaignList || [])
        if (status) setIntegrationStatus(status)
        if (campaignList && campaignList.length > 0) {
          setSelectedCampaignId((current) => current || campaignList[0].id)
        }
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  /** Reads already-discovered creators from PostgreSQL. Never contacts YouTube. */
  const loadCreators = useCallback(
    async (campaignId: string) => {
      if (!campaignId) return
      setListLoading(true)
      setLoadError(null)
      try {
        const res = await api.discovery.listCreators(campaignId, {
          limit: 100,
          sort: filters.sort,
          status: filters.status !== 'all' ? filters.status : undefined,
          min_subscribers: filters.followersMin ? Number(filters.followersMin) : undefined,
          max_subscribers: filters.followersMax ? Number(filters.followersMax) : undefined,
          min_engagement: filters.engagementMin ? Number(filters.engagementMin) : undefined,
          search: appliedQuery || undefined,
        })
        setCreators(res.creators || [])
        setTotal(res.total ?? 0)
      } catch (err: any) {
        setCreators([])
        setTotal(0)
        setLoadError(err?.message || 'Could not load discovered creators.')
      } finally {
        setListLoading(false)
        setHasLoadedOnce(true)
      }
    },
    [filters, appliedQuery],
  )

  useEffect(() => {
    if (!selectedCampaignId) return
    setHasLoadedOnce(false)
    loadCreators(selectedCampaignId)
  }, [selectedCampaignId, loadCreators])

  const handleDiscover = async (refresh = false) => {
    if (!selectedCampaignId || discovering) return

    setDiscovering(true)
    setLoadError(null)
    try {
      const res = await api.discovery.discover(selectedCampaignId, { refresh })

      if (res.count > 0) {
        toast({
          type: 'success',
          title: 'Discovery completed',
          description: `${res.count} YouTube creator(s) matched this campaign (${res.stats.created} new, ${res.stats.updated} refreshed).`,
        })
      } else {
        toast({
          type: 'info',
          title: 'No matches found',
          description:
            'No YouTube creators matched the current campaign criteria. Try broadening your niche, keywords, or audience-size filters.',
        })
      }

      await loadCreators(selectedCampaignId)
    } catch (err: any) {
      const status = err?.status
      let title = 'Discovery failed'
      let description = "We couldn't fetch YouTube creators right now. Please try again."

      if (status === 429) {
        title = 'YouTube quota exhausted'
        description = err.message
      } else if (status === 503) {
        title = 'YouTube API not configured'
        description = err.message
      } else if (status === 422) {
        title = 'Campaign brief is too thin'
        description = err.message
      } else if (err?.message) {
        description = err.message
      }

      setLoadError(description)
      toast({ type: 'error', title, description })
    } finally {
      setDiscovering(false)
    }
  }

  const toggleShortlist = async (influencerId: string) => {
    const entry = creators.find((c) => c.creator.id === influencerId)
    if (!entry || pendingStatusIds[influencerId]) return

    const nextStatus = entry.status === 'SHORTLISTED' ? 'DISCOVERED' : 'SHORTLISTED'
    setPendingStatusIds((prev) => ({ ...prev, [influencerId]: true }))

    // Optimistic update, reverted if the server rejects the change.
    setCreators((prev) =>
      prev.map((c) => (c.creator.id === influencerId ? { ...c, status: nextStatus } : c)),
    )

    try {
      const updated = await api.discovery.setStatus(selectedCampaignId, influencerId, nextStatus)
      setCreators((prev) => prev.map((c) => (c.creator.id === influencerId ? updated : c)))
    } catch (err: any) {
      setCreators((prev) =>
        prev.map((c) => (c.creator.id === influencerId ? { ...c, status: entry.status } : c)),
      )
      toast({
        type: 'error',
        title: 'Could not update shortlist',
        description: err?.message || 'The change was not saved. Please try again.',
      })
    } finally {
      setPendingStatusIds((prev) => {
        const next = { ...prev }
        delete next[influencerId]
        return next
      })
    }
  }

  const shortlistCount = creators.filter((c) => c.status === 'SHORTLISTED').length
  const hasFilters =
    filters.status !== 'all' ||
    !!filters.followersMin ||
    !!filters.followersMax ||
    !!filters.engagementMin ||
    !!appliedQuery

  const resetFilters = () => {
    setFilters(defaultFilters)
    setQuery('')
    setAppliedQuery('')
  }

  // --- No campaign yet -------------------------------------------------------
  if (!bootstrapping && campaigns.length === 0) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Creator Discovery</h1>
          <p className="text-text-secondary mt-1">
            Find real YouTube creators that match a specific campaign brief.
          </p>
        </div>
        <div className="py-16 text-center border border-dashed border-border rounded-2xl bg-white p-8 space-y-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
            <Users className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text">Create a campaign before discovering creators</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Discovery uses your campaign's keywords, niche, target location and subscriber range to
              search YouTube.
            </p>
          </div>
          <div className="pt-2">
            <Link to="/app/campaigns/new">
              <Button size="lg" className="gap-2">
                <Plus className="h-4 w-4" /> Create Campaign
              </Button>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-[32px] font-bold tracking-tight">Creator Discovery</h1>
            {integrationStatus?.youtube?.configured ? (
              <Badge variant="success" className="gap-1 text-xs">
                <Sparkles className="h-3 w-3" /> YouTube API connected
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs">
                YouTube API not configured
              </Badge>
            )}
          </div>
          <p className="text-text-secondary mt-1">
            {selectedCampaign
              ? `Real YouTube creators discovered for "${selectedCampaign.name}".`
              : 'Select a campaign to view its discovered creators.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {campaigns.length > 0 && (
            <div className="w-48 sm:w-60">
              <Select
                options={campaigns.map((c) => ({ value: c.id, label: c.name }))}
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                aria-label="Select campaign"
              />
            </div>
          )}

          <Button onClick={() => handleDiscover(false)} disabled={discovering || !selectedCampaignId} className="gap-2 shrink-0">
            {discovering ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-white" />
                <span>Finding creators...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Discover Creators</span>
              </>
            )}
          </Button>

          {creators.length > 0 && (
            <Button
              variant="secondary"
              onClick={() => handleDiscover(true)}
              disabled={discovering}
              className="gap-2 shrink-0"
              title="Re-fetch the latest statistics from YouTube"
            >
              <RefreshCw className={cn('h-4 w-4', discovering && 'animate-spin')} />
              Refresh
            </Button>
          )}

          {shortlistCount > 0 && (
            <Link to="/app/shortlist">
              <Button variant="soft" className="gap-2 shrink-0">
                <Bookmark className="h-4 w-4" /> Shortlist ({shortlistCount})
              </Button>
            </Link>
          )}
        </div>
      </div>

      {discovering && (
        <Card className="p-4 flex items-center gap-3 bg-primary-soft/40 border-primary/20">
          <Loader2 className="h-5 w-5 animate-spin text-primary shrink-0" />
          <div>
            <p className="text-sm font-semibold text-text">Finding creators matching your campaign...</p>
            <p className="text-xs text-text-secondary">
              Searching YouTube, enriching channel statistics and scoring campaign fit. This may take a moment.
            </p>
          </div>
        </Card>
      )}

      {loadError && !discovering && (
        <Card className="p-4 flex items-start gap-3 border-danger/30 bg-danger/5">
          <AlertTriangle className="h-5 w-5 text-danger shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-text">Something went wrong</p>
            <p className="text-xs text-text-secondary mt-0.5">{loadError}</p>
          </div>
        </Card>
      )}

      {selectedCampaignId && (
        <ManualCreatorSearch
          campaignId={selectedCampaignId}
          disabled={discovering}
          onShortlisted={() => {
            void loadCreators(selectedCampaignId)
          }}
        />
      )}

      {/* Search & filters */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <form
            className="flex-1 relative"
            onSubmit={(e) => {
              e.preventDefault()
              setAppliedQuery(query.trim())
            }}
          >
            <Search className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onBlur={() => setAppliedQuery(query.trim())}
              placeholder="Search discovered creators by channel name, handle or description..."
              className="w-full h-10 pl-10 pr-4 rounded-[10px] border border-border bg-white text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10"
              aria-label="Search discovered creators"
            />
          </form>
          <div className="flex items-center gap-2 shrink-0">
            <Button variant="secondary" className="gap-2" onClick={() => setShowFilters((v) => !v)}>
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
                label="Status"
                options={statusOptions}
                value={filters.status}
                onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
              />
              <Select
                label="Sort by"
                options={sortOptions}
                value={filters.sort}
                onChange={(e) => setFilters((f) => ({ ...f, sort: e.target.value }))}
              />
              <Input
                label="Min subscribers"
                type="number"
                min={0}
                placeholder="e.g. 10000"
                value={filters.followersMin}
                onChange={(e) => setFilters((f) => ({ ...f, followersMin: e.target.value }))}
              />
              <Input
                label="Max subscribers"
                type="number"
                min={0}
                placeholder="e.g. 500000"
                value={filters.followersMax}
                onChange={(e) => setFilters((f) => ({ ...f, followersMax: e.target.value }))}
              />
              <Input
                label="Min engagement %"
                type="number"
                min={0}
                placeholder="e.g. 2.5"
                value={filters.engagementMin}
                onChange={(e) => setFilters((f) => ({ ...f, engagementMin: e.target.value }))}
              />
            </div>
            {hasFilters && (
              <div className="mt-3 flex justify-end">
                <button onClick={resetFilters} className="text-xs font-semibold text-primary hover:underline">
                  Reset all filters
                </button>
              </div>
            )}
          </Card>
        )}
      </div>

      {(bootstrapping || (listLoading && !hasLoadedOnce)) && (
        <div className="py-20 flex flex-col justify-center items-center gap-3 text-text-secondary text-sm">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p>Loading discovered creators...</p>
        </div>
      )}

      {hasLoadedOnce && !bootstrapping && (
        <h2 className="text-sm font-semibold text-text px-1">AI recommended creators</h2>
      )}

      {/* Never discovered for this campaign */}
      {!bootstrapping && hasLoadedOnce && !discovering && creators.length === 0 && !hasFilters && (
        <div className="py-16 text-center border border-dashed border-border rounded-2xl bg-white p-8 space-y-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft text-primary flex items-center justify-center">
            <Users className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-text">No creators discovered yet</h3>
            <p className="text-sm text-text-secondary mt-1 max-w-md mx-auto">
              Find YouTube creators that match your campaign requirements.
            </p>
          </div>
          <div className="pt-2">
            <Button size="lg" onClick={() => handleDiscover(false)} disabled={discovering} className="gap-2">
              <Sparkles className="h-4 w-4" /> Discover Creators
            </Button>
          </div>
        </div>
      )}

      {/* Filters excluded everything */}
      {!bootstrapping && hasLoadedOnce && !discovering && creators.length === 0 && hasFilters && (
        <div className="py-12 text-center text-text-secondary">
          <p className="font-semibold text-text">No creators match these filters</p>
          <p className="text-xs mt-1">
            Try broadening your niche, keywords, or audience-size filters.
          </p>
          <button onClick={resetFilters} className="mt-3 text-xs font-semibold text-primary hover:underline block mx-auto">
            Clear search &amp; filters
          </button>
        </div>
      )}

      {displayedCreators.length > 0 && (
        <>
          <div className="flex items-center justify-between text-xs text-text-secondary px-1">
            <span>
              Showing {displayedCreators.length} of {total} discovered creator{total === 1 ? '' : 's'}
            </span>
            <span className="font-mono">Stored in PostgreSQL · source: YouTube Data API</span>
          </div>

          {view === 'grid' ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {displayedCreators.map((entry) => (
                <InfluencerCard
                  key={entry.link_id}
                  influencer={{ ...entry.creator, shortlisted: entry.status === 'SHORTLISTED' }}
                  matchScore={entry.match_score ?? null}
                  matchReasons={entry.match_reasons}
                  profileHref={`/app/discovery/${entry.creator.id}?campaign=${entry.campaign_id}`}
                  onShortlist={toggleShortlist}
                  shortlistLabel={pendingStatusIds[entry.creator.id] ? 'Saving...' : undefined}
                />
              ))}
            </div>
          ) : (
            <Card className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-text-secondary border-b border-border">
                    <th className="pb-3 pl-4 pt-3 font-semibold">Creator</th>
                    <th className="pb-3 pt-3 font-semibold">Match</th>
                    <th className="pb-3 pt-3 font-semibold">Subscribers</th>
                    <th className="pb-3 pt-3 font-semibold">Avg views</th>
                    <th className="pb-3 pt-3 font-semibold">Engagement</th>
                    <th className="pb-3 pt-3 font-semibold">Videos</th>
                    <th className="pb-3 pt-3 font-semibold">Country</th>
                    <th className="pb-3 pt-3 font-semibold">Channel</th>
                    <th className="pb-3 pr-4 pt-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedCreators.map((entry) => {
                    const inf = entry.creator
                    const hasEngagement = (inf.metricsSampleSize ?? 0) > 0 && !!inf.engagementRate
                    return (
                      <tr key={entry.link_id} className="border-b border-border last:border-0 hover:bg-page/60 transition">
                        <td className="py-3 pl-4">
                          <div className="flex items-center gap-3">
                            <Avatar name={inf.name} src={inf.avatar} size="sm" className="border border-border" />
                            <div>
                              <Link
                                to={`/app/discovery/${inf.id}?campaign=${entry.campaign_id}`}
                                className="font-semibold text-text hover:text-primary transition"
                              >
                                {inf.name}
                              </Link>
                              <p className="text-xs text-text-secondary">{inf.username}</p>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 font-semibold">
                          {typeof entry.match_score === 'number' ? `${Math.round(entry.match_score)}%` : NOT_AVAILABLE}
                        </td>
                        <td className="py-3 font-semibold">
                          {inf.followers ? formatNumber(inf.followers) : NOT_AVAILABLE}
                        </td>
                        <td className="py-3 text-text-secondary">
                          {inf.avgViews ? formatNumber(inf.avgViews) : NOT_AVAILABLE}
                        </td>
                        <td className={cn('py-3 font-semibold', hasEngagement ? 'text-primary' : 'text-text-secondary')}>
                          {hasEngagement ? `${inf.engagementRate}%` : NOT_AVAILABLE}
                        </td>
                        <td className="py-3 text-text-secondary">
                          {inf.content_count ? formatNumber(inf.content_count) : NOT_AVAILABLE}
                        </td>
                        <td className="py-3 text-text-secondary">{inf.country || NOT_AVAILABLE}</td>
                        <td className="py-3">
                          {inf.profile_url ? (
                            <a
                              href={inf.profile_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline inline-flex items-center gap-1 text-xs font-medium"
                            >
                              Open <ExternalLink className="h-3 w-3" />
                            </a>
                          ) : (
                            <span className="text-text-secondary text-xs">{NOT_AVAILABLE}</span>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-right">
                          <Button
                            size="sm"
                            variant={entry.status === 'SHORTLISTED' ? 'soft' : 'primary'}
                            disabled={!!pendingStatusIds[inf.id]}
                            onClick={() => toggleShortlist(inf.id)}
                          >
                            {entry.status === 'SHORTLISTED' ? 'Shortlisted' : 'Shortlist'}
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
