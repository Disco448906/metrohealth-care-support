from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.schemas.schemas import AppointmentResponse, AppointmentBookRequest, AppointmentRescheduleRequest
from backend.api.auth import get_current_user, get_current_doctor
from backend.database.connection import get_db
from backend.services.sms_service import generate_appointment_sms
from backend.services import appointment_service

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


# -----------------------------------------------------------------------------
# 1. Department & Specialization Catalog
# -----------------------------------------------------------------------------
@router.get("/departments", response_model=List[Dict[str, Any]])
def get_departments():
    """Returns all available hospital departments / specializations."""
    return appointment_service.get_all_departments()


# -----------------------------------------------------------------------------
# 2. Doctors Directory
# -----------------------------------------------------------------------------
@router.get("/doctors", response_model=List[Dict[str, Any]])
def get_doctors(
    department_id: Optional[str] = Query(None, alias="departmentId"),
    dept_id: Optional[str] = Query(None, alias="department_id"),
    specialization: Optional[str] = Query(None)
):
    """
    Returns doctors, optionally filtered by department ID (Cardiology, Dermatology, etc.)
    or specialization name.
    """
    active_dept_id = department_id or dept_id
    doctors = appointment_service.get_doctors(
        department_id=active_dept_id,
        specialization=specialization
    )
    return doctors


# -----------------------------------------------------------------------------
# 3. Dynamic Available Slots Calculation
# -----------------------------------------------------------------------------
@router.get("/available-slots", response_model=Dict[str, Any])
def get_available_slots(
    doctor_id: Optional[str] = Query(None, alias="doctorId"),
    doc_id: Optional[str] = Query(None, alias="doctor_id"),
    doctor_name: Optional[str] = Query(None),
    date: str = Query(..., description="Date in YYYY-MM-DD or relative like 'tomorrow'")
):
    """
    Dynamically generates available 30-minute time slots for a doctor on a given date.
    Excludes booked slots, past times, lunch breaks, and non-working days.
    """
    target_identifier = doctor_id or doc_id or doctor_name
    if not target_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'doctorId' or 'doctor_name' must be provided."
        )

    res = appointment_service.calculate_dynamic_available_slots(
        doctor_identifier=target_identifier,
        date_str=date
    )

    if not res["success"]:
        # Return structured response with error message
        return res

    return res


# -----------------------------------------------------------------------------
# 4. Book Appointment
# -----------------------------------------------------------------------------
@router.post("/book", response_model=Dict[str, Any])
def book_appointment(
    req: AppointmentBookRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Books an appointment verifying all rules:
    - 30-minute duration
    - Minimum 2 hours advance booking
    - Maximum 30 days advance booking
    - No double booking
    - Doctor schedule and working hours compliance
    """
    doctor_identifier = req.doctor_id or req.doctor_name
    if not doctor_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor ID or Doctor name is required."
        )

    user_id = str(current_user.get("id") or current_user.get("_id", "guest_user"))
    user_name = current_user.get("name", "Valued Patient")
    user_phone = req.phone or current_user.get("phone", "+1 (555) 019-2831")

    res = appointment_service.book_appointment_record(
        patient_id=user_id,
        patient_name=user_name,
        doctor_identifier=doctor_identifier,
        date_str=req.date,
        time_slot_str=req.time_slot,
        patient_dob=req.patient_dob,
        department_id=req.department_id,
        phone=user_phone,
        payment_method=req.payment_method,
        upi_id=req.upi_id if req.payment_method == "UPI" else None,
        amount=req.amount
    )

    if not res["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res["message"]
        )

    apt = res.get("appointment", {})

    # Generate SMS confirmation
    try:
        sms_res = generate_appointment_sms(
            action="BOOKED",
            customer_name=user_name,
            phone=user_phone,
            appointment_id=apt.get("id", ""),
            doctor_name=apt.get("doctor_name", ""),
            department=apt.get("department", ""),
            date=apt.get("date", ""),
            time_slot=apt.get("time_slot", ""),
            location=apt.get("location", "Main Campus"),
            payment_method=req.payment_method,
            amount=apt.get("amount", 150.0),
            payment_status=apt.get("payment_status", "PENDING"),
        )
        apt["sms_text"] = sms_res["sms_text"]
        apt["sms_delivery_status"] = sms_res["delivery_status"]
    except Exception as e:
        print(f"[Appointments] SMS generation error: {e}")

    return apt


# -----------------------------------------------------------------------------
# 5. List Appointments
# -----------------------------------------------------------------------------
@router.get("", response_model=List[Dict[str, Any]])
def get_appointments(current_user: dict = Depends(get_current_user)):
    """Returns appointments for current customer or all appointments for admin."""
    appointment_service.ensure_appointment_master_seeded()
    db = get_db()
    if current_user.get("role") == "admin":
        query = {}
    else:
        c_set = {
            str(current_user.get("id", "")),
            str(current_user.get("_id", "")),
            str(current_user.get("email", ""))
        }
        c_ids = [c for c in c_set if c]
        query = {
            "$or": [
                {"customer_id": {"$in": c_ids}},
                {"patient_id": {"$in": c_ids}}
            ]
        }

    cursor = db["appointments"].find(query).sort("date", -1)
    appointments = []
    for a in cursor:
        a["id"] = str(a.get("id") or a.get("appointment_id") or a.get("_id", ""))
        a.pop("_id", None)
        appointments.append(a)
    return appointments


@router.get("/doctor/schedule", response_model=List[Dict[str, Any]])
def get_doctor_schedule(current_doctor: dict = Depends(get_current_doctor)):
    """Return appointment details for the authenticated doctor's own schedule."""
    appointment_service.ensure_appointment_master_seeded()
    db = get_db()
    doctor = appointment_service.get_doctor_by_id_or_name(current_doctor["doctor_id"])
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile was not found.")

    query = {"$or": [
        {"doctor_id": current_doctor["doctor_id"]},
        {"doctor_name": doctor["name"]},
    ]}
    patient_schedule_fields = {
        "_id": 0,
        "id": 1,
        "appointment_id": 1,
        "patient_name": 1,
        "patient_id": 1,
        "customer_id": 1,
        "patient_dob": 1,
        "customer_name": 1,
        "department": 1,
        "specialization": 1,
        "date": 1,
        "time_slot": 1,
        "start_time": 1,
        "status": 1,
        "location": 1,
        "phone": 1,
        "amount": 1,
    }
    appointments = []
    for appointment in db["appointments"].find(query, patient_schedule_fields).sort("date", 1):
        appointment["id"] = str(appointment.get("id") or appointment.get("appointment_id", ""))
        appointments.append(appointment)
    return appointments


# -----------------------------------------------------------------------------
# 6. Get Single Appointment Details
# -----------------------------------------------------------------------------
@router.get("/{apt_id}", response_model=Dict[str, Any])
def get_appointment_by_id(
    apt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves single appointment details."""
    apt = appointment_service.get_appointment_by_id(apt_id)
    if not apt:
        raise HTTPException(status_code=404, detail=f"Appointment '{apt_id}' not found.")
    user_id = str(current_user.get("id", ""))
    is_owner = str(apt.get("customer_id") or apt.get("patient_id") or "") == user_id
    is_doctor = current_user.get("role") == "doctor" and apt.get("doctor_id") == current_user.get("doctor_id")
    if not (is_owner or is_doctor or current_user.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="You are not authorized to view this appointment.")
    return apt


# -----------------------------------------------------------------------------
# 7. Reschedule Appointment
# -----------------------------------------------------------------------------
@router.put("/{apt_id}/reschedule", response_model=Dict[str, Any])
def reschedule_appointment(
    apt_id: str,
    req: AppointmentRescheduleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Reschedules an appointment enforcing:
    - 24-hour advance cancellation/rescheduling notice
    - Maximum 2 reschedules per appointment
    - Verified dynamic slot availability
    """
    user_id = str(current_user.get("id") or current_user.get("_id", "guest_user"))
    is_admin = current_user.get("role") == "admin"

    res = appointment_service.reschedule_appointment_record(
        appointment_id=apt_id,
        user_id=user_id,
        new_date_str=req.new_date,
        new_time_slot_str=req.new_time_slot,
        is_admin=is_admin
    )

    if not res["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res["message"]
        )

    # Fetch updated record
    apt = appointment_service.get_appointment_by_id(apt_id) or {}
    try:
        sms_res = generate_appointment_sms(
            action="RESCHEDULED",
            customer_name=current_user.get("name", "Valued Patient"),
            phone=apt.get("phone", current_user.get("phone", "+1 (555) 019-2831")),
            appointment_id=apt_id,
            doctor_name=apt.get("doctor_name", ""),
            department=apt.get("department", ""),
            date=req.new_date,
            time_slot=req.new_time_slot,
            location=apt.get("location", "Main Campus"),
            payment_method=apt.get("payment_method", "UPI"),
            amount=apt.get("amount", 150.0),
            payment_status=apt.get("payment_status", "PENDING"),
        )
        apt["sms_text"] = sms_res["sms_text"]
        apt["sms_delivery_status"] = sms_res["delivery_status"]
    except Exception as e:
        print(f"[Appointments] SMS error: {e}")

    return apt


# -----------------------------------------------------------------------------
# 8. Cancel Appointment
# -----------------------------------------------------------------------------
@router.put("/{apt_id}/cancel", response_model=Dict[str, Any])
def cancel_appointment(
    apt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancels an appointment enforcing:
    - 24-hour advance cancellation rule
    - If < 24 hours: requires Admin / Supervisor approval
    - Completed appointments cannot be cancelled
    """
    user_id = str(current_user.get("id") or current_user.get("_id", "guest_user"))
    is_admin = current_user.get("role") == "admin"

    res = appointment_service.cancel_appointment_record(
        appointment_id=apt_id,
        user_id=user_id,
        is_admin=is_admin
    )

    if not res["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res["message"]
        )

    apt = appointment_service.get_appointment_by_id(apt_id) or {}
    apt["message"] = res.get("message")
    apt["refund_status"] = res.get("refund_status")
    try:
        sms_res = generate_appointment_sms(
            action="CANCELLED",
            customer_name=current_user.get("name", "Valued Patient"),
            phone=apt.get("phone", current_user.get("phone", "+1 (555) 019-2831")),
            appointment_id=apt_id,
            doctor_name=apt.get("doctor_name", ""),
            department=apt.get("department", ""),
            date=apt.get("date", ""),
            time_slot=apt.get("time_slot", ""),
            location=apt.get("location", "Main Campus"),
            payment_method=apt.get("payment_method", "UPI"),
            amount=apt.get("amount", 150.0),
            payment_status=apt.get("payment_status", "PENDING"),
        )
        apt["sms_text"] = sms_res["sms_text"]
        apt["sms_delivery_status"] = sms_res["delivery_status"]
    except Exception as e:
        print(f"[Appointments] SMS error: {e}")

    return apt
