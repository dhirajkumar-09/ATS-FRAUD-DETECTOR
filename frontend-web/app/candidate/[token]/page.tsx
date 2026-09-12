'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getPublicScanResult } from '@/lib/api/scan';
import { Brain, FileText, AlertTriangle, ShieldCheck, Target, Loader2, Info } from 'lucide-react';
import { formatPercent } from '@/lib/utils';
import TrustGauge from '@/components/scan/TrustGauge';
import { motion } from 'framer-motion';

export default function CandidatePublicView() {
  const params = useParams();
  const token = typeof params?.token === 'string' ? params.token : null;

  // We can initialize error/loading based on token existence directly
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(token ? null : 'Invalid share link.');
  const [loading, setLoading] = useState(!!token);

  useEffect(() => {
    if (!token) return;

    getPublicScanResult(token)
      .then((res) => setData(res as Record<string, unknown>))
      .catch((err) => {
        setError(err.response?.data?.detail || 'Scan not found or link expired.');
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B0D12] flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-[#3CB697]" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#0B0D12] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-[#131620] border border-[rgba(255,255,255,0.05)] rounded-2xl p-6 text-center">
          <AlertTriangle size={32} className="text-[#E05252] mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-[#E8E6DF] mb-2">Link Unavailable</h1>
          <p className="text-sm text-[#8A90A4]">{error}</p>
        </div>
      </div>
    );
  }

  interface PublicScanData {
    filename: string;
    scanned_at: string | null;
    trust_score: number;
    trust_label: string;
    ai_content_score: number;
    true_match_score: number | null;
    narrative: {
      summary?: string;
      key_factors?: string[];
      recommendation?: string;
      limitations_disclaimer?: string;
    };
  }

  const {
    filename,
    scanned_at,
    trust_score,
    trust_label,
    ai_content_score,
    true_match_score,
    narrative
  } = data as unknown as PublicScanData;

  const aiScore = ai_content_score;
  const matchScore = true_match_score;
  const aiColor = (aiScore ?? 0) >= 0.7 ? '#E05252' : (aiScore ?? 0) >= 0.4 ? '#E09C52' : '#3CB697';

  return (
    <div className="min-h-screen bg-[#0B0D12] text-[#E8E6DF] py-12 px-4 sm:px-6 font-sans">
      <div className="max-w-3xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#1E2230] border border-[rgba(255,255,255,0.05)] mb-4 shadow-[0_0_15px_rgba(0,0,0,0.5)]">
            <ShieldCheck size={24} className="text-[#3CB697]" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mb-2" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            Automated Resume Feedback
          </h1>
          <p className="text-[#8A90A4] text-sm">
            For: <strong className="text-[#E8E6DF]">{filename}</strong> • Scanned: {scanned_at ? new Date(scanned_at).toLocaleDateString() : 'Unknown'}
          </p>
        </header>

        {/* Top metrics row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2 bg-[#131620] rounded-2xl border border-[rgba(255,255,255,0.05)] p-5 md:p-8 flex flex-col md:flex-row items-center gap-8">
            <div className="w-32 h-32 md:w-40 md:h-40 flex-shrink-0">
              <TrustGauge score={trust_score ?? 0} size={160} label={trust_label} />
            </div>
            <div className="flex-1 text-center md:text-left space-y-2">
              <h2 className="text-lg font-semibold" style={{ fontFamily: 'var(--font-space-grotesk)' }}>Overall Trust Score</h2>
              <p className="text-sm text-[#8A90A4] leading-relaxed">
                This score represents the structural integrity and authenticity of the document formatting.
                Lower scores indicate non-standard formatting, hidden text, or unusual fonts that automated ATS systems struggle to read correctly.
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="bg-[#131620] rounded-2xl border border-[rgba(255,255,255,0.05)] p-5 flex flex-col items-center justify-center text-center flex-1">
              <Brain size={20} color={aiColor} className="mb-2" />
              <span className="text-sm font-medium text-[#8A90A4] mb-1">AI Content Likelihood</span>
              <span className="text-2xl font-bold tabular-nums" style={{ color: aiColor, fontFamily: 'var(--font-space-grotesk)' }}>
                {formatPercent(aiScore ?? 0)}
              </span>
            </div>
            <div className="bg-[#131620] rounded-2xl border border-[rgba(255,255,255,0.05)] p-5 flex flex-col items-center justify-center text-center flex-1">
              <Target size={20} className="text-[#3B82F6] mb-2" />
              <span className="text-sm font-medium text-[#8A90A4] mb-1">Job Match Score</span>
              <span className="text-2xl font-bold tabular-nums text-[#3B82F6]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
                {matchScore != null ? formatPercent(matchScore) : '-'}
              </span>
            </div>
          </div>
        </div>

        {/* Narrative / Findings */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[#131620] rounded-2xl border border-[rgba(255,255,255,0.05)] overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-[rgba(255,255,255,0.05)] flex items-center gap-2">
            <FileText size={16} className="text-[#E8E6DF]/70" />
            <h3 className="text-sm font-semibold text-[#E8E6DF] uppercase tracking-wide">Summary of Findings</h3>
          </div>
          
          <div className="p-6 space-y-6">
            <div>
              <p className="text-sm text-[#E8E6DF] leading-relaxed">
                {narrative.summary}
              </p>
            </div>

            {narrative.key_factors && narrative.key_factors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-[#8A90A4] uppercase tracking-wider mb-3">Key Factors</h4>
                <ul className="space-y-3">
                  {narrative.key_factors.map((factor: string, idx: number) => (
                    <li key={idx} className="flex gap-3 text-sm text-[#E8E6DF] leading-relaxed bg-[#1E2230]/50 p-3 rounded-lg border border-[rgba(255,255,255,0.02)]">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#3CB697] mt-1.5 flex-shrink-0" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <p className="text-sm text-[#E8E6DF] font-medium p-4 bg-[#3CB697]/5 border border-[#3CB697]/10 rounded-lg">
                <strong className="text-[#3CB697] mr-1">Recommendation:</strong> {narrative.recommendation}
              </p>
            </div>
          </div>
          
          <div className="bg-[#0B0D12] px-6 py-4 border-t border-[rgba(255,255,255,0.02)] flex items-start gap-3">
            <Info size={14} className="text-[#8A90A4] mt-0.5 flex-shrink-0" />
            <p className="text-xs text-[#8A90A4] leading-relaxed italic">
              {narrative.limitations_disclaimer}
            </p>
          </div>
        </motion.div>

      </div>
    </div>
  );
}
