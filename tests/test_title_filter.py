"""Tests for the scorer title pre-filter."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scorer import _title_passes_filter


def test_pm_titles_pass():
    assert _title_passes_filter("Program Manager")
    assert _title_passes_filter("Senior Program Manager")
    assert _title_passes_filter("Technical Program Manager")
    assert _title_passes_filter("Project Manager")
    assert _title_passes_filter("TPM III")


def test_analyst_titles_still_pass():
    assert _title_passes_filter("Data Analyst")
    assert _title_passes_filter("Business Intelligence Analyst")


def test_blocklist_still_blocks():
    assert not _title_passes_filter("Data Entry Specialist")
    assert not _title_passes_filter("Warehouse Associate")
    assert not _title_passes_filter("Software Engineer")
