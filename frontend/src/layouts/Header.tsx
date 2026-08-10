import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell,
  HelpCircle,
  Menu,
  Search,
  Bot,
  X,
} from 'lucide-react'
import { agents, notifications, workspace } from '@/mock-data'
import { Avatar, Badge, Button, ProgressBar } from '@/components/ui'
import { cn } from '@/utils'

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const [aiOpen, setAiOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const activeAgents = agents.filter((a) => a.status === 'active' || a.status === 'processing')
  const unread = notifications.filter((n) => !n.read).length

  return (
    <header className="sticky top-0 z-20 h-16 bg-white/90 backdrop-blur border-b border-border flex items-center gap-3 px-4 lg:px-6">
      <button
        className="lg:hidden h-9 w-9 inline-flex items-center justify-center rounded-[10px] hover:bg-muted"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="hidden md:flex flex-1 max-w-md items-center gap-2 h-10 px-3 rounded-[10px] border border-border bg-page">
        <Search className="h-4 w-4 text-text-secondary" />
        <input
          placeholder="Search campaigns, creators, contracts..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-text-secondary"
          aria-label="Global search"
        />
        <kbd className="hidden lg:inline text-[10px] text-text-secondary bg-white border border-border rounded px-1.5 py-0.5">
          ⌘K
        </kbd>
      </div>

      <div className="flex-1 md:hidden" />

      <div className="flex items-center gap-1.5 ml-auto">
        <div className="relative">
          <button
            onClick={() => {
              setAiOpen((v) => !v)
              setNotifOpen(false)
            }}
            className={cn(
              'inline-flex items-center gap-2 h-9 px-3 rounded-full text-xs font-semibold border transition',
              aiOpen
                ? 'bg-primary-soft border-primary/30 text-primary'
                : 'bg-white border-border text-text hover:bg-muted',
            )}
            aria-expanded={aiOpen}
            aria-label="AI activity"
          >
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-60 animate-pulse-dot" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            <Bot className="h-3.5 w-3.5 text-ai hidden sm:block" />
            <span>{activeAgents.length} Agents Active</span>
          </button>

          {aiOpen && (
            <div className="absolute right-0 mt-2 w-[340px] bg-white border border-border rounded-[14px] shadow-xl p-3 animate-fade-in z-50">
              <div className="flex items-center justify-between mb-2 px-1">
                <p className="text-sm font-semibold">AI Activity</p>
                <button onClick={() => setAiOpen(false)} aria-label="Close">
                  <X className="h-4 w-4 text-text-secondary" />
                </button>
              </div>
              <div className="space-y-2 max-h-[360px] overflow-y-auto">
                {agents.slice(0, 4).map((agent) => (
                  <div key={agent.id} className="rounded-[12px] border border-border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold">{agent.name}</p>
                      <Badge
                        variant={
                          agent.status === 'active' || agent.status === 'processing'
                            ? 'success'
                            : agent.status === 'completed'
                              ? 'primary'
                              : 'default'
                        }
                        pulse={agent.status === 'active' || agent.status === 'processing'}
                      >
                        {agent.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-text-secondary mt-1">{agent.currentTask}</p>
                    {agent.startedAt && (
                      <p className="text-[11px] text-text-secondary mt-1">Started {agent.startedAt}</p>
                    )}
                    {typeof agent.progress === 'number' && (
                      <div className="mt-2">
                        <ProgressBar value={agent.progress} size="sm" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <Link
                to="/app/agents"
                onClick={() => setAiOpen(false)}
                className="mt-2 block text-center text-xs font-semibold text-primary hover:underline py-1"
              >
                Open AI Agent Center
              </Link>
            </div>
          )}
        </div>

        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Notifications"
            onClick={() => {
              setNotifOpen((v) => !v)
              setAiOpen(false)
            }}
          >
            <Bell className="h-4.5 w-4.5" />
            {unread > 0 && (
              <span className="absolute top-1.5 right-1.5 h-4 min-w-4 px-1 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center">
                {unread}
              </span>
            )}
          </Button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-[360px] bg-white border border-border rounded-[14px] shadow-xl p-3 animate-fade-in z-50">
              <div className="flex items-center justify-between mb-2 px-1">
                <p className="text-sm font-semibold">Notifications</p>
                <Link
                  to="/app/notifications"
                  onClick={() => setNotifOpen(false)}
                  className="text-xs font-semibold text-primary"
                >
                  View all
                </Link>
              </div>
              <div className="space-y-2 max-h-[320px] overflow-y-auto">
                {notifications.slice(0, 5).map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      'rounded-[12px] border p-3',
                      n.read ? 'border-border bg-white' : 'border-primary/20 bg-primary-soft/40',
                    )}
                  >
                    <p className="text-sm font-semibold">{n.title}</p>
                    <p className="text-xs text-text-secondary mt-0.5">{n.body}</p>
                    <p className="text-[11px] text-text-secondary mt-1.5">{n.timestamp}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <Button variant="ghost" size="icon" aria-label="Help" className="hidden sm:inline-flex">
          <HelpCircle className="h-4.5 w-4.5" />
        </Button>

        <div className="h-6 w-px bg-border mx-1 hidden sm:block" />

        <button className="flex items-center gap-2 rounded-[10px] px-1.5 py-1 hover:bg-muted">
          <Avatar name={workspace.user} size="sm" />
          <div className="hidden xl:block text-left">
            <p className="text-xs font-semibold leading-tight">{workspace.user.split(' ')[0]}</p>
            <p className="text-[10px] text-text-secondary">{workspace.role}</p>
          </div>
        </button>
      </div>
    </header>
  )
}
