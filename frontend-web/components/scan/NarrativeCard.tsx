'use client';

import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { FileText, CheckCircle2, AlertTriangle, Lightbulb, Info } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Narrative } from '@/lib/types';

interface Props {
  narrative: Narrative;
}

const containerVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.08 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

function Section({
  icon: Icon,
  label,
  iconColor,
  children,
}: {
  icon: LucideIcon;
  label: string;
  iconColor: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      variants={itemVariants}
      className="rounded-xl bg-[#131620] border border-[rgba(60,182,151,0.10)] overflow-hidden"
    >

      <div
        className="flex items-center gap-2.5 px-4 py-3 border-b border-[rgba(60,182,151,0.07)]"
        style={{ backgroundColor: `${iconColor}06` }}
      >
        <Icon size={13} style={{ color: iconColor }} />
        <span
          className="text-[10px] font-bold uppercase tracking-[0.14em]"
          style={{ color: iconColor }}
        >
          {label}
        </span>
      </div>
      <div className="px-4 py-3.5">
        {children}
      </div>
    </motion.div>
  );
}

export default function NarrativeCard({ narrative }: Props) {
  const { verdict_title, recommendation, summary, key_factors, limitations_disclaimer } = narrative;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-3"
    >
      {/* Verdict heading */}
      <motion.div variants={itemVariants} className="flex items-start gap-3 px-1 pb-2">
        <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center flex-shrink-0 mt-0.5">
          <FileText size={15} className="text-[#3CB697]" />
        </div>
        <div>
          <p className="text-[10px] text-[#8A90A4] font-mono uppercase tracking-[0.14em] mb-1">Verdict</p>
          <h3
            className="text-lg font-bold text-[#E8E6DF] leading-snug"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            {verdict_title}
          </h3>
        </div>
      </motion.div>

      {/* Summary */}
      <Section icon={Info} label="Summary" iconColor="#3CB697">
        <p className="text-sm text-[#E8E6DF]/80 leading-relaxed">{summary}</p>
      </Section>

      {/* Recommendation */}
      <Section icon={Lightbulb} label="Recommendation" iconColor="#E09C52">
        <p className="text-sm text-[#E8E6DF]/80 leading-relaxed">{recommendation}</p>
      </Section>

      {/* Key factors */}
      {key_factors?.length > 0 && (
        <Section icon={CheckCircle2} label="Key Factors" iconColor="#3CB697">
          <ul className="space-y-2">
            {key_factors.map((factor, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center text-[10px] font-bold text-[#3CB697] font-mono mt-0.5">
                  {i + 1}
                </span>
                <span className="text-sm text-[#E8E6DF]/80 leading-relaxed">{factor}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Disclaimer */}
      {limitations_disclaimer && (
        <motion.div
          variants={itemVariants}
          className="flex items-start gap-2.5 text-xs text-[#8A90A4] leading-relaxed px-1 pt-1"
        >
          <AlertTriangle size={11} className="flex-shrink-0 mt-0.5 text-[#8A90A4]/60" />
          <span>{limitations_disclaimer}</span>
        </motion.div>
      )}
    </motion.div>
  );
}

