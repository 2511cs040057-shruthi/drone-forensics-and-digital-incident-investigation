"""Read-only, SHA-256-verified ArduPilot CSV telemetry for a registered case."""

import csv
import hashlib
import math
from pathlib import Path

from flask import Blueprint, current_app, jsonify
from sqlalchemy import select

from backend.auth import login_required
from backend.models.case import Case
from backend.models.evidence import Evidence
from backend.services.database import SessionLocal
from backend.routes.autopsy_import import get_received_cases_directory

telemetry_api = Blueprint("telemetry_api", __name__)

CHANNELS = tuple(f"C{i}" for i in range(1, 15))
EXPECTED = {
    "ATT.csv": ("TimeUS", "Roll", "Pitch", "Yaw"),
    "CTUN.csv": ("TimeUS", "Alt", "ThO"),
    "GPS.csv": ("TimeUS", "Status", "NSats", "Lat", "Lng"),
    "RCOU.csv": ("TimeUS", "C1", "C2", "C3", "C4"),
    "VIBE.csv": ("TimeUS", "VibeX", "VibeY", "VibeZ", "Clip"),
    "MODE.csv": ("TimeUS", "Mode", "ModeNum", "Rsn"),
    "RCIN.csv": ("TimeUS", "C1", "C2", "C3", "C4"),
    "BARO.csv": ("TimeUS", "Press", "Temp", "Alt", "CRt"),
    "IMU.csv": ("TimeUS", "GyrX", "GyrY", "GyrZ", "AccX", "AccY", "AccZ", "T"),
}
MAX_CSV_BYTES = 100 * 1024 * 1024
MAX_RECORDS_PER_FILE = 250_000


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_csv(path, filename, evidence_id):
    fields = EXPECTED[filename]
    records = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(fields).issubset(reader.fieldnames):
            raise ValueError(f"{filename} is missing required telemetry columns")
        for row in reader:
            if len(records) >= MAX_RECORDS_PER_FILE:
                raise ValueError(f"{filename} exceeds the supported record limit")
            micros = _number(row.get("TimeUS"))
            if micros is None or micros < 0:
                continue
            point = {"time_us": micros, "time_s": round(micros / 1_000_000, 6)}
            if filename == "ATT.csv":
                point.update({name.lower(): _number(row.get(name)) for name in ("Roll", "Pitch", "Yaw")})
            elif filename == "CTUN.csv":
                point.update({
                    "altitude_m": _number(row.get("Alt")),
                    "throttle_output": _number(row.get("ThO")),
                    "climb_rate_m_s": _number(row.get("CRt")),
                })
            elif filename == "GPS.csv":
                status = _number(row.get("Status"))
                satellites = _number(row.get("NSats"))
                latitude = _number(row.get("Lat"))
                longitude = _number(row.get("Lng"))
                valid = (
                    status is not None and status >= 3
                    and satellites is not None and satellites > 0
                    and latitude is not None and longitude is not None
                    and -90 <= latitude <= 90 and -180 <= longitude <= 180
                    and not (latitude == 0 and longitude == 0)
                )
                point.update({
                    "status": status,
                    "satellites": satellites,
                    "hdop": _number(row.get("HDop")),
                    "latitude": latitude if valid else None,
                    "longitude": longitude if valid else None,
                    "gps_valid": valid,
                    "ground_speed_m_s": _number(row.get("Spd")) if valid else None,
                })
            elif filename in ("RCOU.csv", "RCIN.csv"):
                # Preserve channel labels: mapping a channel to a physical motor
                # or transmitter control requires vehicle configuration evidence.
                point["channels"] = {channel: _number(row.get(channel)) for channel in CHANNELS if channel in reader.fieldnames}
            elif filename == "VIBE.csv":
                point.update({
                    "imu": _number(row.get("IMU")),
                    "vibration_x": _number(row.get("VibeX")),
                    "vibration_y": _number(row.get("VibeY")),
                    "vibration_z": _number(row.get("VibeZ")),
                    "clip": _number(row.get("Clip")),
                })
            elif filename == "MODE.csv":
                # Keep raw mode numbers and reason codes; do not guess labels.
                point.update({
                    "mode": _number(row.get("Mode")),
                    "mode_num": _number(row.get("ModeNum")),
                    "reason_code": _number(row.get("Rsn")),
                })
            elif filename == "BARO.csv":
                point.update({
                    "instance": _number(row.get("I")),
                    "pressure_pa": _number(row.get("Press")),
                    "temperature_c": _number(row.get("Temp")),
                    "altitude_m": _number(row.get("Alt")),
                    "climb_rate_m_s": _number(row.get("CRt")),
                })
            elif filename == "IMU.csv":
                point.update({
                    "instance": _number(row.get("I")),
                    "gyro_x_rad_s": _number(row.get("GyrX")),
                    "gyro_y_rad_s": _number(row.get("GyrY")),
                    "gyro_z_rad_s": _number(row.get("GyrZ")),
                    "accel_x_m_s2": _number(row.get("AccX")),
                    "accel_y_m_s2": _number(row.get("AccY")),
                    "accel_z_m_s2": _number(row.get("AccZ")),
                    "temperature_c": _number(row.get("T")),
                })
            records.append(point)
    return {"evidence_id": evidence_id, "filename": filename, "count": len(records), "records": records}


@telemetry_api.get("/cases/<int:case_id>/telemetry")
@login_required
def case_telemetry(case_id):
    try:
        with SessionLocal() as session:
            if session.get(Case, case_id) is None:
                return jsonify({"error": "Case not found"}), 404
            rows = session.execute(
                select(Evidence).where(
                    Evidence.case_id == case_id,
                    Evidence.filename.in_(list(EXPECTED)),
                ).order_by(Evidence.evidence_id)
            ).scalars().all()
            files = [
                {"id": e.evidence_id, "name": e.filename, "path": e.storage_path,
                 "hash": e.sha256, "import_status": e.verification_status,
                 "export_id": e.autopsy_export_id}
                for e in rows
            ]

        root = Path(get_received_cases_directory()).resolve(strict=True)
        output = {}
        problems = []
        for filename in EXPECTED:
            matches = [e for e in files if e["name"].casefold() == filename.casefold()]
            if not matches:
                problems.append({"filename": filename, "reason": "Not registered in this case"})
                continue
            if len(matches) > 1:
                problems.append({"filename": filename, "reason": "Multiple matching evidence records; selection is ambiguous"})
                continue
            entry = matches[0]
            path = Path(entry["path"]).resolve(strict=False)
            allowed = (root / entry["export_id"] / "evidence").resolve(strict=False)
            if not path.is_relative_to(allowed) or path == allowed:
                problems.append({"filename": filename, "reason": "Evidence path is outside its approved export directory"})
                continue
            stage = "checking file existence"
            try:
                if not path.is_file():
                    raise FileNotFoundError("Evidence file is missing")
                stage = "reading file metadata"
                if path.stat().st_size > MAX_CSV_BYTES:
                    raise ValueError("Evidence file exceeds the supported size limit")
                stage = "verifying SHA-256"
                if not entry["hash"] or _sha256(path).lower() != entry["hash"].lower():
                    raise ValueError("Evidence SHA-256 mismatch; telemetry was not loaded")
                stage = "parsing verified CSV"
                output[filename.removesuffix(".csv").lower()] = _load_csv(path, filename, entry["id"])
            except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                # Preserve the original failure, but identify the exact operation.
                # This does not bypass path validation or SHA-256 checks.
                problems.append({"filename": filename, "reason": f"{stage}: {exc}"})

        gps = output.get("gps", {}).get("records", [])
        times = [r["time_us"] for group in output.values() for r in group["records"]]
        return jsonify({
            "case_id": case_id,
            "source": "Registered Autopsy CSV evidence; SHA-256 checked at request time",
            "time_reference": "ArduPilot TimeUS (microseconds since boot); not UTC",
            "time_start_us": min(times) if times else None,
            "duration_s": round((max(times) - min(times)) / 1_000_000, 3) if times else None,
            "gps_fix_available": any(r["gps_valid"] for r in gps),
            "series": output,
            "warnings": problems,
        }), 200
    except OSError:
        return jsonify({"error": "Autopsy evidence storage is unavailable"}), 503
    except Exception:
        current_app.logger.exception("Telemetry retrieval failed for case %s", case_id)
        return jsonify({"error": "Unable to retrieve telemetry"}), 500
