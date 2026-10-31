from flask import Flask, request, jsonify, send_file, send_from_directory
from database.db import get_connection
from flight_log_processor import process_flight_log
from report_generator import generate_forensic_report

from werkzeug.utils import secure_filename

from datetime import datetime
from decimal import Decimal
import hashlib
import os
import uuid


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

app = Flask(__name__)

from additional_routes import additional_api
app.register_blueprint(additional_api, url_prefix="/api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "evidence")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# =========================================================
# GENERAL HELPER FUNCTIONS
# =========================================================

def calculate_sha256(file_path):
    """Calculate the SHA-256 hash of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def serialize_value(value):
    """Convert database values into JSON-compatible values."""

    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def serialize_row(row):
    """Convert a dictionary database row into JSON-compatible data."""

    if row is None:
        return None

    return {
        key: serialize_value(value)
        for key, value in row.items()
    }


def fetch_all(cursor):
    """Fetch all dictionary rows and serialize them."""

    return [serialize_row(row) for row in cursor.fetchall()]


def parse_timestamp(value):
    """Convert a flight-log timestamp into a Python datetime."""

    if isinstance(value, datetime):
        return value

    value = str(value).strip()

    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid timestamp: {value}"
        ) from error


def resolve_evidence_path(stored_path):
    """Resolve a stored evidence path safely."""

    if not stored_path:
        return None

    candidate = os.path.abspath(stored_path)

    allowed_folder = os.path.abspath(UPLOAD_FOLDER)

    try:
        if os.path.commonpath(
            [candidate, allowed_folder]
        ) != allowed_folder:
            return None
    except ValueError:
        return None

    return candidate


def generate_evidence_code():
    """Generate a unique evidence reference."""

    return "EVD-" + uuid.uuid4().hex[:16].upper()


def get_case(cursor, case_id):
    """Retrieve a case by its ID."""

    cursor.execute(
        """
        SELECT *
        FROM cases
        WHERE case_id = %s
        """,
        (case_id,)
    )

    return cursor.fetchone()


def get_evidence(cursor, evidence_id):
    """Retrieve an evidence record by its ID."""

    cursor.execute(
        """
        SELECT *
        FROM evidence
        WHERE evidence_id = %s
        """,
        (evidence_id,)
    )

    return cursor.fetchone()


def register_evidence(
    cursor,
    case_id,
    file_path,
    original_filename,
    evidence_type,
    extraction_method="Manual Upload",
    source_component="Unknown"
):
    """
    Register an evidence file and store its SHA-256 hash.

    The file must already exist in the evidence directory.
    """

    file_size = os.path.getsize(file_path)
    file_hash = calculate_sha256(file_path)
    evidence_code = generate_evidence_code()

    cursor.execute(
        """
        INSERT INTO evidence (
            case_id,
            evidence_code,
            evidence_type,
            source_component,
            file_name,
            file_size,
            extraction_method,
            acquired_at,
            storage_path,
            verification_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            case_id,
            evidence_code,
            evidence_type,
            source_component,
            original_filename,
            file_size,
            extraction_method,
            datetime.now(),
            file_path,
            "Verified"
        )
    )

    evidence_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO hash_records (
            evidence_id,
            hash_algorithm,
            hash_value,
            verification_status
        )
        VALUES (%s, %s, %s, %s)
        """,
        (
            evidence_id,
            "SHA-256",
            file_hash,
            "Verified"
        )
    )

    return {
        "evidence_id": evidence_id,
        "evidence_code": evidence_code,
        "sha256_hash": file_hash,
        "file_size": file_size
    }


def get_flight_for_evidence(cursor, evidence):
    """
    Find the flight associated with an evidence file.

    source_storage stores the evidence_code reference for
    flights processed from uploaded flight-log evidence.
    """

    if not evidence:
        return None

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE source_storage = %s
        ORDER BY flight_id DESC
        LIMIT 1
        """,
        (evidence["evidence_code"],)
    )

    return cursor.fetchone()


def get_latest_hash(cursor, evidence_id):
    """Get the most recent SHA-256 record for evidence."""

    cursor.execute(
        """
        SELECT *
        FROM hash_records
        WHERE evidence_id = %s
          AND hash_algorithm = 'SHA-256'
        ORDER BY hash_id DESC
        LIMIT 1
        """,
        (evidence_id,)
    )

    return cursor.fetchone()


# =========================================================
# BASIC ROUTES
# =========================================================

@app.route("/", methods=["GET"])
def home():
    index_path = os.path.join(STATIC_FOLDER, "index.html")

    if os.path.isfile(index_path):
        return send_from_directory(STATIC_FOLDER, "index.html")

    return jsonify({
        "project": "MD-DRONE",
        "message": "Drone Forensics and Digital Incident Investigation"
    })


@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({
        "message": "MD-DRONE backend is working"
    })


@app.route("/api/health", methods=["GET"])
def health():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE() AS database_name")
        row = cursor.fetchone()

        return jsonify({
            "status": "healthy",
            "database": row[0] if row else None
        })

    except Exception:
        app.logger.exception("Health check failed")

        return jsonify({
            "status": "unhealthy",
            "message": "Database connection failed"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/project", methods=["GET"])
def project():
    return jsonify({
        "project": "MD-DRONE",
        "purpose": "Drone Forensics and Digital Incident Investigation",
        "database": "drone_forensics",
        "backend": "Flask",
        "features": [
            "Forensic case management",
            "Evidence management",
            "SHA-256 integrity verification",
            "Flight-log processing",
            "GPS route retrieval",
            "Flight timeline reconstruction",
            "Potential anomaly analysis",
            "PDF forensic reports"
        ]
    })


# =========================================================
# CASE MANAGEMENT
# =========================================================

@app.route("/api/cases", methods=["POST"])
def create_case():
    data = request.get_json(silent=True) or {}

    case_number = data.get("case_number")
    case_title = data.get("case_title")

    if not case_number or not case_title:
        return jsonify({
            "error": "case_number and case_title are required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO cases (
                case_number,
                case_title,
                description,
                status,
                examiner_name
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                case_number,
                case_title,
                data.get("description"),
                data.get("status", "Open"),
                data.get("examiner_name")
            )
        )

        case_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Case created successfully",
            "case_id": case_id,
            "case_number": case_number,
            "case_title": case_title
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Case creation failed")

        return jsonify({
            "error": "Could not create case",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/cases", methods=["GET"])
def get_cases():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM cases
            ORDER BY created_at DESC
            """
        )

        return jsonify({
            "cases": fetch_all(cursor)
        })

    except Exception as error:
        app.logger.exception("Retrieving cases failed")

        return jsonify({
            "error": "Could not retrieve cases",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/cases/<int:case_id>", methods=["GET"])
def get_case_by_id(case_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM cases WHERE case_id = %s",
            (case_id,)
        )

        case = cursor.fetchone()

        if not case:
            return jsonify({
                "error": "Case not found"
            }), 404

        return jsonify({
            "case": serialize_row(case)
        })

    except Exception as error:
        app.logger.exception("Retrieving case failed")

        return jsonify({
            "error": "Could not retrieve case",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/cases/<int:case_id>", methods=["PUT"])
def update_case(case_id):
    data = request.get_json(silent=True) or {}

    allowed_fields = [
        "case_number",
        "case_title",
        "description",
        "status",
        "examiner_name"
    ]

    updates = {
        key: data[key]
        for key in allowed_fields
        if key in data
    }

    if not updates:
        return jsonify({
            "error": "No valid fields supplied for update"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not get_case(cursor, case_id):
            return jsonify({
                "error": "Case not found"
            }), 404

        set_clause = ", ".join(
            f"{field} = %s"
            for field in updates
        )

        values = list(updates.values())
        values.append(case_id)

        cursor.execute(
            f"""
            UPDATE cases
            SET {set_clause}
            WHERE case_id = %s
            """,
            tuple(values)
        )

        connection.commit()

        return jsonify({
            "message": "Case updated successfully",
            "case_id": case_id
        })

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Case update failed")

        return jsonify({
            "error": "Could not update case",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/cases/<int:case_id>", methods=["DELETE"])
def delete_case(case_id):
    """
    Delete only cases without dependent forensic records.

    Referenced cases are preserved to protect evidence and
    chain-of-custody records.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not get_case(cursor, case_id):
            return jsonify({
                "error": "Case not found"
            }), 404

        dependent_tables = [
            ("drones", "case_id"),
            ("flights", "case_id"),
            ("evidence", "case_id"),
            ("media", "case_id"),
            ("forensic_reports", "case_id"),
            ("bookmarked_evidence", "case_id")
        ]

        for table_name, column_name in dependent_tables:
            cursor.execute(
                f"""
                SELECT 1
                FROM {table_name}
                WHERE {column_name} = %s
                LIMIT 1
                """,
                (case_id,)
            )

            if cursor.fetchone():
                return jsonify({
                    "error": (
                        "This case contains related forensic records. "
                        "It cannot be deleted automatically."
                    ),
                    "table_with_related_records": table_name
                }), 409

        cursor.execute(
            "DELETE FROM cases WHERE case_id = %s",
            (case_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Case deleted successfully",
            "case_id": case_id
        })

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Case deletion failed")

        return jsonify({
            "error": "Could not delete case",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# EVIDENCE MANAGEMENT
# =========================================================

@app.route("/api/evidence", methods=["GET"])
def get_evidence_list():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id", type=int)

        if case_id is not None:
            cursor.execute(
                """
                SELECT e.*, h.hash_algorithm, h.hash_value,
                       h.calculated_at
                FROM evidence e
                LEFT JOIN hash_records h
                    ON h.hash_id = (
                        SELECT MAX(h2.hash_id)
                        FROM hash_records h2
                        WHERE h2.evidence_id = e.evidence_id
                    )
                WHERE e.case_id = %s
                ORDER BY e.created_at DESC
                """,
                (case_id,)
            )
        else:
            cursor.execute(
                """
                SELECT e.*, h.hash_algorithm, h.hash_value,
                       h.calculated_at
                FROM evidence e
                LEFT JOIN hash_records h
                    ON h.hash_id = (
                        SELECT MAX(h2.hash_id)
                        FROM hash_records h2
                        WHERE h2.evidence_id = e.evidence_id
                    )
                ORDER BY e.created_at DESC
                """
            )

        return jsonify({
            "evidence": fetch_all(cursor)
        })

    except Exception as error:
        app.logger.exception("Evidence retrieval failed")

        return jsonify({
            "error": "Could not retrieve evidence",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/evidence/<int:evidence_id>", methods=["GET"])
def get_evidence_by_id(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM evidence
            WHERE evidence_id = %s
            """,
            (evidence_id,)
        )

        evidence = cursor.fetchone()

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        cursor.execute(
            """
            SELECT *
            FROM hash_records
            WHERE evidence_id = %s
            ORDER BY calculated_at DESC
            """,
            (evidence_id,)
        )

        hashes = fetch_all(cursor)

        return jsonify({
            "evidence": serialize_row(evidence),
            "hash_records": hashes
        })

    except Exception as error:
        app.logger.exception("Evidence lookup failed")

        return jsonify({
            "error": "Could not retrieve evidence",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route("/api/evidence/upload", methods=["POST"])
@app.route("/api/evidence", methods=["POST"])
def upload_evidence():
    if "file" not in request.files:
        return jsonify({
            "error": "A file is required"
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "error": "No filename supplied"
        }), 400

    case_id = request.form.get("case_id", type=int)

    if not case_id:
        return jsonify({
            "error": "case_id is required"
        }), 400

    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        return jsonify({
            "error": "Invalid filename"
        }), 400

    unique_filename = (
        uuid.uuid4().hex + "_" + original_filename
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    connection = None
    cursor = None
    saved_file = False
    committed = False

    try:
        uploaded_file.save(file_path)
        saved_file = True

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not get_case(cursor, case_id):
            return jsonify({
                "error": "Case not found"
            }), 404

        evidence_type = request.form.get(
            "evidence_type",
            "Digital File"
        )

        source_component = request.form.get(
            "source_component",
            "Unknown"
        )

        extraction_method = request.form.get(
            "extraction_method",
            "Manual Upload"
        )

        result = register_evidence(
            cursor=cursor,
            case_id=case_id,
            file_path=file_path,
            original_filename=original_filename,
            evidence_type=evidence_type,
            extraction_method=extraction_method,
            source_component=source_component
        )

        connection.commit()
        committed = True

        return jsonify({
           "message": "Evidence uploaded successfully",
        **result
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Evidence upload failed")

        return jsonify({
            "error": "Evidence upload failed",
            "details": str(error)
        }), 500

    
    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

        # Remove the uploaded file if database registration
        # did not commit successfully.
        if saved_file and not committed:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except OSError:
                app.logger.exception(
                    "Could not remove unregistered uploaded evidence"
                )


# =========================================================
# =========================================================
# EVIDENCE INTEGRITY VERIFICATION
# =========================================================

@app.route("/api/evidence/<int:evidence_id>/verify", methods=["GET"])
def verify_evidence(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        hash_record = get_latest_hash(cursor, evidence_id)

        if not hash_record:
            message = "No reference SHA-256 hash was found"

            cursor.execute(
                """
                INSERT INTO evidence_verification_history (
                    evidence_id,
                    reference_hash,
                    current_hash,
                    verification_status,
                    message
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (evidence_id, None, None, "UNVERIFIABLE", message)
            )
            connection.commit()

            return jsonify({
                "evidence_id": evidence_id,
                "status": "UNVERIFIABLE",
                "message": message
            }), 200

        reference_hash = hash_record["hash_value"]
        file_path = resolve_evidence_path(evidence["storage_path"])

        if not file_path or not os.path.isfile(file_path):
            message = "The stored evidence file was not found"

            cursor.execute(
                """
                INSERT INTO evidence_verification_history (
                    evidence_id,
                    reference_hash,
                    current_hash,
                    verification_status,
                    message
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    evidence_id,
                    reference_hash,
                    None,
                    "UNVERIFIABLE",
                    message
                )
            )
            connection.commit()

            return jsonify({
                "evidence_id": evidence_id,
                "status": "UNVERIFIABLE",
                "message": message,
                "reference_hash": reference_hash
            }), 200

        current_hash = calculate_sha256(file_path)
        matched = current_hash.lower() == reference_hash.lower()
        verification_status = "MATCH" if matched else "MISMATCH"
        database_status = "Verified" if matched else "Mismatch"

        cursor.execute(
            """
            UPDATE evidence
            SET verification_status = %s
            WHERE evidence_id = %s
            """,
            (database_status, evidence_id)
        )

        cursor.execute(
            """
            UPDATE hash_records
            SET verification_status = %s
            WHERE hash_id = %s
            """,
            (database_status, hash_record["hash_id"])
        )

        cursor.execute(
            """
            INSERT INTO evidence_verification_history (
                evidence_id,
                reference_hash,
                current_hash,
                verification_status,
                message
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                evidence_id,
                reference_hash,
                current_hash,
                verification_status,
                "File matches the reference hash."
                if matched
                else "File differs from the reference hash."
            )
        )

        connection.commit()

        return jsonify({
            "evidence_id": evidence_id,
            "status": verification_status,
            "algorithm": "SHA-256",
            "reference_hash": reference_hash,
            "current_hash": current_hash,
            "integrity_verified": matched
        }), 200

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Evidence verification failed")

        return jsonify({
            "error": "Could not verify evidence",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route(
    "/api/evidence/<int:evidence_id>/verification-history",
    methods=["GET"]
)
def get_evidence_verification_history(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE evidence_id = %s
            """,
            (evidence_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Evidence not found"
            }), 404

        cursor.execute(
            """
            SELECT
                verification_id,
                evidence_id,
                reference_hash,
                current_hash,
                verification_status,
                message,
                verified_at
            FROM evidence_verification_history
            WHERE evidence_id = %s
            ORDER BY verification_id DESC
            """,
            (evidence_id,)
        )

        history = cursor.fetchall()

        return jsonify({
            "evidence_id": evidence_id,
            "total_attempts": len(history),
            "history": history
        }), 200

    except Exception as error:
        app.logger.exception("Verification-history retrieval failed")

        return jsonify({
            "error": "Could not retrieve verification history",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# FLIGHT-LOG PROCESSING
# =========================================================

@app.route("/api/flight-log/process", methods=["POST"])
def process_uploaded_flight_log():
    if "file" not in request.files:
        return jsonify({
            "error": "A flight-log file is required"
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "error": "No filename supplied"
        }), 400

    case_id = request.form.get("case_id", type=int)

    if not case_id:
        return jsonify({
            "error": "case_id is required"
        }), 400

    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        return jsonify({
            "error": "Invalid filename"
        }), 400

    unique_filename = (
        uuid.uuid4().hex + "_" + original_filename
    )

    file_path = os.path.join(
        UPLOAD_FOLDER,
        unique_filename
    )

    connection = None
    cursor = None
    committed = False

    try:
        uploaded_file.save(file_path)

        # Parse the file before opening a database transaction.
        # Invalid or unreadable flight logs should return HTTP 400.
        try:
            flight_data = process_flight_log(file_path)
        except (ValueError, UnicodeDecodeError) as error:
            return jsonify({
                "error": "Invalid flight-log file",
                "details": str(error)
            }), 400

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case = get_case(cursor, case_id)

        if not case:
            return jsonify({
                "error": "Case not found"
            }), 404

        drone_name = (
            flight_data.get("drone") or "Unknown Drone"
        )

        flight_number = (
            flight_data.get("flight_id") or
            "FLIGHT-" + uuid.uuid4().hex[:8].upper()
        )

        records = flight_data["records"]

        timestamps = [
            parse_timestamp(record["timestamp"])
            for record in records
        ]

        start_time = min(timestamps)
        end_time = max(timestamps)

        duration_seconds = max(
            0,
            int((end_time - start_time).total_seconds())
        )

        # -------------------------------------------------
        # 1. Register the flight-log evidence and its hash.
        # -------------------------------------------------

        evidence_result = register_evidence(
            cursor=cursor,
            case_id=case_id,
            file_path=file_path,
            original_filename=original_filename,
            evidence_type="Flight Log",
            extraction_method="Flight Log Parser",
            source_component="Drone Flight Log"
        )

        evidence_id = evidence_result["evidence_id"]
        evidence_code = evidence_result["evidence_code"]

        # -------------------------------------------------
        # 2. Create or reuse the drone record.
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT *
            FROM drones
            WHERE case_id = %s
              AND drone_name = %s
            ORDER BY drone_id DESC
            LIMIT 1
            """,
            (case_id, drone_name)
        )

        drone = cursor.fetchone()

        if drone:
            drone_id = drone["drone_id"]
        else:
            cursor.execute(
                """
                INSERT INTO drones (
                    case_id,
                    drone_name
                )
                VALUES (%s, %s)
                """,
                (case_id, drone_name)
            )

            drone_id = cursor.lastrowid

        # -------------------------------------------------
        # 3. Create the flight record.
        # -------------------------------------------------

        cursor.execute(
            """
            INSERT INTO flights (
                drone_id,
                case_id,
                flight_number,
                start_time,
                end_time,
                flight_duration_seconds,
                flight_status,
                source_storage
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                drone_id,
                case_id,
                flight_number,
                start_time,
                end_time,
                duration_seconds,
                "Processed",
                evidence_code
            )
        )

        flight_db_id = cursor.lastrowid

        # -------------------------------------------------
        # 4. Save GPS records and timeline entries.
        # -------------------------------------------------

        gps_query = """
            INSERT INTO gps_data (
                flight_id,
                recorded_at,
                latitude,
                longitude,
                altitude_m,
                ground_speed_mps
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        timeline_query = """
            INSERT INTO flight_timeline (
                flight_id,
                sequence_no,
                event_time,
                timeline_type,
                title,
                description,
                latitude,
                longitude,
                altitude_m,
                speed_mps,
                source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for sequence_no, record in enumerate(records, start=1):
            record_time = parse_timestamp(record["timestamp"])

            latitude = record["latitude"]
            longitude = record["longitude"]
            altitude = record["altitude"]
            speed = record["speed"]

            cursor.execute(
                gps_query,
                (
                    flight_db_id,
                    record_time,
                    latitude,
                    longitude,
                    altitude,
                    speed
                )
            )

            cursor.execute(
                timeline_query,
                (
                    flight_db_id,
                    sequence_no,
                    record_time,
                    "Flight Record",
                    f"Flight record {sequence_no}",
                    (
                        "GPS position recorded from the uploaded "
                        "flight log."
                    ),
                    latitude,
                    longitude,
                    altitude,
                    speed,
                    "Flight Log Parser"
                )
            )

        connection.commit()
        committed = True

        return jsonify({
            "message": "Flight log processed successfully",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "evidence_code": evidence_code,
            "drone_id": drone_id,
            "drone": drone_name,
            "flight_id": flight_db_id,
            "flight_number": flight_number,
            "record_count": len(records),
            "gps_records_saved": len(records),
            "timeline_records_saved": len(records),
            "start_time": start_time.isoformat(sep=" "),
            "end_time": end_time.isoformat(sep=" "),
            "duration_seconds": duration_seconds,
            "sha256_hash": evidence_result["sha256_hash"]
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Flight-log processing failed")

        return jsonify({
            "error": "Flight-log processing failed",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

        # If the transaction failed, remove its unregistered upload.
        if not committed and os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                app.logger.exception(
                    "Could not remove unregistered uploaded file"
                )


# =========================================================
# FLIGHT RECORDS
# =========================================================

@app.route("/api/flight-records/<int:evidence_id>", methods=["GET"])
def get_flight_records(evidence_id):
    """
    Return GPS records associated with an evidence ID.

    This maintains the previous API URL while reading gps_data.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        flight = get_flight_for_evidence(cursor, evidence)

        if not flight:
            return jsonify({
                "evidence_id": evidence_id,
                "records": [],
                "message": "No processed flight was found for this evidence"
            }), 200

        cursor.execute(
            """
            SELECT
                gps_id AS flight_record_id,
                flight_id,
                recorded_at AS timestamp,
                latitude,
                longitude,
                altitude_m AS altitude,
                ground_speed_mps AS speed
            FROM gps_data
            WHERE flight_id = %s
            ORDER BY recorded_at ASC, gps_id ASC
            """,
            (flight["flight_id"],)
        )

        records = fetch_all(cursor)

        return jsonify({
            "evidence_id": evidence_id,
            "flight_id": flight["flight_id"],
            "flight_number": flight["flight_number"],
            "records": records
        })

    except Exception as error:
        app.logger.exception("Flight-record retrieval failed")

        return jsonify({
            "error": "Could not retrieve flight records",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# GPS ROUTE
# =========================================================

@app.route("/api/gps-route/<int:evidence_id>", methods=["GET"])
def get_gps_route(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        flight = get_flight_for_evidence(cursor, evidence)

        if not flight:
            return jsonify({
                "evidence_id": evidence_id,
                "flight_id": None,
                "route": []
            })

        cursor.execute(
            """
            SELECT
                recorded_at AS timestamp,
                latitude,
                longitude,
                altitude_m AS altitude,
                ground_speed_mps AS speed
            FROM gps_data
            WHERE flight_id = %s
            ORDER BY recorded_at ASC, gps_id ASC
            """,
            (flight["flight_id"],)
        )

        route = fetch_all(cursor)

        return jsonify({
            "evidence_id": evidence_id,
            "flight_id": flight["flight_id"],
            "route": route
        })

    except Exception as error:
        app.logger.exception("GPS route retrieval failed")

        return jsonify({
            "error": "Could not retrieve GPS route",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# FLIGHT TIMELINE
# =========================================================

@app.route("/api/timeline/<int:evidence_id>", methods=["GET"])
def get_flight_timeline(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        flight = get_flight_for_evidence(cursor, evidence)

        if not flight:
            return jsonify({
                "evidence_id": evidence_id,
                "timeline": []
            })

        cursor.execute(
            """
            SELECT *
            FROM flight_timeline
            WHERE flight_id = %s
            ORDER BY event_time ASC, sequence_no ASC
            """,
            (flight["flight_id"],)
        )

        timeline = fetch_all(cursor)

        return jsonify({
            "evidence_id": evidence_id,
            "flight_id": flight["flight_id"],
            "timeline": timeline
        })

    except Exception as error:
        app.logger.exception("Timeline retrieval failed")

        return jsonify({
            "error": "Could not retrieve timeline",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# POTENTIAL ANOMALY ANALYSIS
# =========================================================

@app.route("/api/accident-analysis/<int:evidence_id>", methods=["GET"])
def accident_analysis(evidence_id):
    connection = None
    cursor = None

    try:
        speed_threshold = float(
            request.args.get("speed_threshold", 25)
        )

        altitude_threshold = float(
            request.args.get("altitude_change_threshold", 30)
        )

        gap_threshold = float(
            request.args.get("time_gap_threshold", 60)
        )

        if (
            speed_threshold < 0
            or altitude_threshold < 0
            or gap_threshold < 0
        ):
            return jsonify({
                "error": "Analysis thresholds cannot be negative"
            }), 400

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        flight = get_flight_for_evidence(cursor, evidence)

        if not flight:
            return jsonify({
                "evidence_id": evidence_id,
                "anomalies": [],
                "message": "No processed flight was found"
            }), 200

        cursor.execute(
            """
            SELECT
                gps_id,
                recorded_at,
                latitude,
                longitude,
                altitude_m,
                ground_speed_mps
            FROM gps_data
            WHERE flight_id = %s
            ORDER BY recorded_at ASC, gps_id ASC
            """,
            (flight["flight_id"],)
        )

        records = cursor.fetchall()

        anomalies = []

        previous_record = None

        for record in records:
            timestamp = record["recorded_at"]
            latitude = record["latitude"]
            longitude = record["longitude"]
            altitude = record["altitude_m"]
            speed = record["ground_speed_mps"]

            if (
                latitude is None
                or longitude is None
                or not -90 <= float(latitude) <= 90
                or not -180 <= float(longitude) <= 180
            ):
                anomalies.append({
                    "timestamp": serialize_value(timestamp),
                    "type": "Invalid GPS",
                    "severity": "Medium",
                    "description": "GPS coordinates are missing or invalid."
                })

            if speed is not None and float(speed) > speed_threshold:
                anomalies.append({
                    "timestamp": serialize_value(timestamp),
                    "type": "High Speed",
                    "severity": "Medium",
                    "description": (
                        f"Recorded speed {float(speed):.2f} m/s "
                        f"exceeds the configured threshold "
                        f"of {speed_threshold:.2f} m/s."
                    )
                })

            if previous_record is not None:
                previous_time = previous_record["recorded_at"]

                time_gap = (
                    timestamp - previous_time
                ).total_seconds()

                if time_gap > gap_threshold:
                    anomalies.append({
                        "timestamp": serialize_value(timestamp),
                        "type": "Time Gap",
                        "severity": "Medium",
                        "description": (
                            f"A gap of {time_gap:.2f} seconds "
                            "exists between consecutive records."
                        )
                    })

                previous_altitude = previous_record["altitude_m"]

                if (
                    altitude is not None
                    and previous_altitude is not None
                ):
                    altitude_change = abs(
                        float(altitude) -
                        float(previous_altitude)
                    )

                    if altitude_change > altitude_threshold:
                        anomalies.append({
                            "timestamp": serialize_value(timestamp),
                            "type": "Altitude Change",
                            "severity": "Medium",
                            "description": (
                                f"Altitude changed by "
                                f"{altitude_change:.2f} metres "
                                "between consecutive records."
                            )
                        })

            previous_record = record

        return jsonify({
            "evidence_id": evidence_id,
            "flight_id": flight["flight_id"],
            "records_analyzed": len(records),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "thresholds": {
                "speed_threshold_mps": speed_threshold,
                "altitude_change_threshold_m": altitude_threshold,
                "time_gap_threshold_seconds": gap_threshold
            },
            "disclaimer": (
                "These results identify potential data anomalies. "
                "They do not independently establish that an accident "
                "occurred. Findings require forensic interpretation "
                "and corroborating evidence."
            )
        })

    except ValueError:
        return jsonify({
            "error": "Analysis thresholds must be valid numbers"
        }), 400

    except Exception as error:
        app.logger.exception("Accident analysis failed")

        return jsonify({
            "error": "Could not analyze flight data",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# PDF FORENSIC REPORT GENERATION
# =========================================================

@app.route("/api/reports/<int:evidence_id>", methods=["GET"])
def generate_report(evidence_id):
    connection = None
    cursor = None
    output_path = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        evidence = get_evidence(cursor, evidence_id)

        if not evidence:
            return jsonify({
                "error": "Evidence not found"
            }), 404

        cursor.execute(
            """
            SELECT *
            FROM cases
            WHERE case_id = %s
            """,
            (evidence["case_id"],)
        )

        case = cursor.fetchone()

        if not case:
            return jsonify({
                "error": "Associated case not found"
            }), 404

        hash_record = get_latest_hash(cursor, evidence_id)

        file_path = resolve_evidence_path(
            evidence["storage_path"]
        )

        current_hash = None
        integrity_status = "UNVERIFIABLE"

        if file_path and os.path.isfile(file_path) and hash_record:
            current_hash = calculate_sha256(file_path)

            integrity_status = (
                "MATCH"
                if current_hash.lower()
                == hash_record["hash_value"].lower()
                else "MISMATCH"
            )

        flight = get_flight_for_evidence(cursor, evidence)

        flight_records = []
        timeline = []
        analysis = {
            "anomalies": [],
            "anomaly_count": 0,
            "records_analyzed": 0
        }

        if flight:
            cursor.execute(
                """
                SELECT
                    gps_id AS flight_record_id,
                    recorded_at AS timestamp,
                    latitude,
                    longitude,
                    altitude_m AS altitude,
                    ground_speed_mps AS speed
                FROM gps_data
                WHERE flight_id = %s
                ORDER BY recorded_at ASC, gps_id ASC
                """,
                (flight["flight_id"],)
            )

            flight_records = fetch_all(cursor)

            cursor.execute(
                """
                SELECT *
                FROM flight_timeline
                WHERE flight_id = %s
                ORDER BY event_time ASC, sequence_no ASC
                """,
                (flight["flight_id"],)
            )

            timeline = fetch_all(cursor)

            # Apply the same default thresholds as the API.
            cursor.execute(
                """
                SELECT recorded_at, altitude_m, ground_speed_mps
                FROM gps_data
                WHERE flight_id = %s
                ORDER BY recorded_at ASC, gps_id ASC
                """,
                (flight["flight_id"],)
            )

            analysis_rows = cursor.fetchall()
            anomalies = []
            previous = None

            for row in analysis_rows:
                if (
                    row["ground_speed_mps"] is not None
                    and float(row["ground_speed_mps"]) > 25
                ):
                    anomalies.append({
                        "timestamp": serialize_value(
                            row["recorded_at"]
                        ),
                        "type": "High Speed",
                        "severity": "Medium",
                        "description": (
                            "Recorded speed exceeds 25 m/s."
                        )
                    })

                if previous is not None:
                    gap = (
                        row["recorded_at"] -
                        previous["recorded_at"]
                    ).total_seconds()

                    if gap > 60:
                        anomalies.append({
                            "timestamp": serialize_value(
                                row["recorded_at"]
                            ),
                            "type": "Time Gap",
                            "severity": "Medium",
                            "description": (
                                f"Time gap of {gap:.2f} seconds."
                            )
                        })

                    current_altitude = row["altitude_m"]
                    previous_altitude = previous["altitude_m"]

                    if (
                        current_altitude is not None
                        and previous_altitude is not None
                        and abs(
                            float(current_altitude) -
                            float(previous_altitude)
                        ) > 30
                    ):
                        anomalies.append({
                            "timestamp": serialize_value(
                                row["recorded_at"]
                            ),
                            "type": "Altitude Change",
                            "severity": "Medium",
                            "description": (
                                "Altitude changed by more than "
                                "30 metres between records."
                            )
                        })

                previous = row

            analysis = {
                "records_analyzed": len(analysis_rows),
                "anomaly_count": len(anomalies),
                "anomalies": anomalies
            }

        # Retrieve chain-of-custody history for this evidence.
        cursor.execute(
            """
            SELECT
                custody_id,
                evidence_id,
                transferred_at,
                released_by,
                received_by,
                action,
                location,
                remarks,
                created_at
            FROM chain_of_custody
            WHERE evidence_id = %s
            ORDER BY transferred_at ASC, custody_id ASC
            """,
            (evidence_id,)
        )

        custody_records = fetch_all(cursor)

        # Adapt the new schema to the existing PDF generator's format.
        report_data = {
            "case": serialize_row(case),
            "evidence": {
                "evidence_id": evidence["evidence_id"],
                "evidence_code": evidence["evidence_code"],
                "file_name": evidence["file_name"],
                "file_type": evidence["evidence_type"],
                "file_size": evidence["file_size"],
                "uploaded_at": serialize_value(
                    evidence["created_at"]
                ),
                "sha256_hash": (
                    hash_record["hash_value"]
                    if hash_record else None
                ),
                "storage_path": evidence["storage_path"]
            },
            "flight": serialize_row(flight) if flight else None,
            "flight_records": flight_records,
            "timeline": timeline,
            "chain_of_custody": custody_records,
            "accident_analysis": analysis,
            "integrity": {
                "status": integrity_status,
                "reference_hash": (
                    hash_record["hash_value"]
                    if hash_record else None
                ),
                "current_hash": current_hash
            }
        }

        report_filename = (
            "MD-DRONE-"
            + uuid.uuid4().hex[:12].upper()
            + ".pdf"
        )

        output_path = os.path.join(
            REPORT_FOLDER,
            report_filename
        )

        generate_forensic_report(
            report_data,
            output_path
        )

        if not os.path.isfile(output_path):
            raise RuntimeError(
                "The PDF report generator did not create a file."
            )

        report_hash = calculate_sha256(output_path)
        report_number = "RPT-" + uuid.uuid4().hex[:16].upper()

        cursor.execute(
            """
            INSERT INTO forensic_reports (
                case_id,
                report_number,
                report_type,
                generated_at,
                file_path,
                report_hash,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                evidence["case_id"],
                report_number,
                "Full Forensic Report",
                datetime.now(),
                output_path,
                report_hash,
                "Generated"
            )
        )

        report_id = cursor.lastrowid

        connection.commit()

        return send_file(
            output_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=report_filename
        )

    except Exception as error:
        if connection:
            connection.rollback()

        app.logger.exception("Report generation failed")

        return jsonify({
            "error": "Could not generate forensic report",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# REPORT HISTORY
# =========================================================

@app.route("/api/reports", methods=["GET"])
def get_reports():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id", type=int)

        if case_id is not None:
            cursor.execute(
                """
                SELECT *
                FROM forensic_reports
                WHERE case_id = %s
                ORDER BY generated_at DESC
                """,
                (case_id,)
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM forensic_reports
                ORDER BY generated_at DESC
                """
            )

        return jsonify({
            "reports": fetch_all(cursor)
        })

    except Exception as error:
        app.logger.exception("Report history retrieval failed")

        return jsonify({
            "error": "Could not retrieve reports",
            "details": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()



# =========================================================
# CHAIN-OF-CUSTODY MANAGEMENT
# =========================================================

@app.route(
    "/api/evidence/<int:evidence_id>/chain-of-custody",
    methods=["POST"]
)
def create_custody_record(evidence_id):
    connection = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "A JSON object is required."
            }), 400

        action = data.get("action")

        if not isinstance(action, str) or not action.strip():
            return jsonify({
                "error": "The action field is required."
            }), 400

        action = action.strip()

        if len(action) > 50:
            return jsonify({
                "error": "The action must not exceed 50 characters."
            }), 400

        optional_fields = {
            "released_by": 150,
            "received_by": 150,
            "location": 255
        }

        values = {}

        for field, max_length in optional_fields.items():
            value = data.get(field)

            if value is not None and not isinstance(value, str):
                return jsonify({
                    "error": f"The {field} field must be a string."
                }), 400

            if value is not None:
                value = value.strip()

                if len(value) > max_length:
                    return jsonify({
                        "error": (
                            f"The {field} field must not exceed "
                            f"{max_length} characters."
                        )
                    }), 400

            values[field] = value or None

        remarks = data.get("remarks")

        if remarks is not None and not isinstance(remarks, str):
            return jsonify({
                "error": "The remarks field must be a string."
            }), 400

        transferred_at = data.get("transferred_at")

        if transferred_at is not None:
            if not isinstance(transferred_at, str):
                return jsonify({
                    "error": (
                        "transferred_at must use "
                        "YYYY-MM-DD HH:MM:SS format."
                    )
                }), 400

            try:
                from datetime import datetime

                parsed_time = datetime.strptime(
                    transferred_at.strip().replace("T", " "),
                    "%Y-%m-%d %H:%M:%S"
                )

                transferred_at = parsed_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            except ValueError:
                return jsonify({
                    "error": (
                        "Invalid transferred_at. Use "
                        "YYYY-MM-DD HH:MM:SS format."
                    )
                }), 400

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE evidence_id = %s
            """,
            (evidence_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Evidence not found",
                "evidence_id": evidence_id
            }), 404

        if transferred_at is None:
            cursor.execute(
                """
                INSERT INTO chain_of_custody (
                    evidence_id,
                    released_by,
                    received_by,
                    action,
                    location,
                    remarks
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    evidence_id,
                    values["released_by"],
                    values["received_by"],
                    action,
                    values["location"],
                    remarks
                )
            )
        else:
            cursor.execute(
                """
                INSERT INTO chain_of_custody (
                    evidence_id,
                    transferred_at,
                    released_by,
                    received_by,
                    action,
                    location,
                    remarks
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    evidence_id,
                    transferred_at,
                    values["released_by"],
                    values["received_by"],
                    action,
                    values["location"],
                    remarks
                )
            )

        custody_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            """
            SELECT *
            FROM chain_of_custody
            WHERE custody_id = %s
            """,
            (custody_id,)
        )

        custody_record = cursor.fetchone()

        return jsonify({
            "message": "Chain-of-custody record created successfully.",
            "custody": serialize_row(custody_record)
        }), 201

    except Exception:
        if connection:
            connection.rollback()

        app.logger.exception("Creating chain-of-custody record failed")

        return jsonify({
            "error": "Could not create chain-of-custody record."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@app.route(
    "/api/evidence/<int:evidence_id>/chain-of-custody",
    methods=["GET"]
)
def get_custody_history(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE evidence_id = %s
            """,
            (evidence_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Evidence not found",
                "evidence_id": evidence_id
            }), 404

        cursor.execute(
            """
            SELECT *
            FROM chain_of_custody
            WHERE evidence_id = %s
            ORDER BY transferred_at ASC, custody_id ASC
            """,
            (evidence_id,)
        )

        records = fetch_all(cursor)

        return jsonify({
            "evidence_id": evidence_id,
            "total_records": len(records),
            "chain_of_custody": records
        }), 200

    except Exception:
        app.logger.exception("Retrieving chain-of-custody history failed")

        return jsonify({
            "error": "Could not retrieve chain-of-custody history."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":
    print("Starting MD-DRONE backend...")
    print("Database: drone_forensics")
    print("Backend URL: http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )