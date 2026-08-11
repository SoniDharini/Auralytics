import { useEffect, useMemo, useState } from 'react'
import {
  CheckCircle2,
  Info,
  User,
  Zap,
} from 'lucide-react'
import { agents as initialAgents, agentTimeline as initialTimeline } from '@/mock-data'
import { api } from '@/services/api'
import { AgentCard, Badge, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'
import { cn } from '@/utils'
import type { Agent, TimelineEvent } from '@/types'

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
  const [agentsList, setAgentsList] = useState<Agent[]>(initialAgents)
  const [timeline, setTimeline] = useState<TimelineEvent[]>(initialTimeline)

  useEffect(() => {
    let mounted = true
    api.agents
      .list()
      .then((data) => {
        if (mounted && data && data.length > 0) {
          setAgentsList(data)
        }
      })
      .catch(() => {})

    api.agents
      .getTimeline()
      .then((events) => {
        if (mounted && events && events.length > 0) {
          setTimeline(events)
        }
      })
      .catch(() => {})

    return () => {
      mounted = false
    }
  }, [])

  const activeCount = useMemo(
    () => agentsList.filter((a) => a.status === 'active' || a.status === 'processing').length,
    [agentsList],
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
        {agentsList.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Autonomous Activity Feed</CardTitle>
            <span className="text-xs text-text-secondary font-mono">Live coordination log</span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
            {timeline.map((event) => {
              const s = timelineStyles[event.type] ?? timelineStyles.info
              const Icon = s.icon
              return (
                <div key={event.id} className="relative flex items-start gap-3">
                  <div
                    className={cn(
                      'absolute -left-6 mt-1 h-5 w-5 rounded-full border-2 border-white flex items-center justify-center',
                      s.dot,
                    )}
                  >
                    <Icon className="h-2.5 w-2.5 text-white" />
                  </div>
                  <div className="flex-1 rounded-xl border border-border bg-page p-3 text-xs">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-semibold text-text">{event.agent}</span>
                      <span className="text-[11px] text-text-secondary font-mono">{event.time}</span>
                    </div>
                    <p className="text-text-secondary">{event.message}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
