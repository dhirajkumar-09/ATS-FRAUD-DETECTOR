'use client';

import { useEffect, useState } from 'react';
import { motion, useMotionValue, animate } from 'framer-motion';
import { getTrustColor } from '@/lib/utils';
import type { TrustLabel } from '@/lib/types';

interface TrustGaugeProps {
  score: number;         // 0 – 1
  label: TrustLabel;
  size?: number;
}

const RADIUS = 56;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
// Only show the top 270° arc (75% of circle)
const ARC_FRACTION = 0.75;

export default function TrustGauge({ score: rawScore, label, size = 160 }: TrustGaugeProps) {
  // Clamp and sanitise — backend sometimes returns 0-100 instead of 0-1
  const score = isNaN(rawScore) || rawScore == null
    ? 0
    : rawScore > 1
    ? rawScore / 100   // handle 0-100 range
    : Math.max(0, Math.min(1, rawScore));
  const color = getTrustColor(label);
  const motionScore = useMotionValue(0);
  const [displayNum, setDisplayNum] = useState(0);

  useEffect(() => {
    const controls = animate(motionScore, score, {
      duration: 1.6,
      ease: 'easeOut',
      onUpdate: (v) => setDisplayNum(Math.round(v * 100)),
    });
    return controls.stop;
  }, [score]); // eslint-disable-line react-hooks/exhaustive-deps

  // Stroke dashoffset: full arc = ARC_FRACTION * CIRCUMFERENCE
  const fullArcLength = ARC_FRACTION * CIRCUMFERENCE;
  const filledLength = score * fullArcLength;
  const offset = fullArcLength - filledLength;

  // Rotation: start at -225deg so arc goes from bottom-left to bottom-right
  const startAngle = -225;

  return (
    <div
      className="flex flex-col items-center gap-3"
      role="meter"
      aria-valuenow={Math.round(score * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Trust score: ${Math.round(score * 100)}%`}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox="0 0 136 136"
          className="overflow-visible"
          style={{ transform: `rotate(${startAngle}deg)` }}
        >
          {/* Track arc */}
          <circle
            cx="68"
            cy="68"
            r={RADIUS}
            fill="none"
            stroke="rgba(60,182,151,0.08)"
            strokeWidth="10"
            strokeDasharray={`${fullArcLength} ${CIRCUMFERENCE}`}
            strokeLinecap="round"
          />

          {/* Filled arc */}
          <motion.circle
            cx="68"
            cy="68"
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={`${fullArcLength} ${CIRCUMFERENCE}`}
            strokeLinecap="round"
            initial={{ strokeDashoffset: fullArcLength }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.6, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 8px ${color}60)` }}
          />
        </svg>

        {/* Center number */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center"
          style={{ transform: `rotate(0deg)` }} // counter-rotate so text is upright
        >
          <span
            className="text-3xl font-bold tabular-nums leading-none"
            style={{ color, fontFamily: 'var(--font-space-grotesk)' }}
          >
            {displayNum}
          </span>
          <span className="text-xs text-[#7A8099] mt-1">/ 100</span>
        </div>
      </div>

      {/* Label */}
      <div
        className="px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase border"
        style={{
          color,
          borderColor: `${color}40`,
          backgroundColor: `${color}12`,
          fontFamily: 'var(--font-space-grotesk)',
        }}
      >
        {label}
      </div>
    </div>
  );
}
