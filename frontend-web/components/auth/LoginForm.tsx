'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { Eye, EyeOff, LogIn, Loader2 } from 'lucide-react';
import { login, getMeWithToken } from '@/lib/api/auth';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type FormData = z.infer<typeof schema>;

export default function LoginForm() {
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
      const tokenRes = await login(data.email, data.password);
      const user = await getMeWithToken(tokenRes.access_token);
      setAuth(tokenRes.access_token, user);
      toast.success(`Welcome back, ${user.full_name ?? user.email}!`);
      router.push('/dashboard/scan');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login failed. Check your credentials.';
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
      className="space-y-5"
    >
      {/* Email */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="login-email">
          Email address
        </label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          placeholder="recruiter@company.com"
          {...register('email')}
          className={cn(
            'w-full px-4 py-2.5 rounded-lg text-sm bg-[#0D0F14] border text-[#E8E6DF]',
            'placeholder:text-[#7A8099] outline-none transition-all duration-200',
            'focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/20',
            errors.email ? 'border-[#E05252]' : 'border-[rgba(60,182,151,0.2)]',
          )}
        />
        {errors.email && (
          <p className="text-xs text-[#E05252]">{errors.email.message}</p>
        )}
      </div>

      {/* Password */}
      <div className="space-y-1.5">
        <label className="text-sm font-medium text-[#E8E6DF]/80" htmlFor="login-password">
          Password
        </label>
        <div className="relative">
          <input
            id="login-password"
            type={showPass ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="••••••••"
            {...register('password')}
            className={cn(
              'w-full px-4 py-2.5 pr-10 rounded-lg text-sm bg-[#0D0F14] border text-[#E8E6DF]',
              'placeholder:text-[#7A8099] outline-none transition-all duration-200',
              'focus:border-[#3CB697] focus:ring-2 focus:ring-[#3CB697]/20',
              errors.password ? 'border-[#E05252]' : 'border-[rgba(60,182,151,0.2)]',
            )}
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
          <LogIn size={16} />
        )}
        {loading ? 'Signing in…' : 'Sign In'}
      </motion.button>
    </motion.form>
  );
}
