import type { Platform } from '@/types'
import { cn } from '@/utils'

const styles: Record<Platform, string> = {
  instagram: 'bg-pink-50 text-pink-600 dark:bg-pink-500/15 dark:text-pink-300',
  youtube: 'bg-red-50 text-red-600 dark:bg-red-500/15 dark:text-red-300',
  tiktok: 'bg-slate-100 text-slate-800 dark:bg-slate-500/20 dark:text-slate-200',
  x: 'bg-slate-100 text-slate-800 dark:bg-slate-500/20 dark:text-slate-200',
  linkedin: 'bg-sky-50 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
}

const labels: Record<Platform, string> = {
  instagram: 'IG',
  youtube: 'YT',
  tiktok: 'TT',
  x: 'X',
  linkedin: 'in',
}

interface PlatformIconProps {
  platform: Platform
  className?: string
  showLabel?: boolean
}

export function PlatformIcon({ platform, className, showLabel }: PlatformIconProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-bold uppercase',
        styles[platform],
        className,
      )}
      title={platform}
    >
      {labels[platform]}
      {showLabel && <span className="font-semibold capitalize">{platform}</span>}
    </span>
  )
}
