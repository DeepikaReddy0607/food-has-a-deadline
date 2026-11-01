import React, { useState, useEffect } from 'react'
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Truck,
  Scale,
  Building2,
  Sparkles,
  ShieldAlert,
  SlidersHorizontal,
  Info,
  Clock,
  RefreshCw,
  Search,
  XCircle,
  Bot,
  Send,
  Loader2,
  Navigation,
  HeartHandshake,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { apiService } from '@/services/api'
import { RouteMapPreview } from '@/components/geospatial/RouteMapPreview'
import type {
  OptimizationProposalResponse,
  AllocationItemDetail,
  BatchEvaluationResponse,
  MatchingQueryResponse,
  CandidateMatch,
  RouteEstimateResult,
  ChatResponse,
} from '@/types'

export const OptimizationDashboard: React.FC = () => {
  // 1. Solver & Proposal State
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [proposal, setProposal] = useState<OptimizationProposalResponse | null>(null)

  // 2. Batch Perishability Intelligence State
  const [perishabilityBatch, setPerishabilityBatch] = useState<BatchEvaluationResponse | null>(null)
  const [perishabilityLoading, setPerishabilityLoading] = useState<boolean>(false)

  // 3. Candidate Matching & Deep-Dive State
  const [selectedListingId, setSelectedListingId] = useState<string | null>(null)
  const [candidatesData, setCandidatesData] = useState<MatchingQueryResponse | null>(null)
  const [candidatesLoading, setCandidatesLoading] = useState<boolean>(false)
  const [candidatesError, setCandidatesError] = useState<string | null>(null)
  const [candidatesFilter, setCandidatesFilter] = useState<'ALL' | 'ELIGIBLE' | 'INELIGIBLE'>('ALL')

  // 4. Geospatial Routing & Route Map State
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateMatch | null>(null)
  const [routeEstimate, setRouteEstimate] = useState<RouteEstimateResult | null>(null)
  const [routeLoading, setRouteLoading] = useState<boolean>(false)
  const [routeError, setRouteError] = useState<string | null>(null)

  // 5. Contextual AI Copilot State
  const [copilotExpanded, setCopilotExpanded] = useState<boolean>(false)
  const [copilotLoading, setCopilotLoading] = useState<boolean>(false)
  const [copilotInput, setCopilotInput] = useState<string>('')
  const [copilotMessages, setCopilotMessages] = useState<
    Array<{ role: 'user' | 'assistant'; text: string; tools?: any[]; fallback?: boolean; created_at: string }>
  >([])
  const [aiProvider, setAiProvider] = useState<string>('Google Gemini (gemini-2.5-flash)')
  const [isFallbackMode, setIsFallbackMode] = useState<boolean>(true)

  // 6. Human Approval and Rejection States
  const [approvalModalOpen, setApprovalModalOpen] = useState<boolean>(false)
  const [rejectionModalOpen, setRejectionModalOpen] = useState<boolean>(false)
  const [dispatchNotes, setDispatchNotes] = useState<string>('')
  const [scheduledPickupAt, setScheduledPickupAt] = useState<string>('')
  const [rejectionReason, setRejectionReason] = useState<string>('')
  const [actionLoading, setActionLoading] = useState<boolean>(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [approvedTxCode, setApprovedTxCode] = useState<string | null>(null)
  const [rejectionRecorded, setRejectionRecorded] = useState<string | null>(null)

  // 7. Navigation & Item Modal
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(5.0)
  const [maxDistanceKm, setMaxDistanceKm] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'allocations' | 'unfulfilled' | 'unallocated' | 'diagnostics'>('allocations')
  const [selectedItem, setSelectedItem] = useState<AllocationItemDetail | null>(null)
  const [searchFilter, setSearchFilter] = useState<string>('')

  // ---------------------------------------------------------------------------
  // Route Feasibility Estimator & Map Trigger
  // ---------------------------------------------------------------------------
  const handleInspectRoute = async (candidate: CandidateMatch) => {
    setSelectedCandidate(candidate)
    setRouteLoading(true)
    setRouteError(null)

    try {
      const res = await apiService.estimateRoute({
        surplus_listing_id: candidate.surplus_listing_id,
        receiver_id: candidate.receiver_id,
        handling_buffer_minutes: candidate.handling_buffer_minutes || 30,
      })
      setRouteEstimate(res)
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Route calculation failed.'
      setRouteError(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } finally {
      setRouteLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Candidate Matching Handler
  // ---------------------------------------------------------------------------
  const handleSelectListing = async (listingId: string) => {
    setSelectedListingId(listingId)
    setCandidatesLoading(true)
    setSelectedCandidate(null)
    setRouteEstimate(null)
    setRouteError(null)

    try {
      const res = await apiService.getListingCandidates(listingId, {
        include_ineligible: true,
        page_size: 50,
      })
      setCandidatesData(res)

      // If candidates exist, default route estimate to the top eligible candidate
      const eligible = res.candidates.find((c) => c.is_eligible) || res.candidates[0]
      if (eligible) {
        handleInspectRoute(eligible)
      }
    } catch (err: unknown) {
      console.warn('Failed to load candidate matches:', err)
    } finally {
      setCandidatesLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Load Batch Perishability on mount
  // ---------------------------------------------------------------------------
  const fetchBatchPerishability = async () => {
    setPerishabilityLoading(true)
    try {
      const data = await apiService.getBatchActivePerishability()
      setPerishabilityBatch(data)
      if (data.items.length > 0 && !selectedListingId) {
        // Automatically select the most urgent listing to populate matching
        const sorted = [...data.items].sort((a, b) => a.remaining_hours - b.remaining_hours)
        const first = sorted[0]
        if (first.listing_id) {
          handleSelectListing(first.listing_id)
        }
      }
    } catch (err: unknown) {
      console.warn('Could not load batch perishability:', err)
    } finally {
      setPerishabilityLoading(false)
    }
  }

  useEffect(() => {
    fetchBatchPerishability()
  }, [])

  // ---------------------------------------------------------------------------
  // Trigger OR-Tools Optimization Run
  // ---------------------------------------------------------------------------
  const handleRunOptimization = async () => {
    setLoading(true)
    setError(null)
    setApprovedTxCode(null)
    setRejectionRecorded(null)
    try {
      const response = await apiService.createAllocationProposal({
        timeout_seconds: timeoutSeconds,
        max_distance_km: maxDistanceKm ? parseFloat(maxDistanceKm) : undefined,
      })
      setProposal(response)
      // Refresh perishability counts
      fetchBatchPerishability()
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } }
        setError(axErr.response?.data?.detail || 'Failed to run optimization.')
      } else {
        setError('Network error running allocation optimization.')
      }
    } finally {
      setLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // AI Copilot Integration
  // ---------------------------------------------------------------------------
  const handleSendCopilotQuery = async (queryText: string) => {
    const text = queryText.trim()
    if (!text || copilotLoading) return

    setCopilotInput('')
    setCopilotLoading(true)
    setCopilotExpanded(true)

    const userEntry = {
      role: 'user' as const,
      text,
      created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setCopilotMessages((prev) => [...prev, userEntry])

    try {
      const resp: ChatResponse = await apiService.sendChatMessage({ message: text })
      setAiProvider(resp.ai_provider)
      setIsFallbackMode(resp.fallback_mode)

      const assistantEntry = {
        role: 'assistant' as const,
        text: resp.response_text,
        tools: resp.tool_calls,
        fallback: resp.fallback_mode,
        created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setCopilotMessages((prev) => [...prev, assistantEntry])
    } catch {
      const assistantError = {
        role: 'assistant' as const,
        text: 'Failed to communicate with AI Copilot. Deterministic engine active.',
        created_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setCopilotMessages((prev) => [...prev, assistantError])
    } finally {
      setCopilotLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Human Approval & Rejection Handlers
  // ---------------------------------------------------------------------------
  const handleApproveProposal = async () => {
    if (!proposal || !proposal.proposal_id) return
    setActionLoading(true)
    setActionError(null)
    try {
      const resp = await apiService.approveProposal(proposal.proposal_id, {
        dispatch_notes: dispatchNotes.trim() ? dispatchNotes.trim() : undefined,
        scheduled_pickup_at: scheduledPickupAt ? new Date(scheduledPickupAt).toISOString() : undefined,
      })
      setProposal({ ...proposal, status: 'APPROVED' })
      const txCode = (resp as any).tracking_code || (resp as any).transaction?.tracking_code
      if (txCode) {
        setApprovedTxCode(txCode)
      }
      setApprovalModalOpen(false)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } }
        setActionError(axErr.response?.data?.detail || 'Failed to approve proposal.')
      } else {
        setActionError('Network error approving allocation proposal.')
      }
    } finally {
      setActionLoading(false)
    }
  }

  const handleRejectProposal = async () => {
    if (!proposal || !proposal.proposal_id) return
    if (!rejectionReason.trim() || rejectionReason.trim().length < 5) {
      setActionError('A valid operational rationale of at least 5 characters is required.')
      return
    }
    setActionLoading(true)
    setActionError(null)
    try {
      const resp = await apiService.rejectProposal(proposal.proposal_id, {
        reason: rejectionReason.trim(),
      })
      setProposal({ ...proposal, status: resp.status })
      setRejectionRecorded(resp.rejection_reason || rejectionReason.trim())
      setRejectionModalOpen(false)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } }
        setActionError(axErr.response?.data?.detail || 'Failed to reject proposal.')
      } else {
        setActionError('Network error rejecting allocation proposal.')
      }
    } finally {
      setActionLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Visual Badge Helpers
  // ---------------------------------------------------------------------------
  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider animate-pulse">
            <Clock className="h-3 w-3" />
            Critical (&lt;6h)
          </span>
        )
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            High (&lt;24h)
          </span>
        )
      case 'MODERATE':
        return (
          <span className="inline-flex items-center gap-1 rounded bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            Moderate (24-72h)
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            Low (&gt;72h)
          </span>
        )
    }
  }

  const getReasonBadge = (reasonCode: string) => {
    switch (reasonCode) {
      case 'NO_COMPATIBLE_SUPPLY':
      case 'NO_COMPATIBLE_DEMAND':
        return (
          <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground border border-border">
            No Compatible Pair
          </span>
        )
      case 'COLD_CHAIN_MISMATCH':
        return (
          <span className="rounded bg-blue-500/15 px-2 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 border border-blue-500/20">
            Cold Chain Deficit
          </span>
        )
      case 'TRANSIT_INFEASIBLE':
        return (
          <span className="rounded bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Transit Infeasible
          </span>
        )
      case 'SUPPLY_ALLOCATED_TO_HIGHER_PRIORITY':
        return (
          <span className="rounded bg-purple-500/15 px-2 py-0.5 text-xs font-medium text-purple-600 dark:text-purple-400 border border-purple-500/20">
            Priority Preempted
          </span>
        )
      case 'INSUFFICIENT_SUPPLY':
        return (
          <span className="rounded bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Supply Depleted
          </span>
        )
      default:
        return (
          <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground border border-border">
            {reasonCode}
          </span>
        )
    }
  }

  // Filter line items for search
  const filteredItems = proposal
    ? proposal.items.filter((it) => {
        if (!searchFilter.trim()) return true
        const q = searchFilter.toLowerCase()
        return (
          it.item_name.toLowerCase().includes(q) ||
          it.food_category.toLowerCase().includes(q) ||
          it.supplier_name.toLowerCase().includes(q) ||
          it.receiver_name.toLowerCase().includes(q)
        )
      })
    : []

  // Filter candidates
  const filteredCandidates = candidatesData
    ? candidatesData.candidates.filter((c) => {
        if (candidatesFilter === 'ELIGIBLE') return c.is_eligible
        if (candidatesFilter === 'INELIGIBLE') return !c.is_eligible
        return true
      })
    : []

  const urgentCount =
    (perishabilityBatch?.counts_by_urgency?.CRITICAL || 0) +
    (perishabilityBatch?.counts_by_urgency?.HIGH || 0)

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------------------------
          TOP HEADER & OPERATIONAL ACTION BAR
      --------------------------------------------------------------------- */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-0.5 text-[11px] font-bold text-primary border border-primary/20">
              <Cpu className="h-3 w-3" />
              Google OR-Tools CP-SAT &bull; Multi-Commodity Constrained Allocation
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
            Intelligent Allocation Decision Center
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Deterministic supply-demand matching, perishability decay intelligence, and explainable decision support.
          </p>
        </div>

        {/* Action Controls & Solvers Options */}
        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            onClick={() => handleSendCopilotQuery('Explain the current allocation proposal and its trade-offs.')}
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs font-semibold border-primary/30 text-primary hover:bg-primary/10"
          >
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            Ask Copilot
          </Button>

          <Button
            onClick={fetchBatchPerishability}
            disabled={perishabilityLoading}
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${perishabilityLoading ? 'animate-spin' : ''}`} />
            Refresh Data
          </Button>

          <Button
            onClick={handleRunOptimization}
            disabled={loading}
            size="sm"
            className="gap-2 font-bold shadow-sm bg-primary hover:bg-fhd-primary-hover text-white"
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Solving MILP Network...
              </>
            ) : (
              <>
                <Cpu className="h-4 w-4" />
                Run OR-Tools Optimization
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ---------------------------------------------------------------------
          SECTION A: SUPPLY AND DEMAND OVERVIEW (EXECUTIVE KPIS)
      --------------------------------------------------------------------- */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        {/* KPI 1: Total Supply Considered */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold mb-1">
            <span>Available Supply</span>
            <Building2 className="h-4 w-4 text-primary" />
          </div>
          <div className="text-2xl font-black text-foreground font-mono">
            {proposal
              ? (proposal.total_allocated_kg + proposal.total_unallocated_kg).toFixed(1)
              : perishabilityBatch
              ? `${perishabilityBatch.total_evaluated} Batches`
              : '—'}
            {proposal && <span className="text-xs font-normal text-muted-foreground ml-1">kg</span>}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {proposal ? `Across ${proposal.diagnostics.num_surplus_considered} facilities` : 'Active surplus in network'}
          </div>
        </div>

        {/* KPI 2: Total Demand Considered */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold mb-1">
            <span>Outstanding Demand</span>
            <HeartHandshake className="h-4 w-4 text-blue-500" />
          </div>
          <div className="text-2xl font-black text-foreground font-mono">
            {proposal
              ? (proposal.total_allocated_kg + proposal.total_unmet_demand_kg).toFixed(1)
              : 'Active'}
            {proposal && <span className="text-xs font-normal text-muted-foreground ml-1">kg</span>}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {proposal ? `Across ${proposal.diagnostics.num_demands_considered} requests` : 'Registered intake requests'}
          </div>
        </div>

        {/* KPI 3: Proposed Volume Salvage */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold mb-1">
            <span>Proposed Salvage</span>
            <Scale className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
            {proposal ? proposal.total_allocated_kg.toFixed(1) : '0.0'}
            <span className="text-xs font-normal text-muted-foreground ml-1">kg</span>
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {proposal && proposal.total_allocated_kg + proposal.total_unallocated_kg > 0
              ? `${Math.round(
                  (proposal.total_allocated_kg /
                    (proposal.total_allocated_kg + proposal.total_unallocated_kg)) *
                    100
                )}% rescued volume`
              : 'Dominant MILP objective'}
          </div>
        </div>

        {/* KPI 4: Urgent Perishable Batches */}
        <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold mb-1">
            <span>Urgent Batches</span>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl font-black text-amber-600 dark:text-amber-400 font-mono">
            {urgentCount}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {perishabilityBatch?.counts_by_urgency?.CRITICAL || 0} Critical &bull;{' '}
            {perishabilityBatch?.counts_by_urgency?.HIGH || 0} High Urgency
          </div>
        </div>

        {/* KPI 5: Evaluated Pairs / Variables */}
        <div className="col-span-2 sm:col-span-1 rounded-xl border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-semibold mb-1">
            <span>Candidate Pairs</span>
            <Cpu className="h-4 w-4 text-purple-500" />
          </div>
          <div className="text-2xl font-black text-foreground font-mono">
            {proposal ? proposal.diagnostics.num_candidate_pairs : 'Ready'}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {proposal
              ? `${proposal.diagnostics.num_variables} decision vars`
              : 'Formulated on demand'}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------------
          SECTIONS B, C, D: INTERACTIVE INTELLIGENCE WORKSPACE
          (Perishability Explorer + Receiver Compatibility + Route Map)
      --------------------------------------------------------------------- */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Perishability Intelligence & Inventory Explorer (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-600" />
              <h2 className="text-sm font-bold text-foreground">Active Perishable Supply</h2>
            </div>
            <span className="text-[11px] font-mono text-muted-foreground">
              {perishabilityBatch?.total_evaluated || 0} Batches
            </span>
          </div>

          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Select an active batch to inspect compatible community receivers and geospatial route feasibility.
          </p>

          {/* List of active perishable surplus */}
          <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
            {perishabilityLoading ? (
              <div className="py-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Evaluating decay curves...
              </div>
            ) : !perishabilityBatch || perishabilityBatch.items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                No active perishable batches discovered.
              </div>
            ) : (
              perishabilityBatch.items.map((item, idx) => {
                const isSelected = item.listing_id === selectedListingId
                return (
                  <div
                    key={item.listing_id || idx}
                    onClick={() => item.listing_id && handleSelectListing(item.listing_id)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/10 ring-1 ring-primary shadow-xs'
                        : 'border-border bg-background hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="font-bold text-foreground truncate">
                        Batch #{item.listing_id ? item.listing_id.slice(0, 8) : idx + 1}
                      </span>
                      {getUrgencyBadge(item.urgency)}
                    </div>

                    <div className="space-y-1 text-muted-foreground text-[11px]">
                      <div className="flex justify-between">
                        <span>Storage:</span>
                        <span className="font-medium text-foreground">{item.storage_condition}</span>
                      </div>
                      <div className="flex justify-between items-center font-semibold text-primary">
                        <span>Remaining Time:</span>
                        <span>{item.remaining_hours.toFixed(1)} Hours</span>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          <div className="pt-2 border-t border-border/80 text-[10px] text-muted-foreground leading-tight">
            <em>Disclaimer:</em> Operational urgency estimates calculated deterministically from supplier timestamps. Does not certify food safety or physical condition.
          </div>
        </div>

        {/* Right Column: Compatibility Analysis & Geospatial Route Feasibility (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Section C: Receiver Compatibility Analysis */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <HeartHandshake className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-bold text-foreground">
                  Receiver Compatibility Analysis
                </h3>
                {candidatesData && (
                  <span className="text-xs font-mono text-muted-foreground">
                    ({candidatesData.source_name || 'Selected Batch'})
                  </span>
                )}
              </div>

              {/* Filter Pills */}
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={() => setCandidatesFilter('ALL')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-colors ${
                    candidatesFilter === 'ALL'
                      ? 'bg-primary text-white'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  }`}
                >
                  All ({candidatesData?.total_candidates || 0})
                </button>
                <button
                  type="button"
                  onClick={() => setCandidatesFilter('ELIGIBLE')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-colors ${
                    candidatesFilter === 'ELIGIBLE'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Eligible ({candidatesData?.eligible_count || 0})
                </button>
                <button
                  type="button"
                  onClick={() => setCandidatesFilter('INELIGIBLE')}
                  className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-colors ${
                    candidatesFilter === 'INELIGIBLE'
                      ? 'bg-red-600 text-white'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Ineligible ({candidatesData?.ineligible_count || 0})
                </button>
              </div>
            </div>

            {/* Candidates Content */}
            {candidatesLoading ? (
              <div className="py-12 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Evaluating multi-factor constraints (category, storage compatibility, road buffers)...
              </div>
            ) : !candidatesData || filteredCandidates.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted-foreground space-y-1">
                <p className="font-semibold text-foreground">No candidate matches found in this view.</p>
                <p>Select another batch from the supply list or adjust candidate filter.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto pr-1">
                {filteredCandidates.map((candidate) => {
                  const isSelected = selectedCandidate?.candidate_id === candidate.candidate_id
                  return (
                    <div
                      key={candidate.candidate_id}
                      className={`p-3.5 rounded-xl border text-xs transition-all space-y-2 ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-1 ring-primary'
                          : candidate.is_eligible
                          ? 'border-border bg-background hover:border-primary/40'
                          : 'border-red-200 bg-red-50/30 dark:bg-red-950/20'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-bold text-foreground text-xs sm:text-sm">
                            {candidate.receiver_name}
                          </div>
                          <span className="text-[11px] text-muted-foreground">
                            Priority {candidate.receiver_priority} &bull; {candidate.receiver_category || 'Receiver'}
                          </span>
                        </div>
                        {candidate.is_eligible ? (
                          <span className="rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 px-2 py-0.5 text-[10px] font-bold">
                            ELIGIBLE ({candidate.score.toFixed(0)}/100)
                          </span>
                        ) : (
                          <span className="rounded bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300 px-2 py-0.5 text-[10px] font-bold">
                            INELIGIBLE
                          </span>
                        )}
                      </div>

                      {/* Compatibility Checks */}
                      <div className="grid grid-cols-2 gap-2 text-[11px] text-muted-foreground pt-1 border-t border-border/60">
                        <div>
                          <span>Storage:</span>{' '}
                          <strong className={candidate.storage_compatibility.is_compatible ? 'text-primary' : 'text-destructive'}>
                            {candidate.storage_compatibility.match_level}
                          </strong>
                        </div>
                        <div>
                          <span>Road Dist:</span>{' '}
                          <strong className="text-foreground">{candidate.road_distance_km.toFixed(1)} km</strong>
                        </div>
                      </div>

                      {/* Actual Rejection Reasons for Ineligible */}
                      {!candidate.is_eligible && candidate.rejection_reasons.length > 0 && (
                        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-[11px] text-destructive space-y-0.5">
                          <strong className="block text-[10px] uppercase font-bold">Rejection Reasons:</strong>
                          {candidate.rejection_reasons.map((r, i) => (
                            <div key={i} className="flex items-center gap-1">
                              &bull; <span>{r}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => handleInspectRoute(candidate)}
                        className="w-full justify-center gap-1.5 text-xs h-7 mt-1 border-border"
                      >
                        <Navigation className="h-3 w-3 text-primary" />
                        Inspect Route &amp; Map
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Section D: Geospatial Feasibility & Route Map */}
          {selectedCandidate && (
            <div className="rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Navigation className="h-4 w-4 text-blue-600" />
                  <h3 className="text-sm font-bold text-foreground">
                    Geospatial Route Feasibility: {selectedCandidate.supplier_name} &rarr; {selectedCandidate.receiver_name}
                  </h3>
                </div>
                {routeEstimate && (
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                      routeEstimate.feasibility === 'FEASIBLE'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                    }`}
                  >
                    {routeEstimate.feasibility}
                  </span>
                )}
              </div>

              {routeLoading ? (
                <div className="py-12 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Calculating road coordinates and temporal margin...
                </div>
              ) : routeError ? (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{routeError}</span>
                </div>
              ) : routeEstimate ? (
                <div className="space-y-4">
                  <RouteMapPreview estimate={routeEstimate} />
                </div>
              ) : null}

              <div className="text-[10px] text-muted-foreground">
                <em>Note:</em> Route estimates calculate driving distance and duration via OSRM or the documented 1.35x circuity fallback without live traffic telemetry.
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ---------------------------------------------------------------------
          SECTION E & F: OPTIMIZATION DECISION & EXPLAINABILITY PANEL
      --------------------------------------------------------------------- */}
      <section className="space-y-6">
        {/* Solver Configuration Drawer */}
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
            <div className="flex items-center gap-2 font-bold text-sm text-foreground">
              <SlidersHorizontal className="h-4 w-4 text-primary" />
              <span>Google OR-Tools CP-SAT Solver Parameters</span>
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              Deterministic Linear Integer Solver
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block text-muted-foreground font-semibold mb-1">
                CP-SAT Timeout Limit (Seconds)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.5"
                  max="30"
                  step="0.5"
                  value={timeoutSeconds}
                  onChange={(e) => setTimeoutSeconds(parseFloat(e.target.value))}
                  className="w-full accent-primary"
                />
                <span className="font-mono font-bold w-12 text-right">{timeoutSeconds.toFixed(1)}s</span>
              </div>
            </div>

            <div>
              <label className="block text-muted-foreground font-semibold mb-1">
                Max Dispatch Radius (km, Optional)
              </label>
              <input
                type="number"
                placeholder="e.g. 50"
                value={maxDistanceKm}
                onChange={(e) => setMaxDistanceKm(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>

            <div className="sm:col-span-2 lg:col-span-1 flex items-center">
              <div className="flex items-start gap-2 text-[11px] text-muted-foreground bg-muted/40 p-2.5 rounded-lg border border-border">
                <Info className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <span>
                  Hundredths-of-a-kilogram (0.01 kg) integer resolution eliminates floating-point drift. Dominant base salvage reward prioritizes maximum feasible food volume rescue.
                </span>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <div>
              <div className="font-semibold">Optimization Run Error</div>
              <div className="text-xs mt-0.5">{error}</div>
            </div>
          </div>
        )}

        {/* Proposal Decision View */}
        {proposal ? (
          <div className="space-y-6">
            {/* SECTION H: HUMAN APPROVAL STATUS BANNER */}
            {proposal.status === 'APPROVED' ? (
              <div className="rounded-2xl border-2 border-emerald-500/30 bg-emerald-500/10 p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold tracking-wide text-xs sm:text-sm uppercase text-emerald-700 dark:text-emerald-400 bg-emerald-500/20 px-2.5 py-0.5 rounded border border-emerald-500/30">
                          PROPOSAL APPROVED &bull; TRANSACTION COMMITTED
                        </span>
                        {approvedTxCode && (
                          <span className="rounded bg-background px-2.5 py-0.5 text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                            {approvedTxCode}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Surplus quantities have been atomically deducted and locked. A binding redistribution transaction is active.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link to="/coordinator/transactions">
                      <Button size="sm" className="gap-2 font-semibold bg-emerald-600 hover:bg-emerald-700 text-white">
                        <Truck className="h-4 w-4" />
                        View Dispatch Tracker
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            ) : proposal.status === 'REJECTED' ? (
              <div className="rounded-2xl border-2 border-red-500/30 bg-red-500/10 p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-red-600 dark:text-red-400">
                    <XCircle className="h-6 w-6" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold tracking-wide text-xs sm:text-sm uppercase text-red-700 dark:text-red-400 bg-red-500/20 px-2.5 py-0.5 rounded border border-red-500/30">
                        PROPOSAL REJECTED BY COORDINATOR
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      This allocation was discarded without deducting supplier inventories.
                      {rejectionRecorded && (
                        <span className="block font-medium text-foreground mt-0.5">
                          Operational Rationale: &ldquo;{rejectionRecorded}&rdquo;
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border-2 border-amber-500/30 bg-amber-500/10 p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400">
                      <ShieldAlert className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold tracking-wide text-xs sm:text-sm uppercase text-amber-700 dark:text-amber-400 bg-amber-500/20 px-2.5 py-0.5 rounded border border-amber-500/30">
                          DRAFT PROPOSAL &bull; PENDING HUMAN APPROVAL
                        </span>
                        <span className="rounded bg-background px-2 py-0.5 text-xs font-mono font-bold text-muted-foreground border border-border">
                          ID: {proposal.proposal_id ? proposal.proposal_id.slice(0, 8) : 'DRY-RUN'}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Quantities have NOT been deducted yet. Review proposed flows and approve to commit the redistribution transaction.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0">
                    {proposal.proposal_id && (
                      <>
                        <Button
                          size="sm"
                          onClick={() => {
                            setActionError(null)
                            setApprovalModalOpen(true)
                          }}
                          className="gap-1.5 font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Approve Allocation
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setActionError(null)
                            setRejectionReason('')
                            setRejectionModalOpen(true)
                          }}
                          className="gap-1.5 font-semibold border-destructive/40 text-destructive hover:bg-destructive/10"
                        >
                          <XCircle className="h-4 w-4" />
                          Reject
                        </Button>
                      </>
                    )}
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
                      Solver: {proposal.solver_status} ({proposal.solve_time_ms.toFixed(1)} ms)
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* SECTION F: EXPLAINABILITY PANEL */}
            <div className="rounded-2xl border border-primary/30 bg-card p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary font-bold">
                    <Sparkles className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-base font-extrabold text-foreground">
                      Why did FHD recommend this allocation?
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Objective hierarchy and mathematical justification generated from the CP-SAT solver.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                      proposal.solver_status === 'OPTIMAL'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                    }`}
                  >
                    {proposal.solver_status}
                  </span>
                </div>
              </div>

              {/* 4 Pillars Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
                <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-1">
                  <span className="font-bold text-foreground block">1. Volume Salvage Dominance</span>
                  <p className="text-[11px] text-muted-foreground leading-tight">
                    The model applies a dominant base salvage reward guaranteeing that maximizing total rescued kilograms strictly dominates all secondary preferences.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-1">
                  <span className="font-bold text-foreground block">2. Urgency Prioritization</span>
                  <p className="text-[11px] text-muted-foreground leading-tight">
                    Prioritizes batches with shorter estimated remaining shelf-life, scheduling them before time runs out.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-1">
                  <span className="font-bold text-foreground block">3. Strict Compatibility Guards</span>
                  <p className="text-[11px] text-muted-foreground leading-tight">
                    Enforces storage compatibility checks, adheres to dietary constraints, and ensures estimated delivery time fits within remaining shelf-life.
                  </p>
                </div>
                <div className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-1">
                  <span className="font-bold text-foreground block">4. Receiver Priority &amp; Proximity</span>
                  <p className="text-[11px] text-muted-foreground leading-tight">
                    Channels scarce surplus to higher-priority community kitchens and shelters while penalizing excess road transit distance.
                  </p>
                </div>
              </div>

              {/* Backend Generated Justification */}
              {proposal.ai_justification && (
                <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 text-xs text-foreground leading-relaxed">
                  <strong className="block text-primary font-bold mb-1">Solver Explanation:</strong>
                  {proposal.ai_justification}
                </div>
              )}
            </div>

            {/* SECTION E: PROPOSAL DETAILED TABS (Allocations, Diagnostics) */}
            <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
              {/* Tab Navigation */}
              <div className="flex border-b border-border bg-muted/30 px-4 pt-2 gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setActiveTab('allocations')}
                  className={`px-4 py-2.5 font-bold border-b-2 transition-colors ${
                    activeTab === 'allocations'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Allocated Flows ({proposal.items.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('unfulfilled')}
                  className={`px-4 py-2.5 font-bold border-b-2 transition-colors ${
                    activeTab === 'unfulfilled'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Unfulfilled Demands ({proposal.unfulfilled_demands.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('unallocated')}
                  className={`px-4 py-2.5 font-bold border-b-2 transition-colors ${
                    activeTab === 'unallocated'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Unallocated Surplus ({proposal.unallocated_surplus.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('diagnostics')}
                  className={`px-4 py-2.5 font-bold border-b-2 transition-colors ${
                    activeTab === 'diagnostics'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Solver Diagnostics
                </button>
              </div>

              {/* Tab 1: Allocated Flows Table */}
              {activeTab === 'allocations' && (
                <div className="p-4 space-y-3">
                  <div className="flex items-center justify-between gap-3 pb-2">
                    <div className="relative flex-1 max-w-sm">
                      <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <input
                        type="text"
                        placeholder="Filter allocations by item, category, or facility..."
                        value={searchFilter}
                        onChange={(e) => setSearchFilter(e.target.value)}
                        className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">
                      Showing {filteredItems.length} of {proposal.items.length} flows
                    </span>
                  </div>

                  {filteredItems.length === 0 ? (
                    <div className="py-8 text-center text-xs text-muted-foreground">
                      No matching allocation flows found.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] tracking-wider font-semibold border-b border-border">
                          <tr>
                            <th className="py-2.5 px-3">Food Item</th>
                            <th className="py-2.5 px-3">Supplier Origin</th>
                            <th className="py-2.5 px-3">Receiver Destination</th>
                            <th className="py-2.5 px-3 text-right">Allocated (kg)</th>
                            <th className="py-2.5 px-3">Distance &amp; Time</th>
                            <th className="py-2.5 px-3">Urgency</th>
                            <th className="py-2.5 px-3">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {filteredItems.map((item, idx) => (
                            <tr key={item.item_id || idx} className="hover:bg-muted/20 transition-colors">
                              <td className="py-2.5 px-3">
                                <span className="font-bold text-foreground block">{item.item_name}</span>
                                <span className="text-[10px] text-muted-foreground">{item.food_category}</span>
                              </td>
                              <td className="py-2.5 px-3 text-foreground font-medium">{item.supplier_name}</td>
                              <td className="py-2.5 px-3 text-foreground font-medium">{item.receiver_name}</td>
                              <td className="py-2.5 px-3 text-right font-mono font-bold text-primary">
                                {item.allocated_quantity_kg.toFixed(2)} kg
                              </td>
                              <td className="py-2.5 px-3 text-muted-foreground">
                                {item.estimated_distance_km.toFixed(1)} km (~{item.estimated_transit_minutes}m)
                              </td>
                              <td className="py-2.5 px-3">{getUrgencyBadge(item.urgency_at_allocation)}</td>
                              <td className="py-2.5 px-3">
                                <button
                                  type="button"
                                  onClick={() => setSelectedItem(item)}
                                  className="text-[11px] font-semibold text-primary hover:underline"
                                >
                                  Details
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Unfulfilled Demands */}
              {activeTab === 'unfulfilled' && (
                <div className="p-4 space-y-3">
                  {proposal.unfulfilled_demands.length === 0 ? (
                    <div className="py-8 text-center text-xs text-muted-foreground">
                      All registered receiver demands were completely fulfilled by this proposal!
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {proposal.unfulfilled_demands.map((unf, idx) => (
                        <div key={idx} className="p-3 rounded-xl border border-border bg-background flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-foreground">{unf.receiver_name}</span>
                              <span className="text-muted-foreground">&bull; {unf.food_category}</span>
                            </div>
                            <p className="text-[11px] text-muted-foreground mt-0.5">
                              {unf.diagnostic_explanation}
                            </p>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            {getReasonBadge(unf.reason_code)}
                            <div className="text-right font-mono">
                              <span className="text-destructive font-bold">-{unf.unfulfilled_quantity_kg.toFixed(1)} kg</span>
                              <span className="text-[10px] text-muted-foreground block">
                                of {unf.requested_quantity_kg.toFixed(1)} kg
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Unallocated Surplus */}
              {activeTab === 'unallocated' && (
                <div className="p-4 space-y-3">
                  {proposal.unallocated_surplus.length === 0 ? (
                    <div className="py-8 text-center text-xs text-muted-foreground">
                      100% of available surplus inventory was allocated! Zero remaining inventory.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {proposal.unallocated_surplus.map((una, idx) => (
                        <div key={idx} className="p-3 rounded-xl border border-border bg-background flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-foreground">{una.item_name}</span>
                              <span className="text-muted-foreground">&bull; {una.supplier_name}</span>
                            </div>
                            <p className="text-[11px] text-muted-foreground mt-0.5">
                              {una.diagnostic_explanation}
                            </p>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            {getReasonBadge(una.reason_code)}
                            <div className="text-right font-mono">
                              <span className="text-amber-600 font-bold">{una.unallocated_quantity_kg.toFixed(1)} kg</span>
                              <span className="text-[10px] text-muted-foreground block">
                                of {una.available_quantity_kg.toFixed(1)} kg
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 4: Diagnostics */}
              {activeTab === 'diagnostics' && (
                <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                  <div className="p-3 rounded-xl border border-border bg-background">
                    <span className="text-muted-foreground block text-[10px] uppercase">Solver Name</span>
                    <strong className="text-foreground">{proposal.diagnostics.solver_name}</strong>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-background">
                    <span className="text-muted-foreground block text-[10px] uppercase">Solve Time</span>
                    <strong className="text-foreground">{proposal.diagnostics.solve_time_ms.toFixed(2)} ms</strong>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-background">
                    <span className="text-muted-foreground block text-[10px] uppercase">Variables</span>
                    <strong className="text-foreground">{proposal.diagnostics.num_variables}</strong>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-background">
                    <span className="text-muted-foreground block text-[10px] uppercase">Constraints</span>
                    <strong className="text-foreground">{proposal.diagnostics.num_constraints}</strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Empty Proposal State */
          <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center space-y-4">
            <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Cpu className="h-6 w-6" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h3 className="font-bold text-base text-foreground">Awaiting Optimization Run</h3>
              <p className="text-xs text-muted-foreground">
                Click &ldquo;Run OR-Tools Optimization&rdquo; to formulate and solve the multi-commodity capacitated redistribution problem across all active supplier batches and receiver demands.
              </p>
            </div>
            <Button onClick={handleRunOptimization} disabled={loading} size="sm" className="gap-2 font-semibold">
              <Sparkles className="h-4 w-4" />
              Trigger Optimization Run
            </Button>
          </div>
        )}
      </section>

      {/* ---------------------------------------------------------------------
          SECTION G: CONTEXTUAL AI COPILOT INTEGRATION
      --------------------------------------------------------------------- */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <div>
              <h3 className="text-sm font-bold text-foreground">
                AI Redistribution Copilot
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Contextual decision support backed by deterministic tools.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isFallbackMode ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-600 border border-amber-500/20">
                <AlertTriangle className="h-3 w-3" />
                Deterministic Fallback Active
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                <Cpu className="h-3 w-3" />
                {aiProvider}
              </span>
            )}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setCopilotExpanded(!copilotExpanded)}
              className="text-xs h-7 px-2"
            >
              {copilotExpanded ? 'Collapse' : 'Expand'}
            </Button>
          </div>
        </div>

        {/* Quick Contextual Action Prompts */}
        <div className="flex flex-wrap gap-2 text-xs">
          <button
            type="button"
            onClick={() => handleSendCopilotQuery('Explain the trade-offs and priorities of this allocation proposal.')}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors text-left"
          >
            💬 Explain this proposal
          </button>
          <button
            type="button"
            onClick={() => handleSendCopilotQuery('Why were these specific receivers selected over other candidates?')}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors text-left"
          >
            🔍 Why were these receivers selected?
          </button>
          <button
            type="button"
            onClick={() => handleSendCopilotQuery('Which surplus listings are most urgent in the network right now?')}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors text-left"
          >
            ⏱️ Which listings are most urgent?
          </button>
          <button
            type="button"
            onClick={() => handleSendCopilotQuery('Which receiver demands remain unfulfilled and why?')}
            className="rounded-lg border border-border bg-background px-3 py-1.5 text-[11px] font-medium hover:border-primary hover:text-primary transition-colors text-left"
          >
            ❓ Which demands remain unfulfilled?
          </button>
        </div>

        {/* Copilot Chat Body (if expanded or has messages) */}
        {(copilotExpanded || copilotMessages.length > 0) && (
          <div className="space-y-3 pt-2">
            <div className="max-h-60 overflow-y-auto space-y-2.5 p-3 rounded-xl bg-background border border-border text-xs">
              {copilotMessages.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">
                  Ask any question about current surplus, receiver compatibility, or allocation trade-offs.
                </div>
              ) : (
                copilotMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-xl px-3.5 py-2 leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-primary text-white font-medium'
                          : 'bg-muted/60 text-foreground border border-border'
                      }`}
                    >
                      {msg.text}
                      {msg.tools && msg.tools.length > 0 && (
                        <div className="mt-2 pt-1 border-t border-border/40 text-[10px] text-muted-foreground space-y-0.5">
                          <span className="font-semibold block text-primary">Executed Tools:</span>
                          {msg.tools.map((t: any, idx: number) => (
                            <span key={idx} className="inline-block bg-card px-1.5 py-0.5 rounded mr-1 font-mono">
                              {t.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="text-[9px] text-muted-foreground mt-0.5 px-1">{msg.created_at}</span>
                  </div>
                ))
              )}
              {copilotLoading && (
                <div className="flex items-center gap-2 text-muted-foreground text-xs py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Reasoning with deterministic tools...
                </div>
              )}
            </div>

            {/* Input Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendCopilotQuery(copilotInput)
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask AI Copilot about allocations, perishability, or route feasibility..."
                value={copilotInput}
                onChange={(e) => setCopilotInput(e.target.value)}
                className="flex-1 rounded-lg border border-input bg-background px-3.5 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <Button type="submit" disabled={copilotLoading || !copilotInput.trim()} size="sm" className="gap-1.5 text-xs">
                <Send className="h-3.5 w-3.5" />
                Ask
              </Button>
            </form>
          </div>
        )}
      </section>

      {/* ---------------------------------------------------------------------
          MODALS: APPROVAL & REJECTION CONFIRMATIONS
      --------------------------------------------------------------------- */}
      {/* Approval Confirmation Modal */}
      {approvalModalOpen && proposal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-base text-foreground">
                    Approve Allocation Proposal
                  </h3>
                  <p className="text-xs font-mono text-muted-foreground">
                    ID: {proposal.proposal_id}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setApprovalModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {actionError && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div className="rounded-lg border border-border bg-muted/30 p-3.5 space-y-2">
                <div className="flex justify-between font-medium">
                  <span className="text-muted-foreground">Total Rescued Volume:</span>
                  <span className="font-bold text-foreground font-mono">{proposal.total_allocated_kg.toFixed(2)} kg</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span className="text-muted-foreground">Redistribution Flows:</span>
                  <span className="font-bold text-foreground">{proposal.items.length} transfers</span>
                </div>
                <div className="flex justify-between font-medium">
                  <span className="text-muted-foreground">Solver Verification:</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">{proposal.solver_status}</span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-muted-foreground block">
                  Scheduled Pickup Window (Optional)
                </label>
                <input
                  type="datetime-local"
                  value={scheduledPickupAt}
                  onChange={(e) => setScheduledPickupAt(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-muted-foreground block">
                  Coordinator Dispatch Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  value={dispatchNotes}
                  onChange={(e) => setDispatchNotes(e.target.value)}
                  placeholder="e.g. Approved for immediate cold-van dispatch. Driver contact verified."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setApprovalModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleApproveProposal}
                disabled={actionLoading}
                className="gap-2 font-bold bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                {actionLoading ? 'Committing...' : 'Confirm & Commit Allocation'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Confirmation Modal */}
      {rejectionModalOpen && proposal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500/10 text-red-600 dark:text-red-400">
                  <XCircle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-base text-foreground">
                    Reject Allocation Proposal
                  </h3>
                  <p className="text-xs font-mono text-muted-foreground">
                    ID: {proposal.proposal_id}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setRejectionModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-lg leading-none"
              >
                &times;
              </button>
            </div>

            {actionError && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="space-y-3 text-xs">
              <p className="text-muted-foreground">
                Rejecting this proposal leaves supplier inventory and receiver demands unchanged. A mandatory justification must be recorded for audit logging.
              </p>

              <div className="space-y-1">
                <label className="font-semibold text-muted-foreground block">
                  Operational Rejection Rationale <span className="text-destructive">*</span>
                </label>
                <textarea
                  rows={3}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Unforeseen weather event has closed mountain route; re-running with radius filter."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setRejectionModalOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleRejectProposal}
                disabled={actionLoading || !rejectionReason.trim()}
                className="gap-2 font-bold bg-destructive hover:bg-destructive/90 text-white"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                {actionLoading ? 'Rejecting...' : 'Confirm Rejection'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Item Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="font-bold text-base text-foreground">{selectedItem.item_name}</h3>
                <span className="text-xs text-muted-foreground">{selectedItem.food_category}</span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedItem(null)}
                className="text-muted-foreground hover:text-foreground text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-muted/30">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Allocated Volume</span>
                  <strong className="text-primary font-mono text-sm">{selectedItem.allocated_quantity_kg.toFixed(2)} kg</strong>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase">Road Distance</span>
                  <strong className="text-foreground font-mono text-sm">{selectedItem.estimated_distance_km.toFixed(1)} km</strong>
                </div>
              </div>

              <div className="p-3 rounded-lg border border-border bg-background space-y-1">
                <span className="font-semibold text-muted-foreground block text-[10px] uppercase">Linear Solver Justification</span>
                <p className="text-foreground leading-relaxed">{selectedItem.explanation}</p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="button" size="sm" onClick={() => setSelectedItem(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
