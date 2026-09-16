'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { getToken, getStoredUser, getMe, removeToken } from '@/lib/api';
import { UserProfile } from '@/lib/types';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace('/login');
      return;
    }

    // Attempt fast local hydration
    const stored = getStoredUser();
    if (stored && stored.email && stored.role) {
      setUser({
        id: stored.id || 1,
        email: stored.email,
        full_name: stored.full_name || stored.email.split('@')[0],
        role: stored.role,
        auth_provider: 'local',
      });
      setLoading(false);
    }

    // Verify token with backend
    getMe()
      .then((profile) => {
        setUser(profile);
        setLoading(false);
      })
      .catch((err) => {
        console.warn('Auth verification failed:', err);
        // Only redirect if no local user could be decoded
        if (!stored?.role) {
          removeToken();
          router.replace('/login');
        }
      });
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400">
        <div className="relative">
          <div className="w-12 h-12 rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin" />
        </div>
        <div className="mt-4 text-xs font-mono tracking-wider uppercase text-slate-500">
          Authenticating Role Credentials...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Dynamic Role-Based Sidebar */}
      <Sidebar user={user} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">Environment:</span>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              production-sim
            </span>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="font-mono text-slate-300">FastAPI API :8000</span>
            </div>
            <div className="hidden sm:block text-slate-700">|</div>
            <div className="hidden sm:flex items-center gap-2 text-slate-400 font-mono">
              Role Clearance: <strong className="text-white">{user?.role}</strong>
            </div>
          </div>
        </header>

        {/* Content Viewport */}
        <div className="flex-1 p-6 md:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
