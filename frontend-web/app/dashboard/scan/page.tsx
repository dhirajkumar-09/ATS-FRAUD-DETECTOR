'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { ScanLine, Loader2, FileText, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import FileDropZone from '@/components/scan/FileDropZone';
import ScanResultPanel from '@/components/scan/ScanResultPanel';
import { scanSingle } from '@/lib/api/scan';
import { cn } from '@/lib/utils';
import type { ScanResult } from '@/lib/types';

// ── Animation Variants (matching layout.tsx & Sidebar.tsx conventions) ──────
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.04,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: 'easeOut' },
  },
};

export default function ScanPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanTriggered, setScanTriggered] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result && !loading && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [result, loading]);

  const handleScan = async () => {
    if (!file || loading) return;

    // Trigger brief tactile micro-interaction on button before scan starts
    setScanTriggered(true);
    await new Promise((resolve) => setTimeout(resolve, 240));
    setLoading(true);
    setScanTriggered(false);
    setResult(null);

    try {
      const res = await scanSingle(file, jobDescription);
      setResult(res);
      toast.success('Forensic scan complete!');
    } catch (err: unknown) {
      const errorObj = err as {
        code?: string;
        message?: string;
        response?: { data?: { detail?: string } };
      };
      let msg = 'Scan failed. Please try again.';
      if (errorObj?.response?.data?.detail) {
        msg = errorObj.response.data.detail;
      } else if (errorObj?.code === 'ERR_NETWORK' || !errorObj?.response) {
        msg = 'Cannot connect to backend server. Make sure backend is running on http://localhost:8000.';
      } else if (errorObj?.message) {
        msg = errorObj.message;
      }
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-[calc(100vh-3.5rem)] py-8 px-4 sm:px-6 overflow-hidden">
      {/* ── Ambient Forensic Grid Texture (Subtle drift & radial fade) ── */}
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden select-none">
        {/* Faint coordinate dot-grid */}
        <div
          className="absolute inset-0 opacity-[0.035] bg-[radial-gradient(#3CB697_1px,transparent_1px)] [background-size:24px_24px]"
          style={{
            maskImage: 'radial-gradient(ellipse 75% 75% at 50% 30%, black 30%, transparent 100%)',
            WebkitMaskImage: 'radial-gradient(ellipse 75% 75% at 50% 30%, black 30%, transparent 100%)',
          }}
        />

        {/* Ambient ultra-soft teal bloom */}
        <motion.div
          animate={{
            scale: [1, 1.14, 1],
            opacity: [0.03, 0.065, 0.03],
          }}
          transition={{
            duration: 9,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute top-28 left-1/2 -translate-x-1/2 w-[640px] h-[360px] rounded-full bg-[#3CB697] blur-[130px]"
        />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto space-y-6">
        {/* ── Upload Card with Staggered Entrance ── */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="glass-card rounded-2xl p-5 sm:p-6 space-y-5 shadow-[0_4px_30px_rgba(0,0,0,0.35),0_0_24px_rgba(60,182,151,0.04)]"
        >
          {/* 1. File Drop Zone */}
          <motion.div variants={itemVariants}>
            <FileDropZone
              file={file}
              onFile={setFile}
              onClear={() => {
                setFile(null);
                setResult(null);
              }}
            />
          </motion.div>

          {/* 2. Job Description Field */}
          <motion.div variants={itemVariants} className="space-y-2">
            <label
              className="flex items-center gap-2 text-xs font-semibold text-[#8A90A4] uppercase tracking-[0.1em]"
              htmlFor="job-desc"
            >
              <Sparkles size={11} className="text-[#3CB697]" />
              Job Description
              <span className="text-[#8A90A4]/50 normal-case font-normal tracking-normal">
                (optional — enables job match scoring)
              </span>
            </label>
            <textarea
              id="job-desc"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the job description here to get a match score…"
              rows={4}
              className="w-full px-4 py-3 rounded-xl text-sm bg-[#0B0D12] border border-[rgba(60,182,151,0.12)] text-[#E8E6DF] placeholder:text-[#8A90A4]/60 outline-none resize-none transition-all focus:border-[#3CB697]/50 focus:ring-2 focus:ring-[#3CB697]/12"
            />
          </motion.div>

          {/* 3. Run Forensic Scan Button with Click Micro-Interaction */}
          <motion.div variants={itemVariants}>
            <motion.button
              onClick={handleScan}
              disabled={!file || loading}
              whileHover={{ scale: !file || loading ? 1 : 1.006 }}
              whileTap={{ scale: !file || loading ? 1 : 0.98 }}
              className={cn(
                "w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl text-sm font-bold bg-[#3CB697] text-[#0B0D12] hover:bg-[#3CB697]/92 transition-all duration-200 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
                file && !loading && !result
                  ? "shadow-[0_0_30px_rgba(60,182,151,0.5)] ring-2 ring-[#3CB697]/60"
                  : "hover:shadow-[0_0_30px_rgba(60,182,151,0.36)]"
              )}
              style={{ fontFamily: 'var(--font-space-grotesk)' }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Analyzing resume…
                </>
              ) : (
                <>
                  <motion.div
                    animate={
                      scanTriggered
                        ? {
                            rotate: [0, -25, 360],
                            scale: [1, 1.35, 1],
                          }
                        : { rotate: 0, scale: 1 }
                    }
                    transition={{ duration: 0.32, ease: 'easeInOut' }}
                  >
                    <ScanLine size={16} />
                  </motion.div>
                  {result ? 'Re-run Forensic Scan' : 'Run Forensic Scan'}
                </>
              )}
            </motion.button>
          </motion.div>
        </motion.div>

        {/* ── Loading Skeleton (Preserved as requested) ── */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-card rounded-2xl p-6 space-y-5 shadow-[0_4px_30px_rgba(0,0,0,0.35)]"
            >
              <div className="flex items-center gap-3">
                <div className="relative w-8 h-8">
                  <div className="absolute inset-0 rounded-full border-2 border-[#3CB697]/20" />
                  <div className="absolute inset-0 rounded-full border-2 border-[#3CB697] border-t-transparent animate-spin" />
                </div>
                <div>
                  <p
                    className="text-sm font-semibold text-[#E8E6DF]"
                    style={{ fontFamily: 'var(--font-space-grotesk)' }}
                  >
                    Running forensic analysis
                  </p>
                  <p className="text-xs text-[#8A90A4] mt-0.5">
                    Extracting text, scanning for fraud signals…
                  </p>
                </div>
              </div>
              {/* Animated progress bars */}
              <div className="space-y-3">
                {[
                  'Extracting text layers',
                  'Detecting fraud signals',
                  'Scoring trust and AI content',
                ].map((step, i) => (
                  <div key={step} className="space-y-1.5">
                    <p className="text-xs text-[#8A90A4] font-mono">{step}</p>
                    <div className="h-1.5 bg-[#1E2230] rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-[#3CB697]/60 rounded-full"
                        initial={{ width: '0%' }}
                        animate={{ width: ['0%', '80%', '95%'] }}
                        transition={{
                          duration: 3 + i * 0.8,
                          ease: 'easeOut',
                          repeat: Infinity,
                          repeatType: 'reverse',
                          delay: i * 0.4,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Results ── */}
        <AnimatePresence>
          {result && !loading && (
            <motion.div
              ref={resultRef}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
            >
              <ScanResultPanel result={result} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Elevated Animated Empty State (Illustration with Sweeping Scan-Line) ── */}
        {!file && !result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.22, duration: 0.45 }}
            className="flex flex-col items-center gap-4 py-12 text-center select-none"
          >
            {/* Animated Document Scan Illustration */}
            <div className="relative flex items-center justify-center w-20 h-20">
              {/* Soft pulsing ambient glow ring */}
              <motion.div
                animate={{
                  scale: [1, 1.25, 1],
                  opacity: [0.25, 0.55, 0.25],
                }}
                transition={{
                  duration: 3.5,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
                className="absolute inset-0 rounded-2xl bg-[#3CB697]/15 blur-xl pointer-events-none"
              />

              {/* Central Document Icon Container */}
              <div className="relative w-16 h-16 rounded-2xl bg-[#131620] border border-[rgba(60,182,151,0.22)] shadow-[0_0_24px_rgba(60,182,151,0.08)] flex items-center justify-center overflow-hidden">
                {/* Subtle grid pattern inside icon */}
                <div className="absolute inset-0 bg-[radial-gradient(#3CB697_1px,transparent_1px)] [background-size:8px_8px] opacity-15 pointer-events-none" />

                {/* Looping Sweeping Laser Scan-Line */}
                <motion.div
                  animate={{
                    y: [-34, 34],
                    opacity: [0, 1, 1, 0],
                  }}
                  transition={{
                    duration: 2.4,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                  className="absolute inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-[#3CB697] to-transparent shadow-[0_0_8px_#3CB697] pointer-events-none z-10"
                />

                <FileText size={24} className="text-[#3CB697] opacity-85 relative z-0" />
              </div>
            </div>

            <div>
              <p
                className="text-sm font-semibold text-[#E8E6DF] tracking-tight"
                style={{ fontFamily: 'var(--font-space-grotesk)' }}
              >
                Upload a resume PDF to get started
              </p>
              <p className="text-xs text-[#8A90A4] mt-1 font-mono">
                Forensic analysis takes 5–15 seconds · 9 fraud detectors active
              </p>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
