import { Link } from 'react-router-dom'
import { cn } from '@/utils'

export type AmbientVariant =
  | 'default'
  | 'landing'
  | 'overview'
  | 'campaign'
  | 'campaigns'
  | 'discovery'
  | 'outreach'
  | 'contract'
  | 'analytics'
  | 'auth'

/** Theme-aware low-opacity ambient layer. Decorative only — no business data. */
export function PageAmbientBackground({
  variant = 'default',
  className,
}: {
  variant?: AmbientVariant
  className?: string
}) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'pointer-events-none absolute inset-0 overflow-hidden -mx-4 lg:-mx-6 -mt-5 lg:-mt-6',
        className,
      )}
    >
      {/* Shared glow orbs — current primary/accent tokens */}
      <div className="absolute -top-28 -right-20 h-80 w-80 rounded-full bg-primary/[0.12] dark:bg-primary/[0.18] blur-3xl animate-orb" />
      <div className="absolute top-[40%] -left-24 h-64 w-64 rounded-full bg-accent/[0.08] dark:bg-accent/[0.14] blur-3xl animate-orb-slow" />
      <div className="absolute bottom-8 right-1/3 h-44 w-44 rounded-full bg-ai/[0.07] dark:bg-ai/[0.12] blur-3xl" />

      {/* Dot matrix */}
      <div
        className="absolute inset-0 opacity-[0.03] dark:opacity-[0.055]"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, var(--auralytics-text-secondary) 1px, transparent 0)',
          backgroundSize: '22px 22px',
        }}
      />

      {/* Soft curved accent line */}
      <svg
        className="absolute inset-x-0 top-0 h-[280px] w-full opacity-[0.06] dark:opacity-[0.1]"
        viewBox="0 0 1200 280"
        preserveAspectRatio="none"
      >
        <path
          d="M0 180 C 280 40, 520 220, 760 100 S 1100 40, 1200 160"
          fill="none"
          stroke="var(--auralytics-primary)"
          strokeWidth="1.5"
          className="animate-ambient-line"
        />
      </svg>

      {variant === 'landing' && (
        <svg
          viewBox="0 0 1200 520"
          className="absolute -right-24 top-16 w-[min(720px,70%)] opacity-[0.18] dark:opacity-[0.28] animate-hero-wave"
          aria-hidden
        >
          <defs>
            <linearGradient id="landing-ribbon" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="var(--auralytics-primary)" stopOpacity="0.55" />
              <stop offset="100%" stopColor="var(--auralytics-accent)" stopOpacity="0.22" />
            </linearGradient>
          </defs>
          <path
            d="M80 360 C 260 80, 420 440, 640 180 S 980 60, 1180 280"
            fill="none"
            stroke="url(#landing-ribbon)"
            strokeWidth="72"
            strokeLinecap="round"
          />
        </svg>
      )}
      {variant === 'overview' && <OverviewAmbientVisual className="absolute right-0 top-8 w-[min(420px,55%)] opacity-[0.14] dark:opacity-[0.22]" />}
      {variant === 'campaign' && <CampaignAmbientPattern className="absolute right-4 top-10 w-64 opacity-[0.1] dark:opacity-[0.16]" />}
      {variant === 'campaigns' && <NodeMeshPattern className="absolute left-1/2 top-16 -translate-x-1/2 w-[480px] opacity-[0.08] dark:opacity-[0.14]" />}
      {variant === 'discovery' && <NodeMeshPattern className="absolute right-0 top-12 w-[360px] opacity-[0.1] dark:opacity-[0.16]" />}
      {variant === 'outreach' && <WaveAmbientPattern className="absolute inset-x-0 top-20 h-40 opacity-[0.08] dark:opacity-[0.14]" />}
      {variant === 'contract' && <DocumentAmbientPattern className="absolute right-8 top-14 w-48 opacity-[0.08] dark:opacity-[0.14]" />}
      {variant === 'analytics' && <WaveAmbientPattern className="absolute inset-x-8 top-24 h-36 opacity-[0.07] dark:opacity-[0.12]" dense />}
      {variant === 'auth' && (
        <div className="absolute bottom-1/4 left-1/4 h-32 w-32 rounded-full border border-primary/20 animate-glow-breathe" />
      )}
    </div>
  )
}

/** @deprecated Prefer PageAmbientBackground — kept for existing imports. */
export function DecorativeBackground({ className }: { className?: string }) {
  return <PageAmbientBackground variant="default" className={className} />
}

/** Overview ambient: flowing ribbon + translucent bars. No nodes or metrics. */
export function OverviewAmbientVisual({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 400 260" className={cn('w-full h-auto', className)} aria-hidden="true">
      <defs>
        <linearGradient id="ov-ribbon" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--auralytics-primary)" stopOpacity="0.55" />
          <stop offset="100%" stopColor="var(--auralytics-accent)" stopOpacity="0.3" />
        </linearGradient>
      </defs>
      <path
        d="M20 180 C 100 60, 180 220, 260 100 S 360 40, 400 140"
        fill="none"
        stroke="url(#ov-ribbon)"
        strokeWidth="36"
        strokeLinecap="round"
        opacity="0.45"
        className="animate-hero-wave"
      />
      <path
        d="M40 190 C 120 90, 200 200, 280 110 S 360 70, 390 150"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="1.25"
        opacity="0.35"
      />
      <rect x="260" y="48" width="100" height="30" rx="10" fill="var(--auralytics-primary)" opacity="0.16" />
      <rect x="275" y="90" width="85" height="24" rx="8" fill="var(--auralytics-accent)" opacity="0.12" />
      <rect x="290" y="126" width="70" height="20" rx="7" fill="var(--auralytics-primary)" opacity="0.1" />
      <circle cx="70" cy="70" r="3" fill="var(--auralytics-primary)" opacity="0.4" className="animate-float-dot" />
      <circle cx="340" cy="200" r="2.5" fill="var(--auralytics-accent)" opacity="0.35" className="animate-float-dot-delayed" />
    </svg>
  )
}

function CampaignAmbientPattern({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 120" className={cn(className)} aria-hidden="true">
      <circle cx="30" cy="60" r="4" fill="var(--auralytics-primary)" opacity="0.5" />
      <circle cx="70" cy="40" r="3.5" fill="var(--auralytics-accent)" opacity="0.45" />
      <circle cx="110" cy="70" r="5" fill="var(--auralytics-primary)" opacity="0.55" />
      <circle cx="150" cy="45" r="3.5" fill="var(--auralytics-accent)" opacity="0.4" />
      <circle cx="180" cy="75" r="4" fill="var(--auralytics-primary)" opacity="0.45" />
      <path
        d="M30 60 L70 40 L110 70 L150 45 L180 75"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="1"
        opacity="0.4"
        className="animate-ambient-line"
      />
    </svg>
  )
}

function NodeMeshPattern({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 400 200" className={cn(className)} aria-hidden="true">
      {[
        [40, 50],
        [120, 30],
        [200, 80],
        [280, 40],
        [360, 90],
        [80, 140],
        [180, 150],
        [300, 130],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i % 2 ? 3.5 : 4.5} fill="var(--auralytics-primary)" opacity={0.35 + (i % 3) * 0.08} />
      ))}
      <path
        d="M40 50 L120 30 L200 80 L280 40 L360 90 M120 30 L80 140 L200 80 L180 150 L300 130 L280 40"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="0.9"
        opacity="0.35"
      />
    </svg>
  )
}

function WaveAmbientPattern({ className, dense }: { className?: string; dense?: boolean }) {
  return (
    <svg viewBox="0 0 800 120" className={cn('w-full', className)} preserveAspectRatio="none" aria-hidden="true">
      <path
        d="M0 70 C 100 20, 200 100, 300 55 S 500 20, 600 65 S 750 100, 800 50"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="1.25"
        opacity="0.5"
        className="animate-ambient-line"
      />
      <path
        d="M0 90 C 120 50, 220 110, 340 70 S 520 40, 640 85 S 760 100, 800 70"
        fill="none"
        stroke="var(--auralytics-accent)"
        strokeWidth="1"
        opacity="0.35"
      />
      {dense && (
        <path
          d="M0 40 C 150 80, 250 10, 400 50 S 600 90, 800 30"
          fill="none"
          stroke="var(--auralytics-primary)"
          strokeWidth="0.75"
          opacity="0.25"
        />
      )}
    </svg>
  )
}

function DocumentAmbientPattern({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 140 180" className={cn(className)} aria-hidden="true">
      <rect
        x="20"
        y="20"
        width="100"
        height="140"
        rx="6"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="1.25"
        opacity="0.45"
      />
      <line x1="36" y1="48" x2="104" y2="48" stroke="var(--auralytics-primary)" strokeWidth="1" opacity="0.3" />
      <line x1="36" y1="68" x2="104" y2="68" stroke="var(--auralytics-primary)" strokeWidth="1" opacity="0.25" />
      <line x1="36" y1="88" x2="90" y2="88" stroke="var(--auralytics-primary)" strokeWidth="1" opacity="0.22" />
      <line x1="36" y1="108" x2="100" y2="108" stroke="var(--auralytics-accent)" strokeWidth="1" opacity="0.22" />
    </svg>
  )
}

/** Compact page title block used across app screens. */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn('relative flex flex-col sm:flex-row sm:items-end justify-between gap-4', className)}>
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">{eyebrow}</p>
        )}
        <h1 className="mt-1 text-[26px] sm:text-[30px] font-bold tracking-tight text-text">{title}</h1>
        {description && (
          <p className="text-sm text-text-secondary mt-1.5 max-w-2xl leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

/** Abstract campaign ↔ creator network. No fake names or metrics. */
export function NetworkIllustration({
  className,
  variant = 'default',
}: {
  className?: string
  variant?: 'default' | 'auth' | 'growth'
}) {
  const id = `net-${variant}`
  return (
    <svg viewBox="0 0 320 220" className={cn('w-full h-auto', className)} aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--auralytics-primary)" stopOpacity="0.7" />
          <stop offset="100%" stopColor="var(--auralytics-accent)" stopOpacity="0.35" />
        </linearGradient>
        <filter id={`${id}-glow`} x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle cx="160" cy="110" r="70" fill={`url(#${id}-g)`} opacity="0.12" />
      <circle cx="160" cy="110" r="42" fill={`url(#${id}-g)`} opacity="0.18" filter={`url(#${id}-glow)`} />

      <path d="M160 110 L70 50" stroke="var(--auralytics-primary)" strokeWidth="1.5" opacity="0.35" />
      <path d="M160 110 L250 45" stroke="var(--auralytics-accent)" strokeWidth="1.5" opacity="0.35" />
      <path d="M160 110 L55 150" stroke="var(--auralytics-primary)" strokeWidth="1.5" opacity="0.28" />
      <path d="M160 110 L265 155" stroke="var(--auralytics-accent)" strokeWidth="1.5" opacity="0.28" />
      <path d="M160 110 L160 195" stroke="var(--auralytics-primary)" strokeWidth="1.5" opacity="0.3" />
      {variant === 'growth' && (
        <>
          <path d="M70 50 L70 20" stroke="var(--auralytics-primary)" strokeWidth="1.25" opacity="0.25" />
          <path d="M250 45 L280 20" stroke="var(--auralytics-accent)" strokeWidth="1.25" opacity="0.25" />
        </>
      )}

      <circle cx="160" cy="110" r="14" fill="var(--auralytics-primary)" opacity="0.9" />
      <circle cx="70" cy="50" r="10" fill="var(--auralytics-accent)" opacity="0.75" />
      <circle cx="250" cy="45" r="9" fill="var(--auralytics-primary)" opacity="0.65" />
      <circle cx="55" cy="150" r="8" fill="var(--auralytics-accent)" opacity="0.55" />
      <circle cx="265" cy="155" r="11" fill="var(--auralytics-primary)" opacity="0.7" />
      <circle cx="160" cy="195" r="9" fill="var(--auralytics-accent)" opacity="0.6" />

      <rect x="286" y="168" width="4" height="14" rx="1" fill="var(--auralytics-primary)" opacity="0.35" />
      <rect x="294" y="160" width="4" height="22" rx="1" fill="var(--auralytics-accent)" opacity="0.45" />
      <rect x="302" y="152" width="4" height="30" rx="1" fill="var(--auralytics-primary)" opacity="0.55" />
    </svg>
  )
}

/** Auth panel decorative stage with flowing ribbon (no network nodes). */
export function AuthStage({
  title,
  subtitle,
  footer,
  children,
}: {
  title: string
  subtitle: string
  footer?: string
  children?: React.ReactNode
}) {
  return (
    <aside className="relative hidden lg:flex flex-col justify-between p-10 xl:p-14 overflow-hidden bg-[#0c0f1c] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_15%_20%,rgba(91,95,239,0.4),transparent_50%),radial-gradient(ellipse_at_85%_75%,rgba(139,92,246,0.28),transparent_45%)]" />
      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />
      <div className="absolute -bottom-10 -right-10 w-72 h-72 rounded-full bg-primary/20 blur-3xl animate-orb" />
      <div className="absolute top-1/3 left-1/4 h-40 w-40 rounded-full border border-white/10 animate-glow-breathe" />
      <svg
        viewBox="0 0 480 420"
        className="absolute -right-16 top-10 w-[120%] opacity-70 animate-orb pointer-events-none"
        aria-hidden
      >
        <defs>
          <linearGradient id="auth-ribbon" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.25" />
          </linearGradient>
        </defs>
        <path
          d="M40 320 C 120 180, 200 380, 280 220 S 400 80, 460 200"
          fill="none"
          stroke="url(#auth-ribbon)"
          strokeWidth="48"
          strokeLinecap="round"
          opacity="0.5"
          className="animate-hero-wave"
        />
      </svg>

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
        <h1 className="text-4xl xl:text-[2.75rem] font-extrabold leading-[1.1] tracking-tight">{title}</h1>
        <p className="mt-5 text-white/70 text-base leading-relaxed">{subtitle}</p>
        {children}
      </div>

      <p className="relative text-xs text-white/40">{footer || 'Autonomous Influencer Marketing. From Discovery to ROI.'}</p>
    </aside>
  )
}

/** Subtle scanning nodes shown while Discovery runs. Decorative only. */
export function DiscoveryScanVisual({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 48" className={cn('w-28 h-auto', className)} aria-hidden="true">
      <defs>
        <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="transparent" />
          <stop offset="50%" stopColor="var(--auralytics-primary)" />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="24" r="5" fill="var(--auralytics-primary)" opacity="0.55" className="animate-pulse-dot" />
      <circle cx="48" cy="14" r="4" fill="var(--auralytics-accent)" opacity="0.45" />
      <circle cx="72" cy="30" r="4.5" fill="var(--auralytics-primary)" opacity="0.5" />
      <circle cx="100" cy="18" r="5" fill="var(--auralytics-accent)" opacity="0.4" className="animate-pulse-dot" />
      <path
        d="M20 24 L48 14 L72 30 L100 18"
        fill="none"
        stroke="var(--auralytics-primary)"
        strokeWidth="1.25"
        opacity="0.35"
      />
      <rect x="0" y="0" width="120" height="48" fill="url(#scanGrad)" opacity="0.2" />
    </svg>
  )
}
