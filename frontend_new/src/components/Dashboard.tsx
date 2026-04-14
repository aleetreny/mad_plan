import { useState, useMemo, lazy, Suspense } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, TrendingUp, Map as MapIcon, List, Loader2, Search, CalendarRange, X } from 'lucide-react';
import { useMadPlanData } from '../hooks/useMadPlanData';
import { useMatchScore } from '../hooks/useMatchScore';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../context/UserContext';
import { EventCard } from './EventCard';
import { NewsCard } from './NewsCard';
import { FilterBar } from './FilterBar';
import { VibeSelector } from './VibeSelector';
import { QuizModal } from './QuizModal';
import { EventModal } from './EventModal';
import type { MadPlanEvent } from '../types';

const MapView = lazy(() => import('./MapView').then(m => ({ default: m.MapView })));

const BARRIOS = ['Malasaña', 'Chueca', 'Lavapiés', 'Chamberí', 'Salamanca', 'Retiro', 'La Latina', 'Usera', 'Tetuán', 'Chamartín', 'Sol', 'Arganzuela', 'Moncloa', 'Carabanchel', 'Vallecas'];

export function Dashboard() {
  const { events, news, loading, error } = useMadPlanData();
  const { timeOfDay } = useTheme();
  const { profile, addToAgenda, removeFromAgenda, isInAgenda, setVibe, setInterests, setAnsweredQuiz } = useUser();

  const [selectedEvent, setSelectedEvent] = useState<MadPlanEvent | null>(null);
  const [quizOpen, setQuizOpen] = useState(false);
  const [showCount, setShowCount] = useState(12);
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');

  // Filters
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('all');
  const [freeOnly, setFreeOnly] = useState(false);
  const [activeBarrio, setActiveBarrio] = useState<string | null>(null);

  // Search
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Match scores
  const scored = useMatchScore(events, profile);

  // Derived filter lists
  const sources = useMemo(() => {
    const s = new Set(events.map(e => e.fuente));
    return Array.from(s).sort();
  }, [events]);

  const categories = useMemo((): string[] => {
    const c: Record<string, number> = {};
    events.forEach(e => {
      const normCats = e.categorias_normalizadas || [];
      normCats.forEach(cat => { c[cat] = (c[cat] || 0) + 1; });
      if (normCats.length === 0) {
        const cat = e.categoria_principal || e.categorias?.[0];
        if (cat) c[cat] = (c[cat] || 0) + 1;
      }
    });
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k]) => k);
  }, [events]);

  // Filter logic
  const filteredScored = useMemo(() => {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const weekEnd = new Date(today); weekEnd.setDate(weekEnd.getDate() + 7);
    const monthEnd = new Date(today); monthEnd.setMonth(monthEnd.getMonth() + 1);
    const sq = searchQuery.trim().toLowerCase();
    const fromDate = dateFrom ? new Date(dateFrom) : null;
    const toDate = dateTo ? new Date(dateTo) : null;

    return scored.filter(({ event }) => {
      if (activeSource && event.fuente !== activeSource) return false;

      // Category filtering using normalized categories
      if (activeCategory) {
        const normCats = event.categorias_normalizadas || [];
        const allCats = [...normCats, event.categoria_principal, ...(event.categorias || [])];
        if (!allCats.includes(activeCategory)) return false;
      }

      if (freeOnly && !event.es_gratis) return false;

      // Barrio filtering
      if (activeBarrio) {
        const searchIn = [event.lugar, event.direccion].filter(Boolean).join(' ').toLowerCase();
        if (!searchIn.includes(activeBarrio.toLowerCase())) return false;
      }

      // Search query
      if (sq) {
        const blob = [event.titulo, event.resumen, event.descripcion, event.lugar, event.direccion,
          ...(event.categorias_normalizadas || []), ...(event.categorias || []), ...(event.etiquetas || [])
        ].filter(Boolean).join(' ').toLowerCase();
        if (!blob.includes(sq)) return false;
      }

      // Date range filter
      const raw = event.sort_datetime || event.proximo_datetime || event.fecha_inicio;
      if (fromDate || toDate) {
        if (!raw) return false;
        const d = new Date(raw); d.setHours(0, 0, 0, 0);
        if (fromDate && d < fromDate) return false;
        if (toDate && d > toDate) return false;
      } else if (dateFilter !== 'all') {
        if (!raw) return false;
        const d = new Date(raw); d.setHours(0, 0, 0, 0);
        if (dateFilter === 'today' && d.getTime() !== today.getTime()) return false;
        if (dateFilter === 'week' && (d < today || d > weekEnd)) return false;
        if (dateFilter === 'month' && (d < today || d > monthEnd)) return false;
      }
      return true;
    });
  }, [scored, activeSource, activeCategory, dateFilter, freeOnly, activeBarrio, searchQuery, dateFrom, dateTo]);

  // Sort: scored first, then by date
  const sorted = useMemo(() => {
    return [...filteredScored].sort((a, b) => {
      // When quiz is answered, strongly prioritize high match scores
      if (profile.answeredQuiz) {
        if (a.score !== b.score) return b.score - a.score;
      }
      const da = a.event.sort_datetime || '';
      const db = b.event.sort_datetime || '';
      return da.localeCompare(db);
    });
  }, [filteredScored, profile.answeredQuiz]);

  const displayed = sorted.slice(0, showCount);

  // Vibe-recommended events
  const vibeEvents = useMemo(() => {
    if (!profile.vibe) return [];
    return scored
      .filter(s => s.score > 20)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);
  }, [scored, profile.vibe]);

  const greetings = {
    morning: '¡Buenos días, Madrid!',
    afternoon: '¡Buenas tardes, Madrid!',
    evening: '¡Buenas noches, Madrid!',
    night: 'Madrid nunca duerme...',
  };

  const heroTexts = {
    morning: 'Empieza el día con energía. Aquí tienes los mejores planes para hoy.',
    afternoon: 'El sol brilla sobre la Cibeles. ¿Qué tal un paseo o una expo?',
    evening: 'La ciudad se ilumina. Es hora de disfrutar de la mejor gastronomía y ocio.',
    night: 'Descubre los secretos de la noche madrileña.',
  };

  const hasSearchFilters = searchQuery || dateFrom || dateTo;
  const clearSearch = () => { setSearchQuery(''); setDateFrom(''); setDateTo(''); };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-20 flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <p className="text-muted-foreground font-medium">Cargando el pulso de Madrid...</p>
      </div>
    );
  }

  if (error && events.length === 0) {
    return <div className="container mx-auto px-4 py-20 text-center text-red-500 font-medium">{error}</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Hero */}
      <section className="mb-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden rounded-3xl bg-primary/10 p-8 md:p-12"
        >
          <div className="relative z-10 max-w-2xl">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 mb-4 text-xs font-bold rounded-full bg-primary text-primary-foreground">
              <Sparkles className="w-3 h-3" /> Recomendado para ti
            </span>
            <h2 className="text-4xl md:text-6xl font-display font-bold mb-4 leading-tight">{greetings[timeOfDay]}</h2>
            <p className="text-lg md:text-xl text-muted-foreground mb-8">{heroTexts[timeOfDay]}</p>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => setQuizOpen(true)}
                className="px-8 py-3 rounded-full bg-primary text-primary-foreground font-bold shadow-lg shadow-primary/20 hover:opacity-90 transition-opacity"
              >
                {profile.answeredQuiz ? 'Repetir quiz' : '¿Cuál es tu vibe?'}
              </button>
              <button
                onClick={() => setViewMode(v => v === 'list' ? 'map' : 'list')}
                className="px-8 py-3 rounded-full border bg-background/50 backdrop-blur-sm font-bold flex items-center gap-2 hover:bg-muted transition-colors"
              >
                {viewMode === 'list' ? <><MapIcon className="w-4 h-4" /> Ver mapa</> : <><List className="w-4 h-4" /> Ver lista</>}
              </button>
            </div>
          </div>
          <div className="absolute top-0 right-0 -translate-y-1/4 translate-x-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 translate-y-1/4 -translate-x-1/4 w-64 h-64 bg-accent/20 rounded-full blur-3xl" />
        </motion.div>
      </section>

      {/* Search Bar */}
      <section className="mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Buscar eventos, lugares, categorías..."
              className="w-full pl-10 pr-4 h-11 bg-muted/50 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="flex gap-2 items-center">
            <div className="flex items-center gap-1.5">
              <CalendarRange className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              <input
                type="date"
                value={dateFrom}
                onChange={e => setDateFrom(e.target.value)}
                className="h-11 px-3 bg-muted/50 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                title="Desde"
              />
              <span className="text-muted-foreground text-xs">—</span>
              <input
                type="date"
                value={dateTo}
                onChange={e => setDateTo(e.target.value)}
                className="h-11 px-3 bg-muted/50 border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                title="Hasta"
              />
            </div>
            {hasSearchFilters && (
              <button onClick={clearSearch} className="p-2.5 rounded-xl bg-red-100 text-red-600 hover:bg-red-200 transition-colors" title="Limpiar búsqueda">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Vibe Selector */}
      <section className="mb-10">
        <h3 className="text-xl font-display font-bold mb-4">¿Qué plan te apetece hoy?</h3>
        <VibeSelector current={profile.vibe} onSelect={setVibe} />
      </section>

      {/* Vibe Results */}
      {vibeEvents.length > 0 && (
        <section className="mb-10 bg-secondary/30 rounded-3xl p-6 md:p-8 border border-primary/10">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground shadow-md">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-display font-bold">Para ti</h3>
              <p className="text-sm text-muted-foreground">Basado en tu vibe: {profile.vibe}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {vibeEvents.map(({ event, score }) => (
              <EventCard
                key={`vibe-${event.id}`}
                event={event}
                matchScore={score}
                inAgenda={isInAgenda(event.id)}
                onToggleAgenda={() => isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)}
                onOpen={() => setSelectedEvent(event)}
              />
            ))}
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Main */}
        <div className="lg:col-span-8 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-2xl font-display font-bold flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-primary" /> Eventos en Madrid
            </h3>
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">{filteredScored.length} resultados</span>
              <div className="flex bg-muted rounded-lg p-0.5">
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-1.5 rounded-md transition-colors ${viewMode === 'list' ? 'bg-background shadow-sm' : 'text-muted-foreground'}`}
                  title="Vista lista"
                >
                  <List className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`p-1.5 rounded-md transition-colors ${viewMode === 'map' ? 'bg-background shadow-sm' : 'text-muted-foreground'}`}
                  title="Vista mapa"
                >
                  <MapIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <FilterBar
            sources={sources}
            categories={categories}
            activeSource={activeSource}
            activeCategory={activeCategory}
            onSourceChange={setActiveSource}
            onCategoryChange={setActiveCategory}
            dateFilter={dateFilter}
            onDateFilterChange={setDateFilter}
            freeOnly={freeOnly}
            onFreeOnlyChange={setFreeOnly}
          />

          {viewMode === 'map' ? (
            <Suspense fallback={<div className="h-[600px] rounded-2xl bg-muted animate-pulse flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>}>
              <MapView
                events={filteredScored.map(s => s.event)}
                onOpenEvent={setSelectedEvent}
              />
            </Suspense>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                {displayed.map(({ event, score }, i) => (
                  <motion.div key={event.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.05, 0.3) }}>
                    <EventCard
                      event={event}
                      matchScore={score > 0 ? score : undefined}
                      inAgenda={isInAgenda(event.id)}
                      onToggleAgenda={() => isInAgenda(event.id) ? removeFromAgenda(event.id) : addToAgenda(event.id)}
                      onOpen={() => setSelectedEvent(event)}
                    />
                  </motion.div>
                ))}
              </div>

              {showCount < filteredScored.length && (
                <div className="text-center py-4">
                  <button
                    onClick={() => setShowCount(c => c + 12)}
                    className="px-8 py-3 rounded-full border font-bold hover:bg-muted transition-colors"
                  >
                    Cargar mÃ¡s eventos ({filteredScored.length - showCount} restantes)
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-4 space-y-8">
          {/* News */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-display font-bold">Actualidad Madrid</h3>
            </div>
            <div className="space-y-3">
              {news.slice(0, 6).map((n, i) => (
                <motion.div key={n.id || i} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                  <NewsCard news={n} />
                </motion.div>
              ))}
            </div>
          </section>

          {/* Barrios */}
          <section>
            <h3 className="text-lg font-display font-bold mb-3">Explorar por barrio</h3>
            <div className="flex flex-wrap gap-2">
              {activeBarrio && (
                <button
                  onClick={() => setActiveBarrio(null)}
                  className="px-3 py-1.5 text-xs font-medium rounded-full bg-red-100 text-red-600 flex items-center gap-1 transition-colors"
                >
                  <X className="w-3 h-3" /> Todos
                </button>
              )}
              {BARRIOS.map(barrio => (
                <button
                  key={barrio}
                  onClick={() => setActiveBarrio(activeBarrio === barrio ? null : barrio)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
                    activeBarrio === barrio
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary/50 hover:bg-primary hover:text-primary-foreground'
                  }`}
                >
                  {barrio}
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* Modals */}
      <QuizModal
        open={quizOpen}
        onClose={() => setQuizOpen(false)}
        onFinish={(interests) => {
          setInterests(interests);
          setAnsweredQuiz(true);
          setQuizOpen(false);
        }}
      />
      <EventModal
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        inAgenda={selectedEvent ? isInAgenda(selectedEvent.id) : false}
        onToggleAgenda={() => {
          if (!selectedEvent) return;
          isInAgenda(selectedEvent.id) ? removeFromAgenda(selectedEvent.id) : addToAgenda(selectedEvent.id);
        }}
        matchScore={selectedEvent ? scored.find(s => s.event.id === selectedEvent.id)?.score : undefined}
      />
    </div>
  );
}
