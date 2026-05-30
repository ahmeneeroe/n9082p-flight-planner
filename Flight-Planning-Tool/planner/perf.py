"""Bridge to the N9082P performance calculator.

The calculator lives in the sibling Performance/ project (package ``src``). In the
Lambda bundle it is copied alongside this package as ``perf_engine`` (see deploy/).
Try the bundled name first, then fall back to the local dev path.
"""
import os
import sys

try:
    from perf_engine.calculator import N9082P  # bundled in Lambda
except ImportError:
    _PERF_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Performance"))
    if _PERF_DIR not in sys.path:
        sys.path.insert(0, _PERF_DIR)
    from src.calculator import N9082P  # local development

__all__ = ["N9082P"]
