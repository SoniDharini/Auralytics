import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { cn } from '@/utils'

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="min-h-screen bg-page">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((v) => !v)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />
      <div className={cn('transition-all duration-300', collapsed ? 'lg:pl-[72px]' : 'lg:pl-[240px]')}>
        <Header onMenuClick={() => setMobileOpen(true)} />
        <main className="px-4 py-5 lg:px-6 lg:py-6 max-w-[1440px] pb-20 lg:pb-6">
          <Outlet />
        </main>
      </div>

      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-border px-2 py-1.5 flex justify-around safe-area-pb">
        {[
          { to: '/app', label: 'Home', end: true },
          { to: '/app/discovery', label: 'Discover' },
          { to: '/app/approvals', label: 'Approve' },
          { to: '/app/analytics', label: 'Analytics' },
          { to: '/app/notifications', label: 'Alerts' },
        ].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex-1 text-center text-[11px] font-semibold py-2 rounded-lg',
                isActive ? 'text-primary' : 'text-text-secondary',
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
