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
  RefreshCw
} from 'lucide-react';

interface HealthStatus {
  status: string;
  app_name: string;
  environment: string;
  timestamp: string;
}

export function App() {
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
      <header className="bg-white border-b border-purple-100 shadow-sm sticky top-0 z-50">
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
                Phase 1: Foundation
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-500">API Status:</span>
              {loading ? (
                <span className="badge bg-amber-100 text-amber-800 animate-pulse">Checking...</span>
              ) : error ? (
                <span className="badge bg-rose-100 text-rose-800 flex items-center gap-1">
                  Offline
                </span>
              ) : (
                <span className="badge bg-emerald-100 text-emerald-800 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Online ({health?.environment})
                </span>
              )}
            </div>
            <button
              onClick={fetchHealth}
              disabled={loading}
              className="p-2 text-purple-700 hover:bg-lavender-100 rounded-lg transition-colors border border-lavender-200"
              title="Refresh Health Probe"
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

        {/* Foundation Architecture Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
              <Cpu className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Asynchronous Workers</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Decoupled background worker pool with heartbeat monitoring, lease fencing, and cooperative graceful shutdown.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-purple-50 border border-purple-100 flex items-center justify-center text-purple-600">
              <Database className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Transactional Outbox</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Atomic database-to-queue handoff guaranteeing zero silent job loss under transient broker outages or network partitions.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-600">
              <Activity className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Full Observability</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              Correlated JSON execution traces, attempt histories, and decoupled non-blocking Elasticsearch index streaming.
            </p>
          </div>

          <div className="card-surface p-6 space-y-3">
            <div className="w-10 h-10 rounded-lg bg-fuchsia-50 border border-fuchsia-100 flex items-center justify-center text-fuchsia-600">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900">Advisory AI Guardrails</h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              CrewAI-assisted failure investigation strictly grounded in execution logs with schema-enforced Pydantic output.
            </p>
          </div>
        </div>

        {/* Runtime Probe Console */}
        <div className="card-surface p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-purple-100 pb-4">
            <div className="flex items-center space-x-2">
              <Terminal className="w-5 h-5 text-purple-600" />
              <h2 className="text-base font-semibold text-slate-900">Foundation Health Probe</h2>
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
            {loading ? (
              <p className="text-slate-400 animate-pulse">// Querying /api/health ...</p>
            ) : error ? (
              <div className="space-y-1">
                <p className="text-rose-400">// Probe Failed: {error}</p>
                <p className="text-slate-500">// Ensure the FastAPI backend server is running on http://localhost:8000</p>
              </div>
            ) : (
              <pre>{JSON.stringify(health, null, 2)}</pre>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-purple-100 bg-white py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500">
          TaskForge Cloud Computing Prototype • Reliable Asynchronous Job Orchestration Platform
        </div>
      </footer>
    </div>
  );
}

export default App;
