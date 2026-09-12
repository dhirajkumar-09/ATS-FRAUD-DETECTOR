'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { useRouter } from 'next/navigation';
import {
  Download, Search, Award, Brain, Target,
  Sparkles, FileText, Loader2, ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';
import TrustGauge from './TrustGauge';
import FraudSignalList from './FraudSignalList';
import NarrativeCard from './NarrativeCard';
import { downloadReport } from '@/lib/api/report';
import { getBadgeUrl } from '@/lib/api/scan';
import { useAuthStore } from '@/store/auth';
import { formatPercent, cn } from '@/lib/utils';
import type { ScanResult } from '@/lib/types';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { generateEnhancedReport } from '@/lib/gemini';

type IconComponent = React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>;

interface Props {
  result: ScanResult;
}

const containerVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.08 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.35 } },
};


// ── Score metric card ─────────────────────────────────────────────────────────
function MetricCard({
  label,
  value,
  icon: Icon,
  color = '#8A90A4',
  sublabel,
}: {
  label:    string;
  value:    string | null;
  icon:     IconComponent;
  color?:   string;
  sublabel?: string;
}) {
  return (
    <div className="flex flex-col gap-2 p-4 rounded-xl bg-[#131620] border border-[rgba(60,182,151,0.10)] hover:border-[rgba(60,182,151,0.20)] transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold text-[#8A90A4] uppercase tracking-[0.12em]">{label}</span>
        <Icon size={13} style={{ color }} />
      </div>
      <span
        className="text-2xl font-bold tabular-nums leading-none"
        style={{ color, fontFamily: 'var(--font-space-grotesk)' }}
      >
        {value ?? <span className="text-[#8A90A4] text-lg">—</span>}
      </span>
      {sublabel && (
        <span className="text-[10px] text-[#8A90A4]">{sublabel}</span>
      )}
    </div>
  );
}

// ── Action button ─────────────────────────────────────────────────────────────
function ActionBtn({
  onClick,
  disabled,
  icon: Icon,
  label,
  variant = 'default',
  loading,
}: {
  onClick: () => void;
  disabled?: boolean;
  icon: IconComponent;
  label: string;
  variant?: 'default' | 'primary' | 'gem';
  loading?: boolean;
}) {
  const base = 'flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    default: 'bg-[#1E2230] border border-[rgba(60,182,151,0.15)] text-[#E8E6DF]/70 hover:text-[#E8E6DF] hover:border-[rgba(60,182,151,0.28)]',
    primary: 'bg-[#3CB697]/12 border border-[#3CB697]/25 text-[#3CB697] hover:bg-[#3CB697]/20',
    gem:     'bg-[#3CB697] text-[#0B0D12] hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)]',
  };
  return (
    <button onClick={onClick} disabled={disabled} className={cn(base, variants[variant])}>
      {loading ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

export default function ScanResultPanel({ result }: Props) {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const [downloading, setDownloading] = useState(false);
  const [badgeOpen, setBadgeOpen] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [geminiReport, setGeminiReport] = useState<string | null>(null);

  const handleDownload = async () => {
    if (!token) return;
    setDownloading(true);
    try {
      await downloadReport(String(result.scan_id), token);
      toast.success('Forensic report downloaded!');
    } catch {
      toast.error('Failed to download report');
    } finally {
      setDownloading(false);
    }
  };

  const handleGeminiReport = async () => {
    setGeneratingReport(true);
    setGeminiReport(null);
    try {
      const report = await generateEnhancedReport(result);
      setGeminiReport(report);
      toast.success('AI report generated!');
    } catch (e: unknown) {
      const msg = (e as Error).message ?? 'Failed to generate AI report';
      toast.error(msg);
    } finally {
      setGeneratingReport(false);
    }
  };

  const aiScore = result.ai_content_score;
  const matchScore = result.true_match_score;
  const aiColor = (aiScore ?? 0) >= 0.7 ? '#E05252' : (aiScore ?? 0) >= 0.4 ? '#E09C52' : '#3CB697';

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      {/* ── Hero card: gauge + scores ──────────────────────────────────────── */}
      <motion.div
        variants={itemVariants}
        className="glass-card rounded-2xl p-5 sm:p-6"
      >
        {/* Filename */}
        <p className="text-xs text-[#8A90A4] font-mono mb-5 flex items-center gap-2 min-w-0">
          <FileText size={11} className="flex-shrink-0 text-[#3CB697]" />
          <span className="truncate" title={result.filename}>{result.filename}</span>
        </p>

        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start">
          {/* Trust gauge */}
          <div className="flex-shrink-0">
            <TrustGauge score={result.trust_score} label={result.trust_label} size={156} />
          </div>

          {/* Metrics grid + actions */}
          <div className="flex-1 w-full space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                label="AI Content"
                value={formatPercent(aiScore)}
                icon={Brain}
                color={aiColor}
                sublabel={
                  (aiScore ?? 0) >= 0.7 ? 'Likely AI-written'
                  : (aiScore ?? 0) >= 0.4 ? 'Possibly AI-written'
                  : 'Likely human-written'
                }
              />
              <MetricCard
                label="Job Match"
                value={matchScore != null ? formatPercent(matchScore) : null}
                icon={Target}
                color="#3B82F6"
                sublabel={matchScore != null ? 'Against job description' : 'No JD provided'}
              />
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2">
              <ActionBtn
                onClick={() => router.push(`/dashboard/inspect/${result.scan_id}`)}
                icon={Search}
                label="Span Inspector"
                variant="primary"
              />
              <ActionBtn
                onClick={handleDownload}
                disabled={downloading}
                icon={Download}
                label={downloading ? 'Downloading…' : 'PDF Report'}
                loading={downloading}
              />
              <ActionBtn
                onClick={() => setBadgeOpen((o) => !o)}
                icon={Award}
                label="Trust Badge"
              />
              <ActionBtn
                onClick={handleGeminiReport}
                disabled={generatingReport}
                icon={Sparkles}
                label={generatingReport ? 'Generating…' : 'AI Report'}
                loading={generatingReport}
                variant="primary"
              />
            </div>

            {/* Badge preview */}
            {badgeOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-3 pt-1"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={getBadgeUrl(result.scan_id)} alt="Trust badge" className="h-6" />
                <a
                  href={getBadgeUrl(result.scan_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-[#3CB697] hover:underline flex items-center gap-1"
                >
                  Open SVG <ChevronRight size={11} />
                </a>
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>

      {/* ── Tabs: Signals / Narrative / Gemini ────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <Tabs defaultValue="signals" className="w-full">
          {/* Tab bar */}
          <TabsList className="h-auto bg-transparent border-b border-[rgba(60,182,151,0.10)] rounded-none p-0 mb-4 w-full gap-0">
            {[
              { value: 'signals',   label: `Fraud Signals (${result.fraud_signals?.length ?? 0})` },
              { value: 'narrative', label: 'AI Briefing' },
              { value: 'gemini',    label: 'Gemini Report', icon: Sparkles },
            ].map(({ value, label, icon: TabIcon }) => (
              <TabsTrigger
                key={value}
                value={value}
                className={cn(
                  'relative flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold rounded-none bg-transparent border-0 text-[#8A90A4]',
                  'hover:text-[#E8E6DF] transition-colors',
                  'data-[state=active]:text-[#3CB697] data-[state=active]:shadow-none',
                  'after:content-[""] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-[#3CB697] after:scale-x-0 after:transition-transform',
                  'data-[state=active]:after:scale-x-100',
                )}
              >
                {TabIcon && <TabIcon size={11} />}
                {label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="signals">
            <FraudSignalList
              signals={result.fraud_signals}
              fraudSummary={result.fraud_summary}
            />
          </TabsContent>

          <TabsContent value="narrative">
            <NarrativeCard narrative={result.narrative} />
          </TabsContent>

          <TabsContent value="gemini">
            {!geminiReport && !generatingReport && (
              <div className="flex flex-col items-center gap-5 py-12 text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
                  <Sparkles size={22} className="text-[#3CB697]" />
                </div>
                <div className="max-w-xs">
                  <p className="text-sm font-semibold text-[#E8E6DF] mb-1.5" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                    Generate an AI-Enhanced Report
                  </p>
                  <p className="text-xs text-[#8A90A4] leading-relaxed">
                    Gemini will analyze this scan and produce a detailed forensic report with hiring recommendations.
                  </p>
                </div>
                <button
                  onClick={handleGeminiReport}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697] text-[#0B0D12] text-sm font-semibold hover:bg-[#3CB697]/90 hover:shadow-[0_0_24px_rgba(60,182,151,0.3)] transition-all"
                >
                  <Sparkles size={14} />
                  Generate Report
                </button>
              </div>
            )}

            {generatingReport && (
              <div className="flex flex-col items-center gap-4 py-12">
                <div className="relative w-12 h-12">
                  <div className="absolute inset-0 rounded-full border-2 border-[#3CB697]/20" />
                  <div className="absolute inset-0 rounded-full border-2 border-[#3CB697] border-t-transparent animate-spin" />
                  <div className="absolute inset-2 flex items-center justify-center">
                    <Sparkles size={12} className="text-[#3CB697]" />
                  </div>
                </div>
                <p className="text-sm text-[#8A90A4]">Gemini is analyzing your resume…</p>
              </div>
            )}

            {geminiReport && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl bg-[#131620] border border-[rgba(60,182,151,0.12)] overflow-hidden"
              >
                {/* Report header */}
                <div className="flex items-center justify-between px-5 py-3.5 border-b border-[rgba(60,182,151,0.08)] bg-[#0B0D12]/40">
                  <div className="flex items-center gap-2">
                    <Sparkles size={13} className="text-[#3CB697]" />
                    <span className="text-xs font-bold text-[#3CB697] uppercase tracking-wider">
                      Gemini Enhanced Report
                    </span>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => { navigator.clipboard.writeText(geminiReport); toast.success('Copied to clipboard!'); }}
                      className="text-[11px] text-[#8A90A4] hover:text-[#E8E6DF] flex items-center gap-1.5 transition-colors"
                    >
                      <FileText size={11} />
                      Copy
                    </button>
                    <button
                      onClick={handleGeminiReport}
                      className="text-[11px] text-[#8A90A4] hover:text-[#3CB697] flex items-center gap-1.5 transition-colors"
                    >
                      <Sparkles size={11} />
                      Regenerate
                    </button>
                  </div>
                </div>

                {/* Report body */}
                <div className="px-5 py-5 max-h-[520px] overflow-y-auto">
                  <div className="prose prose-sm prose-invert max-w-none text-[#E8E6DF]/80 text-sm leading-7 whitespace-pre-wrap">
                    {geminiReport}
                  </div>
                </div>
              </motion.div>
            )}
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}
