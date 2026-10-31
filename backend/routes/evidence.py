from flask import Blueprint, current_app, jsonify
from sqlalchemy import select

from ..auth import login_required
from ..models.case import Case
from ..models.evidence import Evidence
from ..services.database import SessionLocal


evidence_api = Blueprint("evidence_api", __name__)


@evidence_api.get("/cases/<int:case_id>/evidence")
@login_required
def list_case_evidence(case_id: int):
    """List evidence metadata registered to an investigation case."""
    try:
        with SessionLocal() as db:
            case = db.get(Case, case_id)
            if case is None:
                return jsonify({"error": "Investigation case not found."}), 404

            records = db.scalars(
                select(Evidence)
                .where(Evidence.case_id == case_id)
                .order_by(Evidence.evidence_id.asc())
            ).all()

            return jsonify({
                "case_id": case.case_id,
                "case_number": case.case_number,
                "total_evidence": len(records),
                "evidence": [
                    {
                        "evidence_id": item.evidence_id,
                        "case_id": item.case_id,
                        "filename": item.filename,
                        "file_size": item.file_size,
                        "sha256": item.sha256,
                        "source_path": item.source_path,
                        "autopsy_export_id": item.autopsy_export_id,
                        "autopsy_object_id": item.autopsy_object_id,
                        "verification_status": item.verification_status,
                        "imported_at": item.imported_at.isoformat()
                        if item.imported_at else None,
                    }
                    for item in records
                ],
            }), 200
    except Exception:
        current_app.logger.exception(
            "Failed to retrieve evidence for case %s", case_id
        )
        return jsonify({"error": "Unable to retrieve investigation evidence."}), 500
