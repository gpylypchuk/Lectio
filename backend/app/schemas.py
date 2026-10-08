from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisRequest(BaseModel):
    # Stripping first means padding cannot sneak a short text past min_length.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=500, max_length=100_000, description="Full text of the paper.")


# Contract with the LLM. Its JSON schema becomes the tool input schema, so descriptions are
# instructions. A comment, not a docstring, because Pydantic would copy a docstring into the schema.
class PaperSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Nullable but required, so the model has to state explicitly that the title is missing.
    title: str | None = Field(
        description=(
            "Paper title exactly as written in the text, or null if the text does not include it."
        )
    )
    tldr: str = Field(
        max_length=300, description="One or two sentences a non-specialist can follow."
    )
    study_type: Literal["empirical", "theoretical", "review"] = Field(
        description=(
            "empirical: collects or analyzes data. theoretical: models or proofs without new data. "
            "review: summarizes other work."
        )
    )
    key_findings: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Main findings stated in the text, most important first.",
    )
    limitations: list[str] = Field(
        max_length=5,
        description=(
            "Limitations stated in the text. Empty list if the text mentions none. "
            "Do not invent any."
        ),
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "How well the text supports this summary. Use high only if the title is present "
            "and there are at least two key findings."
        )
    )

    @model_validator(mode="after")
    def high_confidence_needs_evidence(self) -> Self:
        if self.confidence == "high" and (self.title is None or len(self.key_findings) < 2):
            # Fed back to the model on retry, so it says how to fix the output.
            raise ValueError(
                "confidence cannot be 'high' when title is null or key_findings has fewer "
                "than 2 items. Lower confidence to 'medium' or 'low'."
            )
        return self


class AnalysisResult(BaseModel):
    summary: PaperSummary
    model: str
