import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  Loader2,
  MapPin,
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
  useToast,
} from '@/components/ui'
import { PlatformIcon } from '@/components/ui/PlatformIcon'
import { cn, formatINR, formatNumber } from '@/utils'
import type { Influencer } from '@/types'

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
  const { toast } = useToast()
  const [influencer, setInfluencer] = useState<Influencer | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [shortlisted, setShortlisted] = useState(false)

  const loadData = () => {
    if (!id) return
    setLoading(true)
    api.influencers
      .get(id)
      .then((data) => {
        if (data) {
          setInfluencer(data)
          setShortlisted(!!data.shortlisted)
        }
      })
      .catch(() => {
        setInfluencer(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    loadData()
  }, [id])

  const toggleShortlist = async () => {
    if (!id) return
    const nextState = !shortlisted
    setShortlisted(nextState)
    try {
      await api.influencers.toggleShortlist(id)
      toast({
        type: 'success',
        title: nextState ? 'Shortlisted' : 'Removed from shortlist',
        description: `${influencer?.name || 'Creator'} shortlist status updated.`,
      })
    } catch {
      setShortlisted(!nextState)
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
              {influencer.avatar ? (
                <img
                  src={influencer.avatar}
                  alt={influencer.name}
                  className="h-16 w-16 rounded-full object-cover border border-border"
                />
              ) : (
                <Avatar name={influencer.name} size="xl" />
              )}
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

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {[
          { label: isYouTube ? 'Subscribers' : 'Followers', value: formatNumber(influencer.followers || 0) },
          { label: 'Engagement Rate', value: `${influencer.engagementRate || 0}%`, color: 'text-primary font-bold' },
          { label: 'Avg Views / Video', value: formatNumber(influencer.avgViews || 0) },
          { label: 'Avg Likes / Video', value: formatNumber(influencer.avgLikes || 0) },
          { label: 'Avg Comments', value: formatNumber(influencer.avgComments || 0) },
          {
            label: 'Estimated Cost',
            value: influencer.estimatedCost ? formatINR(influencer.estimatedCost, true) : 'Not Available',
          },
        ].map((m) => (
          <Card key={m.label} className="p-4">
            <p className="text-xs text-text-secondary">{m.label}</p>
            <p className={cn('text-xl font-bold mt-1', m.color)}>{m.value}</p>
          </Card>
        ))}
      </div>

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
              <span className="font-semibold">{formatNumber(influencer.content_count || 0)} uploads</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Total Channel Views</span>
              <span className="font-semibold">{formatNumber(influencer.total_views || 0)}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Country / Region</span>
              <span className="font-semibold">{influencer.country || influencer.location || 'Global'}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-text-secondary">Data Source</span>
              <span className="font-mono font-semibold uppercase">{influencer.data_source || 'YouTube API v3'}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Outreach & Collaboration Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Shortlist Status</span>
              <span className="font-semibold capitalize text-primary">
                {shortlisted ? 'Shortlisted' : 'Not Shortlisted'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Negotiation Stage</span>
              <span className="font-semibold capitalize">{influencer.status || 'not_contacted'}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-text-secondary">Direct Contact Email</span>
              <span className="text-text-secondary">Not Available (Pending agent outreach)</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
