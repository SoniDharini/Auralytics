import { createContext, useCallback, useContext, useState } from 'react'
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react'
import { cn } from '@/utils'

type ToastType = 'success' | 'info' | 'warning' | 'error'

interface ToastItem {
  id: string
  title: string
  description?: string
  type: ToastType
}

interface ToastContextValue {
  toast: (t: Omit<ToastItem, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const toast = useCallback((t: Omit<ToastItem, 'id'>) => {
    const id = Math.random().toString(36).slice(2)
    setItems((prev) => [...prev, { ...t, id }])
    setTimeout(() => {
      setItems((prev) => prev.filter((i) => i.id !== id))
    }, 3500)
  }, [])

  const icons = {
    success: CheckCircle2,
    info: Info,
    warning: AlertTriangle,
    error: AlertTriangle,
  }

  const colors = {
    success:
      'border-emerald-200/80 bg-emerald-50/95 text-success dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300',
    info: 'border-indigo-200/80 bg-indigo-50/95 text-primary dark:border-primary/30 dark:bg-primary-soft dark:text-primary',
    warning:
      'border-amber-200/80 bg-amber-50/95 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300',
    error:
      'border-red-200/80 bg-red-50/95 text-danger dark:border-red-500/30 dark:bg-red-500/15 dark:text-red-300',
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[70] flex flex-col gap-2 w-full max-w-sm">
        {items.map((item) => {
          const Icon = icons[item.type]
          return (
            <div
              key={item.id}
              className={cn(
                'rounded-[12px] border px-4 py-3 shadow-[0_12px_32px_rgba(15,23,42,0.12)] animate-fade-in flex items-start gap-3 backdrop-blur-sm',
                colors[item.type],
              )}
              role="status"
            >
              <Icon className="h-4 w-4 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text">{item.title}</p>
                {item.description && (
                  <p className="text-xs text-text-secondary mt-0.5 leading-relaxed">{item.description}</p>
                )}
              </div>
              <button
                onClick={() => setItems((prev) => prev.filter((i) => i.id !== item.id))}
                className="text-text-secondary hover:text-text rounded-md p-0.5 transition-colors"
                aria-label="Dismiss"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}
