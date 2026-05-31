from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class OptionEvaluation(BaseModel):
    option_id: str
    score: int = Field(ge=1, le=10)
    comment: str
    concerns: list[str] = Field(default_factory=list)


class EvaluationReport(BaseModel):
    agent_name: str
    preferred_option_id: str
    option_evaluations: list[OptionEvaluation]

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_option_maps(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "option_evaluations" in data:
            return data
        scores = data.get("scores_by_option")
        comments = data.get("comments_by_option", {})
        concerns = data.get("concerns_by_option", {})
        if not isinstance(scores, dict):
            return data
        migrated = dict(data)
        migrated["option_evaluations"] = [
            {
                "option_id": option_id,
                "score": score,
                "comment": comments.get(option_id, ""),
                "concerns": concerns.get(option_id, []),
            }
            for option_id, score in scores.items()
        ]
        return migrated

    def score_for(self, option_id: str) -> int | None:
        for evaluation in self.option_evaluations:
            if evaluation.option_id == option_id:
                return evaluation.score
        return None


class EvaluationReports(BaseModel):
    reports: list[EvaluationReport]