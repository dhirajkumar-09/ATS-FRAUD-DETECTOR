'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Download, Search, Award, Brain, Target, ChevronRight, Sparkles, FileText, Loader2 } from 'lucide-react';
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

const stagger = {
  container: {
    hidden: {},
    show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
  },
  item: {
    hidden: { opacity: 0, y: 14 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  },
};

function ScoreChip({
  label,
  value,
  icon: Icon,
  color = '#7A8099',
}: {
  label: string;
  value: string | null;
  icon: IconComponent;
  color?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5 items-center p-4 rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.10)]">
      <Icon size={16} style={{ color }} />
      <span
        className="text-xl font-bold tabular-nums"
        style={{ color, fontFamily: 'var(--font-space-grotesk)' }}
      >
        {value ?? '—'}
      </span>
      <span className="text-[10px] text-[#7A8099] uppercase tracking-widest text-center">{label}</span>
    </div>
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
      await downloadReport(result.scan_id, token);
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
      const msg = (e as Error).message ?? 'Failed to generate report';
      toast.error(msg);
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <motion.div
      variants={stagger.container}
      initial="hidden"
      animate="show"
      className="space-y-5"
    >
      {/* ── Header row ── */}
      <motion.div
        variants={stagger.item}
        className="glass-card rounded-xl p-5 flex flex-col sm:flex-row gap-6 items-center"
      >
        {/* Gauge */}
        <TrustGauge score={result.trust_score} label={result.trust_label} size={160} />

        {/* Score chips */}
        <div className="flex-1 w-full">
          <p
            className="text-sm text-[#7A8099] mb-3 font-mono truncate"
            title={result.filename}
          >
            📄 {result.filename}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <ScoreChip
              label="AI Content"
              value={formatPercent(result.ai_content_score)}
              icon={Brain}
              color="#A855F7"
            />
            <ScoreChip
              label="Job Match"
              value={result.true_match_score != null ? formatPercent(result.true_match_score) : null}
              icon={Target}
              color="#3B82F6"
            />
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 mt-4">
            <button
              onClick={() => router.push(`/dashboard/inspect/${result.scan_id}`)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 text-xs font-medium text-[#3CB697] hover:bg-[#3CB697]/20 transition-colors"
            >
              <Search size={13} />
              Span Inspector
              <ChevronRight size={12} />
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.15)] text-xs font-medium text-[#E8E6DF]/70 hover:text-[#E8E6DF] hover:border-[rgba(60,182,151,0.3)] transition-colors',
                downloading && 'opacity-60 cursor-not-allowed',
              )}
            >
              <Download size={13} />
              {downloading ? 'Downloading…' : 'PDF Report'}
            </button>
            <button
              onClick={() => setBadgeOpen((o) => !o)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.15)] text-xs font-medium text-[#E8E6DF]/70 hover:text-[#E8E6DF] hover:border-[rgba(60,182,151,0.3)] transition-colors"
            >
              <Award size={13} />
              Trust Badge
            </button>
            <button
              onClick={handleGeminiReport}
              disabled={generatingReport}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-colors',
                'bg-[#3CB697]/8 border-[#3CB697]/25 text-[#3CB697] hover:bg-[#3CB697]/15',
                generatingReport && 'opacity-60 cursor-not-allowed',
              )}
            >
              {generatingReport
                ? <><Loader2 size={13} className="animate-spin" /> Generating…</>
                : <><Sparkles size={13} /> AI Report</>
              }
            </button>
          </div>

          {/* Badge preview */}
          {badgeOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mt-3 flex items-center gap-3"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={getBadgeUrl(result.scan_id)}
                alt="Trust badge"
                className="h-6"
              />
              <a
                href={getBadgeUrl(result.scan_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#3CB697] hover:underline"
              >
                Open SVG ↗
              </a>
            </motion.div>
          )}
        </div>
      </motion.div>

      {/* ── Tabs: Signals / Narrative ── */}
      <motion.div variants={stagger.item}>
        <Tabs defaultValue="signals" className="w-full">
          <TabsList className="bg-[#171A22] border border-[rgba(60,182,151,0.12)] p-1 mb-4 w-full sm:w-auto">
            <TabsTrigger
              value="signals"
              className="text-xs data-[state=active]:bg-[#3CB697] data-[state=active]:text-[#0D0F14] data-[state=active]:shadow-none text-[#7A8099]"
            >
              Fraud Signals ({result.fraud_signals?.length ?? 0})
            </TabsTrigger>
            <TabsTrigger
              value="narrative"
              className="text-xs data-[state=active]:bg-[#3CB697] data-[state=active]:text-[#0D0F14] data-[state=active]:shadow-none text-[#7A8099]"
            >
              AI Briefing
            </TabsTrigger>
            <TabsTrigger
              value="gemini"
              className="text-xs data-[state=active]:bg-[#3CB697] data-[state=active]:text-[#0D0F14] data-[state=active]:shadow-none text-[#7A8099]"
            >
              <Sparkles size={11} className="mr-1 inline" />
              Gemini Report
            </TabsTrigger>
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
              <div className="flex flex-col items-center gap-4 py-10 text-center">
                <div className="w-12 h-12 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
                  <Sparkles size={20} className="text-[#3CB697]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#E8E6DF] mb-1">Generate an AI-enhanced report</p>
                  <p className="text-xs text-[#7A8099]">
                    Gemini will analyze this scan and produce a detailed forensic report
                  </p>
                </div>
                <button
                  onClick={handleGeminiReport}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697] text-[#0D0F14] text-sm font-semibold hover:bg-[#3CB697]/90 transition-colors"
                >
                  <Sparkles size={14} />
                  Generate Report
                </button>
              </div>
            )}

            {generatingReport && (
              <div className="flex items-center gap-3 py-8 justify-center">
                <Loader2 size={16} className="text-[#3CB697] animate-spin" />
                <span className="text-sm text-[#7A8099]">Gemini is analyzing your resume…</span>
              </div>
            )}

            {geminiReport && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] overflow-hidden"
              >
                <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(60,182,151,0.08)]">
                  <div className="flex items-center gap-2">
                    <Sparkles size={13} className="text-[#3CB697]" />
                    <span className="text-xs font-semibold text-[#3CB697] uppercase tracking-widest">
                      Gemini Enhanced Report
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { navigator.clipboard.writeText(geminiReport); toast.success('Report copied!'); }}
                      className="text-xs text-[#7A8099] hover:text-[#E8E6DF] flex items-center gap-1 transition-colors"
                    >
                      <FileText size={11} /> Copy
                    </button>
                    <button
                      onClick={handleGeminiReport}
                      className="text-xs text-[#7A8099] hover:text-[#3CB697] flex items-center gap-1 transition-colors"
                    >
                      <Sparkles size={11} /> Regenerate
                    </button>
                  </div>
                </div>
                <div className="px-5 py-4 max-h-[500px] overflow-y-auto">
                  <div className="prose prose-sm prose-invert max-w-none text-[#E8E6DF]/80 text-sm leading-relaxed whitespace-pre-wrap">
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
