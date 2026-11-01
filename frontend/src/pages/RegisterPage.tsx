import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  UserPlus,
  Building2,
  HeartHandshake,
  Timer,
} from 'lucide-react'

export const RegisterPage: React.FC = () => {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [role, setRole] = useState<'SUPPLIER' | 'RECEIVER'>('SUPPLIER')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      await apiService.register({ name, email, password, role })
      setSuccess('Account created successfully! Redirecting to sign in...')
      setTimeout(() => {
        navigate('/login')
      }, 1500)
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto my-8 sm:my-12">
      <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 shadow-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-white shadow-sm">
            <Timer className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">Create an FHD Account</h1>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Join the perishability-aware food rescue and redistribution network.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-destructive/25 bg-destructive/10 p-3.5 text-xs text-destructive flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <span className="font-semibold block">Registration Error</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {success && (
          <div className="rounded-xl border border-primary/25 bg-primary/10 p-3.5 text-xs text-secondary-foreground flex items-center gap-2.5">
            <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />
            <span className="font-medium">{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Operational Role Selector */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Select Operational Role
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setRole('SUPPLIER')}
                className={`rounded-xl border p-3.5 text-left transition-all ${
                  role === 'SUPPLIER'
                    ? 'border-primary bg-primary/10 ring-1 ring-primary text-foreground shadow-sm'
                    : 'border-border bg-background hover:bg-muted/50 text-muted-foreground'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <Building2 className={`h-4 w-4 ${role === 'SUPPLIER' ? 'text-primary' : 'text-muted-foreground'}`} />
                  <span className={`text-sm font-bold ${role === 'SUPPLIER' ? 'text-foreground' : ''}`}>
                    Food Supplier
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-tight">
                  Supermarket, farm, bakery, distributor or catering facility with surplus stock.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setRole('RECEIVER')}
                className={`rounded-xl border p-3.5 text-left transition-all ${
                  role === 'RECEIVER'
                    ? 'border-primary bg-primary/10 ring-1 ring-primary text-foreground shadow-sm'
                    : 'border-border bg-background hover:bg-muted/50 text-muted-foreground'
                }`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <HeartHandshake className={`h-4 w-4 ${role === 'RECEIVER' ? 'text-primary' : 'text-muted-foreground'}`} />
                  <span className={`text-sm font-bold ${role === 'RECEIVER' ? 'text-foreground' : ''}`}>
                    Food Receiver
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-tight">
                  Food bank, shelter, relief kitchen, or community pantry distributing to clients.
                </p>
              </button>
            </div>
          </div>

          {/* Contact / Organization Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Organization or Contact Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Metro Produce Hub or Valley Community Food Bank"
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
            />
          </div>

          {/* Email Address */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="operator@organization.org"
              className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all"
            />
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Password (min 8 characters)
              </label>
            </div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={8}
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
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
            {loading ? 'Creating Organization Account...' : 'Register Organization'}
          </Button>
        </form>

        <div className="text-center text-xs text-muted-foreground border-t border-border/70 pt-4">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            Sign in to existing account
          </Link>
        </div>
      </div>
    </div>
  )
}
