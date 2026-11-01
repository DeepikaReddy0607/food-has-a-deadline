import React from 'react'
import { Link } from 'react-router-dom'
import {
  Timer,
  Clock,
  ArrowRight,
  ShieldCheck,
  Cpu,
  MapPin,
  Sparkles,
  Building2,
  HeartHandshake,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  TrendingDown,
  Navigation,
  FileCheck,
  UserCheck,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

export const HomePage: React.FC = () => {
  return (
    <div className="space-y-20 py-4 sm:py-8">
      {/* 1. HERO SECTION */}
      <section className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-b from-card via-card to-background p-8 sm:p-12 lg:p-16 shadow-sm">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-primary/5 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 -ml-16 -mb-16 w-80 h-80 rounded-full bg-fhd-light-green/30 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-3xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary">
            <Timer className="h-4 w-4" />
            <span>Deterministic Perishability Intelligence &bull; Google OR-Tools CP-SAT</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.15]">
            Every Hour Matters. <br />
            <span className="text-primary">Every Kilogram Counts.</span>
          </h1>

          <p className="text-base sm:text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-2xl mx-auto font-normal">
            Food Has a Deadline connects food suppliers with community organizations through perishability-aware
            matching, intelligent allocation and geographically feasible redistribution.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register" className="w-full sm:w-auto">
              <Button size="lg" className="w-full sm:w-auto gap-2 text-sm font-semibold shadow-md px-6">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="#how-it-works" className="w-full sm:w-auto">
              <Button variant="outline" size="lg" className="w-full sm:w-auto gap-2 text-sm font-semibold border-border bg-card">
                Explore How It Works
              </Button>
            </a>
          </div>

          <div className="pt-6 flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground border-t border-border/60">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              <span>Perishability-Aware Prioritization</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              <span>Storage Compatibility Checks</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              <span>Human Approval in the Loop</span>
            </div>
          </div>
        </div>

        {/* 2. ILLUSTRATIVE WORKFLOW DEMONSTRATION */}
        <div className="relative mt-12 max-w-4xl mx-auto rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-border pb-4 mb-4 gap-2">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-primary" />
              <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                Illustrative Workflow
              </span>
              <span className="rounded bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground border border-border">
                Example data — not live operational records
              </span>
            </div>
            <span className="text-[11px] font-mono text-muted-foreground bg-muted/60 px-2 py-0.5 rounded">
              DECISION ENGINE: GOOGLE OR-TOOLS CP-SAT
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            {/* Step Card 1 */}
            <div className="rounded-xl border border-border bg-fhd-bg/40 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-foreground">1. Surplus Listing (Scenario)</span>
                <span className="rounded bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 text-[10px] font-bold">
                  HIGH URGENCY
                </span>
              </div>
              <p className="text-sm font-bold text-foreground">Representative Perishable Batch</p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Batch Volume:</span>
                  <span className="font-medium text-foreground">180.00 kg (Example)</span>
                </div>
                <div className="flex justify-between">
                  <span>Storage Required:</span>
                  <span className="font-medium text-foreground">Refrigerated (2–4°C)</span>
                </div>
                <div className="flex justify-between items-center text-amber-700 dark:text-amber-400 font-semibold pt-1">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Estimated Remaining Time:
                  </span>
                  <span>14.2 Hours</span>
                </div>
              </div>
            </div>

            {/* Step Card 2 */}
            <div className="rounded-xl border border-border bg-fhd-bg/40 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-foreground">2. Route Feasibility Check</span>
                <span className="rounded bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold">
                  FEASIBLE
                </span>
              </div>
              <p className="text-sm font-bold text-foreground">Representative Community Receiver</p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Straight Distance:</span>
                  <span className="font-medium text-foreground">7.4 km</span>
                </div>
                <div className="flex justify-between">
                  <span>Road Route (1.35x fallback):</span>
                  <span className="font-medium text-foreground">10.0 km (~20 mins)</span>
                </div>
                <div className="flex justify-between items-center text-primary font-semibold pt-1">
                  <span className="inline-flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3" />
                    Estimated Delivery-Time Margin:
                  </span>
                  <span>+13.8 Hours Margin</span>
                </div>
              </div>
            </div>

            {/* Step Card 3 */}
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-primary">3. Optimization Proposal</span>
                <span className="rounded bg-primary text-white px-2 py-0.5 text-[10px] font-bold">
                  PROPOSAL DRAFT
                </span>
              </div>
              <p className="text-sm font-bold text-foreground">Illustrative Proposal Flow</p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Proposed Allocation:</span>
                  <span className="font-bold text-primary">180.00 kg (Sample Match)</span>
                </div>
                <div className="flex justify-between">
                  <span>Objective Term Score:</span>
                  <span className="font-medium text-foreground">Sample Score: 96 / 100</span>
                </div>
                <div className="flex justify-between items-center text-muted-foreground pt-1 border-t border-border/80">
                  <span>Status:</span>
                  <span className="font-semibold text-amber-600">Pending Human Review</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THE PROBLEM & THE SOLUTION */}
      <section className="space-y-8">
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <span className="text-xs font-bold uppercase tracking-wider text-primary">The Perishability Challenge</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Food Redistribution is a Race Against Physics
          </h2>
          <p className="text-sm text-muted-foreground">
            Perishable food loses nutritional value and marketability rapidly. Traditional manual donation workflows take days,
            causing tons of edible food to expire before delivery.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* The Dilemma */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">The Breakdown in Conventional Rescue</h3>
                <p className="text-xs text-muted-foreground">Where manual coordination fails</p>
              </div>
            </div>

            <ul className="space-y-4 text-xs text-muted-foreground">
              <li className="flex items-start gap-3">
                <TrendingDown className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Surplus Perishable Food:</strong>
                  Fresh produce, chilled dairy, and prepared meals have narrow shelf-life windows. Without
                  perishability-aware scheduling, listings expire before pickup is arranged.
                </div>
              </li>
              <li className="flex items-start gap-3">
                <TrendingDown className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Mismatched Demands & Capacities:</strong>
                  Sending refrigerated pallets to a pantry without cold-storage ruins donations. Incompatible dietary
                  attributes or bulk limits lead to on-site rejections.
                </div>
              </li>
              <li className="flex items-start gap-3">
                <TrendingDown className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Fragmented & Unchecked Logistics:</strong>
                  Phone calls, ad-hoc spreadsheets, and subjective prioritization lead to sub-optimal distribution,
                  and uncoordinated logistics and transit delays lead to edible food expiring before arrival.
                </div>
              </li>
            </ul>
          </div>

          {/* The FHD Solution */}
          <div className="rounded-2xl border border-primary/30 bg-card p-6 sm:p-8 space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full pointer-events-none" />

            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-white">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">The FHD Algorithmic Solution</h3>
                <p className="text-xs text-muted-foreground">Mathematical, deterministic, and verifiable</p>
              </div>
            </div>

            <ul className="space-y-4 text-xs text-muted-foreground">
              <li className="flex items-start gap-3">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Perishability Urgency Intelligence:</strong>
                  Dynamic calculation of estimated remaining time based on food category decay functions, storage
                  temperature parameters, and elapsed transit windows.
                </div>
              </li>
              <li className="flex items-start gap-3">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Multi-Factor Compatibility Filtering:</strong>
                  Deterministic validation performs storage compatibility checks, matches dietary restrictions, and
                  verifies physical receiving capacity.
                </div>
              </li>
              <li className="flex items-start gap-3">
                <CheckCircle2 className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <strong className="text-foreground block">Global Constrained Optimization:</strong>
                  Google OR-Tools CP-SAT solver maximizes total rescued volume while respecting geographic road travel
                  buffers and receiver priority weights.
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 3. 5-STAGE HOW IT WORKS */}
      <section id="how-it-works" className="space-y-10 scroll-mt-24">
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <span className="text-xs font-bold uppercase tracking-wider text-primary">Operational Workflow</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            How Food Has a Deadline Works
          </h2>
          <p className="text-sm text-muted-foreground">
            A 5-stage closed-loop pipeline from surplus declaration to verified physical recipient delivery.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {/* Stage 1 */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-sm">
                1
              </div>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </div>
            <h4 className="text-sm font-bold text-foreground">Register Inventory & Demand</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Suppliers register surplus food with category, prep time, and storage constraints. Receivers specify intake
              capacity and dietary preferences.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-sm">
                2
              </div>
              <Timer className="h-4 w-4 text-amber-600" />
            </div>
            <h4 className="text-sm font-bold text-foreground">Evaluate Perishability Urgency</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Deterministic decay curves compute hours until estimated usable deadline, assigning CRITICAL, HIGH, MODERATE,
              or LOW urgency.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-sm">
                3
              </div>
              <MapPin className="h-4 w-4 text-blue-600" />
            </div>
            <h4 className="text-sm font-bold text-foreground">Identify Compatible Receivers</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Geospatial routing checks travel distance and road duration, eliminating pairs that cannot reach the
              receiver within an adequate operational transit buffer.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="rounded-2xl border border-primary/40 bg-card p-5 space-y-3 relative shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white font-bold text-sm">
                4
              </div>
              <Cpu className="h-4 w-4 text-primary" />
            </div>
            <h4 className="text-sm font-bold text-foreground">Optimize Allocation Globally</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Google OR-Tools CP-SAT solver optimizes distribution globally, maximizing salvaged kilograms before
              optimizing secondary criteria.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold text-sm">
                5
              </div>
              <FileCheck className="h-4 w-4 text-emerald-600" />
            </div>
            <h4 className="text-sm font-bold text-foreground">Approve & Track Physical Custody</h4>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Coordinators review and approve proposals. Dispatchers and drivers track pickup, in-transit custody, and
              verified delivery confirmation.
            </p>
          </div>
        </div>
      </section>

      {/* 4. 4 PLATFORM CAPABILITIES */}
      <section id="capabilities" className="space-y-10 scroll-mt-24">
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <span className="text-xs font-bold uppercase tracking-wider text-primary">Core Architecture</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Platform Capabilities
          </h2>
          <p className="text-sm text-muted-foreground">
            Four specialized engineering subsystems working synchronously to eliminate food waste.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Capability 1 */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-4 hover:border-primary/40 transition-all">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600">
                <Timer className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">1. Perishability Intelligence Engine</h3>
                <span className="text-xs font-medium text-muted-foreground">Deterministic Decay & Urgency Analysis</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Evaluates food shelf life using deterministic decay formulas by category (Produce, Dairy, Prepared, Bakery,
              Meat). Computes estimated remaining hours, classifies operational urgency into four strict tiers, and verifies
              data completeness without manual guesswork.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Category Decay Curves
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Storage Temperature Awareness
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Estimated Remaining Time
              </span>
            </div>
          </div>

          {/* Capability 2 */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-4 hover:border-primary/40 transition-all">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600">
                <Navigation className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">2. Geospatial Routing & Temporal Feasibility</h3>
                <span className="text-xs font-medium text-muted-foreground">Distance, Road Factors & Buffers</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Computes straight-line Haversine distances scaled with the documented urban road network circuity factor
              (1.35x fallback) or OSRM route calculations (distance and travel duration without requiring live traffic feeds).
              Verifies that travel time fits within estimated remaining food time with an operational transit buffer.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Haversine (1.35x Fallback) &amp; OSRM
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Temporal Feasibility Check
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Deadline Buffer Guard
              </span>
            </div>
          </div>

          {/* Capability 3 */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-4 hover:border-primary/40 transition-all">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Cpu className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">3. Google OR-Tools Constrained Allocation</h3>
                <span className="text-xs font-medium text-muted-foreground">Mathematical Google OR-Tools CP-SAT Linear Optimizer</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Formulates redistribution as a multi-commodity integer programming problem. Enforces strict capacity,
              dietary, and storage compatibility constraints while mathematically guaranteeing that maximum food volume salvage
              dominates secondary objective weights (urgency, priority, distance).
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                CP-SAT Constraint Solver
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Volume Salvage Dominance
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Strict Physical Constraints
              </span>
            </div>
          </div>

          {/* Capability 4 */}
          <div className="rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-4 hover:border-primary/40 transition-all">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">4. AI Redistribution Copilot</h3>
                <span className="text-xs font-medium text-muted-foreground">Gemini Tool Orchestration &amp; Deterministic Fallback</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Enables natural language coordination for field operators. Powered by Gemini with structured tool
              calling into deterministic backend services. Includes automatic rule-based deterministic fallback when API
              keys are unavailable, ensuring uninterrupted operation.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Gemini Tool Calling
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Deterministic Fallback Engine
              </span>
              <span className="rounded bg-muted px-2.5 py-1 text-[11px] font-medium text-foreground">
                Operator Action Summaries
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 5. ROLE-BASED VALUE PROPOSITIONS */}
      <section className="space-y-8">
        <div className="text-center space-y-2 max-w-2xl mx-auto">
          <span className="text-xs font-bold uppercase tracking-wider text-primary">Tailored for Every Stakeholder</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Built for Real-World Food Rescue Operations
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Building2 className="h-5 w-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">For Food Suppliers</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Farms, wholesale distributors, grocery chains, and commercial kitchens. Easily list surplus inventory,
              receive real-time perishability alerts, and track tax-deductible rescue receipts without logistical friction.
            </p>
            <ul className="text-xs text-muted-foreground space-y-1.5 pt-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Rapid surplus listing in under 2 minutes
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Automated remaining shelf-life tracker
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Verified physical pickup audit trail
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <HeartHandshake className="h-5 w-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">For Community Receivers</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Food pantries, homeless shelters, community kitchens, and disaster relief programs. Request exact quantities
              and dietary needs without being burdened by unusable items or surprise deliveries.
            </p>
            <ul className="text-xs text-muted-foreground space-y-1.5 pt-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Storage capacity & dietary compatibility
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Advance arrival time estimations
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Partial and recurring demand fulfillment
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <UserCheck className="h-5 w-5" />
            </div>
            <h3 className="text-base font-bold text-foreground">For Redistribution Coordinators</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Regional coordinators and dispatchers. Run global batch optimization across multiple suppliers and
              receivers, approve or adjust allocations, and supervise in-transit delivery progress.
            </p>
            <ul className="text-xs text-muted-foreground space-y-1.5 pt-2">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                One-click global OR-Tools optimization
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                Human-in-the-loop review and approval
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
                End-to-end custody and delivery tracking
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 6. CALL TO ACTION BANNER */}
      <section className="rounded-3xl border border-primary/30 bg-primary/10 p-8 sm:p-12 text-center space-y-6 relative overflow-hidden">
        <div className="max-w-2xl mx-auto space-y-3">
          <h2 className="text-3xl font-extrabold tracking-tight text-foreground">
            Move Food Before Time Runs Out
          </h2>
          <p className="text-sm text-secondary-foreground leading-relaxed">
            Join the Food Has a Deadline network today. Register your facility as a food supplier or community receiver,
            or sign in to manage live redistribution operations.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <Link to="/register" className="w-full sm:w-auto">
            <Button size="lg" className="w-full sm:w-auto gap-2 text-sm font-semibold shadow-md px-8">
              Register Organization
              <ChevronRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link to="/login" className="w-full sm:w-auto">
            <Button variant="outline" size="lg" className="w-full sm:w-auto gap-2 text-sm font-semibold bg-card border-border">
              Sign In to Portal
            </Button>
          </Link>
        </div>
      </section>
    </div>
  )
}
