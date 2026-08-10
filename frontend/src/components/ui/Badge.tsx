import { cn } from '@/utils'

const variants: Record<string, string> = {
  default: 'bg-muted text-text-secondary',
  primary: 'bg-primary-soft text-primary',
  success: 'bg-green-50 text-success',
  warning: 'bg-amber-50 text-amber-700',
  danger: 'bg-red-50 text-danger',
  ai: 'bg-violet-50 text-ai',
  outline: 'border border-border text-text-secondary bg-white',
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
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold',
        variants[variant],
        className,
      )}
    >
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse-dot" />}
      {children}
    </span>
  )
}
