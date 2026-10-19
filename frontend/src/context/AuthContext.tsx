import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types/auth';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  demoLogin: (role?: 'user' | 'admin') => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check saved session in localStorage
    const savedToken = localStorage.getItem('taskforge_token');
    const savedUser = localStorage.getItem('taskforge_user');
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('taskforge_token');
        localStorage.removeItem('taskforge_user');
      }
    }

    if (isSupabaseConfigured) {
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (session) {
          const authUser: User = {
            id: session.user.id,
            email: session.user.email || 'user@taskforge.dev',
            role: session.user.role || 'authenticated',
            isAdmin: session.user.app_metadata?.role === 'admin'
          };
          setUser(authUser);
          setToken(session.access_token);
          localStorage.setItem('taskforge_token', session.access_token);
          localStorage.setItem('taskforge_user', JSON.stringify(authUser));
        }
        setLoading(false);
      });

      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session) {
          const authUser: User = {
            id: session.user.id,
            email: session.user.email || 'user@taskforge.dev',
            role: session.user.role || 'authenticated',
            isAdmin: session.user.app_metadata?.role === 'admin'
          };
          setUser(authUser);
          setToken(session.access_token);
          localStorage.setItem('taskforge_token', session.access_token);
          localStorage.setItem('taskforge_user', JSON.stringify(authUser));
        } else {
          setUser(null);
          setToken(null);
          localStorage.removeItem('taskforge_token');
          localStorage.removeItem('taskforge_user');
        }
      });

      return () => {
        subscription.unsubscribe();
      };
    } else {
      setLoading(false);
    }
  }, []);

  const signIn = async (email: string, password: string) => {
    setError(null);
    setLoading(true);
    try {
      if (isSupabaseConfigured) {
        const { data, error: err } = await supabase.auth.signInWithPassword({ email, password });
        if (err) throw err;
        if (data.session) {
          const authUser: User = {
            id: data.session.user.id,
            email: data.session.user.email || email,
            role: data.session.user.role || 'authenticated',
            isAdmin: data.session.user.app_metadata?.role === 'admin'
          };
          setUser(authUser);
          setToken(data.session.access_token);
          localStorage.setItem('taskforge_token', data.session.access_token);
          localStorage.setItem('taskforge_user', JSON.stringify(authUser));
        }
      } else {
        // Local mode fallback
        await demoLogin(email.includes('admin') ? 'admin' : 'user');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Sign in failed';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (email: string, password: string) => {
    setError(null);
    setLoading(true);
    try {
      if (isSupabaseConfigured) {
        const { data, error: err } = await supabase.auth.signUp({ email, password });
        if (err) throw err;
        if (data.session) {
          const authUser: User = {
            id: data.session.user.id,
            email: data.session.user.email || email,
            role: data.session.user.role || 'authenticated',
          };
          setUser(authUser);
          setToken(data.session.access_token);
          localStorage.setItem('taskforge_token', data.session.access_token);
          localStorage.setItem('taskforge_user', JSON.stringify(authUser));
        }
      } else {
        await demoLogin('user');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const demoLogin = async (role: 'user' | 'admin' = 'user') => {
    setLoading(true);
    setError(null);
    try {
      // Create a deterministic client session for development evaluation
      const demoId = role === 'admin' 
        ? '00000000-0000-0000-0000-000000000001'
        : '00000000-0000-0000-0000-000000000002';
      
      const email = role === 'admin' ? 'admin@taskforge.dev' : 'operator@taskforge.dev';

      // Request a signed token from the backend test token generator if in dev mode, or use fallback
      const response = await fetch('/api/v1/auth/demo-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: demoId, email, role: role === 'admin' ? 'service_role' : 'authenticated' })
      }).catch(() => null);

      let tokenValue = 'demo-token';
      if (response && response.ok) {
        const data = await response.json();
        tokenValue = data.token;
      }

      const demoUser: User = {
        id: demoId,
        email,
        role: role === 'admin' ? 'service_role' : 'authenticated',
        isAdmin: role === 'admin'
      };

      setUser(demoUser);
      setToken(tokenValue);
      localStorage.setItem('taskforge_token', tokenValue);
      localStorage.setItem('taskforge_user', JSON.stringify(demoUser));
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    if (isSupabaseConfigured) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setToken(null);
    localStorage.removeItem('taskforge_token');
    localStorage.removeItem('taskforge_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        error,
        signIn,
        signUp,
        signOut,
        demoLogin,
        clearError: () => setError(null)
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
