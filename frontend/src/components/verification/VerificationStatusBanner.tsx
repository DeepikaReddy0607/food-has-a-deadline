import React, { useState, useEffect } from 'react'
import {
  ShieldCheck,
  Clock,
  AlertCircle,
  XCircle,
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  X,
} from 'lucide-react'
import { apiService } from '@/services/api'
import type { OrganizationVerificationStatusResponse } from '@/types'
import { Button } from '@/components/ui/button'

interface VerificationStatusBannerProps {
  onStatusLoaded?: (status: OrganizationVerificationStatusResponse) => void
}

export const VerificationStatusBanner: React.FC<VerificationStatusBannerProps> = ({
  onStatusLoaded,
}) => {
  const [statusData, setStatusData] = useState<OrganizationVerificationStatusResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [modalOpen, setModalOpen] = useState<boolean>(false)

  // Form states
  const [repName, setRepName] = useState<string>('')
  const [licenseNumber, setLicenseNumber] = useState<string>('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const fetchStatus = async () => {
    try {
      setLoading(true)
      const data = await apiService.getVerificationStatus()
      setStatusData(data)
      if (onStatusLoaded) {
        onStatusLoaded(data)
      }
      if (data.representative_name) setRepName(data.representative_name)
      if (data.license_number) setLicenseNumber(data.license_number)
    } catch (e) {
      console.warn('Could not load verification status', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      // Validate file size: 5MB
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg('Document file size must not exceed 5 MB.')
        setSelectedFile(null)
        return
      }
      // Validate file extension
      const ext = file.name.split('.').pop()?.toLowerCase()
      if (!ext || !['pdf', 'jpg', 'jpeg', 'png'].includes(ext)) {
        setErrorMsg('Only PDF, JPG, or PNG files are supported.')
        setSelectedFile(null)
        return
      }
      setErrorMsg(null)
      setSelectedFile(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repName.trim()) {
      setErrorMsg('Representative name is required.')
      return
    }
    if (!selectedFile && !statusData?.has_document) {
      setErrorMsg('Please select a verification document (PDF, JPG, or PNG).')
      return
    }

    try {
      setSubmitting(true)
      setErrorMsg(null)
      const formData = new FormData()
      formData.append('representative_name', repName.trim())
      if (licenseNumber.trim()) {
        formData.append('license_number', licenseNumber.trim())
      }
      if (selectedFile) {
        formData.append('document', selectedFile)
      }

      const updated = await apiService.submitVerification(formData)
      setStatusData(updated)
      setSuccessMsg('Verification document submitted successfully! A coordinator will review it shortly.')
      setTimeout(() => {
        setModalOpen(false)
        setSuccessMsg(null)
      }, 2000)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setErrorMsg(error.response?.data?.detail || 'Failed to submit verification document. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading || !statusData) {
    return null
  }

  // If verified, show a clean, reassuring badge banner
  if (statusData.verification_status === 'VERIFIED') {
    return (
      <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3.5 dark:border-emerald-800/50 dark:bg-emerald-950/20">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div className="rounded-full bg-emerald-100 p-1.5 dark:bg-emerald-900/40">
              <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <span className="text-xs font-semibold text-emerald-900 dark:text-emerald-200">
                Verified Organization Network Partner
              </span>
              <p className="text-[11px] text-emerald-700 dark:text-emerald-400">
                {statusData.org_name || 'Your organization'} is certified for live matching, automated redistribution proposals, and dispatch operations.
              </p>
            </div>
          </div>
          {statusData.license_number && (
            <span className="text-[11px] font-mono bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 px-2 py-0.5 rounded">
              Lic: {statusData.license_number}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      {statusData.verification_status === 'PENDING_VERIFICATION' && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/60 dark:bg-amber-950/30">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-amber-100 p-2 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400 shrink-0 mt-0.5">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-amber-900 dark:text-amber-200 uppercase tracking-wide">
                  Organization Verification Required
                </h4>
                <p className="mt-0.5 text-xs text-amber-800 dark:text-amber-300">
                  Your organization is currently <strong>Pending Verification</strong>. Unverified organizations cannot be paired in candidate matching or participate in allocation proposals.
                </p>
                <p className="mt-1 text-[11px] text-amber-700 dark:text-amber-400">
                  Submit an official registration certificate, food safety certificate, or 501(c)(3) documentation to activate your organization.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => {
                setErrorMsg(null)
                setSuccessMsg(null)
                setModalOpen(true)
              }}
              className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium gap-1.5 shadow-sm"
            >
              <Upload className="h-3.5 w-3.5" />
              Submit Documents
            </Button>
          </div>
        </div>
      )}

      {statusData.verification_status === 'DOCUMENTS_SUBMITTED' && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800/60 dark:bg-blue-950/30">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-blue-100 p-2 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400 shrink-0 mt-0.5">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-blue-900 dark:text-blue-200 uppercase tracking-wide">
                  Verification Documents Under Review
                </h4>
                <p className="mt-0.5 text-xs text-blue-800 dark:text-blue-300">
                  We have received your verification submission
                  {statusData.document_name && (
                    <span className="font-semibold"> ({statusData.document_name})</span>
                  )}
                  . An FHD coordinator will review your credentials shortly.
                </p>
                <p className="mt-1 text-[11px] text-blue-700 dark:text-blue-400">
                  Representative: {statusData.representative_name || 'N/A'} {statusData.license_number ? `• License: ${statusData.license_number}` : ''}
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setErrorMsg(null)
                setSuccessMsg(null)
                setModalOpen(true)
              }}
              className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:text-blue-300 text-xs gap-1.5"
            >
              <Upload className="h-3.5 w-3.5" />
              Update Documents
            </Button>
          </div>
        </div>
      )}

      {statusData.verification_status === 'REJECTED' && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800/60 dark:bg-red-950/30">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-red-100 p-2 text-red-600 dark:bg-red-900/40 dark:text-red-400 shrink-0 mt-0.5">
                <XCircle className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-red-900 dark:text-red-200 uppercase tracking-wide">
                  Verification Rejected
                </h4>
                <p className="mt-0.5 text-xs text-red-800 dark:text-red-300">
                  Your organization verification could not be approved by the coordinator.
                </p>
                {statusData.rejection_reason && (
                  <div className="mt-2 rounded bg-white/70 dark:bg-black/30 p-2.5 border border-red-200 dark:border-red-900 text-xs text-red-900 dark:text-red-200">
                    <strong>Reason for rejection:</strong> {statusData.rejection_reason}
                  </div>
                )}
                <p className="mt-1.5 text-[11px] text-red-700 dark:text-red-400">
                  Publishing listings and demand requests is paused until valid operating documentation is submitted.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => {
                setErrorMsg(null)
                setSuccessMsg(null)
                setModalOpen(true)
              }}
              className="bg-red-600 hover:bg-red-700 text-white text-xs font-medium gap-1.5 shadow-sm"
            >
              <Upload className="h-3.5 w-3.5" />
              Re-submit Documentation
            </Button>
          </div>
        </div>
      )}

      {/* Submission Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-xl bg-card border border-border p-6 shadow-xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setModalOpen(false)}
              className="absolute right-4 top-4 text-muted-foreground hover:text-foreground p-1 rounded-md"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">
                  Organization Verification Submission
                </h3>
                <p className="text-xs text-muted-foreground">
                  Provide verifiable organization credentials to join the FHD Redistribution Network.
                </p>
              </div>
            </div>

            {errorMsg && (
              <div className="mb-4 rounded-md bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {successMsg && (
              <div className="mb-4 rounded-md bg-emerald-50 border border-emerald-200 p-3 text-xs text-emerald-800 dark:bg-emerald-950/40 dark:border-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                <span>{successMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Representative Name *
                </label>
                <input
                  type="text"
                  required
                  value={repName}
                  onChange={(e) => setRepName(e.target.value)}
                  placeholder="e.g., Dr. Jane Smith, Operations Director"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Registration / License / 501(c)(3) Number
                </label>
                <input
                  type="text"
                  value={licenseNumber}
                  onChange={(e) => setLicenseNumber(e.target.value)}
                  placeholder="e.g., FSSAI-100200300400 / 501C3-994821 / NGO-DARPAN-CA-12"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Verification Document (PDF, JPG, PNG &le; 5 MB) *
                </label>
                <div className="mt-1 flex justify-center rounded-lg border border-dashed border-border px-6 py-6 bg-muted/20">
                  <div className="text-center">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
                    <div className="mt-2 flex text-xs leading-6 text-muted-foreground justify-center">
                      <label className="relative cursor-pointer rounded-md font-semibold text-primary hover:underline">
                        <span>Upload a document</span>
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png"
                          onChange={handleFileChange}
                          className="sr-only"
                        />
                      </label>
                      <p className="pl-1">or drag and drop</p>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Organization certificate, food safety certificate, or NGO registration
                    </p>
                    {selectedFile && (
                      <p className="mt-2 text-xs font-semibold text-primary flex items-center justify-center gap-1">
                        <FileText className="h-3.5 w-3.5" />
                        Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(0)} KB)
                      </p>
                    )}
                    {!selectedFile && statusData?.document_name && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Current file: {statusData.document_name}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2 border-t border-border mt-4">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setModalOpen(false)}
                  disabled={submitting}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={submitting}
                  className="text-xs gap-1.5"
                >
                  {submitting ? (
                    <>
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="h-3.5 w-3.5" />
                      Submit for Verification
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
