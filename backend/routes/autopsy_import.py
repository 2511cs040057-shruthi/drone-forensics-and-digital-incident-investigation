
import hashlib
import json
import os
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..auth import login_required
from ..models.case import Case
from ..models.evidence import Evidence
from ..services.database import SessionLocal


autopsy_import_api = Blueprint("autopsy_import_api", __name__)

DEFAULT_RECEIVED_CASES = (
    r"C:\Users\rango\Downloads\autopsy_bridge_fixed"
    r"\autopsy_bridge_fixed\received_cases"
)

EXPORT_ID_PATTERN = re.compile(r"^autopsy-[a-zA-Z0-9_-]+$")
SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_received_cases_directory() -> Path:
    configured = os.getenv(
        "AUTOPSY_RECEIVED_CASES",
        DEFAULT_RECEIVED_CASES,
    )

    return Path(configured).resolve()


def validate_archive_path(export_directory: Path, archive_path: str):
    if not isinstance(archive_path, str):
        return None

    if "\\" in archive_path:
        return None

    relative_path = Path(archive_path)

    if relative_path.is_absolute():
        return None

    if len(relative_path.parts) != 2:
        return None

    if relative_path.parts[0] != "evidence":
        return None

    if any(part in ("", ".", "..") for part in relative_path.parts):
        return None

    evidence_directory = (export_directory / "evidence").resolve()
    candidate = (export_directory / relative_path).resolve()

    if candidate.parent != evidence_directory:
        return None

    if not candidate.is_file():
        return None

    return candidate


@autopsy_import_api.post("/cases/<int:case_id>/autopsy/import")
@login_required
def import_autopsy_evidence(case_id: int):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "A JSON request body is required."
        }), 400

    export_id = payload.get("autopsy_export_id")

    if not isinstance(export_id, str):
        return jsonify({
            "error": "autopsy_export_id must be a string."
        }), 400

    export_id = export_id.strip()

    if not EXPORT_ID_PATTERN.fullmatch(export_id):
        return jsonify({
            "error": "Invalid Autopsy export ID."
        }), 400

    received_cases = get_received_cases_directory()
    export_directory = (received_cases / export_id).resolve()

    if export_directory.parent != received_cases:
        return jsonify({
            "error": "Invalid export directory."
        }), 400

    manifest_path = export_directory / "manifest.json"

    if not manifest_path.is_file():
        return jsonify({
            "error": "Autopsy manifest was not found."
        }), 404

    try:
        with manifest_path.open("r", encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError):
        current_app.logger.exception(
            "Unable to read Autopsy manifest: %s",
            manifest_path,
        )
        return jsonify({
            "error": "The Autopsy manifest could not be read."
        }), 422

    if not isinstance(manifest, dict):
        return jsonify({
            "error": "Invalid Autopsy manifest structure."
        }), 422

    if manifest.get("case_id") != export_id:
        return jsonify({
            "error": "Autopsy manifest case ID does not match."
        }), 422

    if manifest.get("schema_version") != 1:
        return jsonify({
            "error": "Unsupported Autopsy manifest version."
        }), 422

    if manifest.get("export_complete") is not True:
        return jsonify({
            "error": "Autopsy export is not marked complete."
        }), 422

    entries = manifest.get("evidence")

    if not isinstance(entries, list) or not entries:
        return jsonify({
            "error": "No evidence entries were found in the manifest."
        }), 422

    verified_entries = []
    failures = []
    seen_object_ids = set()

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            failures.append({
                "entry": index,
                "error": "Invalid evidence entry.",
            })
            continue

        object_id = entry.get("object_id")
        filename = entry.get("name")
        expected_sha256 = entry.get("sha256")
        expected_size = entry.get("size")
        archive_path = entry.get("archive_path")
        source_path = entry.get("source_path")

        if not isinstance(object_id, str) or not object_id.strip():
            failures.append({
                "entry": index,
                "error": "Invalid Autopsy object ID.",
            })
            continue

        if object_id in seen_object_ids:
            failures.append({
                "entry": index,
                "error": "Duplicate Autopsy object ID.",
            })
            continue

        seen_object_ids.add(object_id)

        if not isinstance(filename, str) or not filename.strip():
            failures.append({
                "entry": index,
                "error": "Invalid filename.",
            })
            continue

        if len(filename) > 255:
            failures.append({
                "entry": index,
                "error": "Filename exceeds 255 characters.",
            })
            continue

        if not isinstance(expected_sha256, str):
            failures.append({
                "entry": index,
                "error": "Missing SHA-256 hash.",
            })
            continue

        if not SHA256_PATTERN.fullmatch(expected_sha256):
            failures.append({
                "entry": index,
                "error": "Invalid SHA-256 hash.",
            })
            continue

        if type(expected_size) is not int or expected_size < 0:
            failures.append({
                "entry": index,
                "error": "Invalid evidence size.",
            })
            continue

        if source_path is not None and not isinstance(source_path, str):
            failures.append({
                "entry": index,
                "error": "Invalid source path.",
            })
            continue

        evidence_path = validate_archive_path(
            export_directory,
            archive_path,
        )

        if evidence_path is None:
            failures.append({
                "entry": index,
                "filename": filename,
                "error": "Evidence file is missing or has an unsafe path.",
            })
            continue

        actual_size = evidence_path.stat().st_size

        if actual_size != expected_size:
            failures.append({
                "entry": index,
                "filename": filename,
                "error": "File size mismatch.",
            })
            continue

        actual_sha256 = calculate_sha256(evidence_path)

        if actual_sha256.lower() != expected_sha256.lower():
            failures.append({
                "entry": index,
                "filename": filename,
                "error": "SHA-256 mismatch.",
            })
            continue

        verified_entries.append({
            "filename": filename,
            "file_size": actual_size,
            "sha256": actual_sha256,
            "storage_path": str(evidence_path),
            "source_path": source_path,
            "autopsy_export_id": export_id,
            "autopsy_object_id": object_id,
            "verification_status": "Verified",
        })

    if failures:
        return jsonify({
            "error": "Evidence verification failed. No records were imported.",
            "verified_files": len(verified_entries),
            "failed_files": len(failures),
            "failures": failures,
        }), 422

    try:
        with SessionLocal() as db:
            case = db.get(Case, case_id)

            if case is None:
                return jsonify({
                    "error": "The selected MySQL investigation case was not found."
                }), 404

            existing = db.scalars(
                select(Evidence).where(
                    Evidence.autopsy_export_id == export_id
                )
            ).all()

            existing_by_object_id = {
                item.autopsy_object_id: item
                for item in existing
            }

            conflicts = []

            for entry in verified_entries:
                existing_record = existing_by_object_id.get(
                    entry["autopsy_object_id"]
                )

                if existing_record is None:
                    continue

                if (
                    existing_record.case_id != case_id
                    or existing_record.sha256.lower() != entry["sha256"].lower()
                    or existing_record.file_size != entry["file_size"]
                    or existing_record.storage_path != entry["storage_path"]
                ):
                    conflicts.append(entry["autopsy_object_id"])

            if conflicts:
                return jsonify({
                    "error": (
                        "Some Autopsy evidence records already exist "
                        "with different case associations or metadata."
                    ),
                    "conflicting_object_ids": conflicts,
                }), 409

            imported_count = 0
            already_registered = 0

            for entry in verified_entries:
                if entry["autopsy_object_id"] in existing_by_object_id:
                    already_registered += 1
                    continue

                db.add(Evidence(
                    case_id=case_id,
                    **entry,
                ))

                imported_count += 1

            db.commit()

            return jsonify({
                "message": "Autopsy evidence import completed.",
                "case_id": case_id,
                "case_number": case.case_number,
                "autopsy_export_id": export_id,
                "verified_files": len(verified_entries),
                "imported_files": imported_count,
                "already_registered": already_registered,
                "failed_files": 0,
            }), 201 if imported_count else 200

    except IntegrityError:
        current_app.logger.exception(
            "Autopsy evidence import database conflict"
        )
        return jsonify({
            "error": "Evidence registration conflict. Please retry."
        }), 409

    except Exception:
        current_app.logger.exception(
            "Autopsy evidence import failed"
        )
        return jsonify({
            "error": "An unexpected error occurred during evidence import."
        }), 500
