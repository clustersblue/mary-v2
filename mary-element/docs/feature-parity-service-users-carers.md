# Feature parity: Service Users and Carers

**Date:** 19 October 2026

**Legacy sources**

- `C:\Apache24\htdocs\mary-view\src\views\pages\SettingsServiceUsers.vue`
- `C:\Apache24\htdocs\mary-view\src\views\pages\SettingsCarers.vue`
- Laravel controllers those screens call (`MServiceUsersController`, `User` carer save, `UploadController`, notes, conditions, care types, training, requirements, DTR)

**New screens**

- `C:\Projects\Mary\mary-view-element\src\views\management\ServiceUsersView.vue`
- `C:\Projects\Mary\mary-view-element\src\views\management\CarersView.vue`

Both management routes and the settings routes (`settings/service-users`, `settings/carers`) load these views. The stub settings pages in the new app were left unchanged.

**Record API**

- `C:\Projects\Mary\mary-api-fastapi\app\api\v1\endpoints\records.py`
- Expanded carer and service-user schemas in `app/schemas/user.py` and `app/schemas/service_user.py`

Staff roles 1 and 2 can use the record routes. Delete of a service user or carer stays admin-only, matching the FastAPI guards.

## Legacy feature inventory

### Service users

| Area | Legacy behaviour |
| --- | --- |
| List | Add, refresh, PrimeVue global search, session table state (`dt-state-su-session`), CSV of every visible column |
| Columns | Status, SU number, last name, first name, preferred name, age, gender, branch, plus address, phone, and other personal columns that the table exposed |
| Create | `POST` service user. Status is forced to 1. SU number is assigned by the server and is not typed on create |
| Update | `PUT` by `su_id`, including status and SU number |
| Delete | Confirm dialog, then delete. The button was shown to any signed-in user. A bulk-delete dialog only removed rows from the local array and was not wired to a selection |
| Personal | Branch, last name, first name, preferred name, home address, date of birth, gender, marital status, religion, nationality, contact, email, biography |
| Contacts | Next of kin name, relationship, phone, address, with a copy-home-address checkbox. Second contact uses the same shape |
| Service | Start date, end date, contract, GP lookup, NHS contact lookup |
| Health | Existing records only. Medical conditions (condition, category, diagnosis date, primary). Medical history. Home care types. Daily care selections. Medications / care-plan text (Quill). AI care plan |
| Notes | List, add, edit, delete. Empty notes rejected. Author shown |
| Documents | List by `su_{su_number}`. Upload, download, preview, delete. Preview for pdf, txt, png, jpg, jpeg, gif, webp. Word files download |
| Care plan document | From the row: load conditions, home care, daily care, notes, and open visits, then download a Word file |
| AI care plan | Confirm when text already exists. Export Word, print-to-PDF, text. Save onto the document list. Apply into the medications field, with an audit note |
| Visits | Not a tab. Open visits (status 1, payroll or invoice still empty) are loaded only for the care-plan document |
| Validation | Resolver requires SU number and status on edit, plus branch, last name, first name, home address, date of birth, gender, religion, nationality. Marital status shows a required badge but is missing from the resolver. Contact is an `InputNumber`, so leading zeros are dropped. Email is optional |

### Carers

| Area | Legacy behaviour |
| --- | --- |
| List | Add, refresh, global search across employee number, names, date of birth, address, mobile, status, gender, branch. Session table state. CSV of visible columns |
| Columns | Status, employee number, first name, surname, gender, branch, employment start, plus address, mobile, and date of birth |
| Create | Password and confirm collected. Payload sends password and forces `carer_status_id` to 1. Confirm password is not compared and is not sent |
| Update | Same personal and employment fields. Password is not sent. Username is not sent on update. Employee number is sent |
| Delete | Confirm, then delete, shown to any signed-in user. Bulk delete only filters the local array |
| Personal | Employee number (edit), branch, status, first name, surname, username, current address, date of birth, marital status, gender, nationality, mobile, resident status, email, NI number. Middle name is on the form |
| Account | Password and confirm, create only |
| Emergency | Name, number, relation, address, copy current address |
| Employment | Application date, start date, employment type, pension, contract, history, requirements checklist |
| Training | Existing carer only. Course, description, completion date, validity, status. Add, edit, delete. Course and completion date required. Status completed, pending, or failed |
| Documents | List by `id_{employee number}`. Upload, download, delete. No preview. Size check in script is 5 MB |
| Rota | Last attended visits for the carer, with CSV export. The Paid column reads `m_transactions.payroll` |
| Notes | `carer_notes` on the main record, shown when editing |
| Validation | Save does not stop on the client. Badges and `submitted` messages cover employee number, branch, first name, surname, username, current address, and date of birth. Gender and email show a required badge. Password fields are marked required on create. Marital status has `required="true"` on the control and no blocking check |

## What the new screens implement

### Service users (`ServiceUsersView.vue`)

- Add, refresh, client search, status filter, branch filter, pagination, column sort.
- Create `POST /service-users` with `service_status_id` 1. Update `PUT /service-users/{su_id}`. Empty dates are sent as null.
- Admin-only delete with confirm.
- View and edit dialog, 980px, Element Plus tabs. View mode uses `fieldset disabled` so document view and download stay usable.
- Personal, contacts (both copy-address checkboxes), and service tabs, including GP and NHS lookups.
- Health tab on an existing record: conditions, medical history, home care, daily care, medications text, services provided, AI generate.
- Notes add, edit, delete, with an empty-note block and a delete guard.
- Documents: list `GET /files/su_{number}`, upload `POST /upload` (base64), download, preview, delete. Allowed: doc, docx, pdf, txt, png, jpg, jpeg, gif, webp, html. Maximum 20 MB. Preview for pdf, txt, images, and html. Word files download. Object URLs are revoked.
- Care-plan document from the row, built from the same data the legacy document used.
- AI dialog: sanitised HTML preview, Word, print-to-PDF, text, save to documents, apply to the medications field.
- Visits tab shows the same open-visit query the care-plan document uses.
- Subject access request dialog kept: `GET /service_users/{id}/sar-data` and `GET /service_users/{id}/sar-export`.
- Required rules: branch, last name, first name, home address, date of birth, gender, marital status, religion, nationality. SU number and status required on edit. Email checked only when present. Invalid save returns to the Personal tab.

### Carers (`CarersView.vue`)

- Add, refresh, client search, status filter, branch filter, pagination, column sort.
- Create `POST /carers` with password and `carer_status_id` 1. Update `PUT /carers/{id}` without a password. Empty dates are null. Duplicate username or email surfaces the API 409.
- Admin-only delete with confirm.
- Personal, emergency (copy address), and employment tabs.
- Account tab on create only. Password and confirm must match.
- Employee number is shown, editable, and required on edit.
- Requirements checklist calls `saverequirementsstatus` or `updaterequirementsstatus/{id}`.
- Training list, add, edit, delete. Course, completion date, and status required. Completion is sent as `YYYY-MM-DD 00:00:00`.
- Documents: list `GET /carerfiles/id_{employee number}`, upload `POST /carerupload`, download, preview, delete. Maximum 5 MB. Same preview types as service users except html.
- Rota tab, last 90 attended visits, CSV export. Payroll column is the transaction payroll value.
- Notes tab on edit only. Notes save with the carer record.
- Required rules: branch, first name, surname, username, current address, date of birth, gender, email. Employee number on edit. Password and confirm on create.

### API support added for those screens

- Carer and service-user schemas accept the persisted columns used by the forms. Blank strings become null.
- New carers with no employee number receive `user_id` zero-padded from the numeric id.
- Documents, notes, conditions, home care, training, requirements, carer rota, service-user open visits, anonymised AI care plan, and medication update with an audit note.

## GDPR display decisions

Grids and list exports show only what a coordinator needs to find and open a record. Sensitive values stay in the view dialog, the edit dialog, or an authorised file viewer.

| Screen | Shown in the grid and CSV | Kept off the grid and CSV |
| --- | --- | --- |
| Service users | Status, SU number, last name, first name, preferred name, age (not the full date of birth), gender, branch | Address, phone, email, NHS, next of kin, date of birth, medical history, medications, notes, documents |
| Carers | Status, employee number, first name, surname, gender, branch, employment start | Email, mobile, address, date of birth, NI number, notes, emergency contacts, documents |

Search uses those operational fields. It does not match address, phone, email, mobile, or NI number. The legacy global search and full-table CSV did match and export those values. That reduction is intentional.

The AI prompt sends age, gender, conditions, history, medication text, notes, and services. It does not send name, address, or phone. The HTML preview is passed through DOMPurify before display.

Subject access exports remain available from the service-user row for an authorised staff user. They are not part of the operational grid.

## Differences that are intentional

| Topic | Legacy | New | Reason |
| --- | --- | --- | --- |
| Layout | PrimeVue dialogs, Quill, DataTable | Element Plus card, filter bar, table, tabs, dialogs | Keep the new design system |
| Biography and care text | Quill HTML editor | Text area. Stored HTML round-trips | Quill is not in the new app |
| Care-plan Word file | `docxtemplater` against `MaryCarePlanTemplate.docx` | Word-compatible HTML saved as `.doc`, with the same data sections | The template is not in the new `public/documents` folder and was not found under the Apache app |
| AI save format | HTML bytes named as a PDF | `.html` so preview works | The legacy “PDF” was HTML |
| Marital status on a service user | Required badge, omitted from the resolver | Required | Matches the badge the user already saw |
| Contact number | `InputNumber`, leading zeros dropped | Text | Phone numbers need the leading zero |
| Carer password confirm | Collected, not compared, not sent | Must match. Only the password is sent | Stops a mistyped password from being stored |
| Carer gender and email | Badge only. Save still posted | Blocking validation | The badges said the fields were required |
| Carer status on create | Control is visible. Save overwrites it to 1 | Hidden on create. Save sets 1 | Same stored result |
| Carer username on update | Not included in the update payload | Sent, so a wrong username can be corrected | The column exists and the create form already collects it |
| Image type check | Carer allow-list contained the literal `image/*`, so `image/jpeg` never matched | Extension and server allow-list use real types | The old check rejected valid images |
| File size | Service-user widget said 2 MB while script and server used 20 MB. Carer widget said 1 MB while script and server used 5 MB | 20 MB and 5 MB, matching the server | One rule in the UI and the API |
| Delete | Button for any signed-in user | Admin only | The API already returns 403 for non-admins |
| Bulk delete | Local array filter, no API call | Not migrated | It did not delete records |
| Search and export | Global filter and full CSV included address, phone, date of birth, NI | Operational columns only, plus status and branch filters | Data minimisation |
| Table session state | PrimeVue `stateStorage="session"` | Filters reset when the page is reopened | Not required for the business workflow |
| `services_provided` | Stored and sent to AI, never shown on the form | Editable on the Health tab | The value was already part of the record |
| Service-user visits | Used only inside the care-plan download | Also shown on a Visits tab | Same query, so the source data can be checked before download |
| Carer document preview | Download and delete only | Preview for pdf, text, and images | Same viewer as service users |
| Rota “Paid” | Label said Paid. Value was `m_transactions.payroll` | Column labelled Payroll | `m_attendances` has no `paid` column |
| Demo rows and stub fields | New-app stubs had sample people, free-text NHS, key code, mobility notes, DBS, and free-text employment type | Removed | Those fields are not legacy columns. NHS is the NHS contact lookup. Employment type is the lookup |

## Remaining gaps

| Gap | Why it remains |
| --- | --- |
| `middle_name` and `application_date` | Both appear on the legacy carer form and are posted by `saveSetting`. They are not on the Laravel `User` fillable list and they are not columns on the FastAPI `User` model, so they were never stored. They are not on the new form |
| Rich text editing | Biography, medical history, medications, services, employment history, and carer notes are plain text areas. Existing HTML is preserved. There is no toolbar |
| `MaryCarePlanTemplate.docx` | The download is a Word-compatible HTML document with the same sections, not a filled `.docx` template |
| Training course change on edit | Editing a training row and picking a different course updates the newly selected course. The previous assignment can remain. The legacy submit had the same limitation |
| File grouping | The file number is the first two underscore segments of the filename (`su_00001`, `id_00001`). A number or original filename that itself contains underscores can group files the same way the legacy upload did |
| Rota length | The carer rota returns the latest 90 attended visits, matching the legacy query limit |
| AI provider | If `GEMINI_API_KEY` or `GEMINI_API_KEY1` is missing, or the model call fails, the API returns a standard anonymised HTML plan and `is_mock` is true. The screen says the AI service was unavailable |
| Live verification | The Vue production build compiled both screens in the implementation session. The system Python used for a later import check does not have FastAPI installed, so the new routes were syntax-checked with `py_compile` and were not called against MySQL. No browser pass was run. Restart the API process before using the new routes |

Training, requirements, and daily-care tabs depend on `training_course_user`, `m_requirements_status`, and the daily-care table. The daily-care query returns an empty list when that table is missing. Training and requirements are not wrapped that way and will return an error if those tables differ from the models.

## Testing checklist

Run these after the FastAPI process has been restarted so the expanded schemas and `records` routes are loaded. Use a staff user (role 1 or 2) and an admin (role 1) for the delete rows.

### Service users

- [ ] Create: leave each required Personal field empty and confirm save stays on Personal. Then create a record and confirm status becomes the default active status and an SU number appears.
- [ ] Create: enter a contact that starts with 0 and confirm the stored value keeps the 0.
- [ ] Create: enter a badly formed email and confirm it is rejected. Leave email empty and confirm that is allowed.
- [ ] View: open a record and confirm Personal, Contacts, Service, Health, Notes, Documents, and Visits show the stored values and cannot be edited. Document view and download still work.
- [ ] Update: change name, address, next of kin, copy-address, GP, NHS contact, dates, biography, medical history, medications, and services provided. Reopen and confirm each value.
- [ ] Update: add, edit, and delete a medical condition (condition, category, diagnosis date, primary) and a home care type.
- [ ] Search: match last name, first name, preferred name, and SU number. Confirm address, phone, and email do not match.
- [ ] Filter: status and branch together, then clear both. Confirm the page returns to 1 when the filter changes.
- [ ] Export: CSV contains only status, SU number, last name, first name, preferred name, age, gender, and branch.
- [ ] Notes: reject an empty note. Add, edit, and delete a note. Confirm the author name.
- [ ] File upload: accept pdf, png, and txt under 20 MB. Reject an executable and a file over 20 MB.
- [ ] File preview: pdf, txt, and an image open in the dialog. A `.doc` or `.docx` downloads instead.
- [ ] File download: the saved file opens and matches the upload.
- [ ] File deletion: confirm is required, then the row disappears.
- [ ] Care-plan document: the downloaded `.doc` includes conditions, home care, daily care, notes, and open visits.
- [ ] AI: generate, export Word, text, and print, save onto Documents, and apply into the medications field. Confirm the grid never shows the plan text.
- [ ] SAR: summary loads, and PDF and Excel downloads succeed.
- [ ] Permissions: a non-admin does not see Delete and receives 403 if the delete URL is called. A carer role (3) receives 403 on the list.

### Carers

- [ ] Create: block save until branch, first name, surname, username, address, date of birth, gender, email, password, and confirm are valid. Mismatched passwords are rejected.
- [ ] Create: the new row has the default active status and an employee number.
- [ ] Create: a duplicate username or email shows the already-in-use message and leaves the dialog open.
- [ ] View: personal, emergency, employment, training, documents, rota, and notes are visible and not editable. Document view and download still work.
- [ ] Update: change employee number, branch, status, address, NI number, emergency contact, employment type, pension, contract, history, and notes. Reopen and confirm them. Password is not on the edit form.
- [ ] Search: match employee number, first name, and surname. Confirm address, mobile, and NI number do not match.
- [ ] Filter: status and branch, then clear. Export CSV has only status, employee number, first name, surname, gender, branch, and date started.
- [ ] Requirements: tick and untick a row and confirm the state after reopen.
- [ ] Training: require course, date, and status. Add, edit, and delete. Confirm completed, pending, and failed.
- [ ] File upload: accept pdf and jpg under 5 MB. Reject html and a file over 5 MB.
- [ ] File preview, download, and delete behave as on service users.
- [ ] Rota: rows show carer, service user, rate, date, service, time in, time out, and payroll. CSV matches the table.
- [ ] Permissions: non-admin has no Delete button. Carer role receives 403 on the list.

## Verification completed in this work

- Both Vue screens were rewritten and the production Vite build compiled them (`ServiceUsersView` and `CarersView` chunks emitted).
- `records.py`, the user and service-user schemas, `users.py`, `service_users.py`, and `api.py` passed `python -m py_compile`.
- A live import of the FastAPI app was not possible in the system Python because `fastapi` is not installed there.
- No browser walkthrough and no live API call against MySQL were run.
