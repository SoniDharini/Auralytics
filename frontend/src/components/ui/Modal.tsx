import { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/utils'
import { Button } from './Button'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  footer?: React.ReactNode
  className?: string
}

export function Modal({ open, onClose, title, children, footer, className }: ModalProps) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        className="absolute inset-0 bg-slate-900/35 backdrop-blur-[2px] transition-opacity"
        aria-label="Close modal"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          'relative w-full max-w-lg bg-surface rounded-[16px] border border-border',
          'shadow-[0_24px_64px_rgba(15,23,42,0.18)] animate-scale-in',
          className,
        )}
      >
        <header className="flex items-center justify-between px-5 py-4 border-b border-border/80">
          <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </header>
        <div className="px-5 py-4">{children}</div>
        {footer && <footer className="px-5 py-4 border-t border-border/80 bg-page/40 rounded-b-[16px]">{footer}</footer>}
      </div>
    </div>
  )
}
