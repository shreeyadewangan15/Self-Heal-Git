import os
import sys
import time
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .test_runner_agent import Agent1TestRunner, TestRunResult
from .diagnostic_agent import Agent2DiagnosticRepair, DiagnosticRepairResult, PatchDetail
from .verifier_agent import Agent3Verifier, VerificationResult

logger = logging.getLogger("three_agent_orchestrator")


class AgentStepTrace(BaseModel):
    step_number: int
    agent_name: str
    action: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


class VisualDiagnosticTrace(BaseModel):
    pipeline_status: str  # HEALED, PASS, FAILED
    target_file: str
    test_target: str
    total_iterations: int
    total_duration_seconds: float
    initial_failure: Optional[TestRunResult] = None
    repairs: List[DiagnosticRepairResult] = Field(default_factory=list)
    final_verification: Optional[VerificationResult] = None
    trace_steps: List[AgentStepTrace] = Field(default_factory=list)
    diagnostic_summary: str = ""


class ThreeAgentOrchestrator:
    """Orchestrates the 3-Agent event-driven self-healing development pipeline.

    - Agent 1: Executes unit tests on code changes.
    - Agent 2: Intercepts stack trace, diagnoses coding errors, and rewrites offending lines on disk.
    - Agent 3: Re-runs unit tests to verify 100% pass rate.
    Produces a clean visual diagnostic trace mapping exact failure, reasoning, correction, and verification.
    """

    def __init__(self, cwd: Optional[str] = None):
        real_file = os.path.realpath(__file__)
        self.cwd = cwd or os.path.dirname(os.path.dirname(os.path.dirname(real_file)))
        if self.cwd not in sys.path:
            sys.path.insert(0, self.cwd)
        self.agent1 = Agent1TestRunner(cwd=self.cwd)
        self.agent2 = Agent2DiagnosticRepair(cwd=self.cwd)
        self.agent3 = Agent3Verifier(cwd=self.cwd)

    def execute_pipeline(
        self,
        test_target: str,
        target_file: Optional[str] = None,
        max_iterations: int = 3,
    ) -> VisualDiagnosticTrace:
        """Execute the complete 3-Agent self-healing loop."""
        start_time = time.perf_counter()
        trace_steps: List[AgentStepTrace] = []
        repairs: List[DiagnosticRepairResult] = []

        # -------------------------------------------------------------
        # STEP 1: Agent 1 executes unit tests on code changes
        # -------------------------------------------------------------
        logger.info("Pipeline: Step 1 - Agent 1 executing unit tests...")
        test_result = self.agent1.run_tests(test_target)

        trace_steps.append(
            AgentStepTrace(
                step_number=1,
                agent_name="Agent 1: Test Runner",
                action="Execute Unit Test Suite",
                status="PASSED" if test_result.passed else "FAILED",
                details={
                    "total_tests": test_result.total_tests,
                    "passed_tests": test_result.passed_tests,
                    "failed_tests": test_result.failed_tests,
                    "error_type": test_result.error_type,
                    "failing_tests": test_result.failing_tests,
                    "stack_trace": test_result.stack_trace,
                    "summary": test_result.summary,
                },
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        )

        initial_failure = test_result if not test_result.passed else None

        if test_result.passed:
            total_duration = round(time.perf_counter() - start_time, 3)
            return VisualDiagnosticTrace(
                pipeline_status="PASS",
                target_file=target_file or "unknown",
                test_target=test_target,
                total_iterations=1,
                total_duration_seconds=total_duration,
                initial_failure=None,
                repairs=[],
                final_verification=VerificationResult(
                    is_verified=True,
                    pass_rate_percent=100.0,
                    total_tests=test_result.total_tests,
                    passed_tests=test_result.passed_tests,
                    failed_tests=0,
                    execution_time_seconds=test_result.duration_seconds,
                    verification_output=test_result.raw_output,
                    summary="All unit tests passed cleanly on first run. No repairs required.",
                ),
                trace_steps=trace_steps,
                diagnostic_summary="All tests passed cleanly without defects.",
            )

        # -------------------------------------------------------------
        # ITERATIVE HEALING: Agent 2 diagnoses & repairs, Agent 3 verifies
        # -------------------------------------------------------------
        current_test_result = test_result
        iteration = 0
        final_verification = None

        while not current_test_result.passed and iteration < max_iterations:
            iteration += 1
            step_num = len(trace_steps) + 1

            # --- Agent 2: Intercept stack trace and rewrite offending lines ---
            logger.info("Pipeline: Step 2 - Agent 2 intercepting stack trace (Iter %s)...", iteration)
            repair_result = self.agent2.intercept_and_diagnose(
                test_result=current_test_result,
                target_file=target_file,
            )
            repairs.append(repair_result)

            trace_steps.append(
                AgentStepTrace(
                    step_number=step_num,
                    agent_name="Agent 2: Diagnostic & Code Repair",
                    action=f"Intercept Stack Trace & Surgical Line Rewrite (Iter {iteration})",
                    status="SUCCESS" if repair_result.success else "FAILED",
                    details={
                        "target_file": repair_result.target_file,
                        "identified_line_numbers": repair_result.identified_line_numbers,
                        "intercepted_errors": repair_result.intercepted_errors,
                        "root_cause_reasoning": repair_result.root_cause_reasoning,
                        "surgical_diff": repair_result.surgical_diff,
                        "patches_applied": [p.model_dump() for p in repair_result.patches_applied],
                    },
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            )

            if not repair_result.success:
                logger.warning("Pipeline: Agent 2 could not synthesize a patch.")
                break

            # --- Agent 3: Re-run test suite to verify the fix ---
            step_num = len(trace_steps) + 1
            logger.info("Pipeline: Step 3 - Agent 3 re-running test suite (Iter %s)...", iteration)
            verification = self.agent3.verify_fix(test_target)
            final_verification = verification

            trace_steps.append(
                AgentStepTrace(
                    step_number=step_num,
                    agent_name="Agent 3: Verification & Regression Agent",
                    action=f"Re-run Test Suite Verification (Iter {iteration})",
                    status="VERIFIED_100%" if verification.is_verified else "RETEST_FAILED",
                    details={
                        "is_verified": verification.is_verified,
                        "pass_rate_percent": verification.pass_rate_percent,
                        "passed_tests": verification.passed_tests,
                        "total_tests": verification.total_tests,
                        "execution_time_seconds": verification.execution_time_seconds,
                        "summary": verification.summary,
                    },
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            )

            if verification.is_verified:
                logger.info("Pipeline: Agent 3 verified 100% pass rate! Healing complete.")
                break

            # If still failing, re-run Agent 1 to capture the new error for next iteration
            current_test_result = self.agent1.run_tests(test_target)

        total_duration = round(time.perf_counter() - start_time, 3)
        healed_successfully = final_verification.is_verified if final_verification else False

        diagnostic_summary = (
            f"Autonomous 3-Agent Healing Complete in {total_duration}s across {iteration} iteration(s). "
            f"Agent 1 intercepted test failures -> Agent 2 diagnosed and surgically patched {len(repairs)} issue(s) -> "
            f"Agent 3 verified 100% pass rate ({final_verification.passed_tests if final_verification else 0} passed)."
            if healed_successfully
            else f"Healing incomplete after {iteration} iteration(s)."
        )

        return VisualDiagnosticTrace(
            pipeline_status="HEALED" if healed_successfully else "FAILED",
            target_file=target_file or (repairs[0].target_file if repairs else "unknown"),
            test_target=test_target,
            total_iterations=iteration,
            total_duration_seconds=total_duration,
            initial_failure=initial_failure,
            repairs=repairs,
            final_verification=final_verification,
            trace_steps=trace_steps,
            diagnostic_summary=diagnostic_summary,
        )

    def run_benchmark(self) -> VisualDiagnosticTrace:
        """Run the canonical benchmark: missing comma and indexing error in Python."""
        from benchmark.reset import reset_sample_app

        # 1. Reset target benchmark file to original buggy state
        target_file = reset_sample_app()
        test_target = os.path.join(self.cwd, "benchmark", "test_sample_app.py")

        logger.info("Starting canonical benchmark on %s with tests %s", target_file, test_target)
        return self.execute_pipeline(test_target=test_target, target_file=target_file, max_iterations=3)
