import hashlib
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.utils import secure_filename

from ..auth import login_required
from bin_file_converter import extract_logs


bin_conversion_api = Blueprint("bin_conversion_api", __name__)
MAX_BIN_BYTES = 1024 * 1024 * 1024
JOB_TTL_SECONDS = 60 * 60
_jobs = {}
_jobs_lock = threading.Lock()


def _remove_expired_jobs():
    expired = []
    now = time.monotonic()
    with _jobs_lock:
        for job_id, job in list(_jobs.items()):
            if now - job["created"] > JOB_TTL_SECONDS:
                expired.append(job["directory"].parent)
                del _jobs[job_id]
    for directory in expired:
        shutil.rmtree(directory, ignore_errors=True)


def _hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@bin_conversion_api.post("/flight-logs/convert-bin")
@login_required
def convert_bin_upload():
    _remove_expired_jobs()
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Choose a .BIN flight log first."}), 400

    filename = secure_filename(uploaded.filename)
    if not filename or Path(filename).suffix.lower() != ".bin":
        return jsonify({"error": "Only ArduPilot .BIN flight logs are supported here."}), 415

    work_dir = Path(tempfile.mkdtemp(prefix="drone-bin-convert-"))
    try:
        source_path = work_dir / filename
        total_bytes = 0
        too_large = False
        with source_path.open("wb") as source:
            while True:
                chunk = uploaded.stream.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_BIN_BYTES:
                    too_large = True
                    break
                source.write(chunk)

        if too_large:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({"error": "The BIN file exceeds the 1 GB upload limit."}), 413
        if total_bytes == 0:
            shutil.rmtree(work_dir, ignore_errors=True)
            return jsonify({"error": "The selected BIN file is empty."}), 400

        converted_dir = work_dir / "converted"
        result = extract_logs(source_path, converted_dir)
        source_path.unlink(missing_ok=True)
        summary = result["summary"]
        job_id = uuid.uuid4().hex
        files = []
        for output_file in sorted(converted_dir.iterdir()):
            if not output_file.is_file():
                continue
            files.append({
                "name": output_file.name,
                "size": output_file.stat().st_size,
                "sha256": _hash_file(output_file),
                "url": f"/api/flight-logs/conversions/{job_id}/files/{output_file.name}",
            })

        with _jobs_lock:
            _jobs[job_id] = {
                "directory": converted_dir,
                "files": {item["name"] for item in files},
                "created": time.monotonic(),
            }

        return jsonify({
            "conversion_id": job_id,
            "source_sha256": summary["source_sha256"],
            "total_records": summary["total_records"],
            "records_by_type": summary["records_by_type"],
            "files": files,
            "expires_in_seconds": JOB_TTL_SECONDS,
        }), 201
    except FileNotFoundError:
        shutil.rmtree(work_dir, ignore_errors=True)
        return jsonify({"error": "The uploaded BIN file could not be read."}), 400
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        current_app.logger.exception("BIN flight-log conversion failed")
        return jsonify({"error": "BIN conversion failed. Confirm the file is a readable ArduPilot DataFlash log."}), 422


@bin_conversion_api.get("/flight-logs/conversions/<job_id>/files/<path:filename>")
@login_required
def get_conversion_file(job_id, filename):
    _remove_expired_jobs()
    with _jobs_lock:
        job = _jobs.get(job_id)
    safe_name = secure_filename(filename)
    if not job or safe_name != filename or filename not in job["files"]:
        return jsonify({"error": "This converted file is unavailable or has expired."}), 404
    path = job["directory"] / filename
    if not path.is_file():
        return jsonify({"error": "This converted file is unavailable or has expired."}), 404
    return send_file(path, as_attachment=True, download_name=path.name, max_age=0)


@bin_conversion_api.delete("/flight-logs/conversions/<job_id>")
@login_required
def delete_conversion(job_id):
    with _jobs_lock:
        job = _jobs.pop(job_id, None)
    if not job:
        return jsonify({"message": "Conversion output was already removed."})
    shutil.rmtree(job["directory"].parent, ignore_errors=True)
    return jsonify({"message": "Converted output files removed from temporary storage."})
