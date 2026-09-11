'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Save, Loader2, Lock, Shield } from 'lucide-react';
import { getOrgSettings, updateOrgSettings } from '@/lib/api/auth';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { OrgSettingsOut } from '@/lib/types';

const schema = z.object({
  near_white_threshold: z
    .union([z.literal(''), z.coerce.number().int().min(200).max(255)])
    .nullable()
    .optional(),
  hidden_font_size_pt: z
    .union([z.literal(''), z.coerce.number().min(0).max(72)])
    .nullable()
    .optional(),
});

type FormData = z.infer<typeof schema>;

interface Props {
  isAdmin: boolean;
}

export default function OrgSettingsForm({ isAdmin }: Props) {
  const [settings, setSettings] = useState<OrgSettingsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  useEffect(() => {
    getOrgSettings()
      .then((s) => {
        setSettings(s);
        reset({
          near_white_threshold: s.near_white_threshold ?? '',
          hidden_font_size_pt: s.hidden_font_size_pt ?? '',
        });
      })
      .catch(() => toast.error('Failed to load org settings'))
      .finally(() => setLoading(false));
  }, [reset]);

  const onSubmit = async (data: FormData) => {
    setSaving(true);
    try {
      const updated = await updateOrgSettings({
        near_white_threshold: data.near_white_threshold
          ? Number(data.near_white_threshold)
          : null,
        hidden_font_size_pt: data.hidden_font_size_pt
          ? Number(data.hidden_font_size_pt)
          : null,
      });
      setSettings(updated);
      reset({
        near_white_threshold: updated.near_white_threshold ?? '',
        hidden_font_size_pt: updated.hidden_font_size_pt ?? '',
      });
      toast.success('Org settings saved');
    } catch {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full bg-[#1E2230] rounded-xl" />
        <Skeleton className="h-16 w-full bg-[#1E2230] rounded-xl" />
      </div>
    );
  }

  const inputClass = (hasError?: boolean) =>
    cn(
      'w-full px-4 py-2.5 rounded-lg text-sm bg-[#0D0F14] border text-[#E8E6DF]',
      'placeholder:text-[#7A8099] outline-none transition-all duration-200 font-mono',
      'focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/20',
      hasError ? 'border-[#E05252]' : 'border-[rgba(60,182,151,0.2)]',
      !isAdmin && 'cursor-not-allowed opacity-60',
    );

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* Org info */}
      <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[#3CB697]/5 border border-[#3CB697]/15">
        <Shield size={13} className="text-[#3CB697]" />
        <span className="text-xs text-[#3CB697]">
          Organization: <strong>{settings?.organization}</strong>
        </span>
      </div>

      {/* Non-admin notice */}
      {!isAdmin && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[#E09C52]/5 border border-[#E09C52]/15">
          <Lock size={13} className="text-[#E09C52]" />
          <span className="text-xs text-[#E09C52]">
            You have read-only access. Contact your organization admin to modify settings.
          </span>
        </div>
      )}

      {/* near_white_threshold */}
      <div className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.1)] overflow-hidden">
        <div className="px-5 py-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <label className="text-sm font-medium text-[#E8E6DF]" htmlFor="nw-threshold">
                Near-White Text Threshold
              </label>
              <p className="text-xs text-[#7A8099] mt-1">
                RGB brightness value (0–255) above which text is considered &quot;near-white&quot; and flagged.
                Default: 240. Higher = more sensitive.
              </p>
            </div>
            {settings?.near_white_threshold != null && (
              <span className="text-xs font-mono text-[#3CB697] bg-[#3CB697]/10 px-2 py-1 rounded-lg">
                Current: {settings.near_white_threshold}
              </span>
            )}
          </div>
          <input
            id="nw-threshold"
            type="number"
            min={200}
            max={255}
            step={1}
            placeholder="e.g. 240 (leave blank to use app default)"
            disabled={!isAdmin}
            {...register('near_white_threshold')}
            className={inputClass(!!errors.near_white_threshold)}
          />
          {errors.near_white_threshold && (
            <p className="text-xs text-[#E05252] mt-1">
              {errors.near_white_threshold.message as string}
            </p>
          )}
        </div>
      </div>

      {/* hidden_font_size_pt */}
      <div className="rounded-xl bg-[#171A22] border border-[rgba(60,182,151,0.1)] overflow-hidden">
        <div className="px-5 py-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <label className="text-sm font-medium text-[#E8E6DF]" htmlFor="font-size">
                Hidden Font Size Threshold (pt)
              </label>
              <p className="text-xs text-[#7A8099] mt-1">
                Font sizes at or below this value are flagged as potentially hidden.
                Default: 1.0 pt. Lower = stricter.
              </p>
            </div>
            {settings?.hidden_font_size_pt != null && (
              <span className="text-xs font-mono text-[#3CB697] bg-[#3CB697]/10 px-2 py-1 rounded-lg">
                Current: {settings.hidden_font_size_pt} pt
              </span>
            )}
          </div>
          <input
            id="font-size"
            type="number"
            min={0}
            max={72}
            step={0.1}
            placeholder="e.g. 1.0 (leave blank to use app default)"
            disabled={!isAdmin}
            {...register('hidden_font_size_pt')}
            className={inputClass(!!errors.hidden_font_size_pt)}
          />
          {errors.hidden_font_size_pt && (
            <p className="text-xs text-[#E05252] mt-1">
              {errors.hidden_font_size_pt.message as string}
            </p>
          )}
        </div>
      </div>

      {/* Save button (admin only) */}
      {isAdmin && (
        <motion.button
          type="submit"
          disabled={saving || !isDirty}
          whileHover={{ scale: saving || !isDirty ? 1 : 1.01 }}
          whileTap={{ scale: saving || !isDirty ? 1 : 0.98 }}
          className={cn(
            'w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all duration-200',
            'bg-[#3CB697] text-[#0D0F14] hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.3)]',
            'disabled:opacity-40 disabled:cursor-not-allowed',
          )}
          style={{ fontFamily: 'var(--font-space-grotesk)' }}
        >
          {saving ? (
            <><Loader2 size={15} className="animate-spin" /> Saving…</>
          ) : (
            <><Save size={15} /> Save Settings</>
          )}
        </motion.button>
      )}
    </form>
  );
}
