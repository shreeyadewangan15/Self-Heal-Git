import os
import sys
import time
import threading
import logging
from typing import Optional, Callable

from .agents.orchestrator import ThreeAgentOrchestrator, VisualDiagnosticTrace

logger = logging.getLogger("event_driven_watcher")

_WATCHER_THREAD: Optional[threading.Thread] = None
_WATCHER_RUNNING = False
_LATEST_TRACE: Optional[VisualDiagnosticTrace] = None


def get_latest_trace() -> Optional[VisualDiagnosticTrace]:
    """Retrieve the most recent 3-Agent diagnostic trace."""
    global _LATEST_TRACE
    return _LATEST_TRACE


def set_latest_trace(trace: VisualDiagnosticTrace):
    """Store the most recent 3-Agent diagnostic trace."""
    global _LATEST_TRACE
    _LATEST_TRACE = trace


def run_healing_pipeline(test_target: Optional[str] = None, target_file: Optional[str] = None) -> VisualDiagnosticTrace:
    """Execute the 3-Agent self-healing pipeline and store the trace."""
    orchestrator = ThreeAgentOrchestrator()
    if not test_target:
        trace = orchestrator.run_benchmark()
    else:
        trace = orchestrator.execute_pipeline(test_target=test_target, target_file=target_file)
    set_latest_trace(trace)
    return trace


def start_event_driven_watcher(watch_dir: Optional[str] = None):
    """Start event-driven local development file watcher in a background daemon thread."""
    global _WATCHER_THREAD, _WATCHER_RUNNING
    if _WATCHER_RUNNING or os.getenv("TESTING", "").lower() in ("true", "1"):
        return

    _WATCHER_RUNNING = True
    real_file = os.path.realpath(__file__)
    base_dir = watch_dir or os.path.dirname(os.path.dirname(real_file))
    target_dir = os.path.join(base_dir, "benchmark")

    def _watch_loop():
        logger.info("Event-driven watcher active on: %s", target_dir)
        try:
            from watchfiles import watch
            for changes in watch(target_dir):
                if not _WATCHER_RUNNING:
                    break
                for change_type, path in changes:
                    if path.endswith("sample_app.py") and not path.endswith("test_sample_app.py"):
                        logger.info("Event-driven watcher: Detected change in %s. Triggering Agent 1...", path)
                        test_target = os.path.join(target_dir, "test_sample_app.py")
                        run_healing_pipeline(test_target=test_target, target_file=path)
        except Exception as e:
            logger.warning("Event-driven watcher stopped or watchfiles error: %s", e)

    _WATCHER_THREAD = threading.Thread(target=_watch_loop, daemon=True)
    _WATCHER_THREAD.start()


def stop_event_driven_watcher():
    """Stop the background watcher."""
    global _WATCHER_RUNNING
    _WATCHER_RUNNING = False
