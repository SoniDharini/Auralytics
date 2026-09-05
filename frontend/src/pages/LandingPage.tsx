import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  FileText,
  Lock,
  Search,
  Send,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui'
import { PageAmbientBackground } from '@/components/brand/VisualSystem'
import { LandingHeroVisual, ThemeToggleButton } from '@/components/brand/PremiumVisuals'
import { cn } from '@/utils'

const features = [
  { icon: Search, title: 'Creator Discovery', desc: 'Find YouTube creators that match your campaign brief.' },
  { icon: Send, title: 'Outreach', desc: 'Generate pitches, track replies, and negotiate terms.' },
  { icon: FileText, title: 'Contracts', desc: 'Draft, review, and approve collaboration agreements.' },
  { icon: BarChart3, title: 'Analytics', desc: 'Monitor spend, revenue, and campaign health.' },
  { icon: Target, title: 'Optimization', desc: 'Surface improvement opportunities with human approval.' },
]

const heroNotes = [
  { icon: Sparkles, label: 'Powered by AI agents' },
  { icon: Zap, label: 'Human-in-the-loop' },
  { icon: Target, label: 'From Discovery to ROI' },
  { icon: Lock, label: 'Built for marketing teams' },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-page text-text relative overflow-hidden">
      <PageAmbientBackground variant="landing" className="!mx-0 !mt-0 h-full opacity-90" />

      <header className="relative sticky top-0 z-40 border-b border-border/70 bg-surface/75 dark:bg-[#0c0f1c]/70 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2.5 min-w-0">
            <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center shadow-[0_4px_14px_rgba(91,95,239,0.35)]">
              A
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold leading-tight">Auralytics</p>
              <p className="text-[10px] text-text-secondary truncate">From Discovery to ROI</p>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-7 text-sm text-text-secondary">
            <a href="#features" className="hover:text-text transition-colors">
              Features
            </a>
            <a href="#why" className="hover:text-text transition-colors">
              Why Auralytics
            </a>
            <a href="#security" className="hover:text-text transition-colors">
              Security
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggleButton />
            <Link to="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/signup">
              <Button size="sm" className="gap-1.5 shadow-[0_8px_20px_rgba(91,95,239,0.22)]">
                Get Started <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <section className="relative">
        <div className="max-w-6xl mx-auto px-4 pt-16 pb-12 lg:pt-24 lg:pb-16">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="animate-fade-in">
              <p className="inline-flex items-center rounded-full border border-primary/20 bg-primary-soft/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
                AI-powered influencer marketing
              </p>
              <h1 className="mt-4 text-4xl sm:text-5xl lg:text-[52px] font-extrabold tracking-tight leading-[1.08]">
                Find the right creators.
                <br />
                Manage collaborations.
                <br />
                <span className="ai-gradient-text">Measure real impact.</span>
              </h1>
              <p className="mt-5 text-base sm:text-lg text-text-secondary max-w-xl leading-relaxed">
                AI-powered influencer campaign management — from discovery and outreach to contracts and
                performance, with humans always in control.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/signup">
                  <Button size="lg" className="gap-2 shadow-[0_10px_28px_rgba(91,95,239,0.28)] hover:shadow-[0_12px_32px_rgba(91,95,239,0.36)] transition-shadow">
                    Get Started <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/login">
                  <Button size="lg" variant="secondary">
                    Sign In
                  </Button>
                </Link>
              </div>
            </div>

            <div className="relative animate-fade-in">
              <LandingHeroVisual />
            </div>
          </div>
        </div>

        <div className="relative border-t border-border/70 bg-surface/40 dark:bg-elevated/20">
          <div className="max-w-6xl mx-auto px-4 py-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
            {heroNotes.map(({ icon: Icon, label }, i) => (
              <div
                key={label}
                className={cn('flex items-center gap-2 py-1', i > 0 && 'lg:border-l lg:border-border lg:pl-6')}
              >
                <Icon className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="text-xs font-medium text-text-secondary">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="relative py-16 border-b border-border bg-surface/50">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Everything in one workspace</h2>
          <p className="mt-2 text-text-secondary max-w-2xl">
            Real product capabilities — discover creators, run outreach, manage contracts, and track results.
          </p>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {features.map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="rounded-[16px] border border-border bg-surface p-4 ui-card-hover ui-card-accent"
              >
                <div className="h-9 w-9 rounded-xl bg-primary-soft text-primary flex items-center justify-center mb-3">
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="font-semibold text-text text-sm">{title}</h3>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="why" className="relative py-16">
        <div className="max-w-6xl mx-auto px-4 grid lg:grid-cols-2 gap-10 items-start">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Why Auralytics</h2>
            <p className="mt-3 text-text-secondary leading-relaxed">
              Stop juggling spreadsheets and scattered DMs. Run the full influencer lifecycle with AI assistance
              and clear human approval at critical moments.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                'Campaign workflow from strategy to performance',
                'YouTube-backed creator discovery and shortlisting',
                'Outreach and negotiation in one place',
                'Contract review with human sign-off',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-text">
                  <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[18px] border border-border bg-surface p-6 ui-card-accent">
            <div className="flex items-center gap-2 text-primary mb-3">
              <Zap className="h-5 w-5" />
              <p className="text-sm font-semibold">Human-in-the-loop by design</p>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              Agents accelerate discovery, outreach, contracts, and analysis. Approvals stay with your team —
              especially for budget and commercial decisions.
            </p>
          </div>
        </div>
      </section>

      <section id="security" className="relative py-16 border-y border-border bg-surface/50">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <Lock className="h-8 w-8 text-primary mx-auto mb-4" />
          <h2 className="text-2xl font-bold">Built for marketing teams</h2>
          <p className="mt-2 text-text-secondary max-w-xl mx-auto">
            Authenticated workspaces, campaign ownership, and audited workflows so your brand data stays
            protected.
          </p>
        </div>
      </section>

      <section className="relative py-20">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Ready to run campaigns from Discovery to ROI?
          </h2>
          <p className="mt-4 text-text-secondary">Start with Auralytics — your workspace, your campaigns.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/signup">
              <Button size="lg" className="gap-2">
                Get Started <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="secondary">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <footer className="relative border-t border-border bg-surface py-10">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row justify-between gap-4 text-sm text-text-secondary">
          <div>
            <p className="font-bold text-text">Auralytics</p>
            <p className="mt-1">From Discovery to ROI.</p>
          </div>
          <div className="flex gap-6">
            <Link to="/login" className="hover:text-text">
              Sign in
            </Link>
            <Link to="/signup" className="hover:text-text">
              Sign up
            </Link>
            <a href="#features" className="hover:text-text">
              Features
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
