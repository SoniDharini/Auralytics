import { cn } from '@/utils'
import type { TextareaHTMLAttributes } from 'react'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
}

export function Textarea({ className, label, id, ...props }: TextareaProps) {
  const areaId = id || label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={areaId} className="block text-sm font-medium text-text">
          {label}
        </label>
      )}
      <textarea
        id={areaId}
        className={cn(
          'w-full min-h-[100px] px-3 py-2.5 rounded-[10px] border border-border bg-elevated text-sm text-text placeholder:text-text-secondary/70',
          'shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:shadow-[0_1px_2px_rgba(0,0,0,0.25)] transition-all duration-200 resize-y',
          'hover:border-primary/30',
          'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
          className,
        )}
        {...props}
      />
    </div>
  )
}
