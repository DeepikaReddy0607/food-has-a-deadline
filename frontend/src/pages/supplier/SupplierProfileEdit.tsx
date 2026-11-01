import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiService } from '@/services/api'
import { Button } from '@/components/ui/button'
import type { FacilityType } from '@/types'
import { AlertCircle, Building2, CheckCircle2, Loader2, MapPin } from 'lucide-react'

export const SupplierProfileEdit: React.FC = () => {
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
  const [facilityType, setFacilityType] = useState<FacilityType>('RETAILER')
  const [ambient, setAmbient] = useState(true)
  const [refrigerated, setRefrigerated] = useState(false)
  const [frozen, setFrozen] = useState(false)
  const [description, setDescription] = useState('')

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchExisting = async () => {
      try {
        const data = await apiService.getSupplierProfile()
        setOrgName(data.organization_name)
        setPhone(data.contact_phone)
        setAddress(data.address)
        setState(data.state || '')
        setDistrict(data.district || '')
        setCity(data.city || '')
        setLatitude(data.latitude.toString())
        setLongitude(data.longitude.toString())
        setFacilityType(data.facility_type)
        setAmbient(data.storage_capabilities?.ambient ?? true)
        setRefrigerated(data.storage_capabilities?.refrigerated ?? false)
        setFrozen(data.storage_capabilities?.frozen ?? false)
        setDescription(data.description || '')
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load existing profile.')
      } finally {
        setLoadingInitial(false)
      }
    }
    fetchExisting()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)

    try {
      await apiService.updateSupplierProfile({
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
        description: description || undefined,
      })
      navigate('/supplier/profile')
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
            <Building2 className="h-4 w-4" />
            Profile Management
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Edit Supplier Profile</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => navigate('/supplier/profile')}>
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

        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Facility Type
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
            Pickup Address
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
            <span className="text-xs font-bold uppercase tracking-wider">Geographical Coordinates (WGS84)</span>
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
            Storage Capabilities
          </label>
          <div className="flex flex-wrap gap-4 pt-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={ambient}
                onChange={(e) => setAmbient(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Ambient / Dry
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={refrigerated}
                onChange={(e) => setRefrigerated(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Refrigerated
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={frozen}
                onChange={(e) => setFrozen(e.target.checked)}
                className="rounded border-input text-primary focus:ring-primary"
              />
              Freezer
            </label>
          </div>
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
          <Button type="button" variant="outline" onClick={() => navigate('/supplier/profile')}>
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
