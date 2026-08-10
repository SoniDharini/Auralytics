import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/utils'
import type { ButtonHTMLAttributes } from 'react'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:pointer-events-none disabled:opacity-50 cursor-pointer',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-white hover:bg-primary-dark shadow-sm',
        secondary: 'bg-white text-text border border-border hover:bg-muted',
        ghost: 'text-text-secondary hover:bg-muted hover:text-text',
        danger: 'bg-danger text-white hover:bg-red-600',
        soft: 'bg-primary-soft text-primary hover:bg-[#e0e3ff]',
        ai: 'ai-gradient-bg text-white hover:opacity-95 shadow-sm',
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
