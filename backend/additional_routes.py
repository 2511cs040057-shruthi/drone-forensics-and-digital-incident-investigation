import os
import json
import uuid
import hashlib

from datetime import datetime
from decimal import Decimal

from flask import (
    Blueprint,
    request,
    jsonify,
    send_file,
)

from werkzeug.utils import secure_filename

from database.db import get_connection


additional_api = Blueprint("additional_api", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_FOLDER = os.path.join(BASE_DIR, "evidence")
MEDIA_FOLDER = os.path.join(BASE_DIR, "media")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")

os.makedirs(EVIDENCE_FOLDER, exist_ok=True)
os.makedirs(MEDIA_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

MAX_UPLOAD_SIZE = 100 * 1024 * 1024

ALLOWED_MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff",
    ".mp4", ".mov", ".avi", ".mkv"
}


# =========================================================
# GENERAL HELPERS
# =========================================================

def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def serialize_row(row):
    if row is None:
        return None

    return {
        key: serialize_value(value)
        for key, value in row.items()
    }


def fetch_all(cursor):
    return [serialize_row(row) for row in cursor.fetchall()]


def calculate_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_json_data():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {}

    return data


def parse_optional_int(value, field_name):
    if value in (None, ""):
        return None

    try:
        result = int(value)

        if result < 1:
            raise ValueError

        return result

    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )


def check_case(cursor, case_id):
    cursor.execute(
        "SELECT case_id FROM cases WHERE case_id = %s",
        (case_id,)
    )

    return cursor.fetchone() is not None


def check_flight(cursor, flight_id):
    cursor.execute(
        "SELECT flight_id FROM flights WHERE flight_id = %s",
        (flight_id,)
    )

    return cursor.fetchone() is not None


def check_evidence(cursor, evidence_id):
    cursor.execute(
        "SELECT evidence_id FROM evidence WHERE evidence_id = %s",
        (evidence_id,)
    )

    return cursor.fetchone() is not None


def error_response(message, status=400):
    return jsonify({"error": message}), status


# =========================================================
# DRONE MANAGEMENT
# =========================================================

@additional_api.route("/drones", methods=["GET"])
def list_drones():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id")

        if case_id:
            case_id = parse_optional_int(case_id, "case_id")

            cursor.execute(
                """
                SELECT *
                FROM drones
                WHERE case_id = %s
                ORDER BY drone_id DESC
                """,
                (case_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM drones ORDER BY drone_id DESC"
            )

        return jsonify({"drones": fetch_all(cursor)})

    except ValueError as error:
        return error_response(str(error))

    except Exception:
        return jsonify({"error": "Could not retrieve drones."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/drones", methods=["POST"])
def create_drone():
    connection = None
    cursor = None

    try:
        data = get_json_data()

        case_id = parse_optional_int(
            data.get("case_id"), "case_id"
        )

        drone_name = str(
            data.get("drone_name", "")
        ).strip()

        if not drone_name:
            return error_response("drone_name is required.")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_case(cursor, case_id):
            return error_response("Case not found.", 404)

        cursor.execute(
            """
            INSERT INTO drones (
                case_id,
                drone_name,
                model,
                serial_number,
                flight_controller,
                firmware_version
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                drone_name,
                data.get("model"),
                data.get("serial_number"),
                data.get("flight_controller"),
                data.get("firmware_version"),
            )
        )

        drone_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM drones WHERE drone_id = %s",
            (drone_id,)
        )

        return jsonify({
            "message": "Drone registered successfully.",
            "drone": serialize_row(cursor.fetchone())
        }), 201

    except ValueError as error:
        if connection:
            connection.rollback()
        return error_response(str(error))

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({"error": "Could not register drone."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/drones/<int:drone_id>", methods=["GET"])
def get_drone(drone_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM drones WHERE drone_id = %s",
            (drone_id,)
        )

        drone = cursor.fetchone()

        if not drone:
            return error_response("Drone not found.", 404)

        return jsonify({"drone": serialize_row(drone)})

    except Exception:
        return jsonify({"error": "Could not retrieve drone."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/drones/<int:drone_id>", methods=["PUT"])
def update_drone(drone_id):
    connection = None
    cursor = None

    allowed_fields = {
        "drone_name",
        "model",
        "serial_number",
        "flight_controller",
        "firmware_version",
    }

    try:
        data = get_json_data()
        updates = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        if not updates:
            return error_response(
                "Provide at least one valid drone field to update."
            )

        if "drone_name" in updates:
            if not str(updates["drone_name"]).strip():
                return error_response("drone_name cannot be empty.")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT drone_id FROM drones WHERE drone_id = %s",
            (drone_id,)
        )

        if not cursor.fetchone():
            return error_response("Drone not found.", 404)

        assignments = ", ".join(
            f"{field} = %s" for field in updates
        )

        values = list(updates.values()) + [drone_id]

        cursor.execute(
            f"UPDATE drones SET {assignments} WHERE drone_id = %s",
            values
        )

        connection.commit()

        cursor.execute(
            "SELECT * FROM drones WHERE drone_id = %s",
            (drone_id,)
        )

        return jsonify({
            "message": "Drone updated successfully.",
            "drone": serialize_row(cursor.fetchone())
        })

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({"error": "Could not update drone."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# FLIGHT MANAGEMENT
# =========================================================

@additional_api.route("/flights", methods=["GET"])
def list_flights():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id")
        drone_id = request.args.get("drone_id")

        query = """
            SELECT
                f.*,
                d.drone_name,
                d.model AS drone_model
            FROM flights f
            LEFT JOIN drones d ON d.drone_id = f.drone_id
        """

        conditions = []
        parameters = []

        if case_id:
            conditions.append("f.case_id = %s")
            parameters.append(
                parse_optional_int(case_id, "case_id")
            )

        if drone_id:
            conditions.append("f.drone_id = %s")
            parameters.append(
                parse_optional_int(drone_id, "drone_id")
            )

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY f.flight_id DESC"

        cursor.execute(query, tuple(parameters))

        return jsonify({"flights": fetch_all(cursor)})

    except ValueError as error:
        return error_response(str(error))

    except Exception:
        return jsonify({"error": "Could not retrieve flights."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/flights", methods=["POST"])
def create_flight():
    connection = None
    cursor = None

    try:
        data = get_json_data()

        case_id = parse_optional_int(
            data.get("case_id"), "case_id"
        )

        drone_id = parse_optional_int(
            data.get("drone_id"), "drone_id"
        )

        flight_number = str(
            data.get("flight_number", "")
        ).strip()

        if not flight_number:
            return error_response("flight_number is required.")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_case(cursor, case_id):
            return error_response("Case not found.", 404)

        cursor.execute(
            """
            SELECT drone_id
            FROM drones
            WHERE drone_id = %s AND case_id = %s
            """,
            (drone_id, case_id)
        )

        if not cursor.fetchone():
            return error_response(
                "Drone not found in the specified case.", 404
            )

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
                data.get("start_time"),
                data.get("end_time"),
                data.get("flight_duration_seconds"),
                data.get("flight_status", "Recorded"),
                data.get("source_storage"),
            )
        )

        flight_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM flights WHERE flight_id = %s",
            (flight_id,)
        )

        return jsonify({
            "message": "Flight registered successfully.",
            "flight": serialize_row(cursor.fetchone())
        }), 201

    except ValueError as error:
        if connection:
            connection.rollback()
        return error_response(str(error))

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({"error": "Could not register flight."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/flights/<int:flight_id>", methods=["GET"])
def get_flight(flight_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT f.*, d.drone_name, d.model AS drone_model
            FROM flights f
            LEFT JOIN drones d ON d.drone_id = f.drone_id
            WHERE f.flight_id = %s
            """,
            (flight_id,)
        )

        flight = cursor.fetchone()

        if not flight:
            return error_response("Flight not found.", 404)

        return jsonify({"flight": serialize_row(flight)})

    except Exception:
        return jsonify({"error": "Could not retrieve flight."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# SENSOR DATA
# =========================================================

@additional_api.route("/flights/<int:flight_id>/sensors", methods=["GET"])
def get_sensor_data(flight_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_flight(cursor, flight_id):
            return error_response("Flight not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM sensor_data
            WHERE flight_id = %s
            ORDER BY recorded_at ASC, sensor_id ASC
            """,
            (flight_id,)
        )

        return jsonify({
            "flight_id": flight_id,
            "records": fetch_all(cursor)
        })

    except Exception:
        return jsonify({
            "error": "Could not retrieve sensor data."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/flights/<int:flight_id>/sensors", methods=["POST"])
def add_sensor_data(flight_id):
    connection = None
    cursor = None

    numeric_fields = [
        "accel_x", "accel_y", "accel_z",
        "gyro_x", "gyro_y", "gyro_z",
        "heading_deg", "baro_altitude_m",
        "pressure_hpa", "battery_voltage_v",
        "battery_current_a", "battery_remaining_pct",
    ]

    try:
        data = get_json_data()

        recorded_at = data.get("recorded_at")

        if not recorded_at:
            return error_response("recorded_at is required.")

        if "extra_json" in data and data["extra_json"] is not None:
            if not isinstance(data["extra_json"], (dict, list)):
                return error_response(
                    "extra_json must be a JSON object or array."
                )

            extra_json = json.dumps(data["extra_json"])
        else:
            extra_json = None

        values = [data.get(field) for field in numeric_fields]

        remaining = data.get("battery_remaining_pct")

        if remaining is not None:
            if not 0 <= float(remaining) <= 100:
                return error_response(
                    "battery_remaining_pct must be between 0 and 100."
                )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_flight(cursor, flight_id):
            return error_response("Flight not found.", 404)

        cursor.execute(
            """
            INSERT INTO sensor_data (
                flight_id, recorded_at,
                accel_x, accel_y, accel_z,
                gyro_x, gyro_y, gyro_z,
                heading_deg, baro_altitude_m,
                pressure_hpa, battery_voltage_v,
                battery_current_a, battery_remaining_pct,
                extra_json
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                flight_id,
                recorded_at,
                *values,
                extra_json,
            )
        )

        sensor_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM sensor_data WHERE sensor_id = %s",
            (sensor_id,)
        )

        return jsonify({
            "message": "Sensor record saved.",
            "record": serialize_row(cursor.fetchone())
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Could not save sensor data. Check the supplied values."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# FORENSIC EVENTS
# =========================================================

@additional_api.route("/flights/<int:flight_id>/events", methods=["GET"])
def list_forensic_events(flight_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_flight(cursor, flight_id):
            return error_response("Flight not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM forensic_events
            WHERE flight_id = %s
            ORDER BY event_time ASC, event_id ASC
            """,
            (flight_id,)
        )

        return jsonify({
            "flight_id": flight_id,
            "events": fetch_all(cursor)
        })

    except Exception:
        return jsonify({
            "error": "Could not retrieve forensic events."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/flights/<int:flight_id>/events", methods=["POST"])
def create_forensic_event(flight_id):
    connection = None
    cursor = None

    try:
        data = get_json_data()

        event_time = data.get("event_time")
        event_type = str(data.get("event_type", "")).strip()
        description = str(data.get("description", "")).strip()

        if not event_time or not event_type or not description:
            return error_response(
                "event_time, event_type, and description are required."
            )

        severity = data.get("severity", "Info")

        allowed_severities = {
            "Info", "Low", "Medium", "High", "Critical"
        }

        if severity not in allowed_severities:
            return error_response(
                "severity must be Info, Low, Medium, High, or Critical."
            )

        ai_flag = data.get("ai_flag", False)

        if not isinstance(ai_flag, bool):
            return error_response("ai_flag must be true or false.")

        confidence = data.get("confidence")

        if confidence is not None:
            confidence = float(confidence)

            if not 0 <= confidence <= 1:
                return error_response(
                    "confidence must be between 0 and 1."
                )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_flight(cursor, flight_id):
            return error_response("Flight not found.", 404)

        cursor.execute(
            """
            INSERT INTO forensic_events (
                flight_id, event_time, event_type,
                severity, description, source,
                ai_flag, confidence
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                flight_id,
                event_time,
                event_type,
                severity,
                description,
                data.get("source", "Manual Investigation"),
                ai_flag,
                confidence,
            )
        )

        event_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM forensic_events WHERE event_id = %s",
            (event_id,)
        )

        return jsonify({
            "message": "Forensic event recorded.",
            "event": serialize_row(cursor.fetchone())
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Could not record forensic event."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# CHAIN OF CUSTODY
# =========================================================

@additional_api.route(
    "/evidence/<int:evidence_id>/custody",
    methods=["GET"]
)
def get_chain_of_custody(evidence_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_evidence(cursor, evidence_id):
            return error_response("Evidence not found.", 404)

        cursor.execute(
            """
            SELECT *
            FROM chain_of_custody
            WHERE evidence_id = %s
            ORDER BY transferred_at ASC, custody_id ASC
            """,
            (evidence_id,)
        )

        return jsonify({
            "evidence_id": evidence_id,
            "chain_of_custody": fetch_all(cursor)
        })

    except Exception:
        return jsonify({
            "error": "Could not retrieve chain of custody."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route(
    "/evidence/<int:evidence_id>/custody",
    methods=["POST"]
)
def add_chain_of_custody(evidence_id):
    connection = None
    cursor = None

    try:
        data = get_json_data()

        action = str(data.get("action", "")).strip()
        released_by = str(data.get("released_by", "")).strip()
        received_by = str(data.get("received_by", "")).strip()

        if not action or not released_by or not received_by:
            return error_response(
                "action, released_by, and received_by are required."
            )

        transferred_at = data.get("transferred_at")

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_evidence(cursor, evidence_id):
            return error_response("Evidence not found.", 404)

        cursor.execute(
            """
            INSERT INTO chain_of_custody (
                evidence_id, transferred_at,
                released_by, received_by,
                action, location, remarks
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                evidence_id,
                transferred_at or datetime.now(),
                released_by,
                received_by,
                action,
                data.get("location"),
                data.get("remarks"),
            )
        )

        custody_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM chain_of_custody WHERE custody_id = %s",
            (custody_id,)
        )

        return jsonify({
            "message": "Chain-of-custody entry recorded.",
            "entry": serialize_row(cursor.fetchone())
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Could not record chain of custody."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# BOOKMARKED EVIDENCE
# =========================================================

@additional_api.route("/bookmarks", methods=["GET"])
def list_bookmarks():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id")

        query = """
            SELECT
                b.*,
                e.file_name,
                e.evidence_code,
                e.verification_status,
                h.hash_value AS evidence_reference_hash,
                h.hash_algorithm AS evidence_hash_algorithm
            FROM bookmarked_evidence b
            JOIN evidence e ON e.evidence_id = b.evidence_id
            LEFT JOIN hash_records h
                ON h.hash_id = (
                    SELECT MAX(h2.hash_id)
                    FROM hash_records h2
                    WHERE h2.evidence_id = b.evidence_id
                      AND h2.hash_algorithm = 'SHA-256'
                )
        """

        parameters = []

        if case_id:
            query += " WHERE b.case_id = %s"
            parameters.append(
                parse_optional_int(case_id, "case_id")
            )

        query += " ORDER BY b.created_at DESC, b.bookmark_id DESC"

        cursor.execute(query, tuple(parameters))

        return jsonify({"bookmarks": fetch_all(cursor)})

    except ValueError as error:
        return error_response(str(error))

    except Exception:
        return jsonify({"error": "Could not retrieve bookmarks."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/bookmarks", methods=["POST"])
def create_bookmark():
    connection = None
    cursor = None

    try:
        data = get_json_data()

        case_id = parse_optional_int(
            data.get("case_id"), "case_id"
        )

        evidence_id = parse_optional_int(
            data.get("evidence_id"), "evidence_id"
        )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_case(cursor, case_id):
            return error_response("Case not found.", 404)

        cursor.execute(
            """
            SELECT evidence_id, case_id
            FROM evidence
            WHERE evidence_id = %s
            """,
            (evidence_id,)
        )

        evidence = cursor.fetchone()

        if not evidence:
            return error_response("Evidence not found.", 404)

        if evidence["case_id"] != case_id:
            return error_response(
                "Evidence does not belong to the specified case."
            )

        cursor.execute(
            """
            SELECT hash_value
            FROM hash_records
            WHERE evidence_id = %s
              AND hash_algorithm = 'SHA-256'
            ORDER BY hash_id DESC
            LIMIT 1
            """,
            (evidence_id,)
        )
        hash_record = cursor.fetchone()
        trusted_hash = hash_record["hash_value"] if hash_record else None

        cursor.execute(
            """
            INSERT INTO bookmarked_evidence (
                case_id, evidence_id, item_number,
                evidence_category, description,
                source, sha256_hash, tag
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                evidence_id,
                data.get("item_number"),
                data.get("evidence_category"),
                data.get("description"),
                data.get("source"),
                trusted_hash,
                data.get("tag"),
            )
        )

        bookmark_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            """
            SELECT *
            FROM bookmarked_evidence
            WHERE bookmark_id = %s
            """,
            (bookmark_id,)
        )

        return jsonify({
            "message": "Evidence bookmarked successfully.",
            "bookmark": serialize_row(cursor.fetchone())
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({
            "error": "Could not create bookmark."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route(
    "/bookmarks/<int:bookmark_id>",
    methods=["DELETE"]
)
def delete_bookmark(bookmark_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM bookmarked_evidence WHERE bookmark_id = %s",
            (bookmark_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return error_response("Bookmark not found.", 404)

        connection.commit()

        return jsonify({
            "message": "Bookmark deleted successfully."
        })

    except Exception:
        if connection:
            connection.rollback()
        return jsonify({"error": "Could not delete bookmark."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================
# MEDIA UPLOAD AND METADATA
# =========================================================

@additional_api.route("/media", methods=["GET"])
def list_media():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        case_id = request.args.get("case_id")

        if case_id:
            case_id = parse_optional_int(case_id, "case_id")

            cursor.execute(
                """
                SELECT *
                FROM media
                WHERE case_id = %s
                ORDER BY media_id DESC
                """,
                (case_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM media ORDER BY media_id DESC"
            )

        return jsonify({"media": fetch_all(cursor)})

    except ValueError as error:
        return error_response(str(error))

    except Exception:
        return jsonify({"error": "Could not retrieve media."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route("/media/upload", methods=["POST"])
def upload_media():
    connection = None
    cursor = None
    saved_path = None

    try:
        uploaded_file = request.files.get("file")

        if not uploaded_file or not uploaded_file.filename:
            return error_response("A media file is required.")

        original_name = secure_filename(uploaded_file.filename)

        if not original_name:
            return error_response("Invalid filename.")

        extension = os.path.splitext(original_name)[1].lower()

        if extension not in ALLOWED_MEDIA_EXTENSIONS:
            return error_response(
                "Unsupported media format.",
                415
            )

        case_id = parse_optional_int(
            request.form.get("case_id"), "case_id"
        )

        flight_id = parse_optional_int(
            request.form.get("flight_id"), "flight_id"
        )

        media_type = (
            "Image"
            if extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
            else "Video"
        )

        unique_name = uuid.uuid4().hex + "_" + original_name
        saved_path = os.path.join(MEDIA_FOLDER, unique_name)

        uploaded_file.save(saved_path)

        file_size = os.path.getsize(saved_path)

        if file_size > MAX_UPLOAD_SIZE:
            os.remove(saved_path)
            return error_response("File exceeds the 100 MB limit.", 413)

        file_hash = calculate_sha256(saved_path)

        captured_at = None
        latitude = None
        longitude = None
        metadata = {}

        if media_type == "Image":
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS, GPSTAGS

                with Image.open(saved_path) as image:
                    exif = image.getexif()

                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))

                        if tag_name != "GPSInfo":
                            metadata[tag_name] = str(value)

                    gps_info = exif.get_ifd(34853)

                    if gps_info:
                        readable_gps = {
                            GPSTAGS.get(key, str(key)): value
                            for key, value in gps_info.items()
                        }

                        def to_decimal(value):
                            return (
                                float(value[0])
                                + float(value[1]) / 60
                                + float(value[2]) / 3600
                            )

                        if (
                            "GPSLatitude" in readable_gps
                            and "GPSLongitude" in readable_gps
                        ):
                            latitude = to_decimal(
                                readable_gps["GPSLatitude"]
                            )

                            longitude = to_decimal(
                                readable_gps["GPSLongitude"]
                            )

                            if readable_gps.get("GPSLatitudeRef") == "S":
                                latitude = -latitude

                            if readable_gps.get("GPSLongitudeRef") == "W":
                                longitude = -longitude

                    captured_at = (
                        metadata.get("DateTimeOriginal")
                        or metadata.get("DateTime")
                    )

            except ImportError:
                metadata["metadata_note"] = (
                    "Install Pillow to extract image EXIF metadata."
                )

            except Exception as metadata_error:
                metadata["metadata_note"] = (
                    "Image saved; EXIF extraction was unavailable: "
                    + str(metadata_error)
                )

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        if not check_case(cursor, case_id):
            os.remove(saved_path)
            saved_path = None
            return error_response("Case not found.", 404)

        if flight_id is not None:
            cursor.execute(
                """
                SELECT flight_id, case_id
                FROM flights
                WHERE flight_id = %s
                """,
                (flight_id,)
            )

            flight = cursor.fetchone()

            if not flight:
                os.remove(saved_path)
                saved_path = None
                return error_response("Flight not found.", 404)

            if flight["case_id"] != case_id:
                os.remove(saved_path)
                saved_path = None
                return error_response(
                    "Flight does not belong to the specified case."
                )

        cursor.execute(
            """
            INSERT INTO media (
                case_id, flight_id, file_name, media_type,
                file_size, captured_at, latitude, longitude,
                storage_path, sha256
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                case_id,
                flight_id,
                original_name,
                media_type,
                file_size,
                captured_at,
                latitude,
                longitude,
                saved_path,
                file_hash,
            )
        )

        media_id = cursor.lastrowid
        connection.commit()

        cursor.execute(
            "SELECT * FROM media WHERE media_id = %s",
            (media_id,)
        )

        return jsonify({
            "message": "Media uploaded successfully.",
            "media": serialize_row(cursor.fetchone()),
            "sha256": file_hash,
            "extracted_metadata": metadata,
        }), 201

    except ValueError as error:
        if connection:
            connection.rollback()
        return error_response(str(error))

    except Exception:
        if connection:
            connection.rollback()

        if saved_path and os.path.isfile(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                pass

        return jsonify({
            "error": "Could not upload media. Check the database and file."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# =========================================================
# MEDIA INTEGRITY VERIFICATION
# =========================================================

@additional_api.route(
    "/media/<int:media_id>/verify",
    methods=["GET"]
)
def verify_media(media_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                media_id,
                case_id,
                flight_id,
                file_name,
                storage_path,
                sha256
            FROM media
            WHERE media_id = %s
            """,
            (media_id,)
        )

        media = cursor.fetchone()

        if not media:
            return error_response("Media record not found.", 404)

        stored_hash = media.get("sha256")
        storage_path = media.get("storage_path")

        reference_hash = (
            str(stored_hash).strip().lower()
            if stored_hash
            else None
        )

        def finish_verification(
            status,
            message,
            current_hash=None,
            integrity_verified=None
        ):
            cursor.execute(
                """
                INSERT INTO media_verification_history (
                    media_id,
                    reference_hash,
                    current_hash,
                    verification_status,
                    message
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    media_id,
                    reference_hash,
                    current_hash,
                    status,
                    message
                )
            )

            verification_id = cursor.lastrowid
            connection.commit()

            return jsonify({
                "verification_id": verification_id,
                "media_id": media["media_id"],
                "case_id": media["case_id"],
                "flight_id": media["flight_id"],
                "file_name": media["file_name"],
                "algorithm": "SHA-256",
                "reference_hash": reference_hash,
                "current_hash": current_hash,
                "status": status,
                "integrity_verified": integrity_verified,
                "message": message
            }), 200

        if not stored_hash or not storage_path:
            return finish_verification(
                "UNVERIFIABLE",
                "The stored hash or file path is missing."
            )

        media_root = os.path.realpath(MEDIA_FOLDER)
        actual_path = os.path.realpath(storage_path)

        try:
            if os.path.commonpath(
                [media_root, actual_path]
            ) != media_root:
                return finish_verification(
                    "UNVERIFIABLE",
                    "The file is outside the configured "
                    "media storage directory."
                )

        except ValueError:
            return finish_verification(
                "UNVERIFIABLE",
                "The stored file path is invalid."
            )

        if not os.path.isfile(actual_path):
            return finish_verification(
                "UNVERIFIABLE",
                "The stored media file was not found."
            )

        try:
            current_hash = calculate_sha256(actual_path).lower()

        except OSError:
            return finish_verification(
                "UNVERIFIABLE",
                "The media file exists but could not be read."
            )

        if reference_hash == current_hash:
            return finish_verification(
                "MATCH",
                "The current file hash matches the stored hash.",
                current_hash=current_hash,
                integrity_verified=True
            )

        return finish_verification(
            "MISMATCH",
            "The current file hash differs from the stored hash.",
            current_hash=current_hash,
            integrity_verified=False
        )

    except Exception:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass

        additional_api.logger.exception(
    "Media integrity verification failed for media_id=%s",
    media_id
)

        return jsonify({
            "error": (
                "Could not verify media integrity or record "
                "the verification result."
            )
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@additional_api.route(
    "/media/<int:media_id>/verification-history",
    methods=["GET"]
)
def get_media_verification_history(media_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT media_id
            FROM media
            WHERE media_id = %s
            """,
            (media_id,)
        )

        if not cursor.fetchone():
            return error_response("Media record not found.", 404)

        cursor.execute(
            """
            SELECT
                verification_id,
                media_id,
                reference_hash,
                current_hash,
                verification_status,
                message,
                verified_at
            FROM media_verification_history
            WHERE media_id = %s
            ORDER BY verified_at DESC, verification_id DESC
            """,
            (media_id,)
        )

        records = cursor.fetchall()

        return jsonify({
            "media_id": media_id,
            "total_attempts": len(records),
            "history": records
        }), 200

    except Exception:
        additional_api.logger.exception(
    "Could not retrieve media verification history "
    "for media_id=%s",
    media_id
)

        return jsonify({
            "error": "Could not retrieve media verification history."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


@additional_api.route("/reports/<int:report_id>/verify", methods=["GET"])
def verify_report(report_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM forensic_reports
            WHERE report_id = %s
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            return error_response("Report not found.", 404)

        report = serialize_row(report)
        path = report.get("file_path")
        reference_hash = report.get("report_hash")

        if not path or not os.path.isfile(path):
            return jsonify({
                "report_id": report_id,
                "status": "UNVERIFIABLE",
                "integrity_verified": False,
                "message": "The stored report file could not be found."
            })

        if not reference_hash:
            return jsonify({
                "report_id": report_id,
                "status": "UNVERIFIABLE",
                "integrity_verified": False,
                "message": "No reference hash is stored for this report."
            })

        current_hash = calculate_sha256(path)

        matches = (
            current_hash.lower() == reference_hash.lower()
        )

        return jsonify({
            "report_id": report_id,
            "status": "MATCH" if matches else "MISMATCH",
            "integrity_verified": matches,
            "reference_sha256": reference_hash,
            "calculated_sha256": current_hash,
        })

    except Exception:
        return jsonify({
            "error": "Could not verify report integrity."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@additional_api.route(
    "/reports/<int:report_id>/download",
    methods=["GET"]
)
def download_report(report_id):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT report_id, report_number, file_path
            FROM forensic_reports
            WHERE report_id = %s
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            return error_response("Report not found.", 404)

        path = report["file_path"]

        if not path or not os.path.isfile(path):
            return error_response(
                "The generated report file is missing.",
                404
            )

        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.basename(path),
        )

    except Exception:
        return jsonify({"error": "Could not download report."}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()