'use client';

import dynamic from 'next/dynamic';
import { motion, type Variants } from 'framer-motion';
import { Shield, ArrowRight, ScanLine, Brain, BarChart3, Sparkles } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import RoadmapSection from '@/components/landing/RoadmapSection';

// Lazy-load the 3D HeroScene
const HeroScene = dynamic(() => import('@/components/landing/HeroScene'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-20 h-20 rounded-full border border-[#3CB697]/20 animate-pulse" />
    </div>
  ),
});

const LIVE_FEATURES = [
  {
    icon: ScanLine,
    title: 'Forensic PDF Scanning',
    description:
      '9 deterministic fraud detectors — hidden text, homoglyphs, off-page spans, zero-width chars, and more.',
  },
  {
    icon: Brain,
    title: 'AI Content Detection',
    description:
      'Heuristic burstiness + perplexity scoring flags AI-generated resumes before they reach your desk.',
  },
  {
    icon: BarChart3,
    title: 'Trust Score & Batch Ranking',
    description:
      'Blended 0–100 Trust Score with a Verified / Caution / High Risk verdict. Rank entire applicant pools at once.',
  },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.16,
      delayChildren: 0.1,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

export default function HomePage() {
  const { token, _hasHydrated } = useAuthStore();
  const isLoggedIn = _hasHydrated && Boolean(token);

  return (
    <div className="min-h-screen bg-[#0B0D12] text-[#E8E6DF] flex flex-col selection:bg-[#3CB697]/30 selection:text-[#E8E6DF]">
      {/* ── Sticky Top Nav ─────────────────────────────────────────────────── */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-[rgba(60,182,151,0.08)] sticky top-0 z-30 bg-[#0B0D12]/90 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/25 flex items-center justify-center shadow-[0_0_14px_rgba(60,182,151,0.15)]">
            <Shield size={16} className="text-[#3CB697]" />
          </div>
          <span
            className="text-sm font-bold text-[#E8E6DF] tracking-tight"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            ATS Fraud Detector
          </span>
        </div>

        <div className="flex items-center gap-3">
          {isLoggedIn ? (
            <a
              href="/dashboard/scan"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#3CB697] text-[#0B0D12] text-xs font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)] transition-all duration-200"
              style={{ fontFamily: 'var(--font-space-grotesk)' }}
            >
              Go to Dashboard <ArrowRight size={12} />
            </a>
          ) : (
            <div className="flex items-center gap-2">
              <a
                href="/auth"
                className="px-3.5 py-2 rounded-xl text-xs font-medium text-[#8A90A4] hover:text-[#E8E6DF] hover:bg-[#1E2230]/60 transition-all duration-200"
              >
                Sign In
              </a>
              <a
                href="/auth?tab=register"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#3CB697] text-[#0B0D12] text-xs font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)] transition-all duration-200"
                style={{ fontFamily: 'var(--font-space-grotesk)' }}
              >
                Get Started <ArrowRight size={12} />
              </a>
            </div>
          )}
        </div>
      </nav>

      {/* ── 3D Forensic Scanner Hero ───────────────────────────────────────── */}
      <section className="relative min-h-[640px] lg:min-h-[720px] flex items-center justify-center px-4 overflow-hidden">
        {/* Background 3D Canvas */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          className="absolute inset-0 z-0"
        >
          <HeroScene />
        </motion.div>

        {/* Ambient Dark Gradient Vignettes so text remains highly readable */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0B0D12]/75 via-[#0B0D12]/50 to-[#0B0D12] pointer-events-none z-10" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#0B0D12] to-transparent pointer-events-none z-10" />

        {/* Hero Content with Staggered Entrance */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="relative z-20 max-w-3xl mx-auto text-center flex flex-col items-center py-12 sm:py-16"
        >
          {/* Eyebrow badge */}
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 mb-6 px-3.5 py-1.5 rounded-full border border-[rgba(60,182,151,0.3)] bg-[#131620]/80 backdrop-blur-md shadow-[0_0_20px_rgba(60,182,151,0.12)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[#3CB697] pulse-dot" />
            <span
              className="text-[11px] font-semibold text-[#3CB697] uppercase tracking-[0.14em]"
              style={{ fontFamily: 'var(--font-jetbrains-mono)' }}
            >
              Forensic Scanner Engine · Live
            </span>
          </motion.div>

          {/* Value Prop Headline */}
          <motion.h1
            variants={itemVariants}
            className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.08] mb-6 drop-shadow-sm"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            <span className="text-[#E8E6DF]">Stop ATS Fraud </span>
            <br />
            <span className="gradient-text">Before It Starts</span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            variants={itemVariants}
            className="text-[#8A90A4] text-base sm:text-lg max-w-xl mx-auto leading-relaxed mb-10 text-balance"
          >
            Military-grade resume forensics for recruiting teams. Detect invisible white text,
            homoglyphs, layout hijacking, and synthetic AI authorship before candidates enter your pipeline.
          </motion.p>

          {/* Action CTAs */}
          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row items-center justify-center gap-3.5 w-full sm:w-auto"
          >
            {isLoggedIn ? (
              <>
                <a
                  href="/dashboard/scan"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-[#3CB697] text-[#0B0D12] text-sm font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_32px_rgba(60,182,151,0.4)] transition-all duration-200"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  Open Dashboard <ArrowRight size={14} />
                </a>
                <a
                  href="/dashboard/roadmap"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl border border-[rgba(60,182,151,0.25)] bg-[#131620]/60 backdrop-blur-md text-[#E8E6DF] text-sm font-medium hover:border-[rgba(60,182,151,0.45)] hover:bg-[rgba(60,182,151,0.06)] transition-all duration-200"
                >
                  <Sparkles size={14} className="text-[#3CB697]" />
                  View Future Roadmap
                </a>
              </>
            ) : (
              <>
                <a
                  href="/auth"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-[#3CB697] text-[#0B0D12] text-sm font-bold hover:bg-[#3CB697]/90 hover:shadow-[0_0_32px_rgba(60,182,151,0.4)] transition-all duration-200"
                  style={{ fontFamily: 'var(--font-space-grotesk)' }}
                >
                  Start Scanning <ArrowRight size={14} />
                </a>
                <a
                  href="/auth?tab=register"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl border border-[rgba(60,182,151,0.25)] bg-[#131620]/60 backdrop-blur-md text-[#E8E6DF] text-sm font-medium hover:border-[rgba(60,182,151,0.45)] hover:bg-[rgba(60,182,151,0.06)] transition-all duration-200"
                >
                  Create Free Account
                </a>
              </>
            )}
          </motion.div>
        </motion.div>
      </section>

      {/* ── Live features ─────────────────────────────────────────────────── */}
      <section className="px-4 sm:px-6 py-20 max-w-5xl mx-auto w-full">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center text-[11px] font-semibold text-[#3CB697] uppercase tracking-[0.15em] mb-10"
          style={{ fontFamily: 'var(--font-jetbrains-mono)' }}
        >
          What&apos;s shipped today
        </motion.p>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: '-40px' }}
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: 0.12 } },
          }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4"
        >
          {LIVE_FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                variants={{
                  hidden: { opacity: 0, y: 16 },
                  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: 'easeOut' } },
                }}
                className="glass-card rounded-2xl p-5 flex flex-col gap-3 hover:border-[#3CB697]/30 transition-colors"
              >
                <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center flex-shrink-0">
                  <Icon size={16} className="text-[#3CB697]" />
                </div>
                <div>
                  <h3
                    className="text-sm font-semibold text-[#E8E6DF] mb-1"
                    style={{ fontFamily: 'var(--font-space-grotesk)' }}
                  >
                    {f.title}
                  </h3>
                  <p className="text-xs text-[#8A90A4] leading-relaxed">{f.description}</p>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </section>

      {/* ── Roadmap Section (Pitch / Demo) ─────────────────────────────────── */}
      <RoadmapSection />

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="mt-auto border-t border-[rgba(60,182,151,0.08)] px-6 py-8 text-center bg-[#0B0D12]">
        <p className="text-xs text-[#8A90A4]/60">
          ATS Fraud Detector · Built for hackathon demo ·{' '}
          <a href="/auth" className="text-[#3CB697] hover:underline">
            Sign in to the dashboard
          </a>
        </p>
      </footer>
    </div>
  );
}
