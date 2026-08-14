import { useEffect, useMemo, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  Info,
  User,
  Zap,
} from 'lucide-react'

import { api } from '@/services/api'
import { AgentCard, Badge, Card, CardContent, CardHeader, CardTitle } from '@/components/ui'
import { cn } from '@/utils'
import type { Agent, TimelineEvent } from '@/types'

const defaultAgents: Agent[] = [
  {
    id: 'agent-supervisor',
    name: 'Supervisor Agent',
    role: 'Campaign Orchestrator & Coordinator',
    status: 'idle',
    currentTask: 'Awaiting campaign launch',
    lastAction: 'Standing by to coordinate workflow',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
  {
    id: 'agent-strategy',
    name: 'Strategy Agent',
    role: 'Budget Allocation & Creator Mix Strategy',
    status: 'idle',
    currentTask: 'Awaiting campaign brief',
    lastAction: 'Standing by for audience analysis',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
  {
    id: 'agent-discovery',
    name: 'Discovery Agent',
    role: 'Influencer Search & Audience Fit Scoring',
    status: 'idle',
    currentTask: 'Awaiting creator search criteria',
    lastAction: 'Standing by to scan influencer catalog',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
  {
    id: 'agent-outreach',
    name: 'Outreach Agent',
    role: 'Personalized DM & Email Communication',
    status: 'idle',
    currentTask: 'Awaiting creator shortlist',
    lastAction: 'Standing by for pitch preparation',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
  {
    id: 'agent-contract',
    name: 'Contract Agent',
    role: 'Contract Generation & AI Risk Review',
    status: 'idle',
    currentTask: 'Awaiting agreement terms',
    lastAction: 'Standing by for clause verification',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
  {
    id: 'agent-performance',
    name: 'Performance Agent',
    role: 'Real-time Tracking & ROI Optimization',
    status: 'idle',
    currentTask: 'Awaiting live campaign metrics',
    lastAction: 'Standing by for ROAS tracking',
    tasksCompleted: 0,
    avgExecutionTime: '0.0s',
    successRate: 100,
    lastActive: 'Idle',
  },
]

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
  const [agentsList, setAgentsList] = useState<Agent[]>(defaultAgents)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])

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
            <span
              className={cn(
                'absolute inline-flex h-full w-full rounded-full opacity-40',
                activeCount > 0 ? 'bg-success animate-ping' : 'bg-gray-400',
              )}
            />
            <span
              className={cn(
                'relative inline-flex rounded-full h-3 w-3',
                activeCount > 0 ? 'bg-success' : 'bg-gray-400',
              )}
            />
          </span>
          <div>
            <p className="text-sm font-bold text-text">
              {activeCount} agent{activeCount !== 1 ? 's' : ''} active now
            </p>
            <p className="text-xs text-text-secondary">
              {activeCount > 0 ? 'Supervisor orchestrating workflow' : 'Agents standing by'}
            </p>
          </div>
          <Badge variant={activeCount > 0 ? 'success' : 'default'} pulse={activeCount > 0}>
            {activeCount > 0 ? 'Live' : 'Idle'}
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
          {timeline.length === 0 ? (
            <div className="text-center py-10 text-text-secondary">
              <Bot className="h-10 w-10 mx-auto text-text-secondary/40 mb-3" />
              <p className="font-semibold text-text">No agent activity yet</p>
              <p className="text-xs mt-1">AI agent coordination events will appear here once a campaign workflow is started.</p>
            </div>
          ) : (
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
          )}
        </CardContent>
      </Card>
    </div>
  )
}
