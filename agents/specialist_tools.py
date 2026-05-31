from __future__ import annotations

import re
from typing import Any


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _parse_amount_yen(text: str) -> int | None:
    normalized = text.replace(",", "").replace("，", "")
    man_match = re.search(r"(\d+(?:\.\d+)?)\s*万", normalized)
    if man_match:
        return int(float(man_match.group(1)) * 10000)
    yen_match = re.search(r"(\d{4,})\s*円?", normalized)
    if yen_match:
        return int(yen_match.group(1))
    return None


def estimate_mobility_load(
    origin: str,
    destination: str,
    transport: str,
    duration: str,
    access_notes: str,
) -> dict[str, Any]:
    """Estimate travel fatigue from transport, transfers, duration, and access notes."""
    joined = " ".join([origin, destination, transport, duration, access_notes])
    signals: list[str] = []
    score = 7

    if _contains_any(joined, ["徒歩", "walk", "登山", "階段", "坂", "乗換", "transfer"]):
        score -= 2
        signals.append("徒歩・坂道・乗換などの負荷が見える")
    if _contains_any(joined, ["バス", "bus", "本数", "少ない", "要予約"]):
        score -= 1
        signals.append("バスや本数制約がある")
    if _contains_any(joined, ["直通", "乗換なし", "駅近", "送迎", "シャトル"]):
        score += 2
        signals.append("直通・駅近・送迎など移動負荷を下げる要素がある")
    if _contains_any(duration, ["日帰り", "1日", "一日"]):
        score -= 1
        signals.append("滞在時間が短く、移動負荷の影響が大きい")

    score = max(1, min(10, score))
    if score >= 8:
        load_level = "low"
    elif score >= 5:
        load_level = "medium"
    else:
        load_level = "high"

    return {
        "mobility_score": score,
        "load_level": load_level,
        "signals": signals or ["移動負荷を判断する材料が少ない"],
        "summary": f"{origin} から {destination} への移動負荷は {load_level} と推定します。",
    }


def analyze_budget_fit(
    budget: str,
    estimated_cost: str,
    companions: str,
    destination: str,
) -> dict[str, Any]:
    """Compare a user's budget with the candidate's estimated cost text."""
    budget_yen = _parse_amount_yen(budget)
    cost_yen = _parse_amount_yen(estimated_cost)
    concerns: list[str] = []

    if budget_yen is None or cost_yen is None:
        return {
            "fit": "unknown",
            "budget_yen": budget_yen,
            "estimated_cost_yen": cost_yen,
            "margin_yen": None,
            "concerns": ["予算または概算費用を数値として読み取れない"],
            "summary": f"{destination} の費用適合は追加確認が必要です。",
        }

    margin = budget_yen - cost_yen
    ratio = cost_yen / budget_yen if budget_yen else 1.0
    if ratio <= 0.75:
        fit = "comfortable"
    elif ratio <= 0.95:
        fit = "tight"
        concerns.append("予算内だが余裕は小さい")
    else:
        fit = "over_budget"
        concerns.append("概算費用が予算を超える可能性が高い")

    if _contains_any(companions, ["子ども", "家族", "family", "高齢", "elderly"]):
        concerns.append("同行者の事情により追加費用や休憩費が発生しやすい")

    return {
        "fit": fit,
        "budget_yen": budget_yen,
        "estimated_cost_yen": cost_yen,
        "margin_yen": margin,
        "concerns": concerns,
        "summary": f"{destination} は予算に対して {fit} と判定します。",
    }


def extract_trip_quality_signals(
    user_preferences: str,
    constraints: str,
    destination_summary: str,
    recommended_spots: str,
    risks: str,
) -> dict[str, Any]:
    """Extract positive and negative scoring signals from candidate research notes."""
    positive_keywords = {
        "quiet": ["静か", "落ち着", "自然", "里山", "隠れ家"],
        "food": ["食", "海鮮", "郷土料理", "カフェ", "市場"],
        "onsen": ["温泉", "露天", "湯"],
        "culture": ["歴史", "文化", "美術", "工芸", "町並み"],
        "scenery": ["絶景", "海", "山", "湖", "夕日", "星空"],
    }
    risk_keywords = {
        "crowding": ["混雑", "行列", "繁忙", "満席"],
        "weather": ["雨", "雪", "台風", "荒天", "運休"],
        "booking": ["予約", "満室", "要確認", "休業"],
        "access": ["本数", "乗換", "徒歩", "遅延"],
    }

    source = " ".join([user_preferences, constraints, destination_summary, recommended_spots])
    risk_source = " ".join([constraints, risks])
    positives = [
        label for label, keywords in positive_keywords.items() if _contains_any(source, keywords)
    ]
    negatives = [
        label for label, keywords in risk_keywords.items() if _contains_any(risk_source, keywords)
    ]
    score_hint = max(1, min(10, 6 + len(positives) - len(negatives)))

    return {
        "positive_signals": positives,
        "negative_signals": negatives,
        "score_hint": score_hint,
        "summary": "候補の魅力と懸念を scoring signal として抽出しました。",
    }
