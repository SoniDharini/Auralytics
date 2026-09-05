import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Info, RefreshCw } from 'lucide-react'
import { Badge, Button, Card, Skeleton } from '@/components/ui'
import { cn } from '@/utils'

export function SourceLabel({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-text-secondary">
      {children}
    </span>
  )
}

export function InfoTip({ label, text }: { label: string; text: string }) {
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        className="peer inline-flex h-4 w-4 items-center justify-center rounded-full text-text-secondary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        aria-label={label}
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-30 mt-2 w-56 -translate-x-1/2 rounded-[10px] border border-border bg-surface px-3 py-2 text-left text-xs leading-relaxed text-text shadow-lg opacity-0 transition-opacity peer-hover:opacity-100 peer-focus:opacity-100"
      >
        {text}
      </span>
    </span>
  )
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-secondary">{eyebrow}</p>
        )}
        <h2 className="text-lg font-semibold tracking-tight text-text">{title}</h2>
        {description && <p className="mt-1 max-w-2xl text-sm text-text-secondary">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function AnalyticsKpiCard({
  label,
  value,
  context,
  tip,
  source,
}: {
  label: string
  value: string
  context?: string
  tip?: string
  source?: string
}) {
  return (
    <div className="group relative overflow-hidden rounded-[16px] ui-card-surface ui-card-hover p-5">
      <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-primary/80 to-accent/70" />
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-text-secondary">{label}</p>
        {tip && <InfoTip label={`About ${label}`} text={tip} />}
      </div>
      <p className="mt-2 text-[28px] font-bold leading-none tracking-tight text-text">{value}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {context && <p className="text-xs text-text-secondary">{context}</p>}
        {source && <SourceLabel>{source}</SourceLabel>}
      </div>
    </div>
  )
}

export function AnalyticsKpiSkeleton() {
  return (
    <div className="rounded-[16px] border border-border bg-surface p-5 space-y-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-28" />
      <Skeleton className="h-3 w-32" />
    </div>
  )
}

export function SectionCard({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <Card className={cn('overflow-hidden ui-card-hover', className)}>
      {children}
    </Card>
  )
}

export function SectionError({
  title,
  description,
  onRetry,
}: {
  title: string
  description?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-[14px] border border-danger/25 bg-danger/10 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-danger" />
        <div>
          <p className="text-sm font-semibold text-text">{title}</p>
          {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
        </div>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </Button>
      )}
    </div>
  )
}

export function SectionEmpty({
  title,
  description,
  actionLabel,
  to,
}: {
  title: string
  description: string
  actionLabel?: string
  to?: string
}) {
  return (
    <div className="px-1 py-8 text-center">
      <h3 className="text-base font-semibold text-text">{title}</h3>
      <p className="mx-auto mt-1.5 max-w-lg text-sm text-text-secondary">{description}</p>
      {actionLabel && to && (
        <Link to={to} className="mt-4 inline-block">
          <Button variant="secondary" size="sm">
            {actionLabel}
          </Button>
        </Link>
      )}
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="space-y-3 py-2">
      <Skeleton className="h-[220px] w-full rounded-[12px]" />
    </div>
  )
}

export function RowSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-3 w-16" />
        </div>
      ))}
    </div>
  )
}

export function TransparencyBanner() {
  return (
    <div className="rounded-[14px] border border-primary/20 bg-primary-soft/50 dark:bg-primary-soft dark:border-primary/30 px-4 py-3.5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-text">Campaign totals from stored records</p>
          <p className="mt-0.5 text-sm text-text-secondary">
            Spend, revenue, reach, and conversions come from campaign records. Sponsored video tracking is not
            connected yet. Creator profile information may come from real platform data.
          </p>
        </div>
        <Badge variant="ai">Backend Calculated</Badge>
      </div>
    </div>
  )
}

export function HumanInTheLoopNote() {
  return (
    <p className="text-xs font-medium text-text-secondary">
      AI recommends. You decide. No budget change is applied automatically.
    </p>
  )
}
