"""Tests for scorer industry classification."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import scorer

JOB = {"title": "Data Analyst", "company": "Acme", "location": "Remote", "description": "..."}


def _fake(raw):
    return patch.object(scorer, "call_llm", return_value=raw)


def test_tech_parsed():
    with _fake(json.dumps({"score": 8.5, "reasons": ["a", "b"], "industry": "tech"})):
        score, reasons, ind = scorer.score_job(JOB, system_prompt="x")
    assert score == 8.5
    assert reasons == ["a", "b"]
    assert ind == "tech"


def test_non_tech_parsed():
    with _fake(json.dumps({"score": 7.0, "reasons": ["x"], "industry": "non-tech"})):
        _, _, ind = scorer.score_job(JOB, system_prompt="x")
    assert ind == "non-tech"


def test_invalid_industry_raises():
    with _fake(json.dumps({"score": 7.0, "reasons": [], "industry": "software"})):
        with pytest.raises(ValueError, match="invalid industry"):
            scorer.score_job(JOB, system_prompt="x")


def test_missing_industry_raises():
    with _fake(json.dumps({"score": 7.0, "reasons": []})):
        with pytest.raises(ValueError, match="invalid industry"):
            scorer.score_job(JOB, system_prompt="x")
