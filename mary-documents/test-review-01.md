# Test review 01

Date: 22 November 2026
Scope: assessment only. No application code was changed.
System reviewed: Mary Care stack in `mary-v2`, development site `http://127.0.0.1:8080`.

This is a technical and regulatory review of the running implementation. It is not formal legal advice. A care provider should have the privacy notice, lawful basis, and any processor contracts reviewed by its data protection lead or counsel before relying on them.

Evidence used: Vue and FastAPI source, Nginx `deploy/nginx/dev.conf`, the live response headers from `http://127.0.0.1:8080/docs`, and a read-only look at `m_patient_care_types`, `m_patient_care_type_selections`, and `m_audit_logs`. No browser session was available, so the Vue screens were not clicked. The console messages below are the messages those screens produce from the code and headers that were verified.

---

## 1. Document viewer access issue

### Findings

The sentence "This content is blocked. Contact the site owner to fix the issue." does not exist anywhere in the application. It is Chrome's own page, drawn inside a frame when the page's Content Security Policy refuses the frame.

Viewing is broken for every file the screens try to show in an iframe. That includes care-note PDFs and the service-user and carer document preview (PDF, text, HTML, and images). Upload, download, and delete do not use that iframe, so they can succeed while viewing fails.

The preview path is the same in three screens:

- `mary-element/src/views/management/ServiceUsersView.vue` loads the file with `GET /api/v1/download/{filename}`, builds a `blob:` URL, and assigns it to an iframe.
- `mary-element/src/views/management/CarersView.vue` does the same through `GET /api/v1/carerdownload/{filename}`.
- `mary-element/src/views/DailyTimeRecord.vue` loads `GET /api/v1/care-notes/view/{filename}` and does the same for the care-note PDF.

Previewable service-user extensions are `pdf`, `txt`, `png`, `jpg`, `jpeg`, `gif`, `webp`, and `html`. Carer preview uses the same list without `html`. Word files are not previewed. The screen says "This file type opens as a download" and saves the file. That path is unaffected.

The edge Nginx config adds this header to every response, including the HTML page:

```
Content-Security-Policy: default-src 'self'; ... img-src 'self' data: blob:; ...
```

There is no `frame-src` or `object-src`. Those directives fall back to `default-src 'self'`. A `blob:` URL is not covered by `'self'`. `blob:` is allowed only for images. The live response for `http://127.0.0.1:8080/docs` carried this policy. The production template uses the same policy.

Create and delete call `/upload`, `/carerupload`, `/deleteFile/{filename}`, and `/carerDeleteFile/{filename}`. Those are JSON or delete requests. They never open a frame. Staff authentication is required. Names are restricted to a basename, an allowed extension, a size cap (20 MB for service users, 5 MB for carers), and a required prefix (`su_` or `id_`).

### Root cause

The document dialogs display files by framing a blob URL. The Content Security Policy added for the deployment forbids framing any origin other than `'self'`. Chrome then paints its blocked-frame page inside the iframe. The application still fetched the file successfully. The failure is in the browser, caused by the edge policy interacting with the frontend preview. It is not a storage, permission, or care-note-only rule.

Expected console entry when a preview opens:

`Refused to frame 'blob:...' because it violates the following Content Security Policy directive: "default-src 'self'". Note that 'frame-src' was not explicitly set, so 'default-src' is used as a fallback.`

### Technical impact

Staff cannot read care-note PDFs or preview stored documents in the application. The download button still returns the bytes, so the files are not lost. Care-note generation and deletion can still report success. The same break will appear in production because `deploy/nginx/prod.conf.template` sends the same policy.

### Security impact

The policy is doing the job it was given: it stops the page from framing an unexpected URL. The side effect is that it also stops the application's own previews. Tightening the policy was not an authorization bug. Two related access gaps are separate from this message:

- `GET /care-notes/view/{filename}` is mounted on the attendance router, which only requires a logged-in active user. A carer who knows or guesses a filename can retrieve that PDF. The managed download routes additionally require a staff role.
- Neither preview nor download writes an audit row.

### Compliance impact

Care records that cannot be read inside the system push staff toward loose downloads. That is a records-handling and confidentiality problem. The blocked page is not evidence that a care note was withheld from an unauthorised person.

### Recommendations

Keep the page policy. Add an explicit frame source that allows only `blob:` on this origin, for example `frame-src 'self' blob:`, and do not allow general remote frames. Confirm image previews the same way. Prefer a staff-only care-note route that checks the filename the same way managed downloads do. Record document and care-note reads in the audit log. Do not treat the Chrome message as an access-denied state.

### Risk rating

High

---

## 2. Documentation portal blank page

### Findings

`http://127.0.0.1:8080/docs` is not a documentation screen. The edge server forwards everything except `/api/` and `/healthz` to the Vue app. A request for `/docs` returns the SPA shell with HTTP 200. Confirmed on the running stack: `Content-Type: text/html`, the Vue `index.html`, and the Content Security Policy above.

The router has no `/docs` child. The in-app manual is `/user-manual` (`UserManual.vue`), linked from the user menu as "User Manual". FastAPI's interactive API docs are a different server: `http://127.0.0.1:8000/docs`. That URL responded 200 and does not use the Vue login page. In production the API docs are switched off.

Login behaviour matches the report:

1. `/docs` is not a public route, and there is no token yet, so the guard sends the browser to `/login?redirect=/docs`.
2. A successful login calls `router.push(safeInternalPath(route.query.redirect))`.
3. `/docs` passes that check because it is a single-slash path.
4. No route matches `/docs`. `App.vue` renders only `<router-view />`, so the matched view is empty. The screen stays white.
5. Role does not matter. An administrator is allowed through, and a non-administrator has no `meta.role` to fail, because nothing matched. Neither lands on `/access-denied`.

`UserManual.vue` itself renders six short markdown sections. Its search box does not filter those sections. That is a separate, smaller defect. It does not explain a blank `/docs`.

### Root cause

`/docs` is an unmatched Vue route. The login guard preserves it as the post-login destination. Vue Router then has no component to show. Expected console warning:

`[Vue Router warn]: No match found for location with path "/docs"`

No documentation API is called. No permission or claim is missing.

### Technical impact

Anyone who opens the usual documentation URL on the site, including someone looking for the API docs or the user manual, gets a blank page after a normal login. The manual at `/user-manual` is unaffected. API docs remain on port 8000 in development only.

### Security impact

Low. The blank page does not disclose data. Development API docs on `127.0.0.1:8000` are reachable without the Vue login while `ENVIRONMENT` is not `production`. They are bound to localhost in this Compose file. They must stay disabled in production, which the application already does.

### Compliance impact

None by itself. Staff who cannot find the manual may mishandle records, which is an operational risk rather than a GDPR control failure.

### Recommendations

Add a `/docs` route that shows the user manual, or redirect `/docs` to `/user-manual`. Add a not-found page so an unknown path cannot render blank. Keep FastAPI `/docs` off the public origin in production. Point operators at `DEPLOYMENT.md` and `/user-manual`, not at `http://127.0.0.1:8080/docs`.

### Risk rating

Medium

---

## 3. Subject Access Request feature

### Findings

The service-user screen has a Subject Access Request dialog. It calls:

- `GET /api/v1/service_users/{su_id}/sar-data` for the counts in the dialog
- `GET /api/v1/service_users/{su_id}/sar-export?format=pdf|excel` for the file

Both require a staff or administrator session (roles 1 and 2). The dialog offers "PDF dossier" and "Excel portability file" and labels the alert "UK GDPR Article 15". The Excel generator is described in code as an Article 20 portability workbook. The PDF is described as an Article 15 disclosure.

`fetch_sar_dataset` collects the service-user row, care notes, visits and attendance times, invoices linked to those visits, and up to 50 audit rows. The PDF and workbook are built for staff to download. There is no data-subject request record, no identity check, no purpose field, no approval, and no deadline.

The export writes an audit row with action `EXPORT` and record type `sar_export`, but it does not pass the staff user id or username. The live table has 11 audit rows. All 11 have a null `user_id`. Five are SAR previews and five are SAR exports.

### Root cause

The feature was built as an in-product way for staff to assemble a copy of one person's record and to label that copy with Article 15. The Excel path was additionally labelled Article 20. No request workflow was built around it.

### Intended purpose

Give a coordinator a single PDF or spreadsheet containing the personal and care data the application holds for one service user, so the agency can answer an access request.

### Why Article 15 is cited

Article 15 of the UK GDPR is the right of access. A person can ask a controller for confirmation that their data is processed and for a copy of that data, plus the usual notice information. A care system that can gather the copy helps the agency meet the one-month response period. The citation is aimed at that right. It does not, by itself, make the button a completed SAR process.

### Is it legally required?

The right of access is legally required. A specific export button is not. The agency must be able to answer a SAR whether or not this screen exists. The button is a reasonable operational aid. It is not a statutory form.

Article 20, the right to data portability, is narrower. It applies only where the lawful basis is consent or a contract, the processing is automated, and the request is for data the person provided or that was generated by their activity. Health and care data processed under Article 9(2)(h), and ordinary data processed under a legal obligation, are often outside Article 20. Calling the spreadsheet a portability file overstates what the button does. The file can still be a useful Article 15 copy.

### Data minimisation and disclosure

An Article 15 copy is supposed to be broad for the person who asked. The compliance problem is the opposite of over-collecting into the SAR: any staff user who can open service users can download the full dossier without recording why, and the audit row does not identify them. The dataset also includes invoices, which may contain data about the agency's charges rather than only the person's own data. Third-party names, such as carers and next of kin, need a check so one person's SAR does not casually disclose another person's private data beyond what the request requires.

### Safeguards present

- Staff role required.
- The file is not listed on the main service-user grid. The dialog says that.
- An export row is written, including IP address and user agent when the request reaches the API.
- The download is an attachment, not an inline public link.

### Safeguards missing

- No restriction to a SAR owner or administrator.
- No reason, request date, identity verification, or approval.
- No user id on the audit row. All 11 current rows demonstrate that.
- No retention or access control on the downloaded file after it leaves the server.
- No separation of another person's data.

### Should it remain?

Yes. Removing it would make statutory access requests slower and more error-prone. It should stay as a controlled staff tool, not as an open export.

### Technical impact

Large PDF and Excel responses for one service user. The query is bounded for audit rows (50) but not for notes, visits, or invoices. A person with a long history can produce a heavy export. Column names in the SAR SQL match the real `su_first_name` and `su_last_name` columns.

### Security impact

A staff session can export special-category data in one request. The audit trail cannot show which account did it.

### Compliance impact

High. The agency can look more compliant than it is. A SAR file produced with no requester, no identity check, and no identified staff member is a disclosure risk under Article 5(1)(f) and Article 32, not evidence that Article 15 has been met.

### Recommendations

Keep the export. Limit it to administrators, or to a named SAR role. Require a reason and the request date. Store the acting user id on the audit row. Rename the Excel option to "spreadsheet copy" unless counsel confirms Article 20 applies. Review carer and next-of-kin fields before they are included. Do not email the file from the server until mailbox controls exist.

### Risk rating

High

---

## 4. Home care selection

### Findings

The Home Care control is a single-select list. `el-select` in the "Add home care" dialog binds one `care_type_id`. The `multiple` attribute is not set.

The service user can still have more than one home-care type. Each save inserts or updates one row in `m_patient_care_types`. The screen lists those rows and can edit or delete each one. Adding Personal care, then opening Add again and choosing Medication, creates two rows.

The API accepts that. `POST /api/v1/patient-care-types` requires `su_id` and `care_type_id` and inserts a row. It does not reject a type the person already has. The live table's indexes are the primary key on `patient_care_type_id` and a non-unique foreign key on `care_type_id`. There is no unique pair of service user and care type. The same type can be stored twice.

A second table, `m_patient_care_type_selections`, exists and is only read. `_daily_cares` groups it by day for the care-plan document. Nothing in the current API inserts into it. Its only index is the primary key. The Home Care screen does not show that daily list. Only the generated care-plan document includes it, and that list will stay empty unless older data is already in the table.

### Root cause

The screen was built as "add one type at a time" on top of a one-to-many table. It was not built as a multi-select widget. The older selections table was left as a read-only reporting source.

### Technical impact

Coordinators can assign several home-care types. They cannot pick several in one dialog. Duplicate rows are possible and would appear twice in the table and in the care-plan document. No API used by invoicing or payroll was found that assumes exactly one care type.

### Security impact

Low. The endpoints require a staff session. The gap is data quality, not access control.

### Compliance impact

Low, provided the care plan a carer follows is the one the coordinator can see. Duplicate or stale types could misstate the commissioned care. That is a care-record accuracy issue under Article 5(1)(d) if staff rely on the list.

### Is multi-select feasible?

Yes, without a new table. A multi-select can post one `m_patient_care_types` row per chosen id and can diff the current rows on edit. The database already stores many types per person.

Do not point the multi-select at `m_patient_care_type_selections` unless the product still needs a dated daily selection. That table is a different concept: selections over time, not the person's current type list.

### Recommendations

Treat multiple types as the intended model. If the dialog should accept several at once, add `multiple` and write one row per id. Add a unique constraint on (`su_id`, `care_type_id`) after cleaning duplicates. Decide whether `m_patient_care_type_selections` is still required. If it is not, stop reading it into care plans so the document does not imply a history the screen cannot edit.

### Risk rating

Low

---

## 5. UK GDPR Article 9 access audit trail

### Findings

The admin menu opens `/audit-logs`, titled "UK GDPR Article 9 Access Audit Trail". The page loads `GET /api/v1/audit/logs` and can export the rows to CSV. The router requires an administrator. The page shows a fixed "Article 9 Compliance / 100% Active" figure. That figure is not calculated.

`m_audit_logs` stores user id, username, service-user id, patient name, record type, action, details, IP address, user agent, and a timestamp. The privacy notice says every read of medical history, MAR, and care-plan notes is logged and that the trail is immutable.

The code does not do that.

`log_audit_event` is called from three places only:

- `GET /service_users/{id}/dossier` and `GET /getsu/{id}`, action `READ`, type `medical_dossier`
- `GET /service_users/{id}/sar-data`, action `VIEW`, type `sar_preview`
- the SAR export, action `EXPORT`, type `sar_export`

The service-user screen does not call the dossier route when a coordinator opens the record. Document download, document preview, care-note view, conditions, medications, and notes are not logged. `POST /api/v1/audit/log` can insert a client-supplied user id, username, action, and details, but the audit router requires an administrator, and no Vue screen calls it.

The live log confirms the gap: 11 rows, all with a null user id, and only the three event types above. There is no care-note or MAR row. Rows can be updated or deleted by anyone with database access. There is no hash chain, append-only grant, or retention lock. The IP address is taken from the first `X-Forwarded-For` value.

### Root cause

The trail was added as a demonstration of accountability and then described, in the notice and on the screen, as if it already covered every special-category read. The write calls were never placed on those reads, and the calls that do exist omit the acting user.

### Purpose

Show who looked at or exported a service user's health and care data, when, from where, and what they did. That supports investigations, CQC or commissioner questions, and the agency's own accountability record.

### What GDPR asks for

Article 9 defines special-category data, including health data, and the conditions for processing it. Article 9(2)(h) is the health and social care condition. It does not say "keep an access log". The code comment that ties the log to Article 9(2)(h) misstates that paragraph.

The duties that actually point at a log are:

- Article 5(2), accountability
- Article 32, security appropriate to the risk
- Article 5(1)(f), integrity and confidentiality
- sector expectations from CQC, the Caldicott principles, and the Data Security and Protection Toolkit where those apply to the contract

An access log for health records is best practice and, for this kind of system, an expected safeguard. It is not a clause that says a product must ship a screen called "Article 9 audit trail".

### What should be audited

For special-category and care records, log at least:

- who, including a server-side user id that the client cannot choose
- whose record
- which record or file
- view, create, update, delete, export, and print
- timestamp from the server
- source IP from the proxy's own real-IP header, not an untrusted forwarded list
- success or failure

Do not put the clinical note text, medication list, or file bytes into the audit details.

### What happens if it is removed

The empty coverage would be gone, and so would the evidence of SAR exports. The privacy notice would be false in a more obvious way. Removal makes the accountability gap worse. Repair the trail. Do not switch it off.

### Technical impact

Administrators can view and export a log that does not represent access. The "100% Active" card will keep saying that while care-note views leave no row.

### Security impact

A log that omits the actor and accepts a client-chosen username cannot support an investigation. Forging or deleting rows is possible for anyone who can write to MySQL. The forwarded-IP field can be influenced if a client reaches the API without the edge proxy.

### Compliance impact

High. The notice claims a control the system does not operate. That is an Article 5(1)(a) and Article 5(2) problem: processing is not described accurately, and the agency cannot demonstrate the safeguard it says it has.

### Recommendations

Write the log on the server for dossier reads, document views and downloads, care-note views, note and medication changes, and exports. Always store the authenticated user id. Stop taking user id and username from the client. Remove the "100% Active" claim, or replace it with a real count. Restrict update and delete grants on `m_audit_logs`. Align the privacy notice with the events that are actually stored. Keep the admin viewer.

### Risk rating

High

---

## 6. GDPR compliance assessment

This section judges the application as it is built, not the wording of the marketing documents in `mary-element/docs`.

### Compliance strengths

- Role splits exist: administrator, staff, and carer, with extra finance checks on payroll and invoices. The audit viewer is administrator-only.
- Document upload checks extension, size, and filename, and staff must be logged in to upload, download, or delete managed files.
- A privacy notice page exists at `/privacy-policy` and names Article 6 and Article 9(2)(h), the ICO, and a one-month access right.
- An Article 15-style export exists, which is the right mechanism to help with access requests.
- An audit table exists and is at least written for dossier and SAR events.
- The care-plan generator used from the service-user screen tells the model not to include name, address, or telephone number. The on-screen text says a coordinator must review the result.
- Production configuration refuses placeholder secrets, wildcard CORS, public API docs, in-memory sessions, and automatic table creation. Edge TLS and security headers are part of the production Compose design.
- Password reset no longer returns the reset link in the JSON response.

### Compliance gaps

**Privacy notice.** UK GDPR Articles 13 and 14 expect the controller's identity and contact details, the purposes and lawful bases, the categories of data, the recipients, international transfers and their safeguard, retention, the rights, the right to complain to the ICO, and whether providing the data is required. The page is a short in-app notice. It gives a generic "DPO Compliance Team" and `dpo@stmarysteamcare.co.uk`. It does not give a postal address, company number, or the real processor list. It states that the product is "UK GDPR & DPA 2018 Compliant", which this review does not support.

**Special-category data.** Health data, care notes, medications, and conditions are special-category data. Article 9(2)(h) can be an appropriate condition for care delivery, together with the Data Protection Act 2018 Schedule 1 conditions and the duty of confidentiality. The application does not record which condition applies to each processing activity. There is no record of processing activities (Article 30) in the product.

**Access control.** Managed documents require staff. Care-note download only requires any active login, so a carer token is enough if the filename is known. `GET /getsu` returns service users to any active user because of the router-level dependency. List and detail screens are how staff work, but carers should not receive every person's dossier by default.

**Auditability.** Covered in section 5. The notice overclaims the log. Every current row is missing the user id.

**Data portability and subject rights.** Article 15 is partially supported by a staff export, with no request tracker. Article 16 rectification is only the normal edit screens. There is no erasure, restriction, or objection workflow. The notice mentions an eight-year NHS or CQC retention period, and the application does not enforce a retention or disposal schedule. Article 20 should not be promised for the Excel file without a lawful-basis check.

**Data minimisation.** SAR and care-plan documents pull a wide set of fields, which is appropriate only for a real access request or a real care plan. The daily care-note generator sends the service user's name, the carer's name, the care plan, and the carer's observations to Google or OpenAI when an API key is set. That is the opposite of the minimisation claim on the service-user care-plan button.

**International transfers and processors.** Gemini and OpenAI calls leave the UK when a key is configured. Keys are blank in the current development env file, so the path is dormant on this PC. The code is still a transfer of special-category data with no in-app transfer assessment, no Article 28 processor terms, and no mention in the privacy notice.

**Security of the deployment.** Session tokens remain in browser storage. The Content Security Policy allows `'unsafe-inline'` and `'unsafe-eval'`. Local MySQL listens on all interfaces, `mary_admin` has server-wide privileges, and the Windows firewall rules `Port 3306` and `Port 33060` still allow any remote address. Those host settings were recorded in `DEPLOYMENT.md`. They matter because this database holds special-category data.

### Risks

- A staff member exports a full care dossier and the log cannot name them.
- A carer, or any logged-in user, retrieves a care-note PDF by filename.
- Clinical text is sent to an overseas model once an API key is added, without a disclosed basis.
- The agency shows inspectors a notice and an audit screen that describe controls the software does not perform.
- Records are kept, or deleted, with no retention rule in the system.
- The document viewer failure causes staff to download care files onto local machines.

### Potential violations

These are gaps that can become infringements if this build is used for live care. They are not a finding that the ICO has determined a breach.

- Article 5(1)(a) and Articles 13 and 14, if people are given the current notice.
- Article 5(1)(f) and Article 32, for care-note access by any active user, unidentified exports, and the exposed local database.
- Article 5(2), because the agency cannot demonstrate the access logging the notice describes.
- Articles 44 to 49, if special-category text is sent to Gemini or OpenAI without a transfer tool.
- Article 28, if those providers are used without a contract the controller can show.

### Missing controls

- A controller-approved privacy notice and a matching data-protection policy.
- A record of processing activities and a retention schedule the software enforces.
- Server-side audit coverage with a real user id and no client-supplied identity.
- A SAR case log: identity check, dates, exemptions, and who released the file.
- A least-privilege database account and a closed database port.
- A decision, recorded outside the code, on whether AI processing is allowed at all.
- Care-note authorisation tied to the assigned carer or to staff, not to any login.

### Recommended improvements, in order

1. Stop the unidentified SAR export and the any-login care-note fetch before live use. Critical.
2. Rewrite the privacy notice so it describes this system, including whether AI is used. Critical.
3. Log real access events and remove the "100% Active" claim. High.
4. Allow blob previews in the Content Security Policy so staff stop downloading care files to view them. High.
5. Close MySQL to localhost and replace the server-wide database account. High.
6. Add a retention and disposal design. Do not build erasure that deletes records the agency must keep. Medium.
7. Decide home-care cardinality and add the unique constraint. Low.

### Risk rating

Critical

---

## Summary

| Item | Root cause in one line | Risk |
| --- | --- | --- |
| 1. Document viewing | Content Security Policy blocks the blob iframe used for every preview | High |
| 2. Blank `/docs` | No Vue route; login returns the browser to an unmatched path | Medium |
| 3. SAR export | Staff-wide Article 15 download with no request control and no user id on the log | High |
| 4. Home care | Single-select dialog writing many rows; duplicates are allowed | Low |
| 5. Article 9 trail | Log and notice claim coverage the write-paths do not implement | High |
| 6. GDPR posture | Notice, access, audit, retention, and AI transfer do not match UK GDPR expectations for health data | Critical |

No code was changed for this review.
