"""Tests for resume_builder bullet rewriting rules."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.resume_builder import _tailor_bullets


JOB = {
    "title": "Senior Data Analyst",
    "company": "Acme Corp",
    "description": "SQL, Python, Tableau, dashboards, KPIs, cross-functional.",
}

ORIGINAL_BULLETS = [
    "Led onboarding for 7 staff, increasing retention 18%.",
    "Built Python ETL pipeline saving $12K annually.",
    "Delivered stakeholder reports to 600+ participants.",
]


def _fake_llm(result_bullets):
    return lambda system, user, max_tokens: json.dumps(result_bullets)


def test_same_count_accepted():
    with patch("src.resume_builder.call_claude", side_effect=_fake_llm(["A", "B", "C"])):
        out = _tailor_bullets(JOB, "Test", ORIGINAL_BULLETS)
    assert out == ["A", "B", "C"]


def test_more_bullets_accepted():
    with patch("src.resume_builder.call_claude", side_effect=_fake_llm(["A", "B", "C", "D"])):
        out = _tailor_bullets(JOB, "Test", ORIGINAL_BULLETS)
    assert len(out) == 4


def test_fewer_bullets_raises():
    with patch("src.resume_builder.call_claude", side_effect=_fake_llm(["A", "B"])):
        with pytest.raises(ValueError, match="dropped bullets"):
            _tailor_bullets(JOB, "Test", ORIGINAL_BULLETS)


def test_unparseable_raises():
    with patch("src.resume_builder.call_claude", side_effect=_fake_llm("not json at all")):
        # side_effect above returns the string unchanged via json.dumps
        pass
    with patch("src.resume_builder.call_claude", return_value="not json at all"):
        with pytest.raises(ValueError, match="unparseable"):
            _tailor_bullets(JOB, "Test", ORIGINAL_BULLETS)
