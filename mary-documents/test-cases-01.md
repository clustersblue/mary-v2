# Mary Care — test cases, sign-in to sign-out

**Date:** 22 November 2026  
**Application:** Mary Care Management System, served at `http://127.0.0.1:8080` in development  
**Status:** Written for a tester to run. This file does not record a completed test run.

Use a copy of this file, or a spreadsheet with the same columns, and fill **Result** with Pass or Fail. Add a short note for every Fail. Do not paste clinical text, passwords, or full access-request files into the results.

## Roles

| Role | How the account is recognised | First page after sign-in |
| --- | --- | --- |
| Administrator | Role 1, or the administrator flag | Dashboard (`/`) |
| Staff / coordinator | Role 2, without the administrator flag | Care Rota Planner (`/planner`) |
| Carer | Role 3, without the administrator flag | Carer Portal (`/attendance`) |

Finance, the Audit Trail, subject-access download, and delete of a service user or carer are administrator actions. Staff can open service users, carers, the planner, the daily time record, settings other than branch changes, and the user manual. A carer uses the Carer Portal and My Account.

## Before you start

1. The site loads at `http://127.0.0.1:8080` and the sign-in page is shown when no one is signed in.
2. You have one administrator, one staff account, and one carer account. Write down only the usernames in your run notes.
3. The carer has one shift assigned for today, and one shift that is not assigned, so both clock-in paths can be tried. Use a test service user.
4. That test service user already has one home care type, one uploaded document the browser can show (a PDF), and at least two care-note files: one whose name contains the carer's name token, and one that does not.
5. Password reset sends mail only when mail is configured. A missing email is a mail-setup result, not a screen failure, when the confirmation text below still appears.
6. Do not run the forgotten-password case more than a few times. The request is limited to five attempts in 15 minutes.

## How to sign out

On any signed-in page, open the name menu at the top right and choose **Logout**. The expected result for every journey below ends there: the message "Logged out successfully" appears, the sign-in page is shown, and opening a protected address such as `/planner` returns to the sign-in page.

---

## 1. Sign in, session, and sign out

### AUTH-01 Wrong password

**Role:** any known username  
**Steps:**
1. Open `/login`.
2. Enter the username and a wrong password.
3. Choose **Sign In**.

**Expected:** The sign-in page stays open and shows an error. No dashboard, planner, or portal is shown.  
**Result:**

### AUTH-02 Empty sign-in

**Role:** none  
**Steps:** Leave Username or Password empty and choose **Sign In**.  
**Expected:** The form asks for the missing field. No request succeeds as a signed-in session.  
**Result:**

### AUTH-03 Administrator sign-in and sign-out

**Role:** Administrator  
**Steps:**
1. Sign in with **Remember me** ticked.
2. Confirm the Dashboard opens.
3. Open the name menu and choose **Logout**.
4. Open `/planner` in the same browser.

**Expected:** Welcome message uses the person's name. After logout, the sign-in page is shown and `/planner` does not open the planner.  
**Result:**

### AUTH-04 Remember me

**Role:** Staff  
**Steps:**
1. Sign in with **Remember me** ticked. Open a new browser tab to `/planner`.
2. Sign out. Sign in again with **Remember me** cleared. Refresh the planner tab.
3. Close that tab, open a new tab, and go to `/planner`.

**Expected:** With **Remember me** ticked, the new tab is still signed in. With it cleared, a refresh of the same tab stays signed in, and a newly opened tab asks for sign-in.  
**Result:**

### AUTH-05 Staff and carer landing pages

**Role:** Staff, then Carer  
**Steps:** Sign in as staff. Sign out. Sign in as the carer.  
**Expected:** Staff land on **Care Rota Planner**. The carer lands on **Carer Portal**. Neither lands on the administrator Dashboard.  
**Result:**

### AUTH-06 Already signed in

**Role:** Administrator  
**Steps:** While signed in, open `/login`.  
**Expected:** The browser returns to the Dashboard. Staff would return to the planner, and a carer to the portal.  
**Result:**

### AUTH-07 Forgotten password message

**Role:** none  
**Steps:**
1. On the sign-in page choose **Forgot Password?**.
2. Submit a registered email.
3. Close the dialog and submit an email that is not registered.

**Expected:** Both attempts show "If the email is registered, a password reset link has been sent." The page does not say which address exists. A reset link arrives only when mail is configured, and it expires after 60 minutes. The new password must be at least 8 characters, and **Update Password & Return to Login** returns to the sign-in page.  
**Result:**

### AUTH-08 Expired session message

**Role:** any  
**Steps:** Open `/login?reason=expired`.  
**Expected:** A warning says the session has expired and asks the person to sign in again.  
**Result:**

---

## 2. Menu and denied pages

### NAV-01 Administrator menu

**Role:** Administrator  
**Steps:** After AUTH-03 sign-in, before logout, walk the left menu and the name menu.  
**Expected:** The left menu shows Dashboard, Carer Portal, Care Rota Planner, Daily Time Record (DTR), Finance & Payroll (Generate Payments, Payroll Management, Invoice Management), Management (Service Users, Carers), and Settings. The name menu shows My Account, Audit Trail, Privacy Notice, User Manual, and Logout. The header has a light/dark switch and a collapse control.  
**Result:**

### NAV-02 Staff menu

**Role:** Staff  
**Steps:** Sign in and inspect both menus. Open `/`, `/audit-logs`, `/payments`, `/payroll`, and `/invoice` by typing the address.  
**Expected:** Dashboard, Finance & Payroll, and Audit Trail are absent. Each typed address shows **Access Denied**, with **HTTP 403 Forbidden**, a button back to the planner, and **Switch Account**. Service Users, Carers, the planner, DTR, settings, Privacy Notice, and User Manual remain available.  
**Result:**

### NAV-03 Carer menu

**Role:** Carer  
**Steps:** Sign in and inspect both menus. Open `/planner`, `/management/service-users`, `/user-manual`, and `/audit-logs` by address.  
**Expected:** The left menu shows Carer Portal only. The name menu shows My Account, Privacy Notice, and Logout. User Manual and Audit Trail are absent. Each typed address shows Access Denied. **Switch Account** signs out to the sign-in page.  
**Result:**

### NAV-04 Public pages while signed out

**Role:** none  
**Steps:** Open `/privacy-policy`, `/login`, and `/reset-password`. Then open `/account`.  
**Expected:** The privacy notice, sign-in page, and reset-password page open. `/account` returns to sign-in and keeps the return path.  
**Result:**

---

## 3. Dashboard

### DASH-01 Period and refresh

**Role:** Administrator  
**Steps:**
1. Open **Dashboard**.
2. Choose Daily, Weekly, then Monthly.
3. Choose **Refresh**.

**Expected:** The heading is "Executive dashboard". Organisation totals stay on the page. The charts follow the selected period. Refresh reloads without signing the person out.  
**Result:**

---

## 4. Carer Portal

### PORTAL-01 No shift

**Role:** a carer with no shift today, or a time when none is assigned  
**Steps:** Open **Carer Portal**.  
**Expected:** The warning "No active shift is assigned to you." is shown. Clock In and Clock Out are not available.  
**Result:**

### PORTAL-02 Clock in, note, clock out

**Role:** Carer with a shift today  
**Steps:**
1. Choose **Clock In**.
2. Open **Carer Visit Logs & Care Notes**, choose **Add note**, save a short test note, edit it, then delete it.
3. Choose **Clock Out**.
4. Open **My Attendance History**. Confirm **Attendance Records** and **My Scheduled Shifts**.

**Expected:** "Clocked in" appears, then the note can be saved only while the session is open. An empty note is refused. Edit and delete are shown only on that carer's own notes. "Clocked out" appears, and the page then says today's attendance is complete. Clock In is not offered again for that completed day. History lists the clock times.  
**Result:**

### PORTAL-03 Note without a session

**Role:** Carer who is not clocked in  
**Steps:** Choose **Add note**.  
**Expected:** A warning says to clock in before creating care notes. The note is not saved.  
**Result:**

### PORTAL-04 Another carer's care-note file

**Role:** Carer, then Staff  
**Steps:**
1. As the carer, open a care-note file whose name was generated for that carer.
2. Try a care-note file generated for someone else.
3. Sign out, sign in as staff, and open the same second file from the Daily Time Record.

**Expected:** The carer can open the file created in their name. The other file is refused. Staff can open it.  
**Result:**

---

## 5. Care Rota Planner

### PLAN-01 Create, edit, and delete one shift

**Role:** Staff  
**Steps:**
1. Open **Care Rota Planner**.
2. Choose **New Shift Assignment**. Select a carer, the test service user, a shift code, and one date. Leave repeat on **One-Time**. Choose **Create Shift**.
3. Open that shift. Change a field and choose **Update Shift**.
4. Open it again and choose **Delete Shift**. Confirm.

**Expected:** The shift appears on the calendar, the change is kept, and the deleted shift is gone after refresh. Cancel closes the dialog without saving.  
**Result:**

### PLAN-02 Repeat and double-up

**Role:** Staff  
**Steps:**
1. Create a shift with **Daily** or **Custom Days**, an end date, and **Double-Up Shift** selected.
2. Save, then open one occurrence and choose the option that changes the whole series.
3. Use **Bulk Delete Recurrences for Client** for that test service user and cancel, then repeat only if the test data may be removed.

**Expected:** Occurrences run until the end date. A series change asks whether this occurrence or the series is affected. Cancel on the bulk delete leaves the series in place.  
**Result:**

### PLAN-03 Print and export

**Role:** Staff  
**Steps:** Use the print control and the download control.  
**Expected:** Print opens the browser print view of the rota. Download produces a CSV of the shifts on screen.  
**Result:**

---

## 6. Daily Time Record

### DTR-01 Range, expand, and CSV

**Role:** Staff  
**Steps:**
1. Open **Daily Time Record (DTR)**.
2. Set a date range that contains the test visits. Refresh.
3. Expand all rows, then collapse them.
4. Download the CSV.

**Expected:** Rows match the range. An empty range shows the empty-state message rather than an error. Expand and collapse change the visible visits. The CSV downloads.  
**Result:**

### DTR-02 Care-note file in the page

**Role:** Staff  
**Steps:** On a visit that already has a care-note file, choose **View Generated Care Note PDF in Browser**. Then close it.  
**Expected:** The PDF is shown in the page. The tester is not forced to save the file in order to read it.  
**Result:**

### DTR-03 Administrator clock tools

**Role:** Administrator  
**Steps:**
1. Confirm **Generate Automatic Clock Times (Up to Today)** is available.
2. Open the confirmation and choose **Cancel**.
3. Open **Clear / Reset Clock Times** for a test row and choose **Cancel**.

**Expected:** Both actions ask before changing times. Cancel leaves the times unchanged. Staff do not see these two administrator actions.  
**Result:**

### DTR-04 Care-note generation dialog

**Role:** Staff  
**Steps:** On a visit with no care-note file, choose **Care Notes**. Read the dialog **Care Plan Generator (Care Notes)**. Choose **Close** without **Generate Care Plan**.  
**Expected:** The dialog names the service user and the carer and has a box for observations. Close leaves the visit without a new file. Generating the file is a separate, deliberate step. When no external key is configured, generation stays inside the system. When a key is configured, generation sends the names, visit, care-plan text, and observations to that provider, so do not generate against a real record unless that transfer is approved.  
**Result:**

---

## 7. Finance

### FIN-01 Generate Payments

**Role:** Administrator  
**Steps:**
1. Open **Generate Payments**.
2. On **Generate Payroll**, choose a carer and a date range, then search.
3. Open **Generate Invoice**, choose a service user and a date range, then search.
4. If a batch would be created, choose **Cancel** on the confirmation unless this run is allowed to create a financial batch.

**Expected:** Both tabs search completed shifts for the selected person and dates. Generate asks for confirmation. Cancel creates nothing. A staff account cannot open this page (NAV-02).  
**Result:**

### FIN-02 Payroll Management

**Role:** Administrator  
**Steps:** Open **Payroll Management**. Review **Manage Payroll** and **Payroll Records**. Choose **Refresh**, then **Export All Payroll**.  
**Expected:** Both tabs load. Export is available when the list has rows and produces a CSV. An empty list disables export.  
**Result:**

### FIN-03 Invoice Management

**Role:** Administrator  
**Steps:** Open **Invoice Management**. Review **Manage Invoices** and **Invoice Records**. Refresh, then export.  
**Expected:** Both tabs load. Export follows the same rule as payroll.  
**Result:**

---

## 8. Service users

### SU-01 List and export

**Role:** Staff  
**Steps:** Open **Management > Service Users**. Choose **Refresh**, then **Export list**.  
**Expected:** The list loads. Export downloads `service-users.csv`. This list view is not an audit-trail event.  
**Result:**

### SU-02 Create, view, edit, and close

**Role:** Staff  
**Steps:**
1. Choose **Add Service User**. Fill the Personal, Contacts, and Service tabs with test data. Choose **Create**.
2. Open the new row with the view control.
3. Close it, open the edit control, change one non-clinical field, and choose **Update**.
4. Do not delete the row in this case.

**Expected:** Create and Update succeed. View opens the record read-only, with **Close** and no **Update**. Health, Notes, and Documents appear only after the record exists. A staff account does not see **Delete record**.  
**Result:**

### SU-03 Home care once per type

**Role:** Staff  
**Steps:**
1. Edit the test service user. Open **Health**.
2. Add a home care type that is not already on the record. Save.
3. Add the same type again. Save.

**Expected:** The first save is kept. The second save is refused with "This home care type is already assigned". A different type can still be added.  
**Result:**

### SU-04 Documents

**Role:** Staff  
**Steps:** On **Documents**, view the test PDF, then use the download control.  
**Expected:** View shows the file in the page. Download saves a copy. Upload and delete are available while editing and are not audit-trail events. Viewing or downloading a `su_` file is an audit-trail event for an administrator to see later.  
**Result:**

### SU-05 Care plan draft

**Role:** Staff  
**Steps:** On **Health**, choose **Generate care plan**. Read the on-screen hint. Close the dialog without applying it to the record.  
**Expected:** The hint says the draft uses age, medical conditions, and the current care text, and that a coordinator must review it before it is saved. If no external key is configured, the draft is produced inside the system. **Apply to record** is not used in this case, so the saved care text is unchanged.  
**Result:**

### SU-06 Subject access request, administrator

**Role:** Administrator  
**Steps:**
1. On the test service user, choose **Subject access request**.
2. Leave the reason shorter than 8 characters and confirm **Download** stays disabled.
3. Enter a reason of at least 8 characters and a request date in the future. Choose **Download**.
4. Set the request date to today. Leave **Include next-of-kin contact details and carer surnames** unticked. Download the **PDF dossier**, then the **Spreadsheet copy**.
5. Tick the checkbox and download the PDF again only if this run is allowed to include third-party contact details.

**Expected:**
- The dialog title starts with "Subject access request".
- The summary shows counts for visits, notes, and audit events. It does not show the full demographic record.
- The checkbox text wraps inside the dialog.
- A future date is refused with "Request date cannot be in the future."
- Both files download. The names start with `UK_GDPR_Art15_SAR_` and end in `.pdf` and `.xlsx`.
- The file is not emailed.
- The reason sentence is not printed in the file. The request date is printed.
- With the checkbox off, next-of-kin and second-contact telephone numbers and addresses, and carer surnames, are replaced by "Withheld until an administrator reviews these third-party details". Carer first names remain.
- The success message is "Subject access file downloaded".

**Result:**

### SU-07 Subject access request, staff

**Role:** Staff  
**Steps:** Open the same service-user list.  
**Expected:** The subject-access button is not shown.  
**Result:**

### SU-08 Delete is administrator only

**Role:** Administrator  
**Steps:** On a disposable test service user, choose **Delete record** and cancel. Repeat the cancel path for a disposable carer.  
**Expected:** Both ask for confirmation. Cancel leaves the record in the list. Staff do not see either delete button.  
**Result:**

---

## 9. Carers

### CARER-01 List, record, and documents

**Role:** Staff  
**Steps:**
1. Open **Management > Carers**. Refresh and export the list.
2. Open a carer. Review Personal, Emergency, and Employment.
3. On an existing carer, open Training, Documents, Rota, and Notes.
4. View a carer document, then download it.

**Expected:** The list and export succeed. Training, Documents, Rota, and Notes appear on an existing record. View shows a previewable file in the page. **Export rota** downloads that carer's rota. Staff do not see delete.  
**Result:**

### CARER-02 Own training row

**Role:** Staff  
**Steps:** Add a training row to a test carer, edit it, then delete it.  
**Expected:** Each step is confirmed by the list. Delete asks for confirmation.  
**Result:**

### CARER-03 Create validation

**Role:** Staff  
**Steps:** Choose **Add Carer**, leave the required name fields empty, and try to create.  
**Expected:** The record is not created. The form shows the missing fields.  
**Result:**

---

## 10. Settings

### SET-01 Every settings screen opens

**Role:** Staff  
**Steps:** Open each Settings item, search for a known value, and choose **Refresh**.

| Menu label | Address |
| --- | --- |
| Shifts Code | `/settings/shifts` |
| Care Types | `/settings/care-types` |
| Medical Conditions | `/settings/medical-conditions` |
| Condition Categories | `/settings/condition-categories` |
| Branches | `/settings/branches` |
| Kinship Relations | `/settings/relations` |
| Genders | `/settings/genders` |
| Religions | `/settings/religions` |
| Training Courses | `/settings/trainings` |
| General Practitioners | `/settings/gp` |
| NHS Commissioners | `/settings/nhs` |
| Service Statuses | `/settings/service-statuses` |
| Pay Rates | `/settings/rates` |
| Employment Types | `/settings/employment-types` |
| Carer Statuses | `/settings/carer-statuses` |
| Resident Statuses | `/settings/resident-statuses` |
| Pension Schemes | `/settings/pension-schemes` |
| Nationalities | `/settings/nationalities` |
| Contract Types | `/settings/contract-types` |
| Employment Requirements | `/settings/requirements` |
| DTR Shifts | `/settings/dtr-shifts` |

**Expected:** Each screen shows its list. Search narrows that list. Refresh reloads it.  
**Result:**

### SET-02 Add, edit, and the branch limit

**Role:** Staff, then Administrator  
**Steps:**
1. As staff, on **Genders**, add a test value, edit it, then delete it.
2. As staff, open **Branches** and confirm add, edit, and delete are absent.
3. As an administrator, add a test branch, edit it, and delete it.

**Expected:** Staff can change a non-branch list. Only an administrator can change branches. Delete asks for confirmation.  
**Result:**

---

## 11. Audit Trail

### AUDIT-01 Page through the trail

**Role:** Administrator  
**Steps:**
1. Open **Audit Trail** from the name menu.
2. Confirm the four summary figures and the first page of rows.
3. Move to the next page. Change the page size from 50 to 25, then to 100.
4. Choose **Refresh Logs**.

**Expected:** The title is "Audit Trail". The summary counts the whole trail, not only the visible page. The pager shows total, page size, previous, and next. Page size choices are 25, 50, and 100. Changing page loads a different set of rows. Refresh reports how many events match. Rows show the service user's name where the event has one, or an em dash where no service user applies. The words "Unknown Patient" are not used as a name.  
**Result:**

### AUDIT-02 Search and category

**Role:** Administrator  
**Steps:**
1. Choose **Medical dossier** in Record Category.
2. Clear it and type a staff name that exists in the trail.
3. Search for a string that matches nothing.
4. Clear the search.

**Expected:** Category and search apply to the whole trail and return to page 1. A search with no matches shows the empty table, while the four summary figures stay at the whole-trail totals. Clearing the search restores the list.  
**Result:**

### AUDIT-03 Export

**Role:** Administrator  
**Steps:** Export CSV with a category selected, then clear the category and confirm the button while the trail has rows.  
**Expected:** The file name starts with `audit_trail_` and ends with `.csv`. The export follows the current filter. If more than 5,000 rows match, the page warns that the first 5,000 were exported. The button is disabled when the filtered total is zero.  
**Result:**

### AUDIT-04 What a new event covers

**Role:** Administrator  
**Steps:** After SU-04 and SU-06, refresh the trail and find the document view and the access-request export by record type. Do not copy the detail text into the results.  
**Expected:** The new rows name the signed-in administrator. Document view and access-request export are present. Opening the service-user list, editing a service user, adding home care, clocking in, and generating payroll do not by themselves add a row. The trail does not contain the body of a care note.  
**Result:**

---

## 12. Privacy notice, account, and user manual

### PRIV-01 Privacy notice

**Role:** any signed-in role, and once while signed out  
**Steps:** Open **Privacy Notice**. Read sections 1 to 8.  
**Expected:** The notice describes this system. It does not show a "UK GDPR & DPA 2018 Compliant" badge. It says care records stay until an authorised disposal and are not deleted on a schedule. It says an external model is used only when an administrator has configured a key. The contact is the data protection officer at dpo@stmarysteamcare.co.uk. **Return to application** leaves the notice.  
**Result:**

### ACCT-01 My Account

**Role:** Staff  
**Steps:**
1. Open **My Account**.
2. Change a non-password field and choose **Reset Changes**.
3. Choose **Update Account** with the new password and confirmation left blank.
4. Enter a new password and a different confirmation. Submit.
5. Enter matching values only if this run is allowed to change the password, then sign out and sign in with it.

**Expected:** Reset Changes restores the loaded values. A blank password update keeps the current password. Mismatched passwords are refused. A successful password change works at the next sign-in.  
**Result:**

### MAN-01 User manual

**Role:** Staff  
**Steps:**
1. Open **User Manual**.
2. Open each section in the left list.
3. Search for "Audit Trail", then for a word that is not in the manual.
4. Clear the search.

**Expected:** The sections describe the current screens, including sign-in, the carer portal, the planner, finance, service users, the access request, and the audit trail. The manual does not say that clock-in records GPS coordinates, that every access is logged, or that the product is DSPT certified. Search shows the matching section. An unknown word shows "No section matches that search."  
**Result:**

---

## 13. Whole journey

Run these after the detailed cases, or on their own as a smoke pass. Each journey ends with **Logout**.

### E2E-01 Administrator

**Steps:** Sign in. Open Dashboard, Carer Portal, Care Rota Planner, Daily Time Record, Generate Payments, Payroll Management, Invoice Management, Service Users, Carers, one Settings screen, Audit Trail, Privacy Notice, User Manual, and My Account. Sign out. Open `/`.  
**Expected:** Every page opens for the administrator. The last step shows the sign-in page.  
**Result:**

### E2E-02 Staff

**Steps:** Sign in. Confirm the planner. Open Carer Portal, Daily Time Record, Service Users, Carers, Branches, Genders, User Manual, Privacy Notice, and My Account. Confirm Finance and Audit Trail are absent. Sign out.  
**Expected:** Staff pages open. Finance and the audit trail do not. Sign-out returns to the sign-in page.  
**Result:**

### E2E-03 Carer

**Steps:** Sign in. Confirm the Carer Portal. Open My Attendance History and Privacy Notice. Open My Account. Confirm the planner, management, settings, and the user manual are absent. Sign out.  
**Expected:** The carer can complete portal, account, and privacy steps, and cannot open the staff pages. Sign-out returns to the sign-in page.  
**Result:**

## Run log

| Case | Result | Tester | Date | Note |
| --- | --- | --- | --- | --- |
| AUTH-01 | | | | |
| AUTH-02 | | | | |
| AUTH-03 | | | | |
| AUTH-04 | | | | |
| AUTH-05 | | | | |
| AUTH-06 | | | | |
| AUTH-07 | | | | |
| AUTH-08 | | | | |
| NAV-01 | | | | |
| NAV-02 | | | | |
| NAV-03 | | | | |
| NAV-04 | | | | |
| DASH-01 | | | | |
| PORTAL-01 | | | | |
| PORTAL-02 | | | | |
| PORTAL-03 | | | | |
| PORTAL-04 | | | | |
| PLAN-01 | | | | |
| PLAN-02 | | | | |
| PLAN-03 | | | | |
| DTR-01 | | | | |
| DTR-02 | | | | |
| DTR-03 | | | | |
| DTR-04 | | | | |
| FIN-01 | | | | |
| FIN-02 | | | | |
| FIN-03 | | | | |
| SU-01 | | | | |
| SU-02 | | | | |
| SU-03 | | | | |
| SU-04 | | | | |
| SU-05 | | | | |
| SU-06 | | | | |
| SU-07 | | | | |
| SU-08 | | | | |
| CARER-01 | | | | |
| CARER-02 | | | | |
| CARER-03 | | | | |
| SET-01 | | | | |
| SET-02 | | | | |
| AUDIT-01 | | | | |
| AUDIT-02 | | | | |
| AUDIT-03 | | | | |
| AUDIT-04 | | | | |
| PRIV-01 | | | | |
| ACCT-01 | | | | |
| MAN-01 | | | | |
| E2E-01 | | | | |
| E2E-02 | | | | |
| E2E-03 | | | | |
