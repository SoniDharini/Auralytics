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
      className={cn(
        'relative flex items-center gap-1 overflow-x-auto rounded-[14px] border border-border bg-muted/60 dark:bg-elevated p-1',
        className,
      )}
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
              'relative px-3.5 py-2 text-sm font-medium whitespace-nowrap rounded-[10px] transition-all duration-200',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
              isActive
                ? 'bg-surface text-primary shadow-xs border border-border/80'
                : 'text-text-secondary hover:text-text hover:bg-muted/60 border border-transparent',
            )}
          >
            <span className="inline-flex items-center gap-2">
              {tab.label}
              {typeof tab.count === 'number' && (
                <span
                  className={cn(
                    'text-[11px] px-1.5 py-0.5 rounded-full font-semibold transition-colors duration-200',
                    isActive ? 'bg-primary-soft text-primary' : 'bg-muted text-text-secondary',
                  )}
                >
                  {tab.count}
                </span>
              )}
            </span>
            {isActive && (
              <span className="absolute left-3 right-3 -bottom-px h-0.5 rounded-full bg-gradient-to-r from-primary to-accent md:hidden" />
            )}
          </button>
        )
      })}
    </div>
  )
}
