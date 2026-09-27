"""
appointment_agent.py
--------------------
Gemini Function Calling agent for appointment management.

Flow:
  1. User sends a natural-language appointment request.
  2. We send it to Gemini with tool declarations for all appointment functions.
  3. Gemini returns a functionCall → we execute the matching Python function
     from appointment_tools.py.
  4. We send the function result back to Gemini as a functionResponse.
  5. Gemini generates the final natural-language reply.

RAG is NOT used here. This pipeline is completely separate and only activated
for appointment-related intents. All other intents still use the existing RAG path.
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from backend.services.appointment_tools import (
    list_specializations,
    list_doctors,
    get_doctor_availability,
    book_appointment,
    cancel_appointment_by_id,
    reschedule_appointment_by_id,
    get_user_appointments,
    suggest_alternatives,
)
from backend.services import appointment_service

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini Function Declarations (JSON Schema format)
# ---------------------------------------------------------------------------
APPOINTMENT_TOOLS = [
    {
        "name": "list_specializations",
        "description": (
            "Returns all available medical specializations at MetroHealth. "
            "Call this when the user asks what types of doctors or departments are available, "
            "or when you need to know what specializations exist before suggesting doctors."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_doctors",
        "description": (
            "Returns a list of doctors at MetroHealth, optionally filtered by specialization. "
            "Call this when the user asks for doctors in a specific field, "
            "or to show all available doctors."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "specialization": {
                    "type": "string",
                    "description": "Optional medical specialization to filter by (e.g., 'Cardiology', 'Orthopedics')."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_doctor_availability",
        "description": (
            "Returns available time slots for a specific doctor on a given date. "
            "Call this before booking to check if a doctor has open slots, "
            "or when the user asks about a doctor's availability on a specific date."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {
                    "type": "string",
                    "description": "Full or partial name of the doctor (e.g., 'Dr. Sarah Jenkins' or 'Sarah Jenkins')."
                },
                "date": {
                    "type": "string",
                    "description": "Date to check availability for. Can be 'tomorrow', 'next Monday', or YYYY-MM-DD format."
                }
            },
            "required": ["doctor_name", "date"]
        }
    },
    {
        "name": "book_appointment",
        "description": (
            "Books a new appointment for the user with a doctor at a specific date and time slot. "
            "Requires doctor_name, date, and time_slot. "
            "Always call get_doctor_availability first to confirm the slot is free, "
            "unless the user has explicitly specified all three and you are confident the slot is available."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {
                    "type": "string",
                    "description": "Full name of the doctor to book with."
                },
                "date": {
                    "type": "string",
                    "description": "Date for the appointment (YYYY-MM-DD or natural language like 'tomorrow')."
                },
                "time_slot": {
                    "type": "string",
                    "description": "Time slot for the appointment exactly as returned by get_doctor_availability (e.g., '9:00 AM', '10:30 AM')."
                }
            },
            "required": ["doctor_name", "date", "time_slot"]
        }
    },
    {
        "name": "cancel_appointment_by_id",
        "description": (
            "Cancels an existing appointment using its appointment ID. "
            "Use this when the user says they want to cancel an appointment and provides an ID like APT-1001. "
            "If the user does not provide an ID, first call get_user_appointments to show their appointments "
            "and ask which one to cancel."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to cancel (e.g., 'APT-1001')."
                }
            },
            "required": ["appointment_id"]
        }
    },
    {
        "name": "reschedule_appointment_by_id",
        "description": (
            "Reschedules an existing appointment to a new date and time slot. "
            "Use this when the user wants to change the date or time of an existing appointment. "
            "If the user does not provide an appointment ID, call get_user_appointments first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to reschedule (e.g., 'APT-1001')."
                },
                "new_date": {
                    "type": "string",
                    "description": "The new date for the appointment (YYYY-MM-DD or natural language)."
                },
                "new_time_slot": {
                    "type": "string",
                    "description": "The new time slot (e.g., '9:00 AM')."
                }
            },
            "required": ["appointment_id", "new_date", "new_time_slot"]
        }
    },
    {
        "name": "get_user_appointments",
        "description": (
            "Returns all appointments for the current user. "
            "Call this when the user asks to see their appointments, bookings, or schedule. "
            "Also call this when the user wants to cancel or reschedule but hasn't provided an appointment ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "suggest_alternatives",
        "description": (
            "Suggests alternative doctors of the same specialization or alternative available dates "
            "when a doctor is unavailable or fully booked on a requested date. "
            "Call this when get_doctor_availability returns no available slots."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {
                    "type": "string",
                    "description": "Name of the originally requested doctor."
                },
                "date": {
                    "type": "string",
                    "description": "The originally requested date."
                }
            },
            "required": ["doctor_name", "date"]
        }
    }
]


# ---------------------------------------------------------------------------
# System prompt for appointment agent
# ---------------------------------------------------------------------------
APPOINTMENT_SYSTEM_PROMPT = """You are MetroHealth AI Care Assistant — a warm, professional, and empathetic healthcare assistant specializing in appointment management.

You have access to real-time appointment tools that let you:
- List medical specializations and doctors
- Check a doctor's available time slots for any date
- Book, cancel, and reschedule appointments
- View a patient's existing appointments
- Suggest alternative doctors or dates when needed

GUIDELINES:
1. Always be conversational and natural — speak like a caring healthcare receptionist, not a robot.
2. If the user's request is missing required information (doctor name, date, or time slot), politely ask for only the missing piece — do not ask for everything at once.
3. Before booking, always verify slot availability using get_doctor_availability.
4. If a slot is unavailable, immediately call suggest_alternatives and present the options warmly.
5. When showing appointments, format them clearly with dates, times, and statuses.
6. Confirm all actions (booking, cancellation, reschedule) clearly with the appointment ID.
7. Use bold text for appointment IDs, doctor names, dates, and times for easy reading.
8. Never fabricate doctor names, slots, or availability — only use data from the tools.
"""

# ---------------------------------------------------------------------------
# Tool dispatcher — maps function name to Python callable
# ---------------------------------------------------------------------------
def _dispatch_tool(function_name: str, function_args: dict, user_id: str, user_name: str) -> Any:
    """Execute the tool function and return its result."""
    if function_name == "list_specializations":
        return list_specializations()

    elif function_name == "list_doctors":
        return list_doctors(
            specialization=function_args.get("specialization")
        )

    elif function_name == "get_doctor_availability":
        return get_doctor_availability(
            doctor_name=function_args.get("doctor_name", ""),
            date=function_args.get("date", "")
        )

    elif function_name == "book_appointment":
        return book_appointment(
            user_id=user_id,
            user_name=user_name,
            doctor_name=function_args.get("doctor_name", ""),
            date=function_args.get("date", ""),
            time_slot=function_args.get("time_slot", "")
        )

    elif function_name == "cancel_appointment_by_id":
        return cancel_appointment_by_id(
            appointment_id=function_args.get("appointment_id", ""),
            user_id=user_id
        )

    elif function_name == "reschedule_appointment_by_id":
        return reschedule_appointment_by_id(
            appointment_id=function_args.get("appointment_id", ""),
            user_id=user_id,
            new_date=function_args.get("new_date", ""),
            new_time_slot=function_args.get("new_time_slot", "")
        )

    elif function_name == "get_user_appointments":
        return get_user_appointments(user_id=user_id)

    elif function_name == "suggest_alternatives":
        return suggest_alternatives(
            doctor_name=function_args.get("doctor_name", ""),
            date=function_args.get("date", "")
        )

    else:
        return {"success": False, "message": f"Unknown function: {function_name}"}


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------
def handle_appointment_query(
    message: str,
    user_id: str = "guest_user",
    user_name: str = "Valued Patient",
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Handles appointment-related queries using Gemini Function Calling.

    Returns the final natural-language response string.
    Falls back to a helpful static message if Gemini API is unavailable.
    """
    lowered = message.lower()
    if any(term in lowered for term in ("reschedule", "move my appointment", "change my appointment")):
        return (
            "I haven't changed your schedule yet. Open **Patient Care Hub → Appointments**, choose **Reschedule**, "
            "then select a date and an available time. The page checks your visit's reschedule rules before saving."
        )
    if any(term in lowered for term in ("cancel appointment", "cancel my visit", "cancel my appointment")):
        return (
            "I haven't cancelled anything yet. Open **Patient Care Hub → Appointments** and choose **Cancel** on the visit. "
            "This demo does not process online payments or refunds."
        )

    # Keep discovery and booking deterministic. The LLM sometimes replies in
    # plain text instead of calling its availability tools, leaving patients
    # without the doctor/slot choices they need to continue.
    booking_response = _handle_booking_flow(
        message=message,
        user_id=user_id,
        user_name=user_name,
        conversation_history=conversation_history or [],
    )
    if booking_response is not None:
        return booking_response

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    if not gemini_key or gemini_key.startswith("YOUR_"):
        return _fallback_response(message, user_id)

    # Build Gemini contents array from conversation history
    contents = []
    if conversation_history:
        for turn in conversation_history[-6:]:
            role = "user" if turn.get("role") == "user" else "model"
            content = turn.get("content", "").strip()
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})

    # Add current user message
    contents.append({"role": "user", "parts": [{"text": message}]})

    # Gemini request payload with function declarations
    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": APPOINTMENT_SYSTEM_PROMPT}]
        },
        "tools": [
            {
                "function_declarations": APPOINTMENT_TOOLS
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1000,
        }
    }

    # Try Gemini models in order
    for model in ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={gemini_key}"
        )
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25
            )

            if resp.status_code != 200:
                print(f"[AppointmentAgent] Gemini {model} error {resp.status_code}: {resp.text[:300]}")
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                continue

            candidate = candidates[0]
            content_parts = candidate.get("content", {}).get("parts", [])
            finish_reason = candidate.get("finishReason", "")

            # ---------------------------------------------------------------
            # Check if Gemini wants to call a function
            # ---------------------------------------------------------------
            function_call_part = None
            for part in content_parts:
                if "functionCall" in part:
                    function_call_part = part["functionCall"]
                    break

            if function_call_part:
                function_name = function_call_part.get("name", "")
                function_args = function_call_part.get("args", {})

                print(f"[AppointmentAgent] Gemini calling function: {function_name}({function_args})")

                # Execute the tool
                tool_result = _dispatch_tool(function_name, function_args, user_id, user_name)
                print(f"[AppointmentAgent] Tool result: {json.dumps(tool_result, default=str)[:300]}")

                # Send function result back to Gemini for final response
                contents_with_result = contents + [
                    # Model's function call turn
                    {
                        "role": "model",
                        "parts": [{"functionCall": {"name": function_name, "args": function_args}}]
                    },
                    # Tool result turn
                    {
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": function_name,
                                "response": {"content": tool_result}
                            }
                        }]
                    }
                ]

                follow_up_payload = {
                    "contents": contents_with_result,
                    "systemInstruction": {
                        "parts": [{"text": APPOINTMENT_SYSTEM_PROMPT}]
                    },
                    "tools": [{"function_declarations": APPOINTMENT_TOOLS}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1000,
                    }
                }

                follow_resp = requests.post(
                    url,
                    json=follow_up_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=25
                )

                if follow_resp.status_code == 200:
                    follow_data = follow_resp.json()
                    follow_candidates = follow_data.get("candidates", [])
                    if follow_candidates:
                        follow_parts = follow_candidates[0].get("content", {}).get("parts", [])
                        for p in follow_parts:
                            if "text" in p and p["text"].strip():
                                print(f"[AppointmentAgent] Final response from {model}: {len(p['text'])} chars")
                                return p["text"].strip()

                # If follow-up failed, synthesize from tool result directly
                return _synthesize_from_tool_result(function_name, tool_result)

            # ---------------------------------------------------------------
            # Gemini returned a plain text response (e.g., asking for info)
            # ---------------------------------------------------------------
            for part in content_parts:
                if "text" in part and part["text"].strip():
                    print(f"[AppointmentAgent] Plain response from {model}: {len(part['text'])} chars")
                    return part["text"].strip()

        except requests.exceptions.Timeout:
            print(f"[AppointmentAgent] Gemini {model} timeout.")
            continue
        except Exception as e:
            print(f"[AppointmentAgent] Gemini {model} exception: {e}")
            continue

    # All models failed — use fallback
    return _fallback_response(message, user_id)


def _handle_booking_flow(
    message: str,
    user_id: str,
    user_name: str,
    conversation_history: List[Dict[str, str]],
) -> Optional[str]:
    """Return a deterministic response for doctor discovery and new bookings."""
    user_turns = [
        turn.get("content", "")
        for turn in conversation_history
        if turn.get("role") == "user" and turn.get("content")
    ] + [message]
    full_request = " ".join(user_turns).lower()
    if not any(term in full_request for term in ("book", "appointment", "available doctor", "availability", "doctor")):
        return None
    if any(term in message.lower() for term in ("cancel", "reschedule", "move my appointment")):
        return None
    booking_requested = any(phrase in full_request for phrase in (
        "book", "booking", "schedule an appointment", "schedule appointment",
        "make an appointment", "set up an appointment", "appointment with",
        "want an appointment", "need an appointment",
    ))

    # Use the signed-in account name by default. Name and date of birth are
    # optional booking details and should never block availability lookup or booking.
    patient_name, patient_dob = _extract_patient_details(user_turns, identity_was_requested=False)
    patient_name = patient_name or user_name or "Patient"

    doctors = appointment_service.get_doctors()
    if not doctors:
        return "I can't retrieve the doctor directory right now. Please try again in a moment."

    doctor = next(
        (
            item for item in doctors
            if item["name"].lower() in full_request
            or item["name"].lower().replace("dr. ", "") in full_request
        ),
        None,
    )

    specialization = next(
        (item["specialization"] for item in doctors if item["specialization"].lower() in full_request),
        None,
    )
    if not specialization:
        specialty_aliases = {
            "cardiologist": "Cardiology",
            "dermatologist": "Dermatology",
            "pediatrician": "Pediatrics",
            "orthopedist": "Orthopedics",
            "orthopaedist": "Orthopedics",
            "neurologist": "Neurology",
            "general physician": "General Medicine",
            "general doctor": "General Medicine",
        }
        specialization = next(
            (specialty for alias, specialty in specialty_aliases.items() if alias in full_request),
            None,
        )

    if not doctor:
        matching_doctors = [
            item for item in doctors
            if not specialization or item["specialization"].lower() == specialization.lower()
        ]
        if len(matching_doctors) == 1:
            doctor = matching_doctors[0]
        else:
            title = f"Here are our {specialization} doctors:" if specialization else "Here are our available doctors:"
            options = [
                f"• **{item['name']}** — {item['specialization']} | {item.get('location', 'MetroHealth')} | ${item.get('consultation_fee', 0):.0f}"
                for item in matching_doctors
            ]
            if not options:
                return f"I couldn't find a doctor in {specialization}. Which specialty would you like?"
            return f"{title}\n\n" + "\n".join(options) + "\n\nWhich doctor would you like, and what date should I check?"

    date_value = None
    date_patterns = (
        r"\b(?:today|tomorrow|day after tomorrow|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
        r"\b\d{4}-\d{1,2}-\d{1,2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b",
    )
    import re
    for turn in reversed(user_turns):
        for pattern in date_patterns:
            found = re.search(pattern, turn, re.IGNORECASE)
            if found:
                candidate = found.group(0)
                if _is_patient_dob(candidate, patient_dob):
                    continue
                candidate = candidate.replace(",", "")
                candidate = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", candidate, flags=re.IGNORECASE)
                if len(candidate.split()) == 2 and candidate.split()[-1].isdigit():
                    candidate += f" {appointment_service.datetime.now().year}"
                date_value = appointment_service.parse_date_string(candidate)
                if date_value:
                    break
        if date_value:
            break

    if not date_value:
        return f"I can help book with **{doctor['name']}**. What date would you prefer? You can say a date like October 2, 2026 or 'next Monday'."

    availability = get_doctor_availability(doctor["name"], date_value)
    if not availability.get("success"):
        return availability.get("message", "I couldn't check that date. Please try another date.")

    slots = availability.get("available_slots", [])
    if not slots:
        return f"**{doctor['name']}** has no available appointments on **{date_value}**. Please choose another date."

    requested_time = None
    for turn in reversed(user_turns):
        for slot in slots:
            if slot.lower() in turn.lower():
                requested_time = slot
                break
        if requested_time:
            break
        time_matches = re.finditer(
            r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>a\.?m\.?|p\.?m\.?)?\b",
            turn,
            re.IGNORECASE,
        )
        for time_match in time_matches:
            hour_text = time_match.group("hour")
            minute_text = time_match.group("minute")
            period = time_match.group("period")
            # A colon time such as "11:30" is a valid choice even without AM/PM.
            # Match it against the actual available slots; if AM/PM is ambiguous,
            # leave requested_time unset so the user can clarify.
            if minute_text or period:
                if period:
                    raw_time = f"{hour_text}:{minute_text or '00'} {period.replace('.', '').upper()}"
                    parsed_time = appointment_service.parse_time_slot_to_time(raw_time)
                    candidates = [appointment_service.format_slot_12hr(parsed_time)] if parsed_time else []
                else:
                    hour = int(hour_text)
                    minute = int(minute_text)
                    candidates = []
                    for slot in slots:
                        slot_time = appointment_service.parse_time_slot_to_time(slot)
                        if slot_time and slot_time.minute == minute and (slot_time.hour % 12 or 12) == (hour % 12 or 12):
                            candidates.append(slot)
                matching_slots = [candidate for candidate in candidates if candidate in slots]
                if len(matching_slots) == 1:
                    requested_time = matching_slots[0]
                    break
        if requested_time:
            break

    if not requested_time:
        options = "\n".join(f"• {slot}" for slot in slots)
        return f"**{doctor['name']}** has these available times on **{date_value}**:\n\n{options}\n\nWhich time would you like?"

    if not booking_requested:
        return f"**{requested_time}** is available with **{doctor['name']}** on **{date_value}**. If you'd like me to reserve it, say **Book this appointment**."

    result = book_appointment(
        user_id=user_id,
        user_name=patient_name,
        doctor_name=doctor["name"],
        date=date_value,
        time_slot=requested_time,
        patient_dob=patient_dob,
    )
    return _synthesize_from_tool_result("book_appointment", result)


def _extract_patient_details(user_turns: List[str], identity_was_requested: bool) -> tuple[Optional[str], Optional[str]]:
    """Read the patient name and DOB supplied after the assistant asks for them."""
    import re
    from datetime import datetime, date

    date_pattern = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}-\d{1,2}|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\b"
    name = None
    dob = None

    for turn in reversed(user_turns):
        explicit_name = re.search(
            r"(?:(?:my\s+)?(?:full\s+)?name\s+is|i\s+am|i'm)\s+(.+?)(?=\s*(?:,|;|\bdob\b|\bdate of birth\b|\bborn\b)|$)",
            turn,
            re.IGNORECASE,
        )
        turn_name = explicit_name.group(1).strip(" ,.;") if explicit_name else None

        if not turn_name and identity_was_requested and not re.search(r"\b(?:book|appointment|schedule|doctor)\b|\bdr\.", turn, re.IGNORECASE):
            without_date = re.sub(date_pattern, "", turn, flags=re.IGNORECASE)
            without_date = re.sub(r"\b(?:my\s+)?(?:full\s+)?name\s+is\b|\b(?:i\s+am|i'm)\b", "", without_date, flags=re.IGNORECASE)
            without_date = re.sub(r"\b(?:dob|date of birth|born(?:\s+on)?)\b\s*(?:is|:|-)?", "", without_date, flags=re.IGNORECASE)
            candidate = without_date.strip(" ,.;:-")
            if candidate and re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,78}", candidate):
                turn_name = candidate

        if turn_name and not name:
            name = turn_name

        explicit_dob = re.search(r"(?:dob|date of birth|born(?:\s+on)?)\s*(?:is|:|-)?\s*(" + date_pattern + r")", turn, re.IGNORECASE)
        found_dob = explicit_dob.group(1) if explicit_dob else None
        if not found_dob and identity_was_requested and turn_name and not dob:
            found = re.search(date_pattern, turn, re.IGNORECASE)
            found_dob = found.group(0) if found else None
        if found_dob and not dob:
            raw_dob = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", found_dob.replace(",", ""), flags=re.IGNORECASE)
            formats = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d %Y", "%b %d %Y", "%d/%m/%Y", "%d-%m-%Y")
            for fmt in formats:
                try:
                    parsed_dob = datetime.strptime(raw_dob, fmt).date()
                    if parsed_dob < date.today():
                        dob = parsed_dob.isoformat()
                    break
                except ValueError:
                    continue

        if name and dob:
            break

    return name, dob


def _is_patient_dob(candidate: str, patient_dob: Optional[str]) -> bool:
    """Prevent the patient's birth date from being mistaken for the visit date."""
    if not patient_dob:
        return False
    import re
    from datetime import datetime
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", candidate.replace(",", ""), flags=re.IGNORECASE)
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d %Y", "%b %d %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat() == patient_dob
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------------------
# Fallback: synthesize a readable response from tool result without LLM
# ---------------------------------------------------------------------------
def _synthesize_from_tool_result(function_name: str, result: dict) -> str:
    """Generate a plain-text response from a tool result when Gemini follow-up fails."""
    if not result.get("success"):
        return f"I'm sorry, I encountered an issue: {result.get('message', 'Unknown error')}. Please try again or contact our support desk."

    if function_name == "list_specializations":
        specs = result.get("specializations", [])
        return (
            f"MetroHealth offers the following specializations:\n\n"
            + "\n".join(f"• **{s}**" for s in specs)
            + "\n\nWhich specialty would you like to book with?"
        )

    elif function_name == "list_doctors":
        doctors = result.get("doctors", [])
        lines = [f"Here are our available doctors:\n"]
        for d in doctors:
            lines.append(
                f"• **{d['name']}** — {d['specialization']} | {d['location']}\n"
                f"  Available: {', '.join(d['available_days'])} | {d['hours']} | Fee: ${d['consultation_fee']}"
            )
        lines.append("\nWould you like to book an appointment with any of them?")
        return "\n".join(lines)

    elif function_name == "get_doctor_availability":
        slots = result.get("available_slots", [])
        doctor = result.get("doctor", "")
        date = result.get("date", "")
        return (
            f"**{doctor}** has the following available slots on **{date}**:\n\n"
            + "\n".join(f"• {s}" for s in slots)
            + "\n\nWhich time works for you?"
        )

    elif function_name == "book_appointment":
        return (
            f"✅ Your appointment has been confirmed!\n\n"
            f"• **Appointment ID**: `{result.get('appointment_id')}`\n"
            f"• **Patient**: {result.get('patient_name') or 'Patient'}\n"
            f"• **Doctor**: {result.get('doctor')}\n"
            f"• **Date**: {result.get('date')} ({result.get('weekday')})\n"
            f"• **Time**: {result.get('time_slot')}\n"
            f"• **Location**: {result.get('location')}\n"
            f"• **Fee**: ${result.get('consultation_fee')}\n\n"
            f"Is there anything else I can help you with?"
        )

    elif function_name == "cancel_appointment_by_id":
        refund_message = result.get("message") or "No refund details are available. Please check with the billing team."
        return (
            f"Your appointment has been cancelled.\n\n"
            f"• **Appointment ID**: `{result.get('appointment_id')}`\n"
            f"• **Doctor**: {result.get('doctor')}\n"
            f"• **Date**: {result.get('date')} at {result.get('time_slot')}\n\n"
            f"{refund_message}"
        )

    elif function_name == "reschedule_appointment_by_id":
        return (
            f"Your appointment has been rescheduled.\n\n"
            f"• **Appointment ID**: `{result.get('appointment_id')}`\n"
            f"• **New Date**: {result.get('new_date')} at {result.get('new_time_slot')}\n"
            f"• **Location**: {result.get('location')}\n\n"
            f"Is there anything else I can help you with?"
        )

    elif function_name == "get_user_appointments":
        appts = result.get("appointments", [])
        if not appts:
            return "You have no appointments on record. Would you like to book one?"
        lines = ["Here are your appointments:\n"]
        for a in appts:
            lines.append(
                f"• `{a['appointment_id']}` — **{a['doctor']}** | {a['date']} at {a['time_slot']} | "
                f"{a['location']} | Status: **{a['status']}**"
            )
        return "\n".join(lines)

    elif function_name == "suggest_alternatives":
        lines = [f"Here are some alternatives for **{result.get('original_doctor')}**:\n"]

        alt_dates = result.get("alternative_dates_same_doctor", [])
        if alt_dates:
            lines.append("**Other available dates with the same doctor:**")
            for d in alt_dates:
                lines.append(f"• {d['date']} ({d['weekday']}) — Slots: {', '.join(d['available_slots'])}")

        alt_docs = result.get("alternative_doctors_same_specialization", [])
        if alt_docs:
            lines.append(f"\n**Other {result.get('specialization')} doctors available on the requested date:**")
            for d in alt_docs:
                lines.append(f"• **{d['doctor']}** at {d['location']} — Slots: {', '.join(d['available_slots'])}")

        lines.append("\nWould you like to book with any of these options?")
        return "\n".join(lines)

    return result.get("message", "Done.")


def _fallback_response(message: str, user_id: str) -> str:
    """Static fallback if no Gemini key is available."""
    lowered = message.lower()
    if any(term in lowered for term in ("reschedule", "move my appointment", "change my appointment")):
        return (
            "I can help you find a new time. Open **Patient Care Hub → Appointments**, choose **Reschedule**, "
            "then pick a date and one of the available slots. The page checks availability and applies the "
            "appointment's reschedule rules before saving."
        )
    if any(term in lowered for term in ("cancel appointment", "cancel my visit", "cancel my appointment")):
        return (
            "You can cancel eligible visits in **Patient Care Hub → Appointments**. Open the appointment and "
            "choose **Cancel**. This demo does not process online payments or refunds."
        )
    return (
        "I'd be happy to help you with your appointment! "
        "To get started, could you please let me know:\n\n"
        "• Which **specialization** or **doctor** you'd like to see?\n"
        "• Your preferred **date**?\n\n"
        "Once I have that information, I can check availability and book your appointment right away."
    )
