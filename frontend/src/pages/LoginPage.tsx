import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import { AlertCircle, Eye, EyeOff, Loader2, LogIn, Timer, ShieldCheck } from 'lucide-react'

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { login } = useAuth()
  const navigate = useNavigate()

  // Demonstration helper can be disabled for production by setting VITE_ENABLE_DEMO_LOGIN="false"
  const showDemoLogin = import.meta.env.VITE_ENABLE_DEMO_LOGIN !== 'false'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const tokenData = await apiService.login({ email, password })
      await login(tokenData)

      if (tokenData.user.role === 'SUPPLIER') {
        navigate('/supplier/inventory')
      } else if (tokenData.user.role === 'RECEIVER') {
        navigate('/receiver/demands')
      } else if (tokenData.user.role === 'COORDINATOR' || tokenData.user.role === 'ADMIN') {
        navigate('/coordinator/optimization')
      } else {
        navigate('/')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Login failed. Please check your credentials.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const fillQuickAccount = (role: 'COORDINATOR' | 'SUPPLIER' | 'RECEIVER') => {
    if (role === 'COORDINATOR') {
      setEmail('coordinator@fhd.org')
      setPassword('CoordinatorPass123!')
    } else if (role === 'SUPPLIER') {
      setEmail('demo_bakery@fhd.org')
      setPassword('DemoPass123!')
    } else if (role === 'RECEIVER') {
      setEmail('demo_kitchen@fhd.org')
      setPassword('DemoPass123!')
    }
  }

  return (
    <div className="max-w-md mx-auto my-8 sm:my-12">
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
            <Timer className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Sign In to FHD</h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Enter your authorized credentials to access your redistribution dashboard.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-destructive/25 bg-destructive/10 p-3.5 text-xs text-destructive flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <span className="font-semibold block">Authentication Error</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Email Address
            </label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@organization.org"
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Password
              </label>
            </div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg border border-input bg-background pl-3.5 pr-10 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1 rounded focus:outline-none"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <Button type="submit" disabled={loading} className="w-full gap-2 text-sm font-semibold h-10 shadow-sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
            {loading ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>

        <div className="text-center text-xs text-muted-foreground border-t border-border/70 pt-4">
          Don&apos;t have an account yet?{' '}
          <Link to="/register" className="font-semibold text-primary hover:underline">
            Register your organization
          </Link>
        </div>

        {/* Demo Credentials Helper for Evaluators */}
        {showDemoLogin && (
          <div className="rounded-xl border border-border/80 bg-muted/40 p-3 space-y-2 text-xs">
            <div className="flex items-center justify-between text-muted-foreground font-semibold">
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-primary" />
                <span>Demonstration Quick-Fill (Evaluator Convenience)</span>
              </div>
              <span className="text-[10px] text-muted-foreground font-mono">Demo Mode</span>
            </div>
            <p className="text-[11px] text-muted-foreground leading-tight">
              Populates pre-seeded demonstration accounts created by <code className="text-foreground">seed_demo_data.py</code>.
              Can be disabled in production via <code className="text-foreground">VITE_ENABLE_DEMO_LOGIN=false</code>.
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button
                type="button"
                onClick={() => fillQuickAccount('COORDINATOR')}
                className="rounded bg-card border border-border px-2.5 py-1 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors"
                title="coordinator@fhd.org"
              >
                Coordinator
              </button>
              <button
                type="button"
                onClick={() => fillQuickAccount('SUPPLIER')}
                className="rounded bg-card border border-border px-2.5 py-1 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors"
                title="demo_bakery@fhd.org"
              >
                Supplier (Bakery)
              </button>
              <button
                type="button"
                onClick={() => fillQuickAccount('RECEIVER')}
                className="rounded bg-card border border-border px-2.5 py-1 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors"
                title="demo_kitchen@fhd.org"
              >
                Receiver (Kitchen)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
