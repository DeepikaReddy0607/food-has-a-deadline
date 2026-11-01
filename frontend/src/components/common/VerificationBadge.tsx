import React from 'react'
import { ShieldCheck, Clock, AlertCircle, XCircle } from 'lucide-react'
import type { VerificationStatus } from '@/types'

interface VerificationBadgeProps {
  status?: VerificationStatus | string | null
  showLabel?: boolean
  className?: string
  size?: 'sm' | 'md'
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  status = 'PENDING_VERIFICATION',
  showLabel = true,
  className = '',
  size = 'md',
}) => {
  const normStatus = (status || 'PENDING_VERIFICATION').toUpperCase()

  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5 gap-1' : 'text-xs px-2 py-0.5 gap-1.5'
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'

  switch (normStatus) {
    case 'VERIFIED':
      return (
        <span
          className={`inline-flex items-center font-medium rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/60 ${sizeClasses} ${className}`}
          title="Verified Organization - Identity and operating credentials verified by FHD Coordinator"
        >
          <ShieldCheck className={`${iconSize} text-emerald-600 dark:text-emerald-400 shrink-0`} />
          {showLabel && <span>Verified Organization</span>}
        </span>
      )
    case 'DOCUMENTS_SUBMITTED':
      return (
        <span
          className={`inline-flex items-center font-medium rounded-full bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/60 ${sizeClasses} ${className}`}
          title="Documents Submitted - Pending review by FHD Coordinator"
        >
          <Clock className={`${iconSize} text-blue-600 dark:text-blue-400 shrink-0`} />
          {showLabel && <span>Documents Submitted</span>}
        </span>
      )
    case 'REJECTED':
      return (
        <span
          className={`inline-flex items-center font-medium rounded-full bg-red-100 text-red-800 border border-red-200 dark:bg-red-950/60 dark:text-red-300 dark:border-red-800/60 ${sizeClasses} ${className}`}
          title="Verification Rejected - Documentation could not be verified"
        >
          <XCircle className={`${iconSize} text-red-600 dark:text-red-400 shrink-0`} />
          {showLabel && <span>Verification Rejected</span>}
        </span>
      )
    case 'PENDING_VERIFICATION':
    default:
      return (
        <span
          className={`inline-flex items-center font-medium rounded-full bg-amber-100 text-amber-800 border border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/60 ${sizeClasses} ${className}`}
          title="Pending Verification - Registration requires verification documents for full network participation"
        >
          <AlertCircle className={`${iconSize} text-amber-600 dark:text-amber-400 shrink-0`} />
          {showLabel && <span>Pending Verification</span>}
        </span>
      )
  }
}
