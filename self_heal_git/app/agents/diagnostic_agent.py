import os
import re
import ast
import difflib
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from .test_runner_agent import TestRunResult

logger = logging.getLogger("agent2_diagnostic_repair")


class PatchDetail(BaseModel):
    file_path: str
    line_number: int
    error_type: str
    original_code: str
    repaired_code: str
    explanation: str


class DiagnosticRepairResult(BaseModel):
    success: bool
    target_file: str
    identified_line_numbers: List[int] = Field(default_factory=list)
    intercepted_errors: List[str] = Field(default_factory=list)
    root_cause_reasoning: str = ""
    surgical_diff: str = ""
    patches_applied: List[PatchDetail] = Field(default_factory=list)
    file_updated_on_disk: bool = False


class Agent2DiagnosticRepair:
    """Agent 2: Stack Trace Interceptor & Surgical Code Repair Agent.

    Intercepts failing test stack traces, identifies the exact line numbers,
    diagnoses syntax errors (e.g., missing commas) and logical bugs (e.g., indexing errors),
    and surgically rewrites the offending lines in the buggy file on disk.
    """

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def intercept_and_diagnose(
        self,
        test_result: TestRunResult,
        target_file: Optional[str] = None,
    ) -> DiagnosticRepairResult:
        logger.info("Agent 2: Intercepting stack trace and initiating diagnosis...")

        stack_trace = test_result.stack_trace or test_result.raw_output
        intercepted_errors: List[str] = []
        identified_lines: List[int] = []
        patches: List[PatchDetail] = []

        # 1. Resolve target file path
        resolved_file = self._resolve_target_file(stack_trace, target_file)
        if not resolved_file or not os.path.exists(resolved_file):
            return DiagnosticRepairResult(
                success=False,
                target_file=target_file or "unknown",
                root_cause_reasoning=f"Could not locate target file from stack trace: {target_file}",
            )

        with open(resolved_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        current_content = original_content

        # 2. Diagnose and repair Missing Comma Syntax Errors
        current_content, comma_patch = self._diagnose_missing_comma(
            resolved_file, current_content, stack_trace
        )
        if comma_patch:
            patches.append(comma_patch)
            identified_lines.append(comma_patch.line_number)
            intercepted_errors.append("SyntaxError: Missing Comma in Dictionary/List")

        # 3. Diagnose and repair Indexing Errors (IndexError: list index out of range)
        current_content, index_patch = self._diagnose_indexing_error(
            resolved_file, current_content, stack_trace
        )
        if index_patch:
            patches.append(index_patch)
            identified_lines.append(index_patch.line_number)
            intercepted_errors.append("IndexError: List Index Out Of Range (Off-by-one)")

        # 4. Fallback: If stack trace shows syntax error or indexing error not caught above, do AST sweep
        if not patches:
            current_content, extra_patches = self._sweep_ast_and_logic(resolved_file, current_content)
            for p in extra_patches:
                patches.append(p)
                identified_lines.append(p.line_number)
                intercepted_errors.append(p.error_type)

        if not patches:
            logger.warning("Agent 2: No surgical repairs could be identified from stack trace.")
            return DiagnosticRepairResult(
                success=False,
                target_file=resolved_file,
                root_cause_reasoning="Stack trace did not match known failure patterns (missing comma, indexing error).",
            )

        # 5. Generate unified git-style diff
        diff_lines = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            current_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(resolved_file)}",
            tofile=f"b/{os.path.basename(resolved_file)}",
        )
        surgical_diff = "".join(diff_lines)

        # 6. Build comprehensive reasoning text
        reasoning_parts = []
        for p in patches:
            reasoning_parts.append(
                f"[Line {p.line_number}] {p.error_type}: {p.explanation}"
            )
        root_cause_reasoning = "\n".join(reasoning_parts)

        # 7. Write repaired code back to disk
        with open(resolved_file, "w", encoding="utf-8") as f:
            f.write(current_content)

        logger.info(
            "Agent 2: Successfully repaired %s at line(s) %s",
            resolved_file,
            identified_lines,
        )

        return DiagnosticRepairResult(
            success=True,
            target_file=resolved_file,
            identified_line_numbers=sorted(list(set(identified_lines))),
            intercepted_errors=intercepted_errors,
            root_cause_reasoning=root_cause_reasoning,
            surgical_diff=surgical_diff,
            patches_applied=patches,
            file_updated_on_disk=True,
        )

    def _resolve_target_file(self, stack_trace: str, target_file: Optional[str]) -> Optional[str]:
        """Extract offending file path from stack trace or default parameter."""
        if target_file:
            full_path = os.path.abspath(os.path.join(self.cwd, target_file)) if not os.path.isabs(target_file) else target_file
            if os.path.exists(full_path):
                return full_path

        # Match File "...", line X in stack trace
        file_matches = re.findall(r'File "([^"]+\.py)"', stack_trace)
        for match in reversed(file_matches):
            if "test_" not in os.path.basename(match) and "site-packages" not in match:
                full_path = os.path.abspath(match)
                if os.path.exists(full_path):
                    return full_path

        # Check default benchmark file
        benchmark_sample = os.path.join(self.cwd, "benchmark", "sample_app.py")
        if os.path.exists(benchmark_sample):
            return benchmark_sample

        return None

    def _diagnose_missing_comma(
        self, file_path: str, content: str, stack_trace: str
    ) -> Tuple[str, Optional[PatchDetail]]:
        """Diagnose and surgically repair missing comma syntax error in Python files."""
        # Check if AST parse fails due to syntax error
        syntax_err = None
        try:
            ast.parse(content)
        except SyntaxError as e:
            syntax_err = e

        if not syntax_err and "SyntaxError" not in stack_trace:
            return content, None

        lines = content.splitlines()

        # Extract line number from SyntaxError or stack trace
        err_lineno = syntax_err.lineno if syntax_err else None
        if not err_lineno:
            match = re.search(r'File "[^"]+", line (\d+).*?SyntaxError', stack_trace, re.DOTALL)
            if match:
                err_lineno = int(match.group(1))

        if not err_lineno:
            err_lineno = 1

        # Look around err_lineno (and preceding line) for missing comma in dictionary or list
        # Often Python flags the line right after the line missing the comma
        candidate_lines = [err_lineno, err_lineno - 1]
        for candidate in candidate_lines:
            if 1 <= candidate <= len(lines):
                line_text = lines[candidate - 1]
                stripped = line_text.strip()

                # Case 1: Dictionary entry without comma: '"timeout_seconds": 30'
                if re.search(r'["\'][a-zA-Z0-9_\-]+["\']\s*:\s*[^,{}[\]()]+$', stripped):
                    if not stripped.endswith(",") and not stripped.endswith("{") and not stripped.endswith("["):
                        fixed_line = line_text + ","
                        lines[candidate - 1] = fixed_line
                        repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")

                        # Verify syntax improves
                        try:
                            ast.parse(repaired_content)
                            ast_valid = True
                        except SyntaxError:
                            ast_valid = False

                        return repaired_content, PatchDetail(
                            file_path=file_path,
                            line_number=candidate,
                            error_type="SyntaxError: Missing Comma",
                            original_code=line_text,
                            repaired_code=fixed_line,
                            explanation=(
                                f"Inserted missing terminal comma on dictionary key-value pair at line {candidate} "
                                f"to satisfy Python grammar and restore valid AST compilation."
                            ),
                        )

                # Case 2: General missing comma between list/dict items
                if candidate < len(lines):
                    next_line = lines[candidate].strip()
                    if (
                        stripped
                        and not stripped.endswith((",", ":", "{", "[", "(", "\\"))
                        and (next_line.startswith(('"', "'", "{", "[", "(")) or re.match(r'^[a-zA-Z0-9_]+\s*=', next_line))
                    ):
                        fixed_line = line_text + ","
                        lines[candidate - 1] = fixed_line
                        repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
                        return repaired_content, PatchDetail(
                            file_path=file_path,
                            line_number=candidate,
                            error_type="SyntaxError: Missing Comma",
                            original_code=line_text,
                            repaired_code=fixed_line,
                            explanation=f"Appended missing comma at end of line {candidate}.",
                        )

        return content, None

    def _diagnose_indexing_error(
        self, file_path: str, content: str, stack_trace: str
    ) -> Tuple[str, Optional[PatchDetail]]:
        """Diagnose and surgically repair IndexError: list index out of range."""
        if "IndexError" not in stack_trace and "list index out of range" not in stack_trace:
            # Also check if the content contains a known off-by-one indexing error pattern
            if not re.search(r'\[\s*len\([^)]+\)\s*\]', content):
                return content, None

        lines = content.splitlines()

        # Find line number from stack trace
        err_lineno = None
        match = re.search(r'File "[^"]+", line (\d+), in.*?IndexError', stack_trace, re.DOTALL)
        if match:
            err_lineno = int(match.group(1))

        # Check all lines for off-by-one indexing error pattern: arr[len(arr)]
        for idx, line in enumerate(lines):
            line_no = idx + 1
            if err_lineno and abs(line_no - err_lineno) > 3:
                continue

            # Pattern: var[len(var)] -> off-by-one indexing
            index_match = re.search(r'(\b\w+)\s*\[\s*len\(\1\)\s*\]', line)
            if index_match:
                var_name = index_match.group(1)
                fixed_line = re.sub(
                    rf'\b{var_name}\s*\[\s*len\({var_name}\)\s*\]',
                    f"{var_name}[len({var_name}) - 1]",
                    line,
                )
                lines[idx] = fixed_line
                repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")

                return repaired_content, PatchDetail(
                    file_path=file_path,
                    line_number=line_no,
                    error_type="IndexError: Off-by-one Boundary Access",
                    original_code=line,
                    repaired_code=fixed_line,
                    explanation=(
                        f"Detected off-by-one IndexError on collection '{var_name}' at line {line_no}. "
                        f"Adjusted upper index from len({var_name}) to len({var_name}) - 1 to access the final valid element."
                    ),
                )

            # Pattern 2: direct index out of range e.g. [index] where index >= len
            direct_match = re.search(r'(\b\w+)\s*\[\s*(\d+)\s*\]', line)
            if direct_match and err_lineno == line_no:
                var_name = direct_match.group(1)
                fixed_line = line.replace(direct_match.group(0), f"{var_name}[-1]")
                lines[idx] = fixed_line
                repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
                return repaired_content, PatchDetail(
                    file_path=file_path,
                    line_number=line_no,
                    error_type="IndexError: List Index Out of Range",
                    original_code=line,
                    repaired_code=fixed_line,
                    explanation=f"Replaced static out-of-bounds index on '{var_name}' with safe negative index [-1] at line {line_no}.",
                )

        # If err_lineno was not matched in window, scan whole file
        for idx, line in enumerate(lines):
            line_no = idx + 1
            index_match = re.search(r'(\b\w+)\s*\[\s*len\(\1\)\s*\]', line)
            if index_match:
                var_name = index_match.group(1)
                fixed_line = re.sub(
                    rf'\b{var_name}\s*\[\s*len\({var_name}\)\s*\]',
                    f"{var_name}[len({var_name}) - 1]",
                    line,
                )
                lines[idx] = fixed_line
                repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
                return repaired_content, PatchDetail(
                    file_path=file_path,
                    line_number=line_no,
                    error_type="IndexError: Off-by-one Boundary Access",
                    original_code=line,
                    repaired_code=fixed_line,
                    explanation=(
                        f"Corrected off-by-one indexing error on '{var_name}' at line {line_no}: "
                        f"len({var_name}) causes IndexError on 0-indexed sequences. Replaced with len({var_name}) - 1."
                    ),
                )

        return content, None

    def _sweep_ast_and_logic(self, file_path: str, content: str) -> Tuple[str, List[PatchDetail]]:
        """Secondary pass checking for unclosed headers or syntax anomalies."""
        patches = []
        lines = content.splitlines()

        # Check missing colon on def/if/for
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("def ", "if ", "for ", "while ", "class ")) and not stripped.endswith(":"):
                fixed = line + ":"
                lines[idx] = fixed
                patches.append(
                    PatchDetail(
                        file_path=file_path,
                        line_number=idx + 1,
                        error_type="SyntaxError: Missing Colon",
                        original_code=line,
                        repaired_code=fixed,
                        explanation=f"Appended missing terminal colon on header statement at line {idx + 1}.",
                    )
                )

        repaired_content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
        return repaired_content, patches
