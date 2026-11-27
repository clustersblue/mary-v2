<template>
  <div class="management-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><User /></el-icon>
            <span>Service Users</span>
          </div>
          <div class="actions">
            <el-button type="primary" icon="Plus" @click="openCreateModal">Add Service User</el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-input
          v-model="searchQuery"
          placeholder="Search by name, preferred name, or SU number"
          prefix-icon="Search"
          clearable
          style="width: 340px;"
        />
        <el-select v-model="branchFilter" clearable placeholder="Branch" style="width: 180px;">
          <el-option v-for="item in branches" :key="item.branch_id" :label="item.branch || item.name" :value="item.branch_id" />
        </el-select>
        <el-button icon="Refresh" @click="loadServiceUsers">Refresh</el-button>
        <el-button icon="Download" @click="exportOperationalCsv">Export list</el-button>
      </div>

      <el-table :data="paginatedUsers" row-key="su_id" stripe border v-loading="loading">
        <el-table-column label="Status" width="130" :sort-method="sortBy(statusLabel)" sortable>
          <template #default="scope">
            <el-tag :type="statusTag(statusLabel(scope.row))">{{ statusLabel(scope.row) || 'Unknown' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="su_number" label="SU No." width="110" sortable />
        <el-table-column prop="surname" label="Last Name" min-width="130" sortable />
        <el-table-column prop="first_name" label="First Name" min-width="130" sortable />
        <el-table-column prop="preferred_name" label="Preferred" min-width="120" sortable />
        <el-table-column label="Age" width="80" :sort-method="sortBy(row => calculateAge(row.date_of_birth))" sortable>
          <template #default="scope">{{ calculateAge(scope.row.date_of_birth) }}</template>
        </el-table-column>
        <el-table-column label="Gender" width="110" :sort-method="sortBy(genderLabel)" sortable>
          <template #default="scope">{{ genderLabel(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="Branch" min-width="140" :sort-method="sortBy(branchLabel)" sortable>
          <template #default="scope">{{ branchLabel(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="Actions" width="230" align="center" fixed="right">
          <template #default="scope">
            <el-tooltip content="View record" placement="top">
              <el-button size="small" icon="View" circle @click="openRecord(scope.row, true)" />
            </el-tooltip>
            <el-tooltip content="Edit record" placement="top">
              <el-button size="small" type="primary" icon="EditPen" circle @click="openRecord(scope.row, false)" />
            </el-tooltip>
            <el-tooltip content="Create care plan document" placement="top">
              <el-button size="small" type="success" icon="Document" circle @click="generateCarePlan(scope.row)" />
            </el-tooltip>
            <el-tooltip v-if="authStore.isAdmin" content="Subject access request" placement="top">
              <el-button size="small" type="warning" icon="Tickets" circle @click="openSarModal(scope.row)" />
            </el-tooltip>
            <el-tooltip v-if="authStore.isAdmin" content="Delete record" placement="top">
              <el-button size="small" type="danger" icon="Delete" circle @click="deleteServiceUser(scope.row)" />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container mt-15">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredUsers.length"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="980px"
      top="4vh"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="160px">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="Personal" name="personal">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <p class="required-note">Fields marked with * are required.</p>
              <el-row :gutter="12">
                <el-col v-if="isEdit" :span="8">
                  <el-form-item label="SU Number" prop="su_number"><el-input v-model="form.su_number" /></el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Branch" prop="branch_id">
                    <el-select v-model="form.branch_id" filterable style="width: 100%;">
                      <el-option v-for="item in branches" :key="item.branch_id" :label="item.branch || item.name" :value="item.branch_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col v-if="isEdit" :span="8">
                  <el-form-item label="Status" prop="service_status_id">
                    <el-select v-model="form.service_status_id" style="width: 100%;">
                      <el-option v-for="item in serviceStatuses" :key="item.service_status_id" :label="item.service_status || item.name" :value="item.service_status_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="8"><el-form-item label="Last Name" prop="surname"><el-input v-model="form.surname" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="First Name" prop="first_name"><el-input v-model="form.first_name" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="Preferred Name"><el-input v-model="form.preferred_name" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="Home Address" prop="address">
                <el-input v-model="form.address" type="textarea" :rows="3" />
              </el-form-item>
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="Date of Birth" prop="date_of_birth">
                    <el-date-picker v-model="form.date_of_birth" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Gender" prop="gender_id">
                    <el-select v-model="form.gender_id" style="width: 100%;">
                      <el-option v-for="item in genders" :key="item.gender_id" :label="item.gender || item.name" :value="item.gender_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Marital Status" prop="marital_status_id">
                    <el-select v-model="form.marital_status_id" style="width: 100%;">
                      <el-option v-for="item in maritalStatuses" :key="item.marital_status_id" :label="item.marital_status || item.name" :value="item.marital_status_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="Religion" prop="religion_id">
                    <el-select v-model="form.religion_id" filterable style="width: 100%;">
                      <el-option v-for="item in religions" :key="item.religion_id" :label="item.religion || item.name" :value="item.religion_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Nationality" prop="nationality_id">
                    <el-select v-model="form.nationality_id" filterable style="width: 100%;">
                      <el-option v-for="item in nationalities" :key="item.nationality_id" :label="item.nationality || item.name" :value="item.nationality_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="Contact"><el-input v-model="form.phone" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="Email" prop="email"><el-input v-model="form.email" /></el-form-item>
              <el-form-item label="Biography">
                <el-input v-model="form.care_plan_notes" type="textarea" :rows="6" placeholder="Biography and care preferences. Existing formatted text is kept." />
              </el-form-item>
            </fieldset>
          </el-tab-pane>

          <el-tab-pane label="Contacts" name="contacts">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <el-row :gutter="12">
                <el-col :span="8"><el-form-item label="Next of Kin"><el-input v-model="form.next_of_kin" /></el-form-item></el-col>
                <el-col :span="8">
                  <el-form-item label="Relationship">
                    <el-select v-model="form.nok_relationship" clearable filterable style="width: 100%;">
                      <el-option v-for="item in relations" :key="item.relation_id" :label="item.relation || item.name" :value="item.relation_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="Contact Number"><el-input v-model="form.nok_contact_number" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="NOK Address">
                <el-checkbox v-model="copyNok1">Copy home address</el-checkbox>
                <el-input v-model="form.nok_address" />
              </el-form-item>
              <el-divider />
              <el-row :gutter="12">
                <el-col :span="8"><el-form-item label="Second Contact"><el-input v-model="form.second_contact" /></el-form-item></el-col>
                <el-col :span="8">
                  <el-form-item label="Relationship">
                    <el-select v-model="form.second_contact_relationship" clearable filterable style="width: 100%;">
                      <el-option v-for="item in relations" :key="`second-${item.relation_id}`" :label="item.relation || item.name" :value="item.relation_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="Contact Number"><el-input v-model="form.second_contact_number" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="Second Address">
                <el-checkbox v-model="copyNok2">Copy home address</el-checkbox>
                <el-input v-model="form.second_contact_address" />
              </el-form-item>
            </fieldset>
          </el-tab-pane>

          <el-tab-pane label="Service" name="service">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="Start Date">
                    <el-date-picker v-model="form.service_start_date" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="End Date">
                    <el-date-picker v-model="form.service_end_date" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="Contract"><el-input v-model="form.contract" /></el-form-item></el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="GP">
                    <el-select v-model="form.gp_id" clearable filterable style="width: 100%;">
                      <el-option v-for="item in gps" :key="item.gp_id" :label="personName(item, 'gp_first_name', 'gp_last_name')" :value="item.gp_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="NHS Contact">
                    <el-select v-model="form.nhs_id" clearable filterable style="width: 100%;">
                      <el-option v-for="item in nhsContacts" :key="item.nhs_id" :label="personName(item, 'nhs_first_name', 'nhs_last_name')" :value="item.nhs_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </fieldset>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Health" name="health">
            <div class="section-head">
              <h4>Medical Conditions</h4>
              <el-button v-if="!isViewOnly" size="small" type="primary" icon="Plus" @click="openCondition()">Add</el-button>
            </div>            
            <el-table :data="conditions" size="small" border>
              <el-table-column label="Name" min-width="140"><template #default="scope">{{ scope.row.condition?.name }}</template></el-table-column>
              <el-table-column label="Description" min-width="180"><template #default="scope">{{ scope.row.condition?.description }}</template></el-table-column>
              <el-table-column label="Category" width="140"><template #default="scope">{{ scope.row.category?.name }}</template></el-table-column>
              <el-table-column label="Diagnosed" width="120"><template #default="scope">{{ formatDate(scope.row.diagnosis_date) }}</template></el-table-column>
              <el-table-column label="Primary" width="90"><template #default="scope"><el-tag v-if="scope.row.is_primary === 1" type="success">Primary</el-tag></template></el-table-column>
              <el-table-column v-if="!isViewOnly" label="" width="110">
                <template #default="scope">
                  <el-button size="small" icon="Edit" circle @click="openCondition(scope.row)" />
                  <el-button size="small" type="danger" icon="Delete" circle @click="deleteCondition(scope.row)" />
                </template>
              </el-table-column>
            </el-table>
            <el-divider />
            <h4 class="mt-15">Additional Notes</h4>
            <QuillEditor
              v-model:content="form.medical_history"
              class="health-editor"
              content-type="html"
              theme="snow"
              :read-only="isViewOnly"
              :toolbar="isViewOnly ? false : careEditorToolbar"
              @ready="onNotesReady"
              @update:content="markNotesEdit"
            />
            <el-divider />
            <div class="section-head">
              <h4>Home Care</h4>
              <el-button v-if="!isViewOnly" size="small" type="primary" icon="Plus" @click="openCare()">Add</el-button>
            </div>
            <el-table :data="careTypes" size="small" border>
              <el-table-column label="Name" min-width="160"><template #default="scope">{{ scope.row.care_type?.name }}</template></el-table-column>
              <el-table-column label="Description" min-width="220"><template #default="scope">{{ scope.row.care_type?.description }}</template></el-table-column>
              <el-table-column v-if="!isViewOnly" label="" width="110">
                <template #default="scope">
                  <el-button size="small" icon="Edit" circle @click="openCare(scope.row)" />
                  <el-button size="small" type="danger" icon="Delete" circle @click="deleteCare(scope.row)" />
                </template>
              </el-table-column>
            </el-table>
            <el-divider />
            <div class="section-head mt-15">
              <h4>Care Services and Medications</h4>
              <el-button v-if="!isViewOnly" size="small" type="success" icon="MagicStick" :loading="aiLoading" @click="checkAndGenerateAiCarePlan">Generate care plan</el-button>
            </div>
            <p class="hint">Generating a care plan uses age, medical conditions, and the current care text. It does not send the person's name or address. A coordinator must review the result before it is saved.</p>
            <QuillEditor
              v-model:content="form.medications_json"
              class="health-editor medications-editor"
              content-type="html"
              theme="snow"
              :read-only="isViewOnly"
              :toolbar="isViewOnly ? false : careEditorToolbar"
              @ready="onMedicationsReady"
              @update:content="markMedicationsEdit"
            />
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Notes" name="notes">
            <div class="section-head">
              <h4>Care notes</h4>
              <el-button v-if="!isViewOnly" size="small" type="primary" icon="Plus" @click="openNote()">Add note</el-button>
            </div>
            <el-input v-model="noteSearch" clearable placeholder="Search notes, author, service user, or date" class="note-search" />
            <el-table :data="visibleNotes" size="small" border :empty-text="noteSearch.trim() ? 'No matching care notes' : 'No care notes'">
              <el-table-column label="When" min-width="200"><template #default="scope">{{ formatNoteWhen(scope.row.created_at || scope.row.updated_at) }}</template></el-table-column>
              <el-table-column label="Author" width="160"><template #default="scope">{{ `${scope.row.user?.first_name || ''} ${scope.row.user?.surname || ''}`.trim() }}</template></el-table-column>
              <el-table-column prop="notes" label="Note" min-width="240" />
              <el-table-column v-if="!isViewOnly" label="" width="110">
                <template #default="scope">
                  <el-button size="small" icon="Edit" circle @click="openNote(scope.row)" />
                  <el-button size="small" type="danger" icon="Delete" circle @click="deleteNote(scope.row)" />
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Documents" name="documents">
            <div class="section-head">
              <div>
                <el-upload v-if="!isViewOnly" :auto-upload="false" :show-file-list="false" :on-change="onFilePicked" accept=".doc,.docx,.pdf,.txt,.png,.jpg,.jpeg,.gif,.webp,.html">
                  <el-button type="primary" icon="Upload">Upload</el-button>
                </el-upload>
                <p class="hint">Word, image, PDF, text, or HTML. Maximum 20 MB.</p>
              </div>
            </div>
            <el-table :data="files" size="small" border empty-text="No documents">
              <el-table-column prop="filename" label="File" min-width="260" />
              <el-table-column label="" width="160" align="right">
                <template #default="scope">
                  <el-button size="small" icon="View" circle @click="viewFile(scope.row.filename)" />
                  <el-button size="small" icon="Download" circle @click="downloadFile(scope.row.filename)" />
                  <el-button v-if="!isViewOnly" size="small" type="danger" icon="Delete" circle @click="deleteFile(scope.row.filename)" />
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Visits" name="visits">
            <el-table :data="visits" size="small" border empty-text="No open visits">
              <el-table-column label="Date" min-width="160"><template #default="scope">{{ formatDateTime(scope.row.start) }}</template></el-table-column>
              <el-table-column prop="carer_full_name" label="Carer" min-width="150" />
              <el-table-column prop="shift" label="Service" min-width="120" />
              <el-table-column prop="rate" label="Rate" width="90" />
              <el-table-column label="Time in" width="100"><template #default="scope">{{ formatTime(scope.row.time_in) }}</template></el-table-column>
              <el-table-column label="Time out" width="100"><template #default="scope">{{ formatTime(scope.row.time_out) }}</template></el-table-column>
            </el-table>
            <p class="hint">This is the same open-visit list used when a care plan document is created.</p>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ isViewOnly ? 'Close' : 'Cancel' }}</el-button>
        <el-button v-if="!isViewOnly" type="primary" :loading="saving" @click="saveServiceUser">{{ isEdit ? 'Update' : 'Create' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="conditionDialog" :title="conditionForm.patient_condition_id ? 'Edit medical condition' : 'Add medical condition'" width="520px">
      <el-form label-width="140px">
        <el-form-item label="Condition" required>
          <el-select v-model="conditionForm.condition_id" filterable style="width: 100%;">
            <el-option v-for="item in medicalConditions" :key="item.condition_id" :label="item.name" :value="item.condition_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Category" required>
          <el-select v-model="conditionForm.category_id" filterable style="width: 100%;">
            <el-option v-for="item in categories" :key="item.category_id" :label="item.name" :value="item.category_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Diagnosis Date">
          <el-date-picker v-model="conditionForm.diagnosis_date" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="Primary"><el-switch v-model="conditionForm.is_primary" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="conditionDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveCondition">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="careDialog" :title="careForm.patient_care_type_id ? 'Edit home care' : 'Add home care'" width="480px">
      <el-form label-width="120px">
        <el-form-item label="Care Type" required>
          <el-select v-model="careForm.care_type_id" filterable style="width: 100%;">
            <el-option v-for="item in careTypeOptions" :key="item.care_type_id" :label="item.name" :value="item.care_type_id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="careDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveCare">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="noteDialog" :title="noteForm.id ? 'Edit note' : 'Add note'" width="560px">
      <el-input v-model="noteForm.notes" type="textarea" :rows="5" />
      <template #footer>
        <el-button @click="noteDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveNote">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="previewName" width="80%" top="4vh" @closed="closePreview">
      <iframe v-if="previewUrl" :src="previewUrl" class="preview-frame" />
      <template #footer><el-button @click="previewVisible = false">Close</el-button></template>
    </el-dialog>

    <el-dialog v-model="aiDialog" title="Generated care plan" width="860px" top="4vh">
      <p class="hint">Review this plan before it is stored. It was built without the person's name, address, or telephone number.</p>
      <div class="ai-preview" v-html="safeCarePlan"></div>
      <div class="ai-actions">
        <el-button size="small" @click="downloadAiCarePlan('doc')">Word</el-button>
        <el-button size="small" @click="downloadAiCarePlan('pdf')">PDF</el-button>
        <el-button size="small" @click="downloadAiCarePlan('txt')">Text</el-button>
        <el-button size="small" :loading="docUploading" @click="saveCarePlanToDocuments">Save to documents</el-button>
      </div>
      <template #footer>
        <el-button @click="aiDialog = false">Close</el-button>
        <el-button type="primary" @click="applyCarePlan">Apply to record</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="sarDialogVisible" :title="`Subject access request: ${selectedSarUser?.first_name || ''} ${selectedSarUser?.surname || ''}`" width="720px">
      <div v-loading="sarLoading">
        <el-alert title="UK GDPR Article 15" type="info" :closable="false" show-icon description="Administrators can prepare a copy for an access request. The reason is stored on the audit record and is not printed in the file." style="margin-bottom: 16px;" />
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Name">{{ sarSummary?.patient_name || fullName(selectedSarUser) }}</el-descriptions-item>
          <el-descriptions-item label="SU Number">{{ sarSummary?.su_number || selectedSarUser?.su_number || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="Visits">{{ sarSummary?.transactions_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="Notes">{{ sarSummary?.notes_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="Audit events">{{ sarSummary?.audit_logs_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="Prepared">{{ sarSummary?.generated_at || 'Live' }}</el-descriptions-item>
        </el-descriptions>
        <el-form label-position="top" class="mt-15">
          <el-form-item label="Request received" required>
            <el-date-picker v-model="sarRequestDate" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" placeholder="Date the request was received" style="width: 100%;" />
          </el-form-item>
          <el-form-item label="Reason for this copy" required>
            <el-input v-model="sarReason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="Who asked, and why this copy is being made" />
          </el-form-item>
          <el-form-item label="File">
            <el-radio-group v-model="sarExportFormat">
              <el-radio-button label="pdf">PDF dossier</el-radio-button>
              <el-radio-button label="excel">Spreadsheet copy</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-checkbox v-model="sarIncludeThirdParties" class="sar-third-party">Include next-of-kin contact details and carer surnames. Leave this off unless those third-party details have been reviewed and should be in this copy.</el-checkbox>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="sarDialogVisible = false">Close</el-button>
        <el-button type="success" icon="Download" :loading="sarDownloading" :disabled="!sarReady" @click="downloadSarExport">Download</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import DOMPurify from 'dompurify'
import { saveAs } from 'file-saver'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const careEditorToolbar = [
  ['bold', 'italic'],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['link', 'clean']
]
let notesQuill = null
let medicationsQuill = null
let notesFromEditor = false
let medicationsFromEditor = false

function loadQuillHtml(quill, html) {
  if (!quill) return
  const delta = quill.clipboard.convert({ html: html || '' })
  quill.setContents(delta, 'silent')
}
function onNotesReady(quill) {
  notesQuill = quill
  loadQuillHtml(quill, form.value.medical_history)
  quill.enable(!isViewOnly.value)
}
function onMedicationsReady(quill) {
  medicationsQuill = quill
  loadQuillHtml(quill, form.value.medications_json)
  quill.enable(!isViewOnly.value)
}
function markNotesEdit() {
  notesFromEditor = true
}
function markMedicationsEdit() {
  medicationsFromEditor = true
}

const authStore = useAuthStore()
const serviceUsers = ref([])
const searchQuery = ref('')
const branchFilter = ref(null)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const isViewOnly = ref(false)
const editingId = ref(null)
const activeTab = ref('personal')
const formRef = ref(null)
const currentPage = ref(1)
const pageSize = ref(10)

const branches = ref([])
const genders = ref([])
const religions = ref([])
const nationalities = ref([])
const maritalStatuses = ref([])
const serviceStatuses = ref([])
const relations = ref([])
const gps = ref([])
const nhsContacts = ref([])
const medicalConditions = ref([])
const categories = ref([])
const careTypeOptions = ref([])

const conditions = ref([])
const careTypes = ref([])
const notes = ref([])
const noteSearch = ref('')
const files = ref([])
const visits = ref([])
const copyNok1 = ref(false)
const copyNok2 = ref(false)
const suppressCopy = ref(false)

const conditionDialog = ref(false)
const conditionForm = ref({})
const careDialog = ref(false)
const careForm = ref({})
const noteDialog = ref(false)
const noteForm = ref({ id: null, notes: '' })
const noteBusy = ref(false)

const previewVisible = ref(false)
const previewUrl = ref('')
const previewName = ref('')
const aiDialog = ref(false)
const aiLoading = ref(false)
const aiCarePlan = ref('')
const aiIsMock = ref(false)
const docUploading = ref(false)

const sarDialogVisible = ref(false)
const selectedSarUser = ref(null)
const sarSummary = ref(null)
const sarLoading = ref(false)
const sarDownloading = ref(false)
const sarExportFormat = ref('pdf')
const sarRequestDate = ref('')
const sarReason = ref('')
const sarIncludeThirdParties = ref(false)
const sarReady = computed(() => sarReason.value.trim().length >= 8 && /^\d{4}-\d{2}-\d{2}$/.test(sarRequestDate.value || ''))

const SU_EXTENSIONS = ['doc', 'docx', 'pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'html']
const PREVIEW_EXTENSIONS = ['pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'html']

function emptyForm() {
  return {
    su_number: '', first_name: '', surname: '', preferred_name: '', branch_id: null,
    service_status_id: null, address: '', date_of_birth: '', gender_id: null,
    marital_status_id: null, religion_id: null, nationality_id: null, phone: '', email: '',
    next_of_kin: '', nok_address: '', nok_relationship: null, nok_contact_number: '',
    second_contact: '', second_contact_address: '', second_contact_number: '',
    second_contact_relationship: null, service_start_date: '', service_end_date: '',
    gp_id: null, nhs_id: null, contract: '', care_plan_notes: '', medical_history: '',
    medications_json: '', services_provided: ''
  }
}
const form = ref(emptyForm())
const visibleNotes = computed(() => {
  const query = noteSearch.value.trim().toLowerCase()
  if (!query) return notes.value
  const serviceUserName = `${form.value.first_name || ''} ${form.value.surname || ''}`.trim()
  return notes.value.filter(row => {
    const when = formatNoteWhen(row.created_at || row.updated_at)
    const author = `${row.user?.first_name || ''} ${row.user?.surname || ''}`.trim()
    const serviceUser = row.service_user?.full_name || serviceUserName
    return [when, row.created_at, row.updated_at, author, serviceUser, row.notes].join(' ').toLowerCase().includes(query)
  })
})
watch(() => form.value.medical_history, (html) => {
  if (notesFromEditor) {
    notesFromEditor = false
    return
  }
  loadQuillHtml(notesQuill, html)
}, { flush: 'post' })
watch(() => form.value.medications_json, (html) => {
  if (medicationsFromEditor) {
    medicationsFromEditor = false
    return
  }
  loadQuillHtml(medicationsQuill, html)
}, { flush: 'post' })
watch(dialogVisible, (open) => {
  if (!open) {
    notesQuill = null
    medicationsQuill = null
  }
})

const optionalEmail = (rule, value, callback) => {
  if (!value) callback()
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) callback(new Error('Enter a valid email'))
  else callback()
}
const rules = computed(() => ({
  branch_id: [{ required: true, message: 'Branch is required', trigger: 'change' }],
  surname: [{ required: true, message: 'Last name is required', trigger: 'blur' }],
  first_name: [{ required: true, message: 'First name is required', trigger: 'blur' }],
  address: [{ required: true, message: 'Home address is required', trigger: 'blur' }],
  date_of_birth: [{ required: true, message: 'Date of birth is required', trigger: 'change' }],
  gender_id: [{ required: true, message: 'Gender is required', trigger: 'change' }],
  marital_status_id: [{ required: true, message: 'Marital status is required', trigger: 'change' }],
  religion_id: [{ required: true, message: 'Religion is required', trigger: 'change' }],
  nationality_id: [{ required: true, message: 'Nationality is required', trigger: 'change' }],
  email: [{ validator: optionalEmail, trigger: 'blur' }],
  ...(isEdit.value ? {
    su_number: [{ required: true, message: 'SU number is required', trigger: 'blur' }],
    service_status_id: [{ required: true, message: 'Status is required', trigger: 'change' }]
  } : {})
}))

const dialogTitle = computed(() => {
  if (isViewOnly.value) return `Service user ${form.value.su_number || editingId.value || ''}`
  return isEdit.value ? `Edit service user ${form.value.su_number || ''}` : 'New service user'
})
const safeCarePlan = computed(() => DOMPurify.sanitize(aiCarePlan.value || ''))

function lookupName(list, idKey, id, labelKey) {
  const found = list.find(item => item[idKey] === id)
  return found ? (found[labelKey] || found.name || '') : ''
}
function statusLabel(row) {
  return row?.service_status?.status_name || row?.service_status?.name || lookupName(serviceStatuses.value, 'service_status_id', row?.service_status_id, 'service_status')
}
function genderLabel(row) {
  return row?.gender?.gender_name || row?.gender?.name || lookupName(genders.value, 'gender_id', row?.gender_id, 'gender')
}
function branchLabel(row) {
  return row?.branch?.branch_name || row?.branch?.name || lookupName(branches.value, 'branch_id', row?.branch_id, 'branch')
}
function personName(item, first, last) {
  return `${item?.[first] || ''} ${item?.[last] || ''}`.trim() || item?.name || ''
}
function fullName(row) {
  return `${row?.first_name || ''} ${row?.surname || ''}`.trim()
}
function statusTag(status) {
  if (status === 'Passed Away') return 'info'
  if (status === 'Terminated') return 'danger'
  if (status === 'Hiatus') return 'warning'
  return 'success'
}
function sortBy(getter) {
  return (a, b) => String(getter(a) ?? '').localeCompare(String(getter(b) ?? ''), undefined, { numeric: true })
}
function asDateInput(value) {
  if (!value) return ''
  return String(value).slice(0, 10)
}
function formatDate(value) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
  return match ? `${match[3]}/${match[2]}/${match[1]}` : (value ? String(value) : '')
}
function formatDateTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('en-GB')
}
function formatNoteWhen(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  let hours = date.getHours()
  const suffix = hours >= 12 ? 'PM' : 'AM'
  hours = hours % 12 || 12
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()} ${String(hours).padStart(2, '0')}:${minutes} ${suffix}`
}
function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString('en-GB')
}
function calculateAge(value) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return ''
  const birth = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  if (today.getMonth() < birth.getMonth() || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) age -= 1
  return age < 0 ? '' : age
}
function errorText(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map(item => item.msg || item).join('\n')
  if (typeof detail === 'string') return detail
  return error.response?.data?.message || error.message || 'Request failed'
}
function plainText(value) {
  const node = document.createElement('div')
  node.innerHTML = value || ''
  return node.textContent?.trim() || 'N/A'
}
function escapeHtml(value) {
  return String(value ?? 'N/A').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const filteredUsers = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return serviceUsers.value.filter(row => {
    if (branchFilter.value && row.branch_id !== branchFilter.value) return false
    if (!query) return true
    const haystack = [row.su_number, row.first_name, row.surname, row.preferred_name, statusLabel(row), branchLabel(row)].join(' ').toLowerCase()
    return haystack.includes(query)
  })
})
const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredUsers.value.slice(start, start + pageSize.value)
})
watch([searchQuery, branchFilter, pageSize], () => { currentPage.value = 1 })
watch(copyNok1, value => { if (!suppressCopy.value) form.value.nok_address = value ? form.value.address : '' })
watch(copyNok2, value => { if (!suppressCopy.value) form.value.second_contact_address = value ? form.value.address : '' })

async function loadLookups() {
  const requests = [
    ['/getbranches', branches], ['/getgenders', genders], ['/get-religions', religions],
    ['/getnationalities', nationalities], ['/getmaritalstatuses', maritalStatuses],
    ['/getservicestatuses', serviceStatuses], ['/getrelations', relations],
    ['/getgps', gps], ['/getnhs', nhsContacts], ['/medical-conditions', medicalConditions],
    ['/condition-categories', categories], ['/care-types', careTypeOptions]
  ]
  await Promise.all(requests.map(async ([url, target]) => {
    try {
      const response = await api.get(url)
      target.value = Array.isArray(response.data) ? response.data : (response.data?.data || [])
    } catch (error) {
      target.value = []
    }
  }))
}

async function loadServiceUsers() {
  loading.value = true
  try {
    const response = await api.get('/getsu')
    serviceUsers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    serviceUsers.value = []
    ElMessage.error(errorText(error))
  } finally {
    loading.value = false
  }
}

function exportOperationalCsv() {
  const columns = ['Status', 'SU No.', 'Last Name', 'First Name', 'Preferred', 'Age', 'Gender', 'Branch']
  const lines = filteredUsers.value.map(row => [
    statusLabel(row), row.su_number, row.surname, row.first_name, row.preferred_name,
    calculateAge(row.date_of_birth), genderLabel(row), branchLabel(row)
  ].map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(','))
  const blob = new Blob([[columns.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' })
  saveAs(blob, 'service-users.csv')
}

function fillForm(row) {
  const next = emptyForm()
  Object.keys(next).forEach(key => {
    if (row[key] !== undefined && row[key] !== null) next[key] = row[key]
  })
  next.date_of_birth = asDateInput(row.date_of_birth)
  next.service_start_date = asDateInput(row.service_start_date)
  next.service_end_date = asDateInput(row.service_end_date)
  return next
}

async function openRecord(row, viewOnly) {
  suppressCopy.value = true
  copyNok1.value = false
  copyNok2.value = false
  suppressCopy.value = false
  isEdit.value = true
  isViewOnly.value = viewOnly
  editingId.value = row.su_id
  form.value = fillForm(row)
  activeTab.value = 'personal'
  dialogVisible.value = true
  try {
    await Promise.all([loadConditions(), loadCare(), loadNotes(), loadFiles(), loadVisits()])
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}

function openCreateModal() {
  suppressCopy.value = true
  copyNok1.value = false
  copyNok2.value = false
  suppressCopy.value = false
  isEdit.value = false
  isViewOnly.value = false
  editingId.value = null
  form.value = emptyForm()
  conditions.value = []
  careTypes.value = []
  notes.value = []
  files.value = []
  visits.value = []
  activeTab.value = 'personal'
  dialogVisible.value = true
}

async function saveServiceUser() {
  const valid = await formRef.value.validate().then(() => true).catch(() => false)
  if (!valid) {
    ElMessage.warning('Complete the required personal details before saving')
    activeTab.value = 'personal'
    return
  }
  saving.value = true
  const body = { ...form.value }
  ;['date_of_birth', 'service_start_date', 'service_end_date'].forEach(key => { if (!body[key]) body[key] = null })
  try {
    if (isEdit.value) {
      await api.put(`/service-users/${editingId.value}`, body)
      ElMessage.success('Service user updated')
    } else {
      body.service_status_id = 1
      await api.post('/service-users', body)
      ElMessage.success('Service user created')
    }
    dialogVisible.value = false
    await loadServiceUsers()
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    saving.value = false
  }
}

async function deleteServiceUser(row) {
  try {
    await ElMessageBox.confirm(`Delete the record for ${fullName(row)}?`, 'Confirm delete', { type: 'warning' })
    await api.delete(`/service-users/${row.su_id}`)
    ElMessage.success('Service user deleted')
    await loadServiceUsers()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}

async function loadConditions() {
  const response = await api.get(`/patient-conditions/by-user/${editingId.value}`)
  conditions.value = response.data?.data || []
}
async function loadCare() {
  const response = await api.get(`/patient-care-types/by-user/${editingId.value}`)
  careTypes.value = response.data?.data?.patientCareTypes || []
}
async function loadNotes() {
  const response = await api.get('/get-notes', { params: { su_id: editingId.value } })
  notes.value = Array.isArray(response.data) ? response.data : []
}
async function loadFiles() {
  const number = form.value.su_number || editingId.value
  const response = await api.get(`/files/${encodeURIComponent(`su_${number}`)}`)
  const names = Array.isArray(response.data) ? response.data : []
  files.value = names.filter(Boolean).map(filename => ({ filename }))
}
async function loadVisits() {
  const response = await api.get('/getserviceuserdtrs', { params: { suId: editingId.value } })
  visits.value = Array.isArray(response.data) ? response.data : []
}

function openCondition(row) {
  conditionForm.value = row ? {
    patient_condition_id: row.patient_condition_id,
    condition_id: row.condition_id,
    category_id: row.category_id,
    diagnosis_date: asDateInput(row.diagnosis_date),
    is_primary: row.is_primary === 1
  } : { condition_id: null, category_id: null, diagnosis_date: '', is_primary: false }
  conditionDialog.value = true
}
async function saveCondition() {
  if (!conditionForm.value.condition_id || !conditionForm.value.category_id) {
    ElMessage.warning('Choose a medical condition and a category')
    return
  }
  const body = {
    su_id: editingId.value,
    condition_id: conditionForm.value.condition_id,
    category_id: conditionForm.value.category_id,
    diagnosis_date: conditionForm.value.diagnosis_date || null,
    is_primary: conditionForm.value.is_primary ? 1 : 0
  }
  try {
    if (conditionForm.value.patient_condition_id) await api.put(`/patient-conditions/${conditionForm.value.patient_condition_id}`, body)
    else await api.post('/patient-conditions', body)
    conditionDialog.value = false
    await loadConditions()
    ElMessage.success('Medical condition saved')
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function deleteCondition(row) {
  try {
    await ElMessageBox.confirm('Delete this medical condition?', 'Confirm delete', { type: 'warning' })
    await api.delete(`/patient-conditions/${row.patient_condition_id}`)
    await loadConditions()
    ElMessage.success('Medical condition deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}

function openCare(row) {
  careForm.value = row ? { patient_care_type_id: row.patient_care_type_id, care_type_id: row.care_type_id } : { care_type_id: null }
  careDialog.value = true
}
async function saveCare() {
  if (!careForm.value.care_type_id) {
    ElMessage.warning('Choose a care type')
    return
  }
  const body = { su_id: editingId.value, care_type_id: careForm.value.care_type_id }
  try {
    if (careForm.value.patient_care_type_id) await api.put(`/patient-care-types/${careForm.value.patient_care_type_id}`, body)
    else await api.post('/patient-care-types', body)
    careDialog.value = false
    await loadCare()
    ElMessage.success('Home care saved')
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function deleteCare(row) {
  try {
    await ElMessageBox.confirm('Delete this home care record?', 'Confirm delete', { type: 'warning' })
    await api.delete(`/patient-care-types/${row.patient_care_type_id}`)
    await loadCare()
    ElMessage.success('Home care deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}

function openNote(row) {
  noteForm.value = row ? { id: row.id, notes: row.notes } : { id: null, notes: '' }
  noteDialog.value = true
}
async function saveNote() {
  if (!noteForm.value.notes || !noteForm.value.notes.trim()) {
    ElMessage.warning('Note cannot be empty')
    return
  }
  try {
    if (noteForm.value.id) await api.post(`/update-notes/${noteForm.value.id}`, { notes: noteForm.value.notes })
    else await api.post('/notes', { su_id: editingId.value, user_id: authStore.user?.id, notes: noteForm.value.notes })
    noteDialog.value = false
    await loadNotes()
    ElMessage.success('Note saved')
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function deleteNote(row) {
  if (noteBusy.value) return
  noteBusy.value = true
  try {
    await ElMessageBox.confirm('Delete this note?', 'Confirm delete', { type: 'warning' })
    await api.delete(`/notes/${row.id}`)
    await loadNotes()
    ElMessage.success('Note deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  } finally {
    noteBusy.value = false
  }
}

function fileExtension(filename) {
  return String(filename).split('.').pop().toLowerCase()
}
async function onFilePicked(uploadFile) {
  const file = uploadFile.raw
  if (!file) return
  const extension = fileExtension(file.name)
  if (!SU_EXTENSIONS.includes(extension) || file.size > 20000000) {
    ElMessage.error('Use a Word, image, PDF, text, or HTML file smaller than 20 MB')
    return
  }
  const reader = new FileReader()
  reader.onload = async () => {
    const safeName = `su_${form.value.su_number}_${file.name.replace(/[^a-zA-Z0-9._-]/g, '')}`
    try {
      await api.post('/upload', { base64data: reader.result, filename: safeName })
      ElMessage.success('Document uploaded')
      await loadFiles()
    } catch (error) {
      ElMessage.error(errorText(error))
    }
  }
  reader.readAsDataURL(file)
}
async function fetchFileBlob(filename) {
  const response = await api.get(`/download/${encodeURIComponent(filename)}`, { responseType: 'blob' })
  const type = response.headers['content-type'] || 'application/octet-stream'
  return new Blob([response.data], { type })
}
async function downloadFile(filename) {
  try {
    const blob = await fetchFileBlob(filename)
    saveAs(blob, filename)
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function viewFile(filename) {
  try {
    const blob = await fetchFileBlob(filename)
    const extension = fileExtension(filename)
    if (!PREVIEW_EXTENSIONS.includes(extension)) {
      ElMessage.info('This file type opens as a download')
      saveAs(blob, filename)
      return
    }
    closePreview()
    previewUrl.value = window.URL.createObjectURL(blob)
    previewName.value = filename
    previewVisible.value = true
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
function closePreview() {
  if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewName.value = ''
}
async function deleteFile(filename) {
  try {
    await ElMessageBox.confirm(`Delete ${filename}?`, 'Confirm delete', { type: 'warning' })
    await api.delete(`/deleteFile/${encodeURIComponent(filename)}`)
    await loadFiles()
    ElMessage.success('Document deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}

async function checkAndGenerateAiCarePlan() {
  const existing = (form.value.medications_json || '').replace(/<p><br><\/p>/g, '').trim()
  if (existing) {
    try {
      await ElMessageBox.confirm('A care plan is already stored. Generating a new preview replaces the text in this window. Continue?', 'Existing care plan', { type: 'warning' })
    } catch (error) {
      return
    }
  }
  await triggerAiGeneration()
}
async function triggerAiGeneration() {
  aiLoading.value = true
  try {
    const response = await api.post('/service-users/generate-ai-care-plan', {
      age: calculateAge(form.value.date_of_birth),
      gender: genderLabel(form.value) || 'Not specified',
      medical_conditions: conditions.value.map(item => ({
        name: item.condition?.name || 'N/A',
        description: item.condition?.description || 'N/A',
        category: item.category?.name || 'N/A',
        diagnosis_date: item.diagnosis_date || 'N/A',
        is_primary: item.is_primary === 1 ? 'Yes' : 'No'
      })),
      current_medications: form.value.medications_json || '',
      medical_history: form.value.medical_history || '',
      su_notes: form.value.care_plan_notes || '',
      services_provided: form.value.services_provided || ''
    })
    aiCarePlan.value = response.data.care_plan || ''
    aiIsMock.value = Boolean(response.data.is_mock)
    aiDialog.value = true
    ElMessage[aiIsMock.value ? 'warning' : 'success'](aiIsMock.value ? 'A standard care plan was prepared because the AI service was unavailable' : 'Care plan generated')
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    aiLoading.value = false
  }
}
function carePlanFilename(extension) {
  const number = form.value.su_number || '00000'
  const name = fullName(form.value).replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').toUpperCase() || 'CLIENT'
  const now = new Date()
  const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  return `su_${number}_${name}_CARE_PLAN_${stamp}.${extension}`
}
function downloadAiCarePlan(format) {
  const html = safeCarePlan.value
  if (format === 'txt') {
    const node = document.createElement('div')
    node.innerHTML = html
    saveAs(new Blob([node.innerText || ''], { type: 'text/plain;charset=utf-8' }), carePlanFilename('txt'))
    return
  }
  if (format === 'pdf') {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    printWindow.document.write(`<html><head><title>Care plan</title></head><body>${html}</body></html>`)
    printWindow.document.close()
    printWindow.focus()
    setTimeout(() => printWindow.print(), 400)
    return
  }
  const documentHtml = `<html><head><meta charset="utf-8"></head><body>${html}</body></html>`
  saveAs(new Blob(['\ufeff' + documentHtml], { type: 'application/msword' }), carePlanFilename('doc'))
}
async function saveCarePlanToDocuments() {
  if (!aiCarePlan.value || !editingId.value) return
  docUploading.value = true
  try {
    const filename = carePlanFilename('html')
    const html = `<!DOCTYPE html><html><body>${safeCarePlan.value}</body></html>`
    const base64 = `data:text/html;base64,${btoa(unescape(encodeURIComponent(html)))}`
    await api.post('/upload', { base64data: base64, filename })
    await loadFiles()
    ElMessage.success('Care plan saved to documents')
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    docUploading.value = false
  }
}
async function applyCarePlan() {
  try {
    await ElMessageBox.confirm('Save this plan into medications and care services, and add an audit note?', 'Update record', {
      confirmButtonText: 'Update record',
      cancelButtonText: 'Keep in the editor only',
      distinguishCancelAndClose: true,
      type: 'warning'
    })
    await api.post(`/updatesu-medications/${editingId.value}`, {
      medications: aiCarePlan.value,
      user_id: authStore.user?.id
    })
    form.value.medications_json = aiCarePlan.value
    await loadNotes()
    aiDialog.value = false
    ElMessage.success('Medications and care services updated')
  } catch (error) {
    if (error === 'cancel') {
      form.value.medications_json = aiCarePlan.value
      aiDialog.value = false
      ElMessage.info('Plan placed in the editor. Save the service user record to store it.')
    } else if (error !== 'close') {
      ElMessage.error(errorText(error))
    }
  }
}

async function generateCarePlan(row) {
  try {
    await ElMessageBox.confirm(`Create a care plan document for ${fullName(row)}?`, row.su_number || 'Care plan', { confirmButtonText: 'Generate' })
  } catch (error) {
    return
  }
  try {
    const [conditionResponse, careResponse, noteResponse, visitResponse] = await Promise.all([
      api.get(`/patient-conditions/by-user/${row.su_id}`),
      api.get(`/patient-care-types/by-user/${row.su_id}`),
      api.get('/get-notes', { params: { su_id: row.su_id } }),
      api.get('/getserviceuserdtrs', { params: { suId: row.su_id } })
    ])
    const conditionRows = conditionResponse.data?.data || row.patient_conditions || []
    const careRows = careResponse.data?.data?.patientCareTypes || []
    const dailyRows = careResponse.data?.data?.patientdailyhomecares || []
    const noteRows = Array.isArray(noteResponse.data) ? noteResponse.data : []
    const visitRows = Array.isArray(visitResponse.data) ? visitResponse.data : []
    const gp = gps.value.find(item => item.gp_id === row.gp_id)
    const html = `<html><head><meta charset="utf-8"><title>Care plan</title></head><body style="font-family: Arial, sans-serif;">
      <h1>Care plan</h1>
      <p>Prepared ${escapeHtml(formatDate(new Date().toISOString()))}</p>
      <h2>Personal</h2>
      <p>Status: ${escapeHtml(statusLabel(row))}<br>SU number: ${escapeHtml(row.su_number)}<br>Name: ${escapeHtml(fullName(row))}<br>Preferred: ${escapeHtml(row.preferred_name)}<br>
      Address: ${escapeHtml(row.address)}<br>Date of birth: ${escapeHtml(formatDate(row.date_of_birth))}<br>Age: ${escapeHtml(calculateAge(row.date_of_birth))}<br>
      Gender: ${escapeHtml(genderLabel(row))}<br>Branch: ${escapeHtml(branchLabel(row))}<br>Contact: ${escapeHtml(row.phone)}<br>Email: ${escapeHtml(row.email)}</p>
      <h2>Contacts</h2>
      <p>Next of kin: ${escapeHtml(row.next_of_kin)} ${escapeHtml(row.nok_address)} ${escapeHtml(row.nok_contact_number)}<br>
      Second contact: ${escapeHtml(row.second_contact)} ${escapeHtml(row.second_contact_address)} ${escapeHtml(row.second_contact_number)}</p>
      <h2>Service</h2>
      <p>Start: ${escapeHtml(formatDate(row.service_start_date))}<br>End: ${escapeHtml(formatDate(row.service_end_date))}<br>
      GP: ${escapeHtml(gp ? personName(gp, 'gp_first_name', 'gp_last_name') : 'N/A')}</p>
      <h2>Clinical</h2>
      <p>${escapeHtml(plainText(row.medical_history))}</p>
      <p>${escapeHtml(plainText(row.medications_json))}</p>
      <p>${escapeHtml(plainText(row.care_plan_notes))}</p>
      <h2>Conditions</h2>
      <ul>${conditionRows.map(item => `<li>${escapeHtml(item.condition?.name)} — ${escapeHtml(formatDate(item.diagnosis_date))} — primary ${item.is_primary === 1 ? 'yes' : 'no'}</li>`).join('')}</ul>
      <h2>Home care</h2>
      <ul>${careRows.map(item => `<li>${escapeHtml(item.care_type?.name)} — ${escapeHtml(item.care_type?.description)}</li>`).join('')}</ul>
      <h2>Daily care</h2>
      <ul>${dailyRows.map(item => `<li>${escapeHtml(item.created_date)} — ${escapeHtml(item.care_types)}</li>`).join('')}</ul>
      <h2>Notes</h2>
      <ul>${noteRows.map(item => `<li>${escapeHtml(formatDateTime(item.created_at))} ${escapeHtml(item.user?.first_name)} ${escapeHtml(item.user?.surname)}: ${escapeHtml(item.notes)}</li>`).join('')}</ul>
      <h2>Visits</h2>
      <ul>${visitRows.map(item => `<li>${escapeHtml(formatDateTime(item.start))} ${escapeHtml(item.shift)} ${escapeHtml(item.carer_full_name)} ${escapeHtml(formatTime(item.time_in))}-${escapeHtml(formatTime(item.time_out))}</li>`).join('')}</ul>
    </body></html>`
    saveAs(new Blob([html], { type: 'application/msword' }), `${row.su_number || row.su_id}_${fullName(row)}.doc`)
    ElMessage.success('Care plan document downloaded')
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}

async function openSarModal(row) {
  selectedSarUser.value = row
  sarRequestDate.value = ''
  sarReason.value = ''
  sarIncludeThirdParties.value = false
  sarExportFormat.value = 'pdf'
  sarDialogVisible.value = true
  sarLoading.value = true
  sarSummary.value = null
  try {
    const response = await api.get(`/service_users/${row.su_id}/sar-data`)
    if (response.data?.success) sarSummary.value = response.data.data
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    sarLoading.value = false
  }
}
async function downloadSarExport() {
  if (!selectedSarUser.value || !sarReady.value) return
  sarDownloading.value = true
  try {
    const format = sarExportFormat.value
    const response = await api.post(`/service_users/${selectedSarUser.value.su_id}/sar-export`, {
      format,
      reason: sarReason.value.trim(),
      request_date: sarRequestDate.value,
      include_third_parties: sarIncludeThirdParties.value
    }, { responseType: 'blob' })
    const extension = format === 'pdf' ? 'pdf' : 'xlsx'
    saveAs(response.data, `UK_GDPR_Art15_SAR_${selectedSarUser.value.su_number || selectedSarUser.value.su_id}.${extension}`)
    ElMessage.success('Subject access file downloaded')
  } catch (error) {
    ElMessage.error(await blobErrorText(error))
  } finally {
    sarDownloading.value = false
  }
}
async function blobErrorText(error) {
  const data = error.response?.data
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await data.text())
      if (Array.isArray(parsed.detail)) return parsed.detail.map(item => item.msg || item).join('\n')
      if (typeof parsed.detail === 'string') return parsed.detail
    } catch (parseError) {
      return 'Request failed'
    }
  }
  return errorText(error)
}

onMounted(async () => {
  await loadLookups()
  await loadServiceUsers()
})
</script>

<style scoped>
.card-header, .section-head, .filter-bar, .ai-actions { display: flex; gap: 12px; align-items: center; }
.card-header, .section-head { justify-content: space-between; }
.note-search { width: 100%; margin-bottom: 12px; }
.title-box { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 16px; }
.filter-bar { margin-bottom: 16px; flex-wrap: wrap; }
.pagination-container { display: flex; justify-content: flex-end; }
.mt-15 { margin-top: 15px; }
.sar-third-party {
  display: flex;
  align-items: flex-start;
  width: 100%;
  height: auto;
  margin-right: 0;
  white-space: normal;
}
.sar-third-party :deep(.el-checkbox__input) { margin-top: 3px; }
.sar-third-party :deep(.el-checkbox__label) {
  white-space: normal;
  line-height: 1.45;
  word-break: break-word;
}
.plain-fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
.required-note, .hint { color: #64748b; font-size: 12px; }
.preview-frame { width: 100%; height: 70vh; border: 0; }
.ai-preview { max-height: 48vh; overflow: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; background: #fff; }
.health-editor :deep(.ql-container) { min-height: 180px; font-size: 14px; }
.medications-editor :deep(.ql-container) { min-height: 240px; }
.health-editor :deep(.ql-editor) { min-height: 180px; }
.medications-editor :deep(.ql-editor) { min-height: 240px; }
h4 { margin: 0; }
</style>
