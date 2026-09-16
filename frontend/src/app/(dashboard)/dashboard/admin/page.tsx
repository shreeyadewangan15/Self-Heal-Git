'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getUserRole,
  getAdminUsers,
  updateAdminUser,
  getAdminRepositories,
  addAdminRepository,
  deleteAdminRepository,
  updateAdminRepository,
  getAdminTelemetry,
  updateAdminLLMConfig,
} from '@/lib/api';
import {
  UserProfile,
  UserRole,
  AdminRepository,
  AdminTelemetry,
  LLMConfig,
} from '@/lib/types';
import AccessDenied from '@/components/AccessDenied';
import {
  ShieldCheck,
  Users,
  Settings,
  GitBranch,
  Activity,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  DollarSign,
  Cpu,
  Clock,
  ShieldAlert,
  Save,
  BarChart3,
} from 'lucide-react';

export default function AdminControlCenterPage() {
  const router = useRouter();
  const [currentRole, setCurrentRole] = useState<UserRole | null>(null);

  // Data States
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [repos, setRepos] = useState<AdminRepository[]>([]);
  const [telemetry, setTelemetry] = useState<AdminTelemetry | null>(null);

  // Form states
  const [newRepoName, setNewRepoName] = useState('');
  const [newRepoSecret, setNewRepoSecret] = useState('whsec_tcet_auto');
  const [newRepoAutoCommit, setNewRepoAutoCommit] = useState(true);

  // LLM Config state
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    model_target: 'claude-3-5-sonnet-20241022',
    confidence_threshold: 0.85,
    rate_limit_rpm: 60,
    ast_sandboxing: true,
    auto_commit_global: true,
  });

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const role = getUserRole();
    setCurrentRole(role);

    // STRICT RBAC CHECK: If non-admin, redirect with 403 Unauthorized Access toast
    if (role && role !== 'ADMIN') {
      // Set error toast in sessionStorage so dashboard displays it
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('rbac_error_toast', '403 Forbidden: Unauthorized Access to Administrator Control Center.');
      }
      router.replace('/dashboard');
      return;
    }

    if (role === 'ADMIN') {
      loadAllAdminData();
    } else {
      setLoading(false);
    }
  }, [router]);

  const loadAllAdminData = async () => {
    try {
      setLoading(true);
      const [usersData, reposData, telemetryData] = await Promise.all([
        getAdminUsers(),
        getAdminRepositories(),
        getAdminTelemetry(),
      ]);
      setUsers(usersData);
      setRepos(reposData);
      setTelemetry(telemetryData);
      if (telemetryData.runtime_config) {
        setLlmConfig(telemetryData.runtime_config);
      }
    } catch (err: unknown) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId: number, newRole: UserRole) => {
    setActionLoading(true);
    try {
      await updateAdminUser(userId, { role: newRole });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
      setToastMessage({
        type: 'success',
        text: `Updated clearance for user #${userId} to ${newRole}`,
      });
      const tel = await getAdminTelemetry();
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to update user role',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleToggleActive = async (userId: number, currentActive: boolean) => {
    setActionLoading(true);
    try {
      const nextActive = !currentActive;
      await updateAdminUser(userId, { is_active: nextActive });
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: nextActive } : u))
      );
      setToastMessage({
        type: 'success',
        text: `User account ${nextActive ? 'activated' : 'deactivated'} successfully.`,
      });
      const tel = await getAdminTelemetry();
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to update user status',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleAddRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoName.trim()) return;
    setActionLoading(true);
    try {
      const res = await addAdminRepository({
        full_name: newRepoName.trim(),
        webhook_secret: newRepoSecret,
        auto_commit_enabled: newRepoAutoCommit,
      });
      setNewRepoName('');
      setToastMessage({
        type: 'success',
        text: res.message,
      });
      const [updatedRepos, tel] = await Promise.all([
        getAdminRepositories(),
        getAdminTelemetry(),
      ]);
      setRepos(updatedRepos);
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to add repository',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleDeleteRepo = async (repoId: number) => {
    const repo = repos.find((r) => r.id === repoId);
    const repoName = repo ? repo.full_name : `#${repoId}`;
    if (!window.confirm(`Are you sure you want to disconnect and delete repository "${repoName}"? All automated AST healing and webhook listeners for this repo will be removed.`)) {
      return;
    }
    setActionLoading(true);
    try {
      const res = await deleteAdminRepository(repoId);
      setToastMessage({
        type: 'success',
        text: res.message,
      });
      setRepos((prev) => prev.filter((r) => r.id !== repoId));
      const tel = await getAdminTelemetry();
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to delete repository',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleToggleRepoAutoCommit = async (repoId: number, currentAutoCommit: boolean) => {
    setActionLoading(true);
    try {
      const nextState = !currentAutoCommit;
      await updateAdminRepository(repoId, { auto_commit_enabled: nextState });
      setRepos((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, auto_commit_enabled: nextState } : r))
      );
      setToastMessage({
        type: 'success',
        text: `Automated committing ${nextState ? 'ENABLED' : 'PAUSED'} for repository.`,
      });
      const tel = await getAdminTelemetry();
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to update repository auto-commit state',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  const handleSaveLLMConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const res = await updateAdminLLMConfig(llmConfig);
      setToastMessage({
        type: 'success',
        text: res.message,
      });
      const tel = await getAdminTelemetry();
      setTelemetry(tel);
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || 'Failed to update LLM configuration',
      });
    } finally {
      setActionLoading(false);
      setTimeout(() => setToastMessage(null), 3500);
    }
  };

  // If non-admin is detected, show AccessDenied while redirecting
  if (currentRole && currentRole !== 'ADMIN') {
    return (
      <AccessDenied
        requiredRole="ADMIN"
        currentRole={currentRole}
        message="403 Forbidden: Unauthorized Access to Administrator Control Center. Strictly restricted to Tier 3 administrators."
      />
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium tracking-wide bg-purple-500/10 border border-purple-500/30 text-purple-300 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            Tier 3 Clearance Active
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Administrator Control Center & RBAC Governance
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Global system management: user governance, connected repositories, real-time token telemetry, and autonomous LLM tuning.
          </p>
        </div>

        <button
          onClick={loadAllAdminData}
          disabled={loading}
          id="reload-admin-data-btn"
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-800 transition-colors w-fit"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Reload Admin State
        </button>
      </div>

      {/* Toast Alert */}
      {toastMessage && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center gap-2.5 transition-all ${
            toastMessage.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          ) : (
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* SECTION 1: System Health & Telemetry Cards */}
      <div className="space-y-3" id="telemetry">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-purple-400" />
          System Health & LLM Telemetry
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Estimated Token Cost */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Token Usage & Cost</span>
              <DollarSign className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-300 font-mono">
              ${(telemetry?.token_usage.estimated_cost_usd ?? 0).toFixed(4)}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">
              Total: {(telemetry?.token_usage.total_tokens ?? 0).toLocaleString()} tokens
            </div>
          </div>

          {/* Average Healing Latency */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Avg Healing Latency</span>
              <Clock className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold text-cyan-400 font-mono">
              {telemetry?.llm_health.avg_latency_sec ? `${telemetry.llm_health.avg_latency_sec}s` : '0.0s'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              AST AST.parse() sandbox execution
            </div>
          </div>

          {/* Global Error Rate */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Global Error Rate</span>
              <Cpu className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 font-mono">
              {telemetry?.llm_health.error_rate_pct ?? 0}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Deterministic AST fallback verified
            </div>
          </div>

          {/* Target Model */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
              <span>Active Target Engine</span>
              <Settings className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-sm font-bold text-white font-mono truncate">
              {telemetry?.llm_health.current_model || 'claude-3-5-sonnet'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              Confidence threshold: {Math.round(llmConfig.confidence_threshold * 100)}%
            </div>
          </div>
        </div>

        {/* Token Cost Graph & Usage Distribution Panel */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-white">
                <BarChart3 className="w-4 h-4 text-purple-400" />
                <span>Token Consumption & Cost Trajectory Graph</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Hourly cumulative API expenses and token breakdown across autonomous PR review cycles
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="inline-flex items-center gap-1.5 text-purple-300">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
                Prompt: {(telemetry?.token_usage.prompt_tokens ?? 0).toLocaleString()}
              </span>
              <span className="inline-flex items-center gap-1.5 text-cyan-300">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
                Completion: {(telemetry?.token_usage.completion_tokens ?? 0).toLocaleString()}
              </span>
            </div>
          </div>

          {/* Visual Interactive Hourly Cost Graph */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Trend Graph Bars (8 cols) */}
            <div className="lg:col-span-8 space-y-2">
              <div className="h-44 w-full relative flex items-end justify-between px-6 pb-4 pt-6 bg-slate-950/70 rounded-xl border border-slate-800/80">
                {/* Horizontal grid lines */}
                <div className="absolute inset-x-0 top-1/4 border-b border-slate-800/40 pointer-events-none" />
                <div className="absolute inset-x-0 top-2/4 border-b border-slate-800/40 pointer-events-none" />
                <div className="absolute inset-x-0 top-3/4 border-b border-slate-800/40 pointer-events-none" />

                {!telemetry?.token_usage.history || telemetry.token_usage.history.length === 0 ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 text-xs px-4 text-center">
                    <BarChart3 className="w-6 h-6 text-slate-600 mb-1" />
                    <span>No token usage recorded yet. Costs and hourly usage will plot here as pull requests are analyzed.</span>
                  </div>
                ) : (
                  telemetry.token_usage.history.map((point, idx, arr) => {
                    const maxCost = Math.max(...arr.map((p) => p.cost || 0.05));
                    const heightPct = Math.max(20, Math.round((point.cost / (maxCost * 1.15)) * 100));
                    return (
                      <div key={idx} className="flex flex-col items-center gap-2 group z-10 w-16">
                        <span className="text-[10px] font-mono text-purple-300 opacity-0 group-hover:opacity-100 transition-opacity bg-purple-950/90 px-1.5 py-0.5 rounded border border-purple-500/40 shadow">
                          ${point.cost.toFixed(4)}
                        </span>
                        <div
                          style={{ height: `${heightPct}%` }}
                          className="w-10 rounded-t-lg bg-gradient-to-t from-purple-600/70 to-purple-400 group-hover:from-purple-500 group-hover:to-cyan-400 transition-all shadow-md group-hover:shadow-purple-500/30 cursor-pointer"
                        />
                        <span className="text-[10px] font-mono text-slate-400 group-hover:text-white transition-colors">
                          {point.timestamp}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Ratio Breakdown & Economics Card (4 cols) */}
            <div className="lg:col-span-4 space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
              <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span>Prompt vs Completion Ratio</span>
                <span className="font-mono text-purple-300">
                  {telemetry?.token_usage.total_tokens && telemetry.token_usage.total_tokens > 0
                    ? `${Math.round((telemetry.token_usage.prompt_tokens / telemetry.token_usage.total_tokens) * 100)}% Prompt`
                    : '0% Prompt'}
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                <div
                  style={{
                    width: `${
                      telemetry?.token_usage.total_tokens && telemetry.token_usage.total_tokens > 0
                        ? Math.round((telemetry.token_usage.prompt_tokens / telemetry.token_usage.total_tokens) * 100)
                        : 0
                    }%`,
                  }}
                  className="bg-purple-500 h-full"
                />
                <div className="bg-cyan-400 h-full flex-1" />
              </div>

              <div className="pt-2 text-[11px] text-slate-400 space-y-1.5 border-t border-slate-800/60">
                <div className="flex justify-between">
                  <span>Prompt Cost Base:</span>
                  <span className="font-mono text-slate-300">$0.003 / 1k</span>
                </div>
                <div className="flex justify-between">
                  <span>Completion Cost Base:</span>
                  <span className="font-mono text-slate-300">$0.015 / 1k</span>
                </div>
                <div className="flex justify-between font-semibold text-emerald-400 pt-1">
                  <span>Cumulative Session Total:</span>
                  <span className="font-mono">${(telemetry?.token_usage.estimated_cost_usd ?? 0).toFixed(4)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: User Management Table */}
      <div className="space-y-4" id="users">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-purple-400" />
            User Management ({users.length})
          </h2>
          <span className="text-xs text-slate-500 font-mono">SQLite user table</span>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3.5">User Identity</th>
                  <th className="px-4 py-3.5">Auth Provider</th>
                  <th className="px-4 py-3.5">Clearance Role</th>
                  <th className="px-4 py-3.5">Account Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => {
                  const isActive = u.is_active !== false;
                  return (
                    <tr key={u.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-white">{u.full_name || 'System User'}</div>
                        <div className="text-[11px] text-slate-400 font-mono">{u.email}</div>
                      </td>

                      <td className="px-4 py-3.5 font-mono text-[11px]">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {u.auth_provider || 'google'}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <select
                          value={u.role}
                          disabled={actionLoading}
                          onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                          className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold uppercase bg-slate-950 border transition-colors cursor-pointer ${
                            u.role === 'ADMIN'
                              ? 'text-purple-300 border-purple-500/40 bg-purple-950/30'
                              : 'text-emerald-300 border-emerald-500/40 bg-emerald-950/30'
                          }`}
                        >
                          <option value="DEVELOPER" className="bg-slate-900 text-emerald-300">
                            DEVELOPER (Tier 1)
                          </option>
                          <option value="ADMIN" className="bg-slate-900 text-purple-300">
                            ADMIN (Tier 3)
                          </option>
                        </select>
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                            isActive
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          }`}
                        >
                          {isActive ? 'ACTIVE' : 'DEACTIVATED'}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => handleToggleActive(u.id, isActive)}
                          disabled={actionLoading}
                          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors border ${
                            isActive
                              ? 'bg-rose-950/30 hover:bg-rose-900/40 text-rose-300 border-rose-800/40'
                              : 'bg-emerald-950/30 hover:bg-emerald-900/40 text-emerald-300 border-emerald-800/40'
                          }`}
                        >
                          {isActive ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SECTION 3: Connected Repositories Panel */}
      <div className="space-y-4" id="repos">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-purple-400" />
            Connected Repositories ({repos.length})
          </h2>
        </div>

        {/* Add Repo Form */}
        <form
          onSubmit={handleAddRepo}
          className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col sm:flex-row items-stretch sm:items-center gap-3"
        >
          <div className="flex-1">
            <input
              type="text"
              id="add-repo-name-input"
              placeholder="e.g. tcet-opensource/gateway-service"
              value={newRepoName}
              onChange={(e) => setNewRepoName(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 font-mono focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="sm:w-48">
            <input
              type="text"
              id="add-repo-secret-input"
              placeholder="Webhook Secret"
              value={newRepoSecret}
              onChange={(e) => setNewRepoSecret(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-500 font-mono focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              id="auto-commit-toggle"
              checked={newRepoAutoCommit}
              onChange={(e) => setNewRepoAutoCommit(e.target.checked)}
              className="accent-purple-500 rounded"
            />
            <label htmlFor="auto-commit-toggle" className="select-none text-[11px]">
              Auto-Commit Mode
            </label>
          </div>

          <button
            type="submit"
            id="submit-add-repo-btn"
            disabled={actionLoading || !newRepoName.trim()}
            className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors shrink-0 disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" />
            Connect Repository
          </button>
        </form>

        {/* Repo Cards Grid */}
        {repos.length === 0 ? (
          <div className="p-8 text-center rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
            <GitBranch className="w-8 h-8 text-slate-600 mx-auto" />
            <div className="text-xs font-bold text-slate-300">No Monitored Repositories Connected</div>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              Add your repository URL and webhook secret above to begin autonomous PR monitoring.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {repos.map((repo) => (
              <div
                key={repo.id}
                className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 shadow-lg space-y-3"
              >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-mono text-sm font-bold text-white break-all">
                    {repo.full_name}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                    PRs Monitored: {repo.pr_count}
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {repo.webhook_status}
                </span>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400 text-[11px]">Automated Committing:</span>
                  <button
                    type="button"
                    onClick={() => handleToggleRepoAutoCommit(repo.id, repo.auto_commit_enabled)}
                    disabled={actionLoading}
                    title="Click to toggle automated PR commits"
                    className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wider uppercase border transition-all cursor-pointer ${
                      repo.auto_commit_enabled
                        ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/25'
                        : 'bg-amber-500/15 text-amber-300 border-amber-500/40 hover:bg-amber-500/25'
                    }`}
                  >
                    {repo.auto_commit_enabled ? '● ENABLED' : '○ PAUSED'}
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => handleDeleteRepo(repo.id)}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/20 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
        )}
      </div>

      {/* SECTION 4: LLM Configuration & System Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LLM Runtime Config (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-purple-400" />
            Autonomous LLM Parameters
          </h2>

          <form
            onSubmit={handleSaveLLMConfig}
            className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4 shadow-xl"
          >
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Diagnostic Target Model
              </label>
              <select
                value={llmConfig.model_target}
                onChange={(e) =>
                  setLlmConfig((prev) => ({ ...prev, model_target: e.target.value }))
                }
                className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-purple-500"
              >
                <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet-20241022 (Primary)</option>
                <option value="gpt-4o-2024-08-06">gpt-4o-2024-08-06 (Strict JSON)</option>
                <option value="deepseek-coder-v2">deepseek-coder-v2 (Local)</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                <span>Confidence Threshold</span>
                <span className="font-mono text-emerald-400">
                  {Math.round(llmConfig.confidence_threshold * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="0.99"
                step="0.01"
                value={llmConfig.confidence_threshold}
                onChange={(e) =>
                  setLlmConfig((prev) => ({
                    ...prev,
                    confidence_threshold: parseFloat(e.target.value),
                  }))
                }
                className="w-full accent-purple-500 cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Rate Limit (Requests / Minute)
              </label>
              <input
                type="number"
                value={llmConfig.rate_limit_rpm}
                onChange={(e) =>
                  setLlmConfig((prev) => ({
                    ...prev,
                    rate_limit_rpm: parseInt(e.target.value, 10) || 60,
                  }))
                }
                className="w-full px-3 py-1.5 text-xs font-mono rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={actionLoading}
              className="w-full py-2.5 px-4 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              Save LLM Configuration
            </button>
          </form>
        </div>

        {/* Audit Logs Stream (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-purple-400" />
            Security & System Audit Logs
          </h2>

          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-xl max-h-[380px] overflow-y-auto scrollbar-thin space-y-2.5">
            {telemetry?.audit_logs && telemetry.audit_logs.length > 0 ? (
              telemetry.audit_logs.map((log) => (
                <div
                  key={log.id}
                  className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-purple-300 font-bold">{log.action}</span>
                    <span className="text-slate-500">{log.timestamp.slice(11, 19)}</span>
                  </div>
                  <div className="text-slate-300 text-[11px]">{log.details}</div>
                  <div className="text-slate-500 text-[10px] font-mono">Actor: {log.actor}</div>
                </div>
              ))
            ) : (
              <div className="text-slate-500 text-xs text-center py-8">
                No security audit logs recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
