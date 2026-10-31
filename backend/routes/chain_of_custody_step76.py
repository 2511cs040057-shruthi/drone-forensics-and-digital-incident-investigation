"""Step 76A: append-only, case-scoped custody event journal.

Events are investigator declarations. The server records a separate UTC receipt time.
No original evidence bytes or hashes are changed.
"""
from datetime import datetime, timezone
import re

from flask import Blueprint, jsonify, request
from sqlalchemy import inspect, text
from backend.auth import login_required
from backend.models.case import Case
from backend.services.database import SessionLocal

custody_api = Blueprint("custody_api", __name__)
ACTIONS = {"Acquired", "Received", "Transferred", "Examined", "Stored", "Released", "Verified", "Other"}
SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _table(session):
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS custody_events_step76 (
            event_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            case_id INT NOT NULL,
            evidence_id INT NOT NULL,
            action VARCHAR(24) NOT NULL,
            actor VARCHAR(200) NOT NULL,
            counterparty VARCHAR(200) NULL,
            purpose TEXT NOT NULL,
            storage_location VARCHAR(500) NULL,
            event_time VARCHAR(40) NOT NULL,
            recorded_utc VARCHAR(40) NOT NULL,
            integrity_sha256 CHAR(64) NULL,
            integrity_note VARCHAR(500) NULL,
            provenance VARCHAR(64) NOT NULL,
            INDEX ix_custody_case_evidence (case_id, evidence_id, event_id)
        )
    """))


def _registered_evidence(session, case_id, evidence_id):
    """Locate the existing evidence register, without assuming a table name.

    Only tables with both case_id and evidence_id are considered. If the
    schema is ambiguous or unavailable, fail closed instead of accepting an
    unverified evidence reference.
    """
    inspector = inspect(session.get_bind())
    candidates = []
    for table_name in inspector.get_table_names():
        if table_name == "custody_events_step76":
            continue
        columns = {c["name"] for c in inspector.get_columns(table_name)}
        if {"case_id", "evidence_id"}.issubset(columns):
            candidates.append(table_name)
    if not candidates:
        raise RuntimeError("Evidence register table with case_id/evidence_id not found")
    # Check the exact record across candidate tables. Ambiguity is rejected.
    preparer = session.get_bind().dialect.identifier_preparer
    matches = []
    for table_name in candidates:
        quoted = preparer.quote(table_name)
        exists = session.execute(
            text(f"SELECT 1 FROM {quoted} WHERE case_id=:case_id AND evidence_id=:evidence_id LIMIT 1"),
            {"case_id": case_id, "evidence_id": evidence_id}
        ).first()
        if exists:
            matches.append(table_name)
    if len(matches) > 1:
        raise RuntimeError("Ambiguous evidence reference across register tables")
    return bool(matches)


@custody_api.get("/cases/<int:case_id>/custody")
@login_required
def list_custody(case_id):
    raw_evidence_id = request.args.get("evidence_id")
    evidence_id = None
    if raw_evidence_id is not None:
        try:
            evidence_id = int(raw_evidence_id)
            if evidence_id < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify(error="Invalid evidence_id filter"), 400
    with SessionLocal() as session:
        if session.get(Case, case_id) is None:
            return jsonify(error="Case not found"), 404
        _table(session)
        sql = """SELECT event_id, case_id, evidence_id, action, actor,
                        counterparty, purpose, storage_location, event_time,
                        recorded_utc, integrity_sha256, integrity_note, provenance
                 FROM custody_events_step76 WHERE case_id=:case_id"""
        params = {"case_id": case_id}
        if evidence_id is not None:
            sql += " AND evidence_id=:evidence_id"
            params["evidence_id"] = evidence_id
        sql += " ORDER BY event_id ASC"
        rows = session.execute(text(sql), params).mappings().all()
        session.commit()
        return jsonify(events=[dict(row) for row in rows]), 200


@custody_api.post("/cases/<int:case_id>/custody")
@login_required
def add_custody(case_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400
    try:
        evidence_id = int(data.get("evidence_id"))
        if evidence_id < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify(error="A valid evidence_id is required"), 400
    action = data.get("action")
    actor = str(data.get("actor") or "").strip()
    purpose = str(data.get("purpose") or "").strip()
    counterparty = str(data.get("counterparty") or "").strip()
    location = str(data.get("storage_location") or "").strip()
    event_time = str(data.get("event_time") or "").strip()
    sha256 = str(data.get("integrity_sha256") or "").strip()
    integrity_note = str(data.get("integrity_note") or "").strip()
    if action not in ACTIONS:
        return jsonify(error="Invalid custody action"), 400
    if not actor or len(actor) > 200 or not purpose or len(purpose) > 10000:
        return jsonify(error="Actor and purpose are required and must fit length limits"), 400
    if len(counterparty) > 200 or len(location) > 500 or len(integrity_note) > 500:
        return jsonify(error="A text field exceeds its maximum length"), 400
    # An explicit timezone offset is required; this is a declared event time,
    # not a server-confirmed historical timestamp.
    try:
        declared = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if declared.tzinfo is None or declared.utcoffset() is None:
            raise ValueError()
    except ValueError:
        return jsonify(error="event_time must be ISO 8601 with timezone offset"), 400
    if len(event_time) > 40:
        return jsonify(error="event_time is too long"), 400
    if sha256 and not SHA_RE.fullmatch(sha256):
        return jsonify(error="integrity_sha256 must be 64 hexadecimal characters"), 400
    with SessionLocal() as session:
        if session.get(Case, case_id) is None:
            return jsonify(error="Case not found"), 404
        try:
            exists = _registered_evidence(session, case_id, evidence_id)
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503
        if not exists:
            return jsonify(error="Evidence ID not registered to this case"), 404
        _table(session)
        params = {
            "case_id": case_id, "evidence_id": evidence_id,
            "action": action, "actor": actor, "counterparty": counterparty or None,
            "purpose": purpose, "storage_location": location or None,
            "event_time": event_time,
            "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "integrity_sha256": sha256.lower() or None,
            "integrity_note": integrity_note or None,
            "provenance": "INVESTIGATOR_DECLARED",
        }
        result = session.execute(text("""
            INSERT INTO custody_events_step76
                (case_id, evidence_id, action, actor, counterparty, purpose,
                 storage_location, event_time, recorded_utc, integrity_sha256,
                 integrity_note, provenance)
            VALUES (:case_id, :evidence_id, :action, :actor, :counterparty, :purpose,
                    :storage_location, :event_time, :recorded_utc, :integrity_sha256,
                    :integrity_note, :provenance)
        """), params)
        event_id = result.lastrowid
        session.commit()
        return jsonify(event={"event_id": event_id, **params},
                       notice="Investigator-declared custody event saved; no historical event or hash independently verified"), 201
