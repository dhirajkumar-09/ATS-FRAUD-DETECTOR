'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { useRouter } from 'next/navigation';
import {
  Download, Search, Award, Brain, Target,
  Sparkles, FileText, Loader2, ChevronRight,
  Link, Copy, Check, Trash2, Globe, ShieldAlert, HelpCircle, ChevronDown,
  CheckCircle2
} from 'lucide-react';
import { toast } from 'sonner';
import TrustGauge from './TrustGauge';
import FraudSignalList from './FraudSignalList';
import NarrativeCard from './NarrativeCard';
import { downloadReport } from '@/lib/api/report';
import { getBadgeUrl, createShareLink, revokeShareLink } from '@/lib/api/scan';
import { getOrgSettings } from '@/lib/api/auth';
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
};

const BREAKDOWN_CATEGORIES = [
  { label: 'Hidden / Invisible Text',      key: 'hidden_text',      max: 25 },
  { label: 'Zero-width Unicode',           key: 'zero_width_chars', max: 15 },
  { label: 'Homoglyph / Mixed Script',     key: 'homoglyph',        max: 15 },
  { label: 'Off-page / Abnormal Position', key: 'offpage',          max: 15 },
  { label: 'Font / Rendering Anomaly',     key: 'font_anomaly',     max: 10 },
  { label: 'PDF Metadata / Structure',     key: 'metadata',         max: 10 },
  { label: 'Prompt Injection',             key: 'prompt_injection', max: 10 },
] as const;


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

  // Candidate Transparency
  const [transparencyEnabled, setTransparencyEnabled] = useState(false);
  const [shareToken, setShareToken] = useState<string | null>(result.share_token || null);
  const [generatingLink, setGeneratingLink] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    getOrgSettings().then(s => {
      setTransparencyEnabled(s.candidate_transparency_enabled);
    }).catch(() => {});
  }, []);

  const handleCreateShareLink = async () => {
    setGeneratingLink(true);
    try {
      const newToken = await createShareLink(Number(result.scan_id));
      setShareToken(newToken);
      toast.success('Public share link generated');
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || 'Failed to generate share link');
    } finally {
      setGeneratingLink(false);
    }
  };

  const handleRevokeShareLink = async () => {
    try {
      await revokeShareLink(Number(result.scan_id));
      setShareToken(null);
      toast.success('Share link revoked');
    } catch {
      toast.error('Failed to revoke link');
    }
  };

  const shareUrl = typeof window !== 'undefined' && shareToken 
    ? `${window.location.origin}/candidate/${shareToken}` 
    : '';

  const copyToClipboard = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
    toast.success('Link copied to clipboard');
  };

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

  const [whyScoreOpen, setWhyScoreOpen] = useState(false);

  const trustScoreNum = Math.round(result.trust_score ?? 0);
  const riskBreakdown = (result.risk_breakdown ?? {}) as Record<string, number>;

  // Compute breakdown points sum across all 7 forensic categories
  const breakdownSum = BREAKDOWN_CATEGORIES.reduce((sum, cat) => {
    return sum + (Number(riskBreakdown[cat.key]) || 0);
  }, 0);

  const signalSum = (result.fraud_signals ?? []).reduce((sum, s) => sum + (s.risk_points ?? 0), 0);
  const hasSignals = (result.fraud_signals ?? []).length > 0;
  const rawRisk = result.forensic_risk_score != null
    ? result.forensic_risk_score
    : (breakdownSum > 0 ? breakdownSum : signalSum);

  // If there are zero detected signals and zero breakdown points, risk is strictly 0.
  // Never fall back to (100 - trustScore) as Trust Score includes AI Content & Job Match weighting.
  const forensicRisk = (!hasSignals && breakdownSum === 0)
    ? 0
    : Math.min(100, Math.max(0, Math.round(rawRisk)));

  const aiScore = result.ai_content_score;
  const matchScore = result.true_match_score;
  const aiColor = (aiScore ?? 0) >= 70 ? '#E05252' : (aiScore ?? 0) >= 40 ? '#E09C52' : '#3CB697';
  const riskColor = forensicRisk > 40 ? '#E05252' : forensicRisk > 15 ? '#E09C52' : '#3CB697';

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
          <div className="flex-shrink-0 flex flex-col items-center">
            <TrustGauge score={result.trust_score} label={result.trust_label} size={156} />
            <span className="text-[10px] text-[#8A90A4] mt-2 text-center max-w-[160px] leading-tight">
              Score represents detected document-risk indicators per our forensic model.
            </span>
          </div>

          {/* Metrics grid + actions */}
          <div className="flex-1 w-full space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <MetricCard
                label="Forensic Risk"
                value={`${forensicRisk}/100`}
                icon={ShieldAlert}
                color={riskColor}
                sublabel={`Verdict: ${result.trust_label ?? 'Unknown'}`}
              />
              <MetricCard
                label="AI Content Signal"
                value={formatPercent(aiScore)}
                icon={Brain}
                color={aiColor}
                sublabel={
                  (aiScore ?? 0) >= 70 ? 'Likely AI-written'
                  : (aiScore ?? 0) >= 40 ? 'Possibly AI-written'
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

            {/* AI Content Disclaimer */}
            <div className="text-[10px] text-[#8A90A4]/80 flex items-center gap-1.5 px-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#8A90A4] flex-shrink-0" />
              <span>AI-content detection is probabilistic and should not be used as the sole basis for rejecting a candidate.</span>
            </div>

            {/* "Why this score?" Accordion Trigger */}
            <div className="pt-0.5">
              <button
                onClick={() => setWhyScoreOpen((o) => !o)}
                className="flex items-center gap-1.5 text-xs font-semibold text-[#3CB697] hover:underline cursor-pointer"
                aria-expanded={whyScoreOpen}
              >
                <HelpCircle size={13} />
                <span>Why this score? (Explainable Breakdown)</span>
                <ChevronDown size={13} className={cn("transition-transform duration-200", whyScoreOpen ? "rotate-180" : "")} />
              </button>
            </div>

            {/* "Why this score?" Collapsible Table */}
            {whyScoreOpen && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="rounded-xl bg-[#0F1118] border border-[rgba(60,182,151,0.18)] p-4 space-y-3"
              >
                <div className="flex justify-between items-center border-b border-white/5 pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-[#E8E6DF]">
                    Risk Points Scoring Model (Max 100 Points)
                  </span>
                  <span className="text-[11px] font-mono text-[#8A90A4]">
                    Forensic Trust = 100 − Risk
                  </span>
                </div>
                <div className="space-y-1.5 text-xs font-mono">
                  {BREAKDOWN_CATEGORIES.map((cat) => {
                    const pts = Math.round(Number(riskBreakdown[cat.key]) || 0);
                    return (
                      <div key={cat.key} className="flex justify-between items-center py-1 px-2 rounded hover:bg-white/[0.02]">
                        <span className="text-[#8A90A4]">{cat.label}</span>
                        <span className={cn(pts > 0 ? "text-[#E05252] font-bold" : "text-[#8A90A4]")}>
                          {pts} / {cat.max}
                        </span>
                      </div>
                    );
                  })}
                  <div className="border-t border-white/10 pt-2 mt-2 flex justify-between font-bold text-sm">
                    <span className="text-[#E8E6DF]">TOTAL RISK SCORE</span>
                    <span className={cn(forensicRisk > 0 ? "text-[#E05252]" : "text-[#3CB697]")}>
                      {forensicRisk} / 100
                    </span>
                  </div>
                  <div className="flex justify-between font-bold text-sm text-[#3CB697]">
                    <span>COMPOSITE TRUST SCORE</span>
                    <span>{trustScoreNum} / 100</span>
                  </div>
                  {forensicRisk === 0 && trustScoreNum < 100 && (
                    <div className="text-[11px] text-[#8A90A4] bg-white/[0.03] border border-white/5 rounded-lg p-2.5 space-y-1 mt-2">
                      <p className="text-[#3CB697] font-semibold flex items-center gap-1.5">
                        <CheckCircle2 size={13} className="flex-shrink-0" />
                        Zero Document Manipulation (0 / 100 Risk)
                      </p>
                      <p className="text-[10px] text-[#8A90A4] leading-relaxed">
                        No invisible text, zero-width Unicode, homoglyphs, or font tampering detected.
                        The Trust Score ({trustScoreNum}/100) reflects the probabilistic AI Content signal ({Math.round(aiScore ?? 0)}%), not document fraud.
                      </p>
                    </div>
                  )}
                </div>
                <p className="text-[10px] text-[#8A90A4] leading-relaxed pt-2 border-t border-white/5">
                  Every risk point comes directly from verifiable forensic detections performed on the uploaded PDF. Scores are deterministic and reproducible.
                </p>
              </motion.div>
            )}

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2 pt-1">
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
              {transparencyEnabled && !shareToken && (
                <ActionBtn
                  onClick={handleCreateShareLink}
                  disabled={generatingLink}
                  icon={Link}
                  label={generatingLink ? 'Generating…' : 'Share Link'}
                  loading={generatingLink}
                />
              )}
              {transparencyEnabled && shareToken && (
                <div className="flex bg-[#1E2230] border border-[#3CB697]/25 rounded-xl overflow-hidden ml-auto max-w-[280px]">
                  <div className="px-3 py-2 flex items-center bg-[#3CB697]/10 text-xs text-[#3CB697] font-mono truncate border-r border-[#3CB697]/20 select-none">
                    <Globe size={12} className="mr-1.5 flex-shrink-0" />
                    {shareUrl}
                  </div>
                  <button
                    onClick={copyToClipboard}
                    className="px-3 py-2 text-[#E8E6DF]/70 hover:text-[#E8E6DF] hover:bg-[#252A3B] transition-colors"
                    title="Copy Link"
                  >
                    {copiedLink ? <Check size={14} className="text-[#3CB697]" /> : <Copy size={14} />}
                  </button>
                  <button
                    onClick={handleRevokeShareLink}
                    className="px-3 py-2 text-[#E05252]/70 hover:text-[#E05252] hover:bg-[#252A3B] transition-colors border-l border-[#3CB697]/20"
                    title="Revoke Link"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
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
              { value: 'ai_breakdown', label: 'AI Breakdown' },
              { value: 'gemini',    label: 'AI Report', icon: Sparkles },
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
                  <div className="prose prose-sm prose-invert max-w-none text-[#E8E6DF]/80 text-sm leading-7">
                    {geminiReport.split('\n').map((line, i) => {
                      if (line.startsWith('## ')) {
                        return <h3 key={i} className="text-base font-bold text-[#3CB697] mt-5 mb-2">{line.slice(3)}</h3>;
                      }
                      if (line.startsWith('# ')) {
                        return <h2 key={i} className="text-lg font-bold text-[#E8E6DF] mt-6 mb-3">{line.slice(2)}</h2>;
                      }
                      if (line.startsWith('* ') || line.startsWith('- ')) {
                        return (
                          <div key={i} className="flex gap-2.5 mb-1.5 ml-1">
                            <span className="text-[#3CB697] font-bold mt-0.5">•</span>
                            <span dangerouslySetInnerHTML={{ __html: line.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong class="text-[#E8E6DF] font-semibold">$1</strong>').replace(/`(.+?)`/g, '<code class="text-[#3CB697] bg-[#3CB697]/10 px-1 py-0.5 rounded text-[11px] font-mono">$1</code>') }} />
                          </div>
                        );
                      }
                      if (line.trim() === '' || line.trim() === '---') {
                        return <div key={i} className="h-2" />;
                      }
                      return (
                        <p key={i} className="mb-2" dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-[#E8E6DF] font-semibold">$1</strong>').replace(/`(.+?)`/g, '<code class="text-[#3CB697] bg-[#3CB697]/10 px-1 py-0.5 rounded text-[11px] font-mono">$1</code>') }} />
                      );
                    })}
                  </div>
                </div>
              </motion.div>
            )}
          </TabsContent>

          {/* ── AI Breakdown ──────────────────────────────────────────────────────── */}
          <TabsContent value="ai_breakdown" className="mt-0 outline-none">
            {result.paragraph_ai_breakdown && result.paragraph_ai_breakdown.length > 0 ? (
              <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                {result.paragraph_ai_breakdown.map((p, i) => {
                  const score = p.ai_score;
                  const isHigh = score >= 70;
                  const isMedium = score >= 40 && score < 70;
                  const bgClass = isHigh ? 'bg-[#E05252]/10 border-[#E05252]/30 text-[#E05252]' :
                                 isMedium ? 'bg-[#F59E0B]/10 border-[#F59E0B]/30 text-[#F59E0B]' :
                                 'bg-[#3CB697]/10 border-[#3CB697]/30 text-[#E8E6DF]';

                  return (
                    <div key={i} className={`p-4 rounded-xl border ${bgClass} transition-colors`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-semibold uppercase tracking-wider">
                          Page {p.page} • Paragraph {p.paragraph_index + 1}
                        </span>
                        <span className="text-xs font-bold font-mono">
                          {score.toFixed(1)}% AI
                        </span>
                      </div>
                      <p className="text-sm font-serif leading-relaxed opacity-90">{p.text_snippet}</p>
                      
                      {p.contributing_factors && p.contributing_factors.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-current/20">
                          <span className="text-[10px] font-mono uppercase opacity-70">Contributing Factors:</span>
                          <ul className="list-disc pl-4 mt-1 text-xs opacity-90">
                            {p.contributing_factors.map((f, idx) => (
                              <li key={idx}>{f}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="glass-card rounded-xl p-8 text-center text-sm text-[#7A8099]">
                <Brain size={24} className="mx-auto mb-3 opacity-50" />
                No paragraph-level AI breakdown available for this scan.
              </div>
            )}
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}
