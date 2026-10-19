import { useState, useEffect } from 'react';
import { 
  Layers, 
  Activity, 
  ShieldCheck, 
  Cpu, 
  Database, 
  Terminal, 
  CheckCircle2, 
  ExternalLink,
  RefreshCw,
  User,
  LogOut,
  Shield
} from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AuthModal } from './components/auth/AuthModal';

interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  version?: string;
  timestamp: string;
}

function DashboardContent() {
  const { user, token, signOut } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/health');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to connect to backend API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="min-h-screen bg-lavender-50 text-slate-800 flex flex-col">
      {/* Top Navigation */}
      <header className="bg-white border-b border-purple-100 shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <span className="text-xl font-bold bg-gradient-to-r from-indigo-900 via-purple-900 to-slate-900 bg-clip-text text-transparent">
                TaskForge
              </span>
              <span className="hidden sm:inline-block ml-3 px-2.5 py-0.5 rounded-full text-xs font-medium bg-lavender-100 text-purple-800 border border-lavender-200">
                Phase 3: Auth & Security
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* API Status Badge */}
            <div className="hidden sm:flex items-center space-x-2 text-xs">
              <span className="text-slate-500">API:</span>
              {loading ? (
                <span className="badge bg-amber-100 text-amber-800 animate-pulse">Checking...</span>
              ) : error ? (
                <span className="badge bg-rose-100 text-rose-800">Offline</span>
              ) : (
                <span className="badge bg-emerald-100 text-emerald-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Online v{health?.version || '0.1.0'}
                </span>
              )}
            </div>

            {/* User Profile or Sign-In Trigger */}
            {user ? (
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2 bg-lavender-50 border border-lavender-200 rounded-lg px-3 py-1.5 text-xs">
                  <div className="h-5 w-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                    {user.isAdmin ? <Shield className="w-3 h-3" /> : <User className="w-3 h-3" />}
                  </div>
                  <div className="text-left hidden md:block">
                    <p className="font-semibold text-slate-800 leading-tight">{user.email}</p>
                    <p className="text-[10px] text-purple-600 font-medium capitalize">{user.role}</p>
                  </div>
                </div>
                <button
                  onClick={signOut}
                  className="p-2 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-100"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1"
              >
                <User className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}

            <button
              onClick={fetchHealth}
              disabled={loading}
              className="p-2 text-purple-700 hover:bg-lavender-100 rounded-lg transition-colors border border-lavender-200"
              title="Refresh Probes"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="card-surface p-8 bg-gradient-to-br from-white via-lavender-50/50 to-purple-50/30">
          <div className="max-w-3xl space-y-3">
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Submit once. Process reliably. Recover intelligently.
            </h1>
            <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
              TaskForge is a production-minded cloud platform engineered for reliable asynchronous job orchestration, bounded retry semantics with randomized jitter, dead-letter recovery, and evidence-grounded AI failure analysis.
            </p>
          </div>
        </div>

        {/* Security & Multi-Tenancy Architecture Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Supabase Auth JWT</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Cryptographic signature verification, expiration checks, and role claim extraction.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
              <Database className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Owner Scoping & RLS</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Strict per-tenant isolation in API queries and database row-level security policies.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-600">
              <Activity className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Rate Limiting</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Throttling via SlowAPI with per-user token and client IP identification.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-fuchsia-50 border border-fuchsia-100 flex items-center justify-center text-fuchsia-600">
              <Cpu className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Privilege Separation</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Service role keys are restricted to backend workers and never exposed to the frontend.
            </p>
          </div>
        </div>

        {/* Runtime Probe Console */}
        <div className="card-surface p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-purple-100 pb-4">
            <div className="flex items-center space-x-2">
              <Terminal className="w-5 h-5 text-purple-600" />
              <h2 className="text-base font-semibold text-slate-900">Security & Authentication Session</h2>
            </div>
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-1"
            >
              Interactive OpenAPI Docs <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <div className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs overflow-x-auto">
            {user ? (
              <div className="space-y-1">
                <p className="text-emerald-400">// Authenticated User Context:</p>
                <p className="text-slate-300">User ID: {user.id}</p>
                <p className="text-slate-300">Email: {user.email}</p>
                <p className="text-slate-300">Role: {user.role}</p>
                <p className="text-slate-300">Token: {token?.slice(0, 16)}...</p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-amber-400">// No active session detected. Click "Sign In" above to authenticate.</p>
                <p className="text-slate-500">// Unauthenticated requests to protected endpoints will receive 401 Unauthorized.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-purple-100 bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500">
          TaskForge Cloud Computing Platform • Intelligent Asynchronous Job Orchestration Platform
        </div>
      </footer>

      {/* Auth Modal */}
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  );
}

export default App;
