import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bot, Lock, Sparkles } from 'lucide-react'
import { Button, Input } from '@/components/ui'

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('aaditya@glownaturals.com')
  const [password, setPassword] = useState('••••••••')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const onboarded = localStorage.getItem('auralytics_onboarded')
    navigate(onboarded ? '/app' : '/onboarding')
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <aside className="relative hidden lg:flex flex-col justify-between p-10 xl:p-14 overflow-hidden bg-[#0f1225] text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_20%,rgba(91,95,239,0.35),transparent_50%),radial-gradient(ellipse_at_80%_80%,rgba(124,58,237,0.25),transparent_45%)]" />
        <div className="relative">
          <Link to="/" className="inline-flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl ai-gradient-bg flex items-center justify-center font-bold">A</div>
            <div>
              <p className="font-bold">Auralytics</p>
              <p className="text-xs text-white/60">From Discovery to ROI</p>
            </div>
          </Link>
        </div>

        <div className="relative max-w-lg">
          <h1 className="text-4xl xl:text-5xl font-extrabold leading-tight tracking-tight">
            Run influencer campaigns with an AI marketing team.
          </h1>
          <p className="mt-5 text-white/70 text-base leading-relaxed">
            Discover creators, automate outreach, track performance, and optimize ROI from one intelligent workspace.
          </p>

          <div className="mt-10 grid grid-cols-2 gap-3">
            {[
              { name: 'Strategy', status: 'Ready' },
              { name: 'Discovery', status: 'Active' },
              { name: 'Outreach', status: 'Drafting' },
              { name: 'Performance', status: 'Monitoring' },
            ].map((a) => (
              <div key={a.name} className="rounded-xl border border-white/10 bg-white/5 backdrop-blur px-4 py-3">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-[#a5b4fc]" />
                  <p className="text-sm font-semibold">{a.name}</p>
                </div>
                <p className="mt-1 text-xs text-white/50 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
                  {a.status}
                </p>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-white/40 flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5" />
          Autonomous Influencer Marketing. From Discovery to ROI.
        </p>
      </aside>

      <main className="flex items-center justify-center p-6 sm:p-10 bg-page">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">A</div>
            <span className="font-bold">Auralytics</span>
          </div>

          <div className="bg-white border border-border rounded-[16px] p-6 sm:p-8 shadow-sm">
            <h2 className="text-2xl font-bold">Welcome back</h2>
            <p className="text-sm text-text-secondary mt-1">Sign in to your marketing workspace</p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <div>
                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <div className="mt-1.5 text-right">
                  <button type="button" className="text-xs font-semibold text-primary hover:underline">
                    Forgot Password
                  </button>
                </div>
              </div>
              <Button type="submit" className="w-full" size="lg">
                Sign In
              </Button>
            </form>

            <div className="my-5 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-text-secondary">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <Button type="button" variant="secondary" className="w-full" size="lg">
              Sign in with Google
            </Button>

            <p className="mt-5 text-center text-sm text-text-secondary">
              Don&apos;t have an account?{' '}
              <Link to="/signup" className="font-semibold text-primary hover:underline">
                Create account
              </Link>
            </p>
          </div>

          <p className="mt-6 text-center text-xs text-text-secondary flex items-center justify-center gap-1.5">
            <Lock className="h-3.5 w-3.5" />
            Your campaigns and brand data remain securely protected.
          </p>
        </div>
      </main>
    </div>
  )
}
