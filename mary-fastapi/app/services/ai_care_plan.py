import os
import re
import json
import logging
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# A carer break belongs only to a visit of 8 hours or more.
BREAK_THRESHOLD_MINUTES = 8 * 60
LONG_SHIFT_MINUTES = 12 * 60
_CARER_BREAK_LINE = re.compile(
    r"carer['’]?s?\s+break|break\s*/\s*rest|\brest period\b",
    re.IGNORECASE,
)


def requires_carer_break(duration_minutes: int) -> bool:
    return duration_minutes >= BREAK_THRESHOLD_MINUTES


def strip_carer_breaks(notes: str) -> str:
    """Remove carer break lines. Care activities on the other lines stay."""
    kept = []
    for line in str(notes or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _CARER_BREAK_LINE.search(line):
            continue
        if line.strip():
            kept.append(line.strip())
    return "\n".join(kept)


def _apply_break_rule(payload: Dict[str, Any], duration_minutes: int) -> Dict[str, Any]:
    """Visits under 8 hours keep the AI care notes and drop carer breaks."""
    if requires_carer_break(duration_minutes):
        return payload
    notes = payload.get("additional_notes", "")
    payload["additional_notes"] = strip_carer_breaks(notes)
    return payload


async def call_ai_model(
    su_name: str,
    preferred_name: Optional[str],
    carer_name: str,
    date_str: str,
    time_in: str,
    time_out: str,
    care_plan: str,
    clinical_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Python implementation of legacy PHP callAiModel.
    Calculates duration, midpoint, break allocation instructions,
    Care Center / Office work detection, and GDPR PII sanitization.
    Queries Gemini / OpenAI APIs or generates structured JSON conforming to the prompt schema.
    """
    clean_in = time_in.strip()
    clean_out = time_out.strip()

    try:
        dt_base = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        dt_base = datetime.today()

    def parse_time_str(t_str: str) -> datetime:
        parts = t_str.split(":")
        hh = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 8
        mm = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return dt_base.replace(hour=hh, minute=mm, second=0, microsecond=0)

    t_in_dt = parse_time_str(clean_in)
    t_out_dt = parse_time_str(clean_out)

    if t_out_dt <= t_in_dt:
        t_out_dt += timedelta(days=1)

    duration_minutes = int((t_out_dt - t_in_dt).total_seconds() / 60.0)
    duration_hours = round(duration_minutes / 60.0, 1)
    midpoint_dt = t_in_dt + timedelta(minutes=duration_minutes / 2.0)

    t_in_formatted = t_in_dt.strftime("%I:%M %p").lower()
    t_out_formatted = t_out_dt.strftime("%I:%M %p").lower()
    midpoint_formatted = midpoint_dt.strftime("%I:%M %p").lower()

    if duration_minutes >= LONG_SHIFT_MINUTES:
        break_instruction = (
            f"- BREAKS FOR 12+ HOUR SHIFTS (MANDATORY): Because the total shift length is {duration_hours} hours (12 hours or more), "
            f"you MUST automatically include a 2-hour break allocation (carer break/rest period) in the 'additional_notes' timetable, split exactly as:\n"
            f"  1. 1 hour of carer break/rest period during the first half of the shift (between {t_in_formatted} and {midpoint_formatted}).\n"
            f"  2. 1 hour of carer break/rest period during the second half of the shift (between {midpoint_formatted} and {t_out_formatted}).\n"
            f"Both breaks must be clearly logged in the 'additional_notes' chronological timeline using standard 12-hour format (e.g. 'HH:MM am/pm - HH:MM am/pm: Carer break/rest period.'). "
            f"These breaks must be placed such that they do not conflict with or delay realistic meal times."
        )
        notes_spec = (
            f"detailed chronological timetable of care activities (at least 6-8 entries with timestamps starting from {t_in_formatted} to {t_out_formatted}) "
            f"detailing actions performed during the entire service, including the mandatory carer break/rest periods. "
            f"Format: 'HH:MM am/pm: Activity description.\\nHH:MM am/pm - HH:MM am/pm: Activity description.'"
        )
    elif duration_minutes >= BREAK_THRESHOLD_MINUTES:
        break_instruction = (
            f"- BREAKS FOR SHIFTS OF 8 HOURS OR MORE (MANDATORY): Because this visit is {duration_hours} hours (8 hours or more), "
            f"you MUST include a carer break/rest period of at least 2 hours in 'additional_notes'. "
            f"You can split this break (for example into two 1-hour breaks) at logical times that do not block primary care tasks or realistic meal times. "
            f"Log each break as 'HH:MM am/pm - HH:MM am/pm: Carer break/rest period.'"
        )
        notes_spec = (
            f"detailed chronological timetable of care activities (at least 6-8 entries with timestamps starting from {t_in_formatted} to {t_out_formatted}) "
            f"detailing actions performed during the entire service, including the carer break/rest period required for a visit of 8 hours or more. "
            f"Format: 'HH:MM am/pm: Activity description.\\nHH:MM am/pm - HH:MM am/pm: Activity description.'"
        )
    else:
        break_instruction = (
            f"- NO CARER BREAK: This visit is {duration_hours} hours, which is under 8 hours. "
            f"Do NOT include a carer break, a rest period, or a break/rest period anywhere in 'additional_notes'. "
            f"Log only the care provided between {t_in_formatted} and {t_out_formatted}."
        )
        notes_spec = (
            f"detailed chronological timetable of the care provided (timestamps starting from {t_in_formatted} to {t_out_formatted}). "
            f"Do NOT include a carer break or rest period. "
            f"Format: 'HH:MM am/pm: Activity description.\\nHH:MM am/pm - HH:MM am/pm: Activity description.'"
        )

    su_display_name = su_name.strip() if su_name and su_name.strip() else "Service User"
    name_text = f"{su_display_name} {preferred_name or ''}".strip()

    is_care_center = bool(re.search(
        r'\b(care\s*cent(?:er|re)|day\s*cent(?:er|re)|day\s*care|headquarters|\bHQ\b|branch\s*office|office\s*staff|staff\s*facility|office\s*location|\boffice\b|\bcentre\b|\bcenter\b)\b',
        name_text,
        re.IGNORECASE
    ))

    if is_care_center:
        context_instruction = (
            f"- CARE CENTER / OFFICE WORK ENVIRONMENT INSTRUCTION: Service User '{su_display_name}' represents a Care Center, Day Center, or Office facility "
            f"where employees/staff perform office work, administrative tasks, center activity coordination, and facility management rather than an individual receiving home personal care. "
            f"All care notes and logged activities in 'additional_notes' MUST align strictly with office, center, and administrative work "
            f"(e.g., checking shift logs, office administration, receiving visitors/clients, filing documents, coordinating shift handovers, restocking supplies, staff meetings, maintaining office environment). "
            f"Do NOT log personal home care tasks (such as home bed washing, home bathing, or private bedroom assistance). In 'care_tasks.personal_care', set all boolean flags "
            f"(bath_shower, bed_wash, dressing, grooming, oral_wash) to false and set 'assistance_toileting' to 'No'.\n"
            f"- Example line format in additional_notes: \"{t_in_formatted}: Arrived at {su_display_name} office/center, signed in, and commenced office/administrative duties.\""
        )
    else:
        context_instruction = (
            f"- INDIVIDUAL SERVICE USER HOME CARE INSTRUCTION: Service User '{su_display_name}' is an individual patient receiving person-centered care. "
            f"Log realistic care activities (personal care, meals, mobility, companionship) matching their Care Plan needs.\n"
            f"- Example line format in additional_notes: \"{t_in_formatted}: Arrived at home and greeted {su_display_name}.\""
        )

    # Optional carer observations
    carer_obs_prompt = ""
    if clinical_notes and clinical_notes.strip():
        sanitized_obs = re.sub(r'\b[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}\b', '[POSTCODE]', clinical_notes, flags=re.IGNORECASE)
        sanitized_obs = re.sub(r'\b0\d{9,10}\b', '[PHONE REDACTED]', sanitized_obs)
        sanitized_obs = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL REDACTED]', sanitized_obs)
        carer_obs_prompt = f"\n- OPTIONAL CARER OBSERVATIONS TO INCORPORATE: \"{sanitized_obs.strip()}\""

    prompt = f"""You are an AI assistant helping a care coordinator generate daily care reports for Service User {su_display_name} based on their Care Plan.
Given the Care Plan:
\"\"\"
{care_plan or 'Standard person-centred care plan'}
\"\"\"
Generate a realistic structured care report for Service User {su_display_name} for a visit on {date_str} by Carer {carer_name}.
The actual visit time (TIME IN to TIME OUT) is strictly from {t_in_formatted} to {t_out_formatted}.

CRITICAL INSTRUCTIONS FOR TIMINGS & ACTIVITIES:
- NAME REFERENCE INSTRUCTION: Always refer to the service user by their actual name ({su_display_name}) throughout the notes and activities instead of using generic terms like 'the service user' or 'the client'.
- TIME REFERENCE VALIDATION: Every single timestamp or timed observation anywhere in the entire JSON response (including 'additional_notes', 'skin_marks_record.time_assessed', and 'concerns_incidents_list') MUST directly correspond to and fall strictly between {t_in_formatted} and {t_out_formatted}.
- STRICT TIME NOTATION: You MUST use standard 12-hour time notation with a clear space and am/pm suffix (e.g. '08:00 am', '01:30 pm', '08:00 pm') consistently throughout the entire JSON response. Do NOT use 24-hour times (like 13:00, 15:30) and NEVER append am/pm to 24-hour times (like '13:30 pm' or '15:30 pm').
{context_instruction}{carer_obs_prompt}
- Do NOT mention or use shift range times like 8 AM - 8 PM, 8 PM - 8 AM, or 9 AM - 5 PM anywhere in the notes.
- Do NOT generate any timestamp earlier than {t_in_formatted} or later than {t_out_formatted}.
- CONSISTENCY OF ACTIVITIES WITH TIME OF DAY: Activities logged must be realistic and appropriate for the given time frame, environment, and time of day. Meal times must be realistic when a meal falls inside the visit.
{break_instruction}
The report details must align realistically with the environment, needs, and limitations defined in the Care Plan.

You MUST respond with a JSON object containing the following keys (fill with logical values based on the Care Plan):
{{
  "general_well_being": {{
    "alert_responsive": true,
    "unwell": false,
    "unwell_specify": "",
    "tired_fatigued": false,
    "unable_to_walk": false,
    "other_observations": ""
  }},
  "care_tasks": {{
    "personal_care": {{
      "bath_shower": false,
      "bed_wash": {"false" if is_care_center else "true"},
      "dressing": {"false" if is_care_center else "true"},
      "grooming": {"false" if is_care_center else "true"},
      "oral_wash": {"false" if is_care_center else "true"}
    }},
    "assistance_toileting": "No" if is_care_center else "Yes",
    "medication_assistance": {{
      "taken": true,
      "refused": false,
      "specify": ""
    }},
    "meal_preparation": {{
      "meals_count": 2,
      "food_eaten": "Prepared vegetable soup and toasted bread."
    }},
    "mobility_support": {{
      "walking": true,
      "transfer": true,
      "equipment_specify": ""
    }},
    "companionship": "Supported client with companionship and daily activities.",
    "housekeeping": "Completed light housekeeping and office environment checks." if is_care_center else "Completed light housekeeping, washed dishes, and emptied bins.",
    "other_specify": ""
  }},
  "mood_behaviour": {{
    "happy_engaged": true,
    "sad_withdrawn": false,
    "anxious_agitated": false,
    "confused_forgetful": false,
    "other_specify": ""
  }},
  "health_observations": {{
    "no_concern": true,
    "skin_color_changes": "",
    "bruise": "",
    "cut": "",
    "sore": "",
    "pain_discomfort": false,
    "pain_description": ""
  }},
  "food_nutrition": {{
    "eat_portion": "Eat full meal",
    "appetite_changes": "No appetite changes noted."
  }},
  "water_fluid_intake": {{
    "glasses_count": 6,
    "other_liquids": "Tea (2 cups)"
  }},
  "continence_observation": {{
    "stool_type": 4
  }},
  "urine_observations": {{
    "colour": "Straw yellow",
    "smell": "Normal",
    "did_not_urinate_12h": false
  }},
  "skin_marks_record": {{
    "area_assessed": "Full body check",
    "reason_for_assessment": "Routine daily assessment",
    "cause_identified": "No skin lesions apparent.",
    "support_plan_created": "No",
    "no_lesions_apparent": true,
    "time_assessed": "{t_in_formatted}"
  }},
  "concerns_incidents": "None",
  "concerns_incidents_list": [],
  "pain_assessment": {{
    "location": "No pain reported.",
    "intensity_level": 0
  }},
  "additional_notes": "{notes_spec}"
}}"""

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY1")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-flash-latest']
        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    resp = await client.post(url, headers={"x-goog-api-key": gemini_key}, json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.7
                        }
                    })
                    if resp.status_code == 200:
                        res_data = resp.json()
                        text = res_data['candidates'][0]['content']['parts'][0]['text']
                        decoded = json.loads(text)
                        if isinstance(decoded, dict):
                            logger.info(f"Gemini model {model} care note generated successfully")
                            return _apply_break_rule(decoded, duration_minutes)
                except Exception:
                    logger.warning("Gemini model %s call failed", model)

    if openai_key:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }, json={
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                })
                if resp.status_code == 200:
                    res_data = resp.json()
                    text = res_data['choices'][0]['message']['content']
                    decoded = json.loads(text)
                    if isinstance(decoded, dict):
                        logger.info("OpenAI care note generated successfully")
                        return _apply_break_rule(decoded, duration_minutes)
            except Exception:
                logger.warning("OpenAI call failed")

    # Structured Fallback Generator conforming 100% to Prompt Rules
    logger.info("Generating structured fallback care note adhering to prompt rules")
    
    # Dynamic timestamps relative to shift duration
    t1 = (t_in_dt + timedelta(minutes=int(duration_minutes * 0.15))).strftime("%I:%M %p").lower()
    t2 = (t_in_dt + timedelta(minutes=int(duration_minutes * 0.35))).strftime("%I:%M %p").lower()
    t3 = (t_in_dt + timedelta(minutes=int(duration_minutes * 0.45))).strftime("%I:%M %p").lower()
    t4 = (t_in_dt + timedelta(minutes=int(duration_minutes * 0.70))).strftime("%I:%M %p").lower()
    t5 = (t_in_dt + timedelta(minutes=int(duration_minutes * 0.80))).strftime("%I:%M %p").lower()

    if is_care_center:
        if requires_carer_break(duration_minutes):
            notes_timetable = (
                f"{t_in_formatted}: Arrived at {su_display_name} office/center, signed in, and commenced administrative duties.\n"
                f"{t_in_formatted} - {t1}: Reviewed shift handovers, checked office logbook, and organized center schedule.\n"
                f"{t1} - {t2}: Assisted center visitors, managed documentation, and restocked activity supplies.\n"
                f"{t2} - {t3}: Carer break/rest period.\n"
                f"{t3} - {t4}: Coordinated afternoon office administrative tasks and staff updates.\n"
                f"{t4} - {t5}: Carer break/rest period.\n"
                f"{t5} - {t_out_formatted}: Completed office environment safety check, signed off center logs, and completed shift handover by {carer_name}."
            )
        else:
            notes_timetable = (
                f"{t_in_formatted}: Arrived at {su_display_name} office/center, signed in, and commenced administrative duties.\n"
                f"{t_in_formatted} - {t2}: Reviewed the visit log, managed documentation, and assisted center visitors.\n"
                f"{t2} - {t_out_formatted}: Completed the office tasks for this visit and signed off by {carer_name}."
            )
        pc_dict = {"bath_shower": False, "bed_wash": False, "dressing": False, "grooming": False, "oral_wash": False}
        toileting_val = "No"
        housekeeping_val = "Maintained office environment, disinfected staff workstations, and sanitized common areas."
    elif requires_carer_break(duration_minutes):
        notes_timetable = (
            f"{t_in_formatted}: Arrival for visit. Welcomed by {su_display_name}. Checked general wellbeing.\n"
            f"{t_in_formatted} - {t1}: Assisted {su_display_name} with personal care, hygiene, and dressing. Dignity maintained.\n"
            f"{t1} - {t2}: Prepared meal and encouraged fluid intake.\n"
            f"{t2} - {t3}: Carer break/rest period.\n"
            f"{t3} - {t4}: Completed light housekeeping. Washed dishes, swept floors, and emptied bins.\n"
            f"{t4} - {t5}: Carer break/rest period.\n"
            f"{t5} - {t_out_formatted}: Provided companionship, checked skin integrity, completed safety checks, and departed."
        )
        pc_dict = {"bath_shower": False, "bed_wash": True, "dressing": True, "grooming": True, "oral_wash": True}
        toileting_val = "Yes"
        housekeeping_val = "Washed dishes, swept kitchen floors, and emptied bins."
    else:
        notes_timetable = (
            f"{t_in_formatted}: Arrival for visit. Welcomed by {su_display_name}. Checked general wellbeing.\n"
            f"{t_in_formatted} - {t2}: Assisted {su_display_name} with the care tasks due during this visit. Dignity maintained.\n"
            f"{t2} - {t_out_formatted}: Completed the visit, checked comfort and safety, and departed."
        )
        pc_dict = {"bath_shower": False, "bed_wash": True, "dressing": True, "grooming": True, "oral_wash": True}
        toileting_val = "Yes"
        housekeeping_val = "Washed dishes, swept kitchen floors, and emptied bins."

    return {
        "general_well_being": {
            "alert_responsive": True,
            "unwell": False,
            "unwell_specify": "",
            "tired_fatigued": False,
            "unable_to_walk": False,
            "other_observations": ""
        },
        "care_tasks": {
            "personal_care": pc_dict,
            "assistance_toileting": toileting_val,
            "medication_assistance": {
                "taken": True,
                "refused": False,
                "specify": ""
            },
            "meal_preparation": {
                "meals_count": 2,
                "food_eaten": "Cooked vegetable soup and toasted bread."
            },
            "mobility_support": {
                "walking": True,
                "transfer": True,
                "equipment_specify": ""
            },
            "companionship": f"Supported {su_display_name} with daily living tasks and companionship.",
            "housekeeping": housekeeping_val,
            "other_specify": ""
        },
        "mood_behaviour": {
            "happy_engaged": True,
            "sad_withdrawn": False,
            "anxious_agitated": False,
            "confused_forgetful": False,
            "other_specify": ""
        },
        "health_observations": {
            "no_concern": True,
            "skin_color_changes": "",
            "bruise": "",
            "cut": "",
            "sore": "",
            "pain_discomfort": False,
            "pain_description": ""
        },
        "food_nutrition": {
            "eat_portion": "Eat full meal",
            "appetite_changes": "No appetite changes noted."
        },
        "water_fluid_intake": {
            "glasses_count": 6,
            "other_liquids": "Tea (2 cups)"
        },
        "continence_observation": {
            "stool_type": 4
        },
        "urine_observations": {
            "colour": "Straw yellow",
            "smell": "Normal",
            "did_not_urinate_12h": False
        },
        "skin_marks_record": {
            "area_assessed": "Full body check",
            "reason_for_assessment": "Routine daily assessment",
            "cause_identified": "No skin lesions apparent.",
            "support_plan_created": "No",
            "no_lesions_apparent": True,
            "time_assessed": t_in_formatted
        },
        "concerns_incidents": "None",
        "concerns_incidents_list": [],
        "pain_assessment": {
            "location": "No pain reported.",
            "intensity_level": 0
        },
        "additional_notes": notes_timetable
    }
