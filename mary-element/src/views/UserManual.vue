<template>
  <div class="user-manual-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><Document /></el-icon>
            <span>Mary Care — User Manual</span>
          </div>
          <el-input
            v-model="searchQuery"
            placeholder="Search the manual..."
            prefix-icon="Search"
            clearable
            style="width: 250px;"
          />
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <el-menu
            :key="activeDoc"
            :default-active="activeDoc"
            class="doc-menu"
            @select="selectDoc"
          >
            <el-menu-item
              v-for="section in visibleSections"
              :key="section.index"
              :index="section.index"
            >
              {{ section.title }}
            </el-menu-item>
          </el-menu>
        </el-col>

        <el-col :span="18">
          <div v-if="activeSection" class="markdown-content" v-html="renderedDoc"></div>
          <el-empty v-else description="No section matches that search." />
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const searchQuery = ref('')
const activeDoc = ref('start')

const sections = [
  {
    index: 'start',
    title: 'Signing in and out',
    body: `
# Signing in and out

Mary Care is the domiciliary care system used by St Mary's Team Carers Ltd. This manual describes the screens in this version.

### Sign in
1. Open the sign-in page.
2. Enter your username and password.
3. Tick **Remember me** when this browser should stay signed in after you close it. Leave it unticked on a shared computer. An unticked sign-in lasts for this browser tab.
4. Choose **Sign In**.

An administrator opens the Dashboard. Staff open the Care Rota Planner. A carer opens the Carer Portal.

### Forgotten password
Choose **Forgot Password?** and enter the email address on the account. The screen says that a reset link has been sent if the address is registered. It uses the same message when the address is not registered. The link expires after 60 minutes. The new password must be at least 8 characters.

### Sign out
Open your name at the top right and choose **Logout**. The sign-in page returns. Use **Logout** when you leave a shared computer.

### Around the page
The header shows the page name, a control to collapse the left menu, and a light or dark theme switch. **My Account** and **Privacy Notice** are in the name menu for every signed-in person. **User Manual** is shown to administrators and staff.
`
  },
  {
    index: 'roles',
    title: 'Who can open what',
    body: `
# Who can open what

| Person | What they can open |
| --- | --- |
| Administrator | Every screen, including finance, the Audit Trail, subject-access copies, and deleting a service user or carer. |
| Staff | The planner, daily time record, service users, carers, settings, and this manual. Branch records can be viewed. Only an administrator can add, edit, or delete a branch. |
| Carer | The Carer Portal, My Account, and the Privacy Notice. |

A page that your role cannot open shows **Access Denied**. Choose the button back to your home page, or **Switch Account** to sign out.
`
  },
  {
    index: 'dashboard',
    title: 'Dashboard',
    body: `
# Dashboard

The Dashboard is for administrators. It shows organisation totals and charts for the selected period.

Choose **Daily**, **Weekly**, or **Monthly**. The totals stay in place. The charts follow the period. **Refresh** loads them again.
`
  },
  {
    index: 'portal',
    title: 'Carer Portal',
    body: `
# Carer Portal

The Carer Portal is where a carer clocks in and out of today's assigned shift.

### Clock in and out
- When a shift is assigned, **Clock In** starts it and **Clock Out** ends it.
- When no shift is assigned, both buttons stay hidden and the page says no active shift is assigned.
- After clock-out, the page says today's attendance is complete.
- Clock-in does not take a map location.

### Care notes
On **Carer Visit Logs & Care Notes**, **Add note** is available after clock-in. The note cannot be empty. You can edit or delete only your own notes. Search matches the note, the author, the service user, or the date.

### History
**My Attendance History** has two lists:
- **Attendance Records** shows clock-in and clock-out times from the last three months.
- **My Scheduled Shifts** shows the shifts assigned to you.

A generated care-note file can be opened by the carer named in that file. Other care-note files stay with staff.
`
  },
  {
    index: 'planner',
    title: 'Care Rota Planner',
    body: `
# Care Rota Planner

Staff use the planner to put carers onto service-user visits.

### Add a shift
Choose **New Shift Assignment**. Select the carer, the service user, a shift code, and the date. Choose **Create Shift**.

Repeat can be **One-Time**, **Daily**, or **Custom Days**. Set the end date for a repeated shift. **Double-Up Shift** records a second carer on the visit.

### Change or remove a shift
Click the shift on the calendar. Choose **Update Shift** to save changes, or **Delete Shift** to remove it. For a repeated shift, the prompt asks whether the change applies to one visit or to the series.

### Other controls
- Refresh reloads the calendar.
- Print opens the browser print view.
- Download saves a CSV of the rota on screen.
- **Bulk Delete Recurrences for Client** removes a repeated series for one service user. It asks you to confirm.
`
  },
  {
    index: 'dtr',
    title: 'Daily Time Record',
    body: `
# Daily Time Record

The Daily Time Record shows visits for a date range. Set the range and refresh the table. Expand or collapse the rows to see each visit. **Download CSV** saves the rows on screen.

### Care-note files
On a visit that does not yet have a file, **Care Notes** opens **Care Plan Generator (Care Notes)**. **Generate Care Plan** builds the PDF from the service user, the carer, the visit, and the observations you type. When an administrator has configured an external model key, that text, including the names, is sent to the provider. With no key, the PDF is produced inside this system. Review the observations before you generate the file.

Where a file already exists, **View Generated Care Note PDF in Browser** opens it on the page. Staff can also remove that file from the visit. A carer does not use this screen.

### Administrator tools
An administrator can generate clock times up to today, and can clear clock times for a row. Both actions ask for confirmation before anything changes.
`
  },
  {
    index: 'finance',
    title: 'Finance and payroll',
    body: `
# Finance and payroll

Finance is limited to administrators. The left menu groups it under **Finance & Payroll**.

### Generate Payments
**Generate Payroll** selects a carer and a date range, lists completed shifts, and prepares a payroll batch. **Generate Invoice** does the same for a service user. Creating the batch asks for confirmation.

### Payroll Management
**Manage Payroll** lists batches that are still open. **Payroll Records** lists the history. **Refresh** reloads the list. **Export All Payroll** downloads a CSV when the list has rows.

### Invoice Management
**Manage Invoices** and **Invoice Records** follow the same pattern for service-user invoices. Export downloads a CSV when the list has rows.
`
  },
  {
    index: 'service-users',
    title: 'Service users',
    body: `
# Service users

Open **Management**, then **Service Users**. **Refresh** reloads the list. **Export list** downloads \`service-users.csv\`.

### The record
**Add Service User** starts a blank record. The first save uses Personal, Contacts, and Service. After the record exists, edit also shows:
- **Health** for conditions, additional notes, home care, and the care-plan text
- **Notes**
- **Documents**

The eye icon opens the record read-only. The pen icon edits it. **Update** saves an existing record. Only an administrator sees **Delete record**, and delete asks for confirmation.

### Home care
A service user can have more than one home care type. The same type cannot be added twice. The second attempt says "This home care type is already assigned".

### Documents
**View** opens a PDF or another previewable file on the page. **Download** saves a copy. Upload and delete are available while you are editing.

### Care plan
**Generate care plan** drafts care text from age, medical conditions, and the current care text. It does not send the person's name or address. Read the draft before you use **Apply to record**. Word, PDF, text, and **Save to documents** are other ways to keep a copy. An external model is used only when an administrator has configured a key. Otherwise the draft stays inside this system.

### Subject access request
Only an administrator sees **Subject access request** on a row.

1. Check the counts for visits, notes, and audit events.
2. Enter the date the request was received. A future date is refused.
3. Enter the reason. It must be at least 8 characters and no more than 500. The reason is stored on the Audit Trail and is not printed in the file.
4. Choose **PDF dossier** or **Spreadsheet copy**.
5. Leave the third-party box unticked unless next-of-kin contact details and carer surnames have been reviewed and should be included. Unticked copies replace those telephone numbers, addresses, and surnames with "Withheld until an administrator reviews these third-party details". Carer first names stay.
6. Choose **Download**. The file is saved to this computer. It is not emailed.

The spreadsheet is another copy of the same access file. It is not a separate portability export.
`
  },
  {
    index: 'carers',
    title: 'Carers',
    body: `
# Carers

Open **Management**, then **Carers**. Refresh and **Export list** work as they do for service users.

**Add Carer** uses Personal, Emergency, and Employment. An existing record also has Training, Documents, Rota, and Notes.

- Add, edit, or delete training rows from **Training**.
- **Documents** can be viewed on the page or downloaded.
- **Export rota** downloads that carer's rota.
- Only an administrator sees **Delete record**.

Creating or editing a carer is not written to the Audit Trail. Downloading a carer document is recorded, without a service-user name.
`
  },
  {
    index: 'settings',
    title: 'Settings',
    body: `
# Settings

Settings hold the lists used by the other screens. Each list has a search box and **Refresh**. Staff can add, edit, and delete rows on these lists. Delete asks for confirmation. Status can be changed while editing.

The lists in the menu are Shifts Code, Care Types, Medical Conditions, Condition Categories, Branches, Kinship Relations, Genders, Religions, Training Courses, General Practitioners, NHS Commissioners, Service Statuses, Pay Rates, Employment Types, Carer Statuses, Resident Statuses, Pension Schemes, Nationalities, Contract Types, Employment Requirements, and DTR Shifts.

**Branches** is the exception. Staff can open the list. Only an administrator can add, edit, or delete a branch.
`
  },
  {
    index: 'audit',
    title: 'Audit Trail',
    body: `
# Audit Trail

Administrators open **Audit Trail** from the name menu.

The four figures at the top count the whole trail: all events, events with a staff identity, medical dossier access, and other recorded events. They do not change when you filter the table.

The table loads one page at a time. The page size can be 25, 50, or 100. The default is 50. Use the pager to move through older events.

### What is recorded
The trail records the signed-in person when someone:
- opens a service-user dossier
- views or downloads a care file
- opens, creates, or deletes a care-note file
- adds, changes, or deletes a clinical note
- changes a medication record
- prepares or downloads an access-request copy

The row stores the time, the action, the record type, and a short detail such as a file name. It does not store the clinical text.

Opening the service-user or carer list, editing those records, uploading or deleting a file, changing home care or conditions, clocking in, changing the rota, and finance work are not written to this trail. Older rows may have no staff name.

### Find and export
The search box matches the service user, the staff name, the action, or the record type. **Record Category** limits the table to one kind of event. Both apply to the whole trail and return to the first page.

**Export CSV** downloads the filtered events. A very large filtered set exports the first 5,000 rows and warns that the rest were left out. **Refresh Logs** reloads the current page and reports how many events match.
`
  },
  {
    index: 'privacy',
    title: 'Privacy and retention',
    body: `
# Privacy and retention

The **Privacy Notice** in the name menu is the description of this system. Read that page for what is stored, who can see a record, the access log, optional use of an external model, how long records are kept, and how to contact the data protection officer.

This software keeps care records until an authorised person disposes of them. It does not delete care records on a schedule, and it has no button that erases a care record automatically. Questions about retention, correction, restriction, or erasure go to the agency's data protection officer, dpo@stmarysteamcare.co.uk.

The sign-in page links to the same notice. The notice is also available before you sign in.
`
  },
  {
    index: 'account',
    title: 'My Account',
    body: `
# My Account

**My Account** shows your name and sign-in details.

**Update Account** saves changes to your profile. Leave the new password blank to keep the current password. When you set a new password, enter the same value in **Confirm New Password**. **Reset Changes** puts the form back to the last loaded values.

After a password change, sign out and sign in with the new password.
`
  }
]

const visibleSections = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return sections
  return sections.filter((section) => `${section.title}\n${section.body}`.toLowerCase().includes(query))
})

const activeSection = computed(() => (
  visibleSections.value.find((section) => section.index === activeDoc.value) || null
))

const renderedDoc = computed(() => {
  if (!activeSection.value) return ''
  return DOMPurify.sanitize(marked.parse(activeSection.value.body))
})

watch(visibleSections, (list) => {
  if (!list.length) return
  if (!list.some((section) => section.index === activeDoc.value)) {
    activeDoc.value = list[0].index
  }
})

function selectDoc(index) {
  activeDoc.value = index
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.title-box {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}
.doc-menu {
  border-right: 1px solid var(--el-border-color-light);
}
.markdown-content {
  padding: 10px 20px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
}
</style>
