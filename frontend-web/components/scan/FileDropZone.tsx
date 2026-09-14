'use client';

import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileDropZoneProps {
  onFile: (file: File) => void;
  file?: File | null;
  onClear?: () => void;
  accept?: string;
  maxMb?: number;
  label?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileDropZone({
  onFile,
  file,
  onClear,
  accept = '.pdf',
  maxMb = 10,
  label = 'Drop your resume PDF here',
}: FileDropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (f: File): boolean => {
    if (f.size > maxMb * 1024 * 1024) {
      setError(`File is too large (${formatBytes(f.size)} — max ${maxMb} MB)`);
      return false;
    }
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported');
      return false;
    }
    setError(null);
    return true;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const dropped = e.dataTransfer.files[0];
      if (dropped && validate(dropped)) onFile(dropped);
    },
    [onFile], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && validate(selected)) onFile(selected);
    e.target.value = '';
  };

  return (
    <div className="space-y-2">
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        animate={
          dragging
            ? {
                borderColor: '#3CB697',
                backgroundColor: 'rgba(60, 182, 151, 0.07)',
                boxShadow:
                  '0 0 32px rgba(60,182,151,0.24), inset 0 0 24px rgba(60,182,151,0.06)',
                scale: 1.008,
              }
            : file
            ? {
                borderColor: 'rgba(60, 182, 151, 0.35)',
                backgroundColor: '#131620',
                boxShadow: '0 0 0px rgba(60,182,151,0)',
                scale: 1,
              }
            : {
                borderColor: [
                  'rgba(60, 182, 151, 0.16)',
                  'rgba(60, 182, 151, 0.32)',
                  'rgba(60, 182, 151, 0.16)',
                ],
                boxShadow: [
                  '0 0 0px rgba(60,182,151,0)',
                  '0 0 20px rgba(60,182,151,0.06)',
                  '0 0 0px rgba(60,182,151,0)',
                ],
                scale: 1,
              }
        }
        transition={
          dragging
            ? { type: 'spring', damping: 20, stiffness: 300 }
            : file
            ? { duration: 0.3 }
            : {
                duration: 4.5,
                repeat: Infinity,
                ease: 'easeInOut',
              }
        }
        className="relative rounded-2xl border-2 border-dashed transition-colors duration-300 overflow-hidden bg-[#131620]"
      >
        <AnimatePresence mode="wait">
          {file ? (
            /* ── File selected state with spring entrance ── */
            <motion.div
              key="file"
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -8 }}
              transition={{ type: 'spring', damping: 22, stiffness: 280 }}
              className="flex items-center gap-4 px-5 py-4"
            >
              <div className="w-11 h-11 rounded-xl bg-[#3CB697]/12 border border-[#3CB697]/25 flex items-center justify-center flex-shrink-0 shadow-[0_0_16px_rgba(60,182,151,0.15)]">
                <FileText size={19} className="text-[#3CB697]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[#E8E6DF] truncate">{file.name}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-xs text-[#8A90A4]">{formatBytes(file.size)}</span>
                  <span className="text-[#8A90A4]/40 text-xs">·</span>
                  <span className="text-xs text-[#8A90A4] uppercase tracking-wide font-mono">PDF</span>
                  <span className="text-[#8A90A4]/40 text-xs">·</span>
                  <span className="text-[11px] font-medium text-[#3CB697] bg-[#3CB697]/10 px-2 py-0.5 rounded-full border border-[#3CB697]/20">
                    Attached — Click &ldquo;Run Forensic Scan&rdquo; below
                  </span>
                </div>
              </div>
              {onClear && (
                <button
                  onClick={onClear}
                  className="p-1.5 rounded-lg hover:bg-[#E05252]/15 text-[#8A90A4] hover:text-[#E05252] transition-colors flex-shrink-0"
                  aria-label="Remove file"
                >
                  <X size={15} />
                </button>
              )}
            </motion.div>
          ) : (
            /* ── Drop area ── */
            <motion.label
              key="drop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center gap-4 py-14 cursor-pointer select-none"
            >
              {/* Icon with enhanced drag animation */}
              <motion.div
                animate={
                  dragging
                    ? { scale: 1.22, y: -6 }
                    : { scale: 1, y: 0 }
                }
                transition={{ type: 'spring', stiffness: 340, damping: 20 }}
                className={cn(
                  'w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300',
                  dragging
                    ? 'bg-[#3CB697]/25 border-2 border-[#3CB697] shadow-[0_0_24px_rgba(60,182,151,0.4)]'
                    : 'bg-[#1E2230] border border-[rgba(60,182,151,0.2)] shadow-[0_0_16px_rgba(60,182,151,0.05)]',
                )}
              >
                <Upload
                  size={22}
                  className={cn(
                    'transition-colors',
                    dragging ? 'text-[#3CB697]' : 'text-[#8A90A4]',
                  )}
                />
              </motion.div>

              {/* Text */}
              <div className="text-center px-4">
                <p className="text-sm font-semibold text-[#E8E6DF]">
                  {dragging ? 'Release to upload resume' : label}
                </p>
                <p className="text-xs text-[#8A90A4] mt-1">
                  {dragging ? (
                    <span className="text-[#3CB697] font-medium">Drop it here for forensic analysis!</span>
                  ) : (
                    <>Drag & drop or click to browse · PDF only · max {maxMb} MB</>
                  )}
                </p>
              </div>

              {/* Browse button */}
              {!dragging && (
                <span className="px-4 py-1.5 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/25 text-xs text-[#3CB697] font-semibold hover:bg-[#3CB697]/20 hover:border-[#3CB697]/40 transition-all shadow-[0_0_12px_rgba(60,182,151,0.08)]">
                  Browse files
                </span>
              )}

              <input
                type="file"
                accept={accept}
                onChange={handleChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
                aria-label="Upload PDF file"
              />
            </motion.label>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-xs text-[#E05252] px-1 pt-0.5"
          >
            <AlertCircle size={12} className="flex-shrink-0" />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
