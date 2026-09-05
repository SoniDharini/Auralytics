import { Sparkles } from 'lucide-react'
import { cn } from '@/utils'
import type { Insight } from '@/types'
import { Button } from './Button'
import { Badge } from './Badge'
import { Card } from './Card'

interface InsightCardProps {
  insight: Insight
  onPrimary?: () => void
  onSecondary?: () => void
  primaryLabel?: string
  secondaryLabel?: string
  className?: string
}

export function InsightCard({
  insight,
  onPrimary,
  onSecondary,
  primaryLabel = 'Review Recommendation',
  secondaryLabel = 'View Details',
  className,
}: InsightCardProps) {
  return (
    <Card className={cn('p-4 border-l-4 border-l-ai ui-card-hover bg-gradient-to-br from-white to-violet-50/30', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-violet-50 text-ai flex items-center justify-center ring-1 ring-violet-100">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-text">{insight.title}</p>
              <Badge variant="ai">AI Generated</Badge>
            </div>
          </div>
        </div>
        <span className="text-xs font-semibold text-text-secondary">{insight.confidence}% conf.</span>
      </div>
      <p className="mt-3 text-sm text-text-secondary leading-relaxed">{insight.body}</p>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
        <span className="font-semibold text-primary">Impact: {insight.impact}</span>
        <span className="text-text-secondary">Action: {insight.action}</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {onPrimary && (
          <Button size="sm" onClick={onPrimary}>
            {primaryLabel}
          </Button>
        )}
        {onSecondary && (
          <Button size="sm" variant="secondary" onClick={onSecondary}>
            {secondaryLabel}
          </Button>
        )}
      </div>
    </Card>
  )
}
