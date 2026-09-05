import { AlertCircle, Check, Circle, Loader2, Lock } from 'lucide-react'
import { cn } from '@/utils'
import type { CampaignWorkflowStep } from '@/types'

interface CampaignJourneyProps {
  steps: CampaignWorkflowStep[]
  onStepClick?: (step: CampaignWorkflowStep) => void
  compact?: boolean
}

const statusClass: Record<string, string> = {
  COMPLETED: 'bg-primary text-white',
  CURRENT:
    'bg-primary text-white ring-[3px] ring-primary-soft shadow-[0_0_12px_color-mix(in_srgb,var(--auralytics-primary)_40%,transparent)]',
  NEXT: 'bg-primary/90 text-white ring-[3px] ring-primary-soft',
  WAITING_APPROVAL: 'bg-amber-500 text-white ring-[3px] ring-amber-500/25',
  FAILED: 'bg-danger text-white',
  LOCKED: 'bg-muted text-text-secondary border border-border',
  PENDING: 'bg-muted text-text-secondary border border-border',
}

function StepGlyph({ status }: { status: string }) {
  if (status === 'COMPLETED') return <Check className="h-3 w-3" />
  if (status === 'FAILED') return <AlertCircle className="h-3 w-3" />
  if (status === 'LOCKED' || status === 'PENDING') return <Lock className="h-2.5 w-2.5" />
  if (status === 'CURRENT') return <Loader2 className="h-3 w-3 animate-spin" />
  return <Circle className="h-2.5 w-2.5 fill-current" />
}

export function CampaignJourney({ steps, onStepClick, compact = true }: CampaignJourneyProps) {
  return (
    <ol className="flex w-full items-start overflow-x-auto gap-0 pb-0.5">
      {steps.map((step, index) => {
        const clickable = Boolean(step.route) && step.status !== 'LOCKED' && step.status !== 'PENDING'
        const isActive =
          step.status === 'CURRENT' || step.status === 'NEXT' || step.status === 'WAITING_APPROVAL'
        const labelClass =
          step.status === 'LOCKED' || step.status === 'PENDING'
            ? 'text-text-secondary'
            : isActive
              ? 'text-primary'
              : 'text-text'

        const content = (
          <>
            <span
              className={cn(
                'h-6 w-6 rounded-full flex items-center justify-center shrink-0 z-[1]',
                statusClass[step.status] || statusClass.PENDING,
              )}
              title={step.hint || step.status}
            >
              <StepGlyph status={step.status} />
            </span>
            <span
              className={cn(
                'mt-1.5 text-[10px] font-semibold text-center leading-tight max-w-[4.75rem] truncate',
                compact ? '' : 'sm:max-w-none',
                labelClass,
              )}
            >
              {step.label}
            </span>
          </>
        )

        return (
          <li key={step.key} className="flex items-start min-w-0 flex-1">
            <div className="flex flex-col items-center min-w-[4.25rem] flex-1 px-0.5">
              {clickable ? (
                <button
                  type="button"
                  onClick={() => onStepClick?.(step)}
                  className="flex flex-col items-center w-full hover:opacity-90 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 rounded-md"
                >
                  {content}
                </button>
              ) : (
                <div className="flex flex-col items-center w-full">{content}</div>
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  'h-0.5 flex-1 min-w-[6px] mt-3 rounded-full shrink',
                  step.status === 'COMPLETED'
                    ? 'bg-gradient-to-r from-primary to-accent'
                    : 'bg-border',
                )}
                aria-hidden
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
