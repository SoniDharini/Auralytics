import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Lock,
  Play,
  Search,
  Send,
  Sparkles,
  BarChart3,
  Shield,
  Zap,
} from 'lucide-react'
import { Button } from '@/components/ui'
import { agents } from '@/mock-data'

const problems = [
  'Manual creator discovery wastes weeks of research.',
  'Outreach is inconsistent and hard to personalize at scale.',
  'Budget decisions lack clear ROI signal until campaigns end.',
]

const steps = [
  { title: 'Brief', desc: 'Define audience, budget, and goals.' },
  { title: 'Discover', desc: 'AI ranks creators by predicted ROAS.' },
  { title: 'Collaborate', desc: 'Approve outreach, negotiate, contract.' },
  { title: 'Optimize', desc: 'Reallocate spend with human approval.' },
]

export function LandingPage() {
  return (
    <div className="min-h-screen bg-page text-text">
      <header className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-border">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">A</div>
            <div>
              <p className="text-sm font-bold leading-tight">Auralytics</p>
              <p className="text-[10px] text-text-secondary">Autonomous Influencer Marketing</p>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-text-secondary">
            <a href="#how" className="hover:text-text">How it works</a>
            <a href="#agents" className="hover:text-text">AI Agents</a>
            <a href="#analytics" className="hover:text-text">Analytics</a>
            <a href="#security" className="hover:text-text">Security</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link to="/login">
              <Button size="sm">Start Campaign</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(91,95,239,0.12),_transparent_50%),radial-gradient(ellipse_at_bottom_left,_rgba(124,58,237,0.08),_transparent_45%)]" />
        <div className="relative max-w-6xl mx-auto px-4 pt-16 pb-20 lg:pt-24 lg:pb-28">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold text-primary mb-4">Auralytics</p>
            <h1 className="text-4xl sm:text-5xl lg:text-[56px] font-extrabold tracking-tight leading-[1.08]">
              Turn influencer marketing into an{' '}
              <span className="ai-gradient-text">autonomous growth engine.</span>
            </h1>
            <p className="mt-5 text-base sm:text-lg text-text-secondary max-w-2xl leading-relaxed">
              Auralytics uses specialized AI agents to discover creators, manage outreach, monitor campaigns,
              and continuously optimize ROI — with humans always in control of financial decisions.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/login">
                <Button size="lg" className="gap-2">
                  Start Campaign <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <a href="#demo">
                <Button size="lg" variant="secondary" className="gap-2">
                  <Play className="h-4 w-4" /> Watch Demo
                </Button>
              </a>
            </div>
            <p className="mt-4 text-xs text-text-secondary flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5" />
              Built for marketing teams managing six-figure campaign budgets.
            </p>
          </div>

          {/* Product mock */}
          <div id="demo" className="mt-14 rounded-[16px] border border-border bg-white shadow-[0_20px_60px_rgba(17,24,39,0.08)] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-page">
              <span className="h-2.5 w-2.5 rounded-full bg-red-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-300" />
              <span className="ml-3 text-xs text-text-secondary">Campaign Command Center · GlowNaturals Summer Launch</span>
            </div>
            <div className="grid lg:grid-cols-[1fr_280px]">
              <div className="p-5 lg:p-6">
                <div className="flex flex-wrap gap-4 mb-5">
                  {[
                    { label: 'Spend', value: '₹1.28L' },
                    { label: 'Revenue', value: '₹3.92L' },
                    { label: 'ROAS', value: '3.06x' },
                    { label: 'Creators', value: '8' },
                  ].map((m) => (
                    <div key={m.label} className="rounded-[12px] border border-border px-4 py-3 min-w-[120px]">
                      <p className="text-xs text-text-secondary">{m.label}</p>
                      <p className="text-xl font-bold mt-1">{m.value}</p>
                    </div>
                  ))}
                </div>
                <div className="h-40 rounded-[12px] bg-gradient-to-b from-primary-soft to-white border border-border flex items-end px-4 pb-4 gap-2">
                  {[40, 55, 48, 70, 62, 85, 78, 92, 88, 100].map((h, i) => (
                    <div key={i} className="flex-1 rounded-t-md bg-primary/70" style={{ height: `${h}%` }} />
                  ))}
                </div>
              </div>
              <div className="border-t lg:border-t-0 lg:border-l border-border p-4 bg-page/50 space-y-2.5">
                <p className="text-xs font-semibold text-text-secondary uppercase tracking-wide px-1">Live AI Activity</p>
                {agents.slice(0, 4).map((a) => (
                  <div key={a.id} className="rounded-[10px] bg-white border border-border p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold">{a.name.replace(' Agent', '')}</p>
                      <span className="flex items-center gap-1 text-[10px] font-semibold text-success">
                        <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse-dot" />
                        {a.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-secondary mt-1 line-clamp-1">{a.currentTask}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="py-16 bg-white border-y border-border">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl sm:text-3xl font-bold max-w-xl">Influencer marketing is still too manual for modern growth teams.</h2>
          <p className="mt-3 text-text-secondary max-w-2xl">
            Spreadsheets, DMs, and delayed reporting leave budget on the table. Auralytics automates the lifecycle while keeping humans in the approval loop.
          </p>
          <div className="mt-8 grid sm:grid-cols-3 gap-4">
            {problems.map((p) => (
              <div key={p} className="rounded-[14px] border border-border p-5">
                <Zap className="h-5 w-5 text-primary mb-3" />
                <p className="text-sm font-medium leading-relaxed">{p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="py-16">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl sm:text-3xl font-bold">How Auralytics works</h2>
          <p className="mt-2 text-text-secondary">From brief to ROI in one intelligent workspace.</p>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {steps.map((s, i) => (
              <div key={s.title} className="rounded-[14px] bg-white border border-border p-5 relative">
                <span className="text-xs font-bold text-primary">0{i + 1}</span>
                <h3 className="mt-2 text-lg font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm text-text-secondary">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Agents */}
      <section id="agents" className="py-16 bg-white border-y border-border">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-2xl sm:text-3xl font-bold">Meet your autonomous marketing team.</h2>
          <p className="mt-2 text-text-secondary max-w-2xl">
            Seven specialized agents collaborate under a Supervisor — so every campaign moves from discovery to optimization without losing human oversight.
          </p>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { name: 'Strategy Agent', desc: 'Plans campaign direction', icon: Sparkles },
              { name: 'Discovery Agent', desc: 'Finds the best-fit creators', icon: Search },
              { name: 'Outreach Agent', desc: 'Personalizes conversations', icon: Send },
              { name: 'Contract Agent', desc: 'Tracks obligations and risks', icon: Shield },
              { name: 'Performance Agent', desc: 'Analyzes campaign health', icon: BarChart3 },
              { name: 'Optimization Agent', desc: 'Finds opportunities to improve ROI', icon: Zap },
              { name: 'Supervisor Agent', desc: 'Coordinates everything', icon: Bot },
            ].map((a) => (
              <div key={a.name} className="rounded-[14px] border border-border p-5 hover:border-primary/40 transition">
                <div className="h-10 w-10 rounded-xl bg-primary-soft text-primary flex items-center justify-center mb-3">
                  <a.icon className="h-5 w-5" />
                </div>
                <h3 className="font-semibold">{a.name}</h3>
                <p className="text-sm text-text-secondary mt-1">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Analytics + HITL */}
      <section id="analytics" className="py-16">
        <div className="max-w-6xl mx-auto px-4 grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold">Influencer intelligence with explainable AI.</h2>
            <p className="mt-3 text-text-secondary leading-relaxed">
              Every recommendation includes confidence, expected impact, and the data behind it. Budget changes always require human approval.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                'AI Match Score & predicted ROAS',
                'Audience fit and authenticity signals',
                'Negotiation recommendations with ROAS projections',
                'Approval Center for outreach, budget, and contracts',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-[16px] border border-border bg-white p-6 shadow-sm">
            <p className="text-xs font-semibold text-ai mb-3">Human-in-the-Loop Control</p>
            <div className="space-y-3">
              <div className="rounded-[12px] border border-border p-4">
                <p className="text-sm font-semibold">Optimization Agent</p>
                <p className="text-xs text-text-secondary mt-1">Reallocate ₹10,000 from RiyaStyle → NehaBeauty & AditiBeauty</p>
                <p className="text-xs font-semibold text-primary mt-2">Expected uplift +₹34K · 86% confidence</p>
                <div className="mt-3 flex gap-2">
                  <Button size="sm" variant="secondary">Reject</Button>
                  <Button size="sm">Approve</Button>
                </div>
              </div>
              <p className="text-xs text-text-secondary flex items-center gap-1.5">
                <Shield className="h-3.5 w-3.5" />
                Automatic budget modification is never enabled without explicit warnings.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="security" className="py-16 bg-white border-y border-border">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <Lock className="h-8 w-8 text-primary mx-auto mb-4" />
          <h2 className="text-2xl font-bold">Enterprise-ready security</h2>
          <p className="mt-2 text-text-secondary max-w-xl mx-auto">
            Role-based access, audit trails for every AI action, and encrypted campaign data so marketing teams can trust Auralytics with brand budgets.
          </p>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Ready to run influencer campaigns with an AI marketing team?
          </h2>
          <p className="mt-4 text-text-secondary">
            Autonomous Influencer Marketing. From Discovery to ROI.
          </p>
          <Link to="/login" className="inline-block mt-8">
            <Button size="lg" className="gap-2">
              Launch Auralytics <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      <footer className="border-t border-border bg-white py-10">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row justify-between gap-4 text-sm text-text-secondary">
          <div>
            <p className="font-bold text-text">Auralytics</p>
            <p className="mt-1">Autonomous Influencer Marketing. From Discovery to ROI.</p>
          </div>
          <div className="flex gap-6">
            <Link to="/login" className="hover:text-text">Sign in</Link>
            <a href="#how" className="hover:text-text">Product</a>
            <a href="#security" className="hover:text-text">Security</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
