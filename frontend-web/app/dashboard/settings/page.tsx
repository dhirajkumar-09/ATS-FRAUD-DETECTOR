'use client';

import { Settings } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import OrgSettingsForm from '@/components/settings/OrgSettingsForm';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-[#3CB697]/10 border border-[#3CB697]/20 flex items-center justify-center">
          <Settings size={18} className="text-[#3CB697]" />
        </div>
        <div>
          <h1
            className="text-xl font-bold text-[#E8E6DF]"
            style={{ fontFamily: 'var(--font-space-grotesk)' }}
          >
            Organization Settings
          </h1>
          <p className="text-xs text-[#7A8099] mt-0.5">
            Configure fraud detection thresholds for your organization
          </p>
        </div>
      </div>

      <div className="glass-card rounded-xl p-6">
        <OrgSettingsForm isAdmin={user?.is_admin ?? false} />
      </div>
    </div>
  );
}
