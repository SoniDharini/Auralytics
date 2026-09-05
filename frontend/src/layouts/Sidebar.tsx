import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Megaphone,
  Search,
  Send,
  FileText,
  BarChart3,
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
  { to: '/app/approvals', label: 'Approval Center', icon: CheckSquare },
  { to: '/app/reports', label: 'Reports', icon: FileBarChart },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  mobileOpen: boolean
  onMobileClose: () => void
}

function NavItem({
  to,
  label,
  icon: Icon,
  end,
  collapsed,
}: {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  end?: boolean
  collapsed: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        cn(
          'relative flex items-center gap-3 px-2.5 py-2 rounded-[12px] text-sm font-medium transition-all duration-200 ease-out group',
          isActive
            ? 'nav-link-active text-primary font-semibold'
            : 'text-text-secondary hover:bg-muted/80 hover:text-text hover:translate-x-0.5',
          collapsed && 'justify-center px-2 hover:translate-x-0',
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span
              className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[3px] rounded-r-full bg-gradient-to-b from-primary via-accent to-primary animate-nav-indicator"
              aria-hidden
            />
          )}
          <span
            className={cn(
              'shrink-0 transition-all duration-200',
              isActive
                ? 'nav-icon-tile'
                : 'h-7 w-7 inline-flex items-center justify-center rounded-lg text-text-secondary group-hover:text-primary group-hover:bg-primary-soft/60',
              collapsed && !isActive && 'h-8 w-8',
            )}
          >
            <Icon className={cn('h-4 w-4', isActive && 'text-white')} />
          </span>
          {!collapsed && <span className="truncate">{label}</span>}
        </>
      )}
    </NavLink>
  )
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const navigate = useNavigate()
  const { user } = useAuth()

  const displayName = user?.full_name || 'Authenticated User'
  const displayRole = user?.role
    ? user.role.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())
    : 'Marketing Manager'
  const displayOrg = user?.company_name || 'Auralytics'

  const content = (
    <div className="flex h-full flex-col">
      <div
        className={cn(
          'flex items-center gap-2.5 px-4 h-16 border-b border-border',
          collapsed && 'justify-center px-2',
        )}
      >
        <button
          onClick={() => navigate('/app')}
          className="flex items-center gap-2.5 min-w-0 rounded-lg transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
          aria-label="Auralytics home"
        >
          <div className="h-8 w-8 rounded-lg ai-gradient-bg flex items-center justify-center text-white font-bold text-sm shrink-0 shadow-[0_4px_12px_rgba(91,95,239,0.28)]">
            A
          </div>
          {!collapsed && (
            <div className="min-w-0 text-left">
              <p className="text-sm font-bold text-text leading-tight">Auralytics</p>
              <p className="text-[10px] text-text-secondary truncate">From Discovery to ROI</p>
            </div>
          )}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2.5 py-4 space-y-0.5">
        <p
          className={cn(
            'px-3 text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2',
            collapsed && 'sr-only',
          )}
        >
          Main Menu
        </p>
        {mainNav.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} />
        ))}

        <div className="pt-4 mt-4 border-t border-border">
          <p
            className={cn(
              'px-3 text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-2',
              collapsed && 'sr-only',
            )}
          >
            System
          </p>
          <NavItem to="/app/settings" label="Settings" icon={Settings} collapsed={collapsed} />
        </div>
      </nav>

      <div className={cn('border-t border-border p-3', collapsed && 'px-2')}>
        {!collapsed ? (
          <div className="rounded-[12px] bg-elevated border border-border p-3">
            <p className="text-[11px] text-text-secondary">Workspace</p>
            <p className="text-xs font-semibold text-text mt-0.5 truncate">{displayOrg}</p>
            <div className="mt-3 flex items-center gap-2">
              <Avatar name={displayName} size="sm" />
              <div className="min-w-0">
                <p className="text-xs font-semibold truncate text-text">{displayName.split(' ')[0]}</p>
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
          className="mt-2 hidden lg:flex w-full items-center justify-center gap-2 rounded-[10px] py-2 text-xs font-medium text-text-secondary hover:bg-muted hover:text-text transition-colors duration-200"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" /> Collapse
            </>
          )}
        </button>
      </div>
    </div>
  )

  return (
    <>
      <aside
        className={cn(
          'hidden lg:flex flex-col fixed inset-y-0 left-0 z-30 bg-surface border-r border-border transition-all duration-300 ease-out',
          collapsed ? 'w-[72px]' : 'w-[240px]',
        )}
      >
        {content}
      </aside>

      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <button
            className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
            aria-label="Close menu"
            onClick={onMobileClose}
          />
          <aside className="absolute inset-y-0 left-0 w-[260px] bg-surface border-r border-border shadow-[8px_0_32px_rgba(15,23,42,0.35)] animate-slide-in-right">
            {content}
          </aside>
        </div>
      )}
    </>
  )
}
