import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Megaphone,
  Search,
  Send,
  FileText,
  BarChart3,
  Bot,
  CheckSquare,
  FileBarChart,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/utils'
import { Avatar } from '@/components/ui'
import { useAuth } from '@/context/AuthContext'

const mainNav = [
  { to: '/app', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/app/campaigns', label: 'Campaigns', icon: Megaphone },
  { to: '/app/discovery', label: 'Influencer Discovery', icon: Search },
  { to: '/app/outreach', label: 'Outreach', icon: Send },
  { to: '/app/contracts', label: 'Contracts', icon: FileText },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/agents', label: 'AI Agent Center', icon: Bot },
  { to: '/app/approvals', label: 'Approval Center', icon: CheckSquare },
  { to: '/app/reports', label: 'Reports', icon: FileBarChart },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  mobileOpen: boolean
  onMobileClose: () => void
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const navigate = useNavigate()
  const { user } = useAuth()

  const displayName = user?.full_name || 'Aaditya Sharma'
  const displayRole = user?.role ? user.role.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase()) : 'Marketing Manager'
  const displayOrg = user?.company_name || 'InfluenceOS'

  const content = (
    <div className="flex h-full flex-col">
      <div className={cn('flex items-center gap-2.5 px-4 h-16 border-b border-border', collapsed && 'justify-center px-2')}>
        <button
          onClick={() => navigate('/app')}
          className="flex items-center gap-2.5 min-w-0"
          aria-label="InfluenceOS home"
        >
          <div className="h-8 w-8 rounded-lg ai-gradient-bg flex items-center justify-center text-white font-bold text-sm shrink-0">
            A
          </div>
          {!collapsed && (
            <div className="min-w-0 text-left">
              <p className="text-sm font-bold text-text leading-tight">InfluenceOS</p>
              <p className="text-[10px] text-text-secondary truncate">From Discovery to ROI</p>
            </div>
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <p className={cn('px-3 text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2', collapsed && 'sr-only')}>
          Main Menu
        </p>
        {mainNav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-sm font-medium transition group',
                isActive
                  ? 'bg-primary-soft text-primary font-semibold'
                  : 'text-text-secondary hover:bg-muted hover:text-text',
                collapsed && 'justify-center px-2',
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}

        <div className="pt-4 mt-4 border-t border-border">
          <p className={cn('px-3 text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2', collapsed && 'sr-only')}>
            System
          </p>
          <NavLink
            to="/app/settings"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-sm font-medium transition',
                isActive
                  ? 'bg-primary-soft text-primary font-semibold'
                  : 'text-text-secondary hover:bg-muted hover:text-text',
                collapsed && 'justify-center px-2',
              )
            }
            title={collapsed ? 'Settings' : undefined}
          >
            <Settings className="h-4.5 w-4.5 shrink-0" />
            {!collapsed && <span>Settings</span>}
          </NavLink>
        </div>
      </nav>

      <div className={cn('border-t border-border p-3', collapsed && 'px-2')}>
        {!collapsed ? (
          <div className="rounded-[12px] bg-page border border-border p-3">
            <p className="text-[11px] text-text-secondary">Workspace</p>
            <p className="text-xs font-semibold text-text mt-0.5 truncate">{displayOrg}</p>
            <div className="mt-3 flex items-center gap-2">
              <Avatar name={displayName} size="sm" />
              <div className="min-w-0">
                <p className="text-xs font-semibold truncate">{displayName.split(' ')[0]}</p>
                <p className="text-[11px] text-text-secondary truncate">{displayRole}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <Avatar name={displayName} size="sm" />
          </div>
        )}
        <button
          onClick={onToggle}
          className="mt-2 hidden lg:flex w-full items-center justify-center gap-2 rounded-[10px] py-2 text-xs font-medium text-text-secondary hover:bg-muted"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <><ChevronLeft className="h-4 w-4" /> Collapse</>}
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop */}
      <aside
        className={cn(
          'hidden lg:flex flex-col fixed inset-y-0 left-0 z-30 bg-white border-r border-border transition-all duration-300',
          collapsed ? 'w-[72px]' : 'w-[240px]',
        )}
      >
        {content}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <button className="absolute inset-0 bg-black/30" aria-label="Close menu" onClick={onMobileClose} />
          <aside className="absolute inset-y-0 left-0 w-[260px] bg-white border-r border-border shadow-xl animate-slide-in-right">
            {content}
          </aside>
        </div>
      )}
    </>
  )
}
