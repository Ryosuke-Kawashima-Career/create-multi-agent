from __future__ import annotations

from dataclasses import dataclass

from hirenest_support.loaders import load_csv


@dataclass(frozen=True)
class CaseIntake:
    customer_id: str | None
    customer_name: str | None
    category: str
    impact_scope: str
    initial_urgency: str
    key_signals: list[str]


def parse_case(query: str) -> CaseIntake:
    customer = _find_customer(query)
    category = _detect_category(query)
    signals = _signals(query)
    impact = _impact_scope(query, category)
    urgency = _initial_urgency(query, category, impact)
    return CaseIntake(
        customer_id=customer.get("customer_id") if customer else None,
        customer_name=customer.get("customer_name") if customer else None,
        category=category,
        impact_scope=impact,
        initial_urgency=urgency,
        key_signals=signals,
    )


def _find_customer(query: str) -> dict[str, str] | None:
    lowered = query.lower()
    for account in load_csv("accounts/accounts.csv"):
        if account["customer_name"].lower() in lowered or account["customer_id"].lower() in lowered:
            return account
    return None


def _detect_category(query: str) -> str:
    lowered = query.lower()
    if any(
        word in lowered
        for word in [
            "interview invitation",
            "invite email",
            "email not delivered",
            "candidate email",
            "面接招待",
            "招待メール",
            "メールが届かない",
        ]
    ):
        return "candidate_communication"
    if any(
        word in lowered
        for word in [
            "google calendar",
            "calendar",
            "availability",
            "free/busy",
            "空き時間",
            "カレンダー",
        ]
    ):
        return "calendar_integration"
    if any(
        word in lowered
        for word in [
            "careers site",
            "career page",
            "job page",
            "application form",
            "求人ページ",
            "応募フォーム",
        ]
    ):
        return "careers_site"
    if any(
        word in lowered
        for word in [
            "scorecard",
            "evaluation",
            "feedback form",
            "permission",
            "評価シート",
            "権限",
            "面接官",
        ]
    ):
        return "scorecard_permissions"
    if any(
        word in lowered
        for word in [
            "csv",
            "import",
            "missing candidate",
            "candidate data",
            "duplicate",
            "インポート",
            "候補者データ",
            "欠落",
        ]
    ):
        return "candidate_import"
    if any(word in lowered for word in ["analytics", "dashboard", "reporting", "採用分析"]):
        return "reporting"
    return "general"


def _signals(query: str) -> list[str]:
    lowered = query.lower()
    signals: list[str] = []
    checks = [
        ("candidate-facing impact", ["candidate", "候補者", "applicant"]),
        ("interviews blocked", ["interview blocked", "cannot schedule", "面接が止ま", "面接調整"]),
        ("Premier support", ["premier"]),
        ("external application flow down", ["application form", "応募フォーム", "careers site"]),
        ("Google Calendar integration", ["google calendar", "free/busy", "空き時間"]),
        ("scorecard permission issue", ["scorecard", "evaluation", "評価シート", "permission"]),
        ("CSV import data loss signal", ["csv", "import", "candidate data", "欠落", "duplicate"]),
        (
            "broad workflow impact",
            ["all recruiters", "all jobs", "all candidates", "全求人", "全候補者"],
        ),
        ("business impact", ["business impact", "業務影響", "blocked"]),
    ]
    for label, needles in checks:
        if any(needle in lowered for needle in needles):
            signals.append(label)
    return signals


def _impact_scope(query: str, category: str) -> str:
    lowered = query.lower()
    if any(word in lowered for word in ["all candidates", "all jobs", "全求人", "全候補者"]):
        return "A broad candidate-facing recruiting workflow is affected."
    if any(word in lowered for word in ["business impact", "業務影響", "blocked"]):
        return "A business-critical recruiting workflow is degraded."
    if category == "careers_site":
        return "Candidate application submission may be affected."
    if category == "candidate_import":
        return "Recruiting operations data quality is affected."
    return "Impact scope requires confirmation from the customer."


def _initial_urgency(query: str, category: str, impact: str) -> str:
    lowered = query.lower()
    broad_impact = "broad" in impact.lower() or "business-critical" in impact.lower()
    if "premier" in lowered and broad_impact:
        return "High"
    urgent_categories = {"candidate_communication", "calendar_integration", "careers_site"}
    urgent_signal = "business" in lowered or "業務影響" in lowered or "blocked" in lowered
    if category in urgent_categories and urgent_signal:
        return "High"
    if category == "candidate_import":
        return "Medium"
    return "Medium"
