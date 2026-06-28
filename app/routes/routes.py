import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

main_bp = Blueprint("main", __name__)

AUTH_PROVIDERS = [
    {"id": "google", "label": "Google", "description": "OAuth sign in"},
    {"id": "facebook", "label": "Facebook", "description": "OAuth sign in"},
    {"id": "github", "label": "GitHub", "description": "OAuth sign in"},
    {"id": "sms", "label": "SMS OTP", "description": "Phone verification"},
]

SAVED_QUERIES = [
    "document retention policy",
    "escooter incident response",
    "compliance onboarding checklist",
    "architecture decision records",
    "quarterly vendor review",
    "grant proposal drafts",
]

COLLECTIONS = [
    "Operations Manuals",
    "Risk Assessments",
    "Research Notes",
    "Vendor Contracts",
    "Meeting Archives",
    "Policy Library",
]


def _truncate_text(value: str, limit: int = 220) -> str:
    compact = " ".join((value or "").split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3].rstrip()}..."


def _session_list(key: str) -> List[str]:
    value = session.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _push_session_item(key: str, value: str, limit: int = 12) -> None:
    items = [item for item in _session_list(key) if item != value]
    items.insert(0, value)
    session[key] = items[:limit]
    session.modified = True


def _sample_user(provider: str, flow: str) -> Dict[str, str]:
    provider_name = provider.upper() if provider == "sms" else provider.title()
    return {
        "name": f"{provider_name} User",
        "email": f"{provider}@nats-rag.local",
        "provider": provider_name,
        "flow": flow,
    }


def _extract_records(payload: Any) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if any(key in node for key in ("combined_processed_text", "processed_pages", "title", "source_filename")):
                records.append(node)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return records


def _load_sample_documents() -> List[Dict[str, Any]]:
    sample_path = Path(current_app.root_path) / "skills" / "text_extraction" / "combined_docs.json"
    if not sample_path.exists():
        return []

    try:
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return _extract_records(payload)


def _normalize_result(result: Dict[str, Any], index: int) -> Dict[str, Any]:
    metadata = result.get("metadata") or {}
    title = (
        metadata.get("title")
        or metadata.get("source_filename")
        or result.get("title")
        or result.get("source_filename")
        or f"Document {index}"
    )
    preview_url = metadata.get("url") or metadata.get("thumbnail_url") or result.get("url") or ""
    extension = (metadata.get("file_extension") or result.get("file_extension") or "").lower().lstrip(".")
    snippet = result.get("snippet") or result.get("combined_processed_text") or result.get("document") or ""

    return {
        "id": str(result.get("id") or metadata.get("source_filename") or index),
        "title": title,
        "snippet": _truncate_text(str(snippet), 260),
        "preview_url": preview_url,
        "thumbnail_url": metadata.get("thumbnail_url") or result.get("thumbnail_url") or "",
        "file_extension": extension,
        "source_filename": metadata.get("source_filename") or result.get("source_filename") or title,
        "distance": result.get("distance"),
        "language": metadata.get("language") or result.get("language") or "",
        "total_pages": metadata.get("total_pages") or result.get("total_pages") or "",
    }


def _search_with_fallback(query_text: str, requested_results: int) -> List[Dict[str, Any]]:
    normalized_results: List[Dict[str, Any]] = []

    try:
        from app.services.embeddings_storage import search_documents_by_query

        search_payload = search_documents_by_query(query_text, n_results=requested_results)
        documents = search_payload.get("documents", [])
        metadatas = search_payload.get("metadatas", [])
        ids = search_payload.get("ids", [])
        distances = search_payload.get("distances", [])

        for index, document in enumerate(documents, start=1):
            normalized_results.append(
                _normalize_result(
                    {
                        "id": ids[index - 1] if index - 1 < len(ids) else index,
                        "document": document,
                        "metadata": metadatas[index - 1] if index - 1 < len(metadatas) else {},
                        "distance": distances[index - 1] if index - 1 < len(distances) else None,
                    },
                    index,
                )
            )
    except Exception:
        normalized_results = []

    if normalized_results:
        return normalized_results

    fallback_matches: List[Dict[str, Any]] = []
    query_terms = [term for term in query_text.lower().split() if term]

    for raw_record in _load_sample_documents():
        combined_text = str(raw_record.get("combined_processed_text") or "")
        haystack = combined_text.lower()
        if query_terms and not any(term in haystack for term in query_terms):
            continue

        fallback_matches.append(
            _normalize_result(
                {
                    "id": raw_record.get("source_filename") or raw_record.get("title") or len(fallback_matches) + 1,
                    "title": raw_record.get("title"),
                    "source_filename": raw_record.get("source_filename"),
                    "combined_processed_text": combined_text,
                    "file_extension": raw_record.get("file_extension"),
                    "metadata": raw_record,
                },
                len(fallback_matches) + 1,
            )
        )

        if len(fallback_matches) >= requested_results:
            break

    return fallback_matches


def _build_home_sections() -> List[Dict[str, Any]]:
    recent_documents = _session_list("recent_documents") or [
        "Deployment Readiness Checklist",
        "Vendor Security Assessment",
        "Quarterly Roadmap Review",
        "Drive Ingestion Summary",
        "Embedding Quality Report",
        "Operations SOP",
    ]
    recent_queries = _session_list("recent_queries") or [
        "incident response policy",
        "onboarding flow",
        "escooter recovery plan",
        "pii handling standard",
        "language accessibility",
        "contract obligations",
    ]

    return [
        {"title": "Recent Documents", "items": recent_documents},
        {"title": "Recent Queries", "items": recent_queries},
        {"title": "Saved Queries", "items": SAVED_QUERIES},
        {"title": "Collections", "items": COLLECTIONS},
    ]


def _selected_preview(results: List[Dict[str, Any]], selected_id: str) -> Dict[str, Any]:
    if not results:
        return {}

    for result in results:
        if result["id"] == selected_id:
            return result

    return results[0]


@main_bp.route("/", methods=["GET"])
def index():
    """Home page"""
    return render_template(
        "index.html",
        auth_user=session.get("auth_user"),
        auth_providers=AUTH_PROVIDERS,
        home_sections=_build_home_sections(),
    )


@main_bp.route("/search-result", methods=["GET"])
def search_result():
    query_text = request.args.get("q", "", type=str).strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 15

    results: List[Dict[str, Any]] = []
    total_results = 0
    selected_result: Dict[str, Any] = {}
    has_next_page = False

    if query_text:
        requested_results = (page * per_page) + 1
        fetched_results = _search_with_fallback(query_text, requested_results)
        total_results = len(fetched_results)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        results = fetched_results[start_index:end_index]
        has_next_page = total_results > end_index
        selected_result = _selected_preview(results, request.args.get("selected", "", type=str))

        _push_session_item("recent_queries", query_text)
        for result in results[:5]:
            _push_session_item("recent_documents", result["title"], limit=8)

    return render_template(
        "search_results.html",
        auth_user=session.get("auth_user"),
        auth_providers=AUTH_PROVIDERS,
        query_text=query_text,
        results=results,
        selected_result=selected_result,
        page=page,
        per_page=per_page,
        has_next_page=has_next_page,
    )


@main_bp.route("/auth/<flow>", methods=["GET"])
def auth_entry(flow: str):
    if flow not in {"login", "register"}:
        return redirect(url_for("main.index"))

    return render_template(
        "auth_entry.html",
        auth_user=session.get("auth_user"),
        auth_providers=AUTH_PROVIDERS,
        auth_flow=flow,
    )


@main_bp.route("/auth/provider/<provider>", methods=["GET"])
def auth_provider(provider: str):
    provider_ids = {option["id"] for option in AUTH_PROVIDERS}
    if provider not in provider_ids:
        return redirect(url_for("main.index"))

    flow = request.args.get("flow", "login", type=str)
    session["auth_user"] = _sample_user(provider, flow)
    session.modified = True
    return redirect(url_for("main.profile"))


@main_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("auth_user", None)
    return redirect(url_for("main.index"))


@main_bp.route("/profile", methods=["GET"])
def profile():
    auth_user = session.get("auth_user")
    if not auth_user:
        return redirect(url_for("main.auth_entry", flow="login"))

    return render_template(
        "auth_profile.html",
        auth_user=auth_user,
        auth_providers=AUTH_PROVIDERS,
        home_sections=_build_home_sections(),
    )

@main_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Heroku"""
    return jsonify({"status": "healthy"}), 200


@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Not found"}), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500
