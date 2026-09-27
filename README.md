# GenAI-Based Customer Care & Complaint Resolution System

An end-to-end healthcare customer-care capstone that classifies patient requests, answers supported questions from hospital reference material, routes complaints into staff queues, and lets patients follow each ticket through resolution (`MED-2026-XXXXX`).

> **Medical Safety Disclaimer**: This system is a **customer-care and complaint-management capstone**. It does **NOT** diagnose medical conditions, prescribe drugs, alter treatment dosages, or make clinical decisions. Critical concerns are flagged in the doctor queue and the patient sees emergency guidance. The app does not page or notify clinicians; emergencies must go to local emergency services.

---

## 🚀 Key Features

- **AI Intent & Severity Engine**:
  - Classifies queries into categories (Billing, Appointments, Patient Safety, Service, Insurance, Medical Records).
  - Determines severity level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - Chooses execution action: `AUTO_RESOLVE`, `CREATE_TICKET`, or `CRITICAL_ESCALATION`.
- **RAG Knowledge Base Pipeline**:
  - Indexed using `sentence-transformers/all-MiniLM-L6-v2` and `FAISS` vector store over hospital policy knowledge base documents.
  - Grounds routine answers in the hospital reference documents and offers a safe fallback when verified information is unavailable.
- **Support Ticket Management (`MED-2026-XXXXX`)**:
  - Automatically creates and stores tickets in MongoDB when human intervention is required.
  - Full lifecycle tracking with an activity history: `OPEN` ➔ `ASSIGNED` ➔ `IN_PROGRESS` ➔ `RESOLVED` ➔ `CLOSED`.
- **Critical Safety Routing**:
  - Flags medication errors and urgent safety reports as `CRITICAL` in the clinical queue.
  - Displays emergency guidance and medical-safety disclaimers; it does not contact emergency services or page a clinician.
- **Admin Dashboard & Live Analytics**:
  - Admins see every eligible non-clinical ticket, with queue data refreshed every 15 seconds.
  - Metric cards and charts use persisted interaction and ticket data; empty databases show zero, not sample counts.
  - Search, filter, and sort ticket console with modal controls for staff assignment and resolution notes.
  - Interactive Recharts graphics showing category breakdowns, severity distribution, auto-resolution rates, and monthly trends.
- **Admin service desk**: Admins manage appointment, billing and refund, insurance, service and staff, account and portal, and privacy or security requests. Doctors own treatment, patient safety, and medical record correction tickets.
- **Chat-first patient workflow**: Patients use the chatbot for appointment actions, personal reports, medicines, bills, and complaint status. Medical concerns route to a doctor queue; non-medical issues route to the admin queue.
- **Patient care hub**: Patients can review upcoming and past visits, reschedule or cancel eligible appointments, check live appointment availability, and download calendar invites. A unified search covers reports, prescriptions, and bills.
- **Support request tracking**: Patients can filter requests by status and expand each request to review its activity timeline, assigned team, and staff updates. Patient, doctor, and admin views refresh every 15 seconds.
- **Role-scoped records**: Patients see their own records; doctors see reports and prescriptions for their assigned patients; the single admin manages billing and non-medical complaints.

---

## 🛠️ Technology Stack

- **Frontend**: React 18, Vite, Tailwind CSS, React Router v6, Axios, Recharts, Lucide Icons.
- **Backend**: Python 3.14 / 3.10+, FastAPI, Pydantic v2, PyJWT, Passlib / SHA256 Hashing.
- **Database**: MongoDB Atlas / PyMongo for appointments and support workflows (with a mongomock local demo fallback), plus persistent local SQLite storage at `backend/database/patient_records.sqlite3` for reports, prescriptions, and bills.
- **AI & RAG**: FAISS (`faiss-cpu`), Sentence Transformers (`all-MiniLM-L6-v2`), Hugging Face Inference API.

---

## 📁 Project Structure

```text
genai-customer-care/
├── frontend/
│   ├── src/
│   │   ├── components/       # Navbar, Sidebar, AppointmentManager, TicketModal, TicketStatusBadge
│   │   ├── pages/            # Login, Register, CustomerDashboard, ChatPage, AdminDashboard, AnalyticsPage
│   │   ├── context/          # AuthContext.jsx
│   │   ├── services/         # api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── backend/
│   ├── api/                  # auth.py, chat.py, complaints.py, tickets.py, appointments.py, analytics.py
│   ├── models/ & schemas/    # schemas.py
│   ├── services/             # decision_engine.py, ticket_service.py
│   ├── ai/                   # intent_classifier.py
│   ├── rag/                  # vector_store.py, rag_pipeline.py
│   ├── database/             # connection.py
│   ├── utils/                # security.py
│   ├── main.py
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── knowledge_base/           # hospital_info.md, departments_doctors.md, policies_refunds.md, billing_insurance.md, report_access_faq.md
├── scripts/                  # seed_database.py, test_demo_scenarios.py
├── README.md
└── .gitignore
```

---

## ⚙️ Environment Variables

The backend loads configuration from `backend/.env`.

Required variables:

```env
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/metrohealth?retryWrites=true&w=majority
JWT_SECRET=super_secret_genai_customer_care_jwt_key_2026_99482716
```

> *Note*: If `MONGO_URI` is unavailable and local MongoDB is offline, the backend uses `mongomock` and saves its demo snapshot to `backend/database/mongo_fallback.json` so demo tickets, appointments, and chat history survive a restart. SQLite patient records are stored separately.

---

## 🔑 Demo Login Credentials

| Role | Email | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Customer** | `john.doe@example.com` | `Password123!` | AI Chat, Dashboard, Appointments, My Tickets |
| **Admin** | `admin@metrohealth.org` | `Password123!` | Billing, non-medical ticket resolution, analytics |
| **Doctor (Dr. Ravi)** | `doctor.ravi@metrohealth.org` | `Password123!` | Doctor portal with appointments assigned to Dr. Ravi |

Demo doctor accounts are seeded for each doctor using `doctor.<doctor-id>@metrohealth.org` with the same demo password. For example, Dr. Kumar signs in as `doctor.kumar@metrohealth.org`. Each doctor can view their own schedule, records for assigned patients, and medical concern queue. Chat bookings collect the patient's full name and date of birth and include those details in the doctor's appointment view. Public registration creates patient accounts only; staff accounts are seeded or provisioned outside public registration.

---

## 🧪 Required Test Scenarios

The system exercises these five demonstration scenarios. Appointment rescheduling requests route to the appointment workflow, not a generic FAQ response:

| # | Customer Input Query | Intent / Category | Expected Action | Expected Severity |
| :--- | :--- | :--- | :--- | :--- |
| **1** | *"What are the hospital timings?"* | `hospital_timings` / `information` | `AUTO_RESOLVE` | `LOW` |
| **2** | *"I want to reschedule my appointment."* | `reschedule_appointment` / `appointment` | `APPOINTMENT_AGENT` | `LOW` |
| **3** | *"My bill amount is incorrect."* | `wrong_billing` / `billing` | `CREATE_TICKET` | `HIGH` |
| **4** | *"My refund has not arrived."* | `delayed_refund` / `billing` | `CREATE_TICKET` | `HIGH` |
| **5** | *"I received the wrong medication."* | `medication_error` / `patient_safety` | `CRITICAL_ESCALATION` | `CRITICAL` |

---

## 🚀 How to Run the Application

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (optional)
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Seed Demo Database (10 Patients, 5 Doctors, 15 Appointments, 20 Tickets, and patient record samples)
python ../scripts/seed_database.py

# Run FastAPI Server
uvicorn main:app --reload --port 8000
```

The seeded reports, prescription entries, bills, users, and appointment catalog are simulated demo data for the capstone walkthrough. They are not real patient records or medical instructions. Doctors can review and edit records for patients with appointments assigned to them; the patient portal reflects those updates. Appointment confirmation messages are previews only, no SMS is sent, and no online payment or refund processor is connected.

FastAPI interactive documentation will be available at: `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

Open a second terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite Development Server
npm run dev
```

The web dashboard will be available at: `http://localhost:5173`.

### 3. Run Scenario Verification Suite

```bash
python scripts/test_demo_scenarios.py
```

---

## 📊 Walkthrough & Demo Flow

1. **Sign In**: Log in as Customer (`john.doe@example.com`) or Admin (`admin@metrohealth.org`) using the quick demo login shortcuts.
2. **Patient Care Hub**: Review visits, search reports and prescriptions, check bills, and expand support requests to see team updates.
3. **Appointment Management**: Download a calendar invite for the next visit, or reschedule by checking open slots and selecting a new time. Eligible appointments can also be cancelled.
4. **AI Chat Assistant**: Open `/chat` and type queries or click suggested questions.
5. **Auto Resolution**: Queries like *"What are the hospital timings?"* yield instant RAG-grounded answers.
6. **Ticket Creation**: Queries like *"My bill amount is incorrect"* generate support tickets (`MED-2026-XXXXX`).
7. **Follow a complaint to closure**: Open an admin ticket, assign it to a department and staff member, move it through `IN_PROGRESS` to `RESOLVED`, and add the resolution note. The patient sees the same status and update in Support Requests.
8. **Critical Safety Routing**: Queries like *"I received the wrong medication"* create a `CRITICAL` case in the doctor queue and show emergency guidance; no clinician notification is sent.
9. **Admin Management**: Admins view the console (`/admin`), see the case workflow counts, filter tickets, assign support staff, and view live analytics (`/admin/analytics`).
