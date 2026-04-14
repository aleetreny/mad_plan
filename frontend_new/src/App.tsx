import { useState, useMemo } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { UserProvider, useUser } from './context/UserContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { ThemeToggle } from './components/ThemeToggle';
import { AgendaDrawer } from './components/AgendaDrawer';
import { useMadPlanData } from './hooks/useMadPlanData';
import { motion, AnimatePresence } from 'framer-motion';

function AppInner() {
  const [agendaOpen, setAgendaOpen] = useState(false);
  const { profile, removeFromAgenda } = useUser();
  const { events } = useMadPlanData();

  const agendaEvents = useMemo(() => {
    return events.filter(e => profile.agenda.includes(e.id));
  }, [events, profile.agenda]);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar
        onOpenAgenda={() => setAgendaOpen(true)}
        agendaCount={profile.agenda.length}
      />
      <main className="flex-1">
        <AnimatePresence mode="wait">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
            <Dashboard />
          </motion.div>
        </AnimatePresence>
      </main>

      <footer className="border-t py-12 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-1 md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">M</div>
                <h2 className="text-xl font-display font-bold">MadPlan</h2>
              </div>
              <p className="text-muted-foreground max-w-xs mb-6">
                Tu guía definitiva para vivir Madrid. Eventos, noticias y planes personalizados según tu ritmo y el de la ciudad.
              </p>
              <div className="flex gap-4">
                {['Twitter', 'Instagram', 'Facebook'].map(s => (
                  <a key={s} href="#" className="text-muted-foreground hover:text-primary transition-colors font-medium text-sm">{s}</a>
                ))}
              </div>
            </div>
            <div>
              <h4 className="font-bold mb-4">Explorar</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">Eventos hoy</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Mapa interactivo</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Barrios</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Categorías</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Compañía</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">Sobre nosotros</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Contacto</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Privacidad</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Términos</a></li>
              </ul>
            </div>
          </div>
          <div className="mt-12 pt-8 border-t text-center text-xs text-muted-foreground">
            <p>© 2026 MadPlan. Hecho con ❤️ en Madrid.</p>
          </div>
        </div>
      </footer>

      <ThemeToggle />
      <AgendaDrawer open={agendaOpen} onClose={() => setAgendaOpen(false)} events={agendaEvents} onRemove={removeFromAgenda} />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <AppInner />
      </UserProvider>
    </ThemeProvider>
  );
}
