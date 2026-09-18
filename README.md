# QA Testing Platform Backend — V4 User/Admin Access

FastAPI backend for the QA Testing Platform with local QA AI, strict user isolation, and administrator user/work management.

## Access model
- Administrator accounts are created from `ADMIN_EMAIL` / `ADMIN_PASSWORD` and are intended for the web Admin console.
- Admins create normal users. Public self-registration is disabled.
- Normal users can sign in to the Android/mobile app and Windows software through `POST /api/auth/client-login` using `client_type=android` or `client_type=windows`.
- Admin accounts are rejected by the client-login endpoint.
- Inactive users are rejected from login.
- Every project/document/test case/run/report endpoint is scoped to the authenticated user's own projects.
- Admin endpoints can view and manage all users and all user work.

## Admin user management
- `POST /api/admin/users` — create user
- `GET /api/admin/users` — list users
- `GET /api/admin/users/{id}` — view user
- `PUT /api/admin/users/{id}` — edit name/email/password
- `PATCH /api/admin/users/{id}/status` — activate/deactivate
- `DELETE /api/admin/users/{id}` — delete user and all owned QA work
- `GET /api/admin/users/{id}/work` — view the user's projects and latest report summaries
- Existing admin lists expose all projects, test cases, test runs and test results.

No OpenAI API key is required.
