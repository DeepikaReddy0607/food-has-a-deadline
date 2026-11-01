import React, { useState } from 'react'
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Clock,
  Package,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Scale,
  Navigation,
  Info,
} from 'lucide-react'
import type { CandidateMatch, MatchingQueryResponse } from '@/types'
import { Button } from '@/components/ui/button'

interface CandidateMatchesCardProps {
  matchingData: MatchingQueryResponse | null
  loading: boolean
  error?: string | null
  onRefresh?: () => void
  onToggleIneligible?: (include: boolean) => void
  includeIneligible?: boolean
  perspective: 'SUPPLIER' | 'RECEIVER' | 'COORDINATOR'
}

export const CandidateMatchesCard: React.FC<CandidateMatchesCardProps> = ({
  matchingData,
  loading,
  error,
  onRefresh,
  onToggleIneligible,
  includeIneligible = false,
  perspective,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id)
  }

  const getStatusBadge = (eligibility: string) => {
    switch (eligibility) {
      case 'ELIGIBLE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
            <CheckCircle2 className="w-3 h-3" />
            ELIGIBLE
          </span>
        )
      case 'REVIEW_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-700">
            <HelpCircle className="w-3 h-3" />
            REVIEW REQUIRED
          </span>
        )
      case 'INELIGIBLE':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700">
            <AlertTriangle className="w-3 h-3" />
            INELIGIBLE
          </span>
        )
    }
  }

  return (
    <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            <h3 className="text-base font-semibold text-foreground">
              {perspective === 'SUPPLIER'
                ? 'Compatible Receiver Demand Matches'
                : perspective === 'RECEIVER'
                ? 'Compatible Surplus Inventory Matches'
                : 'Supply-Demand Candidate Matches'}
            </h3>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Deterministic multi-factor matching across product category, cold-storage hardware, volume, and road transit feasibility.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeIneligible}
              onChange={(e) => onToggleIneligible && onToggleIneligible(e.target.checked)}
              className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5"
            />
            Show Ineligible
          </label>

          {onRefresh && (
            <Button
              onClick={onRefresh}
              disabled={loading}
              variant="outline"
              size="sm"
              className="text-xs h-8"
            >
              {loading ? 'Evaluating...' : 'Refresh Matches'}
            </Button>
          )}
        </div>
      </div>

      {/* Summary Metrics Bar */}
      {matchingData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div className="p-2.5 bg-muted/40 rounded-lg border border-border/50">
            <span className="text-[10px] text-muted-foreground uppercase font-semibold block">
              Total Candidates
            </span>
            <span className="text-lg font-bold text-foreground">
              {matchingData.total_candidates}
            </span>
          </div>

          <div className="p-2.5 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
            <span className="text-[10px] text-emerald-700 dark:text-emerald-300 uppercase font-semibold block">
              Eligible
            </span>
            <span className="text-lg font-bold text-emerald-800 dark:text-emerald-200">
              {matchingData.eligible_count}
            </span>
          </div>

          <div className="p-2.5 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <span className="text-[10px] text-amber-700 dark:text-amber-300 uppercase font-semibold block">
              Review Required
            </span>
            <span className="text-lg font-bold text-amber-800 dark:text-amber-200">
              {matchingData.review_required_count}
            </span>
          </div>

          <div className="p-2.5 bg-rose-50 dark:bg-rose-950/20 rounded-lg border border-rose-200 dark:border-rose-800">
            <span className="text-[10px] text-rose-700 dark:text-rose-300 uppercase font-semibold block">
              Ineligible
            </span>
            <span className="text-lg font-bold text-rose-800 dark:text-rose-200">
              {matchingData.ineligible_count}
            </span>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3.5 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !matchingData && (
        <div className="py-12 text-center text-xs text-muted-foreground space-y-2">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-primary border-t-transparent" />
          <p>Evaluating multi-factor compatibility from PostgreSQL records...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && matchingData && matchingData.candidates.length === 0 && (
        <div className="py-10 text-center border border-dashed rounded-xl bg-card text-muted-foreground space-y-2">
          <Package className="h-8 w-8 mx-auto text-muted-foreground/50" />
          <p className="text-sm font-medium text-foreground">No Compatible Candidates Found</p>
          <p className="text-xs max-w-md mx-auto">
            {includeIneligible
              ? 'No active demand requests or surplus batches currently exist in the database.'
              : 'No candidates satisfy all hard compatibility and transit constraints. Enable "Show Ineligible" to inspect rejected pairs.'}
          </p>
        </div>
      )}

      {/* Candidates List */}
      {!loading && matchingData && matchingData.candidates.length > 0 && (
        <div className="space-y-3">
          {matchingData.candidates.map((cand: CandidateMatch, idx: number) => {
            const isExpanded = expandedId === cand.candidate_id
            const partnerName =
              perspective === 'SUPPLIER' ? cand.receiver_name : cand.supplier_name

            return (
              <div
                key={cand.candidate_id}
                className={`rounded-xl border transition-all ${
                  cand.is_eligible
                    ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/20 dark:bg-emerald-950/10'
                    : cand.eligibility === 'REVIEW_REQUIRED'
                    ? 'border-amber-200 dark:border-amber-900/60 bg-amber-50/20 dark:bg-amber-950/10'
                    : 'border-border/60 bg-card/60 opacity-80'
                }`}
              >
                {/* Main Summary Row */}
                <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground font-bold">
                        #{idx + 1}
                      </span>
                      <h4 className="font-semibold text-sm text-foreground">{partnerName}</h4>
                      {getStatusBadge(cand.eligibility)}
                      {cand.is_eligible && (
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                          Score: {cand.score}/100
                        </span>
                      )}
                      {cand.receiver_category && (
                        <span className="text-[11px] px-2 py-0.5 rounded bg-muted text-muted-foreground">
                          {cand.receiver_category}
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
                      <span className="flex items-center gap-1">
                        <Package className="w-3.5 h-3.5 text-primary" />
                        Item: <strong className="text-foreground">{cand.item_name}</strong> ({cand.food_category})
                      </span>
                      <span className="flex items-center gap-1">
                        <Scale className="w-3.5 h-3.5 text-blue-500" />
                        Match: <strong className="text-foreground">{cand.quantity_compatibility.matched_quantity_kg} kg</strong>
                        {cand.quantity_compatibility.is_partial && (
                          <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                            ({(cand.quantity_compatibility.fulfillment_ratio * 100).toFixed(0)}% partial)
                          </span>
                        )}
                      </span>
                      <span className="flex items-center gap-1">
                        <Navigation className="w-3.5 h-3.5 text-indigo-500" />
                        {cand.road_distance_km} km ({cand.estimated_transit_minutes} min transit)
                        {cand.is_route_fallback && (
                          <span className="text-[10px] text-orange-600 font-mono">*approx</span>
                        )}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-amber-500" />
                        Shelf life: {cand.remaining_shelf_life_hours.toFixed(1)} hrs ({cand.perishability_urgency})
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center">
                    <Button
                      onClick={() => toggleExpand(cand.candidate_id)}
                      variant="ghost"
                      size="sm"
                      className="text-xs gap-1 h-8"
                    >
                      {isExpanded ? (
                        <>
                          Less Info <ChevronUp className="w-3.5 h-3.5" />
                        </>
                      ) : (
                        <>
                          Evaluation Details <ChevronDown className="w-3.5 h-3.5" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Expanded Evaluation Breakdown */}
                {isExpanded && (
                  <div className="border-t border-border/80 p-4 bg-muted/20 space-y-3.5 text-xs">
                    {/* Explanation Banner */}
                    <div className="p-3 rounded-lg bg-card border text-foreground leading-relaxed">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1 flex items-center gap-1">
                        <Info className="w-3 h-3 text-primary" />
                        Deterministic Evaluation Rationale:
                      </div>
                      <p>{cand.explanation}</p>
                    </div>

                    {/* Score Breakdown (if eligible) */}
                    {cand.is_eligible && (
                      <div className="p-3 rounded-lg bg-card border space-y-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">
                          Weighted Ranking Factors (0 - 100):
                        </span>
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                          <div className="p-2 bg-muted/40 rounded">
                            <span className="block text-[10px] text-muted-foreground">Urgency (25%)</span>
                            <span className="font-bold text-foreground">
                              {cand.score_breakdown.urgency_score}
                            </span>
                          </div>
                          <div className="p-2 bg-muted/40 rounded">
                            <span className="block text-[10px] text-muted-foreground">Proximity (25%)</span>
                            <span className="font-bold text-foreground">
                              {cand.score_breakdown.proximity_score}
                            </span>
                          </div>
                          <div className="p-2 bg-muted/40 rounded">
                            <span className="block text-[10px] text-muted-foreground">Shelf Slack (20%)</span>
                            <span className="font-bold text-foreground">
                              {cand.score_breakdown.shelf_life_margin_score}
                            </span>
                          </div>
                          <div className="p-2 bg-muted/40 rounded">
                            <span className="block text-[10px] text-muted-foreground">Quantity Fit (15%)</span>
                            <span className="font-bold text-foreground">
                              {cand.score_breakdown.quantity_fit_score}
                            </span>
                          </div>
                          <div className="p-2 bg-muted/40 rounded">
                            <span className="block text-[10px] text-muted-foreground">Priority (15%)</span>
                            <span className="font-bold text-foreground">
                              {cand.score_breakdown.priority_score}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Compatibility Check Matrix */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div className="p-2.5 rounded bg-card border space-y-1">
                        <div className="font-semibold text-foreground flex items-center gap-1">
                          Product: {cand.product_compatibility.match_level}
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          {cand.product_compatibility.notes}
                        </p>
                      </div>

                      <div className="p-2.5 rounded bg-card border space-y-1">
                        <div className="font-semibold text-foreground flex items-center gap-1">
                          Storage: {cand.storage_compatibility.match_level}
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          {cand.storage_compatibility.notes}
                        </p>
                      </div>

                      <div className="p-2.5 rounded bg-card border space-y-1">
                        <div className="font-semibold text-foreground flex items-center gap-1">
                          Transit: {cand.transit_feasibility}
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          {cand.road_distance_km} km road route ({cand.routing_provider}).
                        </p>
                      </div>
                    </div>

                    {/* Rejection Reasons if Ineligible */}
                    {cand.rejection_reasons.length > 0 && (
                      <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 space-y-1">
                        <span className="font-bold text-[10px] uppercase tracking-wider block">
                          Hard Constraint Failures:
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-xs">
                          {cand.rejection_reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Warnings List if any */}
                    {cand.warnings.length > 0 && (
                      <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 space-y-1">
                        <span className="font-bold text-[10px] uppercase tracking-wider block">
                          Operational Warnings:
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-xs">
                          {cand.warnings.map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Read-Only Invariant Notice */}
                    <div className="text-[10px] text-muted-foreground italic flex items-center gap-1 pt-1">
                      <Scale className="w-3 h-3 text-muted-foreground/60" />
                      Matching is read-only. Quantities are not reserved or modified. Allocation optimization is conducted by the central solver.
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
