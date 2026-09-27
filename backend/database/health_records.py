"""Persistent SQLite storage for patient clinical records and billing demo data."""
import os
import sqlite3
import uuid
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional


def _database_path() -> str:
    configured = os.getenv("HEALTH_RECORDS_DB")
    if configured:
        return os.path.abspath(configured)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "patient_records.sqlite3")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(_database_path(), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_health_records_db() -> None:
    os.makedirs(os.path.dirname(_database_path()), exist_ok=True)
    with _connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS medical_reports (
                record_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL DEFAULT '',
                doctor_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                report_type TEXT NOT NULL DEFAULT 'Clinical report',
                indication TEXT NOT NULL DEFAULT '',
                findings TEXT NOT NULL DEFAULT '',
                impression TEXT NOT NULL DEFAULT '',
                recommendations TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                report_date TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_reports_patient ON medical_reports(patient_id);
            CREATE INDEX IF NOT EXISTS idx_reports_doctor ON medical_reports(doctor_id, patient_id);
            CREATE TABLE IF NOT EXISTS prescriptions (
                record_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL DEFAULT '',
                doctor_id TEXT NOT NULL,
                doctor_name TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                medicine TEXT NOT NULL DEFAULT '',
                strength TEXT NOT NULL DEFAULT '',
                dosage TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                frequency TEXT NOT NULL DEFAULT '',
                duration TEXT NOT NULL DEFAULT '',
                quantity TEXT NOT NULL DEFAULT '',
                refills TEXT NOT NULL DEFAULT '0',
                diagnosis TEXT NOT NULL DEFAULT '',
                instructions TEXT NOT NULL DEFAULT '',
                issued_date TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_prescriptions_patient ON prescriptions(patient_id);
            CREATE INDEX IF NOT EXISTS idx_prescriptions_doctor ON prescriptions(doctor_id, patient_id);
            CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT '₹',
                service_date TEXT NOT NULL DEFAULT '',
                due_date TEXT NOT NULL DEFAULT '',
                provider_name TEXT NOT NULL DEFAULT 'MetroHealth Hospital',
                payment_method TEXT NOT NULL DEFAULT '',
                line_items TEXT NOT NULL DEFAULT '[]',
                refund_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED',
                refund_note TEXT NOT NULL DEFAULT '',
                refund_updated_at TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'UNPAID',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_bills_patient ON bills(patient_id);
        """)
        # Safely extend databases created by earlier versions without losing rows.
        columns_to_add = {
            "medical_reports": {
                "report_type": "TEXT NOT NULL DEFAULT 'Clinical report'", "indication": "TEXT NOT NULL DEFAULT ''",
                "findings": "TEXT NOT NULL DEFAULT ''", "impression": "TEXT NOT NULL DEFAULT ''",
                "recommendations": "TEXT NOT NULL DEFAULT ''",
            },
            "prescriptions": {
                "strength": "TEXT NOT NULL DEFAULT ''", "route": "TEXT NOT NULL DEFAULT ''",
                "quantity": "TEXT NOT NULL DEFAULT ''", "refills": "TEXT NOT NULL DEFAULT '0'",
                "diagnosis": "TEXT NOT NULL DEFAULT ''", "instructions": "TEXT NOT NULL DEFAULT ''",
                "issued_date": "TEXT NOT NULL DEFAULT ''",
            },
            "bills": {
                "subtotal": "REAL NOT NULL DEFAULT 0", "tax": "REAL NOT NULL DEFAULT 0",
                "service_date": "TEXT NOT NULL DEFAULT ''", "due_date": "TEXT NOT NULL DEFAULT ''",
                "provider_name": "TEXT NOT NULL DEFAULT 'MetroHealth Hospital'", "payment_method": "TEXT NOT NULL DEFAULT ''",
                "line_items": "TEXT NOT NULL DEFAULT '[]'", "refund_status": "TEXT NOT NULL DEFAULT 'NOT_REQUESTED'",
                "refund_note": "TEXT NOT NULL DEFAULT ''", "refund_updated_at": "TEXT NOT NULL DEFAULT ''",
            },
        }
        for table, columns in columns_to_add.items():
            existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def seed_demo_health_records() -> None:
    """Create idempotent, clearly labeled sample rows for all seeded demo patients."""
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    today = datetime.utcnow().date().isoformat()
    patients = [
        ("usr_01", "John Doe", "doc_ravi", "Dr. Ravi", "Cardiology"),
        ("usr_02", "Alice Smith", "doc_michael", "Dr. Michael Chen", "Orthopedics"),
        ("usr_03", "Robert Johnson", "doc_emily", "Dr. Emily Rodriguez", "Pediatrics"),
        ("usr_04", "Emily Davis", "doc_robert", "Dr. Robert Taylor", "General Medicine"),
        ("usr_05", "Michael Brown", "doc_priya", "Dr. Priya", "Dermatology"),
        ("usr_06", "Sophia Wilson", "doc_ravi", "Dr. Ravi", "Cardiology"),
        ("usr_07", "David Martinez", "doc_michael", "Dr. Michael Chen", "Orthopedics"),
        ("usr_08", "Olivia Taylor", "doc_emily", "Dr. Emily Rodriguez", "Pediatrics"),
        ("usr_09", "James Anderson", "doc_robert", "Dr. Robert Taylor", "General Medicine"),
        ("usr_10", "Charlotte Thomas", "doc_priya", "Dr. Priya", "Dermatology"),
    ]
    with _connect() as db:
        for index, (patient_id, patient_name, doctor_id, doctor_name, specialty) in enumerate(patients, start=1):
            db.execute(
                "INSERT OR IGNORE INTO medical_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"demo_report_{index:03d}", patient_id, patient_name, doctor_id, doctor_name,
                    f"{specialty} visit summary (DEMO)",
                    "SIMULATED DEMO DATA — Example portal entry only. This is not a real test result, diagnosis, or medical record.",
                    today, now,
                ),
            )
            db.execute(
                "INSERT OR IGNORE INTO prescriptions (record_id, patient_id, patient_name, doctor_id, doctor_name, title, medicine, dosage, frequency, duration, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"demo_prescription_{index:03d}", patient_id, patient_name, doctor_id, doctor_name,
                    "Sample prescription (DEMO)", "Demo medication placeholder", "Demo only", "Demo only", "Demo only",
                    "SIMULATED DEMO DATA — Not a real prescription. Use doctor-entered instructions for actual care.", now,
                ),
            )
            status = "PAID" if index % 2 == 0 else "UNPAID"
            db.execute(
                "INSERT OR IGNORE INTO bills (bill_id, patient_id, patient_name, description, amount, currency, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"demo_bill_{index:03d}", patient_id, patient_name, "Demo consultation bill",
                    float(450 + index * 125), "₹", status, now, now,
                ),
            )


def _as_dicts(rows) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def get_patient_records(patient_id: str) -> Dict[str, List[Dict[str, Any]]]:
    initialize_health_records_db()
    with _connect() as db:
        reports = _as_dicts(db.execute("SELECT * FROM medical_reports WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)))
        medicines = _as_dicts(db.execute("SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)))
        bills = _as_dicts(db.execute("SELECT * FROM bills WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)))
    return {"reports": reports, "medicines": medicines, "bills": bills}


def get_doctor_records(doctor_id: str, patient_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    initialize_health_records_db()
    if not patient_ids:
        return {"reports": [], "medicines": []}
    marks = ",".join("?" for _ in patient_ids)
    with _connect() as db:
        reports = _as_dicts(db.execute(f"SELECT * FROM medical_reports WHERE doctor_id = ? AND patient_id IN ({marks}) ORDER BY created_at DESC", [doctor_id, *patient_ids]))
        medicines = _as_dicts(db.execute(f"SELECT * FROM prescriptions WHERE doctor_id = ? AND patient_id IN ({marks}) ORDER BY created_at DESC", [doctor_id, *patient_ids]))
    return {"reports": reports, "medicines": medicines}


def add_clinical_record(record_type: str, patient_id: str, doctor_id: str, doctor_name: str, patient_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    record_id = f"rec_{uuid.uuid4().hex[:16]}"
    if record_type == "report":
        item = {"record_id": record_id, "patient_id": patient_id, "patient_name": patient_name, "doctor_id": doctor_id, "doctor_name": doctor_name, "title": str(record.get("title", "")).strip(), "report_type": str(record.get("report_type") or "Clinical report").strip(), "indication": str(record.get("indication", "")).strip(), "findings": str(record.get("findings") or record.get("details", "")).strip(), "impression": str(record.get("impression", "")).strip(), "recommendations": str(record.get("recommendations", "")).strip(), "details": str(record.get("findings") or record.get("details", "")).strip(), "report_date": str(record.get("report_date", "")), "created_at": now}
        with _connect() as db:
            db.execute("INSERT INTO medical_reports (record_id, patient_id, patient_name, doctor_id, doctor_name, title, details, report_date, created_at, report_type, indication, findings, impression, recommendations) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(item[key] for key in ("record_id", "patient_id", "patient_name", "doctor_id", "doctor_name", "title", "details", "report_date", "created_at", "report_type", "indication", "findings", "impression", "recommendations")))
    else:
        medicine = str(record.get("medicine") or record.get("title", "")).strip()
        item = {"record_id": record_id, "patient_id": patient_id, "patient_name": patient_name, "doctor_id": doctor_id, "doctor_name": doctor_name, "title": medicine, "medicine": medicine, "strength": str(record.get("strength", "")).strip(), "dosage": str(record.get("dosage", "")).strip(), "route": str(record.get("route", "")).strip(), "frequency": str(record.get("frequency", "")).strip(), "duration": str(record.get("duration", "")).strip(), "quantity": str(record.get("quantity", "")).strip(), "refills": str(record.get("refills", "0")).strip(), "diagnosis": str(record.get("diagnosis", "")).strip(), "instructions": str(record.get("instructions") or record.get("details", "")).strip(), "issued_date": str(record.get("issued_date") or now[:10]), "details": str(record.get("instructions") or record.get("details", "")).strip(), "created_at": now}
        with _connect() as db:
            db.execute("INSERT INTO prescriptions (record_id, patient_id, patient_name, doctor_id, doctor_name, title, medicine, dosage, frequency, duration, details, created_at, strength, route, quantity, refills, diagnosis, instructions, issued_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(item[key] for key in ("record_id", "patient_id", "patient_name", "doctor_id", "doctor_name", "title", "medicine", "dosage", "frequency", "duration", "details", "created_at", "strength", "route", "quantity", "refills", "diagnosis", "instructions", "issued_date")))
    return item


def update_clinical_record(record_type: str, patient_id: str, doctor_id: str, record_id: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a report or prescription only when it belongs to this doctor and patient."""
    initialize_health_records_db()
    table = "medical_reports" if record_type == "report" else "prescriptions" if record_type == "medicine" else None
    if table is None:
        return None

    if record_type == "report":
        values = (
            str(record.get("title", "")).strip(),
            str(record.get("findings") or record.get("details", "")).strip(),
            str(record.get("report_date", "")).strip(),
            str(record.get("report_type") or "Clinical report").strip(),
            str(record.get("indication", "")).strip(),
            str(record.get("impression", "")).strip(),
            str(record.get("recommendations", "")).strip(),
            record_id,
            patient_id,
            doctor_id,
        )
        statement = f"UPDATE {table} SET title = ?, details = ?, report_date = ?, report_type = ?, indication = ?, findings = ?, impression = ?, recommendations = ? WHERE record_id = ? AND patient_id = ? AND doctor_id = ?"
    else:
        medicine = str(record.get("medicine") or record.get("title", "")).strip()
        values = (
            medicine,
            medicine,
            str(record.get("strength", "")).strip(),
            str(record.get("dosage", "")).strip(),
            str(record.get("route", "")).strip(),
            str(record.get("frequency", "")).strip(),
            str(record.get("duration", "")).strip(),
            str(record.get("quantity", "")).strip(),
            str(record.get("refills", "0")).strip(),
            str(record.get("diagnosis", "")).strip(),
            str(record.get("instructions") or record.get("details", "")).strip(),
            str(record.get("instructions") or record.get("details", "")).strip(),
            record_id,
            patient_id,
            doctor_id,
        )
        statement = f"UPDATE {table} SET title = ?, medicine = ?, strength = ?, dosage = ?, route = ?, frequency = ?, duration = ?, quantity = ?, refills = ?, diagnosis = ?, instructions = ?, details = ? WHERE record_id = ? AND patient_id = ? AND doctor_id = ?"

    with _connect() as db:
        cursor = db.execute(statement, values)
        if cursor.rowcount == 0:
            return None
        row = db.execute(
            f"SELECT * FROM {table} WHERE record_id = ? AND patient_id = ? AND doctor_id = ?",
            (record_id, patient_id, doctor_id),
        ).fetchone()
        return dict(row) if row else None


def get_all_bills() -> List[Dict[str, Any]]:
    initialize_health_records_db()
    with _connect() as db:
        return _as_dicts(db.execute("SELECT * FROM bills ORDER BY created_at DESC"))


def add_bill(patient_id: str, patient_name: str, description: str, amount: float, currency: str = "₹", status: str = "UNPAID", details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    details = details or {}
    lines = details.get("line_items") or [{"description": description, "quantity": 1, "unit_price": float(amount), "total": float(amount)}]
    item = {"bill_id": f"bill_{uuid.uuid4().hex[:16]}", "patient_id": patient_id, "patient_name": patient_name, "description": description, "amount": float(amount), "subtotal": float(details.get("subtotal", amount)), "tax": float(details.get("tax", 0)), "currency": currency, "service_date": str(details.get("service_date") or now[:10]), "due_date": str(details.get("due_date", "")), "provider_name": str(details.get("provider_name") or "MetroHealth Hospital"), "payment_method": str(details.get("payment_method", "")), "line_items": json.dumps(lines, ensure_ascii=False), "status": status, "created_at": now, "updated_at": now}
    with _connect() as db:
        db.execute("INSERT INTO bills (bill_id, patient_id, patient_name, description, amount, subtotal, tax, currency, service_date, due_date, provider_name, payment_method, line_items, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(item.values()))
    return item


def set_bill_status(bill_id: str, status: str) -> Optional[Dict[str, Any]]:
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    with _connect() as db:
        cursor = db.execute("UPDATE bills SET status = ?, updated_at = ? WHERE bill_id = ?", (status, now, bill_id))
        if cursor.rowcount == 0:
            return None
        row = db.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,)).fetchone()
        return dict(row)


def update_bill_details(bill_id: str, description: str, amount: float) -> Optional[Dict[str, Any]]:
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    with _connect() as db:
        current = db.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,)).fetchone()
        if not current:
            return None
        tax = float(current["tax"] or 0)
        subtotal = max(float(amount) - tax, 0)
        lines = [{"description": description, "quantity": 1, "unit_price": subtotal, "total": subtotal}]
        cursor = db.execute(
            "UPDATE bills SET description = ?, amount = ?, subtotal = ?, line_items = ?, updated_at = ? WHERE bill_id = ?",
            (description, float(amount), subtotal, json.dumps(lines, ensure_ascii=False), now, bill_id),
        )
        if cursor.rowcount == 0:
            return None
        row = db.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,)).fetchone()
        return dict(row) if row else None


def update_bill_refund_state(bill_id: str, refund_status: str, refund_note: str) -> Optional[Dict[str, Any]]:
    initialize_health_records_db()
    now = datetime.utcnow().isoformat()
    with _connect() as db:
        cursor = db.execute(
            "UPDATE bills SET refund_status = ?, refund_note = ?, refund_updated_at = ?, updated_at = ? WHERE bill_id = ?",
            (refund_status, refund_note, now, now, bill_id),
        )
        if cursor.rowcount == 0:
            return None
        row = db.execute("SELECT * FROM bills WHERE bill_id = ?", (bill_id,)).fetchone()
        return dict(row) if row else None
