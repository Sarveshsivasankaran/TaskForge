import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Layers, 
  Shield, 
  User, 
  ArrowRight, 
  Lock, 
  Mail, 
  CheckCircle, 
  XCircle, 
  ShieldCheck, 
  SlidersHorizontal,
  ChevronRight,
  Database
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { user, signIn, signUp, demoLogin, error, clearError, loading } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'demo' | 'credentials'>('demo');
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // If already logged in, provide a quick continue
  const handleContinue = () => {
    navigate('/');
  };

  const handleDemoSignIn = async (role: 'user' | 'admin') => {
    setSubmitting(true);
    try {
      await demoLogin(role);
      navigate('/');
    } catch {
      // Error handled in AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (authMode === 'signin') {
        await signIn(email, password);
      } else {
        await signUp(email, password);
      }
      navigate('/');
    } catch {
      // Error handled in AuthContext
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-50 via-white to-purple-50/60 flex flex-col justify-between font-sans">
      {/* Top Banner Navigation */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-purple-100/80 bg-white/70 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xl font-bold bg-gradient-to-r from-indigo-900 via-purple-900 to-slate-900 bg-clip-text text-transparent">
              TaskForge
            </span>
            <span className="hidden sm:inline-block ml-3 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-lavender-100 text-purple-800 border border-lavender-200">
              Identity & Access Management
            </span>
          </div>
        </div>

        {user && (
          <div className="flex items-center space-x-3">
            <span className="text-xs text-slate-500 hidden sm:inline">Active session:</span>
            <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              {user.email} ({user.isAdmin ? 'Cluster Admin' : 'Tenant Operator'})
            </span>
            <button
              onClick={handleContinue}
              className="btn-primary text-xs py-1.5 px-3 flex items-center space-x-1 shadow-sm"
            >
              <span>Go to Dashboard</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </header>

      {/* Main Login Workspace */}
      <main className="max-w-5xl mx-auto px-4 py-8 sm:py-12 w-full flex flex-col items-center">
        {/* Brand Headline */}
        <div className="text-center max-w-2xl mb-8 space-y-3">
          <div className="inline-flex items-center space-x-2 text-xs font-bold text-indigo-700 uppercase tracking-widest bg-indigo-50/80 px-3 py-1 rounded-full border border-indigo-100 shadow-sm">
            <SlidersHorizontal className="w-3.5 h-3.5 text-indigo-600" />
            <span>Role-Based Access Control</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Sign In to TaskForge
          </h1>
          <p className="text-sm text-slate-600 leading-relaxed">
            Select an operational role or sign in with your enterprise credentials.
          </p>
        </div>

        {/* Tab Switcher: Demo Roles vs Credentials */}
        <div className="bg-white p-1 rounded-xl border border-purple-100 shadow-sm flex items-center space-x-1 mb-8 w-full max-w-md">
          <button
            type="button"
            onClick={() => {
              clearError();
              setActiveTab('demo');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
              activeTab === 'demo'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Demo Roles</span>
          </button>
          <button
            type="button"
            onClick={() => {
              clearError();
              setActiveTab('credentials');
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center space-x-1.5 ${
              activeTab === 'credentials'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Credentials</span>
          </button>
        </div>

        {/* TAB 1: INTERACTIVE ROLE CARDS */}
        {activeTab === 'demo' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl animate-in fade-in zoom-in-95 duration-200">
            {/* CARD 1: TENANT OPERATOR */}
            <div className="card-surface p-6 sm:p-7 flex flex-col justify-between border-2 border-indigo-100 hover:border-indigo-400 transition-all shadow-md hover:shadow-lg bg-gradient-to-b from-white via-indigo-50/20 to-white relative group">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="h-12 w-12 rounded-2xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center shadow-inner group-hover:scale-105 transition-transform">
                    <User className="w-6 h-6" />
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-800 border border-indigo-200">
                    Tenant Operator
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-slate-900">Tenant Workload Operator</h3>
                  <p className="text-xs text-indigo-700 font-medium mt-0.5">operator@taskforge.dev (Tenant Scoped)</p>
                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                    Designed for application teams and business microservices submitting and monitoring background asynchronous tasks.
                  </p>
                </div>

                <div className="pt-2 border-t border-indigo-100/80 space-y-2 text-xs">
                  <p className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider">Capabilities & Permissions:</p>
                  <ul className="space-y-1.5 text-slate-600">
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Enqueue background workloads into transactional outbox</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>View real-time telemetry scoped strictly to your tenant</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Inspect attempt logs & cancel/retry own tenant jobs</span>
                    </li>
                    <li className="flex items-center space-x-2 text-slate-400">
                      <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                      <span>Cluster-wide cross-tenant inspection (Forbidden)</span>
                    </li>
                    <li className="flex items-center space-x-2 text-slate-400">
                      <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                      <span>Worker lease recovery & outbox sweeps (Forbidden)</span>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="pt-6 mt-6 border-t border-indigo-100">
                <button
                  type="button"
                  onClick={() => handleDemoSignIn('user')}
                  disabled={submitting || loading}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm flex items-center justify-center space-x-2 shadow-md hover:shadow-indigo-200 transition-all disabled:opacity-50"
                >
                  <User className="w-4 h-4" />
                  <span>{submitting ? 'Redirecting...' : 'Launch as Tenant Operator'}</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </button>
                <p className="text-[11px] text-center text-slate-400 mt-2">
                  Stamps token claims with role: <code>authenticated</code>
                </p>
              </div>
            </div>

            {/* CARD 2: CLUSTER ADMINISTRATOR */}
            <div className="card-surface p-6 sm:p-7 flex flex-col justify-between border-2 border-purple-200 hover:border-purple-400 transition-all shadow-md hover:shadow-lg bg-gradient-to-b from-white via-purple-50/30 to-white relative group">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="h-12 w-12 rounded-2xl bg-purple-50 border border-purple-200 text-purple-700 flex items-center justify-center shadow-inner group-hover:scale-105 transition-transform">
                    <Shield className="w-6 h-6" />
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200">
                    Cluster Admin
                  </span>
                </div>

                <div>
                  <h3 className="text-xl font-bold text-slate-900">Cluster Administrator</h3>
                  <p className="text-xs text-purple-700 font-medium mt-0.5">admin@taskforge.dev (Full Platform SRE)</p>
                  <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                    Designed for Site Reliability Engineers, DevOps, and Platform Administrators overseeing cluster health and distributed queues.
                  </p>
                </div>

                <div className="pt-2 border-t border-purple-100/80 space-y-2 text-xs">
                  <p className="font-semibold text-slate-800 text-[11px] uppercase tracking-wider">Privileged Capabilities:</p>
                  <ul className="space-y-1.5 text-slate-600">
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Cluster-wide visibility across all tenant workspaces</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Reclaim abandoned worker leases & fence crashed nodes</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Manually sweep & flush transactional outbox dispatch</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Cryptographic verification on protected admin endpoints</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Manage poison pill quarantine & dead-letter queue redrive</span>
                    </li>
                  </ul>
                </div>
              </div>

              <div className="pt-6 mt-6 border-t border-purple-100">
                <button
                  type="button"
                  onClick={() => handleDemoSignIn('admin')}
                  disabled={submitting || loading}
                  className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-purple-700 to-indigo-700 hover:from-purple-800 hover:to-indigo-800 text-white font-semibold text-sm flex items-center justify-center space-x-2 shadow-md hover:shadow-purple-200 transition-all disabled:opacity-50"
                >
                  <Shield className="w-4 h-4" />
                  <span>{submitting ? 'Redirecting...' : 'Launch as Cluster Administrator'}</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </button>
                <p className="text-[11px] text-center text-slate-400 mt-2">
                  Stamps token claims with role: <code>service_role / admin</code>
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SUPABASE AUTH CREDENTIALS */}
        {activeTab === 'credentials' && (
          <div className="card-surface p-6 sm:p-8 w-full max-w-md border border-purple-100 shadow-elevated animate-in fade-in zoom-in-95 duration-200">
            <div className="text-center mb-6">
              <h3 className="text-lg font-bold text-slate-900">
                {authMode === 'signin' ? 'Sign In with Supabase' : 'Create TaskForge Account'}
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Direct integration with PostgreSQL Auth & JWT validation
              </p>
            </div>

            {error && (
              <div className="p-3 mb-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start space-x-2">
                <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Enterprise Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="operator@taskforge.dev"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-purple-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 bg-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting || loading}
                className="w-full btn-primary py-2.5 text-sm flex items-center justify-center space-x-2 mt-2"
              >
                <span>{submitting ? 'Authenticating...' : authMode === 'signin' ? 'Sign In & Redirect' : 'Create & Sign In'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>

            <div className="mt-6 pt-4 border-t border-purple-100 flex items-center justify-between text-xs text-slate-500">
              <span>{authMode === 'signin' ? 'Need an account?' : 'Already have an account?'}</span>
              <button
                type="button"
                onClick={() => {
                  clearError();
                  setAuthMode(authMode === 'signin' ? 'signup' : 'signin');
                }}
                className="text-indigo-600 hover:text-indigo-800 font-semibold"
              >
                {authMode === 'signin' ? 'Register Account' : 'Sign In'}
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer Info */}
      <footer className="py-6 border-t border-purple-100/80 bg-white/50 text-center text-xs text-slate-500">
        <p>TaskForge Intelligent Asynchronous Job Orchestration Platform · Production-Ready Cloud Architecture</p>
      </footer>
    </div>
  );
};
