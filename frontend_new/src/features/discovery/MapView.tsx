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
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    previousKey.current = key;
  }, [events, map]);

  return null;
}

interface MapViewProps {
  events: MadPlanEvent[];
  onOpenEvent: (event: MadPlanEvent) => void;
}

export function MapView({ events, onOpenEvent }: MapViewProps) {
  const { timeOfDay } = useTheme();
  const darkTiles = timeOfDay === 'night';

  const withCoordinates = useMemo(
    () => events.filter((event) => event.hasCoordinates && event.latitud != null && event.longitud != null),
    [events],
  );

  if (withCoordinates.length === 0) {
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
    <div className="relative overflow-hidden rounded-3xl border border-border/70 shadow-[0_10px_36px_rgba(15,10,5,0.08)]" style={{ height: '620px' }}>
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
        <FitBounds events={withCoordinates} />
        {withCoordinates.map((event) => (
          <CircleMarker
            key={event.id}
            center={[event.latitud!, event.longitud!]}
            radius={7}
            pathOptions={{
              color: darkTiles ? '#0f1720' : '#ffffff',
              weight: 1.5,
              fillColor: categoryMeta(event.primaryCategory).from,
              fillOpacity: 0.94,
            }}
          >
            <Popup closeButton={false} className="madplan-popup">
              <div className="min-w-[220px] max-w-[260px]">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary">
                  {event.scheduleLabel}
                </p>
                <h3 className="mt-1 font-display text-sm font-bold leading-snug">{event.titulo}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{event.lugar || event.direccion}</p>
                <button
                  onClick={() => onOpenEvent(event)}
                  className="mt-2.5 inline-flex h-8 items-center rounded-full bg-primary px-3.5 text-xs font-semibold text-primary-foreground"
                >
                  Ver detalle
                </button>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="pointer-events-none absolute bottom-3 left-3 z-[400] rounded-full bg-black/55 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur-md">
        {withCoordinates.length} planes en el mapa
      </div>
    </div>
  );
}
