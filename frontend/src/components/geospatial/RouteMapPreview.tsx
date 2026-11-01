import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'
import {
  Navigation,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Clock,
  MapPin,
  TrendingUp,
  Info,
} from 'lucide-react'
import type { RouteEstimateResult } from '@/types'

// Custom DivIcons for crisp SVG-like rendering without Leaflet icon asset loading issues
const supplierPinIcon = L.divIcon({
  className: 'custom-supplier-marker',
  html: `
    <div style="
      background-color: #059669;
      color: white;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
      border: 2px solid white;
      font-weight: 700;
      font-size: 13px;
    ">
      S
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -18],
})

const receiverPinIcon = L.divIcon({
  className: 'custom-receiver-marker',
  html: `
    <div style="
      background-color: #2563eb;
      color: white;
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
      border: 2px solid white;
      font-weight: 700;
      font-size: 13px;
    ">
      R
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -18],
})

// Auto-adjust Leaflet viewport to encompass origin and destination coordinates
function AutoFitBounds({ bounds }: { bounds: L.LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => {
    try {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 })
    } catch {
      // Map may not be ready yet
    }
  }, [bounds, map])
  return null
}

interface RouteMapPreviewProps {
  estimate: RouteEstimateResult
}

export const RouteMapPreview: React.FC<RouteMapPreviewProps> = ({ estimate }) => {
  const sLat = estimate.supplier_coordinates.latitude
  const sLon = estimate.supplier_coordinates.longitude
  const rLat = estimate.receiver_coordinates.latitude
  const rLon = estimate.receiver_coordinates.longitude

  const supplierPos: [number, number] = [sLat, sLon]
  const receiverPos: [number, number] = [rLat, rLon]

  // Construct map bounds
  const bounds: L.LatLngBoundsExpression = [supplierPos, receiverPos]

  // Parse road polyline from GeoJSON [lon, lat] -> Leaflet [lat, lon]
  const routePolyline: [number, number][] =
    estimate.route_geometry && estimate.route_geometry.coordinates.length > 0
      ? estimate.route_geometry.coordinates.map((coord) => [coord[1], coord[0]])
      : [supplierPos, receiverPos]

  // Feasibility color and icon mapping
  const feasibilityConfig = {
    FEASIBLE: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-100',
      badge: 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 border-emerald-300',
      icon: CheckCircle2,
      title: 'Temporally Feasible Redistribution',
      desc: 'Estimated transit and handling time fits comfortably within the remaining usable shelf-life of this surplus food.',
    },
    INFEASIBLE: {
      bg: 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-100',
      badge: 'bg-rose-100 dark:bg-rose-900/60 text-rose-800 dark:text-rose-200 border-rose-300',
      icon: AlertTriangle,
      title: 'Temporally Infeasible Delivery',
      desc: 'Transit plus handling buffer exceeds available shelf-life, or usable deadline has already passed.',
    },
    UNKNOWN: {
      bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-100',
      badge: 'bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200 border-amber-300',
      icon: HelpCircle,
      title: 'Feasibility Indeterminate',
      desc: 'Insufficient timing or location data to verify whether transportation can be safely achieved before expiration.',
    },
  }[estimate.feasibility]

  const StatusIcon = feasibilityConfig.icon

  return (
    <div className="space-y-4">
      {/* 1. Feasibility Banner */}
      <div className={`p-4 rounded-xl border ${feasibilityConfig.bg} shadow-sm transition-all`}>
        <div className="flex items-start gap-3">
          <StatusIcon className="w-6 h-6 mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h4 className="font-semibold text-base">{feasibilityConfig.title}</h4>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold border uppercase tracking-wide ${feasibilityConfig.badge}`}
              >
                {estimate.feasibility}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                Provider: {estimate.routing_provider}
              </span>
            </div>
            <p className="text-sm opacity-90">{feasibilityConfig.desc}</p>

            {/* Warnings list if any */}
            {estimate.warnings.length > 0 && (
              <div className="mt-2.5 space-y-1">
                {estimate.warnings.map((warn, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 text-xs">
                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0 opacity-75" />
                    <span>{warn}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 bg-card border rounded-lg shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <Navigation className="w-3.5 h-3.5 text-blue-500" />
            <span>Straight-Line</span>
          </div>
          <div className="text-lg font-bold text-foreground">
            {estimate.straight_line_distance_km} <span className="text-xs font-normal">km</span>
          </div>
          <div className="text-[10px] text-muted-foreground">Great-circle Haversine</div>
        </div>

        <div className="p-3 bg-card border rounded-lg shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
            <span>Road Distance</span>
          </div>
          <div className="text-lg font-bold text-foreground">
            {estimate.road_distance_km} <span className="text-xs font-normal">km</span>
          </div>
          <div className="text-[10px] text-muted-foreground">
            {estimate.is_fallback ? 'Approx (1.35x circuity)' : 'OSRM driving route'}
          </div>
        </div>

        <div className="p-3 bg-card border rounded-lg shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <Clock className="w-3.5 h-3.5 text-indigo-500" />
            <span>Transit Time</span>
          </div>
          <div className="text-lg font-bold text-foreground">
            {estimate.estimated_travel_minutes} <span className="text-xs font-normal">mins</span>
          </div>
          <div className="text-[10px] text-muted-foreground">
            +{estimate.handling_buffer_minutes}m handling buffer
          </div>
        </div>

        <div className="p-3 bg-card border rounded-lg shadow-xs">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <MapPin className="w-3.5 h-3.5 text-amber-500" />
            <span>Remaining Life</span>
          </div>
          <div className="text-lg font-bold text-foreground">
            {estimate.available_minutes !== null && estimate.available_minutes !== undefined
              ? `${Math.round(estimate.available_minutes)}`
              : 'N/A'}{' '}
            <span className="text-xs font-normal">mins</span>
          </div>
          <div className="text-[10px] text-muted-foreground">
            {estimate.required_minutes !== null && estimate.required_minutes !== undefined
              ? `Required: ${Math.round(estimate.required_minutes)} mins`
              : 'Time check'}
          </div>
        </div>
      </div>

      {/* 3. Interactive Leaflet Map */}
      <div className="relative border rounded-xl overflow-hidden shadow-xs h-[360px] w-full">
        <MapContainer
          bounds={bounds}
          scrollWheelZoom={false}
          className="h-full w-full z-0"
          style={{ minHeight: '360px' }}
        >
          <AutoFitBounds bounds={bounds} />

          {/* OpenStreetMap TileLayer */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Supplier Origin Marker */}
          <Marker position={supplierPos} icon={supplierPinIcon}>
            <Popup>
              <div className="text-xs space-y-1">
                <div className="font-bold text-emerald-700">Origin: Surplus Facility</div>
                <div>{estimate.supplier_name || 'Supplier Facility'}</div>
                <div className="text-muted-foreground font-mono">
                  {sLat.toFixed(5)}, {sLon.toFixed(5)}
                </div>
              </div>
            </Popup>
          </Marker>

          {/* Receiver Destination Marker */}
          <Marker position={receiverPos} icon={receiverPinIcon}>
            <Popup>
              <div className="text-xs space-y-1">
                <div className="font-bold text-blue-700">Destination: Receiver Facility</div>
                <div>{estimate.receiver_name || 'Receiver Facility'}</div>
                <div className="text-muted-foreground font-mono">
                  {rLat.toFixed(5)}, {rLon.toFixed(5)}
                </div>
              </div>
            </Popup>
          </Marker>

          {/* Route Polyline */}
          {estimate.is_fallback ? (
            // Straight dashed line fallback - never fabricate turn-by-turn geometry!
            <Polyline
              positions={[supplierPos, receiverPos]}
              pathOptions={{
                color: '#ea580c',
                dashArray: '8, 8',
                weight: 3.5,
                opacity: 0.85,
              }}
            />
          ) : (
            // Actual OSRM turn-by-turn road geometry
            <Polyline
              positions={routePolyline}
              pathOptions={{
                color: '#2563eb',
                weight: 5,
                opacity: 0.85,
              }}
            />
          )}
        </MapContainer>

        {/* Floating route indicator badge on map */}
        <div className="absolute top-3 right-3 z-[1000] bg-background/90 backdrop-blur-xs px-3 py-1.5 rounded-lg border shadow-sm text-xs font-medium">
          {estimate.is_fallback ? (
            <span className="text-orange-600 dark:text-orange-400 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              Fallback Straight Line (Dashed)
            </span>
          ) : (
            <span className="text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
              OSRM Driving Road Route
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
