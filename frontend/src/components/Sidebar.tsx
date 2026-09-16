'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  GitPullRequest,
  FileDiff,
  Users,
  Settings,
  GitBranch,
  LogOut,
  Bot,
  Activity,
} from 'lucide-react';
import { removeToken } from '@/lib/api';
import { UserProfile, UserRole } from '@/lib/types';

interface SidebarProps {
  user: UserProfile | null;
}

export default function Sidebar({ user }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const role: UserRole = user?.role || 'DEVELOPER';

  const handleLogout = () => {
    removeToken();
    router.push('/login');
  };

  const getRoleBadgeColor = (r: UserRole) => {
    switch (r) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'MAINTAINER':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      case 'DEVELOPER':
      default:
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
    }
  };

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800/80 flex flex-col shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <Link href="/dashboard" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-white shadow-lg shadow-emerald-950/50 group-hover:scale-105 transition-transform">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="font-bold text-sm text-white tracking-tight flex items-center gap-1.5">
              Self-Heal Git
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">
              Autonomous PR Monitor
            </div>
          </div>
        </Link>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin">
        {/* Core Dev Section (All Roles) */}
        <div>
          <div className="px-3 mb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Developer Console
          </div>
          <div className="space-y-1">
            <Link
              href="/dashboard"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                pathname === '/dashboard' || pathname.startsWith('/dashboard/pr')
                  ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <GitPullRequest className="w-4 h-4 text-emerald-400" />
              PR Status Feed
            </Link>

            <Link
              href="/dashboard?modal=sandbox"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                pathname === '/dashboard' && typeof window !== 'undefined' && window.location.search.includes('modal=sandbox')
                  ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <FileDiff className="w-4 h-4 text-cyan-400" />
              Simulate Patch Sandbox
            </Link>
          </div>
        </div>

        {/* Admin Control Center Section (ADMIN ONLY) */}
        {role === 'ADMIN' && (
          <div>
            <div className="px-3 mb-2 text-[10px] font-semibold text-purple-400/80 uppercase tracking-wider flex items-center justify-between">
              <span>Admin Control Center</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
                Tier 3
              </span>
            </div>
            <div className="space-y-1">
              <Link
                href="/dashboard/admin"
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  pathname === '/dashboard/admin'
                    ? 'bg-purple-500/10 text-purple-300 border border-purple-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Settings className="w-4 h-4 text-purple-400" />
                Control Center Home
              </Link>

              <Link
                href="/dashboard/admin#users"
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
              >
                <Users className="w-4 h-4 text-purple-400" />
                User Management
              </Link>

              <Link
                href="/dashboard/admin#repos"
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
              >
                <GitBranch className="w-4 h-4 text-purple-400" />
                Connected Repos
              </Link>

              <Link
                href="/dashboard/admin#telemetry"
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-900 transition-colors"
              >
                <Activity className="w-4 h-4 text-purple-400" />
                System Health & Telemetry
              </Link>
            </div>
          </div>
        )}

        {/* Informational telemetry status */}
        <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center gap-2 text-[11px] font-medium text-slate-300 mb-1">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            Live Engine Status
          </div>
          <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between">
            <span>FastAPI Agent:</span>
            <span className="text-emerald-400">ONLINE</span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between mt-0.5">
            <span>AST Sandboxing:</span>
            <span className="text-cyan-400">ACTIVE</span>
          </div>
        </div>
      </div>

      {/* User Profile & Logout Bottom Bar */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/90">
        <div className="flex items-center justify-between gap-2 mb-2 px-1">
          <div className="flex items-center gap-2 truncate">
            {user?.picture_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={user.picture_url}
                alt={user.full_name || 'Avatar'}
                className="w-7 h-7 rounded-full border border-emerald-500/40 shrink-0"
              />
            ) : null}
            <div className="truncate">
              <div className="text-xs font-semibold text-white truncate">
                {user?.full_name || 'System User'}
              </div>
              <div className="text-[11px] text-slate-400 truncate font-mono">
                {user?.email || 'user@tcet.edu'}
              </div>
            </div>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border shrink-0 ${getRoleBadgeColor(
              role
            )}`}
          >
            {role}
          </span>
        </div>

        <button
          onClick={handleLogout}
          id="logout-btn"
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/20 border border-transparent hover:border-rose-900/30 transition-all"
        >
          <LogOut className="w-3.5 h-3.5" />
          Disconnect Session
        </button>
      </div>
    </aside>
  );
}
