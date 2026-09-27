import re
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_ZS_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"

# ---------------------------------------------------------------------------
# Intent label definitions — used as candidate labels for zero-shot LLM
# ---------------------------------------------------------------------------
ZS_LABEL_MAP = {
    "medication error or wrong drug": {
        "intent": "medication_error", "category": "patient_safety",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Patient Safety & Clinical Governance"
    },
    "privacy or data breach": {
        "intent": "privacy_breach", "category": "data_security",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Legal & Data Security"
    },
    "patient safety emergency": {
        "intent": "patient_safety_issue", "category": "patient_safety",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Emergency Medical Services"
    },
    "incorrect or wrong bill or overcharge": {
        "intent": "wrong_billing", "category": "billing",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Billing & Accounts"
    },
    "delayed or missing refund": {
        "intent": "delayed_refund", "category": "billing",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Billing & Accounts"
    },
    "long waiting time complaint": {
        "intent": "waiting_time_complaint", "category": "service",
        "severity": "MEDIUM", "priority": "MEDIUM",
        "action": "CREATE_TICKET", "department": "Patient Experience"
    },
    "insurance claim dispute or rejection": {
        "intent": "insurance_dispute", "category": "insurance",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Insurance Help Desk"
    },
    "incorrect medical report or lab result": {
        "intent": "incorrect_medical_report", "category": "medical_records",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Diagnostic Lab Support"
    },
    "rude or unprofessional staff complaint": {
        "intent": "staff_complaint", "category": "service",
        "severity": "MEDIUM", "priority": "MEDIUM",
        "action": "CREATE_TICKET", "department": "Hospital Management"
    },
    "poor treatment or misdiagnosis complaint": {
        "intent": "treatment_complaint", "category": "clinical_care",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Medical Quality Assurance"
    },
    "hospital timings or opening hours": {
        "intent": "hospital_timings", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Information Desk"
    },
    "book appointment or schedule a doctor visit": {
        "intent": "book_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk"
    },
    "reschedule or change appointment": {
        "intent": "reschedule_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk"
    },
    "cancel appointment": {
        "intent": "cancel_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk"
    },
    "doctor availability or schedule": {
        "intent": "doctor_availability", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Information Desk"
    },
    "refund policy or rules": {
        "intent": "refund_policy", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Billing Desk"
    },
    "how to access reports or lab results": {
        "intent": "report_access", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Records Desk"
    },
    "hospital location or contact number": {
        "intent": "contact_location", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Information Desk"
    },
    "general complaint or problem": {
        "intent": "general_complaint", "category": "service",
        "severity": "MEDIUM", "priority": "MEDIUM",
        "action": "CREATE_TICKET", "department": "Customer Support"
    },
    "general question or inquiry": {
        "intent": "general_inquiry", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Customer Support"
    },
}

# ---------------------------------------------------------------------------
# Keyword rules — kept as OFFLINE FALLBACK only (not primary)
# ---------------------------------------------------------------------------
_INTENT_RULES_FALLBACK = [
    {
        "intent": "medication_error", "category": "patient_safety",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Patient Safety & Clinical Governance",
        "keywords": ["wrong medication", "wrong medicine", "wrong prescription", "wrong dose",
                     "overdose", "allergic reaction", "medication error", "wrong pill", "poisoning"]
    },
    {
        "intent": "privacy_breach", "category": "data_security",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Legal & Data Security",
        "keywords": ["privacy breach", "data breach", "medical records leaked",
                     "unauthorized access", "hipaa violation", "confidentiality breach"]
    },
    {
        "intent": "patient_safety_issue", "category": "patient_safety",
        "severity": "CRITICAL", "priority": "CRITICAL",
        "action": "CRITICAL_ESCALATION", "department": "Emergency Medical Services",
        "keywords": ["patient safety", "negligence", "life threatening", "icu emergency",
                     "suicidal", "severe pain", "bleeding profusely", "unconscious"]
    },
    {
        "intent": "wrong_billing", "category": "billing",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Billing & Accounts",
        "keywords": ["wrong bill", "incorrect bill", "overcharged", "double charged",
                     "billing error", "wrong charge", "invoice mismatch"]
    },
    {
        "intent": "delayed_refund", "category": "billing",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Billing & Accounts",
        "keywords": ["refund not arrived", "delayed refund", "refund delayed",
                     "where is my refund", "haven't received refund", "refund missing", "money not credited"]
    },
    {
        "intent": "waiting_time_complaint", "category": "service",
        "severity": "MEDIUM", "priority": "MEDIUM",
        "action": "CREATE_TICKET", "department": "Patient Experience",
        "keywords": ["waiting time", "waited too long", "long queue", "doctor late", "kept waiting"]
    },
    {
        "intent": "insurance_dispute", "category": "insurance",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Insurance Help Desk",
        "keywords": ["insurance claim dispute", "claim rejected", "insurance denial",
                     "pre-authorization rejected", "claim problem"]
    },
    {
        "intent": "incorrect_medical_report", "category": "medical_records",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Diagnostic Lab Support",
        "keywords": ["incorrect report", "wrong test result", "incorrect medical report",
                     "wrong patient name on report", "lab error", "report mistake"]
    },
    {
        "intent": "staff_complaint", "category": "service",
        "severity": "MEDIUM", "priority": "MEDIUM",
        "action": "CREATE_TICKET", "department": "Hospital Management",
        "keywords": ["staff complaint", "rude staff", "nurse rude",
                     "receptionist bad behavior", "unprofessional staff"]
    },
    {
        "intent": "treatment_complaint", "category": "clinical_care",
        "severity": "HIGH", "priority": "HIGH",
        "action": "CREATE_TICKET", "department": "Medical Quality Assurance",
        "keywords": ["treatment complaint", "unsatisfied with treatment",
                     "poor care", "doctor rude", "misdiagnosis complaint"]
    },
    {
        "intent": "hospital_timings", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Information Desk",
        "keywords": ["hospital timing", "opening hours", "opd hours",
                     "when is opd open", "clinic hours", "what time does hospital open"]
    },
    {
        "intent": "book_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk",
        "keywords": ["book appointment", "book an appointment", "schedule appointment",
                     "i want to see a doctor", "make an appointment", "i need an appointment",
                     "want to book", "book a slot", "need to see a doctor", "book with dr"]
    },
    {
        "intent": "reschedule_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk",
        "keywords": ["reschedule appointment", "reschedule my appointment", "i want to reschedule",
                     "change appointment date", "change my appointment", "move my appointment",
                     "reschedule my doctor visit", "change slot"]
    },
    {
        "intent": "cancel_appointment", "category": "appointment",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Appointments Desk",
        "keywords": ["cancel appointment", "cancellation of appointment",
                     "cancel my visit", "drop appointment"]
    },
    {
        "intent": "doctor_availability", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "APPOINTMENT_AGENT", "department": "Information Desk",
        "keywords": ["doctor availability", "is doctor available", "doctor schedule",
                     "when is dr", "cardiologist available", "orthopedic timing",
                     "list doctors", "show doctors", "available doctors", "which doctors"]
    },
    {
        "intent": "refund_policy", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Billing Desk",
        "keywords": ["refund policy", "how long refund takes",
                     "cancellation refund rule", "refund terms"]
    },
    {
        "intent": "report_access", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Records Desk",
        "keywords": ["check report", "where can i check my report", "download lab report",
                     "view test results", "prescription access", "portal login report"]
    },
    {
        "intent": "contact_location", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Information Desk",
        "keywords": ["location", "address", "phone number", "contact number",
                     "where is central campus", "hospital map"]
    },
    {
        "intent": "greeting", "category": "general",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Customer Support",
        "keywords": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "howdy", "hiya"]
    },
]

# ---------------------------------------------------------------------------
# Context-aware suggested actions map
# ---------------------------------------------------------------------------
SUGGESTIONS_MAP = {
    "greeting":               ["Hospital Timings", "Book an Appointment", "Find a Doctor", "Billing & Insurance FAQ"],
    "hospital_timings":       ["Book an Appointment", "Find a Doctor", "Contact Support"],
    "book_appointment":       ["View My Appointments", "Find a Doctor", "Check Doctor Availability"],
    "reschedule_appointment": ["View My Appointments", "Cancel Appointment", "Refund Policy"],
    "cancel_appointment":     ["Check Refund Status", "Book New Appointment", "View My Tickets"],
    "refund_policy":          ["Track My Refund", "Contact Billing Desk", "View My Tickets"],
    "report_access":          ["Download Lab Report", "Contact Records Desk", "Speak to Support"],
    "contact_location":       ["Book an Appointment", "Call Helpline", "View Hospital Map"],
    "doctor_availability":    ["Book an Appointment", "View All Doctors", "Contact Information Desk"],
    "wrong_billing":          ["View My Tickets", "Contact Billing Desk", "Check Appointment Status"],
    "delayed_refund":         ["View My Tickets", "Check Refund Policy", "Contact Billing Desk"],
    "insurance_dispute":      ["View My Tickets", "Contact Insurance Help Desk", "Speak to Support"],
    "staff_complaint":        ["Track Complaint Ticket", "Contact Hospital Management", "Return to Dashboard"],
    "treatment_complaint":    ["Track Complaint Ticket", "Speak to Medical Officer", "Return to Dashboard"],
    "incorrect_medical_report": ["View My Tickets", "Contact Lab Support", "Download Report"],
    "waiting_time_complaint": ["Track Complaint Ticket", "View My Appointments", "Contact Support"],
    "medication_error":       ["Call Emergency Care (+1 800-555-0199)", "Track Critical Ticket", "Return to Dashboard"],
    "patient_safety_issue":   ["Call Emergency Care (+1 800-555-0199)", "Track Critical Ticket", "Return to Dashboard"],
    "privacy_breach":         ["Track Critical Ticket", "Contact Legal & Data Security", "Return to Dashboard"],
    "general_complaint":      ["View My Tickets", "Contact Support Desk", "Check Appointment Status"],
    "general_inquiry":        ["Book an Appointment", "View Hospital Info", "Contact Support"],
    "billing_info":           ["View My Bills", "Contact Billing Desk", "Check Refund Policy"],
}


def _build_result(mapping: dict, confidence: float, method: str) -> dict:
    """Attach confidence and method to a ZS_LABEL_MAP entry."""
    result = dict(mapping)
    result["confidence"] = round(confidence, 4)
    result["method"] = method
    result["suggested_actions"] = SUGGESTIONS_MAP.get(result["intent"], ["Contact Support"])
    return result


def _classify_intent_llm(message: str) -> dict | None:
    """
    Primary classifier: HuggingFace zero-shot (facebook/bart-large-mnli).
    Returns None if the API is unavailable or confidence is too low.
    Retries once on 503 (model loading).
    """
    if not HF_TOKEN or HF_TOKEN in ("", "YOUR_HUGGINGFACE_TOKEN", "hf_demo_token_placeholder"):
        return None

    labels = list(ZS_LABEL_MAP.keys())
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": message,
        "parameters": {"candidate_labels": labels, "multi_label": False}
    }

    for attempt in range(1):
        try:
            res = requests.post(HF_ZS_URL, headers=headers, json=payload, timeout=6)

            if res.status_code == 503:
                # Model is loading on HuggingFace — wait and retry
                print(f"[IntentClassifier] HF model loading (503), retrying in 5s... (attempt {attempt + 1})")
                time.sleep(5)
                continue

            if res.status_code != 200:
                print(f"[IntentClassifier] HF API error {res.status_code}: {res.text[:200]}")
                return None

            result = res.json()
            if not isinstance(result, dict) or "labels" not in result:
                return None

            top_label = result["labels"][0]
            top_score = result["scores"][0]

            print(f"[IntentClassifier] LLM → '{top_label}' (score={top_score:.3f}, method=zero_shot)")

            # Confidence threshold — below 0.38 means model is unsure, fall through to keyword rules
            if top_score < 0.38:
                print(f"[IntentClassifier] Low confidence ({top_score:.3f}), falling back to keyword rules.")
                return None

            if top_label in ZS_LABEL_MAP:
                return _build_result(ZS_LABEL_MAP[top_label], top_score, "zero_shot_llm")

        except requests.exceptions.Timeout:
            print("[IntentClassifier] HF API timeout — falling back to keyword rules.")
            return None
        except Exception as e:
            print(f"[IntentClassifier] HF API exception: {e}")
            return None

    return None


def _classify_intent_fallback(message: str) -> dict:
    """
    Secondary classifier: keyword rule matching.
    Used ONLY when the LLM API is offline or returns low confidence.
    """
    msg_clean = message.lower().strip()

    # Check exact/word-boundary greetings first for natural conversation
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]
    tokens = re.findall(r"\b\w+\b", msg_clean)
    if any(g in msg_clean for g in ["good morning", "good afternoon", "good evening"]) or any(t in ["hi", "hello", "hey", "greetings", "howdy"] for t in tokens):
        return {
            "intent": "greeting", "category": "general",
            "severity": "LOW", "priority": "LOW",
            "action": "AUTO_RESOLVE", "department": "Customer Support",
            "confidence": 0.95, "method": "greeting_handler",
            "suggested_actions": SUGGESTIONS_MAP["greeting"]
        }

    for rule in _INTENT_RULES_FALLBACK:
        if rule["intent"] == "greeting":
            continue
        for kw in rule["keywords"]:
            if kw in msg_clean:
                result = {k: v for k, v in rule.items() if k != "keywords"}
                result["confidence"] = 0.9
                result["method"] = "keyword_fallback"
                result["suggested_actions"] = SUGGESTIONS_MAP.get(result["intent"], ["Contact Support"])
                print(f"[IntentClassifier] Keyword -> '{result['intent']}' matched '{kw}'")
                return result

    # Secondary fuzzy checks
    if any(word in msg_clean for word in ["bill", "charge", "payment", "invoice", "cost"]):
        if any(word in msg_clean for word in ["wrong", "high", "incorrect", "extra", "mistake", "error"]):
            return {
                "intent": "wrong_billing", "category": "billing",
                "severity": "HIGH", "priority": "HIGH",
                "action": "CREATE_TICKET", "department": "Billing & Accounts",
                "confidence": 0.75, "method": "fuzzy_fallback",
                "suggested_actions": SUGGESTIONS_MAP["wrong_billing"]
            }
        return {
            "intent": "billing_info", "category": "billing",
            "severity": "LOW", "priority": "LOW",
            "action": "AUTO_RESOLVE", "department": "Billing & Accounts",
            "confidence": 0.65, "method": "fuzzy_fallback",
            "suggested_actions": SUGGESTIONS_MAP["billing_info"]
        }

    if any(word in msg_clean for word in ["refund", "money back"]):
        # Distinguish policy question from actual refund complaint
        if any(w in msg_clean for w in ["policy", "how long", "rules", "terms", "when"]):
            return {
                "intent": "refund_policy", "category": "information",
                "severity": "LOW", "priority": "LOW",
                "action": "AUTO_RESOLVE", "department": "Billing Desk",
                "confidence": 0.75, "method": "fuzzy_fallback",
                "suggested_actions": SUGGESTIONS_MAP["refund_policy"]
            }
        return {
            "intent": "delayed_refund", "category": "billing",
            "severity": "HIGH", "priority": "HIGH",
            "action": "CREATE_TICKET", "department": "Billing & Accounts",
            "confidence": 0.7, "method": "fuzzy_fallback",
            "suggested_actions": SUGGESTIONS_MAP["delayed_refund"]
        }

    if any(word in msg_clean for word in ["complaint", "issue", "problem", "frustrated", "unhappy"]):
        return {
            "intent": "general_complaint", "category": "service",
            "severity": "MEDIUM", "priority": "MEDIUM",
            "action": "CREATE_TICKET", "department": "Customer Support",
            "confidence": 0.6, "method": "fuzzy_fallback",
            "suggested_actions": SUGGESTIONS_MAP["general_complaint"]
        }

    # Default
    return {
        "intent": "general_inquiry", "category": "information",
        "severity": "LOW", "priority": "LOW",
        "action": "AUTO_RESOLVE", "department": "Customer Support",
        "confidence": 0.5, "method": "default_fallback",
        "suggested_actions": SUGGESTIONS_MAP["general_inquiry"]
    }


def classify_intent(message: str) -> dict:
    """
    Main entry point for intent classification.

    Flow:
      1. Try HuggingFace zero-shot LLM (facebook/bart-large-mnli)  ← PRIMARY
      2. If LLM unavailable / low-confidence → keyword rule fallback ← SECONDARY
      3. If no keyword match → fuzzy heuristics → default general_inquiry

    Returns a dict with keys:
      intent, category, severity, priority, action, department,
      confidence (0.0–1.0), method (zero_shot_llm | keyword_fallback | fuzzy_fallback | default_fallback),
      suggested_actions (List[str])
    """
    # Keep explicit safety reports and appointment actions deterministic. A
    # generic high-confidence classifier label must not turn them into FAQs.
    rule_result = _classify_intent_fallback(message)
    if rule_result.get("severity") == "CRITICAL" or rule_result.get("intent") in {
        "book_appointment", "reschedule_appointment", "cancel_appointment"
    }:
        return rule_result

    # Step 1: Try LLM zero-shot for less explicit queries
    llm_result = _classify_intent_llm(message)
    if llm_result:
        return llm_result

    # Step 2: Keyword/fuzzy fallback
    return rule_result
