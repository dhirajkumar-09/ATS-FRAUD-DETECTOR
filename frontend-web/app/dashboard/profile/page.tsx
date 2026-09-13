'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Building2, Mail, Lock, Eye, EyeOff, Save, Shield, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { getMe } from '@/lib/api/auth';
import apiClient from '@/lib/api/client';
import { toast } from 'sonner';

// ── Password change form ──────────────────────────────────────────────────────
function PasswordSection() {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [show, setShow] = useState({ current: false, next: false, confirm: false });
  const [loading, setLoading] = useState(false);

  const toggle = (field: keyof typeof show) =>
    setShow((s) => ({ ...s, [field]: !s[field] }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.next !== form.confirm) {
      toast.error('New passwords do not match');
      return;
    }
    if (form.next.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await apiClient.put('/auth/change-password', {
        current_password: form.current,
        new_password: form.next,
      });
      toast.success('Password updated successfully');
      setForm({ current: '', next: '', confirm: '' });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  const PasswordField = ({
    label,
    field,
    value,
  }: {
    label: string;
    field: keyof typeof show;
    value: string;
  }) => (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-[#8A90A4] uppercase tracking-wider">{label}</label>
      <div className="relative">
        <input
          type={show[field] ? 'text' : 'password'}
          value={value}
          onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
          className="w-full bg-[#0D0F14] border border-[rgba(60,182,151,0.15)] rounded-xl px-4 py-2.5 pr-10 text-sm text-[#E8E6DF] placeholder-[#4A5066] focus:outline-none focus:border-[#3CB697]/50 focus:ring-1 focus:ring-[#3CB697]/20 transition-colors"
          placeholder="••••••••"
          autoComplete="off"
          required
        />
        <button
          type="button"
          onClick={() => toggle(field)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7A8099] hover:text-[#3CB697] transition-colors"
        >
          {show[field] ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PasswordField label="Current Password" field="current" value={form.current} />
      <PasswordField label="New Password" field="next" value={form.next} />
      <PasswordField label="Confirm New Password" field="confirm" value={form.confirm} />

      {/* Strength hint */}
      {form.next.length > 0 && (
        <div className="flex items-center gap-2 text-xs">
          {form.next.length >= 8 ? (
            <><CheckCircle2 size={12} className="text-[#3CB697]" /><span className="text-[#3CB697]">Good length</span></>
          ) : (
            <><AlertCircle size={12} className="text-[#E05252]" /><span className="text-[#E05252]">Min 8 characters</span></>
          )}
        </div>
      )}

      <motion.button
        type="submit"
        disabled={loading || !form.current || !form.next || !form.confirm}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697] text-[#0D0F14] text-sm font-semibold transition-all hover:bg-[#3CB697]/90 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Save size={14} />
        {loading ? 'Updating…' : 'Update Password'}
      </motion.button>
    </form>
  );
}

// ── Main Profile Page ─────────────────────────────────────────────────────────
export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const setAuth = useAuthStore((s) => s.setAuth);
  const token = useAuthStore((s) => s.token);

  const [nameForm, setNameForm] = useState({ full_name: user?.full_name ?? '' });
  const [nameLoading, setNameLoading] = useState(false);

  // Keep form in sync when auth store hydrates or user updates
  useEffect(() => {
    if (user) {
      setNameForm({ full_name: user.full_name ?? '' });
    }
  }, [user]);

  const handleNameUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setNameLoading(true);
    try {
      await apiClient.put('/auth/me', { full_name: nameForm.full_name });
      // Refresh user from server
      const fresh = await getMe();
      if (token) setAuth(token, fresh);
      toast.success('Profile updated successfully');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to update profile');
    } finally {
      setNameLoading(false);
    }
  };

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? '?';

  const cardClass = 'glass-card rounded-2xl p-6 space-y-5';
  const sectionTitle = (text: string, icon: React.ReactNode) => (
    <div className="flex items-center gap-2.5 pb-4 border-b border-[rgba(60,182,151,0.08)]">
      <div className="w-7 h-7 rounded-lg bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
        {icon}
      </div>
      <h2 className="text-sm font-semibold text-[#E8E6DF]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
        {text}
      </h2>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center gap-4"
      >
        {/* Avatar */}
        <div className="w-14 h-14 rounded-2xl bg-[#3CB697]/15 border border-[#3CB697]/25 flex items-center justify-center text-xl font-bold text-[#3CB697]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
          {initials}
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#E8E6DF]" style={{ fontFamily: 'var(--font-space-grotesk)' }}>
            {user?.full_name ?? 'Your Profile'}
          </h1>
          <p className="text-xs text-[#7A8099] mt-0.5">{user?.email}</p>
          {user?.is_admin && (
            <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-semibold text-[#3CB697] bg-[#3CB697]/10 border border-[#3CB697]/20 rounded-full px-2 py-0.5">
              <Shield size={9} /> Organization Admin
            </span>
          )}
        </div>
      </motion.div>

      {/* Account Info (read-only) */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05 }}
        className={cardClass}
      >
        {sectionTitle('Account Information', <User size={13} className="text-[#3CB697]" />)}

        <div className="space-y-4">
          {/* Email (read-only) */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#8A90A4] uppercase tracking-wider flex items-center gap-1.5">
              <Mail size={10} /> Email
            </label>
            <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#0D0F14]/60 border border-[rgba(60,182,151,0.10)] text-sm text-[#8A90A4]">
              {user?.email}
              <span className="ml-auto text-[10px] font-mono text-[#4A5066] bg-[#171A22] px-2 py-0.5 rounded-md">read-only</span>
            </div>
          </div>

          {/* Organization (read-only) */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#8A90A4] uppercase tracking-wider flex items-center gap-1.5">
              <Building2 size={10} /> Organization
            </label>
            <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#0D0F14]/60 border border-[rgba(60,182,151,0.10)] text-sm text-[#8A90A4]">
              {user?.organization}
              <span className="ml-auto text-[10px] font-mono text-[#4A5066] bg-[#171A22] px-2 py-0.5 rounded-md">read-only</span>
            </div>
          </div>
        </div>

        {/* Update display name */}
        <form onSubmit={handleNameUpdate} className="space-y-4 pt-2 border-t border-[rgba(60,182,151,0.06)]">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#8A90A4] uppercase tracking-wider">Display Name</label>
            <input
              type="text"
              value={nameForm.full_name}
              onChange={(e) => setNameForm({ full_name: e.target.value })}
              placeholder="Your full name"
              className="w-full bg-[#0D0F14] border border-[rgba(60,182,151,0.15)] rounded-xl px-4 py-2.5 text-sm text-[#E8E6DF] placeholder-[#4A5066] focus:outline-none focus:border-[#3CB697]/50 focus:ring-1 focus:ring-[#3CB697]/20 transition-colors"
            />
          </div>
          <motion.button
            type="submit"
            disabled={nameLoading || nameForm.full_name === (user?.full_name ?? '')}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#3CB697] text-[#0D0F14] text-sm font-semibold transition-all hover:bg-[#3CB697]/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Save size={14} />
            {nameLoading ? 'Saving…' : 'Save Name'}
          </motion.button>
        </form>
      </motion.div>

      {/* Change Password */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className={cardClass}
      >
        {sectionTitle('Change Password', <Lock size={13} className="text-[#3CB697]" />)}
        <PasswordSection />
      </motion.div>
    </div>
  );
}
