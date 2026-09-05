import { Link } from 'react-router-dom'
import { BarChart3, FileText, Moon, Search, Send, Sparkles, Sun } from 'lucide-react'
import { useTheme } from '@/context/ThemeContext'
import { cn } from '@/utils'

/** Compact theme toggle for public pages. */
export function ThemeToggleButton({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn(
        'inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface text-text-secondary',
        'hover:text-text hover:border-primary/30 transition-colors duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
        className,
      )}
    >
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  )
}

/** Soft flowing ribbon — no nodes, no metrics. */
export function FlowingRibbon({
  className,
  tone = 'violet',
}: {
  className?: string
  tone?: 'violet' | 'indigo' | 'magenta'
}) {
  const fill =
    tone === 'indigo'
      ? 'url(#ribbon-indigo)'
      : tone === 'magenta'
        ? 'url(#ribbon-magenta)'
        : 'url(#ribbon-violet)'

  return (
    <svg viewBox="0 0 480 420" className={cn('w-full h-auto', className)} aria-hidden="true">
      <defs>
        <linearGradient id="ribbon-violet" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.55" />
          <stop offset="55%" stopColor="#6366f1" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#a78bfa" stopOpacity="0.2" />
        </linearGradient>
        <linearGradient id="ribbon-indigo" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#818cf8" stopOpacity="0.25" />
        </linearGradient>
        <linearGradient id="ribbon-magenta" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a855f7" stopOpacity="0.45" />
          <stop offset="100%" stopColor="#6366f1" stopOpacity="0.22" />
        </linearGradient>
        <filter id="ribbon-blur" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="8" />
        </filter>
      </defs>
      <ellipse
        cx="320"
        cy="80"
        rx="120"
        ry="70"
        fill={fill}
        opacity="0.35"
        filter="url(#ribbon-blur)"
        className="animate-orb"
      />
      <path
        d="M40 320 C 120 180, 200 380, 280 220 S 400 80, 460 200"
        fill="none"
        stroke={fill}
        strokeWidth="48"
        strokeLinecap="round"
        opacity="0.45"
        className="animate-hero-wave"
      />
      <path
        d="M20 260 C 140 140, 220 300, 320 180 S 420 120, 470 240"
        fill="none"
        stroke="white"
        strokeWidth="1.25"
        opacity="0.25"
      />
      <circle cx="90" cy="300" r="3" fill="white" opacity="0.35" className="animate-float-dot" />
      <circle cx="380" cy="140" r="2.5" fill="white" opacity="0.3" className="animate-float-dot-delayed" />
      <circle cx="250" cy="90" r="2" fill="white" opacity="0.25" />
    </svg>
  )
}

const capabilityCards = [
  { icon: Search, title: 'Discover', desc: 'Find the right creator' },
  { icon: Send, title: 'Outreach', desc: 'Manage communication' },
  { icon: FileText, title: 'Contracts', desc: 'Create and review' },
  { icon: BarChart3, title: 'Analytics', desc: 'Measure performance' },
]

type CapabilityTone = 'light' | 'glass'

/** Minimal UI fragments — labels only, no fake metrics. */
export function CapabilityStack({
  className,
  tone = 'glass',
}: {
  className?: string
  tone?: CapabilityTone
}) {
  const isGlass = tone === 'glass'
  return (
    <div className={cn('relative space-y-3', className)}>
      {capabilityCards.map(({ icon: Icon, title, desc }, i) => (
        <div
          key={title}
          className={cn(
            'rounded-2xl px-4 py-3 backdrop-blur-md shadow-[0_8px_24px_rgba(15,23,42,0.08)]',
            isGlass
              ? 'border border-white/15 bg-white/10'
              : 'border border-border/70 bg-surface/95 dark:bg-elevated/95',
            i % 2 === 1 && 'ml-6 sm:ml-10',
          )}
        >
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'h-9 w-9 rounded-xl flex items-center justify-center',
                isGlass ? 'bg-white/15 text-white' : 'bg-primary-soft text-primary',
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
            <div>
              <p className={cn('text-sm font-semibold', isGlass ? 'text-white' : 'text-text')}>{title}</p>
              <p className={cn('text-[11px]', isGlass ? 'text-white/65' : 'text-text-secondary')}>{desc}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

/** Landing hero abstract composition. */
export function LandingHeroVisual({ className }: { className?: string }) {
  return (
    <div className={cn('relative', className)}>
      <div className="absolute -inset-6 rounded-[32px] bg-gradient-to-br from-primary/20 via-accent/10 to-transparent blur-2xl animate-glow-breathe" />
      <div className="relative rounded-[28px] border border-border/60 bg-surface/70 dark:bg-elevated/55 backdrop-blur-sm p-6 sm:p-8 overflow-hidden shadow-[0_24px_60px_rgba(91,95,239,0.12)]">
        <div className="absolute inset-0 pointer-events-none">
          <FlowingRibbon className="absolute -right-10 -top-12 w-[115%] opacity-40 dark:opacity-55" />
        </div>
        <div
          className="absolute inset-0 opacity-[0.04] dark:opacity-[0.07] pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, var(--auralytics-primary) 1px, transparent 0)',
            backgroundSize: '18px 18px',
          }}
        />
        <div className="relative grid gap-5 sm:grid-cols-[1.15fr_0.85fr] items-center">
          <CapabilityStack tone="light" />
          <div className="hidden sm:flex flex-col items-center justify-center gap-3 py-2">
            <div className="h-16 w-16 rounded-2xl ai-gradient-bg text-white font-bold text-2xl flex items-center justify-center shadow-[0_12px_32px_rgba(91,95,239,0.35)]">
              A
            </div>
            <p className="text-xs font-semibold text-text-secondary text-center max-w-[140px]">
              From Discovery to ROI
            </p>
            <Sparkles className="h-4 w-4 text-primary animate-float-dot" />
          </div>
        </div>
      </div>
    </div>
  )
}

/** Auth branded panel — unique compositions for sign-in vs sign-up. */
export function AuthBrandPanel({
  variant,
  title,
  subtitle,
  words,
  className,
}: {
  variant: 'signin' | 'signup'
  title: string
  subtitle: string
  words: string[]
  className?: string
}) {
  return (
    <aside
      className={cn(
        'relative hidden lg:flex flex-col justify-between overflow-hidden p-10 xl:p-14 text-white',
        'bg-[#0c0f1c]',
        className,
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_15%,rgba(91,95,239,0.45),transparent_50%),radial-gradient(ellipse_at_85%_80%,rgba(139,92,246,0.32),transparent_45%)]" />
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />

      {variant === 'signin' ? (
        <>
          <FlowingRibbon tone="violet" className="absolute -right-16 top-8 w-[130%] opacity-90 animate-orb" />
          <div className="absolute left-10 bottom-28 w-40 h-40 rounded-full border border-white/10 animate-glow-breathe" />
          <div className="absolute right-16 bottom-16 h-20 w-32 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm" />
        </>
      ) : (
        <>
          <FlowingRibbon
            tone="magenta"
            className="absolute -left-20 bottom-0 w-[140%] rotate-180 opacity-85 animate-orb-slow"
          />
          <div className="absolute right-12 top-24 h-48 w-24 rounded-[40px] border border-white/10 bg-white/5 backdrop-blur-sm animate-float-dot" />
          <div className="absolute right-28 top-40 h-32 w-16 rounded-[32px] border border-white/10 bg-white/[0.04]" />
        </>
      )}

      <div className="relative">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl ai-gradient-bg flex items-center justify-center font-bold shadow-[0_8px_24px_rgba(91,95,239,0.35)]">
            A
          </div>
          <div>
            <p className="font-bold">Auralytics</p>
            <p className="text-xs text-white/55">From Discovery to ROI</p>
          </div>
        </Link>
      </div>

      <div className="relative max-w-lg">
        <h1 className="text-3xl xl:text-[2.6rem] font-extrabold leading-[1.12] tracking-tight">{title}</h1>
        <p className="mt-4 text-white/70 text-base leading-relaxed">{subtitle}</p>
        <div className="mt-8 flex flex-wrap gap-2">
          {words.map((word, i) => (
            <span
              key={word}
              className="inline-flex items-center gap-2 text-[11px] font-semibold tracking-wide text-white/60"
            >
              {i > 0 && <span className="h-px w-4 bg-white/25" />}
              <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1">{word}</span>
            </span>
          ))}
        </div>
        {variant === 'signup' && (
          <div className="mt-8 max-w-xs opacity-95 hidden xl:block">
            <CapabilityStack tone="glass" />
          </div>
        )}
      </div>

      <p className="relative text-xs text-white/40">Autonomous Influencer Marketing. From Discovery to ROI.</p>
    </aside>
  )
}

/** Compact abstract decor for Overview welcome card. */
export function OverviewHeroDecor({ className }: { className?: string }) {
  return (
    <div className={cn('relative w-full max-w-[280px]', className)} aria-hidden>
      <div className="absolute inset-0 rounded-full bg-primary/20 blur-3xl animate-glow-breathe" />
      <svg viewBox="0 0 280 200" className="relative w-full h-auto">
        <defs>
          <linearGradient id="oh-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--auralytics-primary)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--auralytics-accent)" stopOpacity="0.25" />
          </linearGradient>
        </defs>
        <path
          d="M20 140 C 70 60, 120 180, 170 90 S 240 40, 270 110"
          fill="none"
          stroke="url(#oh-g)"
          strokeWidth="28"
          strokeLinecap="round"
          opacity="0.5"
          className="animate-hero-wave"
        />
        <path
          d="M30 150 C 90 80, 130 160, 190 100 S 250 70, 265 120"
          fill="none"
          stroke="var(--auralytics-primary)"
          strokeWidth="1.5"
          opacity="0.35"
        />
        <rect x="168" y="36" width="88" height="28" rx="10" fill="var(--auralytics-primary)" opacity="0.18" />
        <rect x="178" y="72" width="78" height="22" rx="8" fill="var(--auralytics-accent)" opacity="0.14" />
        <rect x="188" y="104" width="68" height="18" rx="7" fill="var(--auralytics-primary)" opacity="0.12" />
        <circle cx="60" cy="50" r="3" fill="var(--auralytics-primary)" opacity="0.45" className="animate-float-dot" />
        <circle
          cx="240"
          cy="160"
          r="2.5"
          fill="var(--auralytics-accent)"
          opacity="0.4"
          className="animate-float-dot-delayed"
        />
      </svg>
    </div>
  )
}
