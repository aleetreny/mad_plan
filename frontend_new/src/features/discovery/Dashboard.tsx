import { lazy, Suspense, useDeferredValue, useState } from 'react';
import { motion } from 'framer-motion';
import { Compass, Loader2, Map, Search, Sparkles, TrendingUp } from 'lucide-react';
import { SeoHead } from '../../app/seo/SeoHead';
import { deriveCityStats, deriveFacetOptions, deriveFeaturedEvents, deriveVisibleEvents, filterAndRankEvents, hasActiveFilters } from '../../domain/madplan/filters';
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

export function Dashboard() {
  const { events, news, loading, error } = useMadPlanData();
  const { profile, addToAgenda, removeFromAgenda, isInAgenda, setAnsweredQuiz, setBudget, setCompanion, setInterests, setVibe, setZones } = useUser();
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
  const effectiveState = { ...state, query: deferredQuery };
  const facets = deriveFacetOptions(events);
  const rankedEvents = filterAndRankEvents(events, effectiveState, profile);
  const featuredEvents = deriveFeaturedEvents(events, profile);
  const visibleEvents = deriveVisibleEvents(rankedEvents, state.showCount);
  const stats = deriveCityStats(events, news);
  const agendaEvents = events.filter((event) => profile.agenda.includes(event.id));
  const filterSummary = hasActiveFilters(state);

  return (
    <>
      <SeoHead events={events} news={news} />
      <Navbar
        agendaCount={profile.agenda.length}
        onOpenAgenda={() => setAgendaOpen(true)}
        onToggleView={() => setView(state.view === 'list' ? 'map' : 'list')}
        isMapView={state.view === 'map'}
      />

      <main id="main-content" className="mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-4 py-6 md:px-6 md:py-8">
        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)]">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.32 }}
            className="relative overflow-hidden rounded-[36px] border border-border/60 bg-[linear-gradient(140deg,rgba(255,255,255,0.18),transparent_40%),radial-gradient(circle_at_top_left,rgba(255,255,255,0.22),transparent_45%),linear-gradient(160deg,var(--hero-from),var(--hero-to))] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.14)] md:p-8"
          >
            <div className="relative z-10 max-w-3xl">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/18 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/92 backdrop-blur-md">
                <Sparkles className="h-4 w-4" />
                La portada útil de Madrid
              </span>
              <h2 className="mt-5 max-w-2xl text-4xl font-display font-bold leading-tight text-white md:text-6xl">
                Encuentra un plan bueno en minutos, no en veinte pestañas.
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-7 text-white/82 md:text-lg">
                MadPlan cruza agenda cultural, ocio, barrio y actualidad para que la búsqueda sea clara, rápida y coherente.
              </p>

              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {stats.map((stat) => (
                  <div key={stat.label} className="rounded-[24px] border border-white/10 bg-black/16 p-4 text-white backdrop-blur-md">
                    <p className="text-2xl font-display font-bold md:text-3xl">{stat.value}</p>
                    <p className="mt-1 text-sm text-white/78">{stat.label}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  onClick={() => setQuizOpen(true)}
                  className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-900 shadow-[0_18px_45px_rgba(0,0,0,0.16)]"
                >
                  <Sparkles className="h-4 w-4" />
                  {profile.answeredQuiz ? 'Refinar preferencias' : 'Descubrir mi vibe'}
                </button>
                <button
                  onClick={() => setView(state.view === 'list' ? 'map' : 'list')}
                  className="inline-flex items-center gap-2 rounded-full border border-white/18 bg-black/16 px-5 py-3 text-sm font-semibold text-white backdrop-blur-md"
                >
                  {state.view === 'list' ? <Map className="h-4 w-4" /> : <Compass className="h-4 w-4" />}
                  {state.view === 'list' ? 'Abrir mapa' : 'Volver a lista'}
                </button>
              </div>
            </div>
          </motion.div>

          <aside className="rounded-[36px] border border-border/70 bg-card/75 p-6 shadow-[0_24px_70px_rgba(0,0,0,0.08)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Búsqueda instantánea</p>
            <h3 className="mt-3 text-2xl font-display font-bold">Tu radar editorial</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Busca por artista, barrio, venue o categoría y deja la agenda en el estado exacto que quieras compartir.
            </p>

            <label className="mt-5 block">
              <span className="sr-only">Buscar en MadPlan</span>
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  data-testid="search-input"
                  value={state.query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar eventos, salas, barrios o temáticas"
                  className="h-14 w-full rounded-[22px] border border-border/70 bg-background/80 pl-11 pr-4 text-sm outline-none ring-0 transition-colors placeholder:text-muted-foreground focus:border-primary"
                />
              </div>
            </label>

            <div className="mt-5 grid gap-3">
              <button
                onClick={() => setDateFilter('today')}
                className="rounded-[24px] border border-border/70 bg-background/70 px-4 py-4 text-left hover:border-primary/40"
              >
                <p className="text-sm font-semibold">Planes para hoy</p>
                <p className="mt-1 text-sm text-muted-foreground">Corta el ruido y empieza por lo inmediato.</p>
              </button>
              <button
                onClick={() => setFreeOnly(true)}
                className="rounded-[24px] border border-border/70 bg-background/70 px-4 py-4 text-left hover:border-primary/40"
              >
                <p className="text-sm font-semibold">Solo gratis</p>
                <p className="mt-1 text-sm text-muted-foreground">Ideal para resolver una tarde sin fricción.</p>
              </button>
              <button
                onClick={clearAll}
                className="rounded-[24px] border border-dashed border-border/70 bg-transparent px-4 py-4 text-left hover:border-primary/40"
              >
                <p className="text-sm font-semibold">Reset limpio</p>
                <p className="mt-1 text-sm text-muted-foreground">Vuelve a la portada editorial completa.</p>
              </button>
            </div>
          </aside>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Personalización</p>
              <h3 className="text-2xl font-display font-bold">¿Qué plan te apetece hoy?</h3>
            </div>
            {profile.vibe ? (
              <button onClick={() => setVibe(null)} className="rounded-full border border-border/70 px-4 py-2 text-sm font-semibold hover:bg-muted/60">
                Quitar vibe
              </button>
            ) : null}
          </div>
          <VibeSelector current={profile.vibe} onSelect={setVibe} />
        </section>

        {featuredEvents.length > 0 ? (
          <section className="rounded-[34px] border border-border/70 bg-card/80 p-5 shadow-[0_20px_50px_rgba(0,0,0,0.06)] md:p-6">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Recomendación</p>
                <h3 className="text-2xl font-display font-bold">Para tu perfil de hoy</h3>
              </div>
              <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
                Afinado con tu quiz
              </span>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {featuredEvents.map(({ event, score }, index) => (
                <EventCard
                  key={`featured-${event.id}`}
                  event={event}
                  matchScore={score}
                  inAgenda={isInAgenda(event.id)}
                  onOpen={() => setSelectedEvent(event)}
                  onToggleAgenda={() => isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)}
                  priority={index === 0}
                />
              ))}
            </div>
          </section>
        ) : null}

        <section className="grid gap-8 xl:grid-cols-[minmax(0,1.45fr)_360px]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Explorador</p>
                <h3 className="flex items-center gap-2 text-3xl font-display font-bold">
                  <TrendingUp className="h-7 w-7 text-primary" />
                  Planes en Madrid
                </h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {rankedEvents.length} resultados coherentes con los filtros actuales.
                </p>
              </div>
              <div className="rounded-full border border-border/70 bg-card/70 px-4 py-2 text-sm font-semibold">
                Vista {state.view === 'map' ? 'mapa' : 'lista'}
              </div>
            </div>

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
              hasActiveFilters={filterSummary}
            />

            {loading ? (
              <div className="grid min-h-[360px] place-items-center rounded-[30px] border border-border/70 bg-card/50">
                <div className="text-center">
                  <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
                  <p className="mt-3 text-sm text-muted-foreground">Cargando el pulso real de Madrid…</p>
                </div>
              </div>
            ) : null}

            {!loading && error && events.length === 0 ? (
              <div className="rounded-[30px] border border-red-200 bg-red-50 p-6 text-red-700">
                {error}
              </div>
            ) : null}

            {!loading && events.length > 0 ? (
              state.view === 'map' ? (
                <Suspense
                  fallback={
                    <div className="grid min-h-[560px] place-items-center rounded-[30px] border border-border/70 bg-card/50">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                  }
                >
                  <MapView events={rankedEvents.map((entry) => entry.event)} onOpenEvent={setSelectedEvent} />
                </Suspense>
              ) : rankedEvents.length === 0 ? (
                <div className="rounded-[30px] border border-dashed border-border/80 bg-card/45 p-8 text-center">
                  <h3 className="text-2xl font-display font-bold">No hay resultados para esta combinación</h3>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    Prueba a quitar un filtro, ampliar zona o cambiar el rango temporal.
                  </p>
                  <button onClick={clearAll} className="mt-5 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground">
                    Limpiar filtros
                  </button>
                </div>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2">
                    {visibleEvents.map(({ event, score }, index) => (
                      <EventCard
                        key={event.id}
                        event={event}
                        matchScore={score}
                        inAgenda={isInAgenda(event.id)}
                        onOpen={() => setSelectedEvent(event)}
                        onToggleAgenda={() => isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)}
                        priority={index === 0 && state.showCount === PAGE_SIZE}
                      />
                    ))}
                  </div>

                  {state.showCount < rankedEvents.length ? (
                    <div className="flex justify-center">
                      <button
                        onClick={loadMore}
                        className="rounded-full border border-border/80 bg-card px-5 py-3 text-sm font-semibold hover:bg-muted/60"
                      >
                        Cargar más planes ({rankedEvents.length - state.showCount} restantes)
                      </button>
                    </div>
                  ) : null}
                </>
              )
            ) : null}
          </div>

          <aside className="space-y-5">
            <section className="rounded-[32px] border border-border/70 bg-card/80 p-5 shadow-[0_18px_46px_rgba(0,0,0,0.06)]">
              <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Radar cultural</p>
                <h3 className="text-2xl font-display font-bold">Actualidad Madrid</h3>
              </div>
              <div className="space-y-3">
                {news.slice(0, 6).map((item) => (
                  <NewsCard key={item.id} news={item} />
                ))}
              </div>
            </section>

            <section className="rounded-[32px] border border-border/70 bg-card/80 p-5 shadow-[0_18px_46px_rgba(0,0,0,0.06)]">
              <div className="mb-4">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Cobertura</p>
                <h3 className="text-2xl font-display font-bold">Qué resuelve esta versión</h3>
              </div>
              <ul className="space-y-3 text-sm leading-6 text-muted-foreground">
                <li>Filtros sincronizados con la URL para compartir una búsqueda exacta.</li>
                <li>Agenda persistente en local sin duplicados ni pérdidas de estado.</li>
                <li>Mapa limitado a coordenadas válidas de Madrid para evitar ruido.</li>
                <li>Modal con sesiones, múltiples enlaces y acciones de compartir reales.</li>
              </ul>
            </section>
          </aside>
        </section>
      </main>

      <footer className="border-t border-border/70 bg-card/55">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3 px-4 py-6 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-6">
          <p>MadPlan convierte la agenda fragmentada de Madrid en una experiencia clara, rápida y editorial.</p>
          <p>Datos de venues, agregadores y medios combinados en una sola capa de descubrimiento.</p>
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
      <AgendaDrawer open={agendaOpen} events={agendaEvents} onClose={() => setAgendaOpen(false)} onRemove={removeFromAgenda} />
    </>
  );
}

