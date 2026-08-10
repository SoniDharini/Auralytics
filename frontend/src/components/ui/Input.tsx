import { cn } from '@/utils'
import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export function Input({ className, label, error, hint, id, ...props }: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-text">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={cn(
          'w-full h-10 px-3 rounded-[10px] border border-border bg-white text-sm text-text placeholder:text-text-secondary/70',
          'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition',
          error && 'border-danger focus:ring-danger/30 focus:border-danger',
          className,
        )}
        {...props}
      />
      {hint && !error && <p className="text-xs text-text-secondary">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
}
