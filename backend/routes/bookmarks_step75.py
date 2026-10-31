"""Step 75A: case-scoped investigator bookmarks and findings.

Append-only entries. Source references are investigator assertions, not automatic
proof of evidence validity. No evidence files or original hashes are modified.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from backend.auth import login_required
from backend.models.case import Case
from backend.services.database import SessionLocal

bookmarks_api = Blueprint("bookmarks_api", __name__)

CATEGORIES = {"Observation", "Finding", "Question", "Follow-up"}
SOURCE_TYPES = {"evidence", "telemetry", "image_sample", "timeline", "case"}
TIME_BASES = {"boot_relative", "utc", "local_unspecified", "not_applicable"}

def _table(session):
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS investigator_findings_step75 (
            finding_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            case_id INT NOT NULL,
            category VARCHAR(24) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT NOT NULL,
            source_type VARCHAR(24) NOT NULL,
            source_reference VARCHAR(255) NOT NULL,
            time_basis VARCHAR(24) NOT NULL,
            time_value VARCHAR(80) NULL,
            created_utc VARCHAR(40) NOT NULL,
            INDEX ix_findings_case (case_id, finding_id)
        )
    """))

def _serialize(row):
    return dict(row)

@bookmarks_api.get("/cases/<int:case_id>/findings")
@login_required
def list_findings(case_id):
    with SessionLocal() as session:
        if session.get(Case, case_id) is None:
            return jsonify(error="Case not found"), 404
        _table(session)
        rows = session.execute(text("""
            SELECT finding_id, case_id, category, title, description,
                   source_type, source_reference, time_basis, time_value, created_utc
            FROM investigator_findings_step75
            WHERE case_id = :case_id ORDER BY finding_id DESC
        """), {"case_id": case_id}).mappings().all()
        session.commit()
        return jsonify(findings=[_serialize(row) for row in rows]), 200

@bookmarks_api.post("/cases/<int:case_id>/findings")
@login_required
def create_finding(case_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Expected JSON object"), 400
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    category = payload.get("category")
    source_type = payload.get("source_type")
    source_reference = str(payload.get("source_reference") or "").strip()
    time_basis = payload.get("time_basis") or "not_applicable"
    time_value = str(payload.get("time_value") or "").strip()
    if not title or len(title) > 200:
        return jsonify(error="Title must be 1–200 characters"), 400
    if not description or len(description) > 10000:
        return jsonify(error="Description must be 1–10000 characters"), 400
    if category not in CATEGORIES or source_type not in SOURCE_TYPES:
        return jsonify(error="Invalid category or source type"), 400
    if not source_reference or len(source_reference) > 255:
        return jsonify(error="Source reference must be 1–255 characters"), 400
    if time_basis not in TIME_BASES or len(time_value) > 80:
        return jsonify(error="Invalid time reference"), 400
    if time_basis == "not_applicable" and time_value:
        return jsonify(error="Time value requires an explicit time basis"), 400
    if time_basis != "not_applicable" and not time_value:
        return jsonify(error="Time value is required for the selected time basis"), 400
    with SessionLocal() as session:
        if session.get(Case, case_id) is None:
            return jsonify(error="Case not found"), 404
        _table(session)
        params = {
            "case_id": case_id, "category": category, "title": title,
            "description": description, "source_type": source_type,
            "source_reference": source_reference, "time_basis": time_basis,
            "time_value": time_value or None,
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        result = session.execute(text("""
            INSERT INTO investigator_findings_step75
              (case_id, category, title, description, source_type,
               source_reference, time_basis, time_value, created_utc)
            VALUES
              (:case_id, :category, :title, :description, :source_type,
               :source_reference, :time_basis, :time_value, :created_utc)
        """), params)
        finding_id = result.lastrowid
        session.commit()
        return jsonify(finding={**params, "finding_id": finding_id},
                       notice="Investigator-entered finding; source reference not independently verified"), 201
