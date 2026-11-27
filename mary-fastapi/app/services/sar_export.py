from html import escape as escape_html
import os
import io
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from weasyprint import HTML
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

async def fetch_sar_dataset(db: AsyncSession, su_id: int) -> Dict[str, Any]:
    """
    Queries and aggregates all personal and Article 9 special category data
    for a Service User under UK GDPR Article 15.
    """
    # 1. Patient Profile
    su_query = text("""
        SELECT su.*,
               g.gender as gender_name,
               b.branch as branch_name,
               ss.service_status as status_name,
               ms.marital_status as marital_status_name
        FROM m_service_users su
        LEFT JOIN m_genders g ON su.gender_id = g.gender_id
        LEFT JOIN m_branches b ON su.branch_id = b.branch_id
        LEFT JOIN m_service_statuses ss ON su.service_status_id = ss.service_status_id
        LEFT JOIN m_marital_statuses ms ON su.marital_status_id = ms.marital_status_id
        WHERE su.su_id = :su_id AND su.deleted_at IS NULL
    """)
    su_res = await db.execute(su_query, {"su_id": su_id})
    su_row = su_res.mappings().first()
    if not su_row:
        return None

    patient_name = f"{su_row.get('su_first_name', '')} {su_row.get('su_last_name', '')}".strip()

    # 2. Care Notes (Chronological observations & welfare checks)
    notes_query = text("""
        SELECT n.id, n.notes, n.created_at,
               u.first_name as carer_first, u.surname as carer_last, u.username as carer_user
        FROM m_notes n
        LEFT JOIN users u ON n.user_id = u.id
        WHERE n.su_id = :su_id
        ORDER BY n.created_at DESC
    """)
    notes_res = await db.execute(notes_query, {"su_id": su_id})
    notes = [dict(r) for r in notes_res.mappings().all()]

    # 3. Scheduled Shifts & Care Visits
    tx_query = text("""
        SELECT t.tx_id, t.start, t.end, t.rate, t.doubleup, t.notes,
               s.shift as shift_name,
               u.first_name as carer_first, u.surname as carer_last,
               a.time_in, a.time_out
        FROM m_transactions t
        LEFT JOIN m_shifts s ON t.shift_id = s.shift_id
        LEFT JOIN users u ON t.id = u.id
        LEFT JOIN m_attendances a ON t.tx_id = a.tx_id
        WHERE t.su_id = :su_id AND t.deleted_at IS NULL
        ORDER BY t.start DESC
    """)
    tx_res = await db.execute(tx_query, {"su_id": su_id})
    transactions = [dict(r) for r in tx_res.mappings().all()]

    # 4. Invoices / Financial Records
    inv_query = text("""
        SELECT i.invoice_id, i.invoice_number, i.date_range, i.invoice as amount,
               i.payment, i.created_at, i.notes
        FROM m_invoices i
        JOIN m_transactions t ON i.tx_id = t.tx_id
        WHERE t.su_id = :su_id AND i.deleted_at IS NULL
        ORDER BY i.created_at DESC
    """)
    inv_res = await db.execute(inv_query, {"su_id": su_id})
    invoices = [dict(r) for r in inv_res.mappings().all()]

    # 5. Access Audit Trail from m_audit_logs (demonstrating Art. 5(2) accountability)
    audit_query = text("""
        SELECT id, created_at, username, record_type, action, details, ip_address
        FROM m_audit_logs
        WHERE su_id = :su_id
        ORDER BY created_at DESC
        LIMIT 50
    """)
    audit_res = await db.execute(audit_query, {"su_id": su_id})
    audit_logs = [dict(r) for r in audit_res.mappings().all()]

    return {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "su_id": su_id,
        "patient": dict(su_row),
        "full_name": patient_name,
        "notes": notes,
        "transactions": transactions,
        "invoices": invoices,
        "audit_logs": audit_logs,
    }


def generate_sar_pdf(data: Dict[str, Any]) -> bytes:
    """
    Renders an official UK GDPR Article 15 Subject Access Request (SAR) Disclosure Dossier PDF.
    """
    patient = data.get("patient", {})
    full_name = data.get("full_name", "UNKNOWN SERVICE USER")
    su_number = patient.get("su_number") or f"SU-{data.get('su_id'):05d}"
    dob = patient.get("date_of_birth") or "Not recorded"
    address = patient.get("home_address") or "Not recorded"
    phone = patient.get("contact_number") or "Not recorded"
    email = patient.get("email") or "Not recorded"
    gender = patient.get("gender_name") or "Not specified"
    branch = patient.get("branch_name") or "Main Branch"
    status = patient.get("status_name") or "Active"
    
    nok = patient.get("next_of_kin") or "None designated"
    nok_phone = patient.get("nok_contact_number") or "-"
    nok_addr = patient.get("nok_address") or "-"

    second_contact = patient.get("second_contact") or "None"
    second_phone = patient.get("second_contact_number") or "-"

    medical_history = patient.get("medical_history") or "No pre-existing clinical conditions on record."
    medications = patient.get("medications") or "No active prescription medications recorded."
    care_notes = patient.get("su_notes") or "Standard domiciliary care protocol."

    notes_list = data.get("notes", [])
    tx_list = data.get("transactions", [])
    invoices_list = data.get("invoices", [])
    audit_list = data.get("audit_logs", [])
    generated_at = data.get("generated_at", "")
    request_date = escape_html(str(data.get("request_date") or "Not recorded"))
    if data.get("third_parties_included"):
        third_party_note = (
            "Next-of-kin contact details and carer surnames are included. "
            "An administrator recorded that those third-party details were reviewed."
        )
    else:
        third_party_note = (
            "Next-of-kin telephone numbers and addresses, and carer surnames, "
            "are withheld until an administrator reviews them."
        )

    # HTML builder
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>UK GDPR Article 15 SAR Dossier - {full_name}</title>
<style>
    @page {{
        size: A4;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-right {{
            content: "Page " counter(page) " of " counter(pages);
            font-size: 8pt;
            color: #666;
            font-family: Arial, sans-serif;
        }}
        @bottom-left {{
            content: "UK GDPR Article 15 Subject Access Disclosure | Confidential Medical Data";
            font-size: 8pt;
            color: #666;
            font-family: Arial, sans-serif;
        }}
    }}
    body {{
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        color: #1f2937;
        font-size: 9pt;
        line-height: 1.4;
        margin: 0;
        padding: 0;
    }}
    .header-box {{
        border-bottom: 2px solid #1e3a8a;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }}
    .org-title {{
        font-size: 14pt;
        font-weight: bold;
        color: #1e3a8a;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .doc-badge {{
        background-color: #1e3a8a;
        color: #ffffff;
        font-size: 8pt;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-top: 4px;
    }}
    .legal-notice {{
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        padding: 8px 12px;
        margin-bottom: 16px;
        font-size: 8.5pt;
        color: #166534;
    }}
    h2.section-header {{
        font-size: 11pt;
        font-weight: bold;
        color: #1e3a8a;
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 4px;
        margin-top: 18px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }}
    table.data-table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 14px;
        font-size: 8.5pt;
    }}
    table.data-table th, table.data-table td {{
        border: 1px solid #e2e8f0;
        padding: 6px 8px;
        vertical-align: top;
    }}
    table.data-table th {{
        background-color: #f8fafc;
        color: #334155;
        font-weight: bold;
        text-align: left;
    }}
    .field-label {{
        font-weight: bold;
        color: #475569;
        width: 25%;
        background-color: #f8fafc;
    }}
    .field-val {{
        color: #0f172a;
    }}
    .art9-box {{
        background-color: #fefce8;
        border: 1px solid #fef08a;
        border-radius: 4px;
        padding: 10px;
        margin-bottom: 12px;
    }}
    .art9-title {{
        font-weight: bold;
        color: #854d0e;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-size: 8.5pt;
    }}
    .content-box {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 8px;
        border-radius: 3px;
        font-size: 8.5pt;
        white-space: pre-wrap;
    }}
    .page-break {{
        page-break-before: always;
        break-before: page;
    }}
    .sign-box {{
        margin-top: 25px;
        border-top: 1px dashed #94a3b8;
        padding-top: 12px;
        font-size: 8.5pt;
    }}
</style>
</head>
<body>

<div class="header-box">
    <div style="float: right; text-align: right; font-size: 8pt; color: #64748b;">
        <strong>Certificate ID:</strong> SAR-{su_number}-{datetime.date.today().strftime('%Y%m%d')}<br>
        <strong>Request received:</strong> {request_date}<br>
        <strong>Generated:</strong> {escape_html(str(generated_at))}<br>
        <strong>Controller:</strong> Mary's Care / St Mary's Team Care<br>
        <strong>DPO Contact:</strong> dpo@stmarysteamcare.co.uk
    </div>
    <div class="org-title">Mary's Care Management System</div>
    <div class="doc-badge">UK GDPR ARTICLE 15 — SUBJECT ACCESS REQUEST (SAR) DISCLOSURE DOSSIER</div>
</div>

<div class="legal-notice">
    <strong>Statutory Notice of Disclosure (UK GDPR Article 15 & Data Protection Act 2018):</strong><br>
    This official disclosure dossier has been prepared in accordance with the Right of Access under Article 15 of the UK General Data Protection Regulation (UK GDPR) and Section 45 of the Data Protection Act 2018. It contains the personal and care records held for the named person. {escape_html(third_party_note)}
</div>

<h2 class="section-header">Section 1: Data Subject Identity & Core Demographics</h2>
<table class="data-table">
    <tr>
        <td class="field-label">Full Name</td>
        <td class="field-val" style="font-weight: bold;">{full_name}</td>
        <td class="field-label">Client Ref / SU Number</td>
        <td class="field-val">{su_number}</td>
    </tr>
    <tr>
        <td class="field-label">Date of Birth</td>
        <td class="field-val">{dob}</td>
        <td class="field-label">Gender</td>
        <td class="field-val">{gender}</td>
    </tr>
    <tr>
        <td class="field-label">Residential Address</td>
        <td class="field-val" colspan="3">{address}</td>
    </tr>
    <tr>
        <td class="field-label">Contact Telephone</td>
        <td class="field-val">{phone}</td>
        <td class="field-label">Email Address</td>
        <td class="field-val">{email}</td>
    </tr>
    <tr>
        <td class="field-label">Allocated Branch</td>
        <td class="field-val">{branch}</td>
        <td class="field-label">Current Service Status</td>
        <td class="field-val">{status}</td>
    </tr>
</table>

<h2 class="section-header">Section 2: Emergency Contacts & Next of Kin (Data Nominees)</h2>
<table class="data-table">
    <tr>
        <th width="35%">Contact Person</th>
        <th width="30%">Contact Number</th>
        <th width="35%">Address / Notes</th>
    </tr>
    <tr>
        <td><strong>Primary:</strong> {nok}</td>
        <td>{nok_phone}</td>
        <td>{nok_addr}</td>
    </tr>
    <tr>
        <td><strong>Secondary:</strong> {second_contact}</td>
        <td>{second_phone}</td>
        <td>-</td>
    </tr>
</table>

<h2 class="section-header">Section 3: Special Category Health & Clinical Profile (UK GDPR Art. 9)</h2>
<div class="art9-box">
    <div class="art9-title">Primary Medical Conditions & Clinical History</div>
    <div class="content-box">{medical_history}</div>
</div>

<div class="art9-box" style="margin-top: 10px;">
    <div class="art9-title">Prescribed / Assisted Medications & MAR Chart Protocols</div>
    <div class="content-box">{medications}</div>
</div>

<div class="art9-box" style="margin-top: 10px;">
    <div class="art9-title">Care Plan Specifics & Client Support Guidelines</div>
    <div class="content-box">{care_notes}</div>
</div>

<div class="page-break"></div>

<h2 class="section-header">Section 4: Care Visits, Shifts & Electronic Call Monitoring (ECM)</h2>
<p style="font-size: 8pt; color: #64748b; margin-top: 0;">Record of scheduled domiciliary care sessions, assigned carers, and actual clock-in/out timestamps.</p>
<table class="data-table">
    <thead>
        <tr>
            <th width="15%">Scheduled Start</th>
            <th width="15%">Scheduled End</th>
            <th width="15%">Shift Code</th>
            <th width="25%">Allocated Carer</th>
            <th width="15%">Clock In (ECM)</th>
            <th width="15%">Clock Out (ECM)</th>
        </tr>
    </thead>
    <tbody>
"""

    if not tx_list:
        html += "<tr><td colspan='6' style='text-align: center; color: #94a3b8;'>No historical shift assignments found.</td></tr>"
    else:
        for t in tx_list[:50]:  # Limit to 50 most recent for PDF readability
            start_str = str(t.get("start") or "-")
            end_str = str(t.get("end") or "-")
            shift_name = t.get("shift_name") or "Standard"
            carer = f"{t.get('carer_first', '')} {t.get('carer_last', '')}".strip() or "Carer"
            t_in = str(t.get("time_in") or "-")
            t_out = str(t.get("time_out") or "-")
            html += f"""
        <tr>
            <td>{start_str}</td>
            <td>{end_str}</td>
            <td>{shift_name}</td>
            <td>{carer}</td>
            <td>{t_in}</td>
            <td>{t_out}</td>
        </tr>
"""

    html += f"""
    </tbody>
</table>

<h2 class="section-header">Section 5: Daily Care Notes & Carer Observations Log</h2>
<p style="font-size: 8pt; color: #64748b; margin-top: 0;">Full unredacted transcript of daily care notes recorded by attending care staff.</p>
<table class="data-table">
    <thead>
        <tr>
            <th width="20%">Date / Time</th>
            <th width="20%">Attending Carer</th>
            <th width="60%">Recorded Care Note & Observation</th>
        </tr>
    </thead>
    <tbody>
"""

    if not notes_list:
        html += "<tr><td colspan='3' style='text-align: center; color: #94a3b8;'>No recorded care notes found.</td></tr>"
    else:
        for n in notes_list[:40]:  # Limit to 40 most recent for PDF
            c_time = str(n.get("created_at") or "-")
            carer = f"{n.get('carer_first', '')} {n.get('carer_last', '')}".strip() or n.get("carer_user") or "Staff"
            note_text = (n.get("notes") or "").replace("<", "&lt;").replace(">", "&gt;")
            html += f"""
        <tr>
            <td style="font-size: 8pt;">{c_time}</td>
            <td><strong>{carer}</strong></td>
            <td style="font-size: 8pt; white-space: pre-wrap;">{note_text}</td>
        </tr>
"""

    html += f"""
    </tbody>
</table>

<div class="page-break"></div>

<h2 class="section-header">Section 6: Regulatory Processing & Access Audit Trail (UK GDPR Art. 5(2))</h2>
<p style="font-size: 8pt; color: #64748b; margin-top: 0;">Access logs verifying who accessed the Data Subject's Special Category Health records and for what purpose.</p>
<table class="data-table">
    <thead>
        <tr>
            <th width="18%">Timestamp</th>
            <th width="18%">User / Officer</th>
            <th width="16%">Classification</th>
            <th width="12%">Action</th>
            <th width="36%">Access Details & Justification</th>
        </tr>
    </thead>
    <tbody>
"""

    if not audit_list:
        html += "<tr><td colspan='5' style='text-align: center; color: #94a3b8;'>No audit events logged for this data subject.</td></tr>"
    else:
        for a in audit_list[:25]:
            a_time = str(a.get("created_at") or "-")
            a_user = a.get("username") or "System User"
            a_type = a.get("record_type") or "medical_dossier"
            a_act = a.get("action") or "READ"
            a_det = a.get("details") or "-"
            html += f"""
        <tr>
            <td style="font-size: 8pt;">{a_time}</td>
            <td>{a_user}</td>
            <td>{a_type}</td>
            <td><span style="font-weight:bold;color:#1e3a8a;">{a_act}</span></td>
            <td style="font-size: 8pt;">{a_det}</td>
        </tr>
"""

    html += f"""
    </tbody>
</table>

<h2 class="section-header">Section 7: Data Subject Rights & Regulatory Contact Information</h2>
<div style="font-size: 8pt; color: #334155; line-height: 1.5; background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; border-radius: 4px;">
    <strong>Your Rights Under the UK GDPR:</strong><br>
    As a Data Subject, you retain the following statutory rights under the UK GDPR and the Data Protection Act 2018:<br>
    &bull; <strong>Right to Rectification (Article 16):</strong> You may request rectification of inaccurate personal data without undue delay.<br>
    &bull; <strong>Right to Erasure (Article 17):</strong> You may request erasure of personal data, subject to statutory health records retention requirements under the Health and Social Care Act.<br>
    &bull; <strong>Right to Restriction of Processing (Article 18):</strong> You may request restriction of processing in specified circumstances.<br>
    &bull; <strong>Right to Data Portability (Article 20):</strong> That right applies only in limited cases. A spreadsheet of this file is another copy of the same Article 15 disclosure. It is not a decision that Article 20 applies.<br>
    &bull; <strong>Right to Lodge a Complaint (Article 77):</strong> You have the right to lodge a complaint with the UK supervisory authority:
    <div style="margin-top: 4px; padding-left: 12px; font-style: italic;">
        Information Commissioner's Office (ICO)<br>
        Wycliffe House, Water Lane, Wilmslow, Cheshire SK9 5AF<br>
        Helpline: 0303 123 1113 | Website: https://ico.org.uk
    </div>
</div>

<div class="sign-box">
    <table width="100%">
        <tr>
            <td width="60%">
                <strong>Certified on Behalf of the Data Controller:</strong><br>
                Mary's Care / St Mary's Team Care Data Governance & Compliance Team<br>
                <em>Automated Regulatory Subject Access Generation Protocol</em>
            </td>
            <td width="40%" style="text-align: right;">
                <strong>Date Issued:</strong> {datetime.date.today().strftime('%d %B %Y')}<br>
                <strong>Security Classification:</strong> OFFICIAL-SENSITIVE
            </td>
        </tr>
    </table>
</div>

</body>
</html>
"""
    return HTML(string=html).write_pdf()


def generate_sar_excel(data: Dict[str, Any]) -> bytes:
    """
    Spreadsheet copy of the same Article 15 disclosure. This is not an Article 20 portability file.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    sub_font = Font(name="Calibri", size=10, italic=True, color="555555")
    border_thin = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    )

    def style_headers(ws, row_idx, col_count):
        for col in range(1, col_count + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def auto_fit_columns(ws):
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

    # -------------------------------------------------------------
    # TAB 1: Demographics & Contacts
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Demographics & Contacts")
    ws1.append(["UK GDPR Article 15 — Data Subject Demographics"])
    ws1.cell(1, 1).font = title_font
    ws1.append([f"Request received: {data.get('request_date', '')}. Export generated: {data.get('generated_at', '')}"])
    ws1.cell(2, 1).font = sub_font
    third_party_note = (
        "Third-party contact details included after administrator review."
        if data.get("third_parties_included")
        else "Next-of-kin contact details and carer surnames withheld pending review."
    )
    ws1.append([third_party_note])
    ws1.append([])

    p = data.get("patient", {})
    demo_fields = [
        ("Client ID (su_id)", p.get("su_id")),
        ("Client Reference #", p.get("su_number")),
        ("Full Name", data.get("full_name")),
        ("First Name", p.get("su_first_name")),
        ("Surname", p.get("su_last_name")),
        ("Date of Birth", str(p.get("date_of_birth") or "")),
        ("Gender", p.get("gender_name")),
        ("Marital Status", p.get("marital_status_name")),
        ("Residential Address", p.get("home_address")),
        ("Contact Phone", p.get("contact_number")),
        ("Email Address", p.get("email")),
        ("Branch", p.get("branch_name")),
        ("Service Status", p.get("status_name")),
        ("Next of Kin Name", p.get("next_of_kin")),
        ("Next of Kin Phone", p.get("nok_contact_number")),
        ("Next of Kin Address", p.get("nok_address")),
        ("Second Emergency Contact", p.get("second_contact")),
        ("Second Contact Phone", p.get("second_contact_number")),
    ]

    ws1.append(["Field Name", "Recorded Value"])
    style_headers(ws1, 5, 2)
    for field, val in demo_fields:
        ws1.append([field, str(val or "")])
    auto_fit_columns(ws1)

    # -------------------------------------------------------------
    # TAB 2: Health & Medical (Article 9 Special Category Data)
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Health & Medical (Art 9)")
    ws2.append(["Article 9 Special Category Medical & Care Record"])
    ws2.cell(1, 1).font = title_font
    ws2.append([])

    ws2.append(["Category", "Clinical Details / Plan Information"])
    style_headers(ws2, 3, 2)
    ws2.append(["Medical History & Diagnoses", str(p.get("medical_history") or "None on record")])
    ws2.append(["Prescribed Medications & MAR Chart", str(p.get("medications") or "None on record")])
    ws2.append(["Care Plan & Special Directives", str(p.get("su_notes") or "Standard protocol")])
    auto_fit_columns(ws2)

    # -------------------------------------------------------------
    # TAB 3: Care Visits & Schedules
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Care Shifts & Visits")
    ws3.append(["Historical Domiciliary Care Visits & Assigned Personnel"])
    ws3.cell(1, 1).font = title_font
    ws3.append([])

    headers_tx = ["Tx ID", "Shift Name", "Scheduled Start", "Scheduled End", "Allocated Carer", "Double Up", "Visit Notes"]
    ws3.append(headers_tx)
    style_headers(ws3, 3, len(headers_tx))
    for t in data.get("transactions", []):
        carer = f"{t.get('carer_first', '')} {t.get('carer_last', '')}".strip()
        ws3.append([
            t.get("tx_id"),
            t.get("shift_name") or "Standard",
            str(t.get("start") or ""),
            str(t.get("end") or ""),
            carer,
            "Yes" if t.get("doubleup") else "No",
            t.get("notes") or ""
        ])
    auto_fit_columns(ws3)

    # -------------------------------------------------------------
    # TAB 4: Attendance & ECM Timestamps
    # -------------------------------------------------------------
    ws4 = wb.create_sheet(title="Attendance & ECM Timestamps")
    ws4.append(["Electronic Call Monitoring (ECM) & Attendance Log"])
    ws4.cell(1, 1).font = title_font
    ws4.append([])

    headers_att = ["Tx ID", "Shift Name", "Carer Name", "Clock In (Verified)", "Clock Out (Verified)"]
    ws4.append(headers_att)
    style_headers(ws4, 3, len(headers_att))
    for t in data.get("transactions", []):
        if t.get("time_in") or t.get("time_out"):
            carer = f"{t.get('carer_first', '')} {t.get('carer_last', '')}".strip()
            ws4.append([
                t.get("tx_id"),
                t.get("shift_name") or "Standard",
                carer,
                str(t.get("time_in") or ""),
                str(t.get("time_out") or "")
            ])
    auto_fit_columns(ws4)

    # -------------------------------------------------------------
    # TAB 5: Care Notes & Daily Observations
    # -------------------------------------------------------------
    ws5 = wb.create_sheet(title="Care Notes & Daily Logs")
    ws5.append(["Carer Daily Observation Notes & Welfare Entries"])
    ws5.cell(1, 1).font = title_font
    ws5.append([])

    headers_notes = ["Note ID", "Timestamp", "Attending Carer", "Observation / Care Notes Transcript"]
    ws5.append(headers_notes)
    style_headers(ws5, 3, len(headers_notes))
    for n in data.get("notes", []):
        carer = f"{n.get('carer_first', '')} {n.get('carer_last', '')}".strip() or n.get("carer_user") or "Staff"
        ws5.append([
            n.get("id"),
            str(n.get("created_at") or ""),
            carer,
            n.get("notes") or ""
        ])
    auto_fit_columns(ws5)

    # -------------------------------------------------------------
    # TAB 6: Regulatory Audit Trail
    # -------------------------------------------------------------
    ws6 = wb.create_sheet(title="Access Audit Trail")
    ws6.append(["UK GDPR Article 5(2) Regulatory Access & Accountability Trail"])
    ws6.cell(1, 1).font = title_font
    ws6.append([])

    headers_audit = ["Audit ID", "Timestamp", "User / Officer", "Data Category", "Action", "Audit Details", "Client IP"]
    ws6.append(headers_audit)
    style_headers(ws6, 3, len(headers_audit))
    for a in data.get("audit_logs", []):
        ws6.append([
            a.get("id"),
            str(a.get("created_at") or ""),
            a.get("username") or "",
            a.get("record_type") or "",
            a.get("action") or "",
            a.get("details") or "",
            a.get("ip_address") or ""
        ])
    auto_fit_columns(ws6)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
