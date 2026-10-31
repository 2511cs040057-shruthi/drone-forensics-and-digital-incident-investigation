import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


def generate_forensic_report(report_data, output_path):
    """
    Generate a PDF forensic report from supplied investigation data.

    Expected report_data keys:
        case
        evidence
        flight_records
        timeline
        chain_of_custody
        accident_analysis
        integrity
    """

    output_directory = os.path.dirname(output_path)

    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    document = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="MD-DRONE Digital Forensic Report",
        author="MD-DRONE Forensic Investigation System",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=20,
            leading=25,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#163A5F"),
            spaceBefore=12,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            wordWrap="CJK",
        )
    )

    story = []

    # -----------------------------------------------------
    # HELPER FUNCTIONS
    # -----------------------------------------------------

    def safe(value):
        """Escape text before adding it to a ReportLab paragraph."""

        if value is None:
            return "N/A"

        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def add_section(title):
        heading = Paragraph(
            safe(title),
            styles["SectionHeading"],
        )

        story.append(KeepTogether([heading, Spacer(1, 2)]))

    def add_table(rows, widths=None):
        """Add a consistently formatted table to the report."""

        table = Table(
            rows,
            colWidths=widths,
            repeatRows=1 if len(rows) > 1 else 0,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#163A5F"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, -1),
                        "Helvetica",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "LEADING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.grey,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------
    # REPORT HEADER
    # -----------------------------------------------------

    story.append(
        Paragraph(
            "MD-DRONE",
            styles["ReportTitle"],
        )
    )

    story.append(
        Paragraph(
            "Drone Forensics and Digital Incident Investigation",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            "Report generated: "
            + safe(
                datetime.now().astimezone().isoformat(
                    timespec="seconds"
                )
            ),
            styles["BodyText"],
        )
    )

    story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------
    # LOAD REPORT DATA
    # -----------------------------------------------------

    case = report_data.get("case") or {}
    evidence = report_data.get("evidence") or {}
    flight = report_data.get("flight") or {}
    integrity = report_data.get("integrity") or {}
    analysis = report_data.get("accident_analysis") or {}

    flight_records = report_data.get("flight_records") or []
    timeline = report_data.get("timeline") or []
    custody_records = report_data.get("chain_of_custody") or []

    # -----------------------------------------------------
    # 1. CASE INFORMATION
    # -----------------------------------------------------

    add_section("1. Case Information")

    add_table(
        [
            ["Field", "Value"],
            ["Case ID", safe(case.get("case_id"))],
            ["Case Number", safe(case.get("case_number"))],
            ["Case Title", safe(case.get("case_title"))],
            ["Case Status", safe(case.get("status"))],
        ],
        [45 * mm, 120 * mm],
    )

    # -----------------------------------------------------
    # 2. EVIDENCE INFORMATION
    # -----------------------------------------------------

    add_section("2. Evidence Information")

    add_table(
        [
            ["Field", "Value"],
            ["Evidence ID", safe(evidence.get("evidence_id"))],
            ["Evidence Code", safe(evidence.get("evidence_code"))],
            ["File Name", safe(evidence.get("file_name"))],
            ["File Type", safe(evidence.get("file_type"))],
            ["File Size (bytes)", safe(evidence.get("file_size"))],
            ["Uploaded At", safe(evidence.get("uploaded_at"))],
            ["Stored SHA-256", safe(evidence.get("sha256_hash"))],
        ],
        [45 * mm, 120 * mm],
    )

    # -----------------------------------------------------
    # 3. FLIGHT INFORMATION
    # -----------------------------------------------------

    add_section("3. Flight Information")

    if flight:
        add_table(
            [
                ["Field", "Value"],
                ["Flight ID", safe(flight.get("flight_id"))],
                ["Flight Number", safe(flight.get("flight_number"))],
                ["Drone ID", safe(flight.get("drone_id"))],
                ["Flight Status", safe(flight.get("flight_status"))],
                ["Start Time", safe(flight.get("start_time"))],
                ["End Time", safe(flight.get("end_time"))],
                [
                    "Duration (seconds)",
                    safe(flight.get("flight_duration_seconds")),
                ],
            ],
            [45 * mm, 120 * mm],
        )
    else:
        story.append(
            Paragraph(
                "No flight information is associated with this evidence.",
                styles["BodyText"],
            )
        )
        story.append(Spacer(1, 3 * mm))

    # -----------------------------------------------------
    # 4. EVIDENCE INTEGRITY VERIFICATION
    # -----------------------------------------------------

    add_section("4. Evidence Integrity Verification")

    integrity_status = integrity.get(
        "status",
        "UNVERIFIABLE",
    )

    reference_hash = integrity.get("reference_hash")
    current_hash = integrity.get("current_hash")

    if (
        integrity_status == "MATCH"
        and reference_hash
        and current_hash
        and str(reference_hash).lower()
        == str(current_hash).lower()
    ):
        integrity_verified = True
    else:
        integrity_verified = False

    add_table(
        [
            ["Field", "Result"],
            ["Integrity Status", safe(integrity_status)],
            ["Integrity Verified", safe(integrity_verified)],
            ["Reference SHA-256", safe(reference_hash)],
            ["Calculated SHA-256", safe(current_hash)],
        ],
        [45 * mm, 120 * mm],
    )

    # -----------------------------------------------------
    # 4. FLIGHT RECORDS
    # -----------------------------------------------------

    add_section("5. Flight Records")

    flight_rows = [
        [
            "Record ID",
            "Timestamp",
            "Latitude",
            "Longitude",
            "Altitude",
            "Speed",
        ]
    ]

    for record in flight_records:
        flight_rows.append(
            [
                safe(record.get("flight_record_id")),
                safe(record.get("timestamp")),
                safe(record.get("latitude")),
                safe(record.get("longitude")),
                safe(record.get("altitude")),
                safe(record.get("speed")),
            ]
        )

    if len(flight_rows) == 1:
        flight_rows.append(
            [
                "No flight records available",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    add_table(
        flight_rows,
        [
            18 * mm,
            36 * mm,
            27 * mm,
            27 * mm,
            25 * mm,
            20 * mm,
        ],
    )

    # -----------------------------------------------------
    # 5. GPS ROUTE SUMMARY
    # -----------------------------------------------------

    add_section("6. GPS Route Summary")

    if flight_records:
        gps_rows = [
            [
                "Point",
                "Latitude",
                "Longitude",
                "Altitude",
            ]
        ]

        for index, record in enumerate(
            flight_records,
            start=1,
        ):
            gps_rows.append(
                [
                    str(index),
                    safe(record.get("latitude")),
                    safe(record.get("longitude")),
                    safe(record.get("altitude")),
                ]
            )

        add_table(
            gps_rows,
            [
                20 * mm,
                45 * mm,
                45 * mm,
                35 * mm,
            ],
        )

    else:
        story.append(
            Paragraph(
                "No GPS route data is available.",
                styles["BodyText"],
            )
        )

        story.append(Spacer(1, 3 * mm))

    # -----------------------------------------------------
    # 6. TIMELINE RECONSTRUCTION
    # -----------------------------------------------------

    add_section("7. Timeline Reconstruction")

    timeline_rows = [
        [
            "Timeline ID",
            "Sequence No",
            "Timestamp",
            "Latitude",
            "Longitude",
        ]
    ]

    for event in timeline:
        timeline_id = event.get("timeline_id")

        sequence_no = event.get("sequence_no")

        timestamp = event.get(
            "event_time",
            event.get(
                "timestamp",
                event.get("recorded_at"),
            ),
        )

        timeline_rows.append(
            [
                safe(timeline_id),
                safe(sequence_no),
                safe(timestamp),
                safe(event.get("latitude")),
                safe(event.get("longitude")),
            ]
        )

    if len(timeline_rows) == 1:
        timeline_rows.append(
            [
                "No timeline events available",
                "",
                "",
                "",
                "",
            ]
        )

    add_table(
        timeline_rows,
        [
            22 * mm,
            23 * mm,
            45 * mm,
            38 * mm,
            38 * mm,
        ],
    )

    # -----------------------------------------------------
    # 7. FLIGHT ANOMALY ANALYSIS
    # -----------------------------------------------------

    add_section("8. Flight Anomaly Analysis")

    records_analyzed = analysis.get(
        "records_analyzed",
        analysis.get(
            "total_records",
            len(flight_records),
        ),
    )

    anomalies = analysis.get("anomalies") or []

    anomaly_count = analysis.get(
        "anomaly_count",
        analysis.get(
            "anomalies_found",
            len(anomalies),
        ),
    )

    story.append(
        Paragraph(
            f"Records analysed: {safe(records_analyzed)}",
            styles["BodyText"],
        )
    )

    story.append(
        Paragraph(
            f"Potential anomalies detected: {safe(anomaly_count)}",
            styles["BodyText"],
        )
    )

    story.append(Spacer(1, 3 * mm))

    if anomalies:
        anomaly_rows = [
            [
                "Timestamp",
                "Type",
                "Severity",
                "Details",
            ]
        ]

        for anomaly in anomalies:
            details = anomaly.get(
                "description",
                anomaly.get("details"),
            )

            anomaly_rows.append(
                [
                    Paragraph(
                        safe(anomaly.get("timestamp")),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(anomaly.get("type")),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(anomaly.get("severity")),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(details),
                        styles["SmallText"],
                    ),
                ]
            )

        add_table(
            anomaly_rows,
            [
                32 * mm,
                30 * mm,
                25 * mm,
                73 * mm,
            ],
        )

    else:
        story.append(
            Paragraph(
                "No anomalies were flagged by the configured checks. "
                "This does not prove that no incident occurred.",
                styles["BodyText"],
            )
        )

        story.append(Spacer(1, 3 * mm))

    # -----------------------------------------------------
    # 8. CHAIN OF CUSTODY
    # -----------------------------------------------------

    add_section("9. Chain of Custody")

    if custody_records:
        custody_rows = [
            [
                "Transfer Time",
                "Action",
                "Released By / Received By",
                "Location",
                "Remarks",
            ]
        ]

        for entry in custody_records:
            transfer_time = entry.get(
                "transferred_at",
                entry.get("created_at"),
            )

            released_by = entry.get("released_by")
            received_by = entry.get("received_by")

            transfer_details = (
                f"Released by: {safe(released_by)}<br/>"
                f"Received by: {safe(received_by)}"
            )

            custody_rows.append(
                [
                    Paragraph(
                        safe(transfer_time),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(entry.get("action")),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        transfer_details,
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(entry.get("location")),
                        styles["SmallText"],
                    ),
                    Paragraph(
                        safe(entry.get("remarks")),
                        styles["SmallText"],
                    ),
                ]
            )

        add_table(
            custody_rows,
            [
                30 * mm,
                25 * mm,
                48 * mm,
                25 * mm,
                46 * mm,
            ],
        )

        story.append(
            Paragraph(
                "The entries above represent chain-of-custody information "
                "recorded in the MD-DRONE database. The accuracy of "
                "identities, times, locations, and transfer details must "
                "be validated against the original custody documentation.",
                styles["BodyText"],
            )
        )

    else:
        story.append(
            Paragraph(
                "No chain-of-custody records were found for this evidence "
                "in the MD-DRONE database at the time of report generation.",
                styles["BodyText"],
            )
        )

    story.append(Spacer(1, 3 * mm))

    # -----------------------------------------------------
    # 9. INVESTIGATOR NOTES AND LIMITATIONS
    # -----------------------------------------------------

    add_section("10. Investigator Notes and Limitations")

    story.append(
        Paragraph(
            "This report presents information extracted from the supplied "
            "flight log and stored investigation records. Automated anomaly "
            "warnings are indicators for further examination; they do not "
            "independently establish that a drone accident occurred. "
            "Investigators should validate the findings against the original "
            "evidence and other available information. A hash match indicates "
            "that the current file matches the stored reference hash; it does "
            "not independently prove the authenticity of the original evidence.",
            styles["BodyText"],
        )
    )

    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            "End of Report",
            ParagraphStyle(
                name="ReportEnd",
                parent=styles["BodyText"],
                alignment=TA_CENTER,
                textColor=colors.grey,
            ),
        )
    )

    # -----------------------------------------------------
    # PAGE NUMBERS
    # -----------------------------------------------------

    def add_page_number(canvas, doc):
        canvas.saveState()

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)

        canvas.drawString(
            18 * mm,
            10 * mm,
            "MD-DRONE | Forensic Report",
        )

        canvas.drawRightString(
            A4[0] - 18 * mm,
            10 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    # -----------------------------------------------------
    # BUILD AND SAVE THE PDF
    # -----------------------------------------------------

    document.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return output_path
