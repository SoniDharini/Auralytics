import { cn } from '@/utils'

interface StepIndicatorProps {
  steps: string[]
  current: number
  className?: string
}

export function StepIndicator({ steps, current, className }: StepIndicatorProps) {
  return (
    <ol className={cn('flex items-center gap-2 w-full overflow-x-auto', className)}>
      {steps.map((step, index) => {
        const n = index + 1
        const done = n < current
        const active = n === current
        return (
          <li key={step} className="flex items-center gap-2 min-w-0 flex-1">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={cn(
                  'h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0',
                  done && 'bg-primary text-white',
                  active && 'bg-primary text-white ring-4 ring-primary-soft',
                  !done && !active && 'bg-muted text-text-secondary',
                )}
              >
                {n}
              </span>
              <span
                className={cn(
                  'text-xs font-semibold truncate hidden sm:block',
                  active || done ? 'text-text' : 'text-text-secondary',
                )}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className={cn('h-px flex-1 min-w-4', done ? 'bg-primary' : 'bg-border')} />
            )}
          </li>
        )
      })}
    </ol>
  )
}
