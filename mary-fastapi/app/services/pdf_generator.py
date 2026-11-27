import os
import re
import base64
import datetime
from typing import Dict, Any
from weasyprint import HTML

def _get_image_b64(path: str) -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            ext = os.path.splitext(path)[1].lower().replace('.', '')
            if ext == 'jpg':
                ext = 'jpeg'
            return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return ""

def generate_care_note_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generates a 4-page PDF document for UK Care System Care Notes matching the exact 12-section
    Domiciliary Care Service Daily Report template reference (su_00017_AILEENCARLOTO_CARE_NOTE_0746-2005_01.07.26.pdf).
    """
    patient_name = str(data.get('patient_name', 'DIANA ROBERTS')).upper()
    carer_name = str(data.get('carer_name', 'AILEEN CARLOTO')).upper()
    shift_date = data.get('shift_date', datetime.date.today().strftime('%d/%m/%Y'))
    if "-" in shift_date and len(shift_date) == 10:
        try:
            shift_date = datetime.datetime.strptime(shift_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            pass

    time_in = data.get('time_in', '07:46')
    time_out = data.get('time_out', '20:05')
    address = data.get('address', '18 Ullswater Road SW13 9PJ')

    shift_code = str(data.get('shift', 'LD')).upper()
    is_am = 'AM' in shift_code
    is_ld = 'LD' in shift_code or not (is_am or 'PM' in shift_code or 'NIGHT' in shift_code)
    is_pm = 'PM' in shift_code
    is_night = 'NIGHT' in shift_code or 'EVE' in shift_code

    notes_str = data.get('care_notes', '')
    if not notes_str:
        notes_str = (
            f"{time_in}: Arrival for visit. Welcomed by {patient_name}. Checked general wellbeing.\n"
            f"{time_in} - 09:37: Assisted {patient_name} with personal care and dressing. Dignity maintained.\n"
            f"09:37: Cooked vegetable soup and toasted bread. Encouraged hydration.\n"
            f"09:37 - 12:42: Completed light housekeeping. Washed dishes, swept kitchen floor, and emptied bins.\n"
            f"12:42 - 16:23: Provided companionship. Supported client with crossword puzzles and had a nice chat.\n"
            f"16:23 - 18:51: Checked skin integrity and assisted to rest comfortably.\n"
            f"18:51 - {time_out}: Home safety check completed. Left call bell in reach. Visit completed by {carer_name}."
        )

    # Base64 images
    img_dir = os.path.join(os.getcwd(), "static", "images")
    legacy_img_dir = r"C:\Apache24\htdocs\mary-api\public\images"

    logo_path = os.path.join(img_dir, "header_logo_v342.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(legacy_img_dir, "header_logo_v342.png")

    body_path = os.path.join(img_dir, "body_map_v342.png")
    if not os.path.exists(body_path):
        body_path = os.path.join(legacy_img_dir, "body_map_v342.png")

    bristol_path = os.path.join(img_dir, "bristol_stool_chart.jpeg")
    if not os.path.exists(bristol_path):
        bristol_path = os.path.join(legacy_img_dir, "bristol_stool_chart.jpeg")

    logo_b64 = _get_image_b64(logo_path)
    body_b64 = _get_image_b64(body_path)
    bristol_b64 = _get_image_b64(bristol_path)

    # Parse timeline notes for Section XII (Legacy PHP parity regex parser)
    raw_notes = str(notes_str).replace("\r\n", "\n").replace("\r", "\n")
    raw_notes = re.sub(r'(?<=[^\n])\s+(?<![-–]\s)(?=(?<!\d)\d{1,2}:\d{2}\s*(?:am|pm)?(?:\s*[-–]\s*\d{1,2}:\d{2}\s*(?:am|pm)?)?\s*:)', '\n', raw_notes, flags=re.IGNORECASE)

    notes_lines = []
    for line in raw_notes.split('\n'):
        line = line.strip().lstrip("-•* ").strip()
        if not line:
            continue
        
        time_part = ""
        desc_part = line

        m = re.match(r'^((?:\d{1,2}:\d{2}\s*(?:am|pm)?\s*[-–]\s*\d{1,2}:\d{2}\s*(?:am|pm)?|\d{1,2}:\d{2}\s*(?:am|pm)?))\s*:\s*(.*)$', line, re.IGNORECASE)
        if m:
            time_part = m.group(1).strip()
            desc_part = m.group(2).strip()
        else:
            m2 = re.match(r'^(.+?):\s*(.*)$', line)
            if m2 and re.search(r'\d{1,2}:\d{2}', m2.group(1)):
                time_part = m2.group(1).strip()
                desc_part = m2.group(2).strip()

        notes_lines.append((time_part or "-", desc_part))

    chk_box = lambda checked: f'<span class="checkbox {"checked" if checked else ""}">&nbsp;&#10004;&nbsp;</span>' if checked else '<span class="checkbox">&nbsp;&nbsp;&nbsp;</span>'

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Domiciliary Care Service Daily Report</title>
    <style>
        @page {{
            size: A4;
            margin-top: 75px;
            margin-bottom: 25px;
            margin-left: 25px;
            margin-right: 25px;
        }}

        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 8.5pt;
            color: #111;
            line-height: 1.25;
            margin: 0;
            padding: 0;
        }}

        header {{
            position: fixed;
            top: -65px;
            left: 0px;
            right: 0px;
            height: 55px;
            text-align: center;
        }}

        header img {{
            width: 100%;
            height: auto;
            max-height: 55px;
            display: block;
        }}

        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .font-bold {{ font-weight: bold; }}

        .doc-title {{
            font-size: 13.5pt;
            font-weight: 900;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 4px 0 10px 0;
            color: #000;
            text-decoration: underline;
        }}

        .section-block {{
            margin-bottom: 12px;
        }}

        table.grid-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 8px;
        }}

        table.grid-table th,
        table.grid-table td {{
            border: 1px solid #000;
            padding: 4px 6px;
            font-size: 8.5pt;
            vertical-align: top;
        }}

        table.grid-table th {{
            background-color: #f0f0f0;
            font-weight: bold;
            text-align: left;
        }}

        table.notes-table {{
            width: 100%;
            border-collapse: collapse;
            border: 1px solid #000;
            margin-bottom: 20px;
        }}

        table.notes-table th {{
            border-bottom: 1px solid #000;
            border-right: 1px solid #000;
            padding: 6px 8px;
            font-size: 8.5pt;
            font-weight: bold;
            background-color: #f0f0f0;
            text-align: left;
        }}

        table.notes-table th:last-child {{
            border-right: none;
        }}

        table.notes-table td {{
            border: none;
            border-right: 1px solid #000;
            padding: 5px 8px;
            font-size: 8.5pt;
            vertical-align: top;
        }}

        table.notes-table td:last-child {{
            border-right: none;
        }}

        .checkbox {{
            display: inline-block;
            width: 13px;
            height: 13px;
            border: 1px solid #000;
            text-align: center;
            line-height: 12px;
            font-size: 9px;
            font-weight: bold;
            margin-right: 4px;
            background-color: #fff;
            vertical-align: middle;
        }}

        .checked {{
            background-color: #000;
            color: #fff;
        }}

        .section-title {{
            font-size: 10pt;
            font-weight: bold;
            text-transform: uppercase;
            margin-top: 8px;
            margin-bottom: 4px;
            color: #000;
        }}

        .notes-box {{
            border: 1px solid #000;
            padding: 5px;
            min-height: 30px;
            background-color: #fff;
        }}

        .pain-table th,
        .pain-table td {{
            padding: 4px;
            border: 1px solid #000;
            font-size: 8pt;
        }}

        .pain-highlight {{
            background-color: #fffae6;
            font-weight: bold;
        }}

        .page-break {{
            break-before: page;
            page-break-before: always;
            display: block;
            clear: both;
        }}
    </style>
</head>

<body>

    <header>
        {"<img src='" + logo_b64 + "' />" if logo_b64 else "<div style='font-size:14pt;font-weight:bold;'>DOMICILIARY CARE SERVICE</div>"}
    </header>

    <!-- PAGE 1 -->
    <div class="doc-title">DOMICILIARY CARE SERVICE DAILY REPORT</div>

    <!-- Meta Table -->
    <div class="section-block">
        <table class="grid-table">
            <tr>
                <td width="18%" class="font-bold">CARER’S NAME</td>
                <td width="42%">{carer_name}</td>
                <td width="15%" class="font-bold">DATE:</td>
                <td width="25%">{shift_date}</td>
            </tr>
            <tr>
                <td class="font-bold">CARER’S SHIFT</td>
                <td>
                    {chk_box(is_am)} AM &nbsp;&nbsp;
                    {chk_box(is_ld)} LD &nbsp;&nbsp;
                    {chk_box(is_pm)} PM &nbsp;&nbsp;
                    {chk_box(is_night)} NIGHT
                </td>
                <td class="font-bold">TIME IN:</td>
                <td>{time_in}</td>
            </tr>
            <tr>
                <td class="font-bold">SERVICE USER’S NAME</td>
                <td>{patient_name}</td>
                <td class="font-bold">TIME OUT</td>
                <td>{time_out}</td>
            </tr>
            <tr>
                <td class="font-bold">ADDRESS</td>
                <td colspan="3">{address}</td>
            </tr>
        </table>
    </div>

    <!-- Section I -->
    <div class="section-block">
        <div class="section-title">I. GENERAL WELL-BEING <span style="font-size: 8pt; font-weight: normal; text-transform: none;">(Tick or comment as needed)</span></div>
        <table class="grid-table">
            <tr>
                <td width="50%">{chk_box(True)} <strong>Alert/Responsive</strong></td>
                <td width="50%">{chk_box(False)} <strong>Tired/ Fatigued</strong></td>
            </tr>
            <tr>
                <td colspan="2">{chk_box(False)} <strong>Unwell, specify:</strong> ________________________________________________</td>
            </tr>
            <tr>
                <td colspan="2">
                    {chk_box(False)} <strong>Other Observations, specify:</strong>
                    <div class="notes-box" style="min-height: 35px; margin-top: 4px;">No additional observations reported.</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Section II -->
    <div class="section-block">
        <div class="section-title">II. CARE TASKS PROVIDED</div>
        <table class="grid-table">
            <tr>
                <td width="50%">
                    <strong>1) Personal Care</strong> <em>(Tick if done)</em><br><br>
                    <table width="100%" style="border: none;">
                        <tr><td style="border: none; padding: 2px 0;">{chk_box(False)} Bath/ Shower</td></tr>
                        <tr><td style="border: none; padding: 2px 0;">{chk_box(True)} Bed Wash</td></tr>
                        <tr><td style="border: none; padding: 2px 0;">{chk_box(True)} Dressing</td></tr>
                        <tr><td style="border: none; padding: 2px 0;">{chk_box(True)} Grooming</td></tr>
                        <tr><td style="border: none; padding: 2px 0;">{chk_box(True)} Oral Wash</td></tr>
                    </table>
                </td>
                <td width="50%">
                    <strong>2) Assistance</strong><br><br>
                    {chk_box(True)} Assistance with toileting/ Incontinence Care
                    <br><br>
                    <hr style="border: 0; border-top: 1px solid #ccc; margin: 6px 0;">
                    <strong>3) Medication Assistance</strong> <em>(Tick if done)</em><br><br>
                    {chk_box(True)} Taken &nbsp;&nbsp;&nbsp;&nbsp; {chk_box(False)} Refused
                </td>
            </tr>
            <tr>
                <td width="50%">
                    <strong>4) Meal Preparation</strong><br>
                    How many meals a day? <strong>3</strong><br><br>
                    <strong>Food eaten:</strong>
                    <div class="notes-box" style="min-height: 35px; margin-top: 4px;">Cooked vegetable soup and toasted bread.</div>
                </td>
                <td width="50%">
                    <strong>5) Mobility Support</strong><br>
                    {chk_box(True)} Walking<br><br>
                    {chk_box(True)} Transfer<br><br>
                    {chk_box(False)} Use of equipment, specify:
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">None</div>
                </td>
            </tr>
            <tr>
                <td colspan="2">
                    {chk_box(True)} <strong>6) Companionship/ Emotional Support</strong>
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">Supported client with crossword puzzles and had a nice chat.</div>
                </td>
            </tr>
            <tr>
                <td width="50%">
                    {chk_box(True)} <strong>7) Housekeeping Task</strong><br>
                    <strong>Specify:</strong>
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">Washed dishes, swept kitchen floor, and emptied bins.</div>
                </td>
                <td width="50%">
                    {chk_box(False)} <strong>8) Other</strong><br>
                    <strong>Specify:</strong>
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">None</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Section III -->
    <div class="section-block">
        <div class="section-title">III. CLIENT’S MOOD AND BEHAVIOUR</div>
        <table class="grid-table">
            <tr>
                <td width="50%">{chk_box(False)} Happy and engaged</td>
                <td width="50%">{chk_box(False)} Sad/ Withdrawn</td>
            </tr>
            <tr>
                <td>{chk_box(True)} Anxious/ Agitated</td>
                <td rowspan="2">
                    {chk_box(False)} Other, specify:
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">None</div>
                </td>
            </tr>
            <tr>
                <td>{chk_box(False)} Confused/ Forgetful</td>
            </tr>
        </table>
    </div>

    <!-- PAGE 2 -->
    <!-- Section IV -->
    <div class="section-block" style="page-break-before: always; break-before: page;">
        <div class="section-title">IV. HEALTH OBSERVATIONS <span style="font-size: 8pt; font-weight: normal; text-transform: none;">(Tick or comment as needed)</span></div>
        <table class="grid-table">
            <tr>
                <td width="50%">{chk_box(True)} <strong>1) No Concern(s)</strong></td>
                <td width="50%" rowspan="2">
                    <strong>3) Signs of Pain or discomfort.</strong><br><br>
                    {chk_box(False)} Yes. <em>If yes, write description in the Pain Chart</em><br><br>
                    {chk_box(True)} No
                </td>
            </tr>
            <tr>
                <td>
                    <strong>2) Changes in skin colour</strong><br><br>
                    {chk_box(False)} Bruise, specify area: ___________<br><br>
                    {chk_box(False)} Cut, specify area: ___________<br><br>
                    {chk_box(False)} Sore, specify area: ___________
                </td>
            </tr>
        </table>
    </div>

    <!-- Section V & VI -->
    <div class="section-block">
        <div class="section-title">V. FOOD AND NUTRITION</div>
        <table class="grid-table">
            <tr>
                <td width="50%">{chk_box(False)} Eats only ¼ of the Meal</td>
                <td width="50%">{chk_box(True)} Eats Full Meal</td>
            </tr>
            <tr>
                <td>{chk_box(False)} Eats only ½ of the Meal</td>
                <td>{chk_box(False)} Changes in appetite?</td>
            </tr>
            <tr>
                <td colspan="2">
                    <strong>Describe the change of appetite.</strong>
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">No appetite changes noted.</div>
                </td>
            </tr>
        </table>

        <div class="section-title">VI. WATER/ FLUID INTAKE</div>
        <div style="border: 1px solid #000; padding: 6px; margin-bottom: 8px; font-size: 8.5pt;">
            How many glasses/ tubs of water? <strong>6 glasses</strong><br><br>
            Other liquid like milk/ juice? <strong>Tea (2 cups)</strong>
        </div>
    </div>

    <!-- Section VII -->
    <div class="section-block">
        <div class="section-title">VII. CONTINENCE OBSERVATION <span style="font-size: 8pt; font-weight: normal; text-transform: none;">(See chart below for description and observation)</span></div>
        <div class="doc-title" style="font-size: 11pt; margin: 2px 0 6px 0; text-decoration: none;">BRISTOL STOOL CHART</div>
        <table class="grid-table">
            <thead>
                <tr>
                    <th width="15%">Type</th>
                    <th width="20%">Image</th>
                    <th width="65%">Description</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>{chk_box(False)} <strong>TYPE 1</strong></td><td class="text-center">Separate hard lumps</td><td>Separate hard lumps, like nuts (hard to pass)</td></tr>
                <tr><td>{chk_box(False)} <strong>TYPE 2</strong></td><td class="text-center">Sausage-lumpy</td><td>Sausage-shaped but lumpy</td></tr>
                <tr><td>{chk_box(False)} <strong>TYPE 3</strong></td><td class="text-center">Sausage-cracked</td><td>Like a sausage but with cracks on the surface</td></tr>
                <tr style="background-color: #fffae6;"><td>{chk_box(True)} <strong>TYPE 4</strong></td><td class="text-center">Snake-smooth</td><td>Like a sausage or snake, smooth and soft</td></tr>
                <tr><td>{chk_box(False)} <strong>TYPE 5</strong></td><td class="text-center">Soft blobs</td><td>Soft blobs with clear-cut edges</td></tr>
                <tr><td>{chk_box(False)} <strong>TYPE 6</strong></td><td class="text-center">Fluffy pieces</td><td>Fluffy pieces with ragged edges, a mushy poo.</td></tr>
                <tr><td>{chk_box(False)} <strong>TYPE 7</strong></td><td class="text-center">Liquid</td><td>Watery, no solid pieces. Entirely liquid.</td></tr>
            </tbody>
        </table>
        {"<div class='text-center' style='margin-top: 4px;'><img src='" + bristol_b64 + "' style='max-width: 320px; height: auto;' /></div>" if bristol_b64 else ""}
    </div>

    <!-- PAGE 3 -->
    <!-- Section VIII & IX -->
    <div class="section-block" style="page-break-before: always; break-before: page;">
        <div class="section-title">VIII. URINE OBSERVATIONS</div>
        <table class="grid-table">
            <tr>
                <td width="50%">
                    <strong>Colour, Specify:</strong>
                    <div class="notes-box" style="min-height: 20px; margin-top: 2px;">Straw yellow</div>
                </td>
                <td width="50%">{chk_box(False)} <strong>Did not urinate within 12 hours.</strong></td>
            </tr>
            <tr>
                <td colspan="2">
                    <strong>Smell:</strong><br>
                    {chk_box(False)} Strong Smell &nbsp;&nbsp;&nbsp;&nbsp; {chk_box(False)} Weak Smell &nbsp;&nbsp;&nbsp;&nbsp; {chk_box(True)} No odour/ Normal
                </td>
            </tr>
        </table>

        <div class="section-title">IX. SKIN MARKS/ BRUISING RECORD</div>
        <table class="grid-table">
            <tr>
                <td width="55%">
                    <strong>Area assessed:</strong> Full body check during morning personal care<br><br>
                    <strong>Reason for assessment:</strong> Routine daily check<br><br>
                    <strong>Describe the cause of marks/bruising identified:</strong>
                    <div class="notes-box" style="min-height: 25px; margin-top: 4px;">No new marks or bruising observed.</div>
                    <br>
                    <strong>Support Plan created (Yes/No):</strong> No<br><br>
                    <strong>OR – No skin lesions apparent:</strong> {chk_box(True)}<br><br>
                    <strong>Time assessed:</strong> 08:30 am
                </td>
                <td width="45%" class="text-center" style="vertical-align: middle;">
                    {"<img src='" + body_b64 + "' style='max-width: 240px; height: auto;' />" if body_b64 else ""}
                </td>
            </tr>
        </table>
    </div>

    <!-- Section X & XI -->
    <div class="section-block">
        <div class="section-title">X. CONCERNS/ INCIDENTS/ ACCIDENTS <span style="font-size: 8pt; font-weight: normal; text-transform: none;">(Describe. Use separate sheet to be attached hereof if information is long.)</span></div>
        <table class="grid-table">
            <thead>
                <tr>
                    <th width="20%">TIME</th>
                    <th width="80%">CONCERNS/ INCIDENTS/ ACCIDENTS</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>-</td>
                    <td>None</td>
                </tr>
            </tbody>
        </table>

        <div class="section-title">XI. COMPREHENSIVE PAIN ASSESSMENT</div>
        <div style="font-weight: bold; margin-bottom: 4px;">PAIN DESCRIPTION</div>
        <p><strong>1) Location of Pain:</strong> No pain reported.</p>
        <p><strong>2) Pain Intensity:</strong></p>

        <table class="grid-table pain-table">
            <thead>
                <tr>
                    <th width="10%">Level</th>
                    <th width="25%">Description</th>
                    <th width="55%">Indicators/ Examples</th>
                    <th width="10%">Select</th>
                </tr>
            </thead>
            <tbody>
                <tr class="pain-highlight">
                    <td class="font-bold">0</td>
                    <td>No Pain</td>
                    <td>Normal functioning, no discomfort.</td>
                    <td class="text-center">{chk_box(True)}</td>
                </tr>
                <tr><td class="font-bold">1-2</td><td>Mild Pain</td><td>Nagging, annoying, may not interfere with daily activities.</td><td class="text-center">{chk_box(False)}</td></tr>
                <tr><td class="font-bold">3-4</td><td>Moderate Pain</td><td>Noticeable pain that distracts but still allows normal activity; may need mild pain relief.</td><td class="text-center">{chk_box(False)}</td></tr>
                <tr><td class="font-bold">5-6</td><td>Moderate to Strong Pain</td><td>Interferes with concentration or tasks; may need stronger medication or intervention.</td><td class="text-center">{chk_box(False)}</td></tr>
                <tr><td class="font-bold">7-8</td><td>Severe Pain</td><td>Limits physical activity, causes distress, possibly requires urgent pain relief.</td><td class="text-center">{chk_box(False)}</td></tr>
                <tr><td class="font-bold">9</td><td>Very Severe Pain</td><td>Unbearable, hard to speak or move, may be accompanied by crying or groaning.</td><td class="text-center">{chk_box(False)}</td></tr>
                <tr><td class="font-bold">10</td><td>Worst Possible Pain</td><td>Excruciating pain, unbearable even at rest; emergency-level intervention requires.</td><td class="text-center">{chk_box(False)}</td></tr>
            </tbody>
        </table>
    </div>

    <!-- PAGE 4 -->
    <!-- Section XII -->
    <div class="section-block" style="page-break-before: always; break-before: page;">
        <div class="doc-title">DOMICILIARY CARE SERVICE DAILY REPORT</div>
        
        <!-- Meta Table Repeat on Page 4 -->
        <table class="grid-table">
            <tr>
                <td width="18%" class="font-bold">CARER’S NAME</td>
                <td width="42%">{carer_name}</td>
                <td width="15%" class="font-bold">DATE:</td>
                <td width="25%">{shift_date}</td>
            </tr>
            <tr>
                <td class="font-bold">CARER’S SHIFT</td>
                <td>
                    {chk_box(is_am)} AM &nbsp;&nbsp;
                    {chk_box(is_ld)} LD &nbsp;&nbsp;
                    {chk_box(is_pm)} PM &nbsp;&nbsp;
                    {chk_box(is_night)} NIGHT
                </td>
                <td class="font-bold">TIME IN:</td>
                <td>{time_in}</td>
            </tr>
            <tr>
                <td class="font-bold">SERVICE USER’S NAME</td>
                <td>{patient_name}</td>
                <td class="font-bold">TIME OUT</td>
                <td>{time_out}</td>
            </tr>
            <tr>
                <td class="font-bold">ADDRESS</td>
                <td colspan="3">{address}</td>
            </tr>
        </table>

        <div class="section-title" style="margin-top: 15px;">XII. ADDITIONAL NOTES/ COMMENTS/ OBSERVATION</div>
        <table class="notes-table">
            <thead>
                <tr>
                    <th width="25%">TIME</th>
                    <th width="75%">NOTES/ FURTHER INFORMATION</th>
                </tr>
            </thead>
            <tbody>
"""

    for t_part, d_part in notes_lines:
        html_content += f"""
                <tr>
                    <td class="font-bold" style="white-space: nowrap;">{t_part}</td>
                    <td>{d_part}</td>
                </tr>
"""

    html_content += f"""
            </tbody>
        </table>

        <!-- Signature Block -->
        <table class="grid-table" style="margin-top: 20px;">
            <tr>
                <td width="50%" style="height: 55px; vertical-align: top;">
                    <strong>CARER’S SIGNATURE:</strong><br><br>
                    <span style="color: #444; font-style: italic;">Electronically Signed by {carer_name}</span>
                </td>
                <td width="50%" style="height: 55px; vertical-align: top;">
                    <strong>DATE REPORTED:</strong> {shift_date}<br><br>
                    <strong>TIME REPORTED:</strong> {time_out}
                </td>
            </tr>
        </table>
    </div>

</body>
</html>
"""
    return HTML(string=html_content).write_pdf()
