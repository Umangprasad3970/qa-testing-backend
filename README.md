# QA Testing Platform Backend V4

FastAPI backend with user/admin RBAC, local QA AI, document upload, test-case generation, automated smoke testing, project reports, and a dedicated multi-page admin panel.

## Admin panel
- `/admin` — Admin login + dashboard
- `/admin/users` — User Management
- `/admin/projects` — Project List
- `/admin/test-cases` — Test Cases
- `/admin/test-results` — Test Case Results
- `/admin/project-reports` — Project Report Summary

Admin must log in first. The browser stores an admin JWT and every admin API requires that JWT plus `is_admin=true` on the server.

## Admin APIs
- `POST /api/auth/login`
- `GET /api/admin/dashboard`
- `POST /api/admin/users`
- `GET /api/admin/users`
- `GET /api/admin/users/{id}`
- `GET /api/admin/users/{id}/work`
- `PUT /api/admin/users/{id}`
- `PATCH /api/admin/users/{id}/status`
- `DELETE /api/admin/users/{id}`
- `GET /api/admin/projects`
- `DELETE /api/admin/projects/{id}`
- `GET /api/admin/projects/{id}/report`
- `GET /api/admin/project-reports`
- `GET /api/admin/test-cases`
- `DELETE /api/admin/test-cases/{id}`
- `GET /api/admin/test-results`

## User isolation
Client users authenticate with `/api/auth/client-login?client_type=android` or `windows`. Admin accounts are rejected from those clients. Project/document/test-case/run/report routes verify the authenticated user's `user_id` against the project owner, so changing IDs cannot expose another user's work.

No OpenAI API key is required. The local QA AI uses the bundled NLP/ML engine.
