import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import type { FacilityType } from '@/types'
import { AlertCircle, Building2, CheckCircle2, Loader2, MapPin } from 'lucide-react'

export const SupplierProfileSetup: React.FC = () => {
  const navigate = useNavigate()

  const [orgName, setOrgName] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [city, setCity] = useState('')
  const [latitude, setLatitude] = useState('20.5937')
  const [longitude, setLongitude] = useState('78.9629')
  const [facilityType, setFacilityType] = useState<FacilityType>('RETAILER')
  const [ambient, setAmbient] = useState(true)
  const [refrigerated, setRefrigerated] = useState(false)
  const [frozen, setFrozen] = useState(false)
  const [openTime, setOpenTime] = useState('08:00')
  const [closeTime, setCloseTime] = useState('20:00')
  const [description, setDescription] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGetCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(pos.coords.latitude.toFixed(6))
          setLongitude(pos.coords.longitude.toFixed(6))
        },
        () => {
          setError('Could not retrieve current browser GPS. Please enter coordinates manually.')
        }
      )
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await apiService.createSupplierProfile({
        organization_name: orgName,
        contact_phone: phone,
        address,
        state: state || undefined,
        district: district || undefined,
        city: city || undefined,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        facility_type: facilityType,
        storage_capabilities: {
          ambient,
          refrigerated,
          frozen,
        },
        operating_hours: {
          general: `${openTime}-${closeTime}`,
        },
        description: description || undefined,
      })
      navigate('/supplier/profile')
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create profile.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto my-8 p-6 sm:p-8 rounded-xl border border-border bg-card shadow-sm space-y-6">
      <div className="border-b border-border pb-4 space-y-1">
        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
          <Building2 className="h-4 w-4" />
          Supplier Onboarding
        </div>
        <h1 className="text-2xl font-bold tracking-tight">Set Up Your Supplier Profile</h1>
        <p className="text-xs text-muted-foreground">
          Provide your facility location, contact number, and storage capabilities to begin listing perishable food surplus.
        </p>
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
              Organization Name *
            </label>
            <input
              type="text"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="e.g. Metro Fresh Market"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Contact Phone *
            </label>
            <input
              type="text"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1-555-0199"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Facility Type *
          </label>
          <select
            value={facilityType}
            onChange={(e) => setFacilityType(e.target.value as FacilityType)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="RETAILER">Supermarket / Retailer</option>
            <option value="WHOLESALER">Wholesale Distributor</option>
            <option value="FARM">Agricultural Farm</option>
            <option value="RESTAURANT">Restaurant / Food Service</option>
            <option value="FOOD_PROCESSOR">Food Processing Plant</option>
            <option value="OTHER">Other Commercial Donor</option>
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Pickup Address *
          </label>
          <input
            type="text"
            required
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Street address, building number, loading dock"
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
              placeholder="e.g. San Francisco"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">District / County</label>
            <input
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="e.g. Bay Area"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">State / Province</label>
            <input
              type="text"
              value={state}
              onChange={(e) => setState(e.target.value)}
              placeholder="e.g. California"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {/* Coordinates */}
        <div className="rounded-lg border border-border/80 bg-muted/20 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary" />
              <span className="text-xs font-bold uppercase tracking-wider">Geographical Coordinates (WGS84) *</span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleGetCurrentLocation}
              className="text-xs h-7 gap-1"
            >
              Autofill GPS
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Latitude (-90 to +90)</label>
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
              <label className="text-xs text-muted-foreground block mb-1">Longitude (-180 to +180)</label>
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

        {/* Storage Capabilities */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            On-Site Storage Capabilities
          </label>
          <div className="flex flex-wrap gap-4 pt-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={ambient}
                onChange={(e) => setAmbient(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Ambient / Dry Storage
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={refrigerated}
                onChange={(e) => setRefrigerated(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Commercial Refrigeration
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={frozen}
                onChange={(e) => setFrozen(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Freezer Facility
            </label>
          </div>
        </div>

        {/* Operating Hours */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Daily Opening Time
            </label>
            <input
              type="time"
              value={openTime}
              onChange={(e) => setOpenTime(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Daily Closing Time
            </label>
            <input
              type="time"
              value={closeTime}
              onChange={(e) => setCloseTime(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Additional Facility Notes (Optional)
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Special loading dock instructions, key contacts, or dispatch requirements."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <Button type="submit" disabled={loading} className="w-full gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
          {loading ? 'Submitting Profile...' : 'Complete Profile Setup'}
        </Button>
      </form>
    </div>
  )
}
