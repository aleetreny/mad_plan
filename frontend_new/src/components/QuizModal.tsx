import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronRight, ChevronLeft, Sparkles, Zap, Heart, Music, Utensils, Mountain, Users } from 'lucide-react';
import { cn } from '../lib/utils';

interface Question {
  q: string;
  emoji: string;
  options: { label: string; emoji: string }[];
  multi?: boolean;
}

const QUESTIONS: Question[] = [
  {
    q: '¿Qué planes te hacen vibrar?',
    emoji: '🎭',
    options: [
      { label: 'Cultura y Arte', emoji: '🎨' },
      { label: 'Música y Conciertos', emoji: '🎵' },
      { label: 'Gastronomía', emoji: '🍷' },
      { label: 'Deporte y Naturaleza', emoji: '🏃' },
      { label: 'Vida nocturna', emoji: '🌙' },
      { label: 'Planes familiares', emoji: '👨‍👩‍👧' },
    ],
    multi: true,
  },
  {
    q: '¿Cuál es tu rollo?',
    emoji: '✨',
    options: [
      { label: 'Tranquilo e íntimo', emoji: '🧘' },
      { label: 'Animado y social', emoji: '🎉' },
      { label: 'Al aire libre', emoji: '🌳' },
      { label: 'Único y alternativo', emoji: '🦄' },
    ],
  },
  {
    q: '¿Cuánto quieres invertir en diversión?',
    emoji: '💰',
    options: [
      { label: 'Solo planes gratis', emoji: '🆓' },
      { label: 'Hasta 15€', emoji: '☕' },
      { label: 'Hasta 30€', emoji: '🍽️' },
      { label: 'No importa el precio', emoji: '💎' },
    ],
  },
  {
    q: '¿Con quién compartes aventura?',
    emoji: '🤝',
    options: [
      { label: 'Solo/a', emoji: '🦸' },
      { label: 'En pareja', emoji: '❤️' },
      { label: 'Con amigos', emoji: '🍻' },
      { label: 'En familia', emoji: '👪' },
    ],
  },
  {
    q: '¿Qué zonas de Madrid te llaman?',
    emoji: '📍',
    options: [
      { label: 'Centro (Sol, Malasaña, Chueca)', emoji: '🏙️' },
      { label: 'Retiro y Salamanca', emoji: '🌿' },
      { label: 'Lavapiés y La Latina', emoji: '🎸' },
      { label: 'Chamberí y Chamartín', emoji: '🏘️' },
      { label: 'Toda la ciudad', emoji: '🗺️' },
    ],
    multi: true,
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
  onFinish: (interests: string[]) => void;
}

export function QuizModal({ open, onClose, onFinish }: Props) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<string[][]>(QUESTIONS.map(() => []));
  const [direction, setDirection] = useState(1); // 1=forward, -1=backward

  const toggle = useCallback((optLabel: string) => {
    const q = QUESTIONS[step];
    setAnswers(prev => {
      const next = [...prev];
      const cur = next[step];
      if (q.multi) {
        next[step] = cur.includes(optLabel) ? cur.filter(x => x !== optLabel) : [...cur, optLabel];
      } else {
        next[step] = [optLabel];
      }
      return next;
    });
  }, [step]);

  const goNext = () => {
    if (step < QUESTIONS.length - 1) {
      setDirection(1);
      setStep(s => s + 1);
    } else {
      const allAnswers = answers.flat().map(a => a.toLowerCase());
      onFinish(allAnswers);
      setStep(0);
      setAnswers(QUESTIONS.map(() => []));
    }
  };

  const goBack = () => {
    if (step > 0) {
      setDirection(-1);
      setStep(s => s - 1);
    }
  };

  const handleClose = () => {
    onClose();
    setStep(0);
    setAnswers(QUESTIONS.map(() => []));
  };

  if (!open) return null;

  const progress = ((step + 1) / QUESTIONS.length) * 100;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={handleClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="bg-background rounded-3xl shadow-2xl max-w-lg w-full relative overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Progress bar */}
        <div className="h-1 bg-muted">
          <motion.div
            className="h-full bg-primary"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>

        <div className="p-6">
          <button onClick={handleClose} className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-muted transition-colors">
            <X className="w-5 h-5" />
          </button>

          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-2xl">
              {QUESTIONS[step].emoji}
            </div>
            <div>
              <h2 className="text-lg font-display font-bold">Descubre tu Match</h2>
              <p className="text-xs text-muted-foreground">Pregunta {step + 1} de {QUESTIONS.length}</p>
            </div>
          </div>

          {/* Question */}
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={step}
              initial={{ x: direction * 60, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -direction * 60, opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              <h3 className="text-xl font-bold mb-5">{QUESTIONS[step].q}</h3>
              {QUESTIONS[step].multi && (
                <p className="text-xs text-muted-foreground mb-3 -mt-3">Puedes elegir varias opciones</p>
              )}
              <div className="grid grid-cols-2 gap-2.5 mb-6">
                {QUESTIONS[step].options.map(opt => {
                  const selected = answers[step].includes(opt.label);
                  return (
                    <motion.button
                      key={opt.label}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => toggle(opt.label)}
                      className={cn(
                        "px-4 py-3.5 rounded-xl text-sm font-medium border-2 transition-all text-left flex items-center gap-2.5",
                        selected
                          ? "border-primary bg-primary/10 text-foreground shadow-sm shadow-primary/10"
                          : "border-border hover:border-primary/40 hover:bg-muted/30"
                      )}
                    >
                      <span className="text-lg flex-shrink-0">{opt.emoji}</span>
                      <span>{opt.label}</span>
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex gap-3">
            {step > 0 && (
              <button
                onClick={goBack}
                className="px-6 py-3 rounded-full border font-bold text-sm flex items-center gap-2 hover:bg-muted transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Anterior
              </button>
            )}
            <button
              onClick={goNext}
              disabled={answers[step].length === 0}
              className={cn(
                "flex-1 py-3 rounded-full font-bold text-sm flex items-center justify-center gap-2 transition-all",
                step === QUESTIONS.length - 1
                  ? "bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-lg shadow-primary/20 disabled:opacity-40"
                  : "bg-primary text-primary-foreground disabled:opacity-40"
              )}
            >
              {step < QUESTIONS.length - 1 ? (
                <>Siguiente <ChevronRight className="w-4 h-4" /></>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> ¡Ver mis recomendaciones!
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
