import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bell,
  HelpCircle,
  Menu,
  Search,
  Bot,
  X,
  User,
  Settings,
  LogOut,
} from 'lucide-react'
import { api } from '@/services/api'
import { Avatar, Badge, Button } from '@/components/ui'
import { LogoutConfirmationModal } from '@/components/auth/LogoutConfirmationModal'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/utils'
import type { Agent, NotificationItem } from '@/types'

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [aiOpen, setAiOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [agentsList, setAgentsList] = useState<Agent[]>([])
  const [notificationsList] = useState<NotificationItem[]>([])
  const profileRef = useRef<HTMLDivElement>(null)


  useEffect(() => {
    let mounted = true
    api.agents
      .list()
      .then((data) => {
        if (mounted && data) setAgentsList(data)
      })
      .catch(() => {})

    return () => {
      mounted = false
    }
  }, [])

  const activeAgents = agentsList.filter((a) => a.status === 'active' || a.status === 'processing')
  const unread = notificationsList.filter((n) => !n.read).length

  const displayName = user?.full_name || 'Authenticated User'
  const displayEmail = user?.email || 'user@influenceos.ai'
  const displayRole = user?.role ? user.role.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase()) : 'Marketing Manager'

  useEffect(() => {
    if (!profileOpen) return
    const onPointerDown = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setProfileOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [profileOpen])

  const handleLogoutConfirm = async () => {
    setLogoutOpen(false)
    setProfileOpen(false)
    await logout()
    navigate('/login')
  }

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
              setProfileOpen(false)
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
              <span
                className={cn(
                  'absolute inline-flex h-full w-full rounded-full opacity-60',
                  activeAgents.length > 0 ? 'bg-success animate-pulse-dot' : 'bg-gray-400',
                )}
              />
              <span
                className={cn(
                  'relative inline-flex h-2 w-2 rounded-full',
                  activeAgents.length > 0 ? 'bg-success' : 'bg-gray-400',
                )}
              />
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
              {agentsList.length === 0 ? (
                <div className="py-8 text-center text-xs text-text-secondary">
                  <Bot className="h-8 w-8 mx-auto text-text-secondary/40 mb-2" />
                  <p className="font-semibold text-text">No active agents</p>
                  <p className="mt-1">Agents will coordinate when campaigns are active.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[360px] overflow-y-auto">
                  {agentsList.slice(0, 4).map((agent) => (
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
                    </div>
                  ))}
                </div>
              )}
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
              setProfileOpen(false)
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
              {notificationsList.length === 0 ? (
                <div className="py-8 text-center text-xs text-text-secondary">
                  <Bell className="h-8 w-8 mx-auto text-text-secondary/40 mb-2" />
                  <p className="font-semibold text-text">No unread notifications</p>
                  <p className="mt-1">You're completely up to date.</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[320px] overflow-y-auto">
                  {notificationsList.slice(0, 5).map((n) => (
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
              )}
            </div>
          )}
        </div>

        <Button variant="ghost" size="icon" aria-label="Help" className="hidden sm:inline-flex">
          <HelpCircle className="h-4.5 w-4.5" />
        </Button>

        <div className="h-6 w-px bg-border mx-1 hidden sm:block" />

        <div className="relative" ref={profileRef}>
          <button
            type="button"
            className={cn(
              'flex items-center gap-2 rounded-[10px] px-1.5 py-1 hover:bg-muted',
              profileOpen && 'bg-muted',
            )}
            aria-expanded={profileOpen}
            aria-haspopup="menu"
            aria-label="User menu"
            onClick={() => {
              setProfileOpen((v) => !v)
              setAiOpen(false)
              setNotifOpen(false)
            }}
          >
            <Avatar name={displayName} size="sm" />
            <div className="hidden xl:block text-left">
              <p className="text-xs font-semibold leading-tight">{displayName.split(' ')[0]}</p>
              <p className="text-[10px] text-text-secondary">{displayRole}</p>
            </div>
          </button>

          {profileOpen && (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-[260px] bg-white border border-border rounded-[14px] shadow-xl py-2 animate-fade-in z-50"
            >
              <div className="px-3 py-2.5 flex items-center gap-3">
                <Avatar name={displayName} size="md" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-text truncate">{displayName}</p>
                  <p className="text-xs text-text-secondary truncate">{displayEmail}</p>
                </div>
              </div>

              <div className="my-1.5 h-px bg-border" />

              <Link
                to="/app/settings"
                role="menuitem"
                onClick={() => setProfileOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 mx-1 rounded-[10px] text-sm font-medium text-text hover:bg-muted"
              >
                <User className="h-4 w-4 text-text-secondary" />
                Profile
              </Link>
              <Link
                to="/app/settings"
                role="menuitem"
                onClick={() => setProfileOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2 mx-1 rounded-[10px] text-sm font-medium text-text hover:bg-muted"
              >
                <Settings className="h-4 w-4 text-text-secondary" />
                Settings
              </Link>

              <div className="my-1.5 h-px bg-border" />

              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setProfileOpen(false)
                  setLogoutOpen(true)
                }}
                className="w-[calc(100%-8px)] mx-1 flex items-center gap-2.5 px-3 py-2 rounded-[10px] text-sm font-medium text-danger hover:bg-red-50"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>

      <LogoutConfirmationModal
        open={logoutOpen}
        onClose={() => setLogoutOpen(false)}
        onConfirm={handleLogoutConfirm}
      />
    </header>
  )
}
