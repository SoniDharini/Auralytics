import { AlertCircle, Check, Circle, Loader2, Lock } from 'lucide-react'
import { cn } from '@/utils'
import type { CampaignWorkflowStep } from '@/types'

interface CampaignJourneyProps {
  steps: CampaignWorkflowStep[]
  onStepClick?: (step: CampaignWorkflowStep) => void
}

const statusClass: Record<string, string> = {
  COMPLETED: 'bg-primary text-white',
  CURRENT: 'bg-primary text-white ring-4 ring-primary-soft',
  NEXT: 'bg-primary text-white ring-4 ring-primary-soft',
  WAITING_APPROVAL: 'bg-amber-500 text-white ring-4 ring-amber-100',
  FAILED: 'bg-danger text-white',
  LOCKED: 'bg-muted text-text-secondary',
  PENDING: 'bg-muted text-text-secondary',
}

function StepGlyph({ status }: { status: string }) {
  if (status === 'COMPLETED') return <Check className="h-3.5 w-3.5" />
  if (status === 'FAILED') return <AlertCircle className="h-3.5 w-3.5" />
  if (status === 'LOCKED' || status === 'PENDING') return <Lock className="h-3 w-3" />
  if (status === 'CURRENT') return <Loader2 className="h-3.5 w-3.5 animate-spin" />
  return <Circle className="h-3 w-3 fill-current" />
}

export function CampaignJourney({ steps, onStepClick }: CampaignJourneyProps) {
  return (
    <ol className="flex flex-col md:flex-row md:items-center gap-3 md:gap-2 w-full">
      {steps.map((step, index) => {
        const clickable = Boolean(step.route) && step.status !== 'LOCKED' && step.status !== 'PENDING'
        const labelClass =
          step.status === 'LOCKED' || step.status === 'PENDING'
            ? 'text-text-secondary'
            : 'text-text'

        const inner = (
          <div className="flex items-center gap-2 min-w-0">
            <span
              className={cn(
                'h-7 w-7 rounded-full flex items-center justify-center shrink-0',
                statusClass[step.status] || statusClass.PENDING,
              )}
              title={step.hint || step.status}
            >
              <StepGlyph status={step.status} />
            </span>
            <span className={cn('text-xs font-semibold truncate', labelClass)}>{step.label}</span>
          </div>
        )

        return (
          <li key={step.key} className="flex md:items-center gap-2 min-w-0 md:flex-1">
            <div className="flex flex-col md:flex-row md:items-center gap-2 min-w-0 flex-1">
              {clickable ? (
                <button
                  type="button"
                  onClick={() => onStepClick?.(step)}
                  className="text-left hover:opacity-80 transition min-w-0"
                >
                  {inner}
                </button>
              ) : (
                inner
              )}
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    'md:h-px md:flex-1 md:min-w-4 w-px h-4 ml-3.5 md:ml-0',
                    step.status === 'COMPLETED' ? 'bg-primary' : 'bg-border',
                  )}
                />
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
