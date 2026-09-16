'use client';

import React, { useState } from 'react';
import { VisualDiagnosticTrace } from '@/lib/types';
import { triggerPipelineBenchmark } from '@/lib/api';
import {
  Play,
  RefreshCw,
  CheckCircle2,
  AlertOctagon,
  Cpu,
  Sparkles,
  FileCode2,
  Terminal,
  Activity,
  Check,
} from 'lucide-react';

interface Props {
  initialTrace?: VisualDiagnosticTrace | null;
}

export default function ThreeAgentDiagnosticTrace({ initialTrace }: Props) {
  const [trace, setTrace] = useState<VisualDiagnosticTrace | null>(initialTrace || null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunBenchmark = async () => {
    setRunning(true);
    setError(null);
    try {
      const data = await triggerPipelineBenchmark();
      setTrace(data);
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to execute 3-Agent benchmark');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Control Banner Card */}
      <div className="p-6 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-slate-900 via-slate-900/90 to-emerald-950/20 shadow-2xl backdrop-blur relative overflow-hidden">
        <div className="absolute -right-16 -top-16 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-mono text-[11px] font-semibold tracking-wider uppercase mb-2">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              Event-Driven 3-Agent Pipeline
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Autonomous Stack Trace Interception & Surgical Healing
            </h2>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
              <strong>Agent 1</strong> executes unit tests $\rightarrow$ <strong>Agent 2</strong> intercepts stack traces, locates line numbers, and rewrites offending lines $\rightarrow$ <strong>Agent 3</strong> re-runs tests to verify a 100% pass rate.
            </p>
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={running}
            id="run-three-agent-pipeline-btn"
            className="flex items-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-xs shadow-xl shadow-emerald-950/60 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {running ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Agents Executing (1 $\rightarrow$ 2 $\rightarrow$ 3)...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-slate-950" />
                <span>Trigger Benchmark (Missing Comma + Index Error)</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertOctagon className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Live Status Summary Header */}
        {trace && (
          <div className="mt-5 pt-4 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3">
              <span
                className={`px-3 py-1 rounded-full font-bold uppercase tracking-wider text-[11px] border ${
                  trace.pipeline_status === 'HEALED'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                }`}
              >
                ● Status: {trace.pipeline_status}
              </span>
              <span className="text-slate-400 font-mono">
                Duration: <strong className="text-white">{trace.total_duration_seconds}s</strong>
              </span>
              <span className="text-slate-400 font-mono">
                Target: <strong className="text-emerald-400 font-mono">{trace.target_file}</strong>
              </span>
            </div>

            {trace.final_verification && (
              <div className="flex items-center gap-2 text-emerald-300 font-semibold font-mono">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>100% Pass Rate ({trace.final_verification.passed_tests}/{trace.final_verification.total_tests} tests verified)</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 3-Agent Visual Diagnostic Trace Stages */}
      {trace && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Visual Diagnostic Trace (Execution Mapping)
            </h3>
            <span className="text-[11px] font-mono text-slate-500">
              {trace.trace_steps.length} sequential steps captured
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {/* STAGE 1: AGENT 1 - TEST EXECUTION & STACK TRACE INTERCEPTION */}
            <div className="p-5 rounded-2xl border border-rose-500/30 bg-slate-900/70 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-rose-500/20 text-rose-400 font-bold font-mono text-xs flex items-center justify-center border border-rose-500/40">
                    1
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">Agent 1: Test Runner / CI Trigger</h4>
                    <p className="text-[11px] text-slate-400">Executed unit test suite on code push</p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 font-mono text-[10px] font-bold border border-rose-500/40 uppercase">
                  TEST FAILURE INTERCEPTED
                </span>
              </div>

              {trace.initial_failure && (
                <div className="space-y-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-rose-400 font-mono">
                      Error: {trace.initial_failure.error_type || 'SyntaxError / IndexError'}
                    </span>
                    <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300 font-mono">
                      Failing test: {trace.initial_failure.failing_tests[0] || 'test_pipeline_configuration_syntax'}
                    </span>
                  </div>

                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-slate-400" />
                      <span>Raw Intercepted Stack Trace:</span>
                    </div>
                    <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-rose-300/90 whitespace-pre overflow-x-auto leading-relaxed scrollbar-thin">
                      {trace.initial_failure.stack_trace || trace.initial_failure.raw_output}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            {/* STAGE 2: AGENT 2 - DIAGNOSTIC REASONING & SURGICAL LINE REWRITE */}
            <div className="p-5 rounded-2xl border border-amber-500/30 bg-slate-900/70 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-amber-500/20 text-amber-300 font-bold font-mono text-xs flex items-center justify-center border border-amber-500/40">
                    2
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">Agent 2: Diagnostic & Surgical Code Repair</h4>
                    <p className="text-[11px] text-slate-400">Identified exact line numbers and rewrote offending code</p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/40 uppercase">
                  SURGICAL PATCH REWRITTEN
                </span>
              </div>

              {trace.repairs.map((repair, idx) => (
                <div key={idx} className="space-y-3 text-xs">
                  {/* Lines & Error Badges */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="bg-amber-500/15 border border-amber-500/30 text-amber-300 font-mono px-2 py-0.5 rounded text-[11px]">
                      Line(s) Identified: {repair.identified_line_numbers.join(', ')}
                    </span>
                    {repair.intercepted_errors.map((errName, errIdx) => (
                      <span key={errIdx} className="bg-slate-800 text-slate-300 font-mono px-2 py-0.5 rounded text-[11px]">
                        {errName}
                      </span>
                    ))}
                  </div>

                  {/* Diagnostic Reasoning */}
                  <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 leading-relaxed font-mono text-[11px] whitespace-pre-wrap">
                    <div className="text-[11px] font-semibold text-amber-400 mb-1 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-amber-400" />
                      <span>Root Cause Reasoning:</span>
                    </div>
                    {repair.root_cause_reasoning}
                  </div>

                  {/* Surgical Diff Viewer */}
                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                      <FileCode2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Offending Lines Rewritten (Unified Surgical Diff):</span>
                    </div>
                    <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-slate-200 whitespace-pre overflow-x-auto leading-relaxed scrollbar-thin">
                      {repair.surgical_diff.split('\n').map((line, lineIdx) => {
                        let colorClass = 'text-slate-400';
                        let bgClass = '';
                        if (line.startsWith('+')) {
                          colorClass = 'text-emerald-300 font-semibold';
                          bgClass = 'bg-emerald-950/30';
                        } else if (line.startsWith('-')) {
                          colorClass = 'text-rose-400 line-through';
                          bgClass = 'bg-rose-950/30';
                        } else if (line.startsWith('@@')) {
                          colorClass = 'text-cyan-400 font-bold';
                        }
                        return (
                          <div key={lineIdx} className={`${colorClass} ${bgClass} px-1 rounded`}>
                            {line || ' '}
                          </div>
                        );
                      })}
                    </pre>
                  </div>
                </div>
              ))}
            </div>

            {/* STAGE 3: AGENT 3 - VERIFICATION & REGRESSION TESTING */}
            <div className="p-5 rounded-2xl border border-emerald-500/30 bg-slate-900/70 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-300 font-bold font-mono text-xs flex items-center justify-center border border-emerald-500/40">
                    3
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">Agent 3: Verification & Regression Agent</h4>
                    <p className="text-[11px] text-slate-400">Re-ran unit test suite against surgically healed file</p>
                  </div>
                </div>
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono text-[10px] font-bold border border-emerald-500/40 uppercase flex items-center gap-1">
                  <Check className="w-3 h-3 text-emerald-400" />
                  100% PASS RATE VERIFIED
                </span>
              </div>

              {trace.final_verification && (
                <div className="space-y-2 text-xs">
                  <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-emerald-300 font-mono text-[11px] flex items-center justify-between">
                    <span>{trace.final_verification.summary}</span>
                    <span className="font-bold text-emerald-400">
                      {trace.final_verification.pass_rate_percent}% PASS
                    </span>
                  </div>

                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-slate-400" />
                      <span>Re-test Execution Output:</span>
                    </div>
                    <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-emerald-300/80 whitespace-pre overflow-x-auto leading-relaxed scrollbar-thin">
                      {trace.final_verification.verification_output}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
