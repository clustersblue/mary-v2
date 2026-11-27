<template>
  <div class="privacy-container">
    <el-card shadow="never" class="privacy-card">
      <template #header>
        <div class="flex items-center gap-3">
          <el-icon :size="28" class="text-blue-600"><DocumentChecked /></el-icon>
          <div>
            <h1 class="text-xl font-bold text-gray-800 m-0">Privacy notice</h1>
            <p class="text-xs text-gray-500 m-0 mt-1">
              St Mary's Team Carers Ltd — Mary Care Management System
            </p>
          </div>
        </div>
      </template>

      <div class="policy-body text-gray-700 leading-relaxed space-y-6">
        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">1. What this notice covers</h2>
          <p class="text-sm">
            This notice describes the Mary Care Management System used by St Mary's Team Carers Ltd.
            It covers personal information about service users, their next of kin and other contacts, and carers.
            The agency decides why this information is used and for how long it is kept. This page describes what the software actually does.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">2. What the system stores</h2>
          <p class="text-sm">The system stores:</p>
          <ul class="list-disc pl-5 text-sm space-y-1 mt-2">
            <li>Service user and contact details, including next of kin</li>
            <li>Visits, care notes, conditions, medications, and uploaded care documents</li>
            <li>Invoices and payroll records</li>
            <li>An access log of who opened or changed those records</li>
          </ul>
          <p class="text-sm mt-2">
            Health and care information is used so the agency can arrange and record care.
            The agency, not this page, decides the lawful reason for each use.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">3. Who can see a record</h2>
          <ul class="list-disc pl-5 text-sm space-y-1">
            <li>Administrators can manage the system and prepare an access-request copy.</li>
            <li>Staff and coordinators can open service-user records, documents, and care notes.</li>
            <li>A carer can open a generated care-note file only when that file was created in their name. Other care-note files are limited to staff.</li>
            <li>An access-request copy is prepared by an administrator. The reason for the request is stored on the access log and is not printed in the file. Next-of-kin telephone numbers and addresses, and carer surnames, are left out unless an administrator chooses to include them.</li>
          </ul>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">4. Access log</h2>
          <p class="text-sm">
            When someone opens a dossier, views or downloads a care file, opens a care-note file, changes a note or a medication record, or exports an access-request copy, the system records the signed-in person, the service user when that person is known, the kind of record, the action, the time, and the address the site saw for that connection.
            The log does not store the clinical text itself. It can be changed by someone with database access. It is not a complete history of every screen that was opened before this version.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">5. Optional use of AI</h2>
          <p class="text-sm">
            Two features can call an external model, and only when an administrator has configured an API key.
            If no key is configured, the software uses a built-in template and does not send that text outside the system.
          </p>
          <ul class="list-disc pl-5 text-sm space-y-1 mt-2">
            <li>A care-plan draft sends age, gender, and a clinical summary. Email addresses and telephone numbers are removed from that summary before it is sent.</li>
            <li>A care-note PDF sends the service user's name, the carer's name, the visit times, the care-plan text, and the carer's observations.</li>
          </ul>
          <p class="text-sm mt-2">
            When a key is configured, that text is sent to Google or OpenAI, which are outside the United Kingdom.
            The agency must not enable a key until it has assessed that transfer and the contract with the provider.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">6. How long records are kept</h2>
          <p class="text-sm">
            The software keeps care records until an authorised person disposes of them.
            It does not delete care records on a schedule, and it does not offer a button that erases a care record automatically.
            The agency's retention and disposal design sets out how a manager approves disposal.
            Access-log entries, including the reason for an access request, are kept with the records they describe.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">7. Your requests</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div class="p-3 bg-gray-50 rounded border">
              <strong>Access</strong>
              <p class="text-xs text-gray-600 mt-1">Ask the agency for a copy. An administrator prepares it from the service-user record. There is no automatic email of that file.</p>
            </div>
            <div class="p-3 bg-gray-50 rounded border">
              <strong>Correction</strong>
              <p class="text-xs text-gray-600 mt-1">Ask a coordinator to correct details that are wrong or incomplete.</p>
            </div>
            <div class="p-3 bg-gray-50 rounded border">
              <strong>Restriction or objection</strong>
              <p class="text-xs text-gray-600 mt-1">Contact the data protection officer. The software does not apply a restriction by itself.</p>
            </div>
            <div class="p-3 bg-gray-50 rounded border">
              <strong>Erasure</strong>
              <p class="text-xs text-gray-600 mt-1">Erasure is considered only where the agency has no duty to keep the record. Care records that must be retained are not deleted by this software.</p>
            </div>
          </div>
          <p class="text-sm mt-3">
            A spreadsheet copy is another copy of the same access file. The system does not provide an automatic portability download.
          </p>
        </section>

        <section>
          <h2 class="text-lg font-bold text-gray-900 border-b pb-2 mb-3">8. Contact</h2>
          <p class="text-sm">
            Questions about this system, and requests to exercise your rights, go to the data protection officer.
          </p>
          <div class="p-3 bg-gray-100 rounded text-sm mt-2 font-mono">
            <strong>Data protection officer:</strong> DPO Compliance Team<br/>
            <strong>Email:</strong> dpo@stmarysteamcare.co.uk<br/>
            <strong>Supervisory authority:</strong> Information Commissioner's Office — <a href="https://ico.org.uk" target="_blank" rel="noopener noreferrer" class="text-blue-600 underline">ico.org.uk</a>
          </div>
        </section>

        <div class="pt-4 border-t flex justify-between items-center text-xs text-gray-500">
          <span>Last updated: 22 November 2026</span>
          <el-button size="small" type="primary" plain @click="$router.push('/')">
            Return to application
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { DocumentChecked } from '@element-plus/icons-vue'
</script>

<style scoped>
.privacy-container {
  max-width: 960px;
  margin: 30px auto;
  padding: 0 16px;
}
.privacy-card {
  border-radius: 8px;
}
</style>
