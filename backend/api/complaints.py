from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.database.connection import get_db
from backend.schemas.schemas import ComplaintCreate, ComplaintResponse
from backend.services.ticket_service import create_ticket

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

_CATEGORY_ROUTING = {
    "billing": ("Billing & Accounts", "HIGH"),
    "appointment": ("Appointments Desk", "MEDIUM"),
    "service": ("Patient Experience", "MEDIUM"),
    "insurance": ("Insurance Help Desk", "HIGH"),
    "medical_records": ("Clinical Review", "HIGH"),
    "clinical_care": ("Clinical Review", "HIGH"),
    "patient_safety": ("Clinical Review", "CRITICAL"),
    "data_security": ("Legal & Data Security", "CRITICAL"),
    "information": ("Information Desk", "LOW"),
    "general": ("Customer Support", "MEDIUM"),
}


@router.post("", response_model=ComplaintResponse)
def create_complaint(
    complaint: ComplaintCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a staff-visible ticket and its linked complaint record together."""
    if current_user.get("role") != "customer":
        raise HTTPException(status_code=403, detail="Patient account required to submit a complaint.")
    title = complaint.title.strip()
    description = complaint.description.strip()
    if not title or not description:
        raise HTTPException(status_code=400, detail="A complaint title and description are required.")

    category = complaint.category.strip().lower().replace(" ", "_")
    route = _CATEGORY_ROUTING.get(category)
    if not route:
        raise HTTPException(status_code=400, detail="Choose a supported complaint category.")
    department, severity = route
    ticket = create_ticket(
        customer_id=str(current_user["id"]),
        customer_name=current_user["name"],
        title=title,
        description=description,
        category=category,
        intent="patient_submitted_complaint",
        severity=severity,
        priority=severity,
        department=department,
        ai_summary=f"Submitted through the patient complaint form and routed to {department}.",
    )
    doc = get_db()["complaints"].find_one({"ticket_id": ticket["ticket_id"]})
    if not doc:
        raise HTTPException(status_code=500, detail="Complaint ticket was created, but its tracking record is unavailable.")
    doc.pop("_id", None)
    return doc


@router.get("", response_model=List[ComplaintResponse])
def get_complaints(current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user.get("role") == "admin":
        query = {"category": {"$nin": ["patient_safety", "clinical_care", "medical_records"]}}
    else:
        c_set = {
            str(current_user.get("id", "")),
            str(current_user.get("_id", "")),
            str(current_user.get("email", "")),
        }
        c_ids = [customer_id for customer_id in c_set if customer_id]
        query = {"customer_id": {"$in": c_ids}}

    cursor = db["complaints"].find(query).sort("created_at", -1)
    complaints = []
    for item in cursor:
        item["id"] = str(item.get("id", item.get("_id", "")))
        item.pop("_id", None)
        complaints.append(item)
    return complaints
