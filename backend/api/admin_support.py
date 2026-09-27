from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.api.auth import get_current_admin
from backend.database.connection import get_db


router = APIRouter(prefix="/api/admin", tags=["Admin Support Actions"])

CLINICAL_CATEGORIES = {"patient_safety", "clinical_care", "medical_records"}
ACCOUNT_CATEGORIES = {"account", "account_login", "login"}
INSURANCE_CATEGORIES = {"insurance", "insurance_documents", "documents"}
DOCUMENT_STATUSES = {"REQUESTED", "RECEIVED", "VERIFIED", "MISSING", "REJECTED"}


class AccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=40)


class InsuranceUpdate(BaseModel):
    provider_name: str = Field(min_length=1, max_length=120)
    member_id: str = Field(min_length=1, max_length=100)
    group_number: str = Field(default="", max_length=100)


class DocumentRequest(BaseModel):
    document_name: str = Field(min_length=2, max_length=120)
    request_note: str = Field(default="", max_length=500)


class DocumentStatusUpdate(BaseModel):
    status: str
    note: str = Field(default="", max_length=500)


def _ticket_context(ticket_id: str, allowed_categories: set[str]) -> tuple[dict, dict]:
    db = get_db()
    ticket = db["tickets"].find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Ticket was not found.")
    category = str(ticket.get("category") or "general").strip().lower()
    if category in CLINICAL_CATEGORIES:
        raise HTTPException(403, "Clinical tickets are handled in the doctor workflow.")
    if category not in allowed_categories:
        raise HTTPException(400, "This action is not available for the ticket category.")

    patient_id = str(ticket.get("customer_id") or ticket.get("patient_id") or "")
    patient = db["users"].find_one({"id": patient_id, "role": "customer"})
    if not patient:
        patient = db["users"].find_one({"email": patient_id, "role": "customer"})
    if not patient:
        raise HTTPException(404, "The patient account linked to this ticket was not found.")
    return ticket, patient


def _public_account(patient: dict) -> Dict[str, Any]:
    return {
        "patient_id": str(patient.get("id") or patient.get("_id") or ""),
        "name": patient.get("name", ""),
        "email": patient.get("email", ""),
        "phone": patient.get("phone", ""),
        "account_locked": bool(patient.get("account_locked", False)),
        "password_reset_required": bool(patient.get("password_reset_required", False)),
        "password_reset_requested_at": patient.get("password_reset_requested_at"),
    }


@router.get("/tickets/{ticket_id}/account")
def get_ticket_patient_account(ticket_id: str, _admin: dict = Depends(get_current_admin)):
    _ticket, patient = _ticket_context(ticket_id, ACCOUNT_CATEGORIES)
    return _public_account(patient)


@router.put("/tickets/{ticket_id}/account")
def update_ticket_patient_account(
    ticket_id: str,
    body: AccountUpdate,
    admin: dict = Depends(get_current_admin),
):
    _ticket, patient = _ticket_context(ticket_id, ACCOUNT_CATEGORIES)
    db = get_db()
    email = str(body.email).strip().lower()
    duplicate = db["users"].find_one({"email": email, "id": {"$ne": patient.get("id")}})
    if duplicate:
        raise HTTPException(409, "That email address is already used by another account.")

    db["users"].update_one(
        {"_id": patient["_id"]},
        {"$set": {
            "name": body.name.strip(),
            "email": email,
            "phone": body.phone.strip(),
            "account_updated_at": datetime.utcnow().isoformat(),
            "account_updated_by": str(admin.get("id") or admin.get("email") or "Admin"),
        }},
    )
    updated = db["users"].find_one({"_id": patient["_id"]})
    return _public_account(updated)


@router.post("/tickets/{ticket_id}/account/unlock")
def unlock_ticket_patient_account(ticket_id: str, admin: dict = Depends(get_current_admin)):
    _ticket, patient = _ticket_context(ticket_id, ACCOUNT_CATEGORIES)
    db = get_db()
    db["users"].update_one(
        {"_id": patient["_id"]},
        {"$set": {
            "account_locked": False,
            "account_unlocked_at": datetime.utcnow().isoformat(),
            "account_unlocked_by": str(admin.get("id") or admin.get("email") or "Admin"),
        }},
    )
    return _public_account(db["users"].find_one({"_id": patient["_id"]}))


@router.post("/tickets/{ticket_id}/account/password-reset")
def request_ticket_patient_password_reset(ticket_id: str, admin: dict = Depends(get_current_admin)):
    _ticket, patient = _ticket_context(ticket_id, ACCOUNT_CATEGORIES)
    db = get_db()
    reset_at = datetime.utcnow().isoformat()
    db["users"].update_one(
        {"_id": patient["_id"]},
        {"$set": {
            "password_reset_required": True,
            "password_reset_requested_at": reset_at,
            "password_reset_requested_by": str(admin.get("id") or admin.get("email") or "Admin"),
        }},
    )
    return _public_account(db["users"].find_one({"_id": patient["_id"]}))


@router.get("/tickets/{ticket_id}/insurance")
def get_ticket_insurance_records(ticket_id: str, _admin: dict = Depends(get_current_admin)):
    _ticket, patient = _ticket_context(ticket_id, INSURANCE_CATEGORIES)
    db = get_db()
    patient_id = str(patient.get("id") or patient.get("_id") or "")
    profile = db["insurance_profiles"].find_one({"patient_id": patient_id}, {"_id": 0}) or {}
    documents = list(db["support_documents"].find({"patient_id": patient_id}, {"_id": 0}).sort("created_at", -1))
    return {"insurance": profile, "documents": documents}


@router.put("/tickets/{ticket_id}/insurance")
def update_ticket_insurance(
    ticket_id: str,
    body: InsuranceUpdate,
    admin: dict = Depends(get_current_admin),
):
    _ticket, patient = _ticket_context(ticket_id, INSURANCE_CATEGORIES)
    patient_id = str(patient.get("id") or patient.get("_id") or "")
    now = datetime.utcnow().isoformat()
    record = {
        "patient_id": patient_id,
        "provider_name": body.provider_name.strip(),
        "member_id": body.member_id.strip(),
        "group_number": body.group_number.strip(),
        "updated_at": now,
        "updated_by": str(admin.get("id") or admin.get("email") or "Admin"),
    }
    get_db()["insurance_profiles"].update_one(
        {"patient_id": patient_id},
        {"$set": record, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return record


@router.post("/tickets/{ticket_id}/documents")
def request_ticket_document(
    ticket_id: str,
    body: DocumentRequest,
    admin: dict = Depends(get_current_admin),
):
    ticket, patient = _ticket_context(ticket_id, INSURANCE_CATEGORIES)
    now = datetime.utcnow().isoformat()
    document = {
        "document_id": f"doc_{uuid4().hex[:16]}",
        "patient_id": str(patient.get("id") or patient.get("_id") or ""),
        "ticket_id": ticket["ticket_id"],
        "document_name": body.document_name.strip(),
        "status": "REQUESTED",
        "request_note": body.request_note.strip(),
        "created_at": now,
        "updated_at": now,
        "updated_by": str(admin.get("id") or admin.get("email") or "Admin"),
    }
    get_db()["support_documents"].insert_one(document.copy())
    document.pop("_id", None)
    return document


@router.put("/tickets/{ticket_id}/documents/{document_id}")
def update_ticket_document_status(
    ticket_id: str,
    document_id: str,
    body: DocumentStatusUpdate,
    admin: dict = Depends(get_current_admin),
):
    ticket, patient = _ticket_context(ticket_id, INSURANCE_CATEGORIES)
    next_status = body.status.strip().upper()
    if next_status not in DOCUMENT_STATUSES:
        raise HTTPException(400, "Choose a valid document status.")
    query = {
        "document_id": document_id,
        "patient_id": str(patient.get("id") or patient.get("_id") or ""),
        "ticket_id": ticket["ticket_id"],
    }
    result = get_db()["support_documents"].find_one_and_update(
        query,
        {"$set": {
            "status": next_status,
            "status_note": body.note.strip(),
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": str(admin.get("id") or admin.get("email") or "Admin"),
        }},
        return_document=True,
    )
    if not result:
        raise HTTPException(404, "Document request was not found for this ticket.")
    result.pop("_id", None)
    return result
