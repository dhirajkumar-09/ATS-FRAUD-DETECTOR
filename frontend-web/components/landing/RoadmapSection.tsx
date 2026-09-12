'use client';

import { motion, type Variants } from 'framer-motion';
import { ShieldCheck, Link2, GitBranch, ExternalLink, Plug2, Workflow, Rocket } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface RoadmapItem {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  accentIcon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  description: string;
  eta: string;
}

const ROADMAP_ITEMS: RoadmapItem[] = [
  {
    icon: ShieldCheck,
    accentIcon: Link2,
    title: 'Blockchain-Anchored Trust Certificate',
    description:
      'Every verified Trust Score gets cryptographically timestamped and anchored on-chain — giving candidates a tamper-proof credential employers can audit independently, forever.',
    eta: 'Q3 2026',
  },
  {
    icon: GitBranch,
    accentIcon: ExternalLink,
    title: 'LinkedIn & GitHub Live Cross-Verification',
    description:
      "Automatically validate claimed work history and open-source contributions against a candidate's public profiles in real time — no manual reference checks required.",
    eta: 'Q4 2026',
  },
  {
    icon: Plug2,
    accentIcon: Workflow,
    title: 'Native ATS Plugin Integration',
    description:
      'Forensic scanning embedded directly into Greenhouse, Workday, and Lever — every new application triggers an automatic fraud check before a recruiter even sees it.',
    eta: '2027',
  },
];

const containerVariants: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.14, delayChildren: 0.05 },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.52, ease: [0.22, 1, 0.36, 1] },
  },
};

const headingVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
};


function RoadmapCard({ item, index }: { item: RoadmapItem; index: number }) {
  const Icon = item.icon;
  const AccentIcon = item.accentIcon;

  return (
    <motion.div
      variants={cardVariants}
      whileHover={{ y: -4, transition: { type: 'spring', damping: 22, stiffness: 260 } }}
      className={cn(
        'relative flex flex-col gap-5 p-6 rounded-2xl overflow-hidden',
        'border border-dashed border-[rgba(60,182,151,0.22)]',
        'bg-[#131620]/60 backdrop-blur-sm',
        'group cursor-default',
        'transition-[box-shadow,border-color] duration-300',
        'hover:border-[rgba(60,182,151,0.45)]',
        'hover:shadow-[0_0_0_1px_rgba(60,182,151,0.12),0_8px_32px_rgba(0,0,0,0.45),0_0_24px_rgba(60,182,151,0.10)]',
      )}
    >
      {/* Radial hover glow */}
      <div
        className='pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500'
        style={{ background: 'radial-gradient(circle, rgba(60,182,151,0.10) 0%, transparent 70%)' }}
        aria-hidden
      />

      {/* Icon cluster */}
      <div className='flex items-start justify-between'>
        <div className='relative flex-shrink-0'>
          <div
            className='w-11 h-11 rounded-xl flex items-center justify-center'
            style={{ background: 'rgba(60,182,151,0.08)', border: '1px solid rgba(60,182,151,0.18)' }}
          >
            <Icon size={20} className='text-[#3CB697] opacity-80' />
          </div>
          <div
            className='absolute -bottom-1.5 -right-1.5 w-5 h-5 rounded-lg flex items-center justify-center'
            style={{ background: '#131620', border: '1px solid rgba(60,182,151,0.20)' }}
          >
            <AccentIcon size={10} className='text-[#3CB697] opacity-60' />
          </div>
        </div>

        <Badge
          variant='outline'
          className='text-[10px] font-semibold tracking-[0.08em] uppercase shrink-0 border-[rgba(60,182,151,0.25)] text-[#8A90A4] bg-[rgba(60,182,151,0.04)] group-hover:border-[rgba(60,182,151,0.40)] group-hover:text-[#3CB697] transition-colors duration-300'
        >
          On the Roadmap
        </Badge>
      </div>

      {/* Text */}
      <div className='flex flex-col gap-2 flex-1'>
        <h3
          className='text-base font-semibold text-[#E8E6DF] leading-snug'
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          {item.title}
        </h3>
        <p className='text-sm text-[#8A90A4] leading-relaxed'>{item.description}</p>
      </div>

      {/* ETA footer */}
      <div className='flex items-center gap-1.5 mt-auto pt-4 border-t border-dashed border-[rgba(60,182,151,0.10)]'>
        <div className='w-1 h-1 rounded-full bg-[#8A90A4]/40' />
        <span
          className='text-[11px] font-mono text-[#8A90A4]/60 tracking-wider'
          style={{ fontFamily: 'var(--font-jetbrains-mono)' }}
        >
          Target: {item.eta}
        </span>
      </div>

      {/* Ghost corner number */}
      <span
        className='absolute bottom-4 right-5 text-[48px] font-black leading-none select-none pointer-events-none'
        style={{ fontFamily: 'var(--font-space-grotesk)', color: 'rgba(60,182,151,0.04)' }}
        aria-hidden
      >
        {String(index + 1).padStart(2, '0')}
      </span>
    </motion.div>
  );
}

export default function RoadmapSection() {
  return (
    <section
      id='roadmap'
      className='relative w-full py-24 px-4 sm:px-6 overflow-hidden scroll-mt-12'
      aria-label='Product roadmap — upcoming features'
    >
      {/* Top rule glow */}
      <div
        className='pointer-events-none absolute inset-x-0 top-0 h-px'
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, rgba(60,182,151,0.18) 30%, rgba(60,182,151,0.28) 50%, rgba(60,182,151,0.18) 70%, transparent 100%)',
        }}
        aria-hidden
      />
      {/* Soft radial bloom */}
      <div
        className='pointer-events-none absolute inset-x-0 top-0 h-64'
        style={{
          background:
            'radial-gradient(ellipse 60% 100% at 50% 0%, rgba(60,182,151,0.05) 0%, transparent 100%)',
        }}
        aria-hidden
      />

      <div className='relative max-w-5xl mx-auto'>
        {/* Heading */}
        <motion.div
          variants={headingVariants}
          initial='hidden'
          whileInView='show'
          viewport={{ once: true, margin: '-60px' }}
          className='text-center mb-14'
        >
          <div className='inline-flex items-center gap-2 mb-4 px-3 py-1.5 rounded-full border border-dashed border-[rgba(60,182,151,0.25)] bg-[rgba(60,182,151,0.04)]'>
            <Rocket size={11} className='text-[#3CB697] opacity-75' />
            <span
              className='text-[11px] font-semibold text-[#8A90A4] uppercase tracking-[0.14em]'
              style={{ fontFamily: 'var(--font-jetbrains-mono)' }}
            >
              Beyond the Hackathon
            </span>
          </div>

          <h2
            className='text-3xl sm:text-4xl font-bold tracking-tight mb-3'
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            <span className='text-[#E8E6DF]'>What&apos;s </span>
            <span className='gradient-text'>Next</span>
          </h2>

          <p className='text-sm text-[#8A90A4] max-w-md mx-auto leading-relaxed'>
            Features on our roadmap beyond this hackathon — a glimpse of where the forensic engine goes next.
          </p>
        </motion.div>

        {/* Cards grid */}
        <motion.div
          variants={containerVariants}
          initial='hidden'
          whileInView='show'
          viewport={{ once: true, margin: '-40px' }}
          className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5'
        >
          {ROADMAP_ITEMS.map((item, i) => (
            <RoadmapCard key={item.title} item={item} index={i} />
          ))}
        </motion.div>

        {/* Honest disclaimer */}
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className='text-center text-[11px] text-[#8A90A4]/50 mt-10 tracking-wide'
          style={{ fontFamily: 'var(--font-jetbrains-mono)' }}
        >
          These features are planned future work — no backend implementation exists yet.
        </motion.p>
      </div>
    </section>
  );
}
