import React, { useState, useEffect } from 'react'
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  FileText,
  Search,
  Building2,
  HeartHandshake,
  Clock,
  AlertCircle,
  AlertTriangle,
  X,
  ExternalLink,
} from 'lucide-react'
import { apiService } from '@/services/api'
import type { OrganizationVerificationItem } from '@/types'
import { VerificationBadge } from '@/components/common/VerificationBadge'
import { Button } from '@/components/ui/button'

export const OrganizationVerificationsPage: React.FC = () => {
  const [items, setItems] = useState<OrganizationVerificationItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL')
  const [orgTypeFilter, setOrgTypeFilter] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Action states
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Reject Modal state
  const [rejectModalItem, setRejectModalItem] = useState<OrganizationVerificationItem | null>(null)
  const [rejectReason, setRejectReason] = useState<string>('')
  const [rejecting, setRejecting] = useState<boolean>(false)

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiService.listVerifications()
      setItems(data)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail || 'Failed to load organization verification requests.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleApprove = async (item: OrganizationVerificationItem) => {
    try {
      setActionLoadingId(item.org_id)
      setActionError(null)
      setActionSuccess(null)
      const updated = await apiService.approveVerification(item.org_type, item.org_id)
      setItems((prev) =>
        prev.map((i) => (i.org_id === item.org_id ? updated : i))
      )
      setActionSuccess(`Successfully verified organization "${item.org_name}".`)
      setTimeout(() => setActionSuccess(null), 4000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setActionError(e.response?.data?.detail || 'Failed to approve organization verification.')
    } finally {
      setActionLoadingId(null)
    }
  }

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rejectModalItem) return
    if (!rejectReason.trim() || rejectReason.trim().length < 3) {
      setActionError('A rejection reason of at least 3 characters is mandatory.')
      return
    }

    try {
      setRejecting(true)
      setActionError(null)
      const updated = await apiService.rejectVerification(
        rejectModalItem.org_type,
        rejectModalItem.org_id,
        rejectReason.trim()
      )
      setItems((prev) =>
        prev.map((i) => (i.org_id === rejectModalItem.org_id ? updated : i))
      )
      setActionSuccess(`Organization "${rejectModalItem.org_name}" rejected with reason.`)
      setRejectModalItem(null)
      setRejectReason('')
      setTimeout(() => setActionSuccess(null), 4000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setActionError(e.response?.data?.detail || 'Failed to reject verification.')
    } finally {
      setRejecting(false)
    }
  }

  // Filter items
  const filteredItems = items.filter((item) => {
    if (statusFilter !== 'ALL' && item.verification_status !== statusFilter) {
      return false
    }
    if (orgTypeFilter !== 'ALL' && item.org_type !== orgTypeFilter) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchName = item.org_name.toLowerCase().includes(q)
      const matchEmail = item.email.toLowerCase().includes(q)
      const matchLic = item.license_number?.toLowerCase().includes(q) || false
      const matchRep = item.representative_name?.toLowerCase().includes(q) || false
      return matchName || matchEmail || matchLic || matchRep
    }
    return true
  })

  // Counters
  const countSubmitted = items.filter((i) => i.verification_status === 'DOCUMENTS_SUBMITTED').length
  const countPending = items.filter((i) => i.verification_status === 'PENDING_VERIFICATION').length
  const countVerified = items.filter((i) => i.verification_status === 'VERIFIED').length
  const countRejected = items.filter((i) => i.verification_status === 'REJECTED').length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-7 w-7 text-primary" />
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
              Organization Verification Center
            </h1>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Manage organization credentials, review submitted legal documents, and approve network redistribution participants.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadData}
          disabled={loading}
          className="text-xs self-start md:self-auto"
        >
          {loading ? 'Refreshing...' : 'Refresh Records'}
        </Button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div
          onClick={() => setStatusFilter('DOCUMENTS_SUBMITTED')}
          className={`cursor-pointer rounded-xl border p-4 transition-all shadow-sm ${
            statusFilter === 'DOCUMENTS_SUBMITTED'
              ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20'
              : 'border-border bg-card hover:border-blue-300'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 font-medium">
            <span>Pending Review</span>
            <Clock className="h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-black text-foreground">{countSubmitted}</div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">Documents submitted</div>
        </div>

        <div
          onClick={() => setStatusFilter('PENDING_VERIFICATION')}
          className={`cursor-pointer rounded-xl border p-4 transition-all shadow-sm ${
            statusFilter === 'PENDING_VERIFICATION'
              ? 'border-amber-500 bg-amber-50/50 dark:bg-amber-950/20'
              : 'border-border bg-card hover:border-amber-300'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-amber-600 dark:text-amber-400 font-medium">
            <span>Pending Documents</span>
            <AlertCircle className="h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-black text-foreground">{countPending}</div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">No docs submitted yet</div>
        </div>

        <div
          onClick={() => setStatusFilter('VERIFIED')}
          className={`cursor-pointer rounded-xl border p-4 transition-all shadow-sm ${
            statusFilter === 'VERIFIED'
              ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20'
              : 'border-border bg-card hover:border-emerald-300'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            <span>Verified Organizations</span>
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-black text-foreground">{countVerified}</div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">Active in redistribution</div>
        </div>

        <div
          onClick={() => setStatusFilter('REJECTED')}
          className={`cursor-pointer rounded-xl border p-4 transition-all shadow-sm ${
            statusFilter === 'REJECTED'
              ? 'border-red-500 bg-red-50/50 dark:bg-red-950/20'
              : 'border-border bg-card hover:border-red-300'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-red-600 dark:text-red-400 font-medium">
            <span>Rejected</span>
            <XCircle className="h-4 w-4" />
          </div>
          <div className="mt-2 text-2xl font-black text-foreground">{countRejected}</div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">Blocked from operations</div>
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800 dark:bg-emerald-950/40 dark:border-emerald-800 dark:text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)}>
            <X className="h-3.5 w-3.5 text-emerald-600" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap w-full md:w-auto">
          {/* Status Tabs */}
          <div className="flex items-center bg-muted/60 p-1 rounded-lg text-xs font-medium">
            {['ALL', 'DOCUMENTS_SUBMITTED', 'PENDING_VERIFICATION', 'VERIFIED', 'REJECTED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md transition-all ${
                  statusFilter === st
                    ? 'bg-card text-foreground shadow-xs font-bold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {st === 'ALL'
                  ? 'All'
                  : st === 'DOCUMENTS_SUBMITTED'
                  ? `Review (${countSubmitted})`
                  : st === 'PENDING_VERIFICATION'
                  ? 'Pending'
                  : st === 'VERIFIED'
                  ? 'Verified'
                  : 'Rejected'}
              </button>
            ))}
          </div>

          {/* Org Type Selector */}
          <select
            value={orgTypeFilter}
            onChange={(e) => setOrgTypeFilter(e.target.value)}
            className="rounded-lg border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="ALL">All Types</option>
            <option value="SUPPLIER">Suppliers Only</option>
            <option value="RECEIVER">Receivers Only</option>
          </select>
        </div>

        {/* Search */}
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search organization or license..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-input bg-background pl-9 pr-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>

      {/* Verification Items List */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Loading verification records...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-xs text-destructive">{error}</div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-xs text-muted-foreground">
            No organizations match the selected criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 text-muted-foreground font-semibold border-b border-border">
                <tr>
                  <th className="py-3 px-4">Organization</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Credentials & License</th>
                  <th className="py-3 px-4">Verification Document</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredItems.map((item) => (
                  <tr key={item.org_id} className="hover:bg-muted/20 transition-colors">
                    {/* Organization Details */}
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-foreground text-sm">{item.org_name}</div>
                      <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                        <span>{item.email}</span>
                        {item.city && (
                          <>
                            <span>&bull;</span>
                            <span>{item.city}</span>
                          </>
                        )}
                      </div>
                    </td>

                    {/* Org Type */}
                    <td className="py-3.5 px-4">
                      {item.org_type === 'SUPPLIER' ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 dark:text-emerald-300">
                          <Building2 className="h-3.5 w-3.5" />
                          Supplier
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 font-semibold text-blue-700 dark:text-blue-300">
                          <HeartHandshake className="h-3.5 w-3.5" />
                          Receiver
                        </span>
                      )}
                    </td>

                    {/* Credentials */}
                    <td className="py-3.5 px-4">
                      {item.license_number ? (
                        <div className="font-mono text-xs font-medium text-foreground bg-muted/60 px-2 py-0.5 rounded inline-block">
                          {item.license_number}
                        </div>
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">Not provided</span>
                      )}
                      {item.representative_name && (
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          Rep: {item.representative_name}
                        </div>
                      )}
                    </td>

                    {/* Document */}
                    <td className="py-3.5 px-4">
                      {item.has_document ? (
                        <a
                          href={apiService.getVerificationDocumentUrl(item.org_type, item.org_id)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline bg-primary/10 px-2.5 py-1 rounded-md"
                        >
                          <FileText className="h-3.5 w-3.5" />
                          <span>{item.document_name || 'Download Doc'}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">No document</span>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col items-start gap-1">
                        <VerificationBadge status={item.verification_status} size="sm" />
                        {item.rejection_reason && (
                          <span
                            className="text-[10px] text-destructive max-w-[180px] truncate"
                            title={item.rejection_reason}
                          >
                            Reason: {item.rejection_reason}
                          </span>
                        )}
                        {item.verified_at && (
                          <span className="text-[10px] text-muted-foreground">
                            Verified: {new Date(item.verified_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {item.verification_status !== 'VERIFIED' && (
                          <Button
                            size="sm"
                            disabled={actionLoadingId === item.org_id}
                            onClick={() => handleApprove(item)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-7 px-2.5 gap-1"
                          >
                            <CheckCircle className="h-3 w-3" />
                            Approve
                          </Button>
                        )}
                        {item.verification_status !== 'REJECTED' && (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={actionLoadingId === item.org_id}
                            onClick={() => {
                              setRejectModalItem(item)
                              setRejectReason('')
                            }}
                            className="border-red-300 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 text-xs h-7 px-2.5 gap-1"
                          >
                            <XCircle className="h-3 w-3" />
                            Reject
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {rejectModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-xl bg-card border border-border p-6 shadow-xl relative">
            <button
              onClick={() => setRejectModalItem(null)}
              className="absolute right-4 top-4 text-muted-foreground hover:text-foreground p-1 rounded-md"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-2.5 text-destructive mb-3">
              <XCircle className="h-6 w-6" />
              <h3 className="text-base font-bold text-foreground">
                Reject Organization Verification
              </h3>
            </div>

            <p className="text-xs text-muted-foreground mb-4">
              Rejecting <strong>{rejectModalItem.org_name}</strong> will pause their ability to publish listings and participate in candidate matching. A specific reason is mandatory.
            </p>

            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Mandatory Rejection Reason *
                </label>
                <textarea
                  rows={3}
                  required
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain why verification failed (e.g., Unreadable document, expired business license, entity name mismatch)..."
                  className="w-full rounded-md border border-input bg-background p-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setRejectModalItem(null)}
                  disabled={rejecting}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  variant="destructive"
                  disabled={rejecting || rejectReason.trim().length < 3}
                  className="text-xs gap-1.5"
                >
                  {rejecting ? 'Rejecting...' : 'Confirm Rejection'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
