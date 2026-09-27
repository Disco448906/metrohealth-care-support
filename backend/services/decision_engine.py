from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.ai.intent_classifier import classify_intent
from backend.rag.rag_pipeline import generate_rag_response
from backend.services.ticket_service import create_ticket
from backend.database.connection import get_db
from backend.database.health_records import get_patient_records
from backend.ai.llm_client import llm_client
from backend.ai.appointment_agent import handle_appointment_query


def datetime_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _is_appointment_followup(conversation_history: Optional[List[Dict]]) -> bool:
    """Recognize short answers to the last appointment question in chat."""
    if not conversation_history:
        return False
    last_assistant = next(
        (turn.get("content", "").lower() for turn in reversed(conversation_history) if turn.get("role") == "assistant"),
        "",
    )
    if "confirmed" in last_assistant or "successfully booked" in last_assistant:
        return False
    return any(marker in last_assistant for marker in (
        "full name",
        "date of birth",
        "which doctor would you like",
        "what date should i check",
        "what date would you prefer",
        "which time would you like",
        "which time works for you",
        "which time works for you?",
    ))


def _is_new_booking_request(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in (
        "book", "schedule an appointment", "schedule appointment",
        "make an appointment", "set up an appointment", "appointment with",
        "want an appointment", "need an appointment",
    ))


def _create_knowledge_followup(
    *,
    message: str,
    user_id: str,
    user_name: str,
    intent_info: Dict[str, Any],
    conversation_id: Optional[str],
) -> Dict[str, Any]:
    """Turn an unanswered information request into a trackable staff follow-up."""
    intent = intent_info.get("intent", "general_inquiry")
    category = intent_info.get("category", "information")
    severity = intent_info.get("severity", "LOW")
    priority = intent_info.get("priority", "LOW")
    department = intent_info.get("department", "Customer Support")
    confidence = intent_info.get("confidence", 0.0)
    method = intent_info.get("method", "unknown")
    ticket = create_ticket(
        customer_id=user_id,
        customer_name=user_name,
        title=f"Information follow-up: {message[:70]}",
        description=message,
        category=category,
        intent="information_follow_up",
        severity=severity,
        priority=priority,
        department=department,
        conversation_reference=conversation_id or "",
        ai_summary=(
            "The knowledge base did not contain a verified answer. "
            f"Staff follow-up requested. Original intent: {intent} "
            f"(confidence={confidence:.2f}, method={method})."
        ),
    )
    ticket_id = ticket["ticket_id"]
    return {
        "message": (
            "I couldn't find a verified answer in the hospital information available to me, "
            f"so I recorded this for the {department} team to review. Your reference is **{ticket_id}**. "
            "You can track its status in Support Requests."
        ),
        "intent": "information_follow_up",
        "category": category,
        "severity": severity,
        "priority": priority,
        "action": "CREATE_TICKET",
        "ticket_id": ticket_id,
        "department": department,
        "rag_used": False,
        "confidence": confidence,
        "method": method,
        "suggested_actions": intent_info.get("suggested_actions", ["View My Tickets"]),
    }


def process_customer_query(
    message: str,
    user_id: str = "guest_user",
    user_name: str = "Valued Customer",
    conversation_id: Optional[str] = None,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Orchestrates the AI Customer Care pipeline:
      1. Classify intent, category, and severity (AI / LLM-grounded).
      2. Route action to:
         - AUTO_RESOLVE: Real-time RAG + LLM conversational answers (timings, appointments, policies, general chat)
         - CREATE_TICKET: MongoDB ticket generation + empathetic, personalized LLM response
         - CRITICAL_ESCALATION: Immediate critical safety ticket + urgent clinical guidance LLM response
         - APPOINTMENT_AGENT: Gemini Function Calling agent for all appointment operations
    """
    # Step 1: Classify intent & severity
    intent_info = classify_intent(message)

    # Patient details, doctor choices, dates, and time slots are often short
    # replies that the standalone classifier labels as general questions.
    # Continue the appointment flow when the previous assistant turn asked for
    # one of those specific booking details.
    if intent_info.get("action") == "AUTO_RESOLVE" and (
        _is_new_booking_request(message) or _is_appointment_followup(conversation_history)
    ):
        intent_info = {
            **intent_info,
            "intent": "book_appointment",
            "category": "appointment",
            "severity": "LOW",
            "priority": "LOW",
            "action": "APPOINTMENT_AGENT",
            "department": "Appointments Desk",
            "method": "appointment_context",
            "suggested_actions": ["View My Appointments", "Find a Doctor"],
        }

    intent = intent_info["intent"]
    category = intent_info["category"]
    severity = intent_info["severity"]
    priority = intent_info["priority"]
    action = intent_info["action"]
    department = intent_info["department"]
    confidence = intent_info.get("confidence", 0.0)
    method = intent_info.get("method", "unknown")
    suggested_actions = intent_info.get("suggested_actions", ["Contact Support"])

    db = get_db()

    # Patient-specific actions are served only from the signed-in patient's own records.
    text = message.lower()
    records_query = any(term in text for term in (
        "my report", "my reports", "my test result", "my lab result", "my health report", "my diagnosis",
        "my prescription", "my medicine", "my medications", "medicine given to me", "medicines given to me",
        "prescribed to me", "my bill", "my invoice", "my appointment details", "my next appointment",
        "upcoming appointment", "show my appointment", "view my appointment", "list my appointment", "when is my appointment"
    )) and not any(term in text for term in ("wrong", "incorrect", "missing", "problem", "issue", "complaint", "cancel", "reschedule", "change my appointment", "book my appointment"))
    if records_query and user_id != "guest_user":
        result = {"reports": [], "medicines": [], "bills": [], "appointments": []}
        patient_records = get_patient_records(user_id)
        if any(term in text for term in ("report", "test result", "lab result", "diagnos")):
            result["reports"] = patient_records["reports"]
        if any(term in text for term in ("medicine", "medication", "prescription", "prescribed")):
            result["medicines"] = patient_records["medicines"]
        if "bill" in text or "invoice" in text:
            result["bills"] = patient_records["bills"]
        if "appointment" in text:
            result["appointments"] = list(db["appointments"].find({"$or": [{"customer_id": user_id}, {"patient_id": user_id}]}, {"_id": 0}))
        labels = {"reports": "Health reports", "medicines": "Prescriptions and medicines", "bills": "Bills", "appointments": "Appointments"}
        found = []
        for key, values in result.items():
            if not values:
                continue
            rows = []
            for item in values:
                if key == "appointments":
                    summary = f"{item.get('date', 'Date not listed')} at {item.get('time_slot', 'time not listed')} with {item.get('doctor_name', 'doctor not listed')} · {item.get('status', 'status unavailable')}"
                elif key == "bills":
                    summary = f"{item.get('description', item.get('title', 'Bill'))} · {item.get('currency', '')}{item.get('amount', 'amount not listed')} · {item.get('status', 'status unavailable')}"
                else:
                    summary = item.get("title") or item.get("medicine") or item.get("name") or "Record"
                    if key == "medicines":
                        instructions = [item.get("dosage"), item.get("frequency"), item.get("duration")]
                        if any(instructions):
                            summary += f" ({' · '.join(value for value in instructions if value)})"
                    if key == "reports" and item.get("report_date"):
                        summary += f" · {item['report_date']}"
                    details = item.get("details") or item.get("summary")
                    if details:
                        summary += f" — {details}"
                rows.append(f"• {summary}")
            found.append(f"{labels[key]}:\n" + "\n".join(rows))
        answer = "Here’s what I found in your account:\n\n" + "\n\n".join(found) if found else "I couldn't find any matching records on your account yet. Please ask your doctor to add medical records or the admin to add billing details."
        return {"message": answer, "intent": "patient_record_lookup", "category": "patient_records", "severity": "LOW", "priority": "LOW", "action": "AUTO_RESOLVE", "ticket_id": None, "department": "Patient Records", "rag_used": False, "confidence": 1.0, "method": "patient_record_lookup", "suggested_actions": []}

    if any(term in text for term in ("my ticket", "my complaint", "ticket status", "complaint status")) and user_id != "guest_user":
        patient_tickets = list(db["tickets"].find({"customer_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(10))
        if patient_tickets:
            answer = "\n\n".join(f"{t.get('ticket_id')} · {t.get('status')} — {t.get('title')}. {t.get('resolution_notes') or 'The responsible team is reviewing your concern.'}" for t in patient_tickets)
        else:
            answer = "I couldn't find any complaint tickets on your account yet. Tell me what happened and I can route it to the right team."
        return {"message": answer, "intent": "ticket_lookup", "category": "service", "severity": "LOW", "priority": "LOW", "action": "AUTO_RESOLVE", "ticket_id": None, "department": "Support", "rag_used": False, "confidence": 1.0, "method": "ticket_lookup", "suggested_actions": []}

    if intent_info.get("category") in {"patient_safety", "clinical_care", "medical_records"} and intent_info.get("action") in {"CREATE_TICKET", "CRITICAL_ESCALATION"}:
        intent_info["department"] = "Clinical Review"
        department = "Clinical Review"

    # -------------------------------------------------------------------
    # Case A: AUTO_RESOLVE — RAG Domain Grounding + Real-Time LLM
    # -------------------------------------------------------------------
    if action == "AUTO_RESOLVE":
        rag_result = generate_rag_response(
            query=message,
            intent_info=intent_info,
            conversation_history=conversation_history,
            return_details=True,
        )
        # Keep compatibility with simple response adapters that return only text.
        if isinstance(rag_result, dict):
            ai_answer = str(rag_result.get("message", ""))
            grounded = rag_result.get("grounded") is True
        else:
            ai_answer = str(rag_result)
            grounded = None

        if grounded is False and intent != "greeting":
            return _create_knowledge_followup(
                message=message,
                user_id=user_id,
                user_name=user_name,
                intent_info=intent_info,
                conversation_id=conversation_id,
            )

        # Log auto-resolved interaction
        db["complaints"].insert_one({
            "customer_id": user_id,
            "customer_name": user_name,
            "title": message[:60],
            "description": message,
            "category": category,
            "severity": severity,
            "status": "AUTO_RESOLVED",
            "ticket_id": None,
            "interaction_type": "self_service",
            "intent": intent,
            "confidence": confidence,
            "method": method,
            "created_at": datetime_now_iso()
        })

        return {
            "message": ai_answer,
            "intent": intent,
            "category": category,
            "severity": severity,
            "priority": priority,
            "action": action,
            "ticket_id": None,
            "department": department,
            "rag_used": grounded is True,
            "confidence": confidence,
            "method": method,
            "suggested_actions": suggested_actions
        }

    # -------------------------------------------------------------------
    # Case B: CREATE_TICKET — Ticket Generation + Real-Time Empathetic LLM Response
    # -------------------------------------------------------------------
    elif action == "CREATE_TICKET":
        ticket = create_ticket(
            customer_id=user_id,
            customer_name=user_name,
            title=f"Support Request: {intent.replace('_', ' ').title()}",
            description=message,
            category=category,
            intent=intent,
            severity=severity,
            priority=priority,
            department=department,
            conversation_reference=conversation_id or "",
            ai_summary=(
                f"Ticket created by GenAI pipeline. Intent: {intent} "
                f"(confidence={confidence:.2f}, method={method}). Severity: {severity}."
            )
        )

        ticket_id = ticket["ticket_id"]

        # Generate conversational, empathetic confirmation using LLM
        prompt_instructions = (
            f"You are MetroHealth AI Assistant. The customer has reported the following problem:\n"
            f"\"{message}\"\n\n"
            f"A formal support ticket has been created:\n"
            f"• Ticket ID: {ticket_id}\n"
            f"• Category: {category.replace('_', ' ').title()}\n"
            f"• Priority: {priority}\n"
            f"• Assigned Department: {department}\n\n"
            f"Write a warm, highly empathetic, and professional response like ChatGPT. "
            f"Acknowledge the user's specific concern directly, give them their Ticket ID (`{ticket_id}`), "
            f"explain that the request is in the {department} queue and can be tracked in their account. "
            f"Do not imply a staff member was notified or assigned. Conclude by asking how else you can support them."
        )

        if llm_client.is_configured():
            response_msg = llm_client.generate(
                user_message=message,
                system_prompt=prompt_instructions,
                conversation_history=conversation_history,
                temperature=0.3
            )
        else:
            response_msg = (
                f"I completely understand your concern regarding: *\"{message}\"*, and I am here to help you resolve this.\n\n"
                f"I have registered your complaint and created a support ticket:\n"
                f"• **Ticket ID**: `{ticket_id}`\n"
                f"• **Category**: {category.replace('_', ' ').title()}\n"
                f"• **Assigned Department**: {department}\n"
                f"• **Priority Level**: {priority}\n\n"
                f"Your request is now in the **{department}** queue. You can follow its status in your Support Requests. "
                f"A staff member has not been assigned yet.\n\n"
                f"Is there anything else I can assist you with right now?"
            )

        return {
            "message": response_msg,
            "intent": intent,
            "category": category,
            "severity": severity,
            "priority": priority,
            "action": action,
            "ticket_id": ticket_id,
            "department": department,
            "rag_used": False,
            "confidence": confidence,
            "method": method,
            "suggested_actions": suggested_actions
        }

    # -------------------------------------------------------------------
    # Case C: CRITICAL_ESCALATION — Critical Ticket + Urgent Safety LLM Response
    # -------------------------------------------------------------------
    elif action == "CRITICAL_ESCALATION":
        ticket = create_ticket(
            customer_id=user_id,
            customer_name=user_name,
            title=f"CRITICAL ESCALATION: {intent.replace('_', ' ').title()}",
            description=message,
            category=category,
            intent=intent,
            severity="CRITICAL",
            priority="CRITICAL",
            department="Clinical Review",
            ai_summary=(
                f"CRITICAL ticket auto-created. Intent: {intent} "
                f"(confidence={confidence:.2f}, method={method}). Urgent human clinician review required."
            )
        )

        ticket_id = ticket["ticket_id"]

        prompt_instructions = (
            f"URGENT CLINICAL SAFETY ESCALATION. The patient/customer has reported a critical safety concern:\n"
            f"\"{message}\"\n\n"
            f"Ticket ID: {ticket_id} (CRITICAL PRIORITY, placed in the clinical review queue).\n\n"
            f"CRITICAL RESPONSE REQUIREMENTS:\n"
            f"1. Highlight: ⚠️ **URGENT NOTICE & CRITICAL ESCALATION**\n"
            f"2. Confirm their issue has been flagged as CRITICAL with Ticket ID `{ticket_id}` and placed in the clinical review queue. Do not imply a clinician was paged or notified.\n"
            f"3. Include Medical Safety Disclaimer: As an AI assistant, you do NOT prescribe medications, adjust dosages, or give diagnostic instructions.\n"
            f"4. Direct the patient: If experiencing severe symptoms or an emergency, contact local emergency services or go to the nearest emergency department now.\n"
            f"5. Do not promise a clinician callback or say a clinician has been dispatched."
        )

        if llm_client.is_configured():
            response_msg = llm_client.generate(
                user_message=message,
                system_prompt=prompt_instructions,
                conversation_history=conversation_history,
                temperature=0.2
            )
        else:
            response_msg = (
                f"⚠️ **URGENT NOTICE & CRITICAL ESCALATION**\n\n"
                f"Your issue has been flagged as **CRITICAL** (Ticket ID: `{ticket_id}`) and "
                f"placed in the clinical review queue. This app does not page or notify clinicians.\n\n"
                f"‼️ **Medical Safety Disclaimer**: This AI assistant does NOT prescribe medications, "
                f"adjust dosages, or provide medical diagnoses.\n\n"
                f"If you or the patient are experiencing acute symptoms, allergic reactions, or a medical emergency, "
                f"please contact local emergency services or visit the nearest emergency department immediately.\n\n"
                f"You can follow Ticket `{ticket_id}` in your Support Requests."
            )

        return {
            "message": response_msg,
            "intent": intent,
            "category": category,
            "severity": "CRITICAL",
            "priority": "CRITICAL",
            "action": action,
            "ticket_id": ticket_id,
            "department": "Clinical Review",
            "rag_used": False,
            "confidence": confidence,
            "method": method,
            "suggested_actions": suggested_actions
        }

    # -------------------------------------------------------------------
    # Case D: APPOINTMENT_AGENT — Gemini Function Calling for appointments
    # -------------------------------------------------------------------
    elif action == "APPOINTMENT_AGENT":
        before_appointments = {
            str(item.get("id") or item.get("appointment_id")): (
                item.get("status"), item.get("date"), item.get("time_slot") or item.get("start_time"), item.get("updated_at")
            )
            for item in db["appointments"].find(
                {"$or": [{"customer_id": user_id}, {"patient_id": user_id}]},
                {"_id": 0},
            )
        }
        agent_response = handle_appointment_query(
            message=message,
            user_id=user_id,
            user_name=user_name,
            conversation_history=conversation_history
        )

        after_appointments = {
            str(item.get("id") or item.get("appointment_id")): (
                item.get("status"), item.get("date"), item.get("time_slot") or item.get("start_time"), item.get("updated_at")
            )
            for item in db["appointments"].find(
                {"$or": [{"customer_id": user_id}, {"patient_id": user_id}]},
                {"_id": 0},
            )
        }
        appointment_changed = before_appointments != after_appointments
        db["complaints"].insert_one({
            "customer_id": user_id,
            "customer_name": user_name,
            "title": message[:60],
            "description": message,
            "category": category,
            "severity": severity,
            "status": "AUTO_RESOLVED" if appointment_changed else "APPOINTMENT_ASSISTED",
            "ticket_id": None,
            "interaction_type": "appointment_assistance",
            "intent": intent,
            "confidence": confidence,
            "method": method,
            "created_at": datetime_now_iso()
        })

        return {
            "message": agent_response,
            "intent": intent,
            "category": category,
            "severity": severity,
            "priority": priority,
            "action": action,
            "ticket_id": None,
            "department": department,
            "rag_used": False,
            "confidence": confidence,
            "method": method,
            "suggested_actions": suggested_actions
        }

    # -------------------------------------------------------------------
    # Fallback: unknown action — treat as AUTO_RESOLVE
    # -------------------------------------------------------------------
    else:
        rag_result = generate_rag_response(
            query=message,
            intent_info=intent_info,
            conversation_history=conversation_history,
            return_details=True,
        )
        if isinstance(rag_result, dict):
            ai_answer = str(rag_result.get("message", ""))
            grounded = rag_result.get("grounded") is True
        else:
            ai_answer = str(rag_result)
            grounded = None
        if grounded is False and intent != "greeting":
            return _create_knowledge_followup(
                message=message,
                user_id=user_id,
                user_name=user_name,
                intent_info=intent_info,
                conversation_id=conversation_id,
            )
        return {
            "message": ai_answer,
            "intent": intent,
            "category": category,
            "severity": severity,
            "priority": priority,
            "action": "AUTO_RESOLVE",
            "ticket_id": None,
            "department": department,
            "rag_used": grounded is True,
            "confidence": confidence,
            "method": method,
            "suggested_actions": suggested_actions
        }
