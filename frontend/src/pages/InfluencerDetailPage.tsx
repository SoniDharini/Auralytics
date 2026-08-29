import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  CircleSlash,
  ExternalLink,
  Loader2,
  MapPin,
  MinusCircle,
  RefreshCw,
  Users,
} from 'lucide-react'
import { api } from '@/services/api'
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ProgressRing,
  useToast,
} from '@/components/ui'
import { PlatformIcon } from '@/components/ui/PlatformIcon'
import { cn, formatNumber } from '@/utils'
import type { CampaignCreator, Influencer, MatchFactor } from '@/types'

const NOT_AVAILABLE = 'N/A'

function formatFreshness(isoString?: string | null): string {
  if (!isoString) return 'Recent'
  try {
    const diffMs = Date.now() - new Date(isoString).getTime()
    const mins = Math.floor(diffMs / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    return new Date(isoString).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
  } catch {
    return 'Recent'
  }
}

export function InfluencerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const campaignId = searchParams.get('campaign')
  const { toast } = useToast()

  const [influencer, setInfluencer] = useState<Influencer | null>(null)
  const [campaignMatch, setCampaignMatch] = useState<CampaignCreator | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [shortlisted, setShortlisted] = useState(false)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)

    // Inside a campaign context the campaign-scoped record also carries the match breakdown.
    const loader = campaignId
      ? api.discovery.getCreator(campaignId, id).then((entry) => {
          if (cancelled) return
          setCampaignMatch(entry)
          setInfluencer(entry.creator)
          setShortlisted(entry.status === 'SHORTLISTED')
        })
      : api.influencers.get(id).then((data) => {
          if (cancelled) return
          setCampaignMatch(null)
          setInfluencer(data)
          setShortlisted(!!data.shortlisted)
        })

    loader
      .catch(() => {
        if (!cancelled) setInfluencer(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [id, campaignId])

  const toggleShortlist = async () => {
    if (!id) return
    const nextState = !shortlisted
    setShortlisted(nextState)
    try {
      if (campaignId) {
        const updated = await api.discovery.setStatus(
          campaignId,
          id,
          nextState ? 'SHORTLISTED' : 'DISCOVERED',
        )
        setCampaignMatch(updated)
      } else {
        await api.influencers.toggleShortlist(id)
      }
      toast({
        type: 'success',
        title: nextState ? 'Shortlisted' : 'Removed from shortlist',
        description: `${influencer?.name || 'Creator'} shortlist status saved.`,
      })
    } catch (err: any) {
      setShortlisted(!nextState)
      toast({
        type: 'error',
        title: 'Could not update shortlist',
        description: err?.message || 'The change was not saved. Please try again.',
      })
    }
  }

  const handleRefreshStats = async () => {
    if (!id) return
    setRefreshing(true)
    try {
      const updated = await api.influencers.refresh(id)
      setInfluencer(updated)
      toast({
        type: 'success',
        title: 'Metrics refreshed',
        description: 'Updated latest view counts and engagement metrics from source platform.',
      })
    } catch (err: any) {
      toast({
        type: 'error',
        title: 'Refresh failed',
        description: err.message || 'Could not refresh platform metrics.',
      })
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <div className="py-24 flex flex-col justify-center items-center gap-3 text-text-secondary">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
        <p className="text-sm">Loading creator profile...</p>
      </div>
    )
  }

  if (!influencer) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Link
          to="/app/discovery"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-text-secondary hover:text-primary transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Discovery
        </Link>
        <Card className="py-12 text-center text-text-secondary">
          <CardContent className="space-y-3">
            <Users className="h-10 w-10 mx-auto text-text-secondary/40" />
            <h3 className="text-base font-semibold text-text">Creator Not Found</h3>
            <p className="text-xs max-w-sm mx-auto">
              This creator record may have been removed or does not exist in your database.
            </p>
            <Link to="/app/discovery">
              <Button size="sm" className="mt-2">
                Return to Discovery
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  const isYouTube = (influencer.platform || '').toLowerCase() === 'youtube'
  const sampleSize = influencer.metricsSampleSize ?? 0
  const hasSample = sampleSize > 0
  const num = (value?: number | null) => (value && value > 0 ? formatNumber(value) : NOT_AVAILABLE)

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <Link
          to="/app/discovery"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-text-secondary hover:text-primary transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Discovery
        </Link>
        <Button
          size="sm"
          variant="secondary"
          onClick={handleRefreshStats}
          disabled={refreshing}
          className="gap-1.5"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', refreshing && 'animate-spin')} />
          <span>Refresh Platform Stats</span>
        </Button>
      </div>

      <Card>
        <CardContent className="pt-5">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-5">
            <div className="flex items-start gap-4">
              <Avatar name={influencer.name} src={influencer.avatar} size="xl" className="border border-border" />
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-2xl font-bold">{influencer.name}</h1>
                  {influencer.verified && (
                    <CheckCircle2 className="h-5 w-5 text-primary" aria-label="Verified" />
                  )}
                </div>
                <p className="text-text-secondary mt-0.5">
                  {influencer.username.startsWith('@') ? influencer.username : `@${influencer.username}`}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-page border border-border px-2.5 py-1 text-xs font-semibold capitalize">
                    <PlatformIcon platform={influencer.platform as any} />
                    {influencer.platform}
                  </span>
                  <Badge variant="outline" className="text-[11px] uppercase font-mono">
                    Source: {influencer.data_source || influencer.platform}
                  </Badge>
                  <span className="text-xs text-text-secondary font-mono bg-page px-2 py-0.5 rounded border border-border">
                    Updated {formatFreshness(influencer.source_fetched_at)}
                  </span>
                  {influencer.location && (
                    <span className="inline-flex items-center gap-1 text-xs text-text-secondary">
                      <MapPin className="h-3.5 w-3.5" />
                      {influencer.location}
                    </span>
                  )}
                </div>

                {influencer.niches && influencer.niches.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {influencer.niches.map((n) => (
                      <Badge key={n} variant="outline">
                        {n}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-2.5 shrink-0">
              {influencer.profile_url && (
                <a
                  href={influencer.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex"
                >
                  <Button variant="secondary" size="lg" className="gap-1.5 w-full">
                    <ExternalLink className="h-4 w-4" /> Open Channel
                  </Button>
                </a>
              )}
              <Button
                size="lg"
                variant={shortlisted ? 'soft' : 'primary'}
                onClick={toggleShortlist}
              >
                {shortlisted ? 'Shortlisted' : 'Add to Shortlist'}
              </Button>
            </div>
          </div>

          {influencer.description && (
            <div className="mt-5 pt-4 border-t border-border">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
                Channel Description & Bio
              </p>
              <p className="text-sm text-text leading-relaxed whitespace-pre-line max-w-4xl">
                {influencer.description}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          {[
            { label: isYouTube ? 'Subscribers' : 'Followers', value: num(influencer.followers) },
            {
              label: 'Engagement Rate',
              value: hasSample && influencer.engagementRate ? `${influencer.engagementRate}%` : NOT_AVAILABLE,
              color: hasSample ? 'text-primary' : undefined,
            },
            { label: 'Avg Views / Video', value: num(influencer.avgViews) },
            { label: 'Avg Likes / Video', value: num(influencer.avgLikes) },
            { label: 'Avg Comments', value: num(influencer.avgComments) },
            { label: 'Total Channel Views', value: num(influencer.total_views) },
          ].map((m) => (
            <Card key={m.label} className="p-4">
              <p className="text-xs text-text-secondary">{m.label}</p>
              <p className={cn('text-xl font-bold mt-1', m.color)}>{m.value}</p>
            </Card>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-text-secondary px-1">
          {hasSample
            ? `Averages and engagement are Auralytics-derived from the ${sampleSize} most recent uploads reported by the YouTube Data API. YouTube does not publish these figures directly.`
            : 'YouTube did not return recent video statistics for this channel, so per-video averages are unavailable.'}
        </p>
      </div>

      {campaignMatch && <CampaignMatchCard match={campaignMatch} />}

      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Platform & Verification Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Platform Identifier</span>
              <span className="font-mono font-semibold">{influencer.external_id || 'N/A'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Total Content Count</span>
              <span className="font-semibold">
                {influencer.content_count ? `${formatNumber(influencer.content_count)} uploads` : NOT_AVAILABLE}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Latest Upload</span>
              <span className="font-semibold">
                {influencer.lastUploadAt
                  ? new Date(influencer.lastUploadAt).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })
                  : NOT_AVAILABLE}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Country / Region</span>
              <span className="font-semibold">{influencer.country || NOT_AVAILABLE}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-text-secondary">Data Source</span>
              <span className="font-mono font-semibold uppercase">{influencer.data_source || 'YouTube API v3'}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Campaign Status</span>
              <span className="font-semibold text-primary">
                {campaignMatch ? campaignMatch.status : shortlisted ? 'SHORTLISTED' : 'DISCOVERED'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Business Email</span>
              <span className="text-text-secondary">{influencer.businessEmail || 'Not available'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Instagram Profile</span>
              <span className="text-text-secondary">Not available</span>
            </div>
            <p className="pt-1 text-[11px] text-text-secondary leading-relaxed">
              The YouTube Data API does not expose creator business emails or linked Instagram accounts.
              Auralytics leaves these empty rather than guessing them.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function factorIcon(factor: MatchFactor) {
  if (!factor.available) return <MinusCircle className="h-4 w-4 text-text-secondary shrink-0 mt-0.5" />
  if ((factor.score ?? 0) >= 0.6) return <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
  return <CircleSlash className="h-4 w-4 text-warning shrink-0 mt-0.5" />
}

/** Explains exactly how the campaign match score was produced. */
function CampaignMatchCard({ match }: { match: CampaignCreator }) {
  const factors = match.match_reasons ?? []
  const availableWeight = factors.filter((f) => f.available).reduce((sum, f) => sum + f.weight, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold">Campaign Match</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row gap-5">
          <div className="flex flex-col items-center justify-center shrink-0 sm:w-32">
            {typeof match.match_score === 'number' ? (
              <>
                <ProgressRing value={match.match_score} size={84} stroke={7} color="#7C3AED" />
                <p className="text-xs text-text-secondary mt-2 text-center">Campaign fit</p>
              </>
            ) : (
              <p className="text-xs text-text-secondary text-center">
                Not enough campaign data to score this creator.
              </p>
            )}
          </div>

          <div className="flex-1 space-y-2.5">
            {factors.length === 0 && (
              <p className="text-xs text-text-secondary">No scoring breakdown was recorded for this creator.</p>
            )}
            {factors.map((factor) => (
              <div key={factor.key} className="flex items-start gap-2.5">
                {factorIcon(factor)}
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-text">{factor.label}</span>
                    <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono">
                      {factor.available ? `${factor.weight}% weight` : 'not scored'}
                    </Badge>
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5">{factor.detail}</p>
                </div>
              </div>
            ))}

            <div className="pt-2 mt-1 border-t border-border text-[11px] text-text-secondary space-y-1">
              <p>
                Score is a deterministic weighted average of the factors above
                {availableWeight > 0 && ` (${availableWeight}% of the total weighting was available)`}. Factors
                without real data are skipped rather than estimated.
              </p>
              {match.discovery_query && (
                <p>
                  Surfaced by the search query <span className="font-mono">"{match.discovery_query}"</span>. A
                  search context is not a verified creator location.
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
