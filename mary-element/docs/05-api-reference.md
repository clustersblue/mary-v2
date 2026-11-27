# Mary Care Management System — API Reference Documentation

**Document File:** `docs/05-api-reference.md`  
**Base URL:** `https://api.stmarysteamcare.co.uk/api/v1` (Local: `http://localhost:8000/api/v1`)  
**Specification Standard:** OpenAPI 3.1 / JSON REST  
**Authentication Scheme:** HTTP Bearer Token (`Authorization: Bearer <token>`)  
**Version:** 1.0.0 Production  
**Date:** October 2026  

---

## 1. Global Conventions & Error Standard

### 1.1 HTTP Status Codes
| Status Code | Meaning | Typical Usage |
| :--- | :--- | :--- |
| **200 OK** | Success | Request succeeded and returned requested payload. |
| **201 Created** | Created | Resource successfully created (e.g., new shift or carer). |
| **400 Bad Request** | Validation Failure | Invalid input payload or date range violation. |
| **401 Unauthorized** | Unauthenticated | Missing, expired, or invalid bearer token. |
| **403 Forbidden** | Access Denied | Authenticated user lacks required role/permission. |
| **404 Not Found** | Missing Resource | Requested ID does not exist or has been soft-deleted. |
| **422 Unprocessable** | Schema Validation | Pydantic validation error on request parameters. |
| **500 Server Error** | Internal Exception | Unhandled backend exception or database timeout. |

### 1.2 Standard Error Response Payload
```json
{
  "detail": "Insufficient permissions. Administrator access required."
}
```

---

## 2. Authentication & Account Management (`/auth`)

### 2.1 User Login
Authenticates an existing user and issues an active bearer token.

- **Endpoint:** `POST /login`
- **Access Level:** Public (No authorization required)
- **Request Body (`application/json`):**
```json
{
  "username": "robertor",
  "password": "your-password",
  "rememberme": true
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "token": "mary_tok_2458fcf62074021b7d05c9b03e540b373a26772007a6fecf",
  "user": {
    "id": 5,
    "username": "robertor",
    "first_name": "Roberto",
    "surname": "Rivera",
    "full_name": "Roberto Rivera",
    "email": "clustersblue@gmail.com",
    "mobile_number": "07123456789",
    "user_id": "00005",
    "is_admin": 1,
    "role": 1
  },
  "message": "Login successful"
}
```
- **Error Response (`401 Unauthorized`):**
```json
{
  "detail": "Incorrect username or password. Please try again."
}
```

### 2.2 Get Current Profile
Returns profile details for the currently authenticated bearer token.

- **Endpoint:** `GET /me`
- **Access Level:** Authenticated (`Role 1, 2, 3`)
- **Headers:** `Authorization: Bearer <token>`
- **Success Response (`200 OK`):**
```json
{
  "id": 5,
  "username": "robertor",
  "first_name": "Roberto",
  "surname": "Rivera",
  "full_name": "Roberto Rivera",
  "email": "clustersblue@gmail.com",
  "is_admin": 1,
  "role": 1
}
```

### 2.3 User Logout
Invalidates the active bearer session in memory/cache.

- **Endpoint:** `POST /logout`
- **Access Level:** Authenticated (`Role 1, 2, 3`)
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### 2.4 Forgot Password Request
Dispatches a secure, 60-minute password reset link to the registered email.

- **Endpoint:** `POST /forgot-password`
- **Access Level:** Public
- **Request Body:**
```json
{
  "email": "clustersblue@gmail.com"
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "If this email is registered, a password reset link has been dispatched."
}
```

### 2.5 Reset Password
Consumes a password reset token and updates the user's bcrypt password.

- **Endpoint:** `POST /reset-password`
- **Access Level:** Public
- **Request Body:**
```json
{
  "token": "d7b2a94f8e6c...",
  "email": "clustersblue@gmail.com",
  "password": "NewSecurePassword123!",
  "password_confirmation": "NewSecurePassword123!"
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Password reset successful. You may now log in."
}
```

---

## 3. Executive Dashboard & Analytics (`/dashboard`)

### 3.1 Get Dashboard Metrics
Retrieves high-level operational statistics including active clients, staff count, and visit completion rates.

- **Endpoint:** `GET /dashboard-summary`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Query Parameters:** `date` (e.g. `2026-10-13`)
- **Success Response (`200 OK`):**
```json
{
  "active_service_users": 142,
  "active_carers": 86,
  "scheduled_shifts_today": 310,
  "completed_visits_today": 284,
  "compliance_rate_percent": 98.4
}
```

---

## 4. Care Rota & Shift Scheduling (`/shifts`)

### 4.1 Get Master Shift Templates
- **Endpoint:** `GET /shifts`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Success Response (`200 OK`):**
```json
[
  {
    "shift_id": 1,
    "shift": "0700-0800 MORNING",
    "time_start": "07:00:00",
    "time_end": "08:00:00",
    "hours": 1.00
  }
]
```

### 4.2 Create Master Shift Template
- **Endpoint:** `POST /shifts`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Request Body:**
```json
{
  "shift": "1800-1900 TEA",
  "time_start": "18:00:00",
  "time_end": "19:00:00",
  "hours": 1.00
}
```
- **Success Response (`201 Created`):**
```json
{
  "success": true,
  "shift_id": 14,
  "shift": "1800-1900 TEA"
}
```

### 4.3 Create User Rota Shift (Schedule Allocation)
- **Endpoint:** `POST /user-shifts`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Request Body:**
```json
{
  "user_id": 8,
  "su_id": 1,
  "shift_id": 1,
  "shift_date": "2026-10-15",
  "recurrence_rule": "WEEKLY",
  "repeat_until": "2026-12-31"
}
```
- **Success Response (`201 Created`):**
```json
{
  "success": true,
  "created_shifts_count": 11,
  "recurrence_id": "rec_91f8a2"
}
```

---

## 5. Electronic Care Monitoring & Attendance (`/attendance`)

### 5.1 Carer Clock-In (`time_in`)
Records a verified arrival event with GPS coordinates.

- **Endpoint:** `POST /time_in`
- **Access Level:** All Authenticated Roles (`Role 1, 2, 3`)
- **Request Body:**
```json
{
  "user_id": 8,
  "su_id": 1,
  "shift_id": 1,
  "clock_in_time": "2026-10-15 07:02:15",
  "latitude": 51.5074,
  "longitude": -0.1278
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "attendance_id": 4182,
  "status": "CLOCKED_IN",
  "gps_variance_meters": 18
}
```

### 5.2 Carer Clock-Out (`time_out`)
Records visit departure time.

- **Endpoint:** `POST /time_out`
- **Access Level:** All Authenticated Roles (`Role 1, 2, 3`)
- **Request Body:**
```json
{
  "attendance_id": 4182,
  "clock_out_time": "2026-10-15 08:01:40"
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "attendance_id": 4182,
  "status": "COMPLETED",
  "duration_hours": 0.99
}
```

### 5.3 Generate Clinical Care Note PDF
Synthesizes a structured visit outcome into an official NHS-styled PDF.

- **Endpoint:** `POST /care-notes/generate`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Request Body:**
```json
{
  "attendance_id": 4182,
  "client_name": "Arthur Pendelton",
  "carer_name": "Gemma Agustin",
  "shift_time": "07:00 - 08:00",
  "date": "15.10.2026",
  "personal_care": true,
  "medication_administered": true,
  "nutrition_notes": "Assisted with breakfast (toast and tea). Drank 250ml fluids.",
  "general_wellbeing": "Alert, cheerful, and resting comfortably."
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "filename": "su_00001_ARTHURPENDELTON_CARE_NOTE_0700-0800_15.10.26.pdf",
  "download_url": "/api/v1/care-notes/view/su_00001_ARTHURPENDELTON_CARE_NOTE_0700-0800_15.10.26.pdf"
}
```

---

## 6. Daily Time Record (DTR) Reconciliation (`/dtr`)

### 6.1 Get Attendance Timesheet Report
- **Endpoint:** `POST /attendances/report`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Request Body:**
```json
{
  "start_date": "2026-10-01",
  "end_date": "2026-10-15",
  "carer_id": null,
  "su_id": null
}
```
- **Success Response (`200 OK`):**
```json
[
  {
    "attendance_id": 4182,
    "carer_full_name": "Gemma Agustin",
    "su_full_name": "Arthur Pendelton",
    "occurrence_date": "2026-10-15",
    "clock_in": "07:02",
    "clock_out": "08:01",
    "variance_minutes": 1,
    "status": "Verified"
  }
]
```

### 6.2 Reset Attendance Row
- **Endpoint:** `POST /attendances/reset`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Request Body:**
```json
{
  "attendance_id": 4182
}
```
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Clock times reset successfully"
}
```

---

## 7. Finance, Payroll & Invoicing (`/finance`)

### 7.1 Get Service User Transactions (Unbatched Shifts)
- **Endpoint:** `GET /getaserviceusertransactions`
- **Access Level:** Finance Staff & Admin (`has_finance_access`)
- **Query Parameters:** `param` (0=Payroll, 1=Invoice), `selectionList` (ID), `dates` (Array of YYYY-MM-DD)
- **Success Response (`200 OK`):**
```json
[
  {
    "id": 9201,
    "carer_id": 8,
    "carer_name": "Gemma Agustin",
    "su_id": 1,
    "su_name": "Arthur Pendelton",
    "start": "2026-10-15 07:00:00",
    "end": "2026-10-15 08:00:00",
    "hours": 1.0,
    "rate": 14.50,
    "total_pay": 14.50
  }
]
```

### 7.2 Get Finalized Payroll Batches
- **Endpoint:** `GET /getpayrolls`
- **Access Level:** Finance Staff & Admin (`has_finance_access`)
- **Success Response (`200 OK`):**
```json
[
  {
    "id": 45,
    "payroll_number": "PAY-2026-W41",
    "carer_id": 8,
    "carer_name": "Gemma Agustin",
    "total_hours": 37.5,
    "total_amount": 543.75,
    "period_start": "2026-10-01",
    "period_end": "2026-10-07",
    "status": "Finalized"
  }
]
```

### 7.3 Get Finalized Client Invoices
- **Endpoint:** `GET /getinvoices`
- **Access Level:** Finance Staff & Admin (`has_finance_access`)
- **Success Response (`200 OK`):**
```json
[
  {
    "id": 82,
    "invoice_number": "INV-2026-0082",
    "su_id": 1,
    "su_name": "Arthur Pendelton",
    "commissioner": "Private / Direct",
    "total_amount": 825.00,
    "status": "Issued"
  }
]
```

---

## 8. Management: Staff & Service Users

### 8.1 Delete Carer Staff Profile
- **Endpoint:** `DELETE /carers/{id}`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Carer profile soft-deleted successfully"
}
```

### 8.2 Delete Service User Record
- **Endpoint:** `DELETE /service-users/{id}`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "message": "Service user soft-deleted successfully"
}
```

### 8.3 Export UK GDPR Article 15 SAR Dossier
- **Endpoint:** `POST /service-users/{su_id}/sar-export`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Query Parameters:** `format` (`xlsx` or `pdf`)
- **Success Response (`200 OK`):**
```json
{
  "success": true,
  "patient_name": "Arthur Pendelton",
  "file_name": "SAR_DOSSIER_SU-001_Arthur_Pendelton_20261013.xlsx",
  "download_url": "/api/v1/sar-export/download/SAR_DOSSIER_SU-001_Arthur_Pendelton_20261013.xlsx"
}
```

---

## 9. Master Data & Pricing Rates (`/master_data`)

### 9.1 Get Service User Rates Matrix
- **Endpoint:** `GET /getsurates`
- **Access Level:** Staff & Admin (`Role 1, 2`)
- **Success Response (`200 OK`):**
```json
[
  {
    "su_id": 1,
    "su_full_name": "Arthur Pendelton",
    "shift_id": 1,
    "shift": "0700-0800 MORNING",
    "id": 12,
    "rate": 14.50,
    "invoice": 22.00
  }
]
```

### 9.2 Upsert Service User Rate (Modify Pricing)
- **Endpoint:** `POST /savesurate`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Request Body:**
```json
{
  "su_id": 1,
  "shift_id": 1,
  "rate": 15.00,
  "invoice": 23.50
}
```
- **Success Response (`200 OK` or `201 Created`):**
```json
{
  "success": true,
  "data": {
    "id": 12,
    "su_id": 1,
    "shift_id": 1,
    "rate": 15.00,
    "invoice": 23.50
  }
}
```

### 9.3 Create Agency Branch
- **Endpoint:** `POST /branches`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Request Body:**
```json
{
  "branch": "London Central Branch",
  "address": "100 Oxford Street, London",
  "contact_number": "020 7946 0000"
}
```
- **Success Response (`201 Created`):**
```json
{
  "success": true,
  "id": 5,
  "name": "London Central Branch"
}
```

---

## 10. UK GDPR Article 9 Audit Logging (`/audit`)

### 10.1 Query Audit Logs
- **Endpoint:** `GET /audit/logs`
- **Access Level:** Super Administrator (`Role 1` or `is_admin: 1`)
- **Query Parameters:** `limit` (Default 200), `su_id` (Optional)
- **Success Response (`200 OK`):**
```json
[
  {
    "id": 341,
    "user_id": 5,
    "username": "robertor",
    "su_id": 1,
    "patient_name": "Arthur Pendelton",
    "record_type": "medical_dossier",
    "action": "VIEW",
    "details": "Viewed clinical assessment and allergy history",
    "ip_address": "192.168.1.45",
    "created_at": "2026-10-13T20:15:30"
  }
]
```
