import { useEffect, useMemo, useRef } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { categoryMeta, MADRID_BOUNDS, MADRID_CENTER } from '../../domain/madplan/constants';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { useTheme } from '../theme/context/useTheme';

const MAX_BOUNDS = L.latLngBounds(
  [MADRID_BOUNDS.latMin, MADRID_BOUNDS.lonMin],
  [MADRID_BOUNDS.latMax, MADRID_BOUNDS.lonMax],
);

const MAX_POPUP_EVENTS = 7;

interface MapPoint {
  key: string;
  lat: number;
  lon: number;
  events: MadPlanEvent[];
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  const previousKey = useRef('');

  useEffect(() => {
    if (points.length === 0) {
      map.setView(MADRID_CENTER, 12);
      previousKey.current = '';
      return;
    }

    const key = points.map((point) => point.key).join('|');
    if (key === previousKey.current) return;

    const bounds = L.latLngBounds(points.map((point) => [point.lat, point.lon] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    previousKey.current = key;
  }, [points, map]);

  return null;
}

interface MapViewProps {
  events: MadPlanEvent[];
  onOpenEvent: (event: MadPlanEvent) => void;
}

export function MapView({ events, onOpenEvent }: MapViewProps) {
  const { timeOfDay } = useTheme();
  const darkTiles = timeOfDay === 'night';

  // Many events share one venue (Matadero, IFEMA…). One marker per venue
  // with the full list in the popup beats 50 stacked, unclickable dots.
  const points = useMemo(() => {
    const byPoint = new Map<string, MapPoint>();
    events.forEach((event) => {
      if (!event.hasCoordinates || event.latitud == null || event.longitud == null) return;
      const key = `${event.latitud.toFixed(4)},${event.longitud.toFixed(4)}`;
      const existing = byPoint.get(key);
      if (existing) {
        existing.events.push(event);
      } else {
        byPoint.set(key, { key, lat: event.latitud, lon: event.longitud, events: [event] });
      }
    });
    return Array.from(byPoint.values());
  }, [events]);

  const totalOnMap = points.reduce((sum, point) => sum + point.events.length, 0);

  if (points.length === 0) {
    return (
      <div className="grid min-h-[560px] place-items-center rounded-3xl border border-dashed border-border/80 bg-card/45 p-8 text-center">
        <div className="max-w-sm">
          <h3 className="font-display text-xl font-bold">Sin puntos para estos filtros</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Amplía la búsqueda o quita algún filtro para ver más planes en el mapa.
          </p>
        </div>
      </div>
    );
  }

  return (
    // `isolate` creates a stacking context so Leaflet's internal z-indexes
    // (400-1000) can never sit above the app's modals and drawers.
    <div className="relative isolate overflow-hidden rounded-3xl border border-border/70 shadow-[0_10px_36px_rgba(15,10,5,0.08)] h-[65vh] min-h-[420px] sm:h-[620px]">
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
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
          url={`https://{s}.basemaps.cartocdn.com/${darkTiles ? 'dark_all' : 'light_all'}/{z}/{x}/{y}{r}.png`}
        />
        <FitBounds points={points} />
        {points.map((point) => {
          const [first] = point.events;
          const count = point.events.length;
          const radius = count === 1 ? 7 : Math.min(15, 8 + Math.log2(count) * 2);
          return (
            <CircleMarker
              key={point.key}
              center={[point.lat, point.lon]}
              radius={radius}
              pathOptions={{
                color: darkTiles ? '#0f1720' : '#ffffff',
                weight: 1.5,
                fillColor: categoryMeta(first.primaryCategory).from,
                fillOpacity: 0.94,
              }}
            >
              <Popup closeButton={false} className="madplan-popup" maxWidth={300}>
                {count === 1 ? (
                  <div className="min-w-[220px] max-w-[260px]">
                    <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary">
                      {first.scheduleLabel}
                    </p>
                    <h3 className="mt-1 font-display text-sm font-bold leading-snug">{first.titulo}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">{first.lugar || first.direccion}</p>
                    <button
                      onClick={() => onOpenEvent(first)}
                      className="mt-2.5 inline-flex h-8 items-center rounded-full bg-primary px-3.5 text-xs font-semibold text-primary-foreground"
                    >
                      Ver detalle
                    </button>
                  </div>
                ) : (
                  <div className="min-w-[230px] max-w-[280px]">
                    <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary">
                      {count} planes aquí
                    </p>
                    <h3 className="mt-0.5 font-display text-sm font-bold leading-snug">
                      {first.lugar || first.direccion || 'Mismo sitio'}
                    </h3>
                    <div className="mt-2 max-h-[210px] space-y-1 overflow-y-auto pr-1">
                      {point.events.slice(0, MAX_POPUP_EVENTS).map((event) => (
                        <button
                          key={event.id}
                          onClick={() => onOpenEvent(event)}
                          className="block w-full rounded-lg border border-border/60 bg-background/70 px-2.5 py-1.5 text-left text-xs leading-snug hover:border-primary/50 hover:text-primary"
                        >
                          <span className="mr-1.5 font-semibold text-primary/85">{event.scheduleLabel}</span>
                          {event.titulo.length > 52 ? `${event.titulo.slice(0, 51)}…` : event.titulo}
                        </button>
                      ))}
                      {count > MAX_POPUP_EVENTS ? (
                        <p className="px-1 pt-0.5 text-[11px] text-muted-foreground">
                          y {count - MAX_POPUP_EVENTS} planes más en este sitio
                        </p>
                      ) : null}
                    </div>
                  </div>
                )}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-3 left-3 z-[400] rounded-full bg-black/55 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur-md">
        {totalOnMap} planes en {points.length} sitios
      </div>
    </div>
  );
}
