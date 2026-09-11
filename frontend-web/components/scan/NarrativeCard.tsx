'use client';

import { motion } from 'framer-motion';
import { FileText, CheckCircle2, AlertTriangle, Info, Lightbulb } from 'lucide-react';
import type { Narrative } from '@/lib/types';

interface Props {
  narrative: Narrative;
}

const stagger = {
  container: {
    hidden: {},
    show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
  },
  item: {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
  },
};

export default function NarrativeCard({ narrative }: Props) {
  const { verdict_title, recommendation, summary, key_factors, limitations_disclaimer } = narrative;

  return (
    <motion.div
      variants={stagger.container}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      {/* Verdict title */}
      <motion.div variants={stagger.item} className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
          <FileText size={14} className="text-[#3CB697]" />
        </div>
        <div>
          <p className="text-xs text-[#7A8099] font-mono uppercase tracking-widest mb-1">Verdict</p>
          <h3
            className="text-lg font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            {verdict_title}
          </h3>
        </div>
      </motion.div>

      {/* Summary */}
      <motion.div
        variants={stagger.item}
        className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] px-5 py-4"
      >
        <div className="flex items-center gap-2 mb-2">
          <Info size={13} className="text-[#3CB697]" />
          <span className="text-xs font-semibold text-[#3CB697] uppercase tracking-widest">Summary</span>
        </div>
        <p className="text-sm text-[#E8E6DF]/80 leading-relaxed">{summary}</p>
      </motion.div>

      {/* Recommendation */}
      <motion.div
        variants={stagger.item}
        className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] px-5 py-4"
      >
        <div className="flex items-center gap-2 mb-2">
          <Lightbulb size={13} className="text-[#E09C52]" />
          <span className="text-xs font-semibold text-[#E09C52] uppercase tracking-widest">Recommendation</span>
        </div>
        <p className="text-sm text-[#E8E6DF]/80 leading-relaxed">{recommendation}</p>
      </motion.div>

      {/* Key factors */}
      {key_factors?.length > 0 && (
        <motion.div
          variants={stagger.item}
          className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] px-5 py-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 size={13} className="text-[#3CB697]" />
            <span className="text-xs font-semibold text-[#3CB697] uppercase tracking-widest">Key Factors</span>
          </div>
          <ul className="space-y-2">
            {key_factors.map((factor, i) => (
              <motion.li
                key={i}
                variants={stagger.item}
                className="flex items-start gap-2.5 text-sm text-[#E8E6DF]/80"
              >
                <span className="text-[#3CB697] mt-0.5 flex-shrink-0 font-mono text-xs">
                  {String(i + 1).padStart(2, '0')}.
                </span>
                {factor}
              </motion.li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Disclaimer */}
      {limitations_disclaimer && (
        <motion.div
          variants={stagger.item}
          className="flex items-start gap-2 text-xs text-[#7A8099] leading-relaxed px-1"
        >
          <AlertTriangle size={12} className="flex-shrink-0 mt-0.5 text-[#7A8099]" />
          <span>{limitations_disclaimer}</span>
        </motion.div>
      )}
    </motion.div>
  );
}
