import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2, Lock, Mail } from 'lucide-react'
import { Button, Input } from '@/components/ui'
import { PasswordInput } from '@/components/auth/PasswordInput'
import { PageAmbientBackground } from '@/components/brand/VisualSystem'
import { AuthBrandPanel, ThemeToggleButton } from '@/components/brand/PremiumVisuals'
import { useAuth } from '@/context/AuthContext'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const [email, setEmail] = useState('aaditya@glownaturals.com')
  const [password, setPassword] = useState('password123')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await login(email, password)
      const fromPath = (location.state as any)?.from?.pathname || '/app'
      navigate(fromPath, { replace: true })
    } catch (err: any) {
      setError(err.message || 'Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <main className="relative flex items-center justify-center p-6 sm:p-10 bg-page overflow-hidden">
        <PageAmbientBackground variant="auth" className="!mx-0 !mt-0" />
        <div className="absolute top-5 right-5 z-10">
          <ThemeToggleButton />
        </div>
        <div className="relative w-full max-w-[420px] animate-fade-in">
          <div className="lg:hidden mb-8 flex items-center gap-2">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg ai-gradient-bg text-white font-bold flex items-center justify-center">
                A
              </div>
              <span className="font-bold text-text">Auralytics</span>
            </Link>
          </div>

          <div className="rounded-[22px] border border-border bg-surface dark:bg-elevated p-6 sm:p-8 relative overflow-hidden shadow-[0_16px_48px_rgba(91,95,239,0.08)] dark:shadow-[0_16px_48px_rgba(0,0,0,0.35)]">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-primary via-accent to-transparent" />
            <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-primary/10 blur-2xl pointer-events-none" />
            <h2 className="text-2xl font-bold tracking-tight text-text">Welcome back</h2>
            <p className="text-sm text-text-secondary mt-1">Sign in to your marketing workspace</p>

            {error && (
              <div className="mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-danger/30 text-danger text-sm flex items-start gap-2.5">
                <AlertCircle className="h-4.5 w-4.5 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="h-11"
              />
              <div>
                <PasswordInput
                  label="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="h-11 bg-elevated"
                />
                <div className="mt-1.5 text-right">
                  <button type="button" className="text-xs font-semibold text-primary hover:underline">
                    Forgot Password
                  </button>
                </div>
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
                    Signing in...
                  </>
                ) : (
                  <>
                    <Mail className="h-4 w-4" />
                    Sign In
                  </>
                )}
              </Button>
            </form>

            <div className="my-5 flex items-center gap-3">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs text-text-secondary">or</span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <Button
              type="button"
              variant="secondary"
              className="w-full"
              size="lg"
              onClick={() =>
                setError('Google sign-in is not available yet. Use your email and password, or create an account.')
              }
            >
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

      <AuthBrandPanel
        variant="signin"
        title="Ideas. Collaborations. Growth. Real Impact."
        subtitle="Discover creators, manage outreach, and measure performance — from one intelligent workspace."
        words={['Discover', 'Collaborate', 'Analyze']}
      />
    </div>
  )
}
