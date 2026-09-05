import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Loader2, Lock } from 'lucide-react'
import { Button, Input, Select } from '@/components/ui'
import { PasswordInput } from '@/components/auth/PasswordInput'
import { PageAmbientBackground } from '@/components/brand/VisualSystem'
import { AuthBrandPanel, ThemeToggleButton } from '@/components/brand/PremiumVisuals'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/utils'

const roles = [
  { value: 'marketing_manager', label: 'Marketing Manager' },
  { value: 'brand_manager', label: 'Brand Manager' },
  { value: 'agency', label: 'Agency' },
  { value: 'founder', label: 'Founder' },
  { value: 'other', label: 'Other' },
]

export function SignUpPage() {
  const navigate = useNavigate()
  const { register } = useAuth()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('marketing_manager')
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [serverError, setServerError] = useState<string | null>(null)

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setServerError(null)
    if (!validate()) return

    setLoading(true)
    try {
      await register({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        company_name: company.trim(),
        role,
      })
      navigate('/app', { replace: true })
    } catch (err: any) {
      if (err.message && err.message.toLowerCase().includes('already exists')) {
        setErrors((prev) => ({ ...prev, email: 'An account with this email already exists.' }))
      } else {
        setServerError(err.message || 'Failed to create account. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <AuthBrandPanel
        variant="signup"
        title="Start. Build. Collaborate. Grow."
        subtitle="Build campaigns, find creators, and collaborate — with humans still in control."
        words={['Start', 'Build', 'Collaborate', 'Grow']}
      />

      <main className="relative flex items-center justify-center p-6 sm:p-10 bg-page overflow-hidden">
        <PageAmbientBackground variant="auth" className="!mx-0 !mt-0" />
        <div className="absolute top-5 right-5 z-10">
          <ThemeToggleButton />
        </div>
        <div className="relative w-full max-w-md animate-fade-in">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">
                A
              </div>
              <div>
                <p className="font-bold leading-tight text-text">Auralytics</p>
                <p className="text-[11px] text-text-secondary">From Discovery to ROI</p>
              </div>
            </Link>
          </div>

          <div className="rounded-[22px] border border-border bg-surface dark:bg-elevated p-6 sm:p-8 relative overflow-hidden shadow-[0_16px_48px_rgba(91,95,239,0.08)] dark:shadow-[0_16px_48px_rgba(0,0,0,0.35)]">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-accent via-primary to-transparent" />
            <h2 className="text-2xl font-bold tracking-tight text-text">Create your account</h2>
            <p className="text-sm text-text-secondary mt-1">
              Start managing smarter influencer campaigns with your AI marketing team.
            </p>

            {serverError && (
              <div className="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-danger/30 text-danger text-sm flex items-start gap-2.5">
                <AlertCircle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                <span>{serverError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
              <Input
                label="Full Name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Aaditya Sharma"
                error={errors.fullName}
                autoComplete="name"
                required
                className="h-11"
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
                className="h-11"
              />
              <PasswordInput
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                hint="Use at least 8 characters."
                error={errors.password}
                autoComplete="new-password"
                required
                className="h-11 bg-elevated"
              />
              <PasswordInput
                label="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                error={errors.confirmPassword}
                autoComplete="new-password"
                required
                className="h-11 bg-elevated"
              />
              <Input
                label="Company / Brand Name"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="GlowNaturals"
                error={errors.company}
                autoComplete="organization"
                required
                className="h-11"
              />
              <Select label="Role" options={roles} value={role} onChange={(e) => setRole(e.target.value)} />

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

              <Button
                type="submit"
                className="w-full shadow-[0_8px_22px_rgba(91,95,239,0.28)] hover:shadow-[0_10px_26px_rgba(91,95,239,0.36)]"
                size="lg"
                disabled={loading}
              >
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
