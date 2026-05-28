"""Safe proof-of-concept helpers for native AI/CDR text editing.

This package is intentionally isolated from the production label renderer.
Workers operate on copied files in output/native_edit_poc only.
"""

from .diagnostics import detect_coreldraw, detect_illustrator, detect_preview_tools, run_diagnostics
from .job_runner import run_native_edit_poc, run_native_edit_poc_for_template

__all__ = [
    "detect_coreldraw",
    "detect_illustrator",
    "detect_preview_tools",
    "run_diagnostics",
    "run_native_edit_poc",
    "run_native_edit_poc_for_template",
]
