import { useMemo } from 'react'
import {
  Activity,
  Bot,
  CheckCircle2,
  Info,
  User,
  Zap,
} from 'lucide-react'
import { agents, agentTimeline } from '@/mock-data'
import { AgentCard, Badge, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'
import { cn } from '@/utils'
import type { TimelineEvent } from '@/types'

const timelineStyles: Record<
  TimelineEvent['type'],
  { icon: React.ComponentType<{ className?: string }>; dot: string; bg: string }
> = {
  info: { icon: Info, dot: 'bg-primary', bg: 'bg-primary-soft' },
  success: { icon: CheckCircle2, dot: 'bg-success', bg: 'bg-green-50' },
  action: { icon: Zap, dot: 'bg-ai', bg: 'bg-violet-50' },
  human: { icon: User, dot: 'bg-warning', bg: 'bg-amber-50' },
}

export function AgentsPage() {
  const activeCount = useMemo(
    () => agents.filter((a) => a.status === 'active' || a.status === 'processing').length,
    [],
  )

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-[32px] font-bold tracking-tight">Your Autonomous Marketing Team</h1>
          <p className="text-text-secondary mt-1">
            Specialized AI agents working together on your campaigns.
          </p>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-border bg-white px-4 py-3 shadow-sm">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-40" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-success" />
          </span>
          <div>
            <p className="text-sm font-bold text-text">
              {activeCount} agent{activeCount !== 1 ? 's' : ''} active now
            </p>
            <p className="text-xs text-text-secondary">Supervisor orchestrating workflow</p>
          </div>
          <Badge variant="success" pulse>
            Live
          </Badge>
        </div>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <div>
              <CardTitle>Agent Activity Timeline</CardTitle>
              <p className="text-sm text-text-secondary mt-0.5">
                Real-time log of agent and human actions
              </p>
            </div>
          </div>
          <Badge variant="ai">
            <Bot className="h-3 w-3" /> Today
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <div className="absolute left-[15px] top-2 bottom-2 w-px bg-border" />
            <ul className="space-y-1">
              {agentTimeline.map((event, i) => (
                <TimelineRow key={event.id} event={event} isLast={i === agentTimeline.length - 1} />
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function TimelineRow({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const style = timelineStyles[event.type]
  const Icon = style.icon

  return (
    <li className={cn('relative flex gap-4 pb-5', isLast && 'pb-0')}>
      <div
        className={cn(
          'relative z-10 h-8 w-8 rounded-full flex items-center justify-center shrink-0 border-2 border-white shadow-sm',
          style.bg,
        )}
      >
        <Icon className={cn('h-3.5 w-3.5', event.type === 'info' && 'text-primary', event.type === 'success' && 'text-success', event.type === 'action' && 'text-ai', event.type === 'human' && 'text-amber-600')} />
      </div>
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono font-semibold text-text-secondary">{event.time}</span>
          <span className="text-sm font-semibold">{event.agent}</span>
          <span
            className={cn(
              'text-[10px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded',
              style.bg,
              event.type === 'info' && 'text-primary',
              event.type === 'success' && 'text-success',
              event.type === 'action' && 'text-ai',
              event.type === 'human' && 'text-amber-700',
            )}
          >
            {event.type}
          </span>
        </div>
        <p className="text-sm text-text-secondary mt-0.5">{event.message}</p>
      </div>
    </li>
  )
}
