import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Sparkles, X } from 'lucide-react';
import { BUDGET_LABELS, COMPANION_LABELS, ZONES } from '../../domain/madplan/constants';
import type { BudgetPreference, CompanionMode, VibeMode } from '../../domain/madplan/types';
import { cn } from '../../shared/lib/cn';

interface QuizPayload {
  interests: string[];
  vibe: VibeMode;
  budget: BudgetPreference;
  companion: CompanionMode;
  zones: string[];
}

interface QuizModalProps {
  open: boolean;
  onClose: () => void;
  onFinish: (payload: QuizPayload) => void;
}

const INTEREST_OPTIONS = [
  'Arte y exposiciones',
  'Conciertos',
  'Gastronomía',
  'Cine y escena',
  'Running y outdoor',
  'Familia',
] as const;

const VIBE_OPTIONS: Array<{ key: Exclude<VibeMode, null>; label: string; emoji: string }> = [
  { key: 'cultural', label: 'Cultural', emoji: '🎨' },
  { key: 'fiesta', label: 'Fiesta', emoji: '🎶' },
  { key: 'relax', label: 'Relax', emoji: '🌿' },
  { key: 'foodie', label: 'Foodie', emoji: '🍷' },
  { key: 'aventura', label: 'Aventura', emoji: '🏃' },
  { key: 'familiar', label: 'Familiar', emoji: '👨‍👩‍👧' },
];

export function QuizModal({ open, onClose, onFinish }: QuizModalProps) {
  const [step, setStep] = useState(0);
  const [interests, setInterests] = useState<string[]>([]);
  const [vibe, setVibe] = useState<VibeMode>(null);
  const [budget, setBudget] = useState<BudgetPreference>(null);
  const [companion, setCompanion] = useState<CompanionMode>(null);
  const [zones, setZones] = useState<string[]>([]);

  if (!open) return null;

  const progress = ((step + 1) / 5) * 100;

  function reset() {
    setStep(0);
    setInterests([]);
    setVibe(null);
    setBudget(null);
    setCompanion(null);
    setZones([]);
  }

  function finish() {
    onFinish({ interests, vibe, budget, companion, zones });
    reset();
  }

  const canContinue = [
    interests.length > 0,
    Boolean(vibe),
    Boolean(budget),
    Boolean(companion),
    zones.length > 0,
  ][step];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={() => { onClose(); reset(); }}>
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 24, scale: 0.98 }}
          className="relative w-full max-w-2xl overflow-hidden rounded-[32px] bg-background shadow-[0_30px_90px_rgba(0,0,0,0.34)]"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="h-1.5 bg-muted">
            <div className="h-full bg-primary transition-[width] duration-300" style={{ width: `${progress}%` }} />
          </div>
          <div className="p-6 sm:p-7">
            <button onClick={() => { onClose(); reset(); }} className="absolute right-4 top-4 inline-flex h-11 w-11 items-center justify-center rounded-full hover:bg-muted/60" aria-label="Cerrar quiz">
              <X className="h-5 w-5" />
            </button>

            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary/80">Quiz editorial</p>
              <div className="mt-3 flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-display font-bold">Afinamos tu Madrid ideal</h2>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">Cinco pasos para que las recomendaciones tengan sentido real, no solo estética.</p>
                </div>
                <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
                  Paso {step + 1} de 5
                </span>
              </div>
            </div>

            <div className="min-h-[320px]">
              {step === 0 ? (
                <div>
                  <h3 className="text-xl font-display font-bold">¿Qué te apetece de verdad?</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Puedes elegir varias opciones.</p>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {INTEREST_OPTIONS.map((option) => {
                      const selected = interests.includes(option);
                      return (
                        <button
                          key={option}
                          onClick={() => setInterests((current) => selected ? current.filter((item) => item !== option) : [...current, option])}
                          className={cn(
                            'rounded-[24px] border border-border/70 p-4 text-left transition-colors',
                            selected ? 'border-primary bg-primary/10' : 'bg-card/75 hover:border-primary/45',
                          )}
                        >
                          <p className="text-base font-semibold">{option}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {step === 1 ? (
                <div>
                  <h3 className="text-xl font-display font-bold">¿Qué energía buscas hoy?</h3>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {VIBE_OPTIONS.map((option) => (
                      <button
                        key={option.key}
                        onClick={() => setVibe(option.key)}
                        className={cn(
                          'rounded-[24px] border border-border/70 p-4 text-left transition-colors',
                          vibe === option.key ? 'border-primary bg-primary/10' : 'bg-card/75 hover:border-primary/45',
                        )}
                      >
                        <p className="text-2xl">{option.emoji}</p>
                        <p className="mt-2 text-base font-semibold">{option.label}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {step === 2 ? (
                <div>
                  <h3 className="text-xl font-display font-bold">¿Cómo va el presupuesto?</h3>
                  <div className="mt-5 grid gap-3">
                    {(Object.entries(BUDGET_LABELS) as Array<[Exclude<BudgetPreference, null>, string]>).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setBudget(key)}
                        className={cn(
                          'rounded-[24px] border border-border/70 p-4 text-left transition-colors',
                          budget === key ? 'border-primary bg-primary/10' : 'bg-card/75 hover:border-primary/45',
                        )}
                      >
                        <p className="text-base font-semibold">{label}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {step === 3 ? (
                <div>
                  <h3 className="text-xl font-display font-bold">¿Con quién sales?</h3>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {(Object.entries(COMPANION_LABELS) as Array<[Exclude<CompanionMode, null>, string]>).map(([key, label]) => (
                      <button
                        key={key}
                        onClick={() => setCompanion(key)}
                        className={cn(
                          'rounded-[24px] border border-border/70 p-4 text-left transition-colors',
                          companion === key ? 'border-primary bg-primary/10' : 'bg-card/75 hover:border-primary/45',
                        )}
                      >
                        <p className="text-base font-semibold">{label}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {step === 4 ? (
                <div>
                  <h3 className="text-xl font-display font-bold">¿Qué zonas te vienen mejor?</h3>
                  <p className="mt-1 text-sm text-muted-foreground">Elige una o varias áreas para ajustar los resultados.</p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {ZONES.map((zone) => {
                      const selected = zones.includes(zone.name);
                      return (
                        <button
                          key={zone.name}
                          onClick={() => setZones((current) => selected ? current.filter((item) => item !== zone.name) : [...current, zone.name])}
                          className={cn(
                            'rounded-full border border-border/70 px-4 py-2 text-sm font-semibold transition-colors',
                            selected ? 'border-primary bg-primary text-primary-foreground' : 'bg-card/75 hover:border-primary/45',
                          )}
                        >
                          {zone.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="mt-6 flex items-center gap-3">
              {step > 0 ? (
                <button onClick={() => setStep((current) => current - 1)} className="inline-flex items-center gap-2 rounded-full border border-border/80 px-5 py-3 text-sm font-semibold hover:bg-muted/60">
                  <ChevronLeft className="h-4 w-4" />
                  Atrás
                </button>
              ) : null}
              <button
                onClick={() => {
                  if (step === 4) finish();
                  else setStep((current) => current + 1);
                }}
                disabled={!canContinue}
                className="ml-auto inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-40"
              >
                {step === 4 ? (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Ver recomendaciones
                  </>
                ) : (
                  <>
                    Siguiente
                    <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

