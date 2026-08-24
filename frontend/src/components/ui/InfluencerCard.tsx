import { CheckCircle2, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn, formatNumber } from '@/utils'
import type { Influencer } from '@/types'
import { Avatar } from './Avatar'
import { Badge } from './Badge'
import { Button } from './Button'
import { Card } from './Card'
import { ProgressRing } from './ProgressRing'
import { PlatformIcon } from './PlatformIcon'

interface InfluencerCardProps {
  influencer: Influencer
  onShortlist?: (id: string) => void
  className?: string
  /** Campaign-specific match score, shown in place of the global AI score. */
  matchScore?: number | null
  /** Link target for the profile button, so campaign context can be preserved. */
  profileHref?: string
  shortlistLabel?: string
}

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

export function InfluencerCard({
  influencer,
  onShortlist,
  className,
  matchScore,
  profileHref,
  shortlistLabel,
}: InfluencerCardProps) {
  const isYouTube = (influencer.platform || '').toLowerCase() === 'youtube'
  const score = matchScore ?? influencer.aiMatchScore
  // Engagement is only meaningful when it was derived from a real video sample.
  const hasEngagement = (influencer.metricsSampleSize ?? 0) > 0 && !!influencer.engagementRate
  const hasAvgViews = (influencer.avgViews ?? 0) > 0
  const hasSubscribers = (influencer.followers ?? 0) > 0
  const detailHref = profileHref ?? `/app/discovery/${influencer.id}`

  return (
    <Card className={cn('p-4 hover:border-primary/35 hover:shadow-sm transition-all group flex flex-col justify-between', className)}>
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            {influencer.avatar ? (
              <img
                src={influencer.avatar}
                alt={influencer.name}
                className="h-12 w-12 rounded-full object-cover border border-border"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none'
                }}
              />
            ) : (
              <Avatar name={influencer.name} size="lg" />
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-sm font-semibold text-text truncate">{influencer.name}</h3>
                {influencer.verified && <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0" />}
              </div>
              <p className="text-xs text-text-secondary truncate">
                {influencer.username.startsWith('@') ? influencer.username : `@${influencer.username}`}
              </p>
              <div className="mt-1.5 flex items-center gap-1.5">
                <PlatformIcon platform={influencer.platform as any} showLabel />
                {influencer.data_source && (
                  <Badge variant="outline" className="text-[10px] py-0 px-1.5 uppercase tracking-wider font-mono">
                    {influencer.data_source}
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {typeof score === 'number' ? (
            <div className="flex flex-col items-center gap-1 shrink-0">
              <ProgressRing value={score} size={44} stroke={4} color="#7C3AED" />
              <span className="text-[10px] text-text-secondary font-medium">Match</span>
            </div>
          ) : (
            <span className="text-[11px] text-text-secondary font-mono bg-page px-2 py-1 rounded-md border border-border">
              {formatFreshness(influencer.source_fetched_at)}
            </span>
          )}
        </div>

        {influencer.niches && influencer.niches.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {influencer.niches.slice(0, 3).map((n) => (
              <Badge key={n} variant="outline">
                {n}
              </Badge>
            ))}
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 gap-y-2.5 gap-x-3 text-xs">
          <div>
            <p className="text-text-secondary">{isYouTube ? 'Subscribers' : 'Followers'}</p>
            <p className="font-semibold">
              {hasSubscribers ? formatNumber(influencer.followers) : NOT_AVAILABLE}
            </p>
          </div>
          <div>
            <p className="text-text-secondary">Engagement</p>
            <p className={cn('font-semibold', hasEngagement ? 'text-primary' : 'text-text-secondary')}>
              {hasEngagement ? `${influencer.engagementRate}%` : NOT_AVAILABLE}
            </p>
          </div>
          <div>
            <p className="text-text-secondary">Avg views</p>
            <p className="font-semibold">
              {hasAvgViews ? formatNumber(influencer.avgViews) : NOT_AVAILABLE}
            </p>
          </div>
          <div>
            <p className="text-text-secondary">Videos</p>
            <p className="font-semibold">
              {influencer.content_count ? formatNumber(influencer.content_count) : NOT_AVAILABLE}
            </p>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between text-xs pt-2 border-t border-border">
          <span className="text-text-secondary truncate max-w-[140px]">
            {influencer.country || influencer.location || 'Location N/A'}
          </span>
          {influencer.profile_url && (
            <a
              href={influencer.profile_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline font-medium inline-flex items-center gap-1 text-[11px]"
            >
              Open Channel <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <Link to={detailHref} className="flex-1">
          <Button variant="secondary" size="sm" className="w-full">
            View Profile
          </Button>
        </Link>
        <Button
          size="sm"
          className="flex-1"
          variant={influencer.shortlisted ? 'soft' : 'primary'}
          onClick={() => onShortlist?.(influencer.id)}
        >
          {shortlistLabel ?? (influencer.shortlisted ? 'Shortlisted' : 'Shortlist')}
        </Button>
      </div>
    </Card>
  )
}
