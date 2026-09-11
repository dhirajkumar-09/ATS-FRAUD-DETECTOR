'use client';

import { motion } from 'framer-motion';
import { Search, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function InspectIndexPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 flex flex-col items-center justify-center min-h-[60vh] text-center gap-5">
      <div className="w-16 h-16 rounded-2xl bg-[#171A22] border border-[rgba(60,182,151,0.15)] flex items-center justify-center">
        <Search size={24} className="text-[#7A8099]" />
      </div>
      <div>
        <h2
          className="text-xl font-bold text-[#E8E6DF] mb-2"
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          Span Inspector
        </h2>
        <p className="text-sm text-[#7A8099] leading-relaxed max-w-sm">
          Navigate to this page from a scan result to inspect flagged text spans.
          The inspector shows clean vs flagged text side-by-side per page.
        </p>
      </div>
      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
        <Link
          href="/dashboard/scan"
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 text-sm font-medium text-[#3CB697] hover:bg-[#3CB697]/20 transition-colors"
        >
          Go to Scanner
          <ArrowRight size={14} />
        </Link>
      </motion.div>
    </div>
  );
}
