import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix standard Leaflet default icon issues in bundler environments
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

export const MapVerification: React.FC = () => {
  const center: [number, number] = [20.5937, 78.9629] // Center coordinate for verification

  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Geospatial Engine Status (Leaflet + React Leaflet)
      </h3>
      <div className="h-64 w-full overflow-hidden rounded-md border border-border">
        <MapContainer
          center={center}
          zoom={4}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Marker position={center} icon={defaultIcon}>
            <Popup>
              <strong>Food Has A Deadline</strong>
              <br />
              Geospatial dispatch ready.
            </Popup>
          </Marker>
        </MapContainer>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Interactive map rendering initialized successfully.
      </p>
    </div>
  )
}
