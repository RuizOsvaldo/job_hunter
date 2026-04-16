"""Tests for role_type classification."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import detect_role_type


def test_analyst_titles():
    assert detect_role_type("Data Analyst") == "analyst"
    assert detect_role_type("Senior Business Analyst") == "analyst"
    assert detect_role_type("Business Intelligence Developer") == "analyst"
    assert detect_role_type("Reporting Specialist") == "analyst"
    assert detect_role_type("BI Engineer") == "analyst"
    assert detect_role_type("Data Scientist") == "analyst"
    assert detect_role_type("Analytics Manager") == "analyst"


def test_pm_titles():
    assert detect_role_type("Program Manager") == "pm"
    assert detect_role_type("Technical Program Manager") == "pm"
    assert detect_role_type("Senior Project Manager") == "pm"
    assert detect_role_type("TPM III") == "pm"


def test_ambiguous_prefers_analyst():
    assert detect_role_type("Senior Data Program Manager") == "analyst"
    assert detect_role_type("Analytics Program Manager") == "analyst"


def test_neither_defaults_to_analyst():
    assert detect_role_type("") == "analyst"
    assert detect_role_type("Project Coordinator") == "analyst"
    assert detect_role_type("Software Engineer") == "analyst"
