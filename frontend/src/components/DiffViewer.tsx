'use client';

import React from 'react';
import { PatchAction, CodeIssue } from '@/lib/types';
import { FileCode, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

interface DiffViewerProps {
  patch: PatchAction;
  issues?: CodeIssue[];
}

export default function DiffViewer({ patch, issues = [] }: DiffViewerProps) {
  const originalLines = (patch.original_snippet || '').split('\n');
  const replacementLines = (patch.replacement_snippet || '').split('\n');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/70 overflow-hidden shadow-xl mb-6">
      {/* File Header */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 bg-slate-900/90 border-b border-slate-800/80 gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-emerald-500/10 text-emerald-400">
            <FileCode className="w-4 h-4" />
          </div>
          <span className="font-mono text-sm font-semibold text-slate-200">
            {patch.file_path || 'source_file.py'}
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            AST Validated Patch
          </span>
          {issues.length > 0 && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium uppercase tracking-wider bg-rose-500/10 text-rose-300 border border-rose-500/20">
              {issues.length} {issues.length === 1 ? 'Defect' : 'Defects'} Fixed
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
          <span className="inline-flex items-center gap-1 text-rose-400">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span> -{originalLines.length} lines
          </span>
          <span className="inline-flex items-center gap-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span> +{replacementLines.length} lines
          </span>
        </div>
      </div>

      {/* Explanation Banner */}
      {patch.explanation && (
        <div className="px-4 py-2.5 bg-emerald-950/20 border-b border-emerald-900/30 flex items-start gap-2.5 text-xs text-emerald-300">
          <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-emerald-200">Autonomous Reasoning: </span>
            {patch.explanation}
          </div>
        </div>
      )}

      {/* Side-by-Side Diff Container */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
        {/* Left: Original Faulty Code */}
        <div className="flex flex-col bg-slate-950/90">
          <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-rose-400/90 bg-rose-950/20 border-b border-slate-800/80 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
              Original Broken Code
            </span>
            <span className="text-[10px] font-mono text-rose-300/60">BEFORE</span>
          </div>

          <div className="p-4 font-mono text-xs overflow-x-auto leading-relaxed max-h-[380px] scrollbar-thin">
            {originalLines.length === 0 || patch.original_snippet === '' ? (
              <p className="text-slate-500 italic py-2">No preceding code snippet.</p>
            ) : (
              originalLines.map((line, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 py-0.5 px-2 -mx-2 rounded bg-rose-950/30 hover:bg-rose-950/40 text-rose-200"
                >
                  <span className="select-none text-slate-600 w-6 text-right shrink-0">
                    {idx + 1}
                  </span>
                  <span className="select-none text-rose-500/80 font-bold shrink-0">-</span>
                  <span className="whitespace-pre flex-1 text-rose-200">{line || ' '}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Healed AST-Validated Patch */}
        <div className="flex flex-col bg-slate-950/90">
          <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-emerald-400/90 bg-emerald-950/20 border-b border-slate-800/80 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Healed AST-Safe Patch
            </span>
            <span className="text-[10px] font-mono text-emerald-300/60">AFTER</span>
          </div>

          <div className="p-4 font-mono text-xs overflow-x-auto leading-relaxed max-h-[380px] scrollbar-thin">
            {replacementLines.length === 0 || patch.replacement_snippet === '' ? (
              <p className="text-slate-500 italic py-2">No replacement snippet.</p>
            ) : (
              replacementLines.map((line, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 py-0.5 px-2 -mx-2 rounded bg-emerald-950/30 hover:bg-emerald-950/40 text-emerald-200"
                >
                  <span className="select-none text-slate-600 w-6 text-right shrink-0">
                    {idx + 1}
                  </span>
                  <span className="select-none text-emerald-400 font-bold shrink-0">+</span>
                  <span className="whitespace-pre flex-1 text-emerald-100">{line || ' '}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
