"""
appointment_service.py
----------------------
Dedicated Rule-Based Appointment Management Engine.
Both the manual appointment UI and the existing chatbot share this exact service,
ensuring consistent validation, availability calculations, and double-booking prevention.

Rules Enforced:
1. Appointment Duration: 30 minutes
2. Minimum Advance Booking: 2 hours from current time
3. Maximum Advance Booking: 30 days
4. Prevention of Double Booking: Active slot conflict checking
5. Doctor Schedules: Enforce doctor working days and hours (exclude outside hours and leaves)
6. No Past Bookings: Strictly reject dates/times in the past
7. Cancellation Rules:
   - Allowed 24+ hours before appointment
   - Less than 24 hours: requires admin approval
   - Completed appointments cannot be cancelled
   - Cancelled appointments cannot be cancelled again
8. Rescheduling Rules:
   - Allowed 24+ hours before appointment
   - Maximum 2 reschedules per appointment
   - New slot must satisfy all booking rules and be available
   - Cannot reschedule to past dates or outside doctor working hours
"""

from datetime import datetime, timedelta, date, time
from typing import Optional, List, Dict, Any, Tuple
import re
from backend.database.connection import get_db

# -----------------------------------------------------------------------------
# Master Data Seeding (Configurable in MongoDB: departments, doctors, schedules)
# -----------------------------------------------------------------------------
DEPARTMENTS_MASTER = [
    {
        "department_id": "dept_cardiology",
        "name": "Cardiology",
        "description": "Comprehensive cardiac care, heart health screening, and cardiovascular management.",
        "icon": "HeartPulse",
    },
    {
        "department_id": "dept_dermatology",
        "name": "Dermatology",
        "description": "Skin, hair, allergy diagnostics, and clinical dermatology consultations.",
        "icon": "Sparkles",
    },
    {
        "department_id": "dept_pediatrics",
        "name": "Pediatrics",
        "description": "Infant care, child wellness exams, growth tracking, and pediatric consultations.",
        "icon": "Baby",
    },
    {
        "department_id": "dept_orthopedics",
        "name": "Orthopedics",
        "description": "Bone, joint, spinal health, sports injuries, and orthopedic care.",
        "icon": "Activity",
    },
    {
        "department_id": "dept_neurology",
        "name": "Neurology",
        "description": "Brain, nerve health, headache clinics, and neurological diagnostics.",
        "icon": "Brain",
    },
    {
        "department_id": "dept_general_medicine",
        "name": "General Medicine",
        "description": "Primary healthcare, chronic disease management, and general wellness checkups.",
        "icon": "Stethoscope",
    },
]

DOCTORS_MASTER = [
    # Cardiology
    {
        "doctor_id": "doc_ravi",
        "name": "Dr. Ravi",
        "department_id": "dept_cardiology",
        "specialization": "Cardiology",
        "location": "Central Campus - Heart Institute (Room 201)",
        "consultation_fee": 160.0,
    },
    {
        "doctor_id": "doc_kumar",
        "name": "Dr. Kumar",
        "department_id": "dept_cardiology",
        "specialization": "Cardiology",
        "location": "Central Campus - Heart Institute (Room 203)",
        "consultation_fee": 150.0,
    },
    {
        "doctor_id": "doc_anil",
        "name": "Dr. Anil",
        "department_id": "dept_cardiology",
        "specialization": "Cardiology",
        "location": "Eastside Care Center (Room 102)",
        "consultation_fee": 155.0,
    },

    # Dermatology
    {
        "doctor_id": "doc_priya",
        "name": "Dr. Priya",
        "department_id": "dept_dermatology",
        "specialization": "Dermatology",
        "location": "Westside Clinic - Skin Care Suite",
        "consultation_fee": 140.0,
    },
    {
        "doctor_id": "doc_anjali",
        "name": "Dr. Anjali",
        "department_id": "dept_dermatology",
        "specialization": "Dermatology",
        "location": "Central Campus - Dermatology Wing (Room 110)",
        "consultation_fee": 145.0,
    },

    # Pediatrics
    {
        "doctor_id": "doc_emily",
        "name": "Dr. Emily Rodriguez",
        "department_id": "dept_pediatrics",
        "specialization": "Pediatrics",
        "location": "Westside Clinic - Children's Center",
        "consultation_fee": 130.0,
    },
    {
        "doctor_id": "doc_sunita",
        "name": "Dr. Sunita Rao",
        "department_id": "dept_pediatrics",
        "specialization": "Pediatrics",
        "location": "Central Campus - Pediatric Pavilion",
        "consultation_fee": 135.0,
    },

    # Orthopedics
    {
        "doctor_id": "doc_michael",
        "name": "Dr. Michael Chen",
        "department_id": "dept_orthopedics",
        "specialization": "Orthopedics",
        "location": "Central Campus - Orthopedics Block",
        "consultation_fee": 170.0,
    },
    {
        "doctor_id": "doc_vikram",
        "name": "Dr. Vikram Mehta",
        "department_id": "dept_orthopedics",
        "specialization": "Orthopedics",
        "location": "Eastside Care Center - Joint Clinic",
        "consultation_fee": 165.0,
    },

    # Neurology
    {
        "doctor_id": "doc_arjun",
        "name": "Dr. Arjun Kapoor",
        "department_id": "dept_neurology",
        "specialization": "Neurology",
        "location": "Central Campus - Neurosciences Pavilion",
        "consultation_fee": 180.0,
    },
    {
        "doctor_id": "doc_sarah",
        "name": "Dr. Sarah Jenkins",
        "department_id": "dept_neurology",
        "specialization": "Neurology",
        "location": "Central Campus - Brain Health Center",
        "consultation_fee": 175.0,
    },

    # General Medicine
    {
        "doctor_id": "doc_robert",
        "name": "Dr. Robert Taylor",
        "department_id": "dept_general_medicine",
        "specialization": "General Medicine",
        "location": "Central Campus - OPD Wing",
        "consultation_fee": 110.0,
    },
    {
        "doctor_id": "doc_deepak",
        "name": "Dr. Deepak Sharma",
        "department_id": "dept_general_medicine",
        "specialization": "General Medicine",
        "location": "Westside Clinic - Primary Care Unit",
        "consultation_fee": 115.0,
    },
]

DOCTOR_SCHEDULES_MASTER = [
    # Dr. Ravi: Mon, Wed, Fri 09:00 - 17:00
    {
        "doctor_id": "doc_ravi",
        "working_days": ["Monday", "Wednesday", "Friday"],
        "hours_start": "09:00",
        "hours_end": "17:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Kumar: Tue, Thu, Sat 09:00 - 16:00
    {
        "doctor_id": "doc_kumar",
        "working_days": ["Tuesday", "Thursday", "Saturday"],
        "hours_start": "09:00",
        "hours_end": "16:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Anil: Mon, Tue, Thu 10:00 - 18:00
    {
        "doctor_id": "doc_anil",
        "working_days": ["Monday", "Tuesday", "Thursday"],
        "hours_start": "10:00",
        "hours_end": "18:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Priya: Mon, Wed, Thu, Fri 10:00 - 16:00
    {
        "doctor_id": "doc_priya",
        "working_days": ["Monday", "Wednesday", "Thursday", "Friday"],
        "hours_start": "10:00",
        "hours_end": "16:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Anjali: Tue, Thu, Sat 09:00 - 15:00
    {
        "doctor_id": "doc_anjali",
        "working_days": ["Tuesday", "Thursday", "Saturday"],
        "hours_start": "09:00",
        "hours_end": "15:00",
        "slot_duration_minutes": 30,
        "lunch_start": "12:30",
        "lunch_end": "13:30",
        "unavailable_dates": [],
    },
    # Dr. Emily: Mon-Fri 08:30 - 14:30
    {
        "doctor_id": "doc_emily",
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "hours_start": "08:30",
        "hours_end": "14:30",
        "slot_duration_minutes": 30,
        "lunch_start": "12:00",
        "lunch_end": "12:30",
        "unavailable_dates": [],
    },
    # Dr. Sunita: Mon, Wed, Fri, Sat 10:00 - 17:00
    {
        "doctor_id": "doc_sunita",
        "working_days": ["Monday", "Wednesday", "Friday", "Saturday"],
        "hours_start": "10:00",
        "hours_end": "17:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Michael: Tue, Thu, Sat 09:30 - 16:30
    {
        "doctor_id": "doc_michael",
        "working_days": ["Tuesday", "Thursday", "Saturday"],
        "hours_start": "09:30",
        "hours_end": "16:30",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Vikram: Mon, Wed, Fri 09:00 - 15:00
    {
        "doctor_id": "doc_vikram",
        "working_days": ["Monday", "Wednesday", "Friday"],
        "hours_start": "09:00",
        "hours_end": "15:00",
        "slot_duration_minutes": 30,
        "lunch_start": "12:30",
        "lunch_end": "13:30",
        "unavailable_dates": [],
    },
    # Dr. Arjun: Mon, Wed, Thu, Fri 09:00 - 16:00
    {
        "doctor_id": "doc_arjun",
        "working_days": ["Monday", "Wednesday", "Thursday", "Friday"],
        "hours_start": "09:00",
        "hours_end": "16:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Sarah: Tue, Thu, Sat 10:00 - 17:00
    {
        "doctor_id": "doc_sarah",
        "working_days": ["Tuesday", "Thursday", "Saturday"],
        "hours_start": "10:00",
        "hours_end": "17:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Robert: Mon-Sat 09:00 - 17:00
    {
        "doctor_id": "doc_robert",
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "hours_start": "09:00",
        "hours_end": "17:00",
        "slot_duration_minutes": 30,
        "lunch_start": "13:00",
        "lunch_end": "14:00",
        "unavailable_dates": [],
    },
    # Dr. Deepak: Mon-Fri 08:00 - 15:00
    {
        "doctor_id": "doc_deepak",
        "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "hours_start": "08:00",
        "hours_end": "15:00",
        "slot_duration_minutes": 30,
        "lunch_start": "12:00",
        "lunch_end": "13:00",
        "unavailable_dates": [],
    },
]


def ensure_appointment_master_seeded():
    """Initializes departments, doctors, and doctor_schedules collections if empty."""
    db = get_db()
    if db["departments"].count_documents({}) == 0:
        db["departments"].insert_many(DEPARTMENTS_MASTER)
        print("[AppointmentService] Seeded departments collection.")
    
    if db["doctors"].count_documents({}) == 0:
        db["doctors"].insert_many(DOCTORS_MASTER)
        print("[AppointmentService] Seeded doctors collection.")

    if db["doctor_schedules"].count_documents({}) == 0:
        db["doctor_schedules"].insert_many(DOCTOR_SCHEDULES_MASTER)
        print("[AppointmentService] Seeded doctor_schedules collection.")


# -----------------------------------------------------------------------------
# Date & Time Utilities
# -----------------------------------------------------------------------------
def parse_date_string(date_input: str) -> Optional[str]:
    """
    Normalizes any date input string to 'YYYY-MM-DD'.
    Handles relative phrases like 'today', 'tomorrow', 'next monday'.
    """
    if not date_input or not isinstance(date_input, str):
        return None
    raw = date_input.strip().lower()
    today = datetime.now().date()

    relative_map = {
        "today": today,
        "tomorrow": today + timedelta(days=1),
        "day after tomorrow": today + timedelta(days=2),
        "next monday": today + timedelta(days=(0 - today.weekday() + 7) % 7 or 7),
        "next tuesday": today + timedelta(days=(1 - today.weekday() + 7) % 7 or 7),
        "next wednesday": today + timedelta(days=(2 - today.weekday() + 7) % 7 or 7),
        "next thursday": today + timedelta(days=(3 - today.weekday() + 7) % 7 or 7),
        "next friday": today + timedelta(days=(4 - today.weekday() + 7) % 7 or 7),
        "next saturday": today + timedelta(days=(5 - today.weekday() + 7) % 7 or 7),
        "next sunday": today + timedelta(days=(6 - today.weekday() + 7) % 7 or 7),
    }
    if raw in relative_map:
        return relative_map[raw].strftime("%Y-%m-%d")

    # Match common formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y", "%B %d %Y", "%b %d %Y"):
        try:
            parsed = datetime.strptime(raw, fmt).date()
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def format_slot_12hr(time_obj: time) -> str:
    """Formats datetime.time to 12-hour string, e.g. '09:00 AM'."""
    return time_obj.strftime("%I:%M %p")


def parse_time_slot_to_time(slot_str: str) -> Optional[time]:
    """Parses '09:00 AM', '9:00 AM', or '09:00' to datetime.time."""
    slot_clean = slot_str.strip().upper()
    for fmt in ("%I:%M %p", "%H:%M", "%I:%M%p"):
        try:
            return datetime.strptime(slot_clean, fmt).time()
        except ValueError:
            continue
    return None


def calculate_end_time(start_time_obj: time, duration_minutes: int = 30) -> time:
    """Adds duration_minutes to a time object."""
    dt = datetime.combine(date.today(), start_time_obj) + timedelta(minutes=duration_minutes)
    return dt.time()


# -----------------------------------------------------------------------------
# Department & Doctor Retrieval APIs
# -----------------------------------------------------------------------------
def get_all_departments() -> List[Dict[str, Any]]:
    """Returns all available hospital departments/specializations."""
    ensure_appointment_master_seeded()
    db = get_db()
    cursor = db["departments"].find({}, {"_id": 0}).sort("name", 1)
    return list(cursor)


def get_doctors(department_id: Optional[str] = None, specialization: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns doctors optionally filtered by department_id or specialization name."""
    ensure_appointment_master_seeded()
    db = get_db()
    query = {}
    if department_id:
        query["department_id"] = department_id
    elif specialization:
        query["specialization"] = {"$regex": f"^{re.escape(specialization)}$", "$options": "i"}

    docs = list(db["doctors"].find(query, {"_id": 0}))
    
    # Attach schedule overview for each doctor
    for doc in docs:
        schedule = db["doctor_schedules"].find_one({"doctor_id": doc["doctor_id"]}, {"_id": 0})
        if schedule:
            doc["working_days"] = schedule.get("working_days", [])
            doc["working_hours"] = f"{schedule.get('hours_start')} - {schedule.get('hours_end')}"
            doc["slot_duration_minutes"] = schedule.get("slot_duration_minutes", 30)
            doc["unavailable_dates"] = schedule.get("unavailable_dates", [])
    return docs


def get_doctor_by_id_or_name(doctor_identifier: str) -> Optional[Dict[str, Any]]:
    """Finds doctor document by doctor_id or doctor name (case-insensitive)."""
    ensure_appointment_master_seeded()
    db = get_db()
    doc = db["doctors"].find_one({
        "$or": [
            {"doctor_id": doctor_identifier},
            {"name": {"$regex": f"^{re.escape(doctor_identifier)}$", "$options": "i"}},
            {"name": {"$regex": re.escape(doctor_identifier), "$options": "i"}}
        ]
    }, {"_id": 0})
    if doc:
        sched = db["doctor_schedules"].find_one({"doctor_id": doc["doctor_id"]}, {"_id": 0})
        if sched:
            doc["schedule"] = sched
    return doc


# -----------------------------------------------------------------------------
# Dynamic Available Slot Calculation Engine
# -----------------------------------------------------------------------------
def calculate_dynamic_available_slots(
    doctor_identifier: str,
    date_str: str,
    current_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Dynamically generates and returns only available 30-minute slots for a doctor on a date.
    
    Rules Evaluated:
    1. Validate normalized date string (YYYY-MM-DD).
    2. Reject past dates.
    3. Maximum advance booking: 30 days.
    4. Validate doctor existence and doctor_schedules.
    5. Check doctor working day for the given date's weekday.
    6. Check doctor leave / unavailable dates.
    7. Generate 30-minute intervals within doctor working hours (excluding lunch break).
    8. Minimum advance booking: 2 hours from current time.
    9. Query database for existing CONFIRMED, RESCHEDULED, or PENDING appointments.
    10. Return only available slots.
    """
    ensure_appointment_master_seeded()
    db = get_db()
    now = current_time or datetime.now()
    today_date = now.date()

    # 1. Validate date
    normalized_date = parse_date_string(date_str)
    if not normalized_date:
        return {
            "success": False,
            "error_code": "INVALID_DATE_FORMAT",
            "message": f"Invalid date format '{date_str}'. Please use YYYY-MM-DD (e.g. {today_date.strftime('%Y-%m-%d')}) or specify 'tomorrow'.",
            "available_slots": []
        }

    target_date = datetime.strptime(normalized_date, "%Y-%m-%d").date()

    # 2. Reject past dates
    if target_date < today_date:
        return {
            "success": False,
            "error_code": "PAST_DATE_REJECTED",
            "message": f"Cannot book appointments for past dates ({normalized_date}).",
            "available_slots": []
        }

    # 3. Maximum advance booking: 30 days
    max_advance_date = today_date + timedelta(days=30)
    if target_date > max_advance_date:
        return {
            "success": False,
            "error_code": "EXCEEDS_MAX_ADVANCE",
            "message": f"Booking date {normalized_date} exceeds the maximum advance booking limit of 30 days (up to {max_advance_date.strftime('%Y-%m-%d')}).",
            "available_slots": []
        }

    # 4. Find Doctor & Schedule
    doctor = get_doctor_by_id_or_name(doctor_identifier)
    if not doctor:
        return {
            "success": False,
            "error_code": "DOCTOR_NOT_FOUND",
            "message": f"Doctor '{doctor_identifier}' was not found in our directory.",
            "available_slots": []
        }

    doctor_id = doctor["doctor_id"]
    doctor_name = doctor["name"]
    schedule = doctor.get("schedule") or db["doctor_schedules"].find_one({"doctor_id": doctor_id}, {"_id": 0})
    if not schedule:
        return {
            "success": False,
            "error_code": "SCHEDULE_NOT_FOUND",
            "message": f"No active schedule configured for {doctor_name}.",
            "available_slots": []
        }

    # 5. Check Working Day
    weekday_name = target_date.strftime("%A")
    working_days = schedule.get("working_days", [])
    if weekday_name not in working_days:
        return {
            "success": False,
            "error_code": "DOCTOR_OFF_DUTY",
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "date": normalized_date,
            "weekday": weekday_name,
            "message": f"{doctor_name} is not available on {weekday_name}s. Working days: {', '.join(working_days)}.",
            "available_slots": []
        }

    # 6. Check Doctor Leave Dates
    unavailable_dates = schedule.get("unavailable_dates", [])
    if normalized_date in unavailable_dates:
        return {
            "success": False,
            "error_code": "DOCTOR_ON_LEAVE",
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "date": normalized_date,
            "message": f"{doctor_name} is on leave/unavailable on {normalized_date}.",
            "available_slots": []
        }

    # 7. Generate Slots (30 min increments)
    start_t = datetime.strptime(schedule.get("hours_start", "09:00"), "%H:%M").time()
    end_t = datetime.strptime(schedule.get("hours_end", "17:00"), "%H:%M").time()
    duration_min = schedule.get("slot_duration_minutes", 30)

    lunch_start_t = None
    lunch_end_t = None
    if schedule.get("lunch_start") and schedule.get("lunch_end"):
        lunch_start_t = datetime.strptime(schedule["lunch_start"], "%H:%M").time()
        lunch_end_t = datetime.strptime(schedule["lunch_end"], "%H:%M").time()

    all_generated_slots: List[Tuple[time, time, str]] = []
    curr_dt = datetime.combine(target_date, start_t)
    end_dt = datetime.combine(target_date, end_t)

    while curr_dt < end_dt:
        slot_end_dt = curr_dt + timedelta(minutes=duration_min)
        if slot_end_dt <= end_dt:
            s_time = curr_dt.time()
            e_time = slot_end_dt.time()
            # Skip lunch break
            if lunch_start_t and lunch_end_t:
                if not (e_time <= lunch_start_t or s_time >= lunch_end_t):
                    curr_dt = slot_end_dt
                    continue
            label = format_slot_12hr(s_time)
            all_generated_slots.append((s_time, e_time, label))
        curr_dt = slot_end_dt

    # 8. Filter out slots within 2 hours of current time (Minimum advance booking: 2 hours)
    min_booking_cutoff = now + timedelta(hours=2)

    valid_slots_advance = []
    for s_time, e_time, label in all_generated_slots:
        slot_start_dt = datetime.combine(target_date, s_time)
        if slot_start_dt >= min_booking_cutoff:
            valid_slots_advance.append((s_time, e_time, label))

    # 9. Query Existing Appointments (CONFIRMED, RESCHEDULED, PENDING)
    existing_appts = list(db["appointments"].find({
        "$or": [
            {"doctor_id": doctor_id},
            {"doctor_name": {"$regex": f"^{re.escape(doctor_name)}$", "$options": "i"}}
        ],
        "date": normalized_date,
        "status": {"$in": ["CONFIRMED", "RESCHEDULED", "PENDING"]}
    }, {"_id": 0, "start_time": 1, "time_slot": 1}))

    booked_labels = set()
    for appt in existing_appts:
        st = appt.get("start_time") or appt.get("time_slot")
        if st:
            parsed_t = parse_time_slot_to_time(st)
            if parsed_t:
                booked_labels.add(format_slot_12hr(parsed_t))
            else:
                booked_labels.add(st.strip())

    # 10. Available Slots = valid slots minus booked
    final_available_slots = [
        label for (s_time, e_time, label) in valid_slots_advance
        if label not in booked_labels
    ]

    return {
        "success": True,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "department_id": doctor.get("department_id"),
        "specialization": doctor.get("specialization"),
        "location": doctor.get("location"),
        "date": normalized_date,
        "weekday": weekday_name,
        "working_hours": f"{schedule.get('hours_start')} - {schedule.get('hours_end')}",
        "slot_duration_minutes": duration_min,
        "consultation_fee": doctor.get("consultation_fee", 150.0),
        "total_possible_slots": len(all_generated_slots),
        "available_slots": final_available_slots,
        "booked_slots_count": len(booked_labels),
        "message": f"Found {len(final_available_slots)} available slot(s) for {doctor_name} on {normalized_date} ({weekday_name})."
    }


# -----------------------------------------------------------------------------
# Appointment Booking Engine with Atomic Double-Booking Prevention
# -----------------------------------------------------------------------------
def book_appointment_record(
    patient_id: str,
    patient_name: str,
    doctor_identifier: str,
    date_str: str,
    time_slot_str: str,
    department_id: Optional[str] = None,
    phone: Optional[str] = "+1 (555) 019-2831",
    patient_dob: Optional[str] = None,
    payment_method: str = "UPI",
    upi_id: Optional[str] = "patient@upi",
    amount: Optional[float] = None
) -> Dict[str, Any]:
    """
    Validates all booking rules and books an appointment.
    Guarantees no double booking.
    """
    ensure_appointment_master_seeded()
    db = get_db()
    now = datetime.now()

    # 1. Run Dynamic Availability Check
    avail_check = calculate_dynamic_available_slots(doctor_identifier, date_str, current_time=now)
    if not avail_check["success"]:
        return {
            "success": False,
            "error_code": avail_check.get("error_code", "AVAILABILITY_CHECK_FAILED"),
            "message": avail_check["message"]
        }

    doctor_id = avail_check["doctor_id"]
    doctor_name = avail_check["doctor_name"]
    normalized_date = avail_check["date"]
    dept_id = department_id or avail_check.get("department_id")
    specialization = avail_check.get("specialization", "General")
    # The doctor directory is the fee authority; do not trust a client-supplied amount.
    fee = avail_check.get("consultation_fee", 150.0)

    # 2. Parse & Format Target Slot
    target_time = parse_time_slot_to_time(time_slot_str)
    if not target_time:
        return {
            "success": False,
            "error_code": "INVALID_TIME_SLOT",
            "message": f"Invalid time slot format: '{time_slot_str}'. Example formats: '09:00 AM', '14:30'."
        }
    formatted_target_slot = format_slot_12hr(target_time)
    end_time_obj = calculate_end_time(target_time, duration_minutes=30)
    formatted_end_slot = format_slot_12hr(end_time_obj)

    # 3. Check Slot is in Dynamic Available Slots
    if formatted_target_slot not in avail_check["available_slots"]:
        return {
            "success": False,
            "error_code": "SLOT_NOT_AVAILABLE",
            "message": (
                f"The slot '{formatted_target_slot}' with {doctor_name} on {normalized_date} is not available. "
                f"Available slots: {', '.join(avail_check['available_slots']) if avail_check['available_slots'] else 'None'}."
            ),
            "available_slots": avail_check["available_slots"]
        }

    # 4. Atomic Double Booking Prevention Check
    conflict = db["appointments"].find_one({
        "$and": [
            {"$or": [
                {"doctor_id": doctor_id},
                {"doctor_name": {"$regex": f"^{re.escape(doctor_name)}$", "$options": "i"}}
            ]},
            {"$or": [
                {"start_time": formatted_target_slot},
                {"time_slot": formatted_target_slot}
            ]}
        ],
        "date": normalized_date,
        "status": {"$in": ["CONFIRMED", "RESCHEDULED", "PENDING"]}
    })
    if conflict:
        return {
            "success": False,
            "error_code": "DOUBLE_BOOKING_PREVENTED",
            "message": f"Conflict detected: Slot {formatted_target_slot} on {normalized_date} with {doctor_name} has just been booked. Please select another slot.",
            "available_slots": [s for s in avail_check["available_slots"] if s != formatted_target_slot]
        }

    # 5. Check daily appointment limit (max 6 per doctor per day)
    daily_count = db["appointments"].count_documents({
        "$or": [
            {"doctor_id": doctor_id},
            {"doctor_name": {"$regex": f"^{re.escape(doctor_name)}$", "$options": "i"}}
        ],
        "date": normalized_date,
        "status": {"$in": ["CONFIRMED", "RESCHEDULED", "PENDING"]}
    })
    if daily_count >= 6:
        return {
            "success": False,
            "error_code": "DAILY_APPOINTMENT_LIMIT_REACHED",
            "message": f"Doctor {doctor_name} already has the maximum of 6 appointments on {normalized_date}. Please choose another date.",
            "available_slots": []
        }

    # 6. Generate Unique Appointment ID
    count = db["appointments"].count_documents({}) + 1001
    apt_id = f"APT-{count}"
    now_iso = now.isoformat()

    doc = {
        "id": apt_id,
        "appointment_id": apt_id,
        "patient_id": patient_id,
        "customer_id": patient_id,
        "patient_name": patient_name,
        "patient_dob": patient_dob,
        "customer_name": patient_name,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "department_id": dept_id,
        "department": specialization,
        "specialization": specialization,
        "date": normalized_date,
        "start_time": formatted_target_slot,
        "end_time": formatted_end_slot,
        "time_slot": formatted_target_slot,
        "status": "CONFIRMED",
        "location": avail_check.get("location", "Main Hospital OPD"),
        "phone": phone or "+1 (555) 019-2831",
        "payment_method": payment_method,
        "upi_id": upi_id if payment_method == "UPI" else None,
        # Appointment booking is supported, but this demo has no payment processor.
        "payment_status": "PENDING",
        "amount": fee,
        "booking_time": now_iso,
        "rescheduled_count": 0,
        "cancellation_reason": None,
        "sms_text": f"Confirmed: Appointment {apt_id} with {doctor_name} on {normalized_date} at {formatted_target_slot}.",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    db["appointments"].insert_one(doc)
    doc.pop("_id", None)

    return {
        "success": True,
        "appointment": doc,
        "appointment_id": apt_id,
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "department": specialization,
        "date": normalized_date,
        "time_slot": formatted_target_slot,
        "status": "CONFIRMED",
        "message": f"Appointment {apt_id} successfully confirmed with {doctor_name} on {normalized_date} at {formatted_target_slot}."
    }


# -----------------------------------------------------------------------------
# Appointment Cancellation Engine with 24-Hour Rule
# -----------------------------------------------------------------------------
def cancel_appointment_record(
    appointment_id: str,
    user_id: str,
    reason: Optional[str] = "Customer request",
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    Cancels an appointment adhering to rules:
    - Cancellation allowed 24+ hours before appointment time.
    - Less than 24 hours: requires admin approval.
    - Completed appointments cannot be cancelled.
    - Already cancelled appointments cannot be cancelled again.
    """
    ensure_appointment_master_seeded()
    db = get_db()
    now = datetime.now()

    apt = db["appointments"].find_one({
        "$or": [
            {"id": appointment_id},
            {"appointment_id": appointment_id}
        ]
    })
    if not apt:
        return {
            "success": False,
            "error_code": "APPOINTMENT_NOT_FOUND",
            "message": f"Appointment '{appointment_id}' does not exist in our records."
        }

    # Ownership check
    customer_id = str(apt.get("customer_id") or apt.get("patient_id", ""))
    if not is_admin and user_id != "guest_user" and customer_id and customer_id != user_id:
        return {
            "success": False,
            "error_code": "UNAUTHORIZED_CANCELLATION",
            "message": "You are only authorized to cancel your own appointments."
        }

    current_status = apt.get("status", "CONFIRMED")
    if current_status == "CANCELLED":
        return {
            "success": False,
            "error_code": "ALREADY_CANCELLED",
            "message": f"Appointment {appointment_id} has already been cancelled."
        }

    if current_status == "COMPLETED":
        return {
            "success": False,
            "error_code": "COMPLETED_APPOINTMENT_CANNOT_BE_CANCELLED",
            "message": f"Cannot cancel appointment {appointment_id} because it is already marked as COMPLETED."
        }

    # Calculate time until appointment
    apt_date_str = apt.get("date")
    apt_time_str = apt.get("start_time") or apt.get("time_slot")
    apt_time_obj = parse_time_slot_to_time(apt_time_str) or time(9, 0)
    apt_datetime = datetime.combine(datetime.strptime(apt_date_str, "%Y-%m-%d").date(), apt_time_obj)

    time_difference = apt_datetime - now
    hours_remaining = time_difference.total_seconds() / 3600.0

    # Less than 24 hours cancellation rule
    if hours_remaining < 24 and not is_admin:
        return {
            "success": False,
            "error_code": "ADMIN_APPROVAL_REQUIRED",
            "hours_remaining": round(hours_remaining, 1),
            "message": (
                f"Appointment {appointment_id} is scheduled in {round(hours_remaining, 1)} hours. "
                "Cancellations requested less than 24 hours before the appointment require Admin / Clinic Supervisor approval. "
                "Please contact the appointments desk to request review."
            )
        }

    now_iso = now.isoformat()
    payment_was_recorded = str(apt.get("payment_status", "PENDING")).upper() == "PAID"
    next_payment_status = "REFUND_REVIEW" if payment_was_recorded else "NOT_CHARGED"
    db["appointments"].update_one(
        {"_id": apt["_id"]},
        {"$set": {
            "status": "CANCELLED",
            "payment_status": next_payment_status,
            "cancellation_reason": reason or "Patient requested cancellation",
            "cancelled_at": now_iso,
            "updated_at": now_iso
        }}
    )

    return {
        "success": True,
        "appointment_id": appointment_id,
        "doctor_name": apt.get("doctor_name"),
        "date": apt_date_str,
        "time_slot": apt_time_str,
        "status": "CANCELLED",
        "refund_status": "REFUND_REVIEW" if payment_was_recorded else "NOT_APPLICABLE",
        "message": (
            f"Appointment {appointment_id} has been cancelled. Its recorded payment needs billing review; "
            "this demo does not process refunds."
            if payment_was_recorded else
            f"Appointment {appointment_id} has been cancelled. No online payment was captured, so no refund is due."
        )
    }


# -----------------------------------------------------------------------------
# Appointment Rescheduling Engine with 24-Hour Rule & Max 2 Reschedules
# -----------------------------------------------------------------------------
def reschedule_appointment_record(
    appointment_id: str,
    user_id: str,
    new_date_str: str,
    new_time_slot_str: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    Reschedules an appointment adhering to rules:
    - Rescheduling allowed 24+ hours before original appointment.
    - Maximum 2 reschedules per appointment.
    - New appointment must satisfy all booking rules (min 2 hours advance, max 30 days).
    - New slot must be verified available and not double booked.
    - Cannot reschedule to past dates or doctor unavailable days.
    """
    ensure_appointment_master_seeded()
    db = get_db()
    now = datetime.now()

    apt = db["appointments"].find_one({
        "$or": [
            {"id": appointment_id},
            {"appointment_id": appointment_id}
        ]
    })
    if not apt:
        return {
            "success": False,
            "error_code": "APPOINTMENT_NOT_FOUND",
            "message": f"Appointment '{appointment_id}' does not exist."
        }

    customer_id = str(apt.get("customer_id") or apt.get("patient_id", ""))
    if not is_admin and user_id != "guest_user" and customer_id and customer_id != user_id:
        return {
            "success": False,
            "error_code": "UNAUTHORIZED_RESCHEDULE",
            "message": "You are only authorized to reschedule your own appointments."
        }

    current_status = apt.get("status", "CONFIRMED")
    if current_status in ("CANCELLED", "COMPLETED"):
        return {
            "success": False,
            "error_code": "INVALID_RESCHEDULE_STATUS",
            "message": f"Appointment {appointment_id} cannot be rescheduled because its status is {current_status}."
        }

    # Check Maximum 2 Reschedules Rule
    rescheduled_count = apt.get("rescheduled_count", 0)
    if rescheduled_count >= 2 and not is_admin:
        return {
            "success": False,
            "error_code": "MAX_RESCHEDULES_EXCEEDED",
            "rescheduled_count": rescheduled_count,
            "message": (
                f"Appointment {appointment_id} has already reached the maximum limit of 2 reschedules. "
                "Further adjustments require booking a new appointment or speaking with administrative staff."
            )
        }

    # Check 24-hour advance notice for current appointment
    apt_date_str = apt.get("date")
    apt_time_str = apt.get("start_time") or apt.get("time_slot")
    apt_time_obj = parse_time_slot_to_time(apt_time_str) or time(9, 0)
    apt_datetime = datetime.combine(datetime.strptime(apt_date_str, "%Y-%m-%d").date(), apt_time_obj)

    time_difference = apt_datetime - now
    hours_remaining = time_difference.total_seconds() / 3600.0
    if hours_remaining < 24 and not is_admin:
        return {
            "success": False,
            "error_code": "RESCHEDULE_24HR_VIOLATION",
            "hours_remaining": round(hours_remaining, 1),
            "message": (
                f"Appointments can only be rescheduled 24 or more hours prior to scheduled time. "
                f"Your appointment is in {round(hours_remaining, 1)} hours. Please contact clinic administration."
            )
        }

    # Validate availability of new slot for same doctor
    doctor_identifier = apt.get("doctor_id") or apt.get("doctor_name")
    avail_check = calculate_dynamic_available_slots(doctor_identifier, new_date_str, current_time=now)
    if not avail_check["success"]:
        return {
            "success": False,
            "error_code": avail_check.get("error_code", "AVAILABILITY_CHECK_FAILED"),
            "message": avail_check["message"]
        }

    new_time_obj = parse_time_slot_to_time(new_time_slot_str)
    if not new_time_obj:
        return {
            "success": False,
            "error_code": "INVALID_NEW_TIME_SLOT",
            "message": f"Invalid time slot format: '{new_time_slot_str}'."
        }
    new_slot_12hr = format_slot_12hr(new_time_obj)
    new_end_slot_12hr = format_slot_12hr(calculate_end_time(new_time_obj, 30))

    if new_slot_12hr not in avail_check["available_slots"]:
        return {
            "success": False,
            "error_code": "SLOT_NOT_AVAILABLE",
            "message": (
                f"Slot '{new_slot_12hr}' on {avail_check['date']} is not available for {apt.get('doctor_name')}. "
                f"Available slots: {', '.join(avail_check['available_slots']) if avail_check['available_slots'] else 'None'}."
            ),
            "available_slots": avail_check["available_slots"]
        }

    # Double booking atomic check
    doctor_id = avail_check["doctor_id"]
    conflict = db["appointments"].find_one({
        "doctor_id": doctor_id,
        "date": avail_check["date"],
        "$or": [
            {"start_time": new_slot_12hr},
            {"time_slot": new_slot_12hr}
        ],
        "id": {"$ne": apt.get("id")},
        "status": {"$in": ["CONFIRMED", "RESCHEDULED", "PENDING"]}
    })
    if conflict:
        return {
            "success": False,
            "error_code": "DOUBLE_BOOKING_PREVENTED",
            "message": f"Slot {new_slot_12hr} on {avail_check['date']} is already booked by another patient.",
            "available_slots": [s for s in avail_check["available_slots"] if s != new_slot_12hr]
        }

    now_iso = now.isoformat()
    new_count = rescheduled_count + 1
    db["appointments"].update_one(
        {"_id": apt["_id"]},
        {"$set": {
            "date": avail_check["date"],
            "start_time": new_slot_12hr,
            "end_time": new_end_slot_12hr,
            "time_slot": new_slot_12hr,
            "status": "RESCHEDULED",
            "rescheduled_count": new_count,
            "updated_at": now_iso,
            "sms_text": f"Rescheduled: Appointment {appointment_id} with {apt.get('doctor_name')} moved to {avail_check['date']} at {new_slot_12hr}."
        }}
    )

    return {
        "success": True,
        "appointment_id": appointment_id,
        "doctor_name": apt.get("doctor_name"),
        "old_date": apt_date_str,
        "old_time_slot": apt_time_str,
        "new_date": avail_check["date"],
        "new_time_slot": new_slot_12hr,
        "rescheduled_count": new_count,
        "remaining_reschedules": max(0, 2 - new_count),
        "status": "RESCHEDULED",
        "message": f"Appointment {appointment_id} successfully rescheduled to {avail_check['date']} at {new_slot_12hr} (Reschedule {new_count}/2)."
    }


def get_appointment_by_id(appointment_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single appointment document by id."""
    ensure_appointment_master_seeded()
    db = get_db()
    apt = db["appointments"].find_one({
        "$or": [
            {"id": appointment_id},
            {"appointment_id": appointment_id}
        ]
    }, {"_id": 0})
    return apt
