import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Sparkles, Zap } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Generate from './pages/Generate';
import Progress from './pages/Progress';
import EntryDetail from './pages/EntryDetail';

function Sidebar() {
  const location = useLocation();

  const links = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/generate', icon: Sparkles, label: 'Generate' },
  ];

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-16 bg-bg-secondary border-r border-border flex flex-col items-center py-4 z-50">
      {/* Logo */}
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-500 flex items-center justify-center mb-6">
        <Zap className="w-5 h-5 text-white" />
      </div>

      {/* Nav Links */}
      <nav className="flex flex-col gap-2 flex-1">
        {links.map(({ to, icon: Icon, label }) => {
          const active = location.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              title={label}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                active
                  ? 'bg-accent/20 text-accent shadow-lg shadow-accent/10'
                  : 'text-text-muted hover:text-text-secondary hover:bg-bg-card'
              }`}
            >
              <Icon className="w-5 h-5" />
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-16 p-6 max-w-6xl">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/generate" element={<Generate />} />
            <Route path="/progress/:jobId" element={<Progress />} />
            <Route path="/entry/:entryId" element={<EntryDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
