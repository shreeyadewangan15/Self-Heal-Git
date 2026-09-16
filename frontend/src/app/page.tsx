'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, getUserRole } from '@/lib/api';

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    if (token) {
      const role = getUserRole();
      if (role === 'ADMIN') {
        router.replace('/dashboard/admin');
      } else {
        router.replace('/dashboard');
      }
    } else {
      router.replace('/login');
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500">
      <div className="w-8 h-8 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin" />
    </div>
  );
}
