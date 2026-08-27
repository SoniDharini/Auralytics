import { ArrowRight, Loader2 } from 'lucide-react'
import { Badge } from './Badge'
import { Button } from './Button'
import { Card, CardContent } from './Card'
import { ProgressBar } from './ProgressBar'
import type { CampaignWorkflow } from '@/types'

interface NextStepCardProps {
  workflow: CampaignWorkflow
  busy?: boolean
  onAction: () => void
}

export function NextStepCard({ workflow, busy, onAction }: NextStepCardProps) {
  const action = workflow.next_action
  const disabled = busy || !action.enabled || action.running
  const failed = workflow.steps.some((s) => s.status === 'FAILED')
  const waiting = workflow.steps.some((s) => s.status === 'WAITING_APPROVAL')

  return (
    <Card className="border-primary/20 bg-primary-soft/40">
      <CardContent className="pt-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-primary">Next Step</p>
            <h3 className="text-lg font-bold text-text mt-1">{action.label}</h3>
            <p className="text-sm text-text-secondary mt-1 leading-relaxed">{action.description}</p>
            {workflow.blocking_reason && (
              <p className="text-xs text-danger mt-2">{workflow.blocking_reason}</p>
            )}
          </div>
          {failed ? (
            <Badge variant="danger">Failed</Badge>
          ) : waiting ? (
            <Badge variant="warning" pulse>
              Waiting for approval
            </Badge>
          ) : action.running ? (
            <Badge variant="ai" pulse>
              In progress
            </Badge>
          ) : null}
        </div>

        <ProgressBar value={workflow.progress_percentage} showLabel size="sm" />

        <Button
          className="gap-2 w-full sm:w-auto"
          onClick={onAction}
          disabled={disabled}
          variant={failed ? 'secondary' : 'primary'}
        >
          {(busy || action.running) && <Loader2 className="h-4 w-4 animate-spin" />}
          {action.label}
          {!disabled && <ArrowRight className="h-4 w-4" />}
        </Button>
      </CardContent>
    </Card>
  )
}
