import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/utils'
import { Button } from './Button'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  width?: string
  footer?: React.ReactNode
}

export function Drawer({ open, onClose, title, subtitle, children, width = 'max-w-lg', footer }: DrawerProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        className="absolute inset-0 bg-slate-900/35 backdrop-blur-[2px]"
        aria-label="Close drawer"
        onClick={onClose}
      />
      <aside
        className={cn(
          'relative h-full w-full bg-surface border-l border-border',
          'shadow-[-12px_0_40px_rgba(15,23,42,0.12)] flex flex-col animate-slide-in-right',
          width,
        )}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-border/80 bg-gradient-to-r from-surface to-primary-soft/30">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-text">{title}</h2>
            {subtitle && <p className="text-sm text-text-secondary mt-0.5">{subtitle}</p>}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && <footer className="border-t border-border/80 px-5 py-4 bg-page/50">{footer}</footer>}
      </aside>
    </div>
  )
}
