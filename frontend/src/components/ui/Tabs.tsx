import { cn } from '@/utils'

interface TabsProps {
  tabs: { id: string; label: string; count?: number }[]
  active: string
  onChange: (id: string) => void
  className?: string
}

export function Tabs({ tabs, active, onChange, className }: TabsProps) {
  return (
    <div
      className={cn('flex items-center gap-1 overflow-x-auto border-b border-border', className)}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors',
              isActive ? 'text-primary' : 'text-text-secondary hover:text-text',
            )}
          >
            <span className="inline-flex items-center gap-2">
              {tab.label}
              {typeof tab.count === 'number' && (
                <span
                  className={cn(
                    'text-[11px] px-1.5 py-0.5 rounded-full font-semibold',
                    isActive ? 'bg-primary-soft text-primary' : 'bg-muted text-text-secondary',
                  )}
                >
                  {tab.count}
                </span>
              )}
            </span>
            {isActive && (
              <span className="absolute left-2 right-2 -bottom-px h-0.5 rounded-full bg-primary" />
            )}
          </button>
        )
      })}
    </div>
  )
}
