"""Paths and defaults for the daily reporting job."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "report.txt"
DEFAULT_DATE = "2026-03-03"
FIELD_SEPARATOR = "|"
