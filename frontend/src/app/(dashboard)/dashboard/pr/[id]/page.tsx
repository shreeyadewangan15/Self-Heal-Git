'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { getPRDiff, approvePRPatch, deletePR } from '@/lib/api';
import { PRRecordDetail, CodeIssue } from '@/lib/types';
import DiffViewer from '@/components/DiffViewer';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  GitCommit,
  Sparkles,
  Cpu,
  RefreshCw,
  Check,
  FileCode,
  Trash2,
} from 'lucide-react';

export default function PRDetailDiffPage() {
  const router = useRouter();
  const params = useParams();
  const prId = parseInt(params.id as string, 10);

  const [pr, setPr] = useState<PRRecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      const data = await getPRDiff(prId);
      setPr(data);
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        text: (err as Error).message || 'Failed to fetch PR diff details',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isNaN(prId)) {
      fetchDetail();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prId]);

  const handleApprove = async () => {
    setApproving(true);
    setFeedback(null);
    try {
      const res = await approvePRPatch(prId);
      setFeedback({
        type: 'success',
        text: res.message,
      });
      await fetchDetail();
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        text: (err as Error).message || 'Failed to approve patch',
      });
    } finally {
      setApproving(false);
    }
  };

  const handleDelete = async () => {
    if (!pr) return;
    if (
      !window.confirm(
        `Are you sure you want to permanently delete Pull Request #${pr.pr_number} (${pr.repo})? This action cannot be undone.`
      )
    ) {
      return;
    }
    setDeleting(true);
    setFeedback(null);
    try {
      await deletePR(prId);
      router.push('/dashboard');
    } catch (err: unknown) {
      setFeedback({
        type: 'error',
        text: (err as Error).message || 'Failed to delete pull request record',
      });
      setDeleting(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      case 'HIGH':
        return 'bg-orange-500/20 text-orange-300 border-orange-500/40';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'LOW':
      default:
        return 'bg-blue-500/20 text-blue-300 border-blue-500/40';
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-500 text-xs">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-400" />
        Loading AST Diff and Parse Logs...
      </div>
    );
  }

  if (!pr) {
    return (
      <div className="text-center py-24 space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Pull Request Record Not Found</h2>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 text-xs"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to PR Feed
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back Navigation Bar */}
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to PR Feed</span>
        </Link>

        {/* Status Badge */}
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide border ${
            pr.status === 'HEALED'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
          }`}
        >
          {pr.status}
        </span>
      </div>

      {/* Toast Notification */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center justify-between gap-3 ${
            feedback.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
            )}
            <span>{feedback.text}</span>
          </div>
        </div>
      )}

      {/* Header Info & Actions */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mb-1">
            <span>{pr.repo}</span>
            <span>•</span>
            <span>PR #{pr.pr_number}</span>
            {pr.commit_sha && (
              <>
                <span>•</span>
                <span className="inline-flex items-center gap-1 text-slate-300">
                  <GitCommit className="w-3.5 h-3.5 text-slate-400" />
                  {pr.commit_sha}
                </span>
              </>
            )}
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white">{pr.title}</h1>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            {pr.summary}
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            id="delete-pr-detail-btn"
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-400 border border-slate-700/60 hover:border-rose-500/40 font-semibold text-xs transition-all disabled:opacity-50"
          >
            {deleting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-rose-400" />
                <span>Deleting PR...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                <span>Delete PR</span>
              </>
            )}
          </button>

          <button
            onClick={handleApprove}
            disabled={approving || pr.status === 'HEALED'}
            id="approve-commit-patch-btn"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-950/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {approving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Committing AST Patch...</span>
              </>
            ) : pr.status === 'HEALED' ? (
              <>
                <Check className="w-4 h-4 text-slate-950" />
                <span>Patch Approved & Committed</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 text-slate-950" />
                <span>Approve & Commit Patch</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* AST Parse Logs Card */}
      {pr.ast_logs && (
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/80 shadow-lg">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>AST Parse & Sandboxing Verification Logs</span>
          </div>
          <div className="font-mono text-xs text-slate-300 whitespace-pre leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
            {pr.ast_logs}
          </div>
        </div>
      )}

      {/* Detected Issues */}
      {pr.issues && pr.issues.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            Detected Code Issues ({pr.issues.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {pr.issues.map((issue: CodeIssue, idx: number) => (
              <div
                key={idx}
                className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-slate-300 text-[11px]">
                    {issue.file_path}:{issue.line_number}
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getSeverityBadge(
                      issue.severity
                    )}`}
                  >
                    {issue.severity} • {issue.issue_type}
                  </span>
                </div>
                <div className="text-slate-400 text-[11px] leading-snug">
                  {issue.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Side-by-Side Split Diff Viewers */}
      <div className="space-y-4 pt-2">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <FileCode className="w-4 h-4 text-emerald-400" />
          Side-by-Side AST Validated Diff ({pr.patches?.length || 0})
        </h3>

        {pr.patches && pr.patches.length > 0 ? (
          pr.patches.map((patch, idx) => (
            <DiffViewer key={idx} patch={patch} issues={pr.issues} />
          ))
        ) : (
          <div className="p-8 text-center text-slate-500 text-xs border border-slate-800 rounded-xl bg-slate-900/40">
            No patch actions recorded for this pull request.
          </div>
        )}
      </div>
    </div>
  );
}
