'use client';

import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, X, Plus, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BatchDropZoneProps {
  files: File[];
  onAdd: (files: File[]) => void;
  onRemove: (index: number) => void;
  maxFiles?: number;
  maxMb?: number;
}

export default function BatchDropZone({
  files,
  onAdd,
  onRemove,
  maxFiles = 20,
  maxMb = 10,
}: BatchDropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (incoming: File[]): File[] => {
    const valid: File[] = [];
    for (const f of incoming) {
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        setError('Only PDF files are supported');
        continue;
      }
      if (f.size > maxMb * 1024 * 1024) {
        setError(`"${f.name}" exceeds ${maxMb} MB limit`);
        continue;
      }
      if (files.length + valid.length >= maxFiles) {
        setError(`Maximum ${maxFiles} files allowed`);
        break;
      }
      valid.push(f);
    }
    if (valid.length > 0) setError(null);
    return valid;
  };

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragging(false);
      const dropped = Array.from(e.dataTransfer.files);
      const valid = validate(dropped);
      if (valid.length) onAdd(valid);
    },
    [files, onAdd], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    const valid = validate(selected);
    if (valid.length) onAdd(valid);
    e.target.value = '';
  };

  return (
    <div className="space-y-3">
      {/* Drop area */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          'relative rounded-xl border-2 border-dashed transition-all duration-300',
          'flex flex-col items-center justify-center gap-3 py-8',
          dragging
            ? 'border-[#3CB697] bg-[#3CB697]/5 shadow-[0_0_30px_rgba(60,182,151,0.15)]'
            : 'border-[rgba(60,182,151,0.2)] bg-[#171A22] hover:border-[#3CB697]/40',
        )}
      >
        <div className="w-12 h-12 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <Upload size={20} className="text-[#3CB697]" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-[#E8E6DF]">
            {files.length > 0 ? 'Add more resumes' : 'Drop multiple PDF resumes here'}
          </p>
          <p className="text-xs text-[#7A8099] mt-1">
            PDF only · max {maxMb} MB each · up to {maxFiles} files
          </p>
        </div>
        <span className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 text-xs text-[#3CB697] font-medium hover:bg-[#3CB697]/20 transition-colors cursor-pointer">
          <Plus size={12} />
          Select files
        </span>
        <input
          type="file"
          multiple
          accept=".pdf"
          onChange={handleChange}
          className="absolute inset-0 opacity-0 cursor-pointer"
          aria-label="Upload multiple PDF files"
        />
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

      {/* File list */}
      <AnimatePresence>
        {files.map((f, i) => (
          <motion.div
            key={`${f.name}-${i}`}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12, height: 0 }}
            transition={{ duration: 0.2, delay: i * 0.03 }}
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-[#171A22] border border-[rgba(60,182,151,0.1)]"
          >
            <div className="w-7 h-7 rounded bg-[#3CB697]/10 flex items-center justify-center flex-shrink-0">
              <FileText size={13} className="text-[#3CB697]" />
            </div>
            <span className="flex-1 text-sm text-[#E8E6DF] truncate">{f.name}</span>
            <span className="text-xs text-[#7A8099] font-mono flex-shrink-0">
              {(f.size / 1024).toFixed(0)} KB
            </span>
            <button
              onClick={() => onRemove(i)}
              className="p-1 rounded hover:bg-[#E05252]/10 text-[#7A8099] hover:text-[#E05252] transition-colors"
              aria-label={`Remove ${f.name}`}
            >
              <X size={13} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
