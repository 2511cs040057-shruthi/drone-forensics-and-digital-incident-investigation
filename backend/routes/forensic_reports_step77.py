"""Step 77A: source-attributed PDF/DOCX case reports. No evidence is modified."""
from datetime import datetime, timezone
from io import BytesIO
from hashlib import sha256
import re

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import inspect, text
from backend.auth import login_required
from backend.models.case import Case
from backend.services.database import SessionLocal

reports_api = Blueprint('reports_api', __name__)


def _records(session, table, case_id, limit=2000):
    inspector = inspect(session.get_bind())
    if table not in inspector.get_table_names():
        return []
    columns = {c['name'] for c in inspector.get_columns(table)}
    if 'case_id' not in columns:
        return []
    quoted = session.get_bind().dialect.identifier_preparer.quote(table)
    result = session.execute(text(f'SELECT * FROM {quoted} WHERE case_id=:cid LIMIT {int(limit)}'), {'cid': case_id})
    return [{k: str(v) if v is not None else '' for k, v in row.items()} for row in result.mappings()]


def _evidence(session, case_id):
    inspector = inspect(session.get_bind())
    candidates = []
    for table in inspector.get_table_names():
        if table.startswith(('custody_events_step76', 'investigator_findings_step75', 'image_samples_step72')):
            continue
        cols = {c['name'] for c in inspector.get_columns(table)}
        if {'case_id', 'evidence_id'}.issubset(cols):
            candidates.append(table)
    # Refuse to silently select the wrong evidence register.
    if len(candidates) != 1:
        return [], f'Evidence register schema unresolved (candidate tables: {", ".join(candidates) or "none"}); inventory omitted.'
    return _records(session, candidates[0], case_id), f'Evidence register: {candidates[0]}'


def _snapshot(case_id):
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        if case is None:
            return None
        evidence, evidence_note = _evidence(session, case_id)
        findings = _records(session, 'investigator_findings_step75', case_id)
        custody = _records(session, 'custody_events_step76', case_id)
        images = _records(session, 'image_samples_step72', case_id)
        return {'case_id': case_id,
                'case_title': str(getattr(case, 'title', '') or getattr(case, 'name', '') or f'Case {case_id}'),
                'case_reference': str(getattr(case, 'case_number', '') or getattr(case, 'case_reference', '') or f'Case {case_id}'),
                'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'evidence': evidence, 'evidence_note': evidence_note,
                'findings': findings, 'custody': custody, 'images': images}


def _sections(snapshot, investigator, summary):
    parts = [
        ('Case information', [f"Reference: {snapshot['case_reference']}", f"Title: {snapshot['case_title']}",
                              f"Case ID: {snapshot['case_id']}", f"Investigator (declared): {investigator}",
                              f"Report generated (UTC): {snapshot['generated_utc']}"]),
        ('Executive summary (investigator-provided)', [summary or 'No investigator summary provided. No automated incident conclusion is asserted.']),
        ('Evidence inventory', [snapshot['evidence_note'], f"Records returned: {len(snapshot['evidence'])}"] +
         [f"Evidence {r.get('evidence_id','?')}: {r.get('filename') or r.get('name') or r.get('original_filename') or '[filename unavailable]'}; "
          f"registered SHA-256: {r.get('sha256') or r.get('sha256_hash') or r.get('file_hash') or 'not exposed'}"
          for r in snapshot['evidence']]),
        ('Acquisition and integrity', [
            'Registered hashes are reported as stored metadata, not as newly verified file hashes.',
            'This report-generation operation does not rehash original evidence. Review the integrity verification module for live results.'
        ]),
        ('Flight log, GPS and sensor analysis', [
            'Flight-log event times are ArduPilot boot-relative TimeUS values, not UTC.',
            'Prior investigation observation: GPS.csv has no valid position fix; NO VALID GPS ROUTE can be reconstructed from that source.',
            'No independent telemetry re-analysis was performed during report generation. Consult the Flight Log, GPS and Sensor pages for primary observations.'
        ]),
        ('Image and EXIF analysis', [
            'External sample images are not established as drone-camera captures.',
            f"Image sample records available: {len(snapshot['images'])}. EXIF capture timestamps must be assessed independently."
        ] + [f"Sample: {r.get('filename') or r.get('original_filename') or r.get('sample_id') or r.get('id') or 'unnamed'}; investigator-provided metadata: {str(r)[:500]}" for r in snapshot['images']]),
        ('Incident timeline', [
            'Boot-relative flight events and calendar timestamps are separate time bases. This report does not infer an offset between them.',
            'Evidence import timestamps reflect system activity, not necessarily evidence creation or incident time.'
        ]),
        ('Bookmarks and findings (investigator assertions)', [f"Saved entries: {len(snapshot['findings'])}"] + [
            f"Finding #{r.get('finding_id','?')} [{r.get('category','')}]: {r.get('title','')}; "
            f"source={r.get('source_type','')}:{r.get('source_reference','')}; "
            f"time={r.get('time_basis','')} {r.get('time_value','')}; "
            f"description={r.get('description','')}" for r in snapshot['findings']]),
        ('Chain of custody (investigator-declared)', [f"Custody entries: {len(snapshot['custody'])}"] + [
            f"Event #{r.get('event_id','?')} evidence={r.get('evidence_id','?')}; action={r.get('action','')}; "
            f"actor={r.get('actor','')}; declared event time={r.get('event_time','')}; "
            f"server recorded UTC={r.get('recorded_utc','')}; purpose={r.get('purpose','')}" for r in snapshot['custody']]),
        ('Limitations and conclusions', [
            'This is a generated investigative compilation, not a certification of source authenticity.',
            'Manually entered findings, image observations and custody histories are declarations and require independent corroboration.',
            'Absence of valid GPS fixes prevents defensible geographic route reconstruction.',
            'No collision, takeoff time, camera capture time or absolute flight time is inferred without source support.',
            'Conclusions beyond the documented source observations require investigator review and sign-off.'
        ]),
    ]
    return parts


def _pdf(snapshot, investigator, summary):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    from reportlab.lib.utils import simpleSplit
    from xml.sax.saxutils import escape
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(595, 842), leftMargin=48, rightMargin=48,
                            topMargin=54, bottomMargin=52, title='MD-DRONE Forensic Report')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle77', parent=styles['Title'], textColor=colors.HexColor('#0C555A'), fontSize=19, leading=23, spaceAfter=16))
    styles.add(ParagraphStyle(name='ReportBody77', parent=styles['BodyText'], fontSize=9, leading=13, spaceAfter=7, wordWrap='CJK'))
    styles.add(ParagraphStyle(name='ReportHead77', parent=styles['Heading2'], textColor=colors.HexColor('#0C555A'), spaceBefore=15, spaceAfter=9))
    story = [Paragraph('MD-DRONE | FORENSIC INVESTIGATION REPORT', styles['ReportTitle77']),
             Paragraph(escape(snapshot['case_reference']), styles['Heading2']), Spacer(1, 16)]
    for heading, lines in _sections(snapshot, investigator, summary):
        story.append(Paragraph(escape(heading), styles['ReportHead77']))
        for line in lines:
            # Preserve full records, while making untrusted user text safe for PDF XML.
            story.append(Paragraph(escape(str(line)).replace('\n', '<br/>'), styles['ReportBody77']))
    def footer(canvas, document):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(48, 28, 'MD-DRONE | Investigator review required')
        canvas.drawRightString(547, 28, f'Page {document.page}')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer


def _docx(snapshot, investigator, summary):
    from docx import Document
    from docx.shared import Inches, Pt
    document = Document()
    document.add_heading('MD-DRONE | Forensic Investigation Report', 0)
    document.add_paragraph(snapshot['case_reference'], style='Subtitle')
    for heading, lines in _sections(snapshot, investigator, summary):
        document.add_heading(heading, level=1)
        for line in lines:
            document.add_paragraph(str(line))
    document.add_paragraph('Generated compilation — investigator review and sign-off required.')
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer



# Step 78: focused, five-item evidence report with evidence diagram and image exhibits.
import os
from pathlib import Path

KEY_FILES = ('00000146.BIN', 'GPS.csv', 'ATT.csv', 'IMU.csv', 'BARO.csv')
KEY_PURPOSE = {
    '00000146.BIN': 'Primary ArduPilot DataFlash flight log; source for telemetry extraction.',
    'GPS.csv': 'GPS receiver status, satellite observations and coordinate fields.',
    'ATT.csv': 'Attitude measurements: roll, pitch and yaw.',
    'IMU.csv': 'Inertial sensor acceleration and angular-rate measurements.',
    'BARO.csv': 'Barometric pressure, temperature and altitude observations.',
}


def _five(snapshot):
    rows = snapshot['evidence']
    chosen = []
    for name in KEY_FILES:
        matching = next((r for r in rows if str(r.get('filename') or r.get('original_filename') or r.get('name') or '').lower() == name.lower()), None)
        chosen.append((name, matching))
    return chosen


def _image_exhibits(snapshot):
    # Read only registered sample images, with strict basename and SHA-256 checks.
    root = Path(os.environ.get('MD_DRONE_SAMPLE_IMAGE_DIR') or (Path.cwd() / 'sample_image_gallery')).expanduser().resolve()
    exhibits = []
    for row in snapshot['images'][:5]:
        stored = row.get('stored_name', '')
        path = root / stored
        data = None
        if re.fullmatch(r'[0-9a-fA-F-]{36}\.(jpg|png)', stored) and path.is_file() and path.resolve().parent == root:
            candidate = path.read_bytes()
            if len(candidate) <= 20 * 1024 * 1024 and sha256(candidate).hexdigest().lower() == row.get('sha256', '').lower():
                data = candidate
        exhibits.append((row, data))
    return exhibits


def _diagram_png():
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (1100, 480), '#ffffff')
    d = ImageDraw.Draw(im)
    colors = ['#0d6267', '#2d7098', '#4d658d', '#647e77', '#9a713e']
    for i, name in enumerate(KEY_FILES):
        x = 24 + i * 218
        d.rounded_rectangle((x, 95, x + 204, 282), radius=14, fill='#f3f7f8', outline=colors[i], width=4)
        d.text((x + 14, 119), f'0{i+1}', fill=colors[i], stroke_width=0)
        d.text((x + 14, 168), name, fill='#182c37')
        d.line((x + 102, 282, x + 102, 335), fill=colors[i], width=4)
    d.rounded_rectangle((295, 335, 805, 427), radius=16, fill='#e7f2f1', outline='#0d6267', width=3)
    d.text((380, 365), 'CASE EVIDENCE ANALYSIS', fill='#0d5054')
    b = BytesIO(); im.save(b, format='PNG'); b.seek(0); return b


def _gps_png():
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (1100, 360), '#ffffff'); d = ImageDraw.Draw(im)
    d.rounded_rectangle((30, 35, 1070, 325), radius=16, fill='#f4f7fa', outline='#bdcbd2', width=3)
    d.text((65, 70), 'GPS PATH / FIX STATUS', fill='#173d51')
    d.line((100, 245, 1000, 245), fill='#9aaeb7', width=3)
    d.rectangle((110, 168, 990, 210), fill='#b7c6ce')
    d.text((270, 178), 'NO VERIFIED GEOGRAPHIC PATH', fill='#1d3541')
    d.text((110, 268), 'GPS.csv: reported Status=1, NSats=0, HDop=99.99, Lat=0, Lng=0', fill='#4a5c65')
    d.text((110, 293), 'No position fix. Diagram is a status visualization, NOT a flight route.', fill='#8c3f37')
    b = BytesIO(); im.save(b, format='PNG'); b.seek(0); return b


def _sections(snapshot, investigator, summary):
    parts = [
        ('Case overview', [f"Reference: {snapshot['case_reference']}", f"Title: {snapshot['case_title']}",
                           f"Investigator (declared): {investigator}", f"Generated UTC: {snapshot['generated_utc']}"]),
        ('Investigator executive summary', [summary or 'No investigator summary provided.']),
        ('Five key evidence items — detailed specifications', [snapshot['evidence_note']]),
    ]
    for i, (name, row) in enumerate(_five(snapshot), 1):
        if row is None:
            parts[-1][1].append(f'{i}. {name} — NOT FOUND in resolved evidence register; details cannot be asserted. Purpose: {KEY_PURPOSE[name]}')
        else:
            parts[-1][1].append(f'{i}. {name} | Investigative role: {KEY_PURPOSE[name]}')
            for key in ('evidence_id', 'filename', 'original_filename', 'file_type', 'mime_type', 'file_size', 'size', 'sha256', 'sha256_hash', 'file_hash', 'source_path', 'imported_at', 'created_at'):
                if row.get(key): parts[-1][1].append(f'    {key}: {row[key]}')
            parts[-1][1].append('    Hash values are registered metadata, not reverified during report generation.')
    parts.extend([
        ('Evidence relationship diagram', ['Five selected artifacts are depicted as independent inputs to the case analysis.']),
        ('GPS path / fix-status graph', ['Previous case observation: GPS.csv contained 665 records without a valid GPS fix.',
            'No latitude/longitude route can be reconstructed. The graph explicitly represents missing valid positions, not a fabricated trajectory.',
            'TimeUS is boot-relative and is not UTC. GPS observations were not reprocessed for this report.']),
        ('Image evidence exhibits', [f"Registered external image samples: {len(snapshot['images'])}. Up to five images are presented below.",
            'These are investigator-supplied external samples; they are NOT established as drone-camera captures.']),
        ('Findings and provenance', [f"Investigator findings: {len(snapshot['findings'])}; custody declarations: {len(snapshot['custody'])}.",
            'Original evidence is not altered by report generation; image bytes are embedded only if their stored SHA-256 matches the register.']),
        ('Limitations and review', ['Evidence hash values shown in inventory are stored metadata, not newly verified original-file hashes.',
            'No absolute flight time, camera capture time, collision event or geographic route is inferred.',
            'Investigator review and sign-off are required before formal use.'])
    ])
    return parts


def _pdf(snapshot, investigator, summary):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from xml.sax.saxutils import escape
    b = BytesIO(); doc = SimpleDocTemplate(b, pagesize=(595,842), leftMargin=46, rightMargin=46, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Step78Title', parent=styles['Title'], fontSize=18, leading=23, textColor=colors.HexColor('#0c555a')))
    styles.add(ParagraphStyle(name='Step78Head', parent=styles['Heading2'], spaceBefore=14, spaceAfter=7, textColor=colors.HexColor('#0c555a')))
    styles.add(ParagraphStyle(name='Step78Body', parent=styles['BodyText'], fontSize=8.5, leading=12, spaceAfter=5, wordWrap='CJK'))
    story=[Paragraph('MD-DRONE | FORENSIC INVESTIGATION REPORT', styles['Step78Title']), Spacer(1,12)]
    for heading, lines in _sections(snapshot, investigator, summary):
        story.append(Paragraph(escape(heading),styles['Step78Head']))
        for line in lines: story.append(Paragraph(escape(str(line)),styles['Step78Body']))
        if heading == 'Evidence relationship diagram': story.append(RLImage(_diagram_png(),width=500,height=218))
        if heading == 'GPS path / fix-status graph': story.append(RLImage(_gps_png(),width=500,height=164))
        if heading == 'Image evidence exhibits':
            for row, raw in _image_exhibits(snapshot):
                story.append(Paragraph(escape('Sample: '+str(row.get('original_name','unnamed'))),styles['Step78Body']))
                story.append(Paragraph(escape('SHA-256: '+str(row.get('sha256','unknown'))),styles['Step78Body']))
                story.append(Paragraph(escape('Dimensions: '+str(row.get('width','?'))+' x '+str(row.get('height','?'))+' | EXIF: '+str(row.get('exif_json','{}'))[:350]),styles['Step78Body']))
                if raw:
                    from PIL import Image as PILImage
                    with PILImage.open(BytesIO(raw)) as pic:
                        w,h=pic.size
                    scale=min(450/w,240/h)
                    story.append(RLImage(BytesIO(raw),width=w*scale,height=h*scale))
                else: story.append(Paragraph('Image not embedded: file missing or SHA-256 mismatch.',styles['Step78Body']))
    def footer(canvas, document):
        canvas.setFont('Helvetica',8); canvas.drawString(46,25,'MD-DRONE | Investigator review required'); canvas.drawRightString(548,25,f'Page {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer); b.seek(0); return b


def _docx(snapshot, investigator, summary):
    from docx import Document
    from docx.shared import Inches
    doc=Document(); doc.add_heading('MD-DRONE | Forensic Investigation Report',0)
    for heading, lines in _sections(snapshot, investigator, summary):
        doc.add_heading(heading,level=1)
        for line in lines: doc.add_paragraph(str(line))
        if heading == 'Evidence relationship diagram': doc.add_picture(_diagram_png(),width=Inches(6.3))
        if heading == 'GPS path / fix-status graph': doc.add_picture(_gps_png(),width=Inches(6.3))
        if heading == 'Image evidence exhibits':
            for row, raw in _image_exhibits(snapshot):
                doc.add_paragraph('External sample: '+str(row.get('original_name','unnamed')))
                doc.add_paragraph('SHA-256: '+str(row.get('sha256','unknown')))
                doc.add_paragraph('Dimensions: '+str(row.get('width','?'))+' x '+str(row.get('height','?')))
                doc.add_paragraph('EXIF: '+str(row.get('exif_json','{}'))[:1000])
                if raw:
                    try: doc.add_picture(BytesIO(raw),width=Inches(4.8))
                    except Exception: doc.add_paragraph('Image preview could not be rendered.')
                else: doc.add_paragraph('Image missing or hash mismatch; not embedded.')
    b=BytesIO(); doc.save(b); b.seek(0); return b


@reports_api.get('/cases/<int:case_id>/reports/preview')
@login_required
def preview_report(case_id):
    snapshot = _snapshot(case_id)
    if snapshot is None:
        return jsonify(error='Case not found'), 404
    return jsonify(case_id=case_id, case_reference=snapshot['case_reference'],
                   case_title=snapshot['case_title'], evidence_count=len(snapshot['evidence']), selected_evidence_count=sum(r is not None for _,r in _five(snapshot)), selected_evidence_names=[n for n,_ in _five(snapshot)],
                   findings_count=len(snapshot['findings']), custody_count=len(snapshot['custody']),
                   image_sample_count=len(snapshot['images']), evidence_note=snapshot['evidence_note'],
                   limitations='Not a live SHA-256 verification; no absolute flight time inferred.'), 200


@reports_api.post('/cases/<int:case_id>/reports/generate')
@login_required
def generate_report(case_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error='JSON request body required'), 400
    fmt = payload.get('format')
    if fmt not in {'pdf', 'docx'}:
        return jsonify(error='format must be pdf or docx'), 400
    investigator = str(payload.get('investigator') or '').strip()
    summary = str(payload.get('summary') or '').strip()
    if not investigator or len(investigator) > 200 or len(summary) > 5000:
        return jsonify(error='Investigator required (max 200 chars); summary max 5000 chars'), 400
    snapshot = _snapshot(case_id)
    if snapshot is None:
        return jsonify(error='Case not found'), 404
    result = _pdf(snapshot, investigator, summary) if fmt == 'pdf' else _docx(snapshot, investigator, summary)
    return send_file(result,
                     mimetype='application/pdf' if fmt == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     as_attachment=True, download_name=f'MD-DRONE_case_{case_id}_report.{fmt}')
