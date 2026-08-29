import { useEffect, useMemo, useState } from 'react'
import { cn } from '@/utils'

interface AvatarProps {
  name: string
  src?: string | null
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const sizes = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg',
}

const colors = [
  'bg-indigo-100 text-indigo-700',
  'bg-violet-100 text-violet-700',
  'bg-sky-100 text-sky-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
]

function safeHttpsMediaUrl(url?: string | null): string | undefined {
  if (!url) return undefined
  const text = url.trim()
  if (!text.toLowerCase().startsWith('https://')) return undefined
  if (/localhost|127\.0\.0\.1/i.test(text)) return undefined
  return text
}

export function Avatar({ name, src, size = 'md', className }: AvatarProps) {
  const [failed, setFailed] = useState(false)
  const safeSrc = useMemo(() => safeHttpsMediaUrl(src), [src])

  useEffect(() => {
    setFailed(false)
  }, [safeSrc])

  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
  const color = colors[name.length % colors.length]
  const showImage = Boolean(safeSrc) && !failed

  if (showImage) {
    return (
      <img
        src={safeSrc}
        alt={name}
        referrerPolicy="no-referrer"
        className={cn('rounded-full object-cover', sizes[size], className)}
        onError={(event) => {
          event.currentTarget.onerror = null
          setFailed(true)
        }}
      />
    )
  }

  return (
    <div
      className={cn(
        'rounded-full flex items-center justify-center font-bold shrink-0',
        sizes[size],
        color,
        className,
      )}
      aria-label={name}
    >
      {initials}
    </div>
  )
}
