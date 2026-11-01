import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { SurplusListing, SurplusStatus } from '@/types'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  Clock,
  Eye,
  Edit,
  Filter,
  Loader2,
  Package,
  Pause,
  Play,
  PlusCircle,
  RefreshCw,
  Thermometer,
  Trash2,
} from 'lucide-react'

const STATUS_FILTERS = [
  { value: '', label: 'All Statuses' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'PAUSED', label: 'Paused' },
  { value: 'DEPLETED', label: 'Depleted' },
  { value: 'EXPIRED', label: 'Expired' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

const CATEGORY_FILTERS = [
  { value: '', label: 'All Categories' },
  { value: 'FRUITS', label: 'Fruits' },
  { value: 'VEGETABLES', label: 'Vegetables' },
  { value: 'GRAINS', label: 'Grains' },
  { value: 'DAIRY', label: 'Dairy' },
  { value: 'BAKERY', label: 'Bakery' },
  { value: 'COOKED_FOOD', label: 'Cooked Food' },
  { value: 'OTHER', label: 'Other' },
]

export const MySurplusInventory: React.FC = () => {
  const [listings, setListings] = useState<SurplusListing[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchListings = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiService.getSurplusListings({
        page,
        page_size: 10,
        status: statusFilter || undefined,
        food_category: categoryFilter || undefined,
      })
      setListings(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load surplus inventory.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchListings()
  }, [page, statusFilter, categoryFilter])

  const handlePause = async (id: string) => {
    setActionLoadingId(id)
    try {
      await apiService.pauseSurplusListing(id)
      fetchListings()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to pause listing.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleResume = async (id: string) => {
    setActionLoadingId(id)
    try {
      await apiService.resumeSurplusListing(id)
      fetchListings()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to resume listing.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleCancel = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to cancel the listing "${name}"? This cannot be undone.`)) {
      return
    }
    setActionLoadingId(id)
    try {
      await apiService.cancelSurplusListing(id)
      fetchListings()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel listing.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const renderStatusBadge = (status: SurplusStatus) => {
    switch (status) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            Active
          </span>
        )
      case 'PAUSED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Paused
          </span>
        )
      case 'DEPLETED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
            Depleted
          </span>
        )
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
            Expired
          </span>
        )
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-neutral-500/10 text-neutral-500 border border-neutral-500/20 line-through">
            Cancelled
          </span>
        )
      default:
        return <span className="text-xs text-muted-foreground">{status}</span>
    }
  }

  const renderUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800 animate-pulse">
            Critical Urgency
          </span>
        )
      case 'HIGH':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800">
            High Urgency
          </span>
        )
      case 'MODERATE':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800">
            Moderate Urgency
          </span>
        )
      case 'LOW':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800">
            Low Urgency
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-medium tracking-wider uppercase bg-muted text-muted-foreground border border-border">
            Pending Evaluation
          </span>
        )
    }
  }

  const formatDeadline = (isoString: string) => {
    const deadline = new Date(isoString)
    const now = new Date()
    const diffHours = (deadline.getTime() - now.getTime()) / (1000 * 3600)

    if (diffHours <= 0) {
      return <span className="text-destructive font-semibold">Expired</span>
    } else if (diffHours < 24) {
      return (
        <span className="text-red-500 font-semibold flex items-center gap-1">
          <Clock className="h-3 w-3" /> {Math.round(diffHours)}h remaining
        </span>
      )
    } else {
      const days = Math.round(diffHours / 24)
      return (
        <span className="text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" /> {days}d remaining
        </span>
      )
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Surplus Food Inventory</h1>
          <p className="text-sm text-muted-foreground">
            Manage your registered perishable batches, monitor countdown deadlines, and track remaining stock.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                await apiService.getBatchActivePerishability()
                fetchListings()
              } catch (err: any) {
                alert(err.response?.data?.detail || 'Failed to evaluate perishability.')
              }
            }}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Evaluate Urgency
          </Button>
          <Link to="/supplier/inventory/new">
            <Button size="sm">
              <PlusCircle className="h-4 w-4 mr-1.5" />
              Add Surplus Food
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl border border-border bg-card shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <Filter className="h-3.5 w-3.5" />
            Filters:
          </div>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-1.5 rounded-lg border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-1.5 rounded-lg border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {CATEGORY_FILTERS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-muted-foreground w-full md:w-auto text-right">
          Showing <strong>{listings.length}</strong> of <strong>{total}</strong> batches
        </div>
      </div>

      {/* Content Area */}
      {error && (
        <div className="p-4 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive flex items-center gap-3 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : listings.length === 0 ? (
        <div className="p-12 rounded-xl border border-dashed border-border bg-card text-center space-y-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Package className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-semibold">No Surplus Food Listings Found</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {statusFilter || categoryFilter
              ? 'No listings match your selected status and category filters. Try clearing the filters.'
              : 'You have not listed any perishable food surplus yet. Start by listing a batch before it spoils.'}
          </p>
          <div className="pt-2">
            <Link to="/supplier/inventory/new">
              <Button size="sm">
                <PlusCircle className="h-4 w-4 mr-1.5" />
                List First Food Batch
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {listings.map((item) => {
              const remaining = Number(item.remaining_quantity_kg)
              const initial = Number(item.initial_quantity_kg)
              const percentRemaining = initial > 0 ? Math.round((remaining / initial) * 100) : 0
              const isActionRunning = actionLoadingId === item.id

              return (
                <div
                  key={item.id}
                  className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/40 transition-all flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold tracking-wider uppercase bg-primary/10 text-primary">
                        {item.food_category}
                      </span>
                      {renderStatusBadge(item.status)}
                      {renderUrgencyBadge(item.urgency_classification)}

                      {/* Condition & Storage Indicators */}
                      {item.food_condition === 'IMMINENT_DECAY' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/30 animate-pulse">
                          Imminent Decay
                        </span>
                      )}
                      {item.food_condition === 'RIPE' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                          Ripe Produce
                        </span>
                      )}
                      {item.storage_condition === 'REFRIGERATED' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
                          Cold Chain
                        </span>
                      )}
                      {item.storage_condition === 'FROZEN' && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                          Frozen
                        </span>
                      )}

                      <span className="text-xs text-muted-foreground ml-auto lg:ml-0">
                        Batch #{item.id.slice(0, 8)}
                      </span>
                    </div>

                    <div>
                      <Link
                        to={`/supplier/inventory/${item.id}`}
                        className="text-lg font-bold text-foreground hover:text-primary transition-colors"
                      >
                        {item.item_name}
                      </Link>
                      {item.description && (
                        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                          {item.description}
                        </p>
                      )}
                    </div>

                    {/* Stock meter */}
                    <div className="max-w-xs space-y-1 pt-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-foreground">
                          {remaining} / {initial} kg remaining
                        </span>
                        <span className="text-muted-foreground text-[11px]">
                          {percentRemaining}% stock
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            percentRemaining > 40
                              ? 'bg-emerald-500'
                              : percentRemaining > 15
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${percentRemaining}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Conditions & Deadline */}
                  <div className="flex flex-wrap sm:flex-nowrap items-center gap-6 text-xs text-muted-foreground border-y sm:border-y-0 sm:border-l border-border py-3 sm:py-0 sm:pl-6">
                    <div className="space-y-1">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                        Storage & Condition
                      </div>
                      <div className="font-medium text-foreground flex items-center gap-1.5">
                        <Thermometer className="h-3.5 w-3.5 text-primary" />
                        {item.storage_condition} • {item.food_condition}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                        Usable Deadline
                      </div>
                      <div className="font-medium">
                        {formatDeadline(item.estimated_deadline)}
                      </div>
                    </div>
                  </div>

                  {/* Operational Actions */}
                  <div className="flex items-center gap-2 pt-2 lg:pt-0 self-end lg:self-center">
                    <Link to={`/supplier/inventory/${item.id}`}>
                      <Button variant="outline" size="sm" className="h-8 px-2.5 text-xs">
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Details
                      </Button>
                    </Link>

                    {(item.status === 'ACTIVE' || item.status === 'PAUSED') && (
                      <Link to={`/supplier/inventory/${item.id}/edit`}>
                        <Button variant="outline" size="sm" className="h-8 px-2.5 text-xs">
                          <Edit className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>
                      </Link>
                    )}

                    {item.status === 'ACTIVE' && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isActionRunning}
                        onClick={() => handlePause(item.id)}
                        className="h-8 px-2.5 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-500/10"
                      >
                        {isActionRunning ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <>
                            <Pause className="h-3.5 w-3.5 mr-1" />
                            Pause
                          </>
                        )}
                      </Button>
                    )}

                    {item.status === 'PAUSED' && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isActionRunning}
                        onClick={() => handleResume(item.id)}
                        className="h-8 px-2.5 text-xs text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                      >
                        {isActionRunning ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <>
                            <Play className="h-3.5 w-3.5 mr-1" />
                            Resume
                          </>
                        )}
                      </Button>
                    )}

                    {(item.status === 'ACTIVE' || item.status === 'PAUSED') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isActionRunning}
                        onClick={() => handleCancel(item.id, item.item_name)}
                        className="h-8 px-2 text-xs text-destructive hover:bg-destructive/10"
                        title="Cancel listing"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Pagination Controls */}
          {pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground font-medium">
                Page {page} of {pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= pages || loading}
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
