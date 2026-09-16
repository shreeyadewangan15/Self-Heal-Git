'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function PRFeedPageRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return (
    <div className="py-24 text-center text-slate-500 text-xs">
      <div className="w-6 h-6 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin mx-auto mb-3" />
      Redirecting to Developer Dashboard Feed...
    </div>
  );
}
