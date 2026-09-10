import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/utils'
import { AGE_DROPDOWN_OPTIONS, parseIntegerAge } from '@/utils/campaignForm'

interface AgeComboboxProps {
  label: string
  value: number
  onChange: (value: number) => void
  error?: string
  className?: string
}

export function AgeCombobox({ label, value, onChange, error, className }: AgeComboboxProps) {
  const generatedId = useId()
  const inputId = generatedId
  const listId = `${generatedId}-list`
  const rootRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(String(value))

  useEffect(() => {
    if (!open) setText(String(value))
  }, [value, open])

  useEffect(() => {
    const onDoc = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const options = useMemo(() => {
    const query = text.trim()
    if (!query) return AGE_DROPDOWN_OPTIONS
    return AGE_DROPDOWN_OPTIONS.filter((n) => String(n).startsWith(query))
  }, [text])

  useEffect(() => {
    if (!open || !listRef.current) return
    const selected = listRef.current.querySelector('[data-selected="true"]')
    if (selected instanceof HTMLElement) selected.scrollIntoView({ block: 'nearest' })
  }, [open, value])

  const commit = (raw: string) => {
    const parsed = parseIntegerAge(raw)
    if (parsed != null) {
      onChange(parsed)
      setText(String(parsed))
      return true
    }
    setText(String(value))
    return false
  }

  return (
    <div className={cn('space-y-1.5', className)} ref={rootRef}>
      <label htmlFor={inputId} className="block text-sm font-medium text-text">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          inputMode="numeric"
          autoComplete="off"
          value={text}
          onChange={(e) => {
            const next = e.target.value.replace(/[^\d]/g, '')
            setText(next)
            setOpen(true)
            const parsed = parseIntegerAge(next)
            if (parsed != null) onChange(parsed)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => commit(text)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false)
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setOpen(true)
            }
            if (e.key === 'Enter') {
              e.preventDefault()
              commit(text)
              setOpen(false)
            }
          }}
          className={cn(
            'w-full h-10 pl-3 pr-10 rounded-[10px] border border-border bg-elevated text-sm text-text',
            'shadow-[0_1px_2px_rgba(15,23,42,0.03)] dark:shadow-[0_1px_2px_rgba(0,0,0,0.25)] transition-all duration-200',
            'hover:border-primary/30',
            'focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary',
            error && 'border-danger focus:ring-danger/30 focus:border-danger',
          )}
        />
        <button
          type="button"
          tabIndex={-1}
          aria-label={`Toggle ${label} options`}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setOpen((v) => !v)}
          className="absolute right-1.5 top-1/2 -translate-y-1/2 h-7 w-7 rounded-lg text-text-secondary hover:bg-muted/80 hover:text-text"
        >
          <ChevronDown className={cn('h-4 w-4 mx-auto transition', open && 'rotate-180')} />
        </button>
        {open && (
          <ul
            id={listId}
            role="listbox"
            ref={listRef}
            className="absolute z-30 mt-1 max-h-48 w-full overflow-y-auto rounded-[10px] border border-border bg-elevated py-1 shadow-[0_8px_24px_rgba(15,23,42,0.12)] dark:shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
          >
            {options.length === 0 && (
              <li className="px-3 py-2 text-xs text-text-secondary">No matching age. Keep typing a number.</li>
            )}
            {options.map((n) => (
              <li key={n} role="option" aria-selected={n === value} data-selected={n === value ? 'true' : 'false'}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange(n)
                    setText(String(n))
                    setOpen(false)
                  }}
                  className={cn(
                    'w-full px-3 py-1.5 text-left text-sm transition',
                    n === value
                      ? 'bg-primary-soft text-primary font-semibold'
                      : 'text-text hover:bg-muted/80',
                  )}
                >
                  {n}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  )
}
