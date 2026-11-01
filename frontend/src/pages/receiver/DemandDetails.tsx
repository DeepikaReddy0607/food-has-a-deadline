import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { DemandRequest, MatchingQueryResponse } from '@/types'
import { CandidateMatchesCard } from '@/components/matching/CandidateMatchesCard'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Edit,
  Flame,
  Info,
  Loader2,
  MapPin,
  Package,
  Pause,
  Play,
  ShieldCheck,
  Trash2,
  Truck,
} from 'lucide-react'

export const DemandDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>()

  const [demand, setDemand] = useState<DemandRequest | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Module 7 Matching candidate states
  const [matchingData, setMatchingData] = useState<MatchingQueryResponse | null>(null)
  const [matchingLoading, setMatchingLoading] = useState(false)
  const [matchingError, setMatchingError] = useState<string | null>(null)
  const [includeIneligible, setIncludeIneligible] = useState(false)

  const fetchCandidates = async (ineligible = includeIneligible) => {
    if (!id) return
    setMatchingLoading(true)
    setMatchingError(null)
    try {
      const data = await apiService.getDemandCandidates(id, {
        include_ineligible: ineligible,
      })
      setMatchingData(data)
    } catch (err: any) {
      if (err?.code === 'ECONNABORTED' || err?.message?.toLowerCase().includes('timeout')) {
        setMatchingError(
          'Candidate evaluation timed out after 60 seconds. Road routing calculation may still be processing on the server.'
        )
      } else {
        setMatchingError(err.response?.data?.detail || 'Failed to fetch candidate matches.')
      }
    } finally {
      setMatchingLoading(false)
    }
  }

  const fetchDemand = async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiService.getDemandRequest(id)
      setDemand(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load demand details.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDemand()
    fetchCandidates()
  }, [id])

  const handlePause = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      const updated = await apiService.pauseDemandRequest(id)
      setDemand(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to pause demand request.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleResume = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      const updated = await apiService.resumeDemandRequest(id)
      setDemand(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to resume demand request.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!id || !demand) return
    if (!window.confirm(`Are you sure you want to cancel this demand request?`)) {
      return
    }
    setActionLoading(true)
    try {
      const updated = await apiService.cancelDemandRequest(id)
      setDemand(updated)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel demand request.')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !demand) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-center space-y-3">
        <AlertCircle className="h-8 w-8 mx-auto" />
        <h3 className="font-semibold">{error || 'Demand request not found'}</h3>
        <Link to="/receiver/demands">
          <Button variant="outline" size="sm">
            Back to Demand Requests
          </Button>
        </Link>
      </div>
    )
  }

  const requested = Number(demand.requested_quantity_kg)
  const fulfilled = Number(demand.fulfilled_quantity_kg)
  const remaining = Number(demand.remaining_requirement_kg)
  const percentFulfilled = requested > 0 ? Math.round((fulfilled / requested) * 100) : 0

  const deadline = new Date(demand.required_by)
  const now = new Date()
  const diffHours = (deadline.getTime() - now.getTime()) / (1000 * 3600)

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between gap-4">
        <Link to="/receiver/demands">
          <Button variant="ghost" size="sm" className="gap-2 text-xs">
            <ArrowLeft className="h-4 w-4" />
            Back to Demands
          </Button>
        </Link>

        {/* Operational Actions */}
        <div className="flex items-center gap-2">
          {(demand.status === 'OPEN' || demand.status === 'PAUSED') && (
            <Link to={`/receiver/demands/${demand.id}/edit`}>
              <Button variant="outline" size="sm" className="text-xs">
                <Edit className="h-3.5 w-3.5 mr-1.5" />
                Edit Request
              </Button>
            </Link>
          )}

          {(demand.status === 'OPEN' || demand.status === 'PARTIALLY_FULFILLED') && (
            <Button
              variant="outline"
              size="sm"
              disabled={actionLoading}
              onClick={handlePause}
              className="text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-500/10"
            >
              <Pause className="h-3.5 w-3.5 mr-1.5" />
              Pause Request
            </Button>
          )}

          {demand.status === 'PAUSED' && (
            <Button
              variant="outline"
              size="sm"
              disabled={actionLoading}
              onClick={handleResume}
              className="text-xs text-sky-600 hover:text-sky-700 hover:bg-sky-500/10"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Resume Request
            </Button>
          )}

          {(demand.status === 'OPEN' ||
            demand.status === 'PAUSED' ||
            demand.status === 'PARTIALLY_FULFILLED') && (
            <Button
              variant="ghost"
              size="sm"
              disabled={actionLoading}
              onClick={handleCancel}
              className="text-xs text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Cancel Request
            </Button>
          )}
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-md text-xs font-bold tracking-wider uppercase bg-primary/10 text-primary">
              {demand.food_category}
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                demand.status === 'OPEN'
                  ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20'
                  : demand.status === 'PARTIALLY_FULFILLED'
                  ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20'
                  : demand.status === 'FULFILLED'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                  : demand.status === 'PAUSED'
                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {demand.status.replace('_', ' ')}
            </span>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[11px] font-bold uppercase bg-red-600 text-white">
              <Flame className="h-3.5 w-3.5" /> Priority Level {demand.priority_weight}
            </span>
          </div>

          <span className="text-xs text-muted-foreground font-mono">
            ID: {demand.id}
          </span>
        </div>

        <div>
          <h1 className="text-2xl font-bold text-foreground">
            {demand.item_name || `${demand.food_category} Requirement`}
          </h1>
          {demand.description && (
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              {demand.description}
            </p>
          )}
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Fulfillment Breakdown */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Package className="h-4 w-4 text-primary" />
            Requirement Fulfillment
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-foreground">
              {remaining} <span className="text-base font-normal text-muted-foreground">kg</span>
            </div>
            <div className="text-xs text-muted-foreground">
              Still needed out of {requested} kg total
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${percentFulfilled}%` }}
            />
          </div>
          <div className="text-[11px] text-muted-foreground flex justify-between">
            <span>Fulfilled: {fulfilled} kg</span>
            <span>{percentFulfilled}% complete</span>
          </div>
        </div>

        {/* Required-By Cut-Off */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Clock className="h-4 w-4 text-primary" />
            Service Cut-Off Deadline
          </div>
          <div className="space-y-1">
            <div className="text-xl font-bold text-foreground">
              {deadline.toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </div>
            <div className="text-xs text-muted-foreground">
              {deadline.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
          <div className="pt-1">
            {diffHours <= 0 ? (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-destructive/10 text-destructive">
                Cut-off has passed
              </span>
            ) : diffHours < 24 ? (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-red-500/10 text-red-600 dark:text-red-400">
                Imminent: {Math.round(diffHours)} hours remaining
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-sky-500/10 text-sky-600 dark:text-sky-400">
                {Math.round(diffHours / 24)} days until cut-off
              </span>
            )}
          </div>
        </div>

        {/* Storage & Dietary */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Intake Constraints
          </div>
          <div className="space-y-2 text-xs">
            <div>
              <span className="text-muted-foreground">Storage Capability:</span>
              <div className="font-semibold text-sm text-foreground mt-0.5">
                {demand.storage_capability}
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Acceptable Condition:</span>
              <div className="font-semibold text-sm text-foreground mt-0.5">
                {demand.acceptable_food_condition || 'FAIR (Any edible)'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dietary Tags Card */}
      {demand.dietary_requirements && demand.dietary_requirements.length > 0 && (
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm flex items-center gap-3">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0">
            Dietary Requirements:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {demand.dietary_requirements.map((tag) => (
              <span
                key={tag}
                className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
              >
                {tag.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Module 7 Multi-Factor Candidate Matches */}
      <CandidateMatchesCard
        matchingData={matchingData}
        loading={matchingLoading}
        error={matchingError}
        onRefresh={() => fetchCandidates(includeIneligible)}
        onToggleIneligible={(val) => {
          setIncludeIneligible(val)
          fetchCandidates(val)
        }}
        includeIneligible={includeIneligible}
        perspective="RECEIVER"
      />

      {/* Delivery Logistics */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <h2 className="text-base font-semibold flex items-center gap-2">
          <Truck className="h-4 w-4 text-primary" />
          Delivery Destination & Instructions
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-primary" />
              Delivery Destination Address
            </div>
            <p className="font-medium text-foreground bg-muted/30 p-3 rounded-lg border border-border/50">
              {demand.delivery_address || 'Facility registered address'}
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-primary" />
              Receiving / Unloading Instructions
            </div>
            <p className="text-foreground bg-muted/30 p-3 rounded-lg border border-border/50">
              {demand.handling_instructions || 'Standard intake and inspection on delivery.'}
            </p>
          </div>
        </div>

        <div className="border-t border-border/60 pt-4 grid grid-cols-2 gap-4 text-xs text-muted-foreground">
          <div>
            <span className="block font-medium text-foreground">Request Created</span>
            <span>{new Date(demand.created_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="block font-medium text-foreground">Last Updated</span>
            <span>{new Date(demand.updated_at).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
