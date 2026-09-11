'use client';

import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileDropZoneProps {
  onFile: (file: File) => void;
  file?: File | null;
  onClear?: () => void;
  accept?: string;
  maxMb?: number;
  label?: string;
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
      setError(`File exceeds ${maxMb} MB limit`);
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
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-xl border-2 border-dashed transition-all duration-300 overflow-hidden',
          dragging
            ? 'border-[#3CB697] bg-[#3CB697]/5 shadow-[0_0_30px_rgba(60,182,151,0.15)]'
            : file
            ? 'border-[#3CB697]/40 bg-[#171A22]'
            : 'border-[rgba(60,182,151,0.2)] bg-[#171A22] hover:border-[#3CB697]/40 hover:bg-[#3CB697]/3',
        )}
      >
        <AnimatePresence mode="wait">
          {file ? (
            /* ── File selected ── */
            <motion.div
              key="file"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center gap-4 px-6 py-5"
            >
              <div className="w-10 h-10 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center flex-shrink-0">
                <FileText size={18} className="text-[#3CB697]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#E8E6DF] truncate">{file.name}</p>
                <p className="text-xs text-[#7A8099] mt-0.5">
                  {(file.size / 1024).toFixed(0)} KB · PDF
                </p>
              </div>
              {onClear && (
                <button
                  onClick={onClear}
                  className="p-1.5 rounded-lg hover:bg-[#E05252]/10 text-[#7A8099] hover:text-[#E05252] transition-colors flex-shrink-0"
                  aria-label="Remove file"
                >
                  <X size={14} />
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
              className="flex flex-col items-center justify-center gap-3 py-12 cursor-pointer"
            >
              <motion.div
                animate={dragging ? { scale: 1.15 } : { scale: 1 }}
                transition={{ type: 'spring', stiffness: 300 }}
                className="w-12 h-12 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center"
              >
                <Upload size={20} className="text-[#3CB697]" />
              </motion.div>
              <div className="text-center">
                <p className="text-sm font-medium text-[#E8E6DF]">{label}</p>
                <p className="text-xs text-[#7A8099] mt-1">
                  PDF only · max {maxMb} MB
                </p>
              </div>
              <span className="px-4 py-1.5 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 text-xs text-[#3CB697] font-medium hover:bg-[#3CB697]/20 transition-colors">
                Browse files
              </span>
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
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center gap-2 text-xs text-[#E05252] px-1"
          >
            <AlertCircle size={12} />
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
