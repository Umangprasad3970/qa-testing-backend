# QA Testing Platform - Final Backend

## Deploy
Deploy this folder to the existing Render web service:
https://qa-testing-api.onrender.com/

Build command:
pip install -r requirements.txt

Start command:
uvicorn main:app --host 0.0.0.0 --port $PORT

## Required Render environment variables
- DATABASE_URL (Render PostgreSQL connection string)
- JWT_SECRET (generate a secure value)
- ADMIN_EMAIL
- ADMIN_PASSWORD

No OpenAI API key is required. The QA scenario generator is local (TF-IDF + Logistic Regression + QA scenario engine).

## Admin
- Login: POST /api/auth/login
- Dashboard: /api/admin/dashboard
- Users: /api/admin/users
- Projects: /api/admin/projects
- Test cases: /api/admin/test-cases
- Test runs: /api/admin/test-runs
- Test results: /api/admin/test-results
- Project reports: /api/admin/project-reports
- Admin UI: /admin

## User/client login
Admin-created users are stored in the same PostgreSQL database and can log into the Android/Windows client using:
POST /api/auth/client-login?client_type=android
or
POST /api/auth/client-login?client_type=windows

Admin accounts are rejected by client-login. Inactive users are rejected.

## Ownership/security
User project, document, test-case, test-run and report endpoints validate that the authenticated user owns the project. Admin endpoints require an administrator JWT.


## Cross-browser automation
The automated runner supports Chrome (Chromium), Firefox, Safari-compatible WebKit, and Opera when an Opera executable is configured. Render/Linux can run Chromium, Firefox and WebKit; Apple's Safari application itself cannot be launched on Linux. For Opera, set OPERA_EXECUTABLE_PATH where Opera is installed. The API records browser per result and exposes browser-by-browser reports.

Run endpoint accepts JSON: {"project_id": 1, "browsers": ["chrome", "firefox", "safari", "opera"]}.
