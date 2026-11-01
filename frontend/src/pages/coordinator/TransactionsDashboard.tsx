import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Truck,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Scale,
  Calendar,
  Building2,
  FileText,
  Copy,
  Check,
  Send,
  XCircle,
  History,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { apiService } from '@/services/api'
import type {
  TransactionResponse,
  TransactionStatus,
  UpdateTransactionStatusRequest,
} from '@/types'

export const TransactionsDashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [transactions, setTransactions] = useState<TransactionResponse[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [expandedTxId, setExpandedTxId] = useState<string | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // Status Update Modal State
  const [updatingTx, setUpdatingTx] = useState<TransactionResponse | null>(null)
  const [targetStatus, setTargetStatus] = useState<TransactionStatus>('PICKUP_SCHEDULED')
  const [statusReason, setStatusReason] = useState<string>('')
  const [statusNotes, setStatusNotes] = useState<string>('')
  const [confirmedReturnedKg, setConfirmedReturnedKg] = useState<string>('')
  const [actualDeliveredKg, setActualDeliveredKg] = useState<string>('')
  const [actionLoading, setActionLoading] = useState<boolean>(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const fetchTransactions = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await apiService.listTransactions({ limit: 100 })
      setTransactions(resp.items)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } }
        setError(axErr.response?.data?.detail || 'Failed to load redistribution transactions.')
      } else {
        setError('Network error fetching transactions.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(text)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const handleExecuteDispatch = async (txId: string) => {
    setActionLoading(true)
    try {
      const updated = await apiService.executeTransaction(txId)
      setTransactions((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    } catch (err: unknown) {
      console.error('Dispatch execution error:', err)
      alert('Failed to execute dispatch.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleOpenStatusModal = (tx: TransactionResponse) => {
    setUpdatingTx(tx)
    setActionError(null)
    setStatusReason('')
    setStatusNotes(tx.dispatch_notes || '')
    setConfirmedReturnedKg('')
    setActualDeliveredKg('')

    // Pick sensible default next status based on current
    switch (tx.status) {
      case 'APPROVED':
        setTargetStatus('PICKUP_SCHEDULED')
        break
      case 'PICKUP_SCHEDULED':
      case 'SCHEDULED':
        setTargetStatus('PICKED_UP')
        break
      case 'PICKED_UP':
      case 'DISPATCHED':
        setTargetStatus('IN_TRANSIT')
        break
      case 'IN_TRANSIT':
        setTargetStatus('DELIVERED')
        break
      case 'DELIVERED':
        setTargetStatus('COMPLETED')
        break
      default:
        setTargetStatus('COMPLETED')
    }
  }

  const handleSubmitStatusUpdate = async () => {
    if (!updatingTx) return
    setActionLoading(true)
    setActionError(null)

    const payload: UpdateTransactionStatusRequest = {
      status: targetStatus,
      reason: statusReason.trim() ? statusReason.trim() : undefined,
      dispatch_notes: statusNotes.trim() ? statusNotes.trim() : undefined,
    }

    if (targetStatus === 'PICKED_UP') {
      payload.actual_pickup_at = new Date().toISOString()
    } else if (targetStatus === 'DELIVERED' || targetStatus === 'COMPLETED') {
      payload.actual_delivery_at = new Date().toISOString()
      if (actualDeliveredKg.trim()) {
        const val = parseFloat(actualDeliveredKg)
        if (!isNaN(val) && val >= 0) {
          payload.actual_delivered_kg = val
        }
      }
    } else if ((targetStatus === 'CANCELLED' || targetStatus === 'FAILED') && confirmedReturnedKg.trim()) {
      const val = parseFloat(confirmedReturnedKg)
      if (!isNaN(val) && val >= 0) {
        payload.confirmed_returned_kg = val
      }
    }

    try {
      const updated = await apiService.updateTransactionStatus(updatingTx.id, payload)
      setTransactions((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      setUpdatingTx(null)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } }
        setActionError(axErr.response?.data?.detail || 'Failed to update transaction status.')
      } else {
        setActionError('Network error updating status checkpoint.')
      }
    } finally {
      setActionLoading(false)
    }
  }

  const getStatusBadge = (status: TransactionStatus) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-cyan-500/15 px-2.5 py-0.5 text-xs font-semibold text-cyan-700 dark:text-cyan-400 border border-cyan-500/30">
            <Clock className="h-3 w-3" />
            Approved
          </span>
        )
      case 'PICKUP_SCHEDULED':
      case 'SCHEDULED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/15 px-2.5 py-0.5 text-xs font-semibold text-blue-700 dark:text-blue-400 border border-blue-500/30">
            <Calendar className="h-3 w-3" />
            Pickup Scheduled
          </span>
        )
      case 'PICKED_UP':
      case 'DISPATCHED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/15 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 dark:text-indigo-400 border border-indigo-500/30">
            <Truck className="h-3 w-3" />
            Picked Up
          </span>
        )
      case 'IN_TRANSIT':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-700 dark:text-amber-400 border border-amber-500/30">
            <Truck className="h-3 w-3 animate-pulse" />
            In Transit
          </span>
        )
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-teal-500/15 px-2.5 py-0.5 text-xs font-semibold text-teal-700 dark:text-teal-400 border border-teal-500/30">
            <CheckCircle2 className="h-3 w-3" />
            Delivered
          </span>
        )
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </span>
        )
      case 'CANCELLED':
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2.5 py-0.5 text-xs font-semibold text-red-700 dark:text-red-400 border border-red-500/30">
            <XCircle className="h-3 w-3" />
            {status}
          </span>
        )
      default:
        return (
          <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold text-muted-foreground border border-border">
            {status}
          </span>
        )
    }
  }

  // Filter transactions
  const filtered = transactions.filter((tx) => {
    const matchesStatus =
      statusFilter === 'ALL'
        ? true
        : statusFilter === 'ACTIVE'
        ? ['APPROVED', 'PICKUP_SCHEDULED', 'SCHEDULED', 'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT'].includes(tx.status)
        : statusFilter === 'COMPLETED'
        ? ['DELIVERED', 'COMPLETED'].includes(tx.status)
        : statusFilter === 'TERMINATED'
        ? ['CANCELLED', 'FAILED'].includes(tx.status)
        : tx.status === statusFilter

    const matchesSearch =
      searchQuery.trim() === ''
        ? true
        : tx.tracking_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tx.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          tx.items.some(
            (i) =>
              i.item_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
              i.supplier_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
              i.receiver_name.toLowerCase().includes(searchQuery.toLowerCase())
          )

    return matchesStatus && matchesSearch
  })

  // KPI calculations
  const totalKg = transactions.reduce((sum, tx) => sum + tx.total_allocated_kg, 0)
  const activeCount = transactions.filter((tx) =>
    ['APPROVED', 'PICKUP_SCHEDULED', 'SCHEDULED', 'DISPATCHED', 'PICKED_UP', 'IN_TRANSIT'].includes(tx.status)
  ).length
  const completedCount = transactions.filter((tx) => ['DELIVERED', 'COMPLETED'].includes(tx.status)).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Truck className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight">
              Redistribution Dispatch & Transaction Tracker
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Human-controlled custody chain tracking approved allocation proposals and physical food dispatch milestones.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTransactions}
            disabled={loading}
            className="gap-2 text-xs"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Link to="/coordinator/optimization">
            <Button size="sm" className="gap-2 text-xs font-semibold">
              <ExternalLink className="h-3.5 w-3.5" />
              Optimization Engine
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="text-xs text-muted-foreground font-medium mb-1">Total Transactions</div>
          <div className="text-2xl font-black font-mono text-foreground">{transactions.length}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Committed human approvals</div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between text-xs text-muted-foreground font-medium mb-1">
            <span>Salvaged Volume</span>
            <Scale className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-600 dark:text-emerald-400">
            {totalKg.toFixed(1)}
            <span className="text-xs font-normal text-muted-foreground ml-1">kg</span>
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Locked in custody</div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="text-xs text-muted-foreground font-medium mb-1">Active Dispatches</div>
          <div className="text-2xl font-black font-mono text-amber-600 dark:text-amber-400">
            {activeCount}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">En route or scheduled</div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="text-xs text-muted-foreground font-medium mb-1">Completed Deliveries</div>
          <div className="text-2xl font-black font-mono text-cyan-600 dark:text-cyan-400">
            {completedCount}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Successfully completed</div>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 text-xs">
          {['ALL', 'ACTIVE', 'COMPLETED', 'TERMINATED'].map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`rounded-lg px-3 py-1.5 font-semibold transition-colors ${
                statusFilter === f
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'bg-muted/60 text-muted-foreground hover:bg-muted'
              }`}
            >
              {f === 'ALL'
                ? 'All Transactions'
                : f === 'ACTIVE'
                ? 'Active Pipelines'
                : f === 'COMPLETED'
                ? 'Completed'
                : 'Cancelled / Failed'}
            </button>
          ))}
        </div>

        <div className="relative min-w-[240px]">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search tracking code, item, facility..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-input bg-background pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Transactions List */}
      {loading ? (
        <div className="text-center py-16 text-muted-foreground text-sm">
          <div className="inline-block animate-spin mb-3">
            <Truck className="h-8 w-8 text-primary" />
          </div>
          <div>Loading custody records...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border p-12 text-center space-y-3">
          <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Truck className="h-6 w-6" />
          </div>
          <div className="font-semibold text-foreground">No Transactions Found</div>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            {searchQuery
              ? 'No transaction matches your search filter.'
              : 'Approve an allocation proposal in the Optimization Engine to generate a tracked redistribution transaction.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((tx) => {
            const isExpanded = expandedTxId === tx.id
            const canExecute = tx.status === 'APPROVED'
            const canUpdate = !['COMPLETED', 'CANCELLED', 'FAILED'].includes(tx.status)

            return (
              <div
                key={tx.id}
                className="rounded-xl border border-border bg-card shadow-sm hover:border-primary/30 transition-all overflow-hidden"
              >
                {/* Transaction Header Card */}
                <div className="p-4 sm:p-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm sm:text-base text-foreground">
                          {tx.tracking_code}
                        </span>
                        <button
                          onClick={() => copyToClipboard(tx.tracking_code)}
                          className="text-muted-foreground hover:text-foreground transition-colors p-1"
                          title="Copy tracking code"
                        >
                          {copiedCode === tx.tracking_code ? (
                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </button>
                        {getStatusBadge(tx.status)}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
                        <span>
                          Created: {new Date(tx.created_at).toLocaleString()}
                        </span>
                        {tx.scheduled_pickup_at && (
                          <span>
                            Scheduled Pickup: {new Date(tx.scheduled_pickup_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                        {tx.actual_delivery_at && (
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                            Delivered: {new Date(tx.actual_delivery_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {canExecute && (
                        <Button
                          size="sm"
                          onClick={() => handleExecuteDispatch(tx.id)}
                          disabled={actionLoading}
                          className="gap-1.5 text-xs font-semibold bg-primary hover:bg-primary/90"
                        >
                          <Send className="h-3.5 w-3.5" />
                          Dispatch / Schedule
                        </Button>
                      )}

                      {canUpdate && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenStatusModal(tx)}
                          className="gap-1.5 text-xs font-semibold"
                        >
                          <Truck className="h-3.5 w-3.5" />
                          Update Checkpoint
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpandedTxId(isExpanded ? null : tx.id)}
                        className="gap-1 text-xs text-muted-foreground"
                      >
                        {isExpanded ? (
                          <>
                            Less Details <ChevronUp className="h-3.5 w-3.5" />
                          </>
                        ) : (
                          <>
                            {tx.items_count} items &bull; {tx.total_allocated_kg.toFixed(1)} kg{' '}
                            <ChevronDown className="h-3.5 w-3.5" />
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {tx.dispatch_notes && (
                    <div className="mt-3 text-xs bg-muted/40 p-2.5 rounded-lg border border-border text-muted-foreground flex items-start gap-2">
                      <FileText className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                      <span>{tx.dispatch_notes}</span>
                    </div>
                  )}
                </div>

                {/* Expanded Details: Items & Status Timeline */}
                {isExpanded && (
                  <div className="border-t border-border bg-muted/15 p-4 sm:p-5 space-y-5">
                    {/* Items table */}
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                        <Scale className="h-3.5 w-3.5" />
                        Allocated Food Flow Items
                      </div>
                      <div className="overflow-x-auto rounded-lg border border-border bg-card">
                        <table className="w-full text-left text-xs">
                          <thead className="border-b border-border bg-muted/40 text-muted-foreground font-medium">
                            <tr>
                              <th className="px-3 py-2">Item / Category</th>
                              <th className="px-3 py-2">Quantity</th>
                              <th className="px-3 py-2">Supplier Facility</th>
                              <th className="px-3 py-2">Receiver Org</th>
                              <th className="px-3 py-2">Est. Transit</th>
                              <th className="px-3 py-2">Urgency</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {tx.items.map((item) => (
                              <tr key={item.item_id} className="hover:bg-muted/20">
                                <td className="px-3 py-2.5 font-medium text-foreground">
                                  {item.item_name}
                                  <span className="block text-[10px] text-muted-foreground">
                                    {item.food_category}
                                  </span>
                                </td>
                                <td className="px-3 py-2.5 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                                  {item.allocated_quantity_kg.toFixed(1)} kg
                                </td>
                                <td className="px-3 py-2.5">
                                  <div className="flex items-center gap-1">
                                    <Building2 className="h-3 w-3 text-muted-foreground" />
                                    <span>{item.supplier_name}</span>
                                  </div>
                                </td>
                                <td className="px-3 py-2.5 font-medium text-primary">
                                  {item.receiver_name}
                                </td>
                                <td className="px-3 py-2.5 text-muted-foreground font-mono">
                                  {item.estimated_distance_km.toFixed(1)} km (~{item.estimated_transit_minutes}m)
                                </td>
                                <td className="px-3 py-2.5">
                                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                                    {item.urgency_at_allocation}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Timeline History */}
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                        <History className="h-3.5 w-3.5" />
                        Custody Status History & Audit Trail
                      </div>
                      <div className="space-y-2">
                        {tx.status_history.map((h, idx) => (
                          <div
                            key={h.id || idx}
                            className="flex items-start gap-3 text-xs bg-card p-2.5 rounded-lg border border-border"
                          >
                            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary font-bold text-[10px] shrink-0 mt-0.5">
                              {idx + 1}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-foreground">
                                  {h.new_status}
                                </span>
                                {h.previous_status && (
                                  <span className="text-[10px] text-muted-foreground">
                                    (from {h.previous_status})
                                  </span>
                                )}
                                <span className="text-[10px] text-muted-foreground ml-auto">
                                  {new Date(h.changed_at).toLocaleString()}
                                </span>
                              </div>
                              {h.reason && (
                                <p className="text-[11px] text-muted-foreground mt-0.5">
                                  {h.reason}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Modal Dialog for Updating Status Checkpoint */}
      {updatingTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="font-extrabold text-base text-foreground">
                  Update Checkpoint Status
                </h3>
                <p className="text-xs font-mono text-muted-foreground">
                  {updatingTx.tracking_code}
                </p>
              </div>
              <button
                onClick={() => setUpdatingTx(null)}
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
              <div>
                <label className="block font-medium text-foreground mb-1">
                  Target Status Checkpoint
                </label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value as TransactionStatus)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="PICKUP_SCHEDULED">PICKUP_SCHEDULED — Dispatch assigned</option>
                  <option value="PICKED_UP">PICKED_UP — Food loaded by driver</option>
                  <option value="IN_TRANSIT">IN_TRANSIT — Vehicle en route to receiver</option>
                  <option value="DELIVERED">DELIVERED — Arrived at receiver site</option>
                  <option value="COMPLETED">COMPLETED — Accepted and logged</option>
                  <option value="FAILED">FAILED — Transport breakdown or rejected</option>
                  <option value="CANCELLED">CANCELLED — Revert allocations</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">
                  Checkpoint Reason / Log Note (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Van en route via highway, delay 10 mins"
                  value={statusReason}
                  onChange={(e) => setStatusReason(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">
                  Updated Gate / Dispatch Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Loading dock instructions, receiver contact..."
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                />
              </div>

              {(targetStatus === 'CANCELLED' || targetStatus === 'FAILED') && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-2.5 space-y-1.5">
                  <label className="block font-semibold text-foreground">
                    Confirmed Physically Returned Quantity (kg)
                  </label>
                  <p className="text-[11px] text-muted-foreground">
                    Post-pickup inventory restoration requires physical custody verification. Only confirmed returned amounts will be credited back to supplier stock. Leave blank or 0 if spoiled/discarded.
                  </p>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={confirmedReturnedKg}
                    onChange={(e) => setConfirmedReturnedKg(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  />
                </div>
              )}

              {(targetStatus === 'DELIVERED' || targetStatus === 'COMPLETED') && (
                <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-2.5 space-y-1.5">
                  <label className="block font-semibold text-foreground">
                    Actual Delivered Quantity (kg)
                  </label>
                  <p className="text-[11px] text-muted-foreground">
                    If partial delivery occurred, enter the exact verified quantity delivered to the receiver. Outstanding demand will be adjusted accordingly. Leave blank if 100% of {updatingTx.total_allocated_kg} kg was delivered.
                  </p>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={updatingTx.total_allocated_kg}
                    placeholder={`${updatingTx.total_allocated_kg}`}
                    value={actualDeliveredKg}
                    onChange={(e) => setActualDeliveredKg(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring font-mono"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setUpdatingTx(null)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitStatusUpdate}
                disabled={actionLoading}
                className="gap-2 font-semibold"
              >
                {actionLoading ? 'Updating Checkpoint...' : 'Confirm Status Update'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
