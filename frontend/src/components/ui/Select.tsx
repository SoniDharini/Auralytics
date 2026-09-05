import { cn } from '@/utils'
import type { SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  options: { value: string; label: string }[]
}

export function Select({ className, label, options, id, ...props }: SelectProps) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-text">
          {label}
        </label>
      )}
      <select
        id={selectId}
        className={cn(
          'w-full h-10 px-3 rounded-[10px] border border-border bg-elevated text-sm text-text',
          'shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:shadow-[0_1px_2px_rgba(0,0,0,0.25)] transition-all duration-200',
          'hover:border-primary/30',
          'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}
