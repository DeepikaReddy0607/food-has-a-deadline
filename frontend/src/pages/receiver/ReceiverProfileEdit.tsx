import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import type { ReceiverCategory } from '@/types'
import { AlertCircle, CheckCircle2, HeartHandshake, Loader2, MapPin } from 'lucide-react'

const DIETARY_OPTIONS = ['VEGETARIAN', 'VEGAN', 'HALAL', 'KOSHER', 'DAIRY_FREE', 'NUT_FREE', 'GLUTEN_FREE']

export const ReceiverProfileEdit: React.FC = () => {
  const navigate = useNavigate()

  const [loadingInitial, setLoadingInitial] = useState(true)
  const [orgName, setOrgName] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [city, setCity] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [receiverCategory, setReceiverCategory] = useState<ReceiverCategory>('COMMUNITY_KITCHEN')
  const [capacity, setCapacity] = useState('')
  const [refrigeration, setRefrigeration] = useState(false)
  const [freezer, setFreezer] = useState(false)
  const [dietary, setDietary] = useState<string[]>([])
  const [priorityLevel, setPriorityLevel] = useState(3)
  const [description, setDescription] = useState('')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchExisting = async () => {
      try {
        const data = await apiService.getReceiverProfile()
        setOrgName(data.organization_name)
        setPhone(data.contact_phone)
        setAddress(data.address)
        setState(data.state || '')
        setDistrict(data.district || '')
        setCity(data.city || '')
        setLatitude(data.latitude.toString())
        setLongitude(data.longitude.toString())
        if (data.receiver_category) {
          setReceiverCategory(data.receiver_category)
        }
        setCapacity(data.capacity_daily_kg.toString())
        setRefrigeration(data.cold_storage_capabilities?.refrigeration ?? false)
        setFreezer(data.cold_storage_capabilities?.freezer ?? false)
        setDietary(data.dietary_handling_capabilities || [])
        setPriorityLevel(data.priority_level)
        setDescription(data.description || '')
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load existing profile.')
      } finally {
        setLoadingInitial(false)
      }
    }
    fetchExisting()
  }, [])

  const handleToggleDietary = (item: string) => {
    if (dietary.includes(item)) {
      setDietary(dietary.filter((d) => d !== item))
    } else {
      setDietary([...dietary, item])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)

    try {
      await apiService.updateReceiverProfile({
        organization_name: orgName,
        contact_phone: phone,
        address,
        state: state || undefined,
        district: district || undefined,
        city: city || undefined,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        receiver_category: receiverCategory,
        capacity_daily_kg: parseFloat(capacity),
        cold_storage_capabilities: {
          refrigeration,
          freezer,
        },
        dietary_handling_capabilities: dietary,
        priority_level: priorityLevel,
        description: description || undefined,
      })
      navigate('/receiver/profile')
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to save changes.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setSaving(false)
    }
  }

  if (loadingInitial) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto my-8 p-6 sm:p-8 rounded-xl border border-border bg-card shadow-sm space-y-6">
      <div className="border-b border-border pb-4 flex items-center justify-between">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
            <HeartHandshake className="h-4 w-4" />
            Profile Management
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Edit Receiver Profile</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate('/receiver/profile')}>
          Cancel
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Organization Name
            </label>
            <input
              type="text"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Contact Phone
            </label>
            <input
              type="text"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Receiver Category
            </label>
            <select
              value={receiverCategory}
              onChange={(e) => setReceiverCategory(e.target.value as ReceiverCategory)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="COMMUNITY_KITCHEN">Community Kitchen / Soup Kitchen</option>
              <option value="SHELTER">Homeless Shelter / Safe House</option>
              <option value="FOOD_BANK">Food Bank / Regional Pantry</option>
              <option value="NGO">Non-Profit Organization (NGO)</option>
              <option value="HOSPITAL">Hospital / Clinic Care</option>
              <option value="OTHER">Other Community Feeding Program</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Max Daily Intake Capacity (kg)
            </label>
            <input
              type="number"
              min="1"
              step="0.5"
              required
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary font-mono"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Destination Address
          </label>
          <input
            type="text"
            required
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">City</label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">District</label>
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">State</label>
            <input
              type="text"
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="rounded-lg border border-border/80 bg-muted/20 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider">Destination Coordinates (WGS84)</span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Latitude</label>
              <input
                type="number"
                step="0.000001"
                required
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Longitude</label>
              <input
                type="number"
                step="0.000001"
                required
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Cold Storage Hardware
          </label>
          <div className="flex flex-wrap gap-4 pt-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={refrigeration}
                onChange={(e) => setRefrigeration(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Commercial Refrigeration
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={freezer}
                onChange={(e) => setFreezer(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Deep Freezer
            </label>
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Dietary Requirements Handled
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            {DIETARY_OPTIONS.map((item) => (
              <button
                type="button"
                key={item}
                onClick={() => handleToggleDietary(item)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                  dietary.includes(item)
                    ? 'bg-primary text-primary-foreground border-primary font-medium'
                    : 'bg-muted text-muted-foreground border-input hover:border-primary/50'
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Social Urgency Priority Level (1 to 5)
            </label>
            <span className="font-bold text-sm text-primary">{priorityLevel} / 5</span>
          </div>
          <input
            type="range"
            min="1"
            max="5"
            step="1"
            value={priorityLevel}
            onChange={(e) => setPriorityLevel(parseInt(e.target.value, 10))}
            className="w-full accent-primary"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Facility Notes
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={() => navigate('/receiver/profile')}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving} className="gap-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </form>
    </div>
  )
}
