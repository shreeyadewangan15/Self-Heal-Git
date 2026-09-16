import pytest
import sys
import os

# Ensure benchmark directory is accessible for import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def test_pipeline_configuration_syntax():
    """Verify that get_pipeline_configuration returns valid configuration dictionary."""
    from sample_app import get_pipeline_configuration
    cfg = get_pipeline_configuration()
    assert cfg["app_name"] == "AutonomousSelfHeal"
    assert cfg["environment"] == "production"
    assert cfg["timeout_seconds"] == 30
    assert cfg["retry_attempts"] == 3


def test_latest_metric_sample_indexing():
    """Verify that get_latest_metric_sample safely extracts the latest metric without IndexError."""
    from sample_app import get_latest_metric_sample
    samples = [10.2, 24.8, 89.4]
    latest = get_latest_metric_sample(samples)
    assert latest == 89.4
    assert get_latest_metric_sample([]) == 0.0
