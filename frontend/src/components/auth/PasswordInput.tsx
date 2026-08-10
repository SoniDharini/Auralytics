import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { cn } from '@/utils'
import type { InputHTMLAttributes } from 'react'

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  error?: string
  hint?: string
}

export function PasswordInput({
  className,
  label,
  error,
  hint,
  id,
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false)
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-') || 'password'

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-text">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type={visible ? 'text' : 'password'}
          className={cn(
            'w-full h-10 px-3 pr-10 rounded-[10px] border border-border bg-white text-sm text-text placeholder:text-text-secondary/70',
            'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition',
            error && 'border-danger focus:ring-danger/30 focus:border-danger',
            className,
          )}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded-md text-text-secondary hover:text-text hover:bg-muted transition"
          aria-label={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      {hint && !error && <p className="text-xs text-text-secondary">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
}
