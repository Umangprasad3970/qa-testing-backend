# QA Testing Platform Backend V1

FastAPI API + PostgreSQL + protected Admin Dashboard.

Local:
python -m venv .venv
Windows: .venv\Scripts\activate
Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

Admin: http://127.0.0.1:8000/admin
API docs: http://127.0.0.1:8000/docs

Render:
1. Push this folder to GitHub.
2. In Render, create a Blueprint from the repo.
3. Set ADMIN_EMAIL and ADMIN_PASSWORD.
4. Deploy.

IMPORTANT: Render currently states that Free Postgres databases expire after 30 days, so this free database is for development/testing unless upgraded before expiry.
