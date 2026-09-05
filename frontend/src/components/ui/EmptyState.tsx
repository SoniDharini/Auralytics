import { cn } from '@/utils'
import { Button } from './Button'
import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-16 px-6', className)}>
      {Icon && (
        <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-primary-soft to-violet-50 text-primary flex items-center justify-center mb-4 ring-1 ring-primary/10 shadow-sm">
          <Icon className="h-6 w-6" />
        </div>
      )}
      <h3 className="text-lg font-semibold tracking-tight text-text">{title}</h3>
      <p className="text-sm text-text-secondary mt-1.5 max-w-md leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <Button className="mt-5" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}
