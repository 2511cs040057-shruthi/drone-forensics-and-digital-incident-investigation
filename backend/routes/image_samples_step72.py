"""Step 72: separately labelled, investigator-supplied sample image gallery.

These files are NOT asserted to be drone-captured or original camera evidence.
The module does not insert them into the Autopsy evidence register.
"""
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file
from sqlalchemy import text
from backend.auth import login_required
from backend.models.case import Case
from backend.services.database import SessionLocal

image_samples_api = Blueprint('image_samples_api', __name__)
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED = {'JPEG', 'PNG'}


def _storage_root():
    # Set MD_DRONE_SAMPLE_IMAGE_DIR to a persistent, access-controlled directory.
    configured = os.environ.get('MD_DRONE_SAMPLE_IMAGE_DIR')
    root = Path(configured).expanduser() if configured else Path.cwd() / 'sample_image_gallery'
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _create_table(session):
    session.execute(text('''CREATE TABLE IF NOT EXISTS image_samples_step72 (
        sample_id VARCHAR(36) PRIMARY KEY,
        case_id INT NOT NULL,
        original_name VARCHAR(255) NOT NULL,
        stored_name VARCHAR(64) NOT NULL,
        sha256 CHAR(64) NOT NULL,
        byte_size BIGINT NOT NULL,
        width INT NOT NULL,
        height INT NOT NULL,
        format VARCHAR(12) NOT NULL,
        exif_json LONGTEXT NOT NULL,
        observation_time VARCHAR(64) NULL,
        notes TEXT NULL,
        created_utc VARCHAR(40) NOT NULL,
        INDEX ix_sample_case (case_id)
    )'''))


def _case_exists(session, case_id):
    return session.get(Case, case_id) is not None


def _item(row):
    return {
        'sample_id': row['sample_id'], 'case_id': row['case_id'],
        'filename': row['original_name'], 'sha256': row['sha256'],
        'byte_size': row['byte_size'], 'width': row['width'],
        'height': row['height'], 'format': row['format'],
        'exif': json.loads(row['exif_json']),
        'observation_time': row['observation_time'], 'notes': row['notes'],
        'created_utc': row['created_utc'],
        'classification': 'EXTERNAL SAMPLE — NOT VERIFIED DRONE-CAPTURED EVIDENCE',
    }


def _get_row(session, case_id, sample_id):
    return session.execute(text('SELECT * FROM image_samples_step72 WHERE case_id=:case_id AND sample_id=:sample_id'),
                           {'case_id': case_id, 'sample_id': sample_id}).mappings().first()


@image_samples_api.get('/cases/<int:case_id>/image-samples')
@login_required
def list_samples(case_id):
    with SessionLocal() as session:
        if not _case_exists(session, case_id):
            return jsonify(error='Case not found'), 404
        _create_table(session)
        rows = session.execute(text('SELECT * FROM image_samples_step72 WHERE case_id=:case_id ORDER BY created_utc, sample_id'),
                               {'case_id': case_id}).mappings().all()
        session.commit()
        return jsonify(samples=[_item(row) for row in rows]), 200


@image_samples_api.post('/cases/<int:case_id>/image-samples')
@login_required
def upload_sample(case_id):
    from PIL import Image, UnidentifiedImageError
    upload = request.files.get('image')
    if not upload or not upload.filename:
        return jsonify(error='Select a JPEG or PNG image'), 400
    name = Path(upload.filename.replace('\\', '/')).name[:255]
    if not re.search(r'\.(jpe?g|png)$', name, re.I):
        return jsonify(error='Only JPEG or PNG files are supported'), 400
    raw = upload.stream.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        return jsonify(error='Image exceeds 20 MB limit'), 413
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            fmt = image.format
            width, height = image.size
            if fmt not in ALLOWED or width * height > 80_000_000:
                return jsonify(error='Unsupported image format or dimensions'), 400
            # Store only non-sensitive, directly reported EXIF fields; no invented values.
            exif = image.getexif()
            tags = {306: 'DateTime', 36867: 'DateTimeOriginal', 36868: 'DateTimeDigitized',
                    271: 'Make', 272: 'Model', 305: 'Software', 274: 'Orientation'}
            metadata = {label: str(exif.get(tag))[:256] for tag, label in tags.items() if exif.get(tag) is not None}
    except (UnidentifiedImageError, OSError, ValueError, OverflowError):
        return jsonify(error='Invalid or corrupted image'), 400
    notes = request.form.get('notes', '')[:2000]
    observation = request.form.get('observation_time', '')[:64] or None
    sample_id = str(uuid.uuid4())
    stored_name = sample_id + ('.jpg' if fmt == 'JPEG' else '.png')
    digest = hashlib.sha256(raw).hexdigest()
    root = _storage_root()
    path = root / stored_name
    try:
        with SessionLocal() as session:
            if not _case_exists(session, case_id):
                return jsonify(error='Case not found'), 404
            _create_table(session)
            # Exclusive creation prevents accidental overwrites.
            with path.open('xb') as output:
                output.write(raw)
            try:
                session.execute(text('''INSERT INTO image_samples_step72
                    (sample_id,case_id,original_name,stored_name,sha256,byte_size,width,height,format,exif_json,observation_time,notes,created_utc)
                    VALUES (:sample_id,:case_id,:original_name,:stored_name,:sha256,:byte_size,:width,:height,:format,:exif_json,:observation_time,:notes,:created_utc)'''),
                    dict(sample_id=sample_id,case_id=case_id,original_name=name,stored_name=stored_name,
                         sha256=digest,byte_size=len(raw),width=width,height=height,format=fmt,
                         exif_json=json.dumps(metadata),observation_time=observation,notes=notes,
                         created_utc=datetime.now(timezone.utc).isoformat()))
                session.commit()
            except Exception:
                path.unlink(missing_ok=True)
                raise
    except OSError:
        current_app.logger.exception('Image sample storage failed')
        return jsonify(error='Sample image storage is unavailable'), 503
    return jsonify(sample_id=sample_id, sha256=digest, classification='EXTERNAL SAMPLE'), 201


@image_samples_api.get('/cases/<int:case_id>/image-samples/<uuid:sample_id>/file')
@login_required
def sample_file(case_id, sample_id):
    with SessionLocal() as session:
        _create_table(session)
        row = _get_row(session, case_id, str(sample_id))
        if row is None:
            return jsonify(error='Sample not found'), 404
        path = _storage_root() / row['stored_name']
        try:
            raw = path.read_bytes()
        except OSError:
            return jsonify(error='Sample file unavailable'), 404
        if hashlib.sha256(raw).hexdigest() != row['sha256']:
            return jsonify(error='SHA-256 mismatch: image withheld'), 409
        return send_file(io.BytesIO(raw), mimetype='image/jpeg' if row['format'] == 'JPEG' else 'image/png',
                         download_name=row['original_name'], as_attachment=False, max_age=0)
