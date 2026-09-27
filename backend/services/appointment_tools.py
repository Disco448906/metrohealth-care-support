"""
appointment_tools.py
--------------------
Deterministic backend functions for all appointment operations.
These are called by the Gemini function-calling agent (appointment_agent.py).

This module connects directly to appointment_service.py so that:
  - The existing chatbot and manual UI share the exact same rules, slot engine, and database.
  - No scheduling or availability logic is decided by the AI; the backend database determines all slots and states.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from backend.database.connection import get_db
from backend.services import appointment_service


def list_specializations() -> Dict[str, Any]:
    """
    Returns all available doctor specializations at MetroHealth.
    Use this when the user asks what types of doctors/departments are available.
    """
    departments = appointment_service.get_all_departments()
    specs = sorted(list(set(d["name"] for d in departments)))
    return {
        "success": True,
        "specializations": specs,
        "departments": departments,
        "count": len(specs),
        "message": f"MetroHealth offers {len(specs)} specializations: {', '.join(specs)}."
    }


def list_doctors(specialization: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a list of doctors, optionally filtered by specialization.
    Use this when the user asks for doctors in a particular field.
    """
    doctors = appointment_service.get_doctors(specialization=specialization)

    if not doctors:
        return {
            "success": False,
            "doctors": [],
            "message": f"No doctors found for specialization '{specialization}'."
        }

    doctor_list = []
    for d in doctors:
        doctor_list.append({
            "doctor_id": d.get("doctor_id"),
            "name": d["name"],
            "specialization": d["specialization"],
            "location": d["location"],
            "available_days": d.get("working_days", []),
            "hours": d.get("working_hours", "09:00 - 17:00"),
            "consultation_fee": d["consultation_fee"],
        })

    return {
        "success": True,
        "doctors": doctor_list,
        "count": len(doctor_list),
        "message": f"Found {len(doctor_list)} doctor(s)."
    }


def get_doctor_availability(doctor_name: str, date: str) -> Dict[str, Any]:
    """
    Returns dynamically calculated available time slots for a doctor on a date.
    Subtracts booked appointments, respects doctor working hours, and rejects past slots.
    """
    res = appointment_service.calculate_dynamic_available_slots(
        doctor_identifier=doctor_name,
        date_str=date
    )
    if not res["success"]:
        return {
            "success": False,
            "available_slots": [],
            "doctor": doctor_name,
            "date": date,
            "message": res["message"]
        }

    return {
        "success": True,
        "doctor": res["doctor_name"],
        "specialization": res.get("specialization"),
        "location": res.get("location"),
        "date": res["date"],
        "weekday": res.get("weekday"),
        "available_slots": res["available_slots"],
        "consultation_fee": res.get("consultation_fee"),
        "message": res["message"]
    }


def book_appointment(
    user_id: str,
    user_name: str,
    doctor_name: str,
    date: str,
    time_slot: str,
    patient_dob: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Books an appointment for the user with a specific doctor on a date at a time slot.
    Validates all booking rules and prevents double booking.
    """
    res = appointment_service.book_appointment_record(
        patient_id=user_id,
        patient_name=user_name,
        doctor_identifier=doctor_name,
        date_str=date,
        time_slot_str=time_slot,
        patient_dob=patient_dob,
    )
    if not res["success"]:
        return {
            "success": False,
            "message": res["message"]
        }

    apt = res.get("appointment", {})
    return {
        "success": True,
        "appointment_id": res["appointment_id"],
        "patient_name": apt.get("patient_name"),
        "patient_dob": apt.get("patient_dob"),
        "doctor": res["doctor_name"],
        "specialization": res.get("department"),
        "date": res["date"],
        "time_slot": res["time_slot"],
        "location": apt.get("location", "Central Campus"),
        "consultation_fee": apt.get("amount", 150.0),
        "status": "CONFIRMED",
        "message": res["message"]
    }


def cancel_appointment_by_id(appointment_id: str, user_id: str) -> Dict[str, Any]:
    """
    Cancels an existing appointment by its ID.
    Enforces the 24-hour advance cancellation rule and requires admin approval if less than 24h.
    """
    res = appointment_service.cancel_appointment_record(
        appointment_id=appointment_id,
        user_id=user_id,
        reason="Patient requested cancellation via AI assistant"
    )
    return res


def reschedule_appointment_by_id(
    appointment_id: str,
    user_id: str,
    new_date: str,
    new_time_slot: str
) -> Dict[str, Any]:
    """
    Reschedules an existing appointment to a new date and time slot.
    Enforces the 24-hour rule, maximum 2 reschedules rule, and slot availability check.
    """
    res = appointment_service.reschedule_appointment_record(
        appointment_id=appointment_id,
        user_id=user_id,
        new_date_str=new_date,
        new_time_slot_str=new_time_slot
    )
    return res


def get_user_appointments(user_id: str) -> Dict[str, Any]:
    """
    Returns all appointments for the current user.
    Use this when the user asks to see their appointments, bookings, or schedule.
    """
    appointment_service.ensure_appointment_master_seeded()
    db = get_db()

    query = {}
    if user_id and user_id != "guest_user":
        query = {"$or": [{"customer_id": user_id}, {"patient_id": user_id}]}

    cursor = db["appointments"].find(query, {"_id": 0}).sort("date", -1)
    appointments = []
    for a in cursor:
        appointments.append({
            "appointment_id": a.get("id") or a.get("appointment_id"),
            "doctor": a.get("doctor_name"),
            "specialization": a.get("department") or a.get("specialization"),
            "date": a.get("date"),
            "time_slot": a.get("time_slot") or a.get("start_time"),
            "location": a.get("location"),
            "status": a.get("status"),
        })

    if not appointments:
        return {
            "success": True,
            "appointments": [],
            "message": "You have no appointments on record."
        }

    return {
        "success": True,
        "appointments": appointments,
        "count": len(appointments),
        "message": f"Found {len(appointments)} appointment(s) for you."
    }


def suggest_alternatives(doctor_name: str, date: str) -> Dict[str, Any]:
    """
    Suggests alternative doctors of the same specialization with available slots,
    or alternative available dates for the same doctor.
    Use this when a doctor is unavailable or fully booked on a requested date.
    """
    appointment_service.ensure_appointment_master_seeded()
    db = get_db()

    doctor = appointment_service.get_doctor_by_id_or_name(doctor_name)
    if not doctor:
        return {"success": False, "message": f"Doctor '{doctor_name}' not found."}

    norm_date = appointment_service.parse_date_string(date) or datetime.now().date().strftime("%Y-%m-%d")
    start_date = datetime.strptime(norm_date, "%Y-%m-%d").date()

    # 1. Next 3 available dates for the same doctor
    same_doctor_dates = []
    check_date = start_date + timedelta(days=1)
    attempts = 0
    while len(same_doctor_dates) < 3 and attempts < 30:
        avail = appointment_service.calculate_dynamic_available_slots(doctor["name"], check_date.strftime("%Y-%m-%d"))
        if avail["success"] and avail["available_slots"]:
            same_doctor_dates.append({
                "date": check_date.strftime("%Y-%m-%d"),
                "weekday": check_date.strftime("%A"),
                "available_slots": avail["available_slots"][:3],
            })
        check_date += timedelta(days=1)
        attempts += 1

    # 2. Other doctors of same department on the requested date
    alt_doctors = appointment_service.get_doctors(department_id=doctor.get("department_id"))
    alt_doctor_options = []
    for alt in alt_doctors:
        if alt["name"] != doctor["name"]:
            avail = appointment_service.calculate_dynamic_available_slots(alt["name"], norm_date)
            if avail["success"] and avail["available_slots"]:
                alt_doctor_options.append({
                    "doctor": alt["name"],
                    "location": alt["location"],
                    "date": norm_date,
                    "available_slots": avail["available_slots"][:3],
                })

    return {
        "success": True,
        "original_doctor": doctor["name"],
        "specialization": doctor["specialization"],
        "alternative_dates_same_doctor": same_doctor_dates,
        "alternative_doctors_same_specialization": alt_doctor_options,
        "message": (
            f"Here are alternatives for {doctor['name']} — "
            f"{len(same_doctor_dates)} upcoming date(s) and "
            f"{len(alt_doctor_options)} other {doctor['specialization']} doctor(s) available."
        )
    }
