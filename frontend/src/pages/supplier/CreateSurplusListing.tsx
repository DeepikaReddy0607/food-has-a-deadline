import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Info,
  Loader2,
  PlusCircle,
  Thermometer,
  Truck,
  Utensils,
} from 'lucide-react'

const CATEGORIES = [
  { value: 'FRUITS', label: 'Fresh Fruits', icon: '🍎' },
  { value: 'VEGETABLES', label: 'Fresh Vegetables', icon: '🥦' },
  { value: 'GRAINS', label: 'Grains & Cereals', icon: '🌾' },
  { value: 'DAIRY', label: 'Dairy & Eggs', icon: '🥛' },
  { value: 'BAKERY', label: 'Bakery & Bread', icon: '🥖' },
  { value: 'COOKED_FOOD', label: 'Cooked / Prepared Meals', icon: '🍲' },
  { value: 'OTHER', label: 'Other Perishables', icon: '📦' },
]

export const CreateSurplusListing: React.FC = () => {
  const navigate = useNavigate()

  // Profile check state
  const [checkingProfile, setCheckingProfile] = useState(true)
  const [profileMissing, setProfileMissing] = useState(false)

  // Form state
  const [foodCategory, setFoodCategory] = useState('FRUITS')
  const [itemName, setItemName] = useState('')
  const [description, setDescription] = useState('')
  const [initialQuantityKg, setInitialQuantityKg] = useState('')
  const [harvestOrPrepDate, setHarvestOrPrepDate] = useState('')
  const [preparationDate, setPreparationDate] = useState('')
  const [estimatedDeadline, setEstimatedDeadline] = useState('')
  const [foodCondition, setFoodCondition] = useState('GOOD')
  const [storageCondition, setStorageCondition] = useState('AMBIENT')
  const [pickupAddress, setPickupAddress] = useState('')
  const [handlingInstructions, setHandlingInstructions] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Set default datetimes on mount
  useEffect(() => {
    const now = new Date()
    // Harvest / prep: now
    const nowIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16)
    setHarvestOrPrepDate(nowIso)

    // Deadline: 48 hours ahead
    const deadlineDate = new Date(now.getTime() + 48 * 3600 * 1000)
    const deadlineIso = new Date(deadlineDate.getTime() - deadlineDate.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16)
    setEstimatedDeadline(deadlineIso)

    // Check profile
    const verifyProfile = async () => {
      try {
        const p = await apiService.getSupplierProfile()
        setPickupAddress(`${p.address}, ${p.city || ''}, ${p.district || ''}, ${p.state || ''}`)
      } catch (err: any) {
        if (err.response?.status === 404 || err.response?.status === 400) {
          setProfileMissing(true)
        }
      } finally {
        setCheckingProfile(false)
      }
    }

    verifyProfile()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const qty = parseFloat(initialQuantityKg)
    if (isNaN(qty) || qty <= 0) {
      setError('Please provide a valid initial food quantity greater than 0 kg.')
      return
    }

    if (!harvestOrPrepDate) {
      setError('Harvest or procurement timestamp is required.')
      return
    }

    if (!estimatedDeadline) {
      setError('Estimated usable deadline timestamp is required.')
      return
    }

    const prepTime = new Date(harvestOrPrepDate).getTime()
    const deadlineTime = new Date(estimatedDeadline).getTime()
    const nowTime = Date.now()

    if (deadlineTime <= prepTime) {
      setError('Estimated usable deadline must be after harvest or preparation date.')
      return
    }

    if (deadlineTime <= nowTime) {
      setError('Estimated usable deadline cannot be in the past. Food is already expired.')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        food_category: foodCategory,
        item_name: itemName.trim(),
        description: description.trim() || undefined,
        initial_quantity_kg: qty,
        harvest_or_prep_date: new Date(harvestOrPrepDate).toISOString(),
        preparation_date: preparationDate ? new Date(preparationDate).toISOString() : undefined,
        estimated_deadline: new Date(estimatedDeadline).toISOString(),
        food_condition: foodCondition,
        storage_condition: storageCondition,
        pickup_address: pickupAddress.trim() || undefined,
        handling_instructions: handlingInstructions.trim() || undefined,
      }

      const res = await apiService.createSurplusListing(payload)
      navigate(`/supplier/inventory/${res.id}`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to create surplus listing. Please check input values.'
      )
    } finally {
      setSubmitting(false)
    }
  }

  if (checkingProfile) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (profileMissing) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 rounded-xl border border-dashed border-amber-500/40 bg-amber-50/10 dark:bg-amber-950/20 text-center space-y-4">
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-400">
          <AlertCircle className="h-7 w-7" />
        </div>
        <h2 className="text-2xl font-bold">Supplier Profile Required</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          You must set up and complete your verified supplier facility profile before listing available food surplus.
        </p>
        <div className="pt-2">
          <Link to="/supplier/profile/setup">
            <Button className="bg-amber-600 hover:bg-amber-700 text-white">
              Complete Supplier Profile Now
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/supplier/inventory">
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">List Perishable Surplus Food</h1>
          <p className="text-sm text-muted-foreground">
            Register available food batches with hard expiration timestamps before quality degrades.
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
        {/* Category & Title Card */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Utensils className="h-4 w-4 text-primary" />
            Food Item Information
          </h2>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Food Category <span className="text-destructive">*</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setFoodCategory(cat.value)}
                  className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all text-left ${
                    foodCategory === cat.value
                      ? 'border-primary bg-primary/10 text-primary shadow-sm ring-1 ring-primary'
                      : 'border-border bg-background hover:bg-muted/50 text-foreground'
                  }`}
                >
                  <span className="text-base">{cat.icon}</span>
                  <span className="truncate">{cat.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Item Name / Batch Title <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Fresh Organic Tomatoes, Sliced Sourdough Bread, Cooked Lentil Stew"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Details on food packaging, variety, source, or allergen warnings..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Quantities & Critical Timelines */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Quantities & Critical Deadlines
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Quantity Available (kg) <span className="text-destructive">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                required
                placeholder="e.g. 50.0"
                value={initialQuantityKg}
                onChange={(e) => setInitialQuantityKg(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Harvest / Intake Date <span className="text-destructive">*</span>
              </label>
              <input
                type="datetime-local"
                required
                value={harvestOrPrepDate}
                onChange={(e) => setHarvestOrPrepDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Prep / Cook Date (Optional)
              </label>
              <input
                type="datetime-local"
                value={preparationDate}
                onChange={(e) => setPreparationDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-destructive font-bold">
                Usable Deadline <span className="text-destructive">*</span>
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

          <div className="p-3 rounded-lg bg-muted/40 border border-border/60 text-xs text-muted-foreground flex items-center gap-2.5">
            <Info className="h-4 w-4 text-primary shrink-0" />
            <span>
              The <strong>usable deadline</strong> is the strict hard cut-off timestamp. Food redistribution proposals are prioritised based on how rapidly this countdown elapses.
            </span>
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
                Food Condition <span className="text-destructive">*</span>
              </label>
              <select
                value={foodCondition}
                onChange={(e) => setFoodCondition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="EXCELLENT">EXCELLENT (Just harvested/cooked, pristine)</option>
                <option value="GOOD">GOOD (Fresh, safe, minor cosmetic variations)</option>
                <option value="FAIR">FAIR (Ripe, safe to consume, urgent distribution)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Required Storage Environment <span className="text-destructive">*</span>
              </label>
              <select
                value={storageCondition}
                onChange={(e) => setStorageCondition(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="AMBIENT">AMBIENT (Room temperature storage)</option>
                <option value="REFRIGERATED">REFRIGERATED (Cold storage 2°C - 8°C)</option>
                <option value="FROZEN">FROZEN (Freezer storage &lt; -18°C)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Logistics & Handling */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Truck className="h-4 w-4 text-primary" />
            Logistics & Handling
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Pickup Address (Defaults to facility location)
            </label>
            <input
              type="text"
              placeholder="Facility address or specific loading dock"
              value={pickupAddress}
              onChange={(e) => setPickupAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Handling / Transport Instructions (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Bring insulated cooler boxes, stack crates no higher than 3 layers, call dock supervisor on arrival"
              value={handlingInstructions}
              onChange={(e) => setHandlingInstructions(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link to="/supplier/inventory">
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={submitting} className="min-w-[160px]">
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Registering...
              </>
            ) : (
              <>
                <PlusCircle className="h-4 w-4 mr-2" />
                Publish Listing
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
