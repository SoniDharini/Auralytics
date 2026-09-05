import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'
import type { ButtonHTMLAttributes } from 'react'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-semibold transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-1 focus-visible:ring-offset-page disabled:pointer-events-none disabled:opacity-50 cursor-pointer active:scale-[0.98]',
  {
    variants: {
      variant: {
        primary:
          'bg-gradient-to-b from-primary to-primary-dark text-white shadow-[0_1px_2px_rgba(66,70,217,0.35),0_4px_12px_rgba(91,95,239,0.22)] hover:brightness-[1.04] hover:shadow-[0_2px_8px_rgba(91,95,239,0.3)]',
        secondary:
          'bg-surface text-text border border-border shadow-[0_1px_2px_rgba(15,23,42,0.04)] hover:bg-muted/80 hover:border-primary/20',
        ghost: 'text-text-secondary hover:bg-muted/80 hover:text-text',
        danger:
          'bg-danger text-white shadow-[0_1px_2px_rgba(239,68,68,0.3)] hover:brightness-110 hover:shadow-[0_4px_12px_rgba(239,68,68,0.25)]',
        soft: 'bg-primary-soft text-primary hover:brightness-95 border border-primary/10',
        ai: 'ai-gradient-bg text-white shadow-[0_4px_14px_rgba(124,58,237,0.28)] hover:brightness-105',
      },
      size: {
        sm: 'h-8 px-3 text-xs rounded-[8px]',
        md: 'h-10 px-4 text-sm rounded-[10px]',
        lg: 'h-11 px-5 text-sm rounded-[10px]',
        icon: 'h-9 w-9 rounded-[10px]',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
