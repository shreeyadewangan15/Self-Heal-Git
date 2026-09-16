'use client';

import React from 'react';
import Link from 'next/link';
import { ShieldAlert, ArrowLeft, Lock } from 'lucide-react';
import { UserRole } from '@/lib/types';

interface AccessDeniedProps {
  requiredRole?: UserRole | string;
  currentRole?: UserRole | string | null;
  message?: string;
}

export default function AccessDenied({
  requiredRole = 'ADMIN',
  currentRole = 'DEVELOPER',
  message,
}: AccessDeniedProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] p-6 text-center">
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center shadow-lg shadow-rose-950/40">
          <ShieldAlert className="w-10 h-10 text-rose-400 animate-pulse" />
        </div>
        <div className="absolute -bottom-2 -right-2 bg-slate-900 border border-rose-500/40 rounded-full p-1.5 shadow">
          <Lock className="w-4 h-4 text-rose-400" />
        </div>
      </div>

      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium tracking-wider uppercase bg-rose-500/10 border border-rose-500/20 text-rose-300 mb-3">
        HTTP 403 Forbidden
      </div>

      <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">
        Access Denied & Role Clearance Required
      </h1>

      <p className="max-w-md text-sm text-slate-400 mb-6">
        {message ||
          `This sector requires ${requiredRole} clearance. Your current active role is ${currentRole || 'DEVELOPER'}. Please contact your administrator to request elevated permissions.`}
      </p>

      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 mb-6 max-w-sm w-full text-left font-mono text-xs space-y-2">
        <div className="flex justify-between items-center text-slate-400">
          <span>Required Clearance:</span>
          <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-semibold">
            {requiredRole}
          </span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Your Active Role:</span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold">
            {currentRole || 'DEVELOPER'}
          </span>
        </div>
        <div className="flex justify-between items-center text-slate-400">
          <span>Enforcement Policy:</span>
          <span className="text-rose-400">Strict RBAC</span>
        </div>
      </div>

      <Link
        href="/pr-feed"
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition-colors border border-slate-700/60 shadow"
      >
        <ArrowLeft className="w-4 h-4" />
        Return to PR Feed
      </Link>
    </div>
  );
}
