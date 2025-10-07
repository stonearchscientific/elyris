# Elyris — personal care mesh (MVP)

Prototype monorepo for Elyris (local dev). FastAPI backend + React frontend.  
Backend stores canonical Person, Document, Event plus simple ERP, CRM, EHR, LMS routers. SQLite for dev.

## Quick start (local, Python)
# from backend/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/seed_db.py
uvicorn app.main:app --reload --port 8000

# from frontend/
npm install
npm run dev

Open frontend at http://localhost:5173, backend at http://localhost:8000/docs
