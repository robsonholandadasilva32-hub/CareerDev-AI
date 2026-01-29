# Technical Debt & Known Issues

## Critical Performance Issues
- **AuthMiddleware Blocking**: `app/middleware/auth.py` is defined as `async def dispatch`, but it performs synchronous database operations (`db.query(User)...`, `db.commit()`). This blocks the main event loop for *every* authenticated request, limiting concurrency.
  - **Remediation**: Refactor `AuthMiddleware` to use `async/await` with `asyncpg` or run blocking calls in a threadpool (`run_in_threadpool`).

## Data Model Inconsistencies
- **Duplicate AuditLog Models**: `AuditLog` is defined in both `app/db/models/audit.py` (Forensic/System logs) and `app/db/models/security.py` (Admin/Activity logs).
  - Both map to the same `audit_logs` table but have different columns. This is a schema collision.
  - **Action Taken**: I commented out the `user` relationship in `security.py` to prevent mapper conflicts, but the underlying model duplication must be resolved.
- **User Model Fields**: The `User` model in `app/db/models/user.py` was missing `github_id` and `linkedin_id` columns, causing runtime errors in onboarding logic.
  - **Action Taken**: I added these columns to the model.
- **Test Inconsistencies**: `app/tests/test_perf_career.py` instantiated `User` with fields (`is_profile_completed`, `is_premium`, `subscription_status`) that do not exist in the `User` model.
  - **Action Taken**: I updated the test to verify `full_name` and removed invalid fields. Other tests may also rely on these phantom fields.

## Code Quality
- **Missing Imports**: `app/services/career_engine.py` was trying to import `MLRiskLog` from `app.db.models.career` where it did not exist.
  - **Action Taken**: Fixed import to point to `app.db.models.ml_risk_log`.
