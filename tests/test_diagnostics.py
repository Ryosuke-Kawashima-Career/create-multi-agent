from __future__ import annotations

from hirenest_support.diagnostics import recommend_diagnostics


def test_diagnostics_returns_candidate_communication_evidence_gaps() -> None:
    diagnostics = recommend_diagnostics("Apex Robotics interview invitation email fails.")

    assert diagnostics["category"] == "candidate_communication"
    assert "Example candidate IDs" in diagnostics["evidence_to_collect"]
    assert any("all candidates" in question for question in diagnostics["clarification_questions"])


def test_diagnostics_returns_candidate_import_evidence_gaps() -> None:
    diagnostics = recommend_diagnostics("Evergreen Retail CSV import missing candidate data.")

    assert diagnostics["category"] == "candidate_import"
    assert "CSV file name and import job ID" in diagnostics["evidence_to_collect"]
    assert diagnostics["customer_safe_next_steps"]
