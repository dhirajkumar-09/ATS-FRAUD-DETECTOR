'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Eye, EyeOff, UserPlus, Loader2 } from 'lucide-react';
import { register as registerUser, getMeWithToken } from '@/lib/api/auth';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

const schema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Enter a valid email address'),
  organization: z.string().min(1, 'Organization name is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type FormData = z.infer<typeof schema>;

const inputClass = (hasError: boolean) =>
  cn(
    'w-full px-4 py-2.5 rounded-lg text-sm bg-[#0D0F14] border text-[#E8E6DF]',
    'placeholder:text-[#7A8099] outline-none transition-all duration-200',
    'focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/20',
    hasError ? 'border-[#E05252]' : 'border-[rgba(60,182,151,0.2)]',
  );

export default function RegisterForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      const tokenRes = await registerUser(data);
      const user = await getMeWithToken(tokenRes.access_token);
      setAuth(tokenRes.access_token, user);
      toast.success('Account created! Welcome to ATS Fraud Detector.');
      router.push('/dashboard/scan');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Registration failed. Please try again.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.form
      onSubmit={handleSubmit(onSubmit)}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.3 }}
      className="space-y-4"
    >
      {/* Full Name */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="reg-name">
          Full name
        </label>
        <input
          id="reg-name"
          type="text"
          autoComplete="name"
          placeholder="Jane Smith"
          {...register('full_name')}
          className={inputClass(!!errors.full_name)}
        />
        {errors.full_name && (
          <p className="text-xs text-[#E05252]">{errors.full_name.message}</p>
        )}
      </div>

      {/* Email */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="reg-email">
          Email address
        </label>
        <input
          id="reg-email"
          type="email"
          autoComplete="email"
          placeholder="recruiter@company.com"
          {...register('email')}
          className={inputClass(!!errors.email)}
        />
        {errors.email && (
          <p className="text-xs text-[#E05252]">{errors.email.message}</p>
        )}
      </div>

      {/* Organization */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="reg-org">
          Organization
        </label>
        <input
          id="reg-org"
          type="text"
          autoComplete="organization"
          placeholder="Acme Corp"
          {...register('organization')}
          className={inputClass(!!errors.organization)}
        />
        {errors.organization && (
          <p className="text-xs text-[#E05252]">{errors.organization.message}</p>
        )}
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="reg-password">
          Password
        </label>
        <div className="relative">
          <input
            id="reg-password"
            type={showPass ? 'text' : 'password'}
            autoComplete="new-password"
            placeholder="Min. 8 characters"
            {...register('password')}
            className={inputClass(!!errors.password)}
          />
          <button
            type="button"
            onClick={() => setShowPass((p) => !p)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7A8099] hover:text-[#3CB697] transition-colors"
            aria-label={showPass ? 'Hide password' : 'Show password'}
          >
            {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        {errors.password && (
          <p className="text-xs text-[#E05252]">{errors.password.message}</p>
        )}
      </div>

      <p className="text-xs text-[#7A8099]">
        The first person to register for an organization is automatically granted admin access.
      </p>

      {/* Submit */}
      <motion.button
        type="submit"
        disabled={loading}
        whileHover={{ scale: loading ? 1 : 1.01 }}
        whileTap={{ scale: loading ? 1 : 0.98 }}
        className={cn(
          'w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold',
          'bg-[#3CB697] text-[#0D0F14] transition-all duration-200',
          'hover:bg-[#3CB697]/90 hover:shadow-[0_0_20px_rgba(60,182,151,0.35)]',
          'disabled:opacity-60 disabled:cursor-not-allowed',
          'font-[family-name:var(--font-space-grotesk)]',
        )}
      >
        {loading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : (
          <UserPlus size={16} />
        )}
        {loading ? 'Creating account…' : 'Create Account'}
      </motion.button>
    </motion.form>
  );
}
