import { lazy, Suspense, useDeferredValue, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { CalendarDays, Loader2, MapPin, Newspaper, Search, Sparkles, Ticket } from 'lucide-react';
import { SeoHead } from '../../app/seo/SeoHead';
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
  const visibleEvents = deriveVisibleEvents(rankedEvents, state.showCount);
  const stats = useMemo(() => deriveCityStats(events, news), [events, news]);
  const agendaEvents = events.filter((event) => profile.agenda.includes(event.id));
  const filtersActive = hasActiveFilters(state);
  const updatedLabel = formatUpdatedAt(updatedAt);

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

  const loadingBlock = (
    <div className="grid min-h-[320px] place-items-center rounded-3xl border border-border/70 bg-card/50">
      <div className="text-center">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
        <p className="mt-3 text-sm text-muted-foreground">Cargando los planes de Madrid…</p>
      </div>
    </div>
  );

  return (
    <>
      <SeoHead events={events} news={news} />
      <Navbar
        view={state.view}
        onViewChange={setView}
        agendaCount={profile.agenda.length}
        onOpenAgenda={() => setAgendaOpen(true)}
      />

      <main id="main-content" className="mx-auto flex w-full max-w-[1280px] flex-col gap-7 px-4 py-6 md:px-6 md:py-8">
        {state.view === 'list' ? (
          <>
            <motion.section
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="relative overflow-hidden rounded-[28px] border border-border/50 bg-[linear-gradient(150deg,var(--hero-from),var(--hero-to))] px-5 py-8 shadow-[0_18px_60px_rgba(0,0,0,0.14)] sm:px-8 sm:py-10"
            >
              <div
                className="pointer-events-none absolute inset-0 opacity-20"
                style={{
                  backgroundImage: 'radial-gradient(circle at 85% 10%, rgba(255,255,255,0.55), transparent 45%)',
                }}
              />
              <div className="relative z-10 mx-auto max-w-3xl text-center">
                <h2 className="font-display text-3xl font-bold leading-tight text-white sm:text-5xl">
                  ¿Qué plan hay hoy en Madrid?
                </h2>
                <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-white/85 sm:text-base">
                  Conciertos, expos, mercados y rutas de {facets.sources.length} fuentes, en un solo sitio y sin ruido.
                </p>

                <label className="mx-auto mt-6 block max-w-xl">
                  <span className="sr-only">Buscar planes en Madrid</span>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-500" />
                    <input
                      data-testid="search-input"
                      value={state.query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Busca por artista, sala, barrio o tema…"
                      className="h-13 w-full rounded-full border-0 bg-white/95 pl-11 pr-4 text-[15px] text-slate-900 shadow-[0_10px_36px_rgba(0,0,0,0.18)] outline-none ring-0 transition placeholder:text-slate-400 focus:bg-white"
                    />
                  </div>
                </label>

                <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                  <button
                    onClick={() => setDateFilter(state.dateFilter === 'today' ? 'all' : 'today')}
                    aria-pressed={state.dateFilter === 'today'}
                    className={`rounded-full px-4 py-2 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/25 ${state.dateFilter === 'today' ? 'bg-white/35 ring-1 ring-white/60' : 'bg-white/15'}`}
                  >
                    Hoy · {stats.today}
                  </button>
                  <button
                    onClick={() => setDateFilter(state.dateFilter === 'weekend' ? 'all' : 'weekend')}
                    aria-pressed={state.dateFilter === 'weekend'}
                    className={`rounded-full px-4 py-2 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/25 ${state.dateFilter === 'weekend' ? 'bg-white/35 ring-1 ring-white/60' : 'bg-white/15'}`}
                  >
                    Este finde
                  </button>
                  <button
                    onClick={() => setFreeOnly(!state.freeOnly)}
                    aria-pressed={state.freeOnly}
                    className={`rounded-full px-4 py-2 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/25 ${state.freeOnly ? 'bg-white/35 ring-1 ring-white/60' : 'bg-white/15'}`}
                  >
                    Gratis
                  </button>
                  <button
                    onClick={() => setQuizOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-sm font-bold text-slate-900 shadow-md transition hover:-translate-y-0.5"
                  >
                    <Sparkles className="h-4 w-4" />
                    {profile.answeredQuiz ? 'Afinar mi perfil' : 'Planes a mi medida'}
                  </button>
                </div>

                <p className="mt-5 text-xs font-medium text-white/70">
                  {stats.total.toLocaleString('es-ES')} planes activos · {stats.freeToday} gratis hoy
                  {updatedLabel ? ` · datos actualizados ${updatedLabel}` : ''}
                </p>
              </div>
            </motion.section>

            <section aria-label="Elige tu vibe">
              <VibeSelector current={profile.vibe} onSelect={setVibe} />
            </section>

            {featuredEvents.length > 0 && !filtersActive ? (
              <section className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="flex items-center gap-2 font-display text-xl font-bold sm:text-2xl">
                    <Sparkles className="h-5 w-5 text-primary" />
                    Elegidos para ti
                  </h3>
                  <button
                    onClick={() => setQuizOpen(true)}
                    className="text-sm font-semibold text-primary hover:underline"
                  >
                    Ajustar preferencias
                  </button>
                </div>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {featuredEvents.slice(0, 3).map(({ event, score }, index) => (
                    <EventCard
                      key={`featured-${event.id}`}
                      event={event}
                      matchScore={score}
                      inAgenda={isInAgenda(event.id)}
                      onOpen={() => setSelectedEvent(event)}
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
                  <h3 className="flex items-center gap-2 font-display text-xl font-bold sm:text-2xl">
                    <Ticket className="h-5 w-5 text-primary" />
                    Todos los planes
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {rankedEvents.length.toLocaleString('es-ES')}{' '}
                    {rankedEvents.length === 1 ? 'plan' : 'planes'}
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

              {!loading && !error && rankedEvents.length === 0 ? (
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

              {!loading && rankedEvents.length > 0 ? (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {visibleEvents.map(({ event, score }, index) => (
                      <EventCard
                        key={event.id}
                        event={event}
                        matchScore={profile.answeredQuiz || profile.vibe ? score : undefined}
                        inAgenda={isInAgenda(event.id)}
                        onOpen={() => setSelectedEvent(event)}
                        onToggleAgenda={() =>
                          isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)
                        }
                        priority={index === 0 && state.showCount === PAGE_SIZE}
                      />
                    ))}
                  </div>

                  {state.showCount < rankedEvents.length ? (
                    <div className="flex justify-center pt-1">
                      <button
                        onClick={loadMore}
                        className="rounded-full border border-border/80 bg-card px-6 py-3 text-sm font-semibold transition-colors hover:bg-muted/60"
                      >
                        Ver más planes ({(rankedEvents.length - state.showCount).toLocaleString('es-ES')} más)
                      </button>
                    </div>
                  ) : null}
                </>
              ) : null}
            </section>

            {news.length > 0 ? (
              <section className="space-y-3 rounded-3xl border border-border/70 bg-card/60 p-5">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="flex items-center gap-2 font-display text-xl font-bold">
                    <Newspaper className="h-5 w-5 text-primary" />
                    Radar Madrid
                  </h3>
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
              <h2 className="font-display text-2xl font-bold sm:text-3xl">Madrid en el mapa</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {rankedEvents.length.toLocaleString('es-ES')} planes con los filtros actuales. Toca un punto para ver el detalle.
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
                <MapView events={rankedEvents.map((entry) => entry.event)} onOpenEvent={setSelectedEvent} />
              </Suspense>
            )}
          </section>
        ) : null}

        {state.view === 'news' ? (
          <section className="space-y-4">
            <div>
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
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {news.map((item) => (
                <NewsCard key={item.id} news={item} variant="featured" />
              ))}
            </div>
          </section>
        ) : null}
      </main>

      <footer className="mt-4 border-t border-border/70 bg-card/55">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-2 px-4 py-6 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
          <p>
            <span className="font-display font-bold text-foreground">MadPlan</span> · la agenda de Madrid en un solo sitio.
          </p>
          <p className="inline-flex items-center gap-1.5">
            <CalendarDays className="h-4 w-4" />
            {updatedLabel ? `Datos actualizados ${updatedLabel}` : 'Datos de fuentes públicas de Madrid'}
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
        event={selectedEvent}
        inAgenda={selectedEvent ? isInAgenda(selectedEvent.id) : false}
        matchScore={selectedEvent ? rankedEvents.find((entry) => entry.event.id === selectedEvent.id)?.score : undefined}
        onClose={() => setSelectedEvent(null)}
        onToggleAgenda={() => {
          if (!selectedEvent) return;
          if (isInAgenda(selectedEvent.id)) removeFromAgenda(selectedEvent.id);
          else addToAgenda(selectedEvent.id);
        }}
      />
      <AgendaDrawer
        open={agendaOpen}
        events={agendaEvents}
        onClose={() => setAgendaOpen(false)}
        onRemove={removeFromAgenda}
        onOpenEvent={(event) => {
          setAgendaOpen(false);
          setSelectedEvent(event);
        }}
      />
    </>
  );
}
