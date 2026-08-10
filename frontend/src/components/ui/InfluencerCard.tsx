import { CheckCircle2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn, formatINR, formatNumber } from '@/utils'
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
}

export function InfluencerCard({ influencer, onShortlist, className }: InfluencerCardProps) {
  return (
    <Card className={cn('p-4 hover:border-primary/35 hover:shadow-sm transition-all group', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={influencer.name} size="lg" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-semibold text-text truncate">{influencer.name}</h3>
              {influencer.verified && <CheckCircle2 className="h-3.5 w-3.5 text-primary shrink-0" />}
            </div>
            <p className="text-xs text-text-secondary">@{influencer.username}</p>
            <div className="mt-1.5">
              <PlatformIcon platform={influencer.platform} showLabel />
            </div>
          </div>
        </div>
        <ProgressRing value={influencer.aiMatchScore} size={48} stroke={4} color="#7C3AED" />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {influencer.niches.map((n) => (
          <Badge key={n} variant="outline">
            {n}
          </Badge>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-y-2.5 gap-x-3 text-xs">
        <div>
          <p className="text-text-secondary">Followers</p>
          <p className="font-semibold">{formatNumber(influencer.followers)}</p>
        </div>
        <div>
          <p className="text-text-secondary">Engagement</p>
          <p className="font-semibold">{influencer.engagementRate}%</p>
        </div>
        <div>
          <p className="text-text-secondary">Avg views</p>
          <p className="font-semibold">{formatNumber(influencer.avgViews)}</p>
        </div>
        <div>
          <p className="text-text-secondary">Est. cost</p>
          <p className="font-semibold">{formatINR(influencer.estimatedCost, true)}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="text-text-secondary">{influencer.location}</span>
        <span className="font-semibold text-primary">Pred. ROAS {influencer.predictedRoas}x</span>
      </div>

      <div className="mt-4 flex gap-2">
        <Link to={`/app/discovery/${influencer.id}`} className="flex-1">
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
          {influencer.shortlisted ? 'Shortlisted' : 'Shortlist'}
        </Button>
      </div>
    </Card>
  )
}
