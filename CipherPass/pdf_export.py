"""
CipherPass — PDF Report Generator
Generates professional compliance reports using ReportLab.
"""

import os
from datetime import datetime
from pathlib import Path


def generate_pdf_report(manual: dict, results: dict, compliance_decision: dict = None) -> str:
    """
    Generate a PDF compliance report and save it to disk.
    Returns the path of the saved PDF.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        return None

    # ── Output path ──
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    ts_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    cnic_clean = manual.get("cnic", "unknown").replace("-", "")
    pdf_path = out_dir / f"CipherPass_Report_{cnic_clean}_{ts_file}.pdf"

    # ── Colours ──
    TEAL       = colors.HexColor("#38b2ac")
    NAVY       = colors.HexColor("#0d2137")
    DARK_BG    = colors.HexColor("#111827")
    LIGHT_TEXT = colors.HexColor("#e2e8f0")
    MUTED      = colors.HexColor("#718096")
    GREEN      = colors.HexColor("#48bb78")
    RED        = colors.HexColor("#fc8181")
    AMBER      = colors.HexColor("#f6ad55")
    WHITE      = colors.white
    LIGHT_GREY = colors.HexColor("#f7fafc")
    ROW_ALT    = colors.HexColor("#edf2f7")

    trust = results.get("trust_score", 0)
    risk_level = results.get("risk_level", "unknown").upper()
    trust_color = GREEN if trust >= 70 else (AMBER if trust >= 40 else RED)
    cr = results.get("criminal_record", {})
    has_criminal = cr.get("has_criminal_record", False)
    now_str = datetime.now().strftime("%d %B %Y  at  %H:%M:%S")
    report_id = f"CP-{datetime.now().strftime('%Y%m%d')}-{cnic_clean[-4:]}"

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        topMargin=1.5*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )
    story = []

    styles = getSampleStyleSheet()

    def style(name, **kw):
        s = ParagraphStyle(name, parent=styles["Normal"], **kw)
        return s

    H1   = style("H1",  fontSize=22, textColor=TEAL,  fontName="Helvetica-Bold",  spaceAfter=2)
    H2   = style("H2",  fontSize=13, textColor=NAVY,  fontName="Helvetica-Bold",  spaceBefore=10, spaceAfter=4)
    BODY = style("BODY",fontSize=10, textColor=colors.HexColor("#2d3748"), leading=15)
    SMALL= style("SM",  fontSize=8,  textColor=MUTED,  leading=12)
    CTR  = style("CTR", fontSize=10, textColor=colors.HexColor("#2d3748"), alignment=TA_CENTER)

    # ── HEADER BANNER ──
    header_data = [[
        Paragraph("<b>🔐  Cipher<font color='#805ad5'>Pass</font></b>", style("LOGO", fontSize=24, textColor=NAVY, fontName="Helvetica-Bold")),
        Paragraph(
            f"<font color='#718096'>VERIFICATION &amp; COMPLIANCE REPORT</font><br/>"
            f"<font size='8' color='#718096'>Report ID: {report_id}</font>",
            style("RHDR", fontSize=11, textColor=NAVY, alignment=TA_RIGHT)
        )
    ]]
    header_tbl = Table(header_data, colWidths=["55%", "45%"])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [6, 6, 6, 6]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6))

    # ── Meta row ──
    meta_data = [[
        Paragraph(f"<font color='#718096'>Generated:</font>  {now_str}", SMALL),
        Paragraph(f"<font color='#718096'>Status:</font>  <b>{'⚠  FLAGGED' if has_criminal else '✔  CLEAR'}</b>", style("META_R", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
    ]]
    meta_tbl = Table(meta_data, colWidths=["60%", "40%"])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 12))

    # ── TRUST SCORE BANNER ──
    verdict_text = "APPROVED — Low Risk Customer" if trust >= 70 else (
        "MANUAL REVIEW REQUIRED" if trust >= 40 else "REJECTED — High Risk Customer"
    )
    score_banner = [[
        Paragraph(f"<b>Trust Score</b>", style("SB1", fontSize=10, textColor=WHITE)),
        Paragraph(f"<b>{trust}/100</b>", style("SB2", fontSize=22, textColor=WHITE, alignment=TA_CENTER)),
        Paragraph(f"<b>{risk_level} RISK</b><br/><font size='9'>{verdict_text}</font>",
                  style("SB3", fontSize=11, textColor=WHITE, alignment=TA_RIGHT)),
    ]]
    banner_bg = colors.HexColor("#276749") if trust >= 70 else (colors.HexColor("#7b341e") if trust < 40 else colors.HexColor("#744210"))
    score_tbl = Table(score_banner, colWidths=["25%", "25%", "50%"])
    score_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), banner_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 14))

    # ── CUSTOMER INFORMATION ──
    story.append(Paragraph("CUSTOMER INFORMATION", H2))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=6))

    cust_data = [
        ["Full Name",     manual.get("name", "N/A"),       "CNIC Number",    manual.get("cnic", "N/A")],
        ["Father's Name", manual.get("father_name", "N/A"),"Date of Birth",  manual.get("date_of_birth", "N/A")],
        ["Address",       manual.get("address", "N/A"),    "Verification",   now_str[:10]],
    ]
    cust_tbl = Table(cust_data, colWidths=["20%", "30%", "20%", "30%"])
    cust_tbl.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR",     (2, 0), (2, -1), MUTED),
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREY),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT_GREY, ROW_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(cust_tbl)
    story.append(Spacer(1, 14))

    # ── VERIFICATION SCORES ──
    story.append(Paragraph("VERIFICATION SCORES", H2))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=6))

    face_score = results.get("face_score", 0)
    doc_score  = results.get("doc_score", 0)
    identity_ok = results.get("is_correct_person", False)

    scores_data = [
        ["Module", "Score", "Status"],
        ["Biometric Face Analysis", f"{face_score}%",
         "PASS" if face_score >= 60 else "FAIL"],
        ["Document Authenticity",  f"{doc_score}%",
         "PASS" if doc_score >= 60 else "FAIL"],
        ["Identity Name Match", "—",
         "VERIFIED" if identity_ok else "MISMATCH"],
        ["Criminal Background Check", "—",
         "CLEAR" if not has_criminal else "FLAGGED"],
        ["Overall Trust Score", f"{trust}/100", risk_level + " RISK"],
    ]
    scores_tbl = Table(scores_data, colWidths=["50%", "20%", "30%"])
    score_style = TableStyle([
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GREY, ROW_ALT]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ])
    for row_i, row in enumerate(scores_data[1:], 1):
        status = row[2]
        if status in ("PASS", "VERIFIED", "CLEAR"):
            score_style.add("TEXTCOLOR", (2, row_i), (2, row_i), GREEN)
        elif status in ("FAIL", "MISMATCH", "FLAGGED"):
            score_style.add("TEXTCOLOR", (2, row_i), (2, row_i), RED)
        else:
            score_style.add("TEXTCOLOR", (2, row_i), (2, row_i), AMBER)
        score_style.add("FONTNAME", (2, row_i), (2, row_i), "Helvetica-Bold")
    scores_tbl.setStyle(score_style)
    story.append(scores_tbl)
    story.append(Spacer(1, 14))

    # ── CRIMINAL RECORD ──
    story.append(Paragraph("CRIMINAL BACKGROUND CHECK", H2))
    story.append(HRFlowable(width="100%", thickness=1, color=RED if has_criminal else TEAL, spaceAfter=6))

    if has_criminal:
        cr_status_color = colors.HexColor("#fff5f5")
        story.append(Paragraph(
            f"<b><font color='#c53030'>⚠  CRIMINAL RECORD FOUND</font></b>  —  "
            f"Risk Level: <b>{cr.get('risk_level','').upper()}</b>  |  "
            f"Source: {cr.get('source','N/A')}",
            style("CR_HDR", fontSize=10, textColor=colors.HexColor("#c53030"),
                  backColor=colors.HexColor("#fff5f5"), borderPadding=8)
        ))
        story.append(Spacer(1, 6))

        for i, crime in enumerate(cr.get("crimes", []), 1):
            status = crime.get("status", "").lower()
            s_color = "#c53030" if status == "convicted" else "#c05621"
            crime_data = [
                [Paragraph(f"<b>#{i}  {crime.get('type','Unknown')}</b>",
                           style("CT", fontSize=10, textColor=colors.HexColor("#c53030"))),
                 Paragraph(crime.get("date", "N/A"),
                           style("CD", fontSize=9, textColor=MUTED, alignment=TA_RIGHT))],
                [Paragraph(crime.get("description", ""), BODY), ""],
                [Paragraph(f"<b>Status:</b> <font color='{s_color}'>{status.upper()}</font>  "
                           f"  |  <b>Penalty:</b> {crime.get('penalty','N/A')}",
                           style("CP", fontSize=9, textColor=colors.HexColor("#2d3748"))), ""],
            ]
            crime_tbl = Table(crime_data, colWidths=["70%", "30%"])
            crime_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#fff5f5")),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#feb2b2")),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("SPAN",          (0, 1), (1, 1)),
                ("SPAN",          (0, 2), (1, 2)),
            ]))
            story.append(crime_tbl)
            story.append(Spacer(1, 6))

        flags = cr.get("flags", [])
        if flags:
            flag_text = "  |  ".join(flags)
            story.append(Paragraph(
                f"<b>AML Flags:</b>  <font color='#c05621'>{flag_text}</font>",
                style("FLAGS", fontSize=9, textColor=colors.HexColor("#2d3748"))
            ))
    else:
        story.append(Paragraph(
            "✔  No criminal record found.  Customer is CLEAR on all watchlists.",
            style("CLEAR", fontSize=10, textColor=GREEN,
                  backColor=colors.HexColor("#f0fff4"), borderPadding=10)
        ))
    story.append(Spacer(1, 14))

    # ── COMPLIANCE DECISION (if provided) ──
    if compliance_decision:
        story.append(Paragraph("COMPLIANCE OFFICER DECISION", H2))
        story.append(HRFlowable(width="100%", thickness=1, color=AMBER, spaceAfter=6))
        action = compliance_decision.get("action_full", compliance_decision.get("action", "N/A"))
        officer = compliance_decision.get("officer_name", "N/A")
        notes   = compliance_decision.get("notes", "").strip() or "No notes provided."
        ts_cd   = compliance_decision.get("timestamp", "")[:19].replace("T", " ")

        comp_data = [
            ["Action Taken", action],
            ["Compliance Officer", officer],
            ["Decision Time", ts_cd],
            ["Review Notes", notes],
        ]
        comp_tbl = Table(comp_data, colWidths=["25%", "75%"])
        comp_tbl.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("TEXTCOLOR",     (0, 0), (0, -1), MUTED),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.HexColor("#fffaf0"), colors.HexColor("#fef3c7")]),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#fbd38d")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(comp_tbl)
        story.append(Spacer(1, 14))

    # ── FLAGS ──
    flags_list = results.get("flags", [])
    if flags_list:
        story.append(Paragraph("RISK FLAGS", H2))
        story.append(HRFlowable(width="100%", thickness=1, color=AMBER, spaceAfter=6))
        for flag in flags_list:
            story.append(Paragraph(f"▸  {flag}", style("FL", fontSize=9,
                textColor=colors.HexColor("#c05621"), leftIndent=10)))
        story.append(Spacer(1, 10))

    # ── FOOTER ──
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED, spaceBefore=10, spaceAfter=6))
    story.append(Paragraph(
        f"This report was generated by <b>GuardianKYC</b> on {now_str}.  "
        f"Report ID: <b>{report_id}</b>.  "
        f"For official use only — handle with confidentiality.",
        style("FOOTER", fontSize=7.5, textColor=MUTED, alignment=TA_CENTER)
    ))

    doc.build(story)
    return str(pdf_path)
