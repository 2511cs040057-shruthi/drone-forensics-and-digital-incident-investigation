from datetime import date

from flask import Blueprint, jsonify, request, session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..models.case import Case
from ..services.database import SessionLocal


cases_api = Blueprint("cases_api", __name__)
ALLOWED_STATUSES = {"Open", "In Progress", "Review", "Closed"}
MAX_LENGTHS = {"case_number": 64, "case_title": 200, "examiner_name": 150}


@cases_api.before_request
def require_login():
    if not session.get("user_id"):
        return jsonify({"error": "Please sign in to continue."}), 401


def error(message: str, status: int):
    return jsonify({"error": message}), status


def validate_case_payload(payload: object, *, partial: bool = False):
    if not isinstance(payload, dict):
        return None, "A JSON object is required."

    result = {}
    required = ("case_number", "case_title")
    if not partial:
        missing = [field for field in required if not str(payload.get(field, "")).strip()]
        if missing:
            return None, f"Required fields: {', '.join(missing)}."

    for field, max_length in MAX_LENGTHS.items():
        if field not in payload:
            continue
        value = payload[field]
        if value is None and field == "examiner_name":
            result[field] = None
            continue
        if not isinstance(value, str):
            return None, f"{field} must be a string."
        value = value.strip()
        if field in required and not value:
            return None, f"{field} is required."
        if len(value) > max_length:
            return None, f"{field} must be {max_length} characters or fewer."
        result[field] = value or None

    if "description" in payload:
        description = payload["description"]
        if description is not None and not isinstance(description, str):
            return None, "description must be a string."
        result["description"] = description.strip() or None if description else None

    if "status" in payload:
        status = payload["status"]
        if not isinstance(status, str) or status.strip() not in ALLOWED_STATUSES:
            options = ", ".join(sorted(ALLOWED_STATUSES))
            return None, f"status must be one of: {options}."
        result["status"] = status.strip()

    if "investigation_date" in payload:
        raw_date = payload["investigation_date"]
        if not isinstance(raw_date, str):
            return None, "investigation_date must use YYYY-MM-DD format."
        try:
            result["investigation_date"] = date.fromisoformat(raw_date.strip())
        except ValueError:
            return None, "investigation_date must use YYYY-MM-DD format."

    return result, None


@cases_api.get("/cases")
def list_cases():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    with SessionLocal() as session:
        statement = select(Case)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                Case.case_number.ilike(pattern)
                | Case.case_title.ilike(pattern)
                | Case.examiner_name.ilike(pattern)
            )
        if status:
            if status not in ALLOWED_STATUSES:
                return error("Unsupported case status filter.", 400)
            statement = statement.where(Case.status == status)
        records = session.scalars(
            statement.order_by(Case.updated_at.desc(), Case.case_id.desc())
        ).all()
        return jsonify({"cases": [item.to_dict() for item in records], "total": len(records)})


@cases_api.post("/cases")
def create_case():
    payload, validation_error = validate_case_payload(request.get_json(silent=True))
    if validation_error:
        return error(validation_error, 400)
    payload.setdefault("status", "Open")
    payload.setdefault("investigation_date", date.today())
    record = Case(**payload)
    with SessionLocal() as session:
        session.add(record)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return error("A case with this case_number already exists.", 409)
        session.refresh(record)
        return jsonify({"message": "Case created.", "case": record.to_dict()}), 201


@cases_api.get("/cases/<int:case_id>")
def get_case(case_id: int):
    with SessionLocal() as session:
        record = session.get(Case, case_id)
        if record is None:
            return error("Case not found.", 404)
        return jsonify({"case": record.to_dict()})


@cases_api.put("/cases/<int:case_id>")
def update_case(case_id: int):
    payload, validation_error = validate_case_payload(
        request.get_json(silent=True), partial=True
    )
    if validation_error:
        return error(validation_error, 400)
    if not payload:
        return error("Provide at least one case field to update.", 400)

    with SessionLocal() as session:
        record = session.get(Case, case_id)
        if record is None:
            return error("Case not found.", 404)
        for field, value in payload.items():
            setattr(record, field, value)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return error("A case with this case_number already exists.", 409)
        session.refresh(record)
        return jsonify({"message": "Case updated.", "case": record.to_dict()})


@cases_api.delete("/cases/<int:case_id>")
def delete_case(case_id: int):
    with SessionLocal() as session:
        record = session.get(Case, case_id)
        if record is None:
            return error("Case not found.", 404)
        session.delete(record)
        session.commit()
        return jsonify({"message": "Case deleted.", "case_id": case_id})
