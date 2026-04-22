import { AppProviders } from './providers/AppProviders';
import { Dashboard } from '../features/discovery/Dashboard';

export default function App() {
  return (
    <AppProviders>
      <Dashboard />
    </AppProviders>
  );
}

