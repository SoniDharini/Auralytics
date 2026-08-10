import { cn } from '@/utils'
import { TrendingDown, TrendingUp } from 'lucide-react'
import type { MetricCard as MetricCardType } from '@/types'

interface MetricCardProps {
  metric: MetricCardType
  className?: string
}

export function MetricCard({ metric, className }: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-surface border border-border rounded-[14px] p-5 hover:border-primary/30 hover:shadow-sm transition-all',
        className,
      )}
    >
      <p className="text-sm font-medium text-text-secondary">{metric.label}</p>
      <div className="mt-2 flex items-end justify-between gap-3">
        <p className="text-[28px] leading-none font-bold tracking-tight text-text">{metric.value}</p>
        {metric.sparkline && (
          <div className="flex items-end gap-0.5 h-8">
            {metric.sparkline.map((v, i) => {
              const max = Math.max(...metric.sparkline!)
              const h = Math.max(12, (v / max) * 100)
              return (
                <span
                  key={i}
                  className="w-1.5 rounded-sm bg-primary/25 last:bg-primary"
                  style={{ height: `${h}%` }}
                />
              )
            })}
          </div>
        )}
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs">
        {metric.trend && (
          <span
            className={cn(
              'inline-flex items-center gap-1 font-semibold',
              metric.trend.positive ? 'text-success' : 'text-warning',
            )}
          >
            {metric.trend.positive ? (
              <TrendingUp className="h-3.5 w-3.5" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5" />
            )}
            {metric.trend.value}
          </span>
        )}
        <span className="text-text-secondary">{metric.context}</span>
      </div>
    </div>
  )
}
