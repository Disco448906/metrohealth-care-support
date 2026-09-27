from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import math
from typing import Any, Dict, List
from backend.api.auth import get_current_user, get_current_admin, get_current_doctor
from backend.database.connection import get_db
from backend.database.health_records import (
    add_bill, add_clinical_record as save_clinical_record, get_all_bills, get_doctor_records,
    get_patient_records, set_bill_status, update_bill_details, update_bill_refund_state, update_clinical_record,
)

router = APIRouter(prefix="/api/records", tags=["Patient Records and Billing"])


def _validate_clinical_record(record_type: str, record: Dict[str, Any]) -> None:
    if record_type not in {"report", "medicine"}:
        raise HTTPException(400, "Record type must be report or medicine.")
    if record_type == "report":
        if not str(record.get("title", "")).strip():
            raise HTTPException(400, "A report title is required.")
        if not str(record.get("details", "")).strip():
            raise HTTPException(400, "Report details are required.")
    else:
        if not str(record.get("medicine") or record.get("title", "")).strip():
            raise HTTPException(400, "A medicine name is required.")
        required = {"dosage": "Dose", "route": "Route", "frequency": "Frequency", "duration": "Duration", "quantity": "Quantity", "instructions": "Patient instructions"}
        missing = [label for key, label in required.items() if not str(record.get(key, "")).strip()]
        if missing:
            raise HTTPException(400, f"Complete prescription details: {', '.join(missing)}.")

@router.get("/mine")
def get_my_records(user: dict = Depends(get_current_user)):
    if user.get("role") != "customer":
        raise HTTPException(403, "Patient account required.")
    return get_patient_records(str(user["id"]))

@router.get("/doctor/patients")
def doctor_patients(user: dict = Depends(get_current_doctor)):
    db = get_db()
    doctor_id = user["doctor_id"]
    # Doctors can only see records for patients they have treated or have scheduled.
    patient_ids = {str(a.get("customer_id") or a.get("patient_id")) for a in db["appointments"].find({"doctor_id": doctor_id})}
    return get_doctor_records(doctor_id, list(patient_ids))

@router.post("/doctor/{patient_id}")
def add_clinical_record(patient_id: str, record: Dict[str, Any], user: dict = Depends(get_current_doctor)):
    db = get_db()
    doctor_id = user["doctor_id"]
    if not db["appointments"].find_one({"doctor_id": doctor_id, "$or": [{"patient_id": patient_id}, {"customer_id": patient_id}]}):
        raise HTTPException(403, "This patient is not assigned to your care.")
    record_type = record.get("type")
    _validate_clinical_record(record_type, record)
    appointment = db["appointments"].find_one({"doctor_id": doctor_id, "$or": [{"patient_id": patient_id}, {"customer_id": patient_id}]})
    patient_name = str(appointment.get("patient_name") or appointment.get("customer_name") or record.get("patient_name") or "Patient")
    return save_clinical_record(record_type, patient_id, doctor_id, user["name"], patient_name, record)

@router.put("/doctor/{patient_id}/{record_id}")
def edit_clinical_record(patient_id: str, record_id: str, record: Dict[str, Any], user: dict = Depends(get_current_doctor)):
    db = get_db()
    doctor_id = user["doctor_id"]
    if not db["appointments"].find_one({"doctor_id": doctor_id, "$or": [{"patient_id": patient_id}, {"customer_id": patient_id}]}):
        raise HTTPException(403, "This patient is not assigned to your care.")

    record_type = record.get("type")
    _validate_clinical_record(record_type, record)

    updated = update_clinical_record(record_type, patient_id, doctor_id, record_id, record)
    if not updated:
        raise HTTPException(404, "This record was not found for the selected patient.")
    return updated

@router.get("/admin/bills")
def admin_bills(user: dict = Depends(get_current_admin)):
    return get_all_bills()

@router.post("/admin/bills")
def create_bill(bill: Dict[str, Any], user: dict = Depends(get_current_admin)):
    patient_id = str(bill.get("patient_id", ""))
    patient = get_db()["users"].find_one({"id": patient_id, "role": "customer"})
    if not patient:
        raise HTTPException(400, "A valid patient_id is required.")
    try:
        amount = float(bill["amount"])
        description = str(bill.get("description") or bill.get("title") or "").strip()
        bill_status = str(bill.get("status") or "UNPAID").upper()
        if not math.isfinite(amount) or amount <= 0:
            raise HTTPException(400, "Bill amount must be a positive finite number.")
        if not description:
            raise HTTPException(400, "A bill description is required.")
        if bill_status not in {"UNPAID", "PENDING", "PAID", "OVERDUE", "CANCELLED"}:
            raise HTTPException(400, "Choose a valid billing status.")
        tax = float(bill.get("tax") or 0)
        subtotal = float(bill.get("subtotal") if bill.get("subtotal") is not None else amount - tax)
        if not math.isfinite(tax) or tax < 0 or not math.isfinite(subtotal) or subtotal < 0:
            raise HTTPException(400, "Enter valid subtotal and tax amounts.")
        if abs((subtotal + tax) - amount) > 0.02:
            raise HTTPException(400, "Bill total must equal subtotal plus tax.")
        return add_bill(patient_id, patient.get("name", "Patient"), description, amount, str(bill.get("currency") or "₹"), bill_status, bill)
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "A valid bill amount is required.")

@router.put("/admin/bills/{bill_id}/status")
def update_bill_status(bill_id: str, body: Dict[str, str], user: dict = Depends(get_current_admin)):
    status = body.get("status", "").upper()
    if status not in {"UNPAID", "PENDING", "PAID", "OVERDUE", "CANCELLED"}:
        raise HTTPException(400, "Choose a valid billing status.")
    result = set_bill_status(bill_id, status)
    if not result:
        raise HTTPException(404, "Bill was not found.")
    return result

@router.put("/admin/bills/{bill_id}/refund")
def update_bill_refund(bill_id: str, body: Dict[str, str], user: dict = Depends(get_current_admin)):
    refund_status = str(body.get("refund_status") or "").strip().upper()
    refund_note = str(body.get("refund_note") or "").strip()
    allowed = {"NOT_REQUESTED", "UNDER_REVIEW", "APPROVED", "PROCESSING_EXTERNALLY", "COMPLETED_EXTERNALLY"}
    if refund_status not in allowed:
        raise HTTPException(400, "Choose a valid refund workflow status.")
    if refund_status != "NOT_REQUESTED" and not refund_note:
        raise HTTPException(400, "Add a note explaining the refund status.")
    result = update_bill_refund_state(bill_id, refund_status, refund_note)
    if not result:
        raise HTTPException(404, "Bill was not found.")
    return result

@router.put("/admin/bills/{bill_id}")
def edit_bill(bill_id: str, body: Dict[str, Any], user: dict = Depends(get_current_admin)):
    description = str(body.get("description", "")).strip()
    try:
        amount = float(body.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(400, "Enter a valid bill amount.")
    if not description:
        raise HTTPException(400, "A bill description is required.")
    if not math.isfinite(amount) or amount <= 0:
        raise HTTPException(400, "Bill amount must be a positive finite number.")
    result = update_bill_details(bill_id, description, amount)
    if not result:
        raise HTTPException(404, "Bill was not found.")
    return result
