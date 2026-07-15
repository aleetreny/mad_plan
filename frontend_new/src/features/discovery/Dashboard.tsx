import { lazy, Suspense, useCallback, useDeferredValue, useMemo, useState } from 'react';
import { CalendarDays, Dices, Loader2, MapPin, Search, X } from 'lucide-react';
import { SeoHead } from '../../app/seo/SeoHead';
import { getCurrentThemeTime } from '../../domain/madplan/formatters';
import {
  deriveCityStats,
  deriveFacetOptions,
  deriveFeaturedEvents,
  deriveVisibleEvents,
  filterAndRankEvents,
  hasActiveFilters,
} from '../../domain/madplan/filters';
import { PAGE_SIZE } from '../../domain/madplan/constants';
import { useUser } from '../preferences/context/useUser';
import { useMadPlanData } from '../../shared/hooks/useMadPlanData';
import { EventCard } from '../../shared/ui/EventCard';
import { EventModal } from '../../shared/ui/EventModal';
import { Navbar } from '../../shared/ui/Navbar';
import { NewsCard } from '../../shared/ui/NewsCard';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { AgendaDrawer } from '../agenda/AgendaDrawer';
import { FilterBar } from './FilterBar';
import { QuizModal } from '../preferences/QuizModal';
import { VibeSelector } from '../preferences/VibeSelector';
import { useDiscoveryState } from './useDiscoveryState';

const MapView = lazy(() => import('./MapView').then((module) => ({ default: module.MapView })));

const DAYPART_LINE: Record<ReturnType<typeof getCurrentThemeTime>, (n: string) => string> = {
  morning: (n) => `Madrid amanece con ${n} planes`,
  afternoon: (n) => `Madrid encara la tarde con ${n} planes`,
  evening: (n) => `Madrid estira el día con ${n} planes`,
  night: (n) => `Madrid trasnocha con ${n} planes`,
};

function formatUpdatedAt(updatedAt: Date | null): string | null {
  if (!updatedAt) return null;
  const now = new Date();
  const diffHours = Math.round((now.getTime() - updatedAt.getTime()) / 3600000);
  if (diffHours < 1) return 'hace un momento';
  if (diffHours < 24) return `hace ${diffHours} h`;
  const diffDays = Math.round(diffHours / 24);
  return diffDays === 1 ? 'ayer' : `hace ${diffDays} días`;
}

export function Dashboard() {
  const { events, news, updatedAt, loading, error } = useMadPlanData();
  const {
    profile,
    addToAgenda,
    removeFromAgenda,
    isInAgenda,
    setAnsweredQuiz,
    setBudget,
    setCompanion,
    setInterests,
    setVibe,
    setZones,
  } = useUser();
  const [selectedEvent, setSelectedEvent] = useState<MadPlanEvent | null>(null);
  const [agendaOpen, setAgendaOpen] = useState(false);
  const [quizOpen, setQuizOpen] = useState(false);
  const {
    state,
    clearAll,
    loadMore,
    setCategory,
    setDateFilter,
    setFreeOnly,
    setQuery,
    setSource,
    setView,
    setZone,
  } = useDiscoveryState();

  const deferredQuery = useDeferredValue(state.query);
  const effectiveState = useMemo(() => ({ ...state, query: deferredQuery }), [state, deferredQuery]);

  const facets = useMemo(() => deriveFacetOptions(events), [events]);
  const rankedEvents = useMemo(
    () => filterAndRankEvents(events, effectiveState, profile),
    [events, effectiveState, profile],
  );
  const featuredEvents = useMemo(() => deriveFeaturedEvents(events, profile), [events, profile]);
  const stats = useMemo(() => deriveCityStats(events, news), [events, news]);
  const agendaEvents = events.filter((event) => profile.agenda.includes(event.id));
  const filtersActive = hasActiveFilters(state);
  const updatedLabel = formatUpdatedAt(updatedAt);

  // Los destacados no se repiten como primeras tarjetas de la parrilla.
  const featuredShown = useMemo(
    () => (!filtersActive ? featuredEvents.slice(0, 3) : []),
    [featuredEvents, filtersActive],
  );
  const gridEvents = useMemo(() => {
    if (featuredShown.length === 0) return rankedEvents;
    const featuredIds = new Set(featuredShown.map((entry) => entry.event.id));
    return rankedEvents.filter((entry) => !featuredIds.has(entry.event.id));
  }, [rankedEvents, featuredShown]);
  const visibleEvents = deriveVisibleEvents(gridEvents, state.showCount);

  // Deep-link del detalle: abrir un plan escribe ?plan=<id> en la URL, de
  // modo que el enlace se puede compartir y restaurar tal cual.
  const [pendingPlanId, setPendingPlanId] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get('plan'),
  );
  const openEvent = useCallback((event: MadPlanEvent | null) => {
    setPendingPlanId(null);
    setSelectedEvent(event);
    const params = new URLSearchParams(window.location.search);
    if (event) params.set('plan', event.id);
    else params.delete('plan');
    const query = params.toString();
    window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
  }, []);

  // Estado derivado, no efecto: hasta la primera interacción, el ?plan= de la
  // URL de llegada abre su detalle en cuanto los datos están disponibles.
  const effectiveSelectedEvent =
    selectedEvent ??
    (pendingPlanId ? events.find((event) => event.id === pendingPlanId) ?? null : null);

  function surpriseMe() {
    const pool = events.filter((event) => event.isToday || event.isThisWeek || event.isOngoing);
    const candidates = pool.length > 0 ? pool : events;
    if (candidates.length === 0) return;
    openEvent(candidates[Math.floor(Math.random() * candidates.length)]);
  }

  const filterBar = (
    <FilterBar
      categories={facets.categories}
      sources={facets.sources}
      activeCategory={state.category}
      activeSource={state.source}
      dateFilter={state.dateFilter}
      freeOnly={state.freeOnly}
      activeZone={state.zone}
      onCategoryChange={setCategory}
      onSourceChange={setSource}
      onDateFilterChange={setDateFilter}
      onFreeOnlyChange={setFreeOnly}
      onZoneChange={setZone}
      onClear={clearAll}
      hasActiveFilters={filtersActive}
    />
  );

  // Skeletons con la forma real de las tarjetas: la página "aparece" en vez
  // de mostrar un spinner vacío mientras baja el feed.
  const loadingBlock = (
    <div aria-busy="true" aria-label="Cargando planes" className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, index) => (
        <div key={index} className="flex animate-pulse overflow-hidden rounded-2xl border border-border/60 bg-card sm:flex-col sm:rounded-3xl">
          <div className="h-[122px] w-[112px] flex-shrink-0 bg-muted sm:aspect-[16/9] sm:h-auto sm:w-full" />
          <div className="flex-1 space-y-2.5 p-4">
            <div className="h-3 w-1/3 rounded-full bg-muted" />
            <div className="h-4 w-5/6 rounded-full bg-muted" />
            <div className="h-3 w-2/3 rounded-full bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <>
      <SeoHead events={events} news={news} />
      <Navbar
        view={state.view}
        onViewChange={setView}
        agendaCount={agendaEvents.length}
        onOpenAgenda={() => setAgendaOpen(true)}
      />

      <main id="main-content" className="mx-auto flex w-full max-w-[1440px] flex-col gap-7 px-4 py-6 md:px-6 md:py-8">
        {state.view === 'list' ? (
          <>
            <section className="anim-fade-up masthead-rule pt-2">
              <p className="text-[13px] font-medium text-muted-foreground first-letter:uppercase">
                {new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Europe/Madrid' }).format(new Date())}
                <span className="mx-2 text-primary">·</span>
                {DAYPART_LINE[getCurrentThemeTime()](stats.today.toLocaleString('es-ES'))}
              </p>

              <h2 className="mt-3 max-w-3xl font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
                Qué hacer en Madrid, <em className="marker-underline">resuelto</em>.
              </h2>
              <p className="mt-4 max-w-xl text-[15px] leading-7 text-muted-foreground">
                Conciertos, expos, mercados y rutas de {facets.sources.length} agendas distintas,
                cruzadas y sin duplicados. Lo que antes eran veinte pestañas, ahora es esta.
              </p>

              <div className="mt-6 flex max-w-2xl flex-col gap-3 sm:flex-row sm:items-center">
                <label className="min-w-0 flex-1">
                  <span className="sr-only">Buscar planes en Madrid</span>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      data-testid="search-input"
                      value={state.query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Busca por artista, sala, barrio o tema…"
                      className="h-13 w-full rounded-2xl border border-border bg-card pl-11 pr-10 text-[15px] shadow-[0_2px_0_var(--border)] outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary focus:shadow-[0_2px_0_var(--primary)]"
                    />
                    {state.query ? (
                      <button
                        onClick={() => setQuery('')}
                        aria-label="Borrar búsqueda"
                        className="absolute right-2.5 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    ) : null}
                  </div>
                </label>
                <button
                  onClick={surpriseMe}
                  className="inline-flex h-13 flex-shrink-0 items-center justify-center gap-2 rounded-2xl border border-foreground bg-foreground px-5 text-sm font-semibold text-background transition-transform hover:-translate-y-0.5"
                  title="Abre un plan al azar de esta semana"
                >
                  <Dices className="h-4.5 w-4.5" />
                  Sorpréndeme
                </button>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
                <button
                  onClick={() => setDateFilter(state.dateFilter === 'today' ? 'all' : 'today')}
                  aria-pressed={state.dateFilter === 'today'}
                  className={`link-chip ${state.dateFilter === 'today' ? 'link-chip-active' : ''}`}
                >
                  Hoy tengo hueco
                </button>
                <button
                  onClick={() => setDateFilter(state.dateFilter === 'weekend' ? 'all' : 'weekend')}
                  aria-pressed={state.dateFilter === 'weekend'}
                  className={`link-chip ${state.dateFilter === 'weekend' ? 'link-chip-active' : ''}`}
                >
                  Planazo de finde
                </button>
                <button
                  onClick={() => setFreeOnly(!state.freeOnly)}
                  aria-pressed={state.freeOnly}
                  className={`link-chip ${state.freeOnly ? 'link-chip-active' : ''}`}
                >
                  A coste cero
                </button>
                <button onClick={() => setQuizOpen(true)} className="link-chip">
                  {profile.answeredQuiz ? 'Afinar mi perfil' : 'Dime qué me pega'}
                </button>
              </div>

              <p className="mt-5 pb-5 text-xs text-muted-foreground/80">
                {stats.total.toLocaleString('es-ES')} planes vivos · {stats.freeToday} gratis hoy
                {updatedLabel ? ` · actualizado ${updatedLabel}` : ''}
              </p>
            </section>

            <section aria-label="Elige tu vibe">
              <VibeSelector current={profile.vibe} onSelect={setVibe} />
            </section>

            {featuredShown.length > 0 ? (
              <section className="space-y-3">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <p className="kicker">Para ti</p>
                    <h3 className="font-display text-xl font-bold sm:text-2xl">Elegidos con tu criterio</h3>
                  </div>
                  <button
                    onClick={() => setQuizOpen(true)}
                    className="text-sm font-semibold text-primary hover:underline"
                  >
                    Ajustar preferencias
                  </button>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {featuredShown.map(({ event, score }, index) => (
                    <EventCard
                      key={`featured-${event.id}`}
                      event={event}
                      matchScore={score}
                      inAgenda={isInAgenda(event.id)}
                      onOpen={() => openEvent(event)}
                      onToggleAgenda={() =>
                        isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)
                      }
                      priority={index === 0}
                    />
                  ))}
                </div>
              </section>
            ) : null}

            <section className="space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="kicker">La agenda</p>
                  <h3 className="font-display text-xl font-bold sm:text-2xl">Todos los planes</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {gridEvents.length.toLocaleString('es-ES')}{' '}
                    {gridEvents.length === 1 ? 'plan' : 'planes'}
                    {filtersActive ? ' con los filtros actuales' : ' en Madrid'}
                  </p>
                </div>
                <button
                  onClick={() => setView('map')}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-card/70 px-4 py-2 text-sm font-semibold hover:bg-muted/50"
                >
                  <MapPin className="h-4 w-4" />
                  Ver en mapa
                </button>
              </div>

              {filterBar}

              {loading ? loadingBlock : null}

              {!loading && error ? (
                <div className="rounded-3xl border border-red-300/50 bg-red-500/10 p-6 text-sm leading-6 text-red-600">
                  {error}
                </div>
              ) : null}

              {!loading && !error && gridEvents.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-border/80 bg-card/45 p-10 text-center">
                  <h3 className="font-display text-2xl font-bold">Nada por aquí con esos filtros</h3>
                  <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                    Prueba a quitar un filtro, cambiar de zona o ampliar el rango de fechas.
                  </p>
                  <button
                    onClick={clearAll}
                    className="mt-5 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground"
                  >
                    Quitar filtros
                  </button>
                </div>
              ) : null}

              {!loading && gridEvents.length > 0 ? (
                <>
                  <div className="grid gap-3 min-[480px]:gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {visibleEvents.map(({ event, score }, index) => (
                      <EventCard
                        key={event.id}
                        event={event}
                        matchScore={profile.answeredQuiz || profile.vibe ? score : undefined}
                        inAgenda={isInAgenda(event.id)}
                        onOpen={() => openEvent(event)}
                        onToggleAgenda={() =>
                          isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)
                        }
                        priority={index === 0 && state.showCount === PAGE_SIZE}
                      />
                    ))}
                  </div>

                  {state.showCount < gridEvents.length ? (
                    <div className="flex justify-center pt-1">
                      <button
                        onClick={loadMore}
                        className="rounded-full border border-border/80 bg-card px-6 py-3 text-sm font-semibold transition-colors hover:bg-muted/60"
                      >
                        Ver más planes ({(gridEvents.length - state.showCount).toLocaleString('es-ES')} más)
                      </button>
                    </div>
                  ) : null}
                </>
              ) : null}
            </section>

            {news.length > 0 ? (
              <section className="space-y-3 rounded-3xl border border-border/70 bg-card/60 p-5">
                <div className="flex items-end justify-between gap-3">
                  <div>
                    <p className="kicker">El radar</p>
                    <h3 className="font-display text-xl font-bold">Lo que se cuece en Madrid</h3>
                  </div>
                  <button
                    onClick={() => setView('news')}
                    className="text-sm font-semibold text-primary hover:underline"
                  >
                    Todas las noticias
                  </button>
                </div>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {news.slice(0, 3).map((item) => (
                    <NewsCard key={item.id} news={item} />
                  ))}
                </div>
              </section>
            ) : null}
          </>
        ) : null}

        {state.view === 'map' ? (
          <section className="space-y-4">
            <div>
              <p className="kicker">El plano</p>
              <h2 className="font-display text-2xl font-bold sm:text-3xl">Madrid, calle a calle</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {rankedEvents.length.toLocaleString('es-ES')} planes con los filtros actuales. Toca un punto para ver qué hay.
              </p>
            </div>
            {filterBar}
            {loading ? (
              loadingBlock
            ) : (
              <Suspense
                fallback={
                  <div className="grid min-h-[560px] place-items-center rounded-3xl border border-border/70 bg-card/50">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                }
              >
                <MapView events={rankedEvents.map((entry) => entry.event)} onOpenEvent={openEvent} />
              </Suspense>
            )}
          </section>
        ) : null}

        {state.view === 'news' ? (
          <section className="space-y-4">
            <div>
              <p className="kicker">El radar</p>
              <h2 className="font-display text-2xl font-bold sm:text-3xl">Actualidad de Madrid</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Lo último sobre cultura, ocio y ciudad, directo de los medios locales.
              </p>
            </div>
            {loading ? loadingBlock : null}
            {!loading && news.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-border/80 bg-card/45 p-10 text-center">
                <h3 className="font-display text-xl font-bold">Sin noticias recientes</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  El radar se rellena con cada actualización diaria de datos.
                </p>
              </div>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {news.map((item) => (
                <NewsCard key={item.id} news={item} variant="featured" />
              ))}
            </div>
          </section>
        ) : null}
      </main>

      <footer className="mt-4 border-t border-border/70 bg-card/55">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-2 px-4 py-6 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
          <p>
            <span className="font-display font-bold italic text-foreground">madplan<span className="not-italic text-primary">.</span></span>{' '}
            — hecho en Madrid, para no perderse Madrid.
          </p>
          <p className="inline-flex items-center gap-1.5">
            <CalendarDays className="h-4 w-4" />
            {updatedLabel ? `Agenda actualizada ${updatedLabel}` : 'La agenda se refresca cada mañana'} · {facets.sources.length} fuentes
          </p>
        </div>
      </footer>

      <QuizModal
        open={quizOpen}
        onClose={() => setQuizOpen(false)}
        onFinish={({ interests, vibe, budget, companion, zones }) => {
          setInterests(interests);
          setVibe(vibe);
          setBudget(budget);
          setCompanion(companion);
          setZones(zones);
          setAnsweredQuiz(true);
          setQuizOpen(false);
        }}
      />
      <EventModal
        event={effectiveSelectedEvent}
        inAgenda={effectiveSelectedEvent ? isInAgenda(effectiveSelectedEvent.id) : false}
        matchScore={effectiveSelectedEvent ? rankedEvents.find((entry) => entry.event.id === effectiveSelectedEvent.id)?.score : undefined}
        onClose={() => openEvent(null)}
        onToggleAgenda={() => {
          if (!effectiveSelectedEvent) return;
          if (isInAgenda(effectiveSelectedEvent.id)) removeFromAgenda(effectiveSelectedEvent.id);
          else addToAgenda(effectiveSelectedEvent.id);
        }}
      />
      <AgendaDrawer
        open={agendaOpen}
        events={agendaEvents}
        onClose={() => setAgendaOpen(false)}
        onRemove={removeFromAgenda}
        onOpenEvent={(event) => {
          setAgendaOpen(false);
          openEvent(event);
        }}
      />
    </>
  );
}
