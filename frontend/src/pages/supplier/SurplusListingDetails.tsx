import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type {
  SurplusListing,
  PerishabilityEvaluation,
  UrgencyClassification,
  ReceiverProfile,
  RouteEstimateResult,
  MatchingQueryResponse,
} from '@/types'
import { RouteMapPreview } from '@/components/geospatial/RouteMapPreview'
import { CandidateMatchesCard } from '@/components/matching/CandidateMatchesCard'
import { Button } from '@/components/ui/button'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Clock,
  Compass,
  Edit,
  Flame,
  Info,
  Loader2,
  MapPin,
  Navigation,
  Package,
  Pause,
  Play,
  Route,
  ShieldAlert,
  ShieldCheck,
  Thermometer,
  Trash2,
  Truck,
} from 'lucide-react'

export const SurplusListingDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>()

  const [listing, setListing] = useState<SurplusListing | null>(null)
  const [perishability, setPerishability] = useState<PerishabilityEvaluation | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Geospatial route estimation states
  const [receivers, setReceivers] = useState<ReceiverProfile[]>([])
  const [selectedReceiverId, setSelectedReceiverId] = useState<string>('')
  const [handlingBuffer, setHandlingBuffer] = useState<number>(30)
  const [routeEstimate, setRouteEstimate] = useState<RouteEstimateResult | null>(null)
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeError, setRouteError] = useState<string | null>(null)

  // Module 7 Matching candidates states
  const [matchingData, setMatchingData] = useState<MatchingQueryResponse | null>(null)
  const [matchingLoading, setMatchingLoading] = useState(false)
  const [matchingError, setMatchingError] = useState<string | null>(null)
  const [includeIneligible, setIncludeIneligible] = useState(false)

  const fetchListingData = async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const listingData = await apiService.getSurplusListing(id)
      setListing(listingData)

      // Fetch deterministic perishability intelligence
      try {
        const intelData = await apiService.getListingPerishability(id)
        setPerishability(intelData)
      } catch (intelErr) {
        console.warn('Perishability intelligence fetch warning:', intelErr)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load listing details.')
    } finally {
      setLoading(false)
    }
  }

  const fetchCandidates = async (ineligible = includeIneligible) => {
    if (!id) return
    setMatchingLoading(true)
    setMatchingError(null)
    try {
      const data = await apiService.getListingCandidates(id, {
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

  useEffect(() => {
    fetchListingData()
    fetchCandidates()
  }, [id])

  useEffect(() => {
    const loadReceivers = async () => {
      try {
        const list = await apiService.getReceiversDirectory()
        setReceivers(list)
        if (list.length > 0 && !selectedReceiverId) {
          setSelectedReceiverId(list[0].id)
        }
      } catch (e) {
        console.warn('Failed to load receiver directory', e)
      }
    }
    loadReceivers()
  }, [])

  const handleEstimateRoute = async () => {
    if (!id || !selectedReceiverId) return
    setRouteLoading(true)
    setRouteError(null)
    try {
      const res = await apiService.estimateRoute({
        surplus_listing_id: id,
        receiver_id: selectedReceiverId,
        handling_buffer_minutes: Number(handlingBuffer),
      })
      setRouteEstimate(res)
    } catch (err: any) {
      setRouteError(err.response?.data?.detail || 'Failed to estimate route feasibility.')
    } finally {
      setRouteLoading(false)
    }
  }

  const handlePause = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      const updated = await apiService.pauseSurplusListing(id)
      setListing(updated)
      fetchListingData()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to pause listing.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleResume = async () => {
    if (!id) return
    setActionLoading(true)
    try {
      const updated = await apiService.resumeSurplusListing(id)
      setListing(updated)
      fetchListingData()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to resume listing.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!id || !listing) return
    if (!window.confirm(`Are you sure you want to permanently cancel "${listing.item_name}"?`)) {
      return
    }
    setActionLoading(true)
    try {
      const updated = await apiService.cancelSurplusListing(id)
      setListing(updated)
      fetchListingData()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel listing.')
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

  if (error || !listing) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-center space-y-3">
        <AlertCircle className="h-8 w-8 mx-auto" />
        <h3 className="font-semibold">{error || 'Listing not found'}</h3>
        <Link to="/supplier/inventory">
          <Button variant="outline" size="sm">
            Back to Surplus Inventory
          </Button>
        </Link>
      </div>
    )
  }

  const initialQty = Number(listing.initial_quantity_kg)
  const remainingQty = Number(listing.remaining_quantity_kg)
  const distributedQty = Math.max(0, initialQty - remainingQty)
  const percentRemaining = initialQty > 0 ? Math.round((remainingQty / initialQty) * 100) : 0

  const deadline = new Date(listing.estimated_deadline)
  const now = new Date()
  const diffHours = (deadline.getTime() - now.getTime()) / (1000 * 3600)

  const renderUrgencyBanner = (urgency: UrgencyClassification) => {
    switch (urgency) {
      case 'CRITICAL':
        return (
          <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300 flex items-start gap-3">
            <ShieldAlert className="h-6 w-6 text-red-600 dark:text-red-400 shrink-0 mt-0.5 animate-pulse" />
            <div className="space-y-1">
              <div className="font-bold text-sm tracking-wide flex items-center gap-2">
                CRITICAL OPERATIONAL URGENCY &bull; IMMEDIATE ACTION REQUIRED
              </div>
              <p className="text-xs opacity-90">
                Less than 6 hours remain before usable cutoff. This batch must be allocated and dispatched immediately to prevent food waste.
              </p>
            </div>
          </div>
        )
      case 'HIGH':
        return (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200 flex items-start gap-3">
            <Flame className="h-6 w-6 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-sm tracking-wide flex items-center gap-2">
                HIGH URGENCY &bull; SCHEDULE FOR NEXT ALLOCATION CYCLE
              </div>
              <p className="text-xs opacity-90">
                Between 6 and 24 hours remain. Batch should be matched to nearby local receivers within the immediate operational radius.
              </p>
            </div>
          </div>
        )
      case 'MODERATE':
        return (
          <div className="p-4 rounded-xl border border-sky-500/30 bg-sky-500/10 text-sky-800 dark:text-sky-200 flex items-start gap-3">
            <Clock className="h-6 w-6 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-sm tracking-wide flex items-center gap-2">
                MODERATE URGENCY &bull; STANDARD SCHEDULED DISPATCH
              </div>
              <p className="text-xs opacity-90">
                Between 24 and 72 hours remain before expiration. Eligible for standard batching and multi-stop consolidation.
              </p>
            </div>
          </div>
        )
      case 'LOW':
        return (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200 flex items-start gap-3">
            <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-sm tracking-wide flex items-center gap-2">
                LOW URGENCY &bull; STABLE SHELF LIFE
              </div>
              <p className="text-xs opacity-90">
                72 hours or more remaining. Flexible dispatch window; suitable for regional transfer or bulk food bank routing.
              </p>
            </div>
          </div>
        )
      default:
        return (
          <div className="p-4 rounded-xl border border-border bg-muted/30 text-muted-foreground flex items-start gap-3">
            <Info className="h-6 w-6 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-sm tracking-wide">URGENCY PENDING VERIFICATION</div>
              <p className="text-xs">
                Awaiting complete cut-off parameters or physical inspection to determine operational classification.
              </p>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between gap-4">
        <Link to="/supplier/inventory">
          <Button variant="ghost" size="sm" className="gap-2 text-xs">
            <ArrowLeft className="h-4 w-4" />
            Back to Inventory
          </Button>
        </Link>

        {/* Operational Actions */}
        <div className="flex items-center gap-2">
          {(listing.status === 'ACTIVE' || listing.status === 'PAUSED') && (
            <Link to={`/supplier/inventory/${listing.id}/edit`}>
              <Button variant="outline" size="sm" className="text-xs">
                <Edit className="h-3.5 w-3.5 mr-1.5" />
                Edit Listing
              </Button>
            </Link>
          )}

          {listing.status === 'ACTIVE' && (
            <Button
              variant="outline"
              size="sm"
              disabled={actionLoading}
              onClick={handlePause}
              className="text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-500/10"
            >
              <Pause className="h-3.5 w-3.5 mr-1.5" />
              Pause Redistribution
            </Button>
          )}

          {listing.status === 'PAUSED' && (
            <Button
              variant="outline"
              size="sm"
              disabled={actionLoading}
              onClick={handleResume}
              className="text-xs text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Resume Redistribution
            </Button>
          )}

          {(listing.status === 'ACTIVE' || listing.status === 'PAUSED') && (
            <Button
              variant="ghost"
              size="sm"
              disabled={actionLoading}
              onClick={handleCancel}
              className="text-xs text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Cancel Listing
            </Button>
          )}
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-md text-xs font-bold tracking-wider uppercase bg-primary/10 text-primary">
              {listing.food_category}
            </span>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                listing.status === 'ACTIVE'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                  : listing.status === 'PAUSED'
                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {listing.status}
            </span>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold tracking-wider uppercase bg-red-600 text-white">
              {listing.urgency_classification}
            </span>
          </div>

          <span className="text-xs text-muted-foreground font-mono">
            ID: {listing.id}
          </span>
        </div>

        <div>
          <h1 className="text-2xl font-bold text-foreground">{listing.item_name}</h1>
          {listing.description && (
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              {listing.description}
            </p>
          )}
        </div>
      </div>

      {/* Urgency Highlight Banner */}
      {renderUrgencyBanner(listing.urgency_classification as UrgencyClassification)}

      {/* MODULE 5: DEDICATED PERISHABILITY INTELLIGENCE PANEL */}
      <div className="p-6 rounded-xl border border-primary/30 bg-primary/5 shadow-sm space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-primary/20 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <h2 className="text-base font-bold text-foreground">
              Deterministic Perishability Intelligence
            </h2>
          </div>
          {perishability && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Data Quality:</span>
              <span className="px-2 py-0.5 rounded font-bold uppercase bg-background border border-border text-foreground">
                {perishability.data_quality}
              </span>
            </div>
          )}
        </div>

        {perishability ? (
          <div className="space-y-4">
            {/* Explanation */}
            <div className="p-3.5 rounded-lg bg-background border border-border text-xs sm:text-sm text-foreground space-y-1">
              <div className="font-semibold text-muted-foreground text-[11px] uppercase tracking-wider">
                Intelligence Justification:
              </div>
              <p>{perishability.explanation}</p>
            </div>

            {/* Warnings list */}
            {perishability.warnings.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                  Handling & Quality Warnings:
                </div>
                <div className="space-y-1.5">
                  {perishability.warnings.map((warn, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded-lg bg-amber-50/50 dark:bg-amber-950/20 border border-amber-500/30 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-2"
                    >
                      <span className="text-amber-500 font-bold">&bull;</span>
                      <span>{warn}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
              <div className="bg-background p-2.5 rounded-lg border border-border">
                <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                  Usable Window
                </span>
                <span className="font-bold text-sm text-foreground">
                  {perishability.remaining_hours} hrs
                </span>
              </div>
              <div className="bg-background p-2.5 rounded-lg border border-border">
                <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                  Remaining Seconds
                </span>
                <span className="font-bold text-sm text-foreground">
                  {Math.round(perishability.remaining_seconds)}s
                </span>
              </div>
              <div className="bg-background p-2.5 rounded-lg border border-border">
                <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                  Reported Condition
                </span>
                <span className="font-bold text-sm text-foreground">
                  {perishability.condition}
                </span>
              </div>
              <div className="bg-background p-2.5 rounded-lg border border-border">
                <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                  Storage Requirement
                </span>
                <span className="font-bold text-sm text-foreground">
                  {perishability.storage_condition}
                </span>
              </div>
            </div>

            <div className="text-[11px] text-muted-foreground pt-1 flex justify-between">
              <span>Evaluated at: {new Date(perishability.evaluated_at).toLocaleString()}</span>
              <span>Method: Deterministic Boundary Engine</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center py-6 text-xs text-muted-foreground">
            <Loader2 className="h-4 w-4 mr-2 animate-spin text-primary" />
            Computing perishability assessment...
          </div>
        )}

        {/* FOOD SAFETY DISCLAIMER BANNER */}
        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-900 dark:text-amber-200 space-y-1">
          <div className="font-bold flex items-center gap-1.5 uppercase tracking-wider text-[10px]">
            <ShieldAlert className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
            Food Safety & Liability Disclaimer:
          </div>
          <p className="text-[11px] leading-relaxed opacity-95">
            This platform calculates logistical urgency scores based solely on supplier-entered timestamps. 
            It does <strong>NOT</strong> inspect or certify food safety, verify microbial sterility, or guarantee shelf life. 
            Receivers and logistics partners are required by law to conduct sensory inspection at handover.
          </p>
        </div>
      </div>

      {/* Grid Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Quantity Breakdown */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Package className="h-4 w-4 text-primary" />
            Inventory Stock
          </div>
          <div className="space-y-1">
            <div className="text-3xl font-extrabold text-foreground">
              {remainingQty} <span className="text-base font-normal text-muted-foreground">kg</span>
            </div>
            <div className="text-xs text-muted-foreground">
              Remaining of {initialQty} kg initial batch
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${percentRemaining}%` }}
            />
          </div>
          <div className="text-[11px] text-muted-foreground flex justify-between">
            <span>Distributed: {distributedQty} kg</span>
            <span>{percentRemaining}% in stock</span>
          </div>
        </div>

        {/* Usability Cut-off Deadline */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Clock className="h-4 w-4 text-primary" />
            Cut-Off Usable Deadline
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
                Food has expired
              </span>
            ) : diffHours < 24 ? (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-red-500/10 text-red-600 dark:text-red-400">
                Critical: {Math.round(diffHours)} hours remaining
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                {Math.round(diffHours / 24)} days before deadline
              </span>
            )}
          </div>
        </div>

        {/* Quality & Environment */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Thermometer className="h-4 w-4 text-primary" />
            Storage & Quality
          </div>
          <div className="space-y-2 text-xs">
            <div>
              <span className="text-muted-foreground">Storage Environment:</span>
              <div className="font-semibold text-sm text-foreground mt-0.5">
                {listing.storage_condition}
              </div>
            </div>
            <div>
              <span className="text-muted-foreground">Food Condition:</span>
              <div className="font-semibold text-sm text-foreground mt-0.5">
                {listing.food_condition}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Geospatial Routing & Transit Feasibility Subsystem */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold flex items-center gap-2">
              <Route className="h-4 w-4 text-primary" />
              Geospatial Transit & Route Feasibility
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Estimate real-time driving distance, travel duration, and temporal shelf-life feasibility
              towards a registered receiver facility.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Coordinates:</span>
            <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-foreground">
              {routeEstimate
                ? `${routeEstimate.supplier_coordinates.latitude.toFixed(4)}, ${routeEstimate.supplier_coordinates.longitude.toFixed(4)}`
                : 'Facility GPS Profile'}
            </span>
          </div>
        </div>

        {/* Destination & Buffer Selection Controls */}
        <div className="p-4 rounded-xl bg-muted/30 border border-border/60 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-foreground block">
                Destination Receiver Facility:
              </label>
              {receivers.length > 0 ? (
                <select
                  value={selectedReceiverId}
                  onChange={(e) => setSelectedReceiverId(e.target.value)}
                  className="w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring"
                >
                  {receivers.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.organization_name} ({r.city || r.district || 'Facility'}) — Category: {r.receiver_category} — Cap: {r.capacity_daily_kg} kg/day
                    </option>
                  ))}
                </select>
              ) : (
                <div className="text-xs text-muted-foreground italic py-1">
                  Loading verified receiver organizations...
                </div>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground block">
                Handling Buffer (minutes):
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="240"
                  value={handlingBuffer}
                  onChange={(e) => setHandlingBuffer(Math.max(0, parseInt(e.target.value) || 0))}
                  className="w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:outline-hidden focus:ring-2 focus:ring-ring font-mono"
                  placeholder="30"
                />
                <Button
                  onClick={handleEstimateRoute}
                  disabled={routeLoading || !selectedReceiverId}
                  size="sm"
                  className="shrink-0 text-xs gap-1.5"
                >
                  {routeLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Navigation className="h-3.5 w-3.5" />
                  )}
                  {routeLoading ? 'Routing...' : 'Estimate'}
                </Button>
              </div>
            </div>
          </div>

          {routeError && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs text-destructive flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{routeError}</span>
            </div>
          )}
        </div>

        {/* Route Map Preview with Metrics & Feasibility Banner */}
        {routeEstimate ? (
          <RouteMapPreview estimate={routeEstimate} />
        ) : (
          <div className="p-8 text-center border border-dashed rounded-xl bg-card text-muted-foreground space-y-2">
            <Compass className="h-8 w-8 mx-auto text-muted-foreground/60" />
            <div className="text-sm font-medium text-foreground">No Route Estimated Yet</div>
            <p className="text-xs max-w-md mx-auto">
              Select a receiver destination and click <strong>Estimate</strong> to compute road distance,
              travel duration via OSRM (or Haversine fallback), and check if the trip fits within remaining shelf life.
            </p>
          </div>
        )}
      </div>

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
        perspective="SUPPLIER"
      />

      {/* Logistics & Handling Details */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <h2 className="text-base font-semibold flex items-center gap-2">
          <Truck className="h-4 w-4 text-primary" />
          Logistics, Pickup & Handling
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 text-primary" />
              Designated Pickup Address
            </div>
            <p className="font-medium text-foreground bg-muted/30 p-3 rounded-lg border border-border/50">
              {listing.pickup_address || 'Facility default address'}
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-primary" />
              Special Handling Instructions
            </div>
            <p className="text-foreground bg-muted/30 p-3 rounded-lg border border-border/50">
              {listing.handling_instructions || 'Standard food handling procedures apply.'}
            </p>
          </div>
        </div>

        <div className="border-t border-border/60 pt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs text-muted-foreground">
          <div>
            <span className="block font-medium text-foreground">Harvest / Prep Timestamp</span>
            <span>{new Date(listing.harvest_or_prep_date).toLocaleString()}</span>
          </div>
          <div>
            <span className="block font-medium text-foreground">Listing Registered</span>
            <span>{new Date(listing.created_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="block font-medium text-foreground">Last Updated</span>
            <span>{new Date(listing.updated_at).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
