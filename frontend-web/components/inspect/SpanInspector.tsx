'use client';

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { getSignalColor } from '@/lib/utils';
import type { InspectResult, TextSpan } from '@/lib/types';

interface Props {
  data: InspectResult;
}

// All unique signal types across the document
function collectSignalTypes(data: InspectResult): string[] {
  const set = new Set<string>();
  data.pages.forEach((p) => p.spans.forEach((s) => s.signal_types.forEach((t) => set.add(t))));
  return Array.from(set);
}

function renderSpans(spans: TextSpan[], showFlagged: boolean) {
  return spans.map((span, i) => {
    if (span.is_flagged && showFlagged) {
      const colors = span.signal_types.map(getSignalColor);
      const borderColor = colors[0] ?? '#E05252';
      return (
        <mark
          key={i}
          title={span.signal_types.join(', ')}
          style={{
            backgroundColor: `${borderColor}22`,
            borderBottom: `2px solid ${borderColor}`,
            color: '#E8E6DF',
          }}
          className="rounded-sm px-0.5 cursor-help"
        >
          {span.text}
        </mark>
      );
    }
    return (
      <span key={i} className="text-[#E8E6DF]">
        {span.text}
      </span>
    );
  });
}

export default function SpanInspector({ data }: Props) {
  const signalTypes = useMemo(() => collectSignalTypes(data), [data]);
  const [currentPage, setCurrentPage] = useState(0);
  const [view, setView] = useState<'side-by-side' | 'clean' | 'flagged'>('side-by-side');

  const pageData = data.pages[currentPage];

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* View toggle */}
        <div className="flex p-1 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.12)]">
          {(['side-by-side', 'clean', 'flagged'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                view === v
                  ? 'bg-[#3CB697] text-[#0D0F14]'
                  : 'text-[#7A8099] hover:text-[#E8E6DF]'
              }`}
            >
              {v.replace('-', ' ')}
            </button>
          ))}
        </div>

        {/* Page selector */}
        {data.pages.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#7A8099]">Page</span>
            <div className="flex gap-1">
              {data.pages.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i)}
                  className={`w-7 h-7 rounded-lg text-xs font-mono transition-all ${
                    currentPage === i
                      ? 'bg-[#3CB697] text-[#0D0F14]'
                      : 'bg-[#171A22] text-[#7A8099] hover:text-[#E8E6DF] border border-[rgba(60,182,151,0.12)]'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      {signalTypes.length > 0 && (
        <div className="flex flex-wrap gap-3 px-4 py-3 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.1)]">
          <span className="text-xs text-[#7A8099] mr-1">Signal types:</span>
          {signalTypes.map((t) => (
            <div key={t} className="flex items-center gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: `${getSignalColor(t)}55`, border: `1px solid ${getSignalColor(t)}` }}
              />
              <span className="text-xs text-[#E8E6DF]/70 font-mono">{t.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      )}

      {/* Panels */}
      <motion.div
        key={`${currentPage}-${view}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className={`grid gap-4 ${view === 'side-by-side' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}
      >
        {/* Clean text panel */}
        {(view === 'side-by-side' || view === 'clean') && (
          <div className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] overflow-hidden">
            <div className="px-4 py-2.5 border-b border-[rgba(60,182,151,0.08)] flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-[#3CB697]" />
              <span className="text-xs font-semibold text-[#3CB697] uppercase tracking-widest">
                Clean Text
              </span>
            </div>
            <div className="px-5 py-4 text-sm leading-loose font-mono text-[#E8E6DF]/70 whitespace-pre-wrap break-words max-h-[600px] overflow-y-auto">
              {pageData.spans.map((s) => s.text).join('')}
            </div>
          </div>
        )}

        {/* Flagged text panel */}
        {(view === 'side-by-side' || view === 'flagged') && (
          <div className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.12)] overflow-hidden">
            <div className="px-4 py-2.5 border-b border-[rgba(60,182,151,0.08)] flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-[#E05252]" />
              <span className="text-xs font-semibold text-[#E05252] uppercase tracking-widest">
                Flagged Spans
              </span>
              <span className="ml-auto text-[10px] text-[#7A8099]">
                {pageData.spans.filter((s) => s.is_flagged).length} flagged
              </span>
            </div>
            <div className="px-5 py-4 text-sm leading-loose font-mono whitespace-pre-wrap break-words max-h-[600px] overflow-y-auto">
              {renderSpans(pageData.spans, true)}
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
