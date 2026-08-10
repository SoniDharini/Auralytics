import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  BarChart3,
  CheckCircle2,
  Loader2,
  Lock,
  Search,
  Sparkles,
  Target,
  Workflow,
} from 'lucide-react'
import { Button, Input, Select } from '@/components/ui'
import { PasswordInput } from '@/components/auth/PasswordInput'
import { cn } from '@/utils'

const roles = [
  { value: 'marketing_manager', label: 'Marketing Manager' },
  { value: 'brand_manager', label: 'Brand Manager' },
  { value: 'agency', label: 'Agency' },
  { value: 'founder', label: 'Founder' },
  { value: 'other', label: 'Other' },
]

const highlights = [
  { icon: Search, text: 'Discover the right creators' },
  { icon: Workflow, text: 'Automate campaign workflows' },
  { icon: BarChart3, text: 'Monitor performance' },
  { icon: Target, text: 'Optimize ROI' },
]

export function SignUpPage() {
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('marketing_manager')
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const next: Record<string, string> = {}
    if (!fullName.trim()) next.fullName = 'Full name is required.'
    if (!email.trim()) next.email = 'Work email is required.'
    if (password.length < 8) next.password = 'Use at least 8 characters.'
    if (password !== confirmPassword) next.confirmPassword = 'Passwords do not match.'
    if (!company.trim()) next.company = 'Company / brand name is required.'
    if (!agreed) next.agreed = 'Please agree to the Terms of Service and Privacy Policy.'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    // Demo-only UI flow — no backend auth. Mirror existing login navigation.
    window.setTimeout(() => {
      setLoading(false)
      const onboarded = localStorage.getItem('auralytics_onboarded')
      navigate(onboarded ? '/app' : '/onboarding')
    }, 900)
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <aside className="relative hidden lg:flex flex-col justify-between p-10 xl:p-14 overflow-hidden bg-[#0f1225] text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_20%_20%,rgba(91,95,239,0.35),transparent_50%),radial-gradient(ellipse_at_80%_80%,rgba(124,58,237,0.25),transparent_45%)]" />
        <div className="relative">
          <Link to="/" className="inline-flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl ai-gradient-bg flex items-center justify-center font-bold">A</div>
            <div>
              <p className="font-bold">InfluenceOS</p>
              <p className="text-xs text-white/60">From Discovery to ROI</p>
            </div>
          </Link>
        </div>

        <div className="relative max-w-lg">
          <h1 className="text-4xl xl:text-5xl font-extrabold leading-tight tracking-tight">
            Your AI-powered influencer marketing team starts here.
          </h1>
          <p className="mt-5 text-white/70 text-base leading-relaxed">
            Autonomous Influencer Marketing. From Discovery to ROI.
          </p>

          <ul className="mt-10 space-y-3">
            {highlights.map(({ icon: Icon, text }) => (
              <li
                key={text}
                className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3"
              >
                <span className="h-8 w-8 rounded-lg bg-white/10 flex items-center justify-center">
                  <Icon className="h-4 w-4 text-[#a5b4fc]" />
                </span>
                <span className="text-sm font-medium text-white/90">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/40 flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5" />
          Autonomous Influencer Marketing. From Discovery to ROI.
        </p>
      </aside>

      <main className="flex items-center justify-center p-6 sm:p-10 bg-page">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">
              A
            </div>
            <div>
              <p className="font-bold leading-tight">InfluenceOS</p>
              <p className="text-[11px] text-text-secondary">
                Autonomous Influencer Marketing. From Discovery to ROI.
              </p>
            </div>
          </div>

          <div className="bg-white border border-border rounded-[16px] p-6 sm:p-8 shadow-sm">
            <h2 className="text-2xl font-bold">Create your account</h2>
            <p className="text-sm text-text-secondary mt-1">
              Start managing smarter influencer campaigns with your AI marketing team.
            </p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
              <Input
                label="Full Name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Aaditya Sharma"
                error={errors.fullName}
                autoComplete="name"
                required
              />
              <Input
                label="Work Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                error={errors.email}
                autoComplete="email"
                required
              />
              <PasswordInput
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                hint="Use at least 8 characters."
                error={errors.password}
                autoComplete="new-password"
                required
              />
              <PasswordInput
                label="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={errors.confirmPassword}
                autoComplete="new-password"
                required
              />
              <Input
                label="Company / Brand Name"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="GlowNaturals"
                error={errors.company}
                autoComplete="organization"
                required
              />
              <Select
                label="Role"
                options={roles}
                value={role}
                onChange={(e) => setRole(e.target.value)}
              />

              <div className="space-y-1.5">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={agreed}
                    onChange={(e) => setAgreed(e.target.checked)}
                    className={cn(
                      'mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary/30',
                      errors.agreed && 'outline outline-1 outline-danger',
                    )}
                  />
                  <span className="text-sm text-text-secondary leading-relaxed">
                    I agree to the{' '}
                    <button type="button" className="font-semibold text-primary hover:underline">
                      Terms of Service
                    </button>{' '}
                    and{' '}
                    <button type="button" className="font-semibold text-primary hover:underline">
                      Privacy Policy
                    </button>
                    .
                  </span>
                </label>
                {errors.agreed && <p className="text-xs text-danger">{errors.agreed}</p>}
              </div>

              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4" />
                    Create Account
                  </>
                )}
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-text-secondary">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-primary hover:underline">
                Sign in
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
