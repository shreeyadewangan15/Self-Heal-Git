'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AdminPageRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/admin');
  }, [router]);

  return (
    <div className="py-24 text-center text-slate-500 text-xs">
      <div className="w-6 h-6 rounded-full border-2 border-purple-500/20 border-t-purple-400 animate-spin mx-auto mb-3" />
      Redirecting to Administrator Control Center...
    </div>
  );
}
