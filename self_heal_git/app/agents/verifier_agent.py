import logging
import time
from typing import Optional
from pydantic import BaseModel

from .test_runner_agent import Agent1TestRunner, TestRunResult

logger = logging.getLogger("agent3_verifier")


class VerificationResult(BaseModel):
    is_verified: bool
    pass_rate_percent: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time_seconds: float
    verification_output: str
    summary: str


class Agent3Verifier:
    """Agent 3: Verification & Regression Agent.

    Re-runs the unit test suite against the surgically healed file.
    Validates that a 100% pass rate is achieved without inducing any regression.
    """

    def __init__(self, cwd: Optional[str] = None):
        self.runner = Agent1TestRunner(cwd=cwd)

    def verify_fix(self, test_target: str) -> VerificationResult:
        logger.info("Agent 3: Initiating verification pass on test target: %s", test_target)
        start_time = time.perf_counter()

        test_result: TestRunResult = self.runner.run_tests(test_target)
        duration = round(time.perf_counter() - start_time, 3)

        total = test_result.total_tests
        passed = test_result.passed_tests
        failed = test_result.failed_tests

        pass_rate = round((passed / total * 100), 1) if total > 0 else (100.0 if test_result.passed else 0.0)
        is_verified = (test_result.passed and pass_rate == 100.0)

        summary = (
            f"Verification PASS: Test suite achieved 100% pass rate ({passed}/{total} passed) in {duration}s."
            if is_verified
            else f"Verification INCOMPLETE: Test suite pass rate is {pass_rate}% ({passed}/{total} passed, {failed} failed)."
        )

        logger.info("Agent 3: %s", summary)

        return VerificationResult(
            is_verified=is_verified,
            pass_rate_percent=pass_rate,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            execution_time_seconds=duration,
            verification_output=test_result.raw_output,
            summary=summary,
        )
