import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { SurplusListing } from '@/types'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Loader2,
  Save,
  Thermometer,
  Truck,
  Utensils,
} from 'lucide-react'

export const EditSurplusListing: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [listing, setListing] = useState<SurplusListing | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Editable form fields
  const [itemName, setItemName] = useState('')
  const [description, setDescription] = useState('')
  const [remainingQuantityKg, setRemainingQuantityKg] = useState('')
  const [estimatedDeadline, setEstimatedDeadline] = useState('')
  const [foodCondition, setFoodCondition] = useState('GOOD')
  const [storageCondition, setStorageCondition] = useState('AMBIENT')
  const [pickupAddress, setPickupAddress] = useState('')
  const [handlingInstructions, setHandlingInstructions] = useState('')

  useEffect(() => {
    if (!id) return
    const fetch = async () => {
      setLoading(true)
      try {
        const data = await apiService.getSurplusListing(id)
        setListing(data)
        setItemName(data.item_name)
        setDescription(data.description || '')
        setRemainingQuantityKg(String(data.remaining_quantity_kg))
        setFoodCondition(data.food_condition)
        setStorageCondition(data.storage_condition)
        setPickupAddress(data.pickup_address || '')
        setHandlingInstructions(data.handling_instructions || '')

        // Format deadline for datetime-local
        const dl = new Date(data.estimated_deadline)
        const dlIso = new Date(dl.getTime() - dl.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
        setEstimatedDeadline(dlIso)
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load listing.')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !listing) return
    setError(null)

    const remaining = parseFloat(remainingQuantityKg)
    if (isNaN(remaining) || remaining < 0) {
      setError('Remaining quantity must be a non-negative number.')
      return
    }

    const initial = Number(listing.initial_quantity_kg)
    if (remaining > initial) {
      setError(`Remaining quantity cannot exceed the initial registered quantity (${initial} kg).`)
      return
    }

    if (!estimatedDeadline) {
      setError('Estimated usable deadline timestamp is required.')
      return
    }

    const deadlineTime = new Date(estimatedDeadline).getTime()
    const prepTime = new Date(listing.harvest_or_prep_date).getTime()
    const nowTime = Date.now()

    if (deadlineTime <= prepTime) {
      setError('Estimated usable deadline must be after harvest or preparation date.')
      return
    }

    if (deadlineTime <= nowTime) {
      setError('Estimated usable deadline cannot be in the past.')
      return
    }

    setSaving(true)
    try {
      await apiService.updateSurplusListing(id, {
        item_name: itemName.trim(),
        description: description.trim() || undefined,
        remaining_quantity_kg: remaining,
        estimated_deadline: new Date(estimatedDeadline).toISOString(),
        food_condition: foodCondition,
        storage_condition: storageCondition,
        pickup_address: pickupAddress.trim() || undefined,
        handling_instructions: handlingInstructions.trim() || undefined,
      })

      navigate(`/supplier/inventory/${id}`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to update surplus listing.'
      )
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error && !listing) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-center space-y-3">
        <AlertCircle className="h-8 w-8 mx-auto" />
        <h3 className="font-semibold">{error}</h3>
        <Link to="/supplier/inventory">
          <Button variant="outline" size="sm">
            Back to Inventory
          </Button>
        </Link>
      </div>
    )
  }

  if (listing && (listing.status === 'CANCELLED' || listing.status === 'DEPLETED' || listing.status === 'EXPIRED')) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 rounded-xl border border-border bg-card text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold">Listing Is Closed</h2>
        <p className="text-sm text-muted-foreground">
          This surplus listing currently has status <strong>{listing.status}</strong> and cannot be modified.
        </p>
        <Link to={`/supplier/inventory/${listing.id}`}>
          <Button variant="outline" size="sm" className="mt-2">
            View Listing Details
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/supplier/inventory/${id}`}>
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Edit Surplus Food Batch</h1>
          <p className="text-sm text-muted-foreground">
            Update remaining stock, extend or adjust cut-off deadline, or update storage requirements.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg border border-destructive/30 bg-destructive/10 text-destructive flex items-center gap-3 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Utensils className="h-4 w-4 text-primary" />
            Basic Information
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Item Name / Batch Title <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              required
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Quantities & Deadline */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Remaining Quantity & Usable Deadline
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Remaining Stock (kg) <span className="text-destructive">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max={listing ? Number(listing.initial_quantity_kg) : undefined}
                required
                value={remainingQuantityKg}
                onChange={(e) => setRemainingQuantityKg(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span className="text-[11px] text-muted-foreground block">
                Initial batch was {listing?.initial_quantity_kg} kg. Setting to 0 marks it as DEPLETED.
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-destructive font-bold">
                Estimated Usable Deadline <span className="text-destructive">*</span>
              </label>
              <input
                type="datetime-local"
                required
                value={estimatedDeadline}
                onChange={(e) => setEstimatedDeadline(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-destructive/50 bg-background text-sm focus:outline-none focus:ring-2 focus:ring-destructive font-medium"
              />
            </div>
          </div>
        </div>

        {/* Condition & Storage */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Thermometer className="h-4 w-4 text-primary" />
            Quality & Storage Conditions
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Food Condition
              </label>
              <select
                value={foodCondition}
                onChange={(e) => setFoodCondition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="EXCELLENT">EXCELLENT</option>
                <option value="GOOD">GOOD</option>
                <option value="FAIR">FAIR</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Required Storage Environment
              </label>
              <select
                value={storageCondition}
                onChange={(e) => setStorageCondition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="AMBIENT">AMBIENT</option>
                <option value="REFRIGERATED">REFRIGERATED</option>
                <option value="FROZEN">FROZEN</option>
              </select>
            </div>
          </div>
        </div>

        {/* Logistics & Handling */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Truck className="h-4 w-4 text-primary" />
            Logistics & Instructions
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Pickup Address
            </label>
            <input
              type="text"
              value={pickupAddress}
              onChange={(e) => setPickupAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Handling Instructions
            </label>
            <textarea
              rows={2}
              value={handlingInstructions}
              onChange={(e) => setHandlingInstructions(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link to={`/supplier/inventory/${id}`}>
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={saving} className="min-w-[140px]">
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
