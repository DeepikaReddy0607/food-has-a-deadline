import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { DemandRequest } from '@/types'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Flame,
  Loader2,
  Save,
  ShieldCheck,
  Truck,
  Utensils,
} from 'lucide-react'

const DIETARY_OPTIONS = [
  'VEGETARIAN',
  'VEGAN',
  'GLUTEN_FREE',
  'DAIRY_FREE',
  'NUT_FREE',
  'HALAL',
  'KOSHER',
]

export const EditDemandRequest: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [demand, setDemand] = useState<DemandRequest | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Editable fields
  const [itemName, setItemName] = useState('')
  const [description, setDescription] = useState('')
  const [requestedQuantityKg, setRequestedQuantityKg] = useState('')
  const [requiredBy, setRequiredBy] = useState('')
  const [acceptableFoodCondition, setAcceptableFoodCondition] = useState('FAIR')
  const [dietaryRequirements, setDietaryRequirements] = useState<string[]>([])
  const [storageCapability, setStorageCapability] = useState('AMBIENT')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [handlingInstructions, setHandlingInstructions] = useState('')
  const [priorityWeight, setPriorityWeight] = useState(3)

  useEffect(() => {
    if (!id) return
    const fetch = async () => {
      setLoading(true)
      try {
        const data = await apiService.getDemandRequest(id)
        setDemand(data)
        setItemName(data.item_name || '')
        setDescription(data.description || '')
        setRequestedQuantityKg(String(data.requested_quantity_kg))
        setAcceptableFoodCondition(data.acceptable_food_condition || 'FAIR')
        setDietaryRequirements(data.dietary_requirements || [])
        setStorageCapability(data.storage_capability)
        setDeliveryAddress(data.delivery_address || '')
        setHandlingInstructions(data.handling_instructions || '')
        setPriorityWeight(data.priority_weight)

        // Format required_by for datetime-local
        const rb = new Date(data.required_by)
        const rbIso = new Date(rb.getTime() - rb.getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
        setRequiredBy(rbIso)
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load demand request.')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [id])

  const toggleDietary = (item: string) => {
    setDietaryRequirements((prev) =>
      prev.includes(item) ? prev.filter((d) => d !== item) : [...prev, item]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !demand) return
    setError(null)

    const qty = parseFloat(requestedQuantityKg)
    if (isNaN(qty) || qty <= 0) {
      setError('Requested quantity must be a positive number.')
      return
    }

    const fulfilled = Number(demand.fulfilled_quantity_kg)
    if (qty < fulfilled) {
      setError(`Requested quantity cannot be reduced below already fulfilled amount (${fulfilled} kg).`)
      return
    }

    if (!requiredBy) {
      setError('Required-by cut-off timestamp is required.')
      return
    }

    const requiredTime = new Date(requiredBy).getTime()
    if (requiredTime <= Date.now()) {
      setError('Required-by deadline cannot be in the past.')
      return
    }

    setSaving(true)
    try {
      await apiService.updateDemandRequest(id, {
        item_name: itemName.trim() || undefined,
        description: description.trim() || undefined,
        requested_quantity_kg: qty,
        required_by: new Date(requiredBy).toISOString(),
        acceptable_food_condition: acceptableFoodCondition,
        dietary_requirements: dietaryRequirements,
        storage_capability: storageCapability,
        delivery_address: deliveryAddress.trim() || undefined,
        handling_instructions: handlingInstructions.trim() || undefined,
        priority_weight: priorityWeight,
      })

      navigate(`/receiver/demands/${id}`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to update demand request.'
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

  if (error && !demand) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-xl border border-destructive/20 bg-destructive/10 text-destructive text-center space-y-3">
        <AlertCircle className="h-8 w-8 mx-auto" />
        <h3 className="font-semibold">{error}</h3>
        <Link to="/receiver/demands">
          <Button variant="outline" size="sm">
            Back to Demands
          </Button>
        </Link>
      </div>
    )
  }

  if (
    demand &&
    (demand.status === 'CANCELLED' || demand.status === 'FULFILLED' || demand.status === 'EXPIRED')
  ) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 rounded-xl border border-border bg-card text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold">Request Is Closed</h2>
        <p className="text-sm text-muted-foreground">
          This demand request currently has status <strong>{demand.status}</strong> and cannot be modified.
        </p>
        <Link to={`/receiver/demands/${demand.id}`}>
          <Button variant="outline" size="sm" className="mt-2">
            View Request Details
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/receiver/demands/${id}`}>
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Edit Food Demand Request</h1>
          <p className="text-sm text-muted-foreground">
            Adjust requested quantity, extend deadline cut-off, or modify priority urgency.
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
              Item Title / Preferred Food Details
            </label>
            <input
              type="text"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description / Notes
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Quantities & Timeline */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Quantity, Priority & Timeline
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Requested Quantity (kg) <span className="text-destructive">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min={demand ? Number(demand.fulfilled_quantity_kg) : 0.1}
                required
                value={requestedQuantityKg}
                onChange={(e) => setRequestedQuantityKg(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span className="text-[11px] text-muted-foreground block">
                Already fulfilled: {demand?.fulfilled_quantity_kg} kg
              </span>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-destructive font-bold">
                Required-By Cut-Off Deadline <span className="text-destructive">*</span>
              </label>
              <input
                type="datetime-local"
                required
                value={requiredBy}
                onChange={(e) => setRequiredBy(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-destructive/50 bg-background text-sm focus:outline-none focus:ring-2 focus:ring-destructive font-medium"
              />
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Flame className="h-3.5 w-3.5 text-primary" />
              Priority Urgency Level (1 = Flexible, 5 = Critical / Imminent Service)
            </label>
            <div className="grid grid-cols-5 gap-2">
              {[1, 2, 3, 4, 5].map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setPriorityWeight(lvl)}
                  className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all text-center ${
                    priorityWeight === lvl
                      ? 'border-primary bg-primary text-primary-foreground shadow-sm'
                      : 'border-border bg-background hover:bg-muted/50 text-foreground'
                  }`}
                >
                  Level {lvl}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quality, Storage & Dietary */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Quality & Dietary Requirements
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Minimum Acceptable Condition
              </label>
              <select
                value={acceptableFoodCondition}
                onChange={(e) => setAcceptableFoodCondition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="FAIR">FAIR (Ripe / urgent cooking)</option>
                <option value="GOOD">GOOD (Fresh with minor cosmetic flaws)</option>
                <option value="EXCELLENT">EXCELLENT (Pristine commercial grade)</option>
                <option value="ANY">ANY (Maximum flexibility)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Storage Capability
              </label>
              <select
                value={storageCapability}
                onChange={(e) => setStorageCapability(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="AMBIENT">AMBIENT</option>
                <option value="REFRIGERATED">REFRIGERATED</option>
                <option value="FROZEN">FROZEN</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Dietary Requirements
            </label>
            <div className="flex flex-wrap gap-2">
              {DIETARY_OPTIONS.map((tag) => {
                const active = dietaryRequirements.includes(tag)
                return (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => toggleDietary(tag)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                      active
                        ? 'border-primary bg-primary/10 text-primary shadow-xs ring-1 ring-primary'
                        : 'border-border bg-background hover:bg-muted text-foreground'
                    }`}
                  >
                    {tag.replace('_', ' ')}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Delivery Logistics */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Truck className="h-4 w-4 text-primary" />
            Delivery Destination & Instructions
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Delivery Address
            </label>
            <input
              type="text"
              value={deliveryAddress}
              onChange={(e) => setDeliveryAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Unloading / Receiving Instructions
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
          <Link to={`/receiver/demands/${id}`}>
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
