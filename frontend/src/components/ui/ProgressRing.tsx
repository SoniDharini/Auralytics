import { cn } from '@/utils'

interface ProgressRingProps {
  value: number
  size?: number
  stroke?: number
  label?: string
  color?: string
  className?: string
}

export function ProgressRing({
  value,
  size = 56,
  stroke = 5,
  label,
  color = '#5B5FEF',
  className,
}: ProgressRingProps) {
  const radius = (size - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#EEF0FF"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xs font-bold text-text">{Math.round(value)}%</span>
        {label && <span className="text-[9px] text-text-secondary leading-none">{label}</span>}
      </div>
    </div>
  )
}
