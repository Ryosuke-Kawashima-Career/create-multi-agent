from __future__ import annotations

import os
from typing import Any

SERVING_CONFIG_ENV = "HIRENEST_AGENT_SEARCH_SERVING_CONFIG"


def search_agent_search(query: str, limit: int = 5) -> dict[str, Any]:
    """Search a Gemini Enterprise Agent Search serving config when configured.

    The local fixture search remains the deterministic fallback for the hands-on lab. Set
    HIRENEST_AGENT_SEARCH_SERVING_CONFIG to a Discovery Engine servingConfig resource to use
    Agent Search backed by Gemini Enterprise / Agent Builder retrieval.
    """
    serving_config = os.getenv(SERVING_CONFIG_ENV, "").strip()
    if not serving_config:
        return {
            "backend": "local_fallback",
            "configured": False,
            "message": f"Set {SERVING_CONFIG_ENV} to enable Gemini Enterprise Agent Search.",
            "results": [],
        }

    try:
        from google.cloud import discoveryengine_v1
    except ImportError as exc:
        return {
            "backend": "local_fallback",
            "configured": True,
            "message": f"google-cloud-discoveryengine is unavailable: {exc}",
            "results": [],
        }

    try:
        client = discoveryengine_v1.SearchServiceClient()
        request = discoveryengine_v1.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=max(1, min(limit, 10)),
        )
        response = client.search(request=request)
        return {
            "backend": "gemini_enterprise_agent_search",
            "configured": True,
            "serving_config": serving_config,
            "results": [_result_to_dict(result) for result in response.results],
        }
    except Exception as exc:
        return {
            "backend": "local_fallback",
            "configured": True,
            "message": f"Agent Search request failed: {type(exc).__name__}: {exc}",
            "results": [],
        }


def _result_to_dict(result: Any) -> dict[str, Any]:
    document = getattr(result, "document", None)
    derived = getattr(document, "derived_struct_data", {}) if document else {}
    struct_data = getattr(document, "struct_data", {}) if document else {}
    return {
        "id": getattr(document, "id", ""),
        "name": getattr(document, "name", ""),
        "score": {key: str(value) for key, value in getattr(result, "model_scores", {}).items()},
        "title": _pick(derived, "title") or _pick(struct_data, "title"),
        "link": _pick(derived, "link") or _pick(struct_data, "uri"),
        "snippet": _snippet(derived) or _pick(struct_data, "summary"),
    }


def _pick(mapping: Any, key: str) -> Any:
    if not mapping:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return getattr(mapping, key, None)


def _snippet(mapping: Any) -> str:
    snippets = _pick(mapping, "snippets")
    if not snippets:
        return ""
    first = snippets[0]
    if isinstance(first, dict):
        return first.get("snippet", "")
    return getattr(first, "snippet", "")
