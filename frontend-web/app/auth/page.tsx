'use client';

import dynamic from 'next/dynamic';
import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Shield } from 'lucide-react';
import { useRouter } from 'next/navigation';
import LoginForm from '@/components/auth/LoginForm';
import RegisterForm from '@/components/auth/RegisterForm';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';

// Lazy-load the heavy 3D scene
const AuthScene = dynamic(() => import('@/components/auth/AuthScene'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-24 h-24 rounded-full border border-[#3CB697]/20 animate-pulse" />
    </div>
  ),
});

type Tab = 'login' | 'register';

export default function AuthPage() {
  const [tab, setTab] = useState<Tab>('login');
  const router = useRouter();
  const { token, _hasHydrated } = useAuthStore();

  // If store has hydrated and we have a valid token, skip auth page
  useEffect(() => {
    if (_hasHydrated && token) {
      router.replace('/dashboard/scan');
      return;
    }
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('tab') === 'register' || params.get('mode') === 'register') {
        setTab('register');
      }
    }
  }, [_hasHydrated, token, router]);

  return (
    <div className="min-h-screen flex bg-[#0D0F14]">
      {/* ── Left panel: 3D scene ─────────────────────────────────────────── */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#0D0F14]/0 via-[#0D0F14]/0 to-[#0D0F14]/80 z-10 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#3CB697]/5 to-[#0D0F14]/20 pointer-events-none" />

        <AuthScene />

        {/* Brand overlay text */}
        <div className="absolute bottom-12 left-12 z-20">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="text-[#3CB697]" size={20} />
            <span className="text-[#3CB697] text-sm font-mono font-medium tracking-widest uppercase">
              Forensic Engine v2
            </span>
          </div>
          <h1
            className="text-4xl font-bold text-[#E8E6DF] leading-tight mb-2"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            ATS Fraud
            <br />
            <span className="text-[#3CB697]">Detector</span>
          </h1>
          <p className="text-[#7A8099] text-sm max-w-xs leading-relaxed">
            AI-powered resume forensics. Detect manipulation, protect your hiring pipeline.
          </p>
        </div>
      </div>

      {/* ── Right panel: auth form ───────────────────────────────────────── */}
      <div className="w-full lg:w-[480px] flex flex-col justify-center px-8 py-12 lg:px-14 relative">
        {/* Soft left border glow */}
        <div className="hidden lg:block absolute left-0 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-[#3CB697]/20 to-transparent" />

        {/* Mobile brand */}
        <div className="flex lg:hidden items-center gap-2 mb-10">
          <Shield className="text-[#3CB697]" size={20} />
          <span
            className="text-xl font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            ATS Fraud Detector
          </span>
        </div>

        {/* Heading */}
        <div className="mb-8">
          <h2
            className="text-2xl font-bold text-[#E8E6DF] mb-1"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            {tab === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-sm text-[#7A8099]">
            {tab === 'login'
              ? 'Sign in to access your forensic dashboard'
              : 'Start scanning resumes for ATS fraud'}
          </p>
        </div>

        {/* Tab switcher */}
        <div className="flex mb-8 p-1 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.12)]">
          {(['login', 'register'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'flex-1 py-2 rounded-md text-sm font-medium transition-all duration-200 capitalize',
                tab === t
                  ? 'bg-[#3CB697] text-[#0D0F14] shadow-[0_0_12px_rgba(60,182,151,0.3)]'
                  : 'text-[#7A8099] hover:text-[#E8E6DF]',
              )}
            >
              {t === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        {/* Animated form switcher */}
        <AnimatePresence mode="wait">
          <motion.div key={tab}>
            {tab === 'login' ? <LoginForm /> : <RegisterForm />}
          </motion.div>
        </AnimatePresence>

        {/* Footer */}
        <p className="mt-8 text-center text-xs text-[#7A8099]">
          {tab === 'login' ? (
            <>
              Don&apos;t have an account?{' '}
              <button
                onClick={() => setTab('register')}
                className="text-[#3CB697] hover:underline"
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                onClick={() => setTab('login')}
                className="text-[#3CB697] hover:underline"
              >
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
