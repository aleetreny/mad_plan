import { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { MadPlanEvent } from '../types';

const MADRID_CENTER: [number, number] = [40.4168, -3.7038];
const MADRID_ZOOM = 13;

// Only show markers within the Madrid metro area
const MADRID_LAT = [40.30, 40.55] as const;
const MADRID_LON = [-3.85, -3.55] as const;

function isInMadrid(lat: number, lon: number) {
  return lat >= MADRID_LAT[0] && lat <= MADRID_LAT[1]
      && lon >= MADRID_LON[0] && lon <= MADRID_LON[1];
}

// Restrict max panning to Madrid area
const MAX_BOUNDS = L.latLngBounds([40.25, -3.92], [40.60, -3.48]);

interface Props {
  events: MadPlanEvent[];
  onOpenEvent: (event: MadPlanEvent) => void;
}

function FitBounds({ events }: { events: MadPlanEvent[] }) {
  const map = useMap();
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (events.length === 0) {
      map.setView(MADRID_CENTER, MADRID_ZOOM);
      prevCountRef.current = 0;
      return;
    }
    if (Math.abs(events.length - prevCountRef.current) > 5) {
      const coords = events.map(e => [e.latitud!, e.longitud!] as [number, number]);
      if (coords.length > 0) {
        const bounds = L.latLngBounds(coords);
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      }
      prevCountRef.current = events.length;
    }
  }, [events, map]);

  return null;
}

function fmtDate(ev: MadPlanEvent): string {
  const raw = ev.sort_datetime || ev.proximo_datetime || ev.fecha_inicio;
  if (!raw) return '';
  try {
    return new Date(raw).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  } catch { return ''; }
}

export function MapView({ events, onOpenEvent }: Props) {
  const madridEvents = useMemo(
    () => events.filter(e => e.latitud && e.longitud && isInMadrid(e.latitud, e.longitud)),
    [events],
  );

  return (
    <div className="rounded-xl overflow-hidden border" style={{ height: '540px' }}>
      <MapContainer
        center={MADRID_CENTER}
        zoom={MADRID_ZOOM}
        minZoom={11}
        maxBounds={MAX_BOUNDS}
        maxBoundsViscosity={1.0}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds events={madridEvents} />
        {madridEvents.map(event => (
          <CircleMarker
            key={event.id}
            center={[event.latitud!, event.longitud!]}
            radius={6}
            pathOptions={{
              fillColor: 'var(--primary, #6366f1)',
              fillOpacity: 0.85,
              color: '#fff',
              weight: 1.5,
            }}
            eventHandlers={{ click: () => onOpenEvent(event) }}
          >
            <Popup maxWidth={220} closeButton={false}>
              <div className="font-sans text-xs leading-relaxed">
                <p className="font-semibold text-sm mb-0.5 line-clamp-2">{event.titulo}</p>
                <p className="text-gray-500">{fmtDate(event)}{event.lugar ? ` · ${event.lugar}` : ''}</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
