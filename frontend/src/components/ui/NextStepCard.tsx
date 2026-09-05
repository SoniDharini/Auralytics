import { ArrowRight, Loader2 } from 'lucide-react'
import { Badge } from './Badge'
import { Button } from './Button'
import { ProgressBar } from './ProgressBar'
import type { CampaignWorkflow } from '@/types'

interface NextStepCardProps {
  workflow: CampaignWorkflow
  busy?: boolean
  onAction: () => void
}

/** Compact next-action bar — same behavior, less vertical space. */
export function NextStepCard({ workflow, busy, onAction }: NextStepCardProps) {
  const action = workflow.next_action
  const disabled = busy || !action.enabled || action.running
  const failed = workflow.steps.some((s) => s.status === 'FAILED')
  const waiting = workflow.steps.some((s) => s.status === 'WAITING_APPROVAL')

  return (
    <div className="rounded-[14px] border border-primary/20 bg-primary-soft/30 px-3.5 py-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[10px] font-bold uppercase tracking-wide text-primary">Next</p>
            {failed ? (
              <Badge variant="danger">Failed</Badge>
            ) : waiting ? (
              <Badge variant="warning" pulse>
                Waiting
              </Badge>
            ) : action.running ? (
              <Badge variant="ai" pulse>
                In progress
              </Badge>
            ) : null}
            <span className="text-[11px] text-text-secondary tabular-nums">
              {workflow.progress_percentage}%
            </span>
          </div>
          <p className="text-sm font-semibold text-text mt-0.5 truncate">{action.label}</p>
          <p className="text-[11px] text-text-secondary line-clamp-1 mt-0.5">{action.description}</p>
          {workflow.blocking_reason && (
            <p className="text-[11px] text-danger mt-1">{workflow.blocking_reason}</p>
          )}
          <div className="mt-2 max-w-xs">
            <ProgressBar value={workflow.progress_percentage} size="sm" />
          </div>
        </div>
        <Button
          size="sm"
          className="gap-1.5 shrink-0 w-full sm:w-auto"
          onClick={onAction}
          disabled={disabled}
          variant={failed ? 'secondary' : 'primary'}
        >
          {(busy || action.running) && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {action.label}
          {!disabled && <ArrowRight className="h-3.5 w-3.5" />}
        </Button>
      </div>
    </div>
  )
}
