import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { DemandRequest, DemandStatus } from '@/types'
import { Button } from '@/components/ui/button'
import { VerificationStatusBanner } from '@/components/verification/VerificationStatusBanner'
import {
  AlertCircle,
  Clock,
  Edit,
  Eye,
  Filter,
  Flame,
  Loader2,
  Package,
  Pause,
  Play,
  PlusCircle,
  RefreshCw,
  Trash2,
} from 'lucide-react'

const STATUS_FILTERS = [
  { value: '', label: 'All Statuses' },
  { value: 'OPEN', label: 'Open' },
  { value: 'PAUSED', label: 'Paused' },
  { value: 'PARTIALLY_FULFILLED', label: 'Partially Fulfilled' },
  { value: 'FULFILLED', label: 'Fulfilled' },
  { value: 'EXPIRED', label: 'Expired' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

const CATEGORY_FILTERS = [
  { value: '', label: 'All Categories' },
  { value: 'ANY', label: 'Any' },
  { value: 'FRUITS', label: 'Fruits' },
  { value: 'VEGETABLES', label: 'Vegetables' },
  { value: 'GRAINS', label: 'Grains' },
  { value: 'DAIRY', label: 'Dairy' },
  { value: 'BAKERY', label: 'Bakery' },
  { value: 'COOKED_FOOD', label: 'Cooked Food' },
  { value: 'OTHER', label: 'Other' },
]

export const MyDemandRequests: React.FC = () => {
  const [demands, setDemands] = useState<DemandRequest[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchDemands = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiService.getDemandRequests({
        page,
        page_size: 10,
        status: statusFilter || undefined,
        food_category: categoryFilter || undefined,
      })
      setDemands(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load demand requests.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDemands()
  }, [page, statusFilter, categoryFilter])

  const handlePause = async (id: string) => {
    setActionLoadingId(id)
    try {
      await apiService.pauseDemandRequest(id)
      fetchDemands()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to pause demand request.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleResume = async (id: string) => {
    setActionLoadingId(id)
    try {
      await apiService.resumeDemandRequest(id)
      fetchDemands()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to resume demand request.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleCancel = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to cancel the food demand "${name || 'Request'}"?`)) {
      return
    }
    setActionLoadingId(id)
    try {
      await apiService.cancelDemandRequest(id)
      fetchDemands()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to cancel demand request.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const renderStatusBadge = (status: DemandStatus) => {
    switch (status) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
            Open
          </span>
        )
      case 'PAUSED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            Paused
          </span>
        )
      case 'PARTIALLY_FULFILLED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
            Partially Fulfilled
          </span>
        )
      case 'FULFILLED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            Fulfilled
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

  const renderPriorityBadge = (priority: number) => {
    if (priority >= 4) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-600 text-white">
          <Flame className="h-3 w-3" /> Priority {priority}
        </span>
      )
    }
    if (priority === 3) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-amber-500 text-white">
          Priority 3
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-muted text-muted-foreground">
        Priority {priority}
      </span>
    )
  }

  const formatDeadline = (isoString: string) => {
    const deadline = new Date(isoString)
    const now = new Date()
    const diffHours = (deadline.getTime() - now.getTime()) / (1000 * 3600)

    if (diffHours <= 0) {
      return <span className="text-destructive font-semibold">Cut-off passed</span>
    } else if (diffHours < 24) {
      return (
        <span className="text-red-500 font-semibold flex items-center gap-1">
          <Clock className="h-3 w-3" /> Due in {Math.round(diffHours)}h
        </span>
      )
    } else {
      const days = Math.round(diffHours / 24)
      return (
        <span className="text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" /> Due in {days}d
        </span>
      )
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-6">
      <VerificationStatusBanner />

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Food Demand Requests</h1>
          <p className="text-sm text-muted-foreground">
            Manage your intake requirements, monitor allocation fulfillment, and track meal service cut-offs.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" onClick={fetchDemands} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Link to="/receiver/demands/new">
            <Button size="sm">
              <PlusCircle className="h-4 w-4 mr-1.5" />
              New Demand Request
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
          Showing <strong>{demands.length}</strong> of <strong>{total}</strong> requests
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
      ) : demands.length === 0 ? (
        <div className="p-12 rounded-xl border border-dashed border-border bg-card text-center space-y-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Package className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-semibold">No Demand Requests Found</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {statusFilter || categoryFilter
              ? 'No requests match your selected filters. Try clearing the filters.'
              : 'You have not registered any food requirements yet. Submit a demand request to receive redistribution proposals.'}
          </p>
          <div className="pt-2">
            <Link to="/receiver/demands/new">
              <Button size="sm">
                <PlusCircle className="h-4 w-4 mr-1.5" />
                Submit First Request
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {demands.map((item) => {
              const requested = Number(item.requested_quantity_kg)
              const fulfilled = Number(item.fulfilled_quantity_kg)
              const remaining = Number(item.remaining_requirement_kg)
              const percentFulfilled = requested > 0 ? Math.round((fulfilled / requested) * 100) : 0
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
                      {renderPriorityBadge(item.priority_weight)}
                      <span className="text-xs text-muted-foreground ml-auto lg:ml-0">
                        Req #{item.id.slice(0, 8)}
                      </span>
                    </div>

                    <div>
                      <Link
                        to={`/receiver/demands/${item.id}`}
                        className="text-lg font-bold text-foreground hover:text-primary transition-colors"
                      >
                        {item.item_name || `${item.food_category} Food Request`}
                      </Link>
                      {item.description && (
                        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                          {item.description}
                        </p>
                      )}
                    </div>

                    {/* Fulfillment progress */}
                    <div className="max-w-xs space-y-1 pt-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-foreground">
                          {fulfilled} / {requested} kg fulfilled
                        </span>
                        <span className="text-muted-foreground text-[11px]">
                          {remaining} kg needed
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${percentFulfilled}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Requirements & Deadline */}
                  <div className="flex flex-wrap sm:flex-nowrap items-center gap-6 text-xs text-muted-foreground border-y sm:border-y-0 sm:border-l border-border py-3 sm:py-0 sm:pl-6">
                    <div className="space-y-1">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                        Storage & Condition
                      </div>
                      <div className="font-medium text-foreground">
                        {item.storage_capability} • Min {item.acceptable_food_condition || 'FAIR'}
                      </div>
                      {item.dietary_requirements && item.dietary_requirements.length > 0 && (
                        <div className="text-[11px] text-primary truncate max-w-[160px]">
                          {item.dietary_requirements.join(', ')}
                        </div>
                      )}
                    </div>

                    <div className="space-y-1">
                      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                        Required By Cut-Off
                      </div>
                      <div className="font-medium">
                        {formatDeadline(item.required_by)}
                      </div>
                    </div>
                  </div>

                  {/* Operational Actions */}
                  <div className="flex items-center gap-2 pt-2 lg:pt-0 self-end lg:self-center">
                    <Link to={`/receiver/demands/${item.id}`}>
                      <Button variant="outline" size="sm" className="h-8 px-2.5 text-xs">
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Details
                      </Button>
                    </Link>

                    {(item.status === 'OPEN' || item.status === 'PAUSED') && (
                      <Link to={`/receiver/demands/${item.id}/edit`}>
                        <Button variant="outline" size="sm" className="h-8 px-2.5 text-xs">
                          <Edit className="h-3.5 w-3.5 mr-1" />
                          Edit
                        </Button>
                      </Link>
                    )}

                    {(item.status === 'OPEN' || item.status === 'PARTIALLY_FULFILLED') && (
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
                        className="h-8 px-2.5 text-xs text-sky-600 hover:text-sky-700 hover:bg-sky-500/10"
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

                    {(item.status === 'OPEN' ||
                      item.status === 'PAUSED' ||
                      item.status === 'PARTIALLY_FULFILLED') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isActionRunning}
                        onClick={() => handleCancel(item.id, item.item_name || 'Request')}
                        className="h-8 px-2 text-xs text-destructive hover:bg-destructive/10"
                        title="Cancel demand request"
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
