import { useEffect, useMemo, useRef } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MADRID_BOUNDS, MADRID_CENTER } from '../../domain/madplan/constants';
import { formatShortDate } from '../../domain/madplan/formatters';
import type { MadPlanEvent } from '../../domain/madplan/types';

const MAX_BOUNDS = L.latLngBounds(
  [MADRID_BOUNDS.latMin, MADRID_BOUNDS.lonMin],
  [MADRID_BOUNDS.latMax, MADRID_BOUNDS.lonMax],
);

function FitBounds({ events }: { events: MadPlanEvent[] }) {
  const map = useMap();
  const previousKey = useRef('');

  useEffect(() => {
    if (events.length === 0) {
      map.setView(MADRID_CENTER, 12);
      previousKey.current = '';
      return;
    }

    const key = events.map((event) => event.id).join('|');
    if (key === previousKey.current) return;

    const bounds = L.latLngBounds(events.map((event) => [event.latitud!, event.longitud!] as [number, number]));
    map.fitBounds(bounds, { padding: [36, 36], maxZoom: 15 });
    previousKey.current = key;
  }, [events, map]);

  return null;
}

interface MapViewProps {
  events: MadPlanEvent[];
  onOpenEvent: (event: MadPlanEvent) => void;
}

export function MapView({ events, onOpenEvent }: MapViewProps) {
  const withCoordinates = useMemo(
    () => events.filter((event) => event.hasCoordinates && event.latitud != null && event.longitud != null),
    [events],
  );

  if (withCoordinates.length === 0) {
    return (
      <div className="grid min-h-[560px] place-items-center rounded-[30px] border border-dashed border-border/80 bg-card/45 p-8 text-center">
        <div className="max-w-sm">
          <h3 className="text-xl font-display font-bold">Sin puntos para este filtro</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Prueba a ampliar la búsqueda o quitar un filtro de zona para ver más resultados en el mapa.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[30px] border border-border/70 shadow-[0_18px_45px_rgba(0,0,0,0.08)]" style={{ height: '560px' }}>
      <MapContainer
        center={MADRID_CENTER}
        zoom={12}
        minZoom={11}
        maxBounds={MAX_BOUNDS}
        maxBoundsViscosity={0.9}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
        zoomControl={false}
        preferCanvas
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds events={withCoordinates} />
        {withCoordinates.map((event) => (
          <CircleMarker
            key={event.id}
            center={[event.latitud!, event.longitud!]}
            radius={6}
            pathOptions={{
              color: '#ffffff',
              weight: 1.5,
              fillColor: 'var(--primary)',
              fillOpacity: 0.92,
            }}
            eventHandlers={{ click: () => onOpenEvent(event) }}
          >
            <Popup closeButton={false}>
              <button onClick={() => onOpenEvent(event)} className="min-w-[220px] text-left">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary/80">{formatShortDate(event.primaryDate)}</p>
                <h3 className="mt-1 text-sm font-semibold">{event.titulo}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{event.locationLabel}</p>
              </button>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}

