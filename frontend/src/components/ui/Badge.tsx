import { cn } from '@/utils'

const variants: Record<string, string> = {
  default: 'bg-muted text-text-secondary ring-1 ring-border/80',
  primary: 'bg-primary-soft text-primary ring-1 ring-primary/15',
  success: 'bg-emerald-50 text-success ring-1 ring-emerald-100/80 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/25',
  warning: 'bg-amber-50 text-amber-700 ring-1 ring-amber-100 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/25',
  danger: 'bg-red-50 text-danger ring-1 ring-red-100 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/25',
  ai: 'bg-violet-50 text-ai ring-1 ring-violet-100 dark:bg-violet-500/15 dark:text-violet-300 dark:ring-violet-500/25',
  outline: 'border border-border text-text-secondary bg-surface/80',
}

interface BadgeProps {
  children: React.ReactNode
  variant?: keyof typeof variants
  className?: string
  pulse?: boolean
}

export function Badge({ children, variant = 'default', className, pulse }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide transition-colors duration-200',
        variants[variant],
        className,
      )}
    >
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-dot" />}
      {children}
    </span>
  )
}
