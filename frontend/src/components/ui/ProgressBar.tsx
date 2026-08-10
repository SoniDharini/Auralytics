import { cn } from '@/utils'

interface ProgressBarProps {
  value: number
  max?: number
  className?: string
  barClassName?: string
  showLabel?: boolean
  size?: 'sm' | 'md'
}

export function ProgressBar({
  value,
  max = 100,
  className,
  barClassName,
  showLabel,
  size = 'md',
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between text-xs text-text-secondary mb-1.5">
          <span>Progress</span>
          <span className="font-semibold text-text">{Math.round(pct)}%</span>
        </div>
      )}
      <div className={cn('w-full rounded-full bg-muted overflow-hidden', size === 'sm' ? 'h-1.5' : 'h-2')}>
        <div
          className={cn('h-full rounded-full bg-primary transition-all duration-700 ease-out', barClassName)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
