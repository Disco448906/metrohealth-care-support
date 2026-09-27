import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Ensure backend root and project root are in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _current_dir not in sys.path:
    sys.path.append(_current_dir)
if _parent_dir not in sys.path:
    sys.path.append(_parent_dir)

load_dotenv()

from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.complaints import router as complaints_router
from backend.api.tickets import router as tickets_router
from backend.api.appointments import router as appointments_router
from backend.api.analytics import router as analytics_router
from backend.api.patient_records import router as patient_records_router
from backend.api.admin_support import router as admin_support_router
from backend.rag.vector_store import vector_store
from backend.database.connection import get_db
from backend.database.health_records import initialize_health_records_db, seed_demo_health_records
from scripts.seed_database import seed_db, ensure_doctor_accounts, ensure_single_admin_account

app = FastAPI(
    title="GenAI Healthcare Customer Care & Complaint Resolution System",
    version="1.0.0",
    description="Automated AI Customer Support, Intent Classification, RAG Knowledge Base, and Complaint Escalation Platform"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(complaints_router)
app.include_router(tickets_router)
app.include_router(appointments_router)
app.include_router(analytics_router)
app.include_router(patient_records_router)
app.include_router(admin_support_router)

@app.on_event("startup")
def on_startup():
    print("--- Starting GenAI Customer Care Backend ---")
    try:
        initialize_health_records_db()
    except Exception as e:
        print(f"Patient records database initialization error: {e}")
    # Initialize FAISS / RAG Vector Store
    try:
        vector_store.load_and_index()
    except Exception as e:
        print(f"Vector Store Indexing error on startup: {e}")

    # Seed Database if empty
    try:
        db = get_db()
        if db["users"].count_documents({}) == 0:
            print("Database empty. Seeding initial demo data...")
            seed_db()
        else:
            added_doctors = ensure_doctor_accounts()
            ensure_single_admin_account()
            if added_doctors:
                print(f"Added {added_doctors} doctor portal accounts.")
    except Exception as e:
        print(f"Auto-seed error on startup: {e}")

    try:
        seed_demo_health_records()
    except Exception as e:
        print(f"Patient records demo seed error: {e}")

@app.get("/")
def root():
    return {
        "status": "online",
        "system": "GenAI Healthcare Customer Care & Complaint Resolution System",
        "version": "1.0.0",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    app_target = "backend.main:app" if os.path.exists(os.path.join(os.getcwd(), "backend")) else "main:app"
    uvicorn.run(app_target, host="127.0.0.1", port=8000, reload=True)
