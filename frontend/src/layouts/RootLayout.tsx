import React, { useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import {
  Timer,
  LogIn,
  LogOut,
  User as UserIcon,
  Building2,
  HeartHandshake,
  Cpu,
  Sparkles,
  Truck,
  Menu,
  X,
  ShieldCheck,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

export const RootLayout: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/')
    setMobileMenuOpen(false)
  }

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const navLinkClass = (path: string) =>
    `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
      isActive(path)
        ? 'bg-primary text-white shadow-sm'
        : 'text-foreground/80 hover:text-foreground hover:bg-black/5 dark:hover:bg-white/5'
    }`

  const currentYear = 2026

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/20 selection:text-foreground">
      {/* Top Banner Notice */}
      <div className="bg-primary/10 border-b border-primary/20 py-1.5 px-4 text-center text-xs text-secondary-foreground font-medium flex items-center justify-center gap-2">
        <ShieldCheck className="h-3.5 w-3.5 text-primary shrink-0" />
        <span>
          <strong>Food Has a Deadline (FHD)</strong> &bull; Perishability-Aware Redistribution Logistics Platform
        </span>
      </div>

      {/* Main Navigation Bar */}
      <header className="border-b border-border bg-card/90 backdrop-blur sticky top-0 z-50 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* Logo & Brand */}
          <Link
            to="/"
            className="flex items-center gap-3 group focus:outline-none focus:ring-2 focus:ring-primary rounded-lg p-1"
            onClick={() => setMobileMenuOpen(false)}
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white font-bold shadow-sm transition-transform group-hover:scale-105">
              <Timer className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold tracking-tight text-base sm:text-lg text-foreground leading-tight">
                FOOD HAS A DEADLINE
              </span>
              <span className="text-[11px] text-muted-foreground font-medium tracking-wide">
                Move food before time runs out.
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-2">
            {user ? (
              <div className="flex items-center gap-2">
                {user.role === 'SUPPLIER' && (
                  <>
                    <Link to="/supplier/inventory" className={navLinkClass('/supplier/inventory')}>
                      <Timer className="h-3.5 w-3.5" />
                      Surplus Inventory
                    </Link>
                    <Link to="/supplier/profile" className={navLinkClass('/supplier/profile')}>
                      <Building2 className="h-3.5 w-3.5" />
                      Facility Profile
                    </Link>
                  </>
                )}
                {user.role === 'RECEIVER' && (
                  <>
                    <Link to="/receiver/demands" className={navLinkClass('/receiver/demands')}>
                      <HeartHandshake className="h-3.5 w-3.5" />
                      Food Demands
                    </Link>
                    <Link to="/receiver/profile" className={navLinkClass('/receiver/profile')}>
                      <Building2 className="h-3.5 w-3.5" />
                      Facility Profile
                    </Link>
                  </>
                )}
                {(user.role === 'COORDINATOR' || user.role === 'ADMIN') && (
                  <>
                    <Link to="/coordinator/optimization" className={navLinkClass('/coordinator/optimization')}>
                      <Cpu className="h-3.5 w-3.5" />
                      Optimization Engine
                    </Link>
                    <Link to="/coordinator/transactions" className={navLinkClass('/coordinator/transactions')}>
                      <Truck className="h-3.5 w-3.5" />
                      Transactions
                    </Link>
                  </>
                )}

                <Link to="/assistant" className={navLinkClass('/assistant')}>
                  <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                  AI Copilot
                </Link>

                <div className="h-4 w-px bg-border mx-1" />

                <div className="flex items-center gap-2 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs">
                  <UserIcon className="h-3.5 w-3.5 text-primary" />
                  <span className="font-medium max-w-[140px] truncate" title={user.email}>
                    {user.email}
                  </span>
                  <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-bold text-primary uppercase tracking-wider">
                    {user.role}
                  </span>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="text-xs gap-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign Out
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <a
                  href="/#how-it-works"
                  className="px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                >
                  How It Works
                </a>
                <a
                  href="/#capabilities"
                  className="px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                >
                  Platform Capabilities
                </a>
                <div className="h-4 w-px bg-border mx-1" />
                <Link to="/login">
                  <Button variant="ghost" size="sm" className="gap-1.5 text-xs font-semibold">
                    <LogIn className="h-3.5 w-3.5 text-primary" />
                    Sign In
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="sm" className="gap-1.5 text-xs font-semibold shadow-sm">
                    Get Started
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex lg:hidden items-center gap-2">
            {user && (
              <span className="rounded bg-primary/15 px-2 py-0.5 text-[10px] font-bold text-primary uppercase">
                {user.role}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
              className="p-1.5 h-9 w-9"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-b border-border bg-card px-4 py-4 space-y-3 shadow-lg animate-in slide-in-from-top-2">
            {user ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 border-b border-border pb-2 text-xs">
                  <UserIcon className="h-4 w-4 text-primary" />
                  <span className="font-medium truncate">{user.email}</span>
                  <span className="ml-auto rounded bg-primary/20 px-2 py-0.5 text-[10px] font-bold text-primary">
                    {user.role}
                  </span>
                </div>

                {user.role === 'SUPPLIER' && (
                  <>
                    <Link
                      to="/supplier/inventory"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/supplier/inventory') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <Timer className="h-4 w-4" />
                      Surplus Inventory
                    </Link>
                    <Link
                      to="/supplier/profile"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/supplier/profile') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <Building2 className="h-4 w-4" />
                      Facility Profile
                    </Link>
                  </>
                )}

                {user.role === 'RECEIVER' && (
                  <>
                    <Link
                      to="/receiver/demands"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/receiver/demands') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <HeartHandshake className="h-4 w-4" />
                      Food Demands
                    </Link>
                    <Link
                      to="/receiver/profile"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/receiver/profile') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <Building2 className="h-4 w-4" />
                      Facility Profile
                    </Link>
                  </>
                )}

                {(user.role === 'COORDINATOR' || user.role === 'ADMIN') && (
                  <>
                    <Link
                      to="/coordinator/optimization"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/coordinator/optimization') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <Cpu className="h-4 w-4" />
                      Optimization Engine
                    </Link>
                    <Link
                      to="/coordinator/transactions"
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                        isActive('/coordinator/transactions') ? 'bg-primary text-white' : 'hover:bg-muted'
                      }`}
                    >
                      <Truck className="h-4 w-4" />
                      Transactions
                    </Link>
                  </>
                )}

                <Link
                  to="/assistant"
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium ${
                    isActive('/assistant') ? 'bg-primary text-white' : 'hover:bg-muted'
                  }`}
                >
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  AI Copilot
                </Link>

                <div className="pt-2 border-t border-border">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLogout}
                    className="w-full justify-center gap-2 text-destructive border-destructive/20 hover:bg-destructive/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign Out
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <a
                  href="/#how-it-works"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-muted"
                >
                  How It Works
                </a>
                <a
                  href="/#capabilities"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-3 py-2 rounded-md text-sm font-medium text-foreground hover:bg-muted"
                >
                  Platform Capabilities
                </a>
                <div className="pt-2 border-t border-border flex flex-col gap-2">
                  <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                    <Button variant="outline" size="sm" className="w-full justify-center gap-2">
                      <LogIn className="h-4 w-4" />
                      Sign In
                    </Button>
                  </Link>
                  <Link to="/register" onClick={() => setMobileMenuOpen(false)}>
                    <Button size="sm" className="w-full justify-center gap-2">
                      Get Started
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* Platform Footer */}
      <footer className="border-t border-border bg-card/70 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-white font-bold">
                  <Timer className="h-4 w-4" />
                </div>
                <span className="font-extrabold tracking-tight text-sm text-foreground">
                  FOOD HAS A DEADLINE
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed max-w-md">
                A mathematical and perishability-aware food rescue logistics platform connecting surplus food suppliers
                with community relief organizations before time runs out.
              </p>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                <span>Deterministic Perishability &bull; Google OR-Tools CP-SAT &bull; Gemini Orchestration</span>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">Quick Navigation</h4>
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                <li>
                  <a href="/#how-it-works" className="hover:text-primary transition-colors">
                    How It Works
                  </a>
                </li>
                <li>
                  <a href="/#capabilities" className="hover:text-primary transition-colors">
                    Platform Capabilities
                  </a>
                </li>
                <li>
                  <Link to="/login" className="hover:text-primary transition-colors">
                    Sign In
                  </Link>
                </li>
                <li>
                  <Link to="/register" className="hover:text-primary transition-colors">
                    Register Organization
                  </Link>
                </li>
              </ul>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">Operational Integrity</h4>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                FHD provides algorithmic scheduling, route feasibility, and optimization. All physical transfers require
                human verification and compliance with food hygiene standards.
              </p>
            </div>
          </div>

          <div className="pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
            <p>&copy; {currentYear} Food Has a Deadline (FHD). All rights reserved.</p>
            <p className="text-[11px]">
              Engineered for urgent perishability redistribution &bull; Hackathon Edition
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
