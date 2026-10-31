
import hashlib
import os
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify

from ..auth import login_required
from ..models.case import Case
from ..models.evidence import Evidence
from ..services.database import SessionLocal
from .autopsy_import import get_received_cases_directory


evidence_integrity_api = Blueprint(
    "evidence_integrity_api",
    __name__,
)

SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
EXPORT_ID_PATTERN = re.compile(r"^autopsy-[a-zA-Z0-9_-]+$")


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for chunk in iter(
            lambda: source.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def resolve_evidence_path(evidence: Evidence) -> Path | None:
    """
    Only permit evidence files inside their registered
    Autopsy export's evidence directory.
    """

    export_id = evidence.autopsy_export_id

    if not EXPORT_ID_PATTERN.fullmatch(export_id):
        return None

    received_cases = get_received_cases_directory()
    export_directory = (received_cases / export_id).resolve()
    evidence_directory = (export_directory / "evidence").resolve()

    if export_directory.parent != received_cases:
        return None

    if evidence_directory.parent != export_directory:
        return None

    stored_path = Path(evidence.storage_path)

    if not stored_path.is_absolute():
        return None

    resolved_path = stored_path.resolve()

    if resolved_path.parent != evidence_directory:
        return None

    return resolved_path


@evidence_integrity_api.get(
    "/cases/<int:case_id>/evidence/<int:evidence_id>/verify"
)
@login_required
def verify_evidence_integrity(case_id: int, evidence_id: int):
    """
    Recalculate the current SHA-256 hash of one evidence file.

    This endpoint reads the file without modifying it.
    The original hash stored in MySQL is not changed.
    """

    try:
        with SessionLocal() as db:
            case = db.get(Case, case_id)

            if case is None:
                return jsonify({
                    "error": "Investigation case not found."
                }), 404

            evidence = db.get(Evidence, evidence_id)

            if evidence is None or evidence.case_id != case_id:
                return jsonify({
                    "error": "Evidence record not found in this case."
                }), 404

            expected_hash = evidence.sha256

            if not SHA256_PATTERN.fullmatch(expected_hash):
                return jsonify({
                    "error": "Stored SHA-256 hash is invalid."
                }), 422

            evidence_path = resolve_evidence_path(evidence)

            if evidence_path is None:
                return jsonify({
                    "error": "Evidence storage path is invalid."
                }), 422

            if not evidence_path.is_file():
                return jsonify({
                    "case_id": case_id,
                    "evidence_id": evidence_id,
                    "filename": evidence.filename,
                    "result": "FILE MISSING",
                    "expected_sha256": expected_hash,
                    "actual_sha256": None,
                }), 200

            actual_hash = calculate_sha256(evidence_path)

            result = (
                "MATCH"
                if actual_hash.lower() == expected_hash.lower()
                else "MISMATCH"
            )

            return jsonify({
                "case_id": case_id,
                "case_number": case.case_number,
                "evidence_id": evidence_id,
                "filename": evidence.filename,
                "result": result,
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "file_size": evidence_path.stat().st_size,
            }), 200

    except OSError:
        current_app.logger.exception(
            "Unable to read evidence file %s",
            evidence_id,
        )

        return jsonify({
            "error": "Unable to read the evidence file."
        }), 500

    except Exception:
        current_app.logger.exception(
            "Evidence integrity verification failed"
        )

        return jsonify({
            "error": "Evidence integrity verification failed."
        }), 500
