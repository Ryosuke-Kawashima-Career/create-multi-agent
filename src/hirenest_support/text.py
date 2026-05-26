from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]+", re.IGNORECASE)

SYNONYMS = {
    "candidate": {"applicant", "application", "interview", "recruiting"},
    "applicant": {"candidate", "application", "careers", "job"},
    "interview": {"candidate", "calendar", "schedule", "scorecard", "evaluation"},
    "invitation": {"invite", "email", "candidate_communication", "delivery"},
    "email": {"invite", "invitation", "notification", "delivery"},
    "calendar": {"google", "free-busy", "availability", "schedule", "interview"},
    "availability": {"calendar", "free-busy", "schedule", "interview"},
    "careers": {"job", "application", "form", "applicant", "career-site"},
    "job": {"posting", "careers", "application", "form"},
    "scorecard": {"evaluation", "feedback", "permission", "interviewer"},
    "evaluation": {"scorecard", "feedback", "permission", "interviewer"},
    "permission": {"role", "access", "scorecard", "evaluation"},
    "csv": {"import", "candidate", "mapping", "dedupe", "missing"},
    "import": {"csv", "candidate", "mapping", "dedupe", "missing"},
    "missing": {"import", "csv", "candidate", "field", "data"},
    "dashboard": {"analytics", "reporting", "metrics", "funnel"},
}


def tokens(text: str) -> set[str]:
    normalized = (
        text.lower()
        .replace("候補者", " candidate ")
        .replace("面接", " interview ")
        .replace("招待メール", " invitation email ")
        .replace("空き時間", " availability ")
        .replace("求人", " job ")
        .replace("応募フォーム", " application form ")
        .replace("評価シート", " scorecard ")
        .replace("権限", " permission ")
        .replace("インポート", " import ")
        .replace("欠落", " missing ")
    )
    result = {match.group(0) for match in TOKEN_RE.finditer(normalized)}
    for key, values in SYNONYMS.items():
        if key in result:
            result.update(values)
    return result


def text_from_record(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for value in record.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.append(text_from_record(value))
        else:
            parts.append(str(value))
    return " ".join(parts)


def score_text(query: str, text: str, boosts: Iterable[str] = ()) -> int:
    query_tokens = tokens(query)
    document = text.lower()
    document_tokens = tokens(document)
    score = 0
    for token in query_tokens:
        if token in document_tokens:
            score += 3
        elif token in document:
            score += 1
    for boost in boosts:
        if boost and boost.lower() in document:
            score += 8
    return score


def compact(text: str, max_chars: int = 280) -> str:
    one_line = re.sub(r"\s+", " ", text).strip()
    if len(one_line) <= max_chars:
        return one_line
    return one_line[: max_chars - 3].rstrip() + "..."
