from fastapi import APIRouter, Depends
from app.api.v1.endpoints import auth, master_data, users, service_users, shifts, attendance, dashboard, finance, audit, records
from app.core.security import get_current_active_user, get_current_admin_user, get_current_finance_user

api_router = APIRouter()

# Authentication & Password Recovery router (Public endpoints /login, /forgot-password, /reset-password)
# Protected endpoints inside auth (/me, /logout, /updateaccount) carry individual security dependencies
api_router.include_router(auth.router, tags=["Authentication & Password Management"])

# Protected API Routers with RBAC Guards
api_router.include_router(
    dashboard.router,
    dependencies=[Depends(get_current_admin_user)],
    tags=["Dashboard Statistics"]
)
api_router.include_router(
    master_data.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Master Data"]
)
api_router.include_router(
    users.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Carers / Users"]
)
api_router.include_router(
    service_users.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Service Users / Patients"]
)
api_router.include_router(
    records.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Service User and Carer Records"]
)
api_router.include_router(
    shifts.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Shifts & Scheduling"]
)
api_router.include_router(
    attendance.router,
    dependencies=[Depends(get_current_active_user)],
    tags=["Attendance, GPS & Care Notes"]
)
api_router.include_router(
    finance.router,
    dependencies=[Depends(get_current_finance_user)],
    tags=["Finance, Payroll & Invoicing"]
)
api_router.include_router(
    audit.router,
    dependencies=[Depends(get_current_admin_user)],
    tags=["UK GDPR & Article 9 Audit Logging"]
)

