from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas import AnalysisRequest, PaperSummary


def summary_data(**overrides: Any) -> dict[str, Any]:
    # A dict, because that is how the LLM tool input arrives.
    data: dict[str, Any] = {
        "title": "Sleep and Memory Consolidation in Adults",
        "tldr": "Adults who slept after learning remembered more the next day.",
        "study_type": "empirical",
        "key_findings": ["Sleep improved recall by 20%", "The effect was larger for word lists"],
        "limitations": [],
        "confidence": "high",
    }
    data.update(overrides)
    return data


def test_high_confidence_with_title_and_two_findings_is_valid() -> None:
    summary = PaperSummary.model_validate(summary_data())
    assert summary.confidence == "high"
    assert summary.limitations == []


@pytest.mark.parametrize(
    "overrides",
    [{"title": None}, {"key_findings": ["Sleep improved recall by 20%"]}],
    ids=["no_title", "one_finding"],
)
def test_high_confidence_without_evidence_is_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="confidence cannot be 'high'"):
        PaperSummary.model_validate(summary_data(**overrides))


@pytest.mark.parametrize("confidence", ["low", "medium"])
def test_lower_confidence_without_evidence_is_valid(confidence: str) -> None:
    data = summary_data(
        title=None, key_findings=["Sleep improved recall by 20%"], confidence=confidence
    )
    summary = PaperSummary.model_validate(data)
    assert summary.title is None


@pytest.mark.parametrize("length", [500, 100_000])
def test_text_within_limits_is_valid(length: int) -> None:
    assert len(AnalysisRequest(text="a" * length).text) == length


@pytest.mark.parametrize("length", [499, 100_001])
def test_text_outside_limits_is_rejected(length: int) -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest(text="a" * length)


def test_surrounding_whitespace_does_not_count_towards_min_length() -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest(text=" " * 300 + "a" * 300)
