import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Flame,
  Loader2,
  PlusCircle,
  ShieldCheck,
  Truck,
  Utensils,
} from 'lucide-react'

const CATEGORIES = [
  { value: 'ANY', label: 'Any Category', icon: '✨' },
  { value: 'FRUITS', label: 'Fresh Fruits', icon: '🍎' },
  { value: 'VEGETABLES', label: 'Fresh Vegetables', icon: '🥦' },
  { value: 'GRAINS', label: 'Grains & Cereals', icon: '🌾' },
  { value: 'DAIRY', label: 'Dairy & Eggs', icon: '🥛' },
  { value: 'BAKERY', label: 'Bakery & Bread', icon: '🥖' },
  { value: 'COOKED_FOOD', label: 'Cooked / Prepared Meals', icon: '🍲' },
  { value: 'OTHER', label: 'Other Perishables', icon: '📦' },
]

const DIETARY_OPTIONS = [
  'VEGETARIAN',
  'VEGAN',
  'GLUTEN_FREE',
  'DAIRY_FREE',
  'NUT_FREE',
  'HALAL',
  'KOSHER',
]

export const CreateDemandRequest: React.FC = () => {
  const navigate = useNavigate()

  // Profile check state
  const [checkingProfile, setCheckingProfile] = useState(true)
  const [profileMissing, setProfileMissing] = useState(false)

  // Form state
  const [foodCategory, setFoodCategory] = useState('ANY')
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

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Default required_by: 24 hours from now
    const now = new Date()
    const targetDate = new Date(now.getTime() + 24 * 3600 * 1000)
    const targetIso = new Date(targetDate.getTime() - targetDate.getTimezoneOffset() * 60000)
      .toISOString()
      .slice(0, 16)
    setRequiredBy(targetIso)

    const verifyProfile = async () => {
      try {
        const p = await apiService.getReceiverProfile()
        setDeliveryAddress(`${p.address}, ${p.city || ''}, ${p.district || ''}, ${p.state || ''}`)
        if (p.dietary_handling_capabilities && Array.isArray(p.dietary_handling_capabilities)) {
          setDietaryRequirements(p.dietary_handling_capabilities)
        }
        if (p.priority_level) {
          setPriorityWeight(p.priority_level)
        }
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

  const toggleDietary = (item: string) => {
    setDietaryRequirements((prev) =>
      prev.includes(item) ? prev.filter((d) => d !== item) : [...prev, item]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    const qty = parseFloat(requestedQuantityKg)
    if (isNaN(qty) || qty <= 0) {
      setError('Please provide a valid requested food quantity greater than 0 kg.')
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

    setSubmitting(true)
    try {
      const payload = {
        food_category: foodCategory,
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
      }

      const res = await apiService.createDemandRequest(payload)
      navigate(`/receiver/demands/${res.id}`)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          'Failed to create demand request. Please check input values.'
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
        <h2 className="text-2xl font-bold">Receiver Profile Required</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          You must set up and complete your verified organization profile before submitting food demand requests.
        </p>
        <div className="pt-2">
          <Link to="/receiver/profile/setup">
            <Button className="bg-amber-600 hover:bg-amber-700 text-white">
              Complete Receiver Profile Now
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/receiver/demands">
          <Button variant="ghost" size="sm" className="h-9 w-9 p-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create Food Demand Request</h1>
          <p className="text-sm text-muted-foreground">
            Register your facility&apos;s food requirements and cut-off deadlines for AI-driven redistribution matching.
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
        {/* Category & Title */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Utensils className="h-4 w-4 text-primary" />
            Requested Food Category & Item
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
              Item Title / Preferred Food Details (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Sliced Whole Wheat Bread, Fresh Cooking Greens, Prepared Lunch Portions"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description / Intended Meal Program (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Context for meal prep, expected number of beneficiaries, or flexibility..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {/* Quantity & Deadline */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Quantity & Cut-Off Timeline
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Quantity Needed (kg) <span className="text-destructive">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                required
                placeholder="e.g. 75.0"
                value={requestedQuantityKg}
                onChange={(e) => setRequestedQuantityKg(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-destructive font-bold">
                Required By Cut-Off Deadline <span className="text-destructive">*</span>
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
                  <span className="block text-[10px] font-normal opacity-80">
                    {lvl === 1 ? 'Low' : lvl === 3 ? 'Medium' : lvl === 5 ? 'Critical' : ''}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Quality, Storage & Dietary Preferences */}
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-5">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Quality, Storage & Dietary Requirements
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
                <option value="FAIR">FAIR (Accept ripe/surplus food for immediate cooking)</option>
                <option value="GOOD">GOOD (Fresh condition with minor cosmetic flaws)</option>
                <option value="EXCELLENT">EXCELLENT (Pristine commercial grade only)</option>
                <option value="ANY">ANY (Maximum flexibility for all safe edible food)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Available Facility Storage Capability <span className="text-destructive">*</span>
              </label>
              <select
                value={storageCapability}
                onChange={(e) => setStorageCapability(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="AMBIENT">AMBIENT (Dry / room temperature)</option>
                <option value="REFRIGERATED">REFRIGERATED (Cold room / chillers 2°C - 8°C)</option>
                <option value="FROZEN">FROZEN (Commercial freezer &lt; -18°C)</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Dietary Restrictions / Certifications
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
            Destination & Delivery Logistics
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Delivery Address (Defaults to recipient facility address)
            </label>
            <input
              type="text"
              placeholder="Delivery destination or specific receiving bay"
              value={deliveryAddress}
              onChange={(e) => setDeliveryAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Unloading & Receiving Instructions (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Ring side gate buzzer, ramp available for pallet jacks, staff available from 08:00 to 17:00"
              value={handlingInstructions}
              onChange={(e) => setHandlingInstructions(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link to="/receiver/demands">
            <Button variant="outline" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={submitting} className="min-w-[170px]">
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Registering...
              </>
            ) : (
              <>
                <PlusCircle className="h-4 w-4 mr-2" />
                Submit Demand
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
