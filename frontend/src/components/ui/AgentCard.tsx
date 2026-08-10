import { Bot, Clock } from 'lucide-react'
import { cn } from '@/utils'
import type { Agent } from '@/types'
import { Badge } from './Badge'
import { Card } from './Card'
import { ProgressBar } from './ProgressBar'

const statusVariant: Record<string, 'success' | 'warning' | 'default' | 'ai' | 'danger' | 'primary'> = {
  active: 'success',
  processing: 'ai',
  idle: 'default',
  completed: 'primary',
  error: 'danger',
}

interface AgentCardProps {
  agent: Agent
  className?: string
  compact?: boolean
}

export function AgentCard({ agent, className, compact }: AgentCardProps) {
  return (
    <Card className={cn('p-5 hover:border-primary/30 transition-all', className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl ai-gradient-bg text-white flex items-center justify-center shadow-sm">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text">{agent.name}</h3>
            <p className="text-xs text-text-secondary">{agent.role}</p>
          </div>
        </div>
        <Badge
          variant={statusVariant[agent.status] || 'default'}
          pulse={agent.status === 'active' || agent.status === 'processing'}
        >
          {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
        </Badge>
      </div>

      <p className="mt-4 text-sm text-text font-medium">{agent.currentTask}</p>
      <p className="mt-1 text-xs text-text-secondary">Last action: {agent.lastAction}</p>

      {typeof agent.progress === 'number' && (
        <div className="mt-3">
          <ProgressBar value={agent.progress} size="sm" showLabel />
        </div>
      )}

      {!compact && (
        <div className="mt-4 grid grid-cols-3 gap-3 pt-3 border-t border-border">
          <div>
            <p className="text-[11px] text-text-secondary">Completed</p>
            <p className="text-sm font-bold">{agent.tasksCompleted}</p>
          </div>
          <div>
            <p className="text-[11px] text-text-secondary">Avg time</p>
            <p className="text-sm font-bold">{agent.avgExecutionTime}</p>
          </div>
          <div>
            <p className="text-[11px] text-text-secondary">Success</p>
            <p className="text-sm font-bold">{agent.successRate}%</p>
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center gap-1.5 text-xs text-text-secondary">
        <Clock className="h-3.5 w-3.5" />
        Last active: {agent.lastActive}
      </div>
    </Card>
  )
}
