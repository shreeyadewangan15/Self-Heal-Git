'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  getMyPRFeed,
  simulatePR,
  simulateSandboxPatch,
  deletePR,
} from '@/lib/api';
import {
  PRRecordSummary,
  PRStats,
  SandboxSimulateResult,
} from '@/lib/types';
import ThreeAgentDiagnosticTrace from '@/components/ThreeAgentDiagnosticTrace';
import {
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  Zap,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  GitCommit,
  Cpu,
  FileCode,
  Play,
  X,
  Code2,
  ExternalLink,
  ShieldAlert,
  Trash2,
} from 'lucide-react';

const SANDBOX_TEMPLATES = [
  {
    name: 'Missing Import Bug',
    description: "Calls json.loads() without declaring 'import json'",
    code: `# Faulty service handling JSON payload
def parse_payload(payload_str):
    data = json.loads(payload_str)
    return data.get("status")
`,
  },
  {
    name: 'ZeroDivisionError Hazard',
    description: 'Divides total by count without divisor == 0 safeguard',
    code: `# Metric calculator missing divisor guard
def calculate_ratio(total, count):
    return total / count
`,
  },
  {
    name: 'Malformed Syntax Anomaly',
    description: 'Function definition missing trailing colon and parameter list closure',
    code: `# Unclosed syntax definition
def broken_func(
    value = 42
    return value * 2
`,
  },
];

export default function DeveloperDashboardPage() {
  const searchParams = useSearchParams();
  const [stats, setStats] = useState<PRStats>({
    total: 0,
    healed: 0,
    analyzing: 0,
    failed: 0,
    success_rate: 0,
    avg_confidence: 0,
  });
  const [prs, setPrs] = useState<PRRecordSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Sandbox Modal State
  const [isSandboxOpen, setIsSandboxOpen] = useState(false);
  const [sandboxCode, setSandboxCode] = useState(SANDBOX_TEMPLATES[0].code);
  const [sandboxFilePath, setSandboxFilePath] = useState('core/service.py');
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [sandboxResult, setSandboxResult] = useState<SandboxSimulateResult | null>(null);

  const [rbacToast, setRbacToast] = useState<string | null>(null);

  const fetchFeed = async () => {
    try {
      setLoading(true);
      const res = await getMyPRFeed();
      setStats(res.stats);
      setPrs(res.prs);
    } catch (err) {
      console.error('Failed to fetch developer PR feed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    if (searchParams.get('modal') === 'sandbox') {
      setIsSandboxOpen(true);
    }

    if (typeof window !== 'undefined') {
      const errorMsg = sessionStorage.getItem('rbac_error_toast');
      if (errorMsg) {
        setRbacToast(errorMsg);
        sessionStorage.removeItem('rbac_error_toast');
        const timer = setTimeout(() => {
          setRbacToast(null);
        }, 8000);
        return () => clearTimeout(timer);
      }
    }
  }, [searchParams]);

  const handleRunSandbox = async () => {
    setSandboxLoading(true);
    try {
      const res = await simulateSandboxPatch({
        code_snippet: sandboxCode,
        file_path: sandboxFilePath,
      });
      setSandboxResult(res);
    } catch (err: unknown) {
      console.error('Sandbox execution failed:', err);
    } finally {
      setSandboxLoading(false);
    }
  };

  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSimulateNewPR = async () => {
    try {
      setLoading(true);
      await simulatePR();
      setTimeout(async () => {
        await fetchFeed();
      }, 1000);
    } catch (err) {
      console.error('Simulate PR failed:', err);
      setLoading(false);
    }
  };

  const handleDeletePR = async (prId: number, prNumber: number) => {
    if (!window.confirm(`Are you sure you want to delete Pull Request #${prNumber}? This action cannot be undone.`)) {
      return;
    }
    setDeletingId(prId);
    try {
      const res = await deletePR(prId);
      setToastMessage({
        type: 'success',
        text: res.message || `Pull Request #${prNumber} deleted successfully.`,
      });
      await fetchFeed();
    } catch (err: unknown) {
      setToastMessage({
        type: 'error',
        text: (err as Error).message || `Failed to delete PR #${prNumber}.`,
      });
    } finally {
      setDeletingId(null);
      setTimeout(() => setToastMessage(null), 4000);
    }
  };

  const filteredPrs = useMemo(() => {
    return prs.filter((item) => {
      const matchesSearch =
        item.repo.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.pr_number.toString().includes(searchQuery);

      if (statusFilter === 'ALL') return matchesSearch;
      return matchesSearch && item.status.toUpperCase() === statusFilter.toUpperCase();
    });
  }, [prs, searchQuery, statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'HEALED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            HEALED
          </span>
        );
      case 'ANALYZING':
      case 'RECEIVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
            <RefreshCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
            {status}
          </span>
        );
      case 'FAILED':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* 403 Forbidden RBAC Toast Alert */}
      {rbacToast && (
        <div
          id="rbac-error-toast"
          className="p-4 rounded-xl border border-rose-500/50 bg-rose-950/80 backdrop-blur-md shadow-2xl flex items-center justify-between gap-4 animate-in fade-in slide-in-from-top-3 duration-300"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>403 Unauthorized Access</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold">
                  Tier 3 Admin Clearance Required
                </span>
              </div>
              <div className="text-xs text-rose-300/90 mt-0.5">{rbacToast}</div>
            </div>
          </div>
          <button
            type="button"
            id="dismiss-rbac-toast-btn"
            onClick={() => setRbacToast(null)}
            className="p-1.5 rounded-lg text-rose-400 hover:text-white hover:bg-rose-900/40 transition-colors shrink-0"
            aria-label="Dismiss error"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Action Toast Alert */}
      {toastMessage && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 animate-in fade-in slide-in-from-top-2 transition-all ${
            toastMessage.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {toastMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            )}
            <span>{toastMessage.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium tracking-wide bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-2">
            <Cpu className="w-3.5 h-3.5" />
            Developer Console Active
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Pull Request Status Feed & AST Healer
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time GitHub pull requests monitored for syntax, import, and logic bugs with zero-regression AST sandboxing.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsSandboxOpen(true)}
            id="open-sandbox-btn"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-500/30 text-xs font-semibold shadow-sm transition-all"
          >
            <Code2 className="w-4 h-4" />
            Simulate Patch Sandbox
          </button>

          <button
            onClick={handleSimulateNewPR}
            id="simulate-pr-feed-btn"
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 text-xs font-bold shadow-lg shadow-emerald-950/40 transition-all disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Simulate Live PR
          </button>
        </div>
      </div>

      {/* Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Total Intercepted PRs</span>
            <GitPullRequest className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{stats.total}</div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <span className="text-emerald-400">●</span> Real-time GitHub Webhook feed
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Auto-Healed PRs</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">{stats.healed}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            Zero-regression AST verified commits
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Autonomous Success Rate</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 font-mono">{stats.success_rate}%</div>
          <div className="text-[11px] text-slate-400 mt-1">Syntactic AST parse verification</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-2">
            <span>Average Confidence</span>
            <Sparkles className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400 font-mono">
            {stats.avg_confidence}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Multi-stage LLM diagnostic engine</div>
        </div>
      </div>

      {/* 3-Agent Event-Driven Pipeline Diagnostic Trace */}
      <ThreeAgentDiagnosticTrace />

      {/* PR Table Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              id="search-pr-feed-input"
              placeholder="Search repository, PR title, or #..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 focus:border-emerald-500 focus:outline-none text-white placeholder-slate-400"
            />
          </div>

          {/* Status Filter Tabs */}
          <div className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs">
            {['ALL', 'HEALED', 'ANALYZING', 'FAILED'].map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1 rounded text-[11px] font-medium transition-colors ${
                  statusFilter === tab
                    ? 'bg-emerald-500/20 text-emerald-300 font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* PR Feed Table */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/90 text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Repository / PR</th>
                  <th className="px-5 py-3.5">Title & Diagnostics</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Confidence</th>
                  <th className="px-5 py-3.5 text-right">Inspect Split Diff</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPrs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-12 text-center text-slate-500">
                      {loading ? (
                        <div className="flex items-center justify-center gap-2 py-4">
                          <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                          <span className="text-xs">Connecting to autonomous PR feed...</span>
                        </div>
                      ) : (
                        <div className="py-6 space-y-3 max-w-md mx-auto">
                          <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
                            <GitPullRequest className="w-6 h-6 text-slate-400" />
                          </div>
                          <div className="text-sm font-semibold text-white">No Pull Requests Monitored Yet</div>
                          <p className="text-xs text-slate-400 leading-relaxed">
                            Pull requests and AST healing actions will be recorded here once live webhooks arrive or when you trigger a simulation.
                          </p>
                          <div className="flex items-center justify-center gap-2 pt-2">
                            <button
                              type="button"
                              onClick={handleSimulateNewPR}
                              className="px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-colors"
                            >
                              + Simulate Live PR
                            </button>
                            <button
                              type="button"
                              onClick={() => setIsSandboxOpen(true)}
                              className="px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-semibold transition-colors"
                            >
                              Simulate Patch Sandbox
                            </button>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                ) : (
                  filteredPrs.map((pr) => (
                    <tr
                      key={pr.id}
                      className="hover:bg-slate-800/40 transition-colors group"
                    >
                      <td className="px-5 py-4">
                        <div className="font-mono text-white font-medium">{pr.repo}</div>
                        <div className="text-[11px] text-slate-400 font-mono">
                          PR #{pr.pr_number}
                          {pr.commit_sha && (
                            <span className="ml-2 inline-flex items-center gap-1 text-slate-400">
                              <GitCommit className="w-3 h-3 text-slate-400" />
                              {pr.commit_sha.slice(0, 7)}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="font-semibold text-white group-hover:text-emerald-300 transition-colors">
                          {pr.title}
                        </div>
                        {pr.summary && (
                          <div className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                            {pr.summary}
                          </div>
                        )}
                      </td>

                      <td className="px-5 py-4 whitespace-nowrap">
                        {getStatusBadge(pr.status)}
                      </td>

                      <td className="px-5 py-4 font-mono">
                        {pr.confidence !== null ? (
                          <span className="text-emerald-400 font-bold">
                            {Math.round(
                              pr.confidence > 1 ? pr.confidence : pr.confidence * 100
                            )}
                            %
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/dashboard/pr/${pr.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-emerald-300 text-xs font-medium border border-slate-700/60 transition-colors"
                          >
                            <span>Inspect Diff</span>
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                          <button
                            type="button"
                            onClick={() => handleDeletePR(pr.id, pr.pr_number)}
                            disabled={deletingId === pr.id}
                            title="Delete this PR record"
                            aria-label={`Delete PR #${pr.pr_number}`}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 border border-slate-700/60 hover:border-rose-500/40 transition-colors disabled:opacity-50"
                          >
                            {deletingId === pr.id ? (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin text-rose-400" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SIMULATE PATCH SANDBOX MODAL */}
      {isSandboxOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
          <div className="w-full max-w-4xl rounded-2xl border border-slate-800 bg-slate-950 p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto scrollbar-thin">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  <Code2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    Autonomous AST Code Sandbox
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      Zero GitHub Mutation
                    </span>
                  </h2>
                  <p className="text-xs text-slate-400">
                    Test arbitrary code snippets against the diagnostic AST validator without modifying any remote branches.
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  setIsSandboxOpen(false);
                  setSandboxResult(null);
                }}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Template Buttons */}
            <div className="mb-4">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">
                Quick Bug Templates:
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {SANDBOX_TEMPLATES.map((tmpl, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setSandboxCode(tmpl.code);
                      setSandboxResult(null);
                    }}
                    className="p-2.5 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-800 text-left transition-colors group"
                  >
                    <div className="text-xs font-semibold text-white group-hover:text-cyan-300 truncate">
                      {tmpl.name}
                    </div>
                    <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">
                      {tmpl.description}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Code Input & File Path */}
            <div className="space-y-3 mb-5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                  Target Code Snippet:
                </label>
                <input
                  type="text"
                  value={sandboxFilePath}
                  onChange={(e) => setSandboxFilePath(e.target.value)}
                  placeholder="file_path.py"
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[11px] focus:outline-none focus:border-cyan-500"
                />
              </div>

              <textarea
                value={sandboxCode}
                onChange={(e) => setSandboxCode(e.target.value)}
                rows={7}
                className="w-full p-3 font-mono text-xs rounded-xl bg-slate-900/90 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 leading-relaxed scrollbar-thin"
              />

              <div className="flex justify-end">
                <button
                  type="button"
                  id="run-sandbox-diagnostic-btn"
                  disabled={sandboxLoading || !sandboxCode.trim()}
                  onClick={handleRunSandbox}
                  className="px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-600 hover:from-cyan-400 hover:to-teal-500 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-950/50 transition-all disabled:opacity-50"
                >
                  <Play className={`w-3.5 h-3.5 fill-current ${sandboxLoading ? 'animate-spin' : ''}`} />
                  {sandboxLoading ? 'Synthesizing AST Patch...' : 'Diagnose & Verify AST'}
                </button>
              </div>
            </div>

            {/* Sandbox Result Output */}
            {sandboxResult && (
              <div className="pt-4 border-t border-slate-800 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    Sandbox Diagnostic Verdict
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-mono font-semibold uppercase ${
                      sandboxResult.ast_valid
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                    }`}
                  >
                    AST Status: {sandboxResult.ast_valid ? 'VALIDATED SAFE' : 'SYNTAX ERROR'}
                  </span>
                </div>

                {/* AST Logs */}
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre leading-relaxed">
                  {sandboxResult.ast_logs}
                </div>

                {/* Split Diff Comparison */}
                {sandboxResult.patches && sandboxResult.patches.length > 0 && (
                  <div className="rounded-xl border border-slate-800 overflow-hidden">
                    <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs font-semibold text-slate-300 flex items-center justify-between">
                      <span>Side-by-Side Sandbox Diff</span>
                      <span className="text-emerald-400 font-mono text-[11px]">
                        Confidence: {Math.round(sandboxResult.confidence * 100)}%
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800 text-xs font-mono">
                      {/* Before */}
                      <div className="p-3 bg-rose-950/15">
                        <div className="text-[10px] text-rose-400 font-bold uppercase mb-1">
                          Original Broken Snippet
                        </div>
                        <pre className="text-rose-200 whitespace-pre overflow-x-auto">
                          {sandboxResult.patches[0].original_snippet}
                        </pre>
                      </div>

                      {/* After */}
                      <div className="p-3 bg-emerald-950/15">
                        <div className="text-[10px] text-emerald-400 font-bold uppercase mb-1">
                          Healed AST-Validated Snippet
                        </div>
                        <pre className="text-emerald-200 whitespace-pre overflow-x-auto">
                          {sandboxResult.patches[0].replacement_snippet}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
