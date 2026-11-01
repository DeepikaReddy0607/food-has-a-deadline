import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiService } from '@/services/api'
import type { SupplierProfile } from '@/types'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  Building2,
  Calendar,
  Clock,
  Edit,
  Loader2,
  MapPin,
  Phone,
  Snowflake,
  Thermometer,
} from 'lucide-react'

export const SupplierProfileView: React.FC = () => {
  const [profile, setProfile] = useState<SupplierProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchProfile = async () => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    try {
      const data = await apiService.getSupplierProfile()
      setProfile(data)
    } catch (err: any) {
      if (err.response?.status === 404) {
        setNotFound(true)
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load profile.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="max-w-md mx-auto my-12 p-8 rounded-xl border border-dashed border-border bg-card text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Building2 className="h-6 w-6" />
        </div>
        <h2 className="text-xl font-bold">Profile Setup Required</h2>
        <p className="text-xs text-muted-foreground">
          You haven&apos;t completed your supplier facility profile yet. You must complete your profile before listing perishable food batches.
        </p>
        <Link to="/supplier/profile/setup">
          <Button className="mt-2">Set Up Supplier Profile</Button>
        </Link>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-lg border border-destructive/20 bg-destructive/10 text-destructive text-center space-y-2">
        <AlertCircle className="h-6 w-6 mx-auto" />
        <p className="font-semibold">{error || 'Unable to load profile'}</p>
        <Button variant="outline" size="sm" onClick={fetchProfile}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto my-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight">{profile.organization_name}</h1>
            <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary border border-primary/20">
              {profile.facility_type}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Registered Food Supplier &bull; ID: {profile.id.slice(0, 8)}...
          </p>
        </div>
        <Link to="/supplier/profile/edit">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Edit className="h-3.5 w-3.5" />
            Edit Profile
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Contact & Location Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <MapPin className="h-4 w-4 text-primary" />
            Facility Location & Contact
          </h2>

          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-muted-foreground w-24 shrink-0">Address:</span>
              <span className="font-medium">{profile.address}</span>
            </div>
            {(profile.city || profile.district || profile.state) && (
              <div className="flex items-start gap-2">
                <span className="text-muted-foreground w-24 shrink-0">Region:</span>
                <span>
                  {[profile.city, profile.district, profile.state].filter(Boolean).join(', ')}
                </span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground w-24 shrink-0">Phone:</span>
              <span className="font-mono flex items-center gap-1 font-medium">
                <Phone className="h-3.5 w-3.5 text-muted-foreground" />
                {profile.contact_phone}
              </span>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-border/50">
              <span className="text-muted-foreground w-24 shrink-0">GPS (WGS84):</span>
              <span className="font-mono text-xs bg-muted px-2 py-0.5 rounded">
                {profile.latitude}, {profile.longitude}
              </span>
            </div>
          </div>
        </div>

        {/* Storage & Schedule Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Storage & Dispatch Window
          </h2>

          <div className="space-y-3 text-sm">
            <div>
              <span className="text-muted-foreground text-xs block mb-1">Cold Chain Capabilities:</span>
              <div className="flex flex-wrap gap-2">
                <span
                  className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md border ${
                    profile.storage_capabilities?.ambient
                      ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  <Thermometer className="h-3 w-3" />
                  Ambient / Dry
                </span>
                <span
                  className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md border ${
                    profile.storage_capabilities?.refrigerated
                      ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  <Snowflake className="h-3 w-3" />
                  Refrigerated
                </span>
                <span
                  className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md border ${
                    profile.storage_capabilities?.frozen
                      ? 'bg-indigo-500/10 text-indigo-600 border-indigo-500/20'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  <Snowflake className="h-3 w-3" />
                  Freezer
                </span>
              </div>
            </div>

            <div className="border-t border-border/50 pt-2">
              <span className="text-muted-foreground text-xs block mb-1">Operating Hours:</span>
              <p className="font-medium text-xs">
                {typeof profile.operating_hours?.general === 'string'
                  ? `Standard Pickup: ${profile.operating_hours.general}`
                  : 'Standard Business Hours'}
              </p>
            </div>

            <div className="border-t border-border/50 pt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <Calendar className="h-3.5 w-3.5" />
              Profile updated: {new Date(profile.updated_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {profile.description && (
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-2">
          <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Facility Overview & Dispatch Notes
          </h2>
          <p className="text-sm leading-relaxed text-foreground/90">{profile.description}</p>
        </div>
      )}
    </div>
  )
}
