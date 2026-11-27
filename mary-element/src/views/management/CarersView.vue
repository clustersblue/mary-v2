<template>
  <div class="management-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><UserFilled /></el-icon>
            <span>Carers</span>
          </div>
          <el-button type="primary" icon="Plus" @click="openCreateModal">Add Carer</el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-input v-model="searchQuery" placeholder="Search by name or employee number" prefix-icon="Search" clearable style="width: 320px;" />
        <el-select v-model="branchFilter" clearable placeholder="Branch" style="width: 180px;">
          <el-option v-for="item in branches" :key="item.branch_id" :label="item.branch || item.name" :value="item.branch_id" />
        </el-select>
        <el-button icon="Refresh" @click="loadCarers">Refresh</el-button>
        <el-button icon="Download" @click="exportOperationalCsv">Export list</el-button>
      </div>

      <el-table :data="paginatedCarers" row-key="id" stripe border v-loading="loading">
        <el-table-column label="Status" width="130" :sort-method="sortBy(statusLabel)" sortable>
          <template #default="scope"><el-tag :type="statusTag(statusLabel(scope.row))">{{ statusLabel(scope.row) || 'Unknown' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="user_id" label="Emp No." width="110" sortable />
        <el-table-column prop="first_name" label="First Name" min-width="130" sortable />
        <el-table-column prop="surname" label="Surname" min-width="130" sortable />
        <el-table-column label="Gender" width="110" :sort-method="sortBy(genderLabel)" sortable>
          <template #default="scope">{{ genderLabel(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="Branch" min-width="140" :sort-method="sortBy(branchLabel)" sortable>
          <template #default="scope">{{ branchLabel(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="Date Started" width="130" sortable sort-by="employment_start_date">
          <template #default="scope">{{ formatDate(scope.row.employment_start_date) }}</template>
        </el-table-column>
        <el-table-column label="Actions" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" icon="View" circle @click="openRecord(scope.row, true)" />
            <el-button size="small" type="primary" icon="EditPen" circle @click="openRecord(scope.row, false)" />
            <el-button v-if="authStore.isAdmin" size="small" type="danger" icon="Delete" circle @click="deleteCarer(scope.row)" />
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container mt-15">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredCarers.length"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="980px" top="4vh" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="170px">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="Personal" name="personal">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <p class="required-note">Fields marked with * are required.</p>
              <el-row :gutter="12">
                <el-col v-if="isEdit" :span="8"><el-form-item label="Employee No." prop="user_id"><el-input v-model="form.user_id" /></el-form-item></el-col>
                <el-col :span="8">
                  <el-form-item label="Branch" prop="branch_id">
                    <el-select v-model="form.branch_id" filterable style="width: 100%;">
                      <el-option v-for="item in branches" :key="item.branch_id" :label="item.branch || item.name" :value="item.branch_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col v-if="isEdit" :span="8">
                  <el-form-item label="Status">
                    <el-select v-model="form.carer_status_id" style="width: 100%;">
                      <el-option v-for="item in carerStatuses" :key="item.carer_status_id" :label="item.carer_status || item.name" :value="item.carer_status_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="8"><el-form-item label="First Name" prop="first_name"><el-input v-model="form.first_name" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="Surname" prop="surname"><el-input v-model="form.surname" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="Username" prop="username"><el-input v-model="form.username" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="Current Address" prop="address"><el-input v-model="form.address" type="textarea" :rows="3" /></el-form-item>
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
                  <el-form-item label="Marital Status">
                    <el-select v-model="form.marital_status_id" clearable style="width: 100%;">
                      <el-option v-for="item in maritalStatuses" :key="item.marital_status_id" :label="item.marital_status || item.name" :value="item.marital_status_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="Nationality">
                    <el-select v-model="form.nationality_id" clearable filterable style="width: 100%;">
                      <el-option v-for="item in nationalities" :key="item.nationality_id" :label="item.nationality || item.name" :value="item.nationality_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Resident Status">
                    <el-select v-model="form.resident_status_id" clearable style="width: 100%;">
                      <el-option v-for="item in residentStatuses" :key="item.resident_status_id" :label="item.resident_status || item.name" :value="item.resident_status_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8"><el-form-item label="Mobile"><el-input v-model="form.mobile" /></el-form-item></el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :span="12"><el-form-item label="Email" prop="email"><el-input v-model="form.email" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="NI Number"><el-input v-model="form.ni_num" /></el-form-item></el-col>
              </el-row>
            </fieldset>
          </el-tab-pane>

          <el-tab-pane v-if="!isEdit" label="Account" name="account">
            <el-form-item label="Password" prop="password"><el-input v-model="form.password" type="password" show-password /></el-form-item>
            <el-form-item label="Confirm Password" prop="password2"><el-input v-model="form.password2" type="password" show-password /></el-form-item>
          </el-tab-pane>

          <el-tab-pane label="Emergency" name="emergency">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <el-row :gutter="12">
                <el-col :span="8"><el-form-item label="Contact Name"><el-input v-model="form.emergency_contact_name" /></el-form-item></el-col>
                <el-col :span="8"><el-form-item label="Contact Number"><el-input v-model="form.emergency_contact_number" /></el-form-item></el-col>
                <el-col :span="8">
                  <el-form-item label="Relation">
                    <el-select v-model="form.relation_id" clearable style="width: 100%;">
                      <el-option v-for="item in relations" :key="item.relation_id" :label="item.relation || item.name" :value="item.relation_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="Contact Address">
                <el-checkbox v-model="copyAddress">Copy current address</el-checkbox>
                <el-input v-model="form.emergency_address" type="textarea" :rows="3" />
              </el-form-item>
            </fieldset>
          </el-tab-pane>

          <el-tab-pane label="Employment" name="employment">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item label="Start Date">
                    <el-date-picker v-model="form.employment_start_date" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Employment Type">
                    <el-select v-model="form.employment_type_id" clearable style="width: 100%;">
                      <el-option v-for="item in employmentTypes" :key="item.employment_type_id" :label="item.employment_type || item.name" :value="item.employment_type_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="Contract">
                    <el-select v-model="form.contract_type_id" clearable style="width: 100%;">
                      <el-option v-for="item in contractTypes" :key="item.contract_type_id" :label="item.contract_type || item.name" :value="item.contract_type_id" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="Pension Scheme">
                <el-select v-model="form.pension_scheme_id" clearable style="width: 280px;">
                  <el-option v-for="item in pensionSchemes" :key="item.pension_scheme_id" :label="item.pension_scheme || item.name" :value="item.pension_scheme_id" />
                </el-select>
              </el-form-item>
            </fieldset>
            <el-form-item label="History" class="history-field">
              <div class="history-editor">
                <QuillEditor
                  v-model:content="form.employment_history"
                  content-type="html"
                  theme="snow"
                  :read-only="isViewOnly"
                  :toolbar="isViewOnly ? false : historyEditorToolbar"
                  @ready="onHistoryReady"
                  @update:content="markHistoryEdit"
                />
              </div>
            </el-form-item>
            <div v-if="isEdit">
              <el-form-item label="Requirements">
                <el-table :data="requirements" size="small" border>
                  <el-table-column prop="requirement" label="Requirement" />
                  <el-table-column label="Complete" width="120">
                    <template #default="scope">
                      <el-checkbox :model-value="Boolean(scope.row.status)" :disabled="isViewOnly" @change="value => updateRequirement(scope.row, value)" />
                    </template>
                  </el-table-column>
                </el-table>
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Training" name="training">
            <div class="section-head">
              <h4>Training courses</h4>
              <el-button v-if="!isViewOnly" size="small" type="primary" icon="Plus" @click="openTraining()">Add</el-button>
            </div>
            <el-table :data="trainings" size="small" border>
              <el-table-column prop="name" label="Course" min-width="160" />
              <el-table-column prop="description" label="Description" min-width="180" />
              <el-table-column label="Date Taken" width="120"><template #default="scope">{{ formatDate(scope.row.pivot?.completion_date) }}</template></el-table-column>
              <el-table-column prop="validity_months" label="Valid (months)" width="130" />
              <el-table-column label="Status" width="120"><template #default="scope">{{ scope.row.pivot?.status }}</template></el-table-column>
              <el-table-column v-if="!isViewOnly" label="" width="110">
                <template #default="scope">
                  <el-button size="small" icon="Edit" circle @click="openTraining(scope.row)" />
                  <el-button size="small" type="danger" icon="Delete" circle @click="deleteTraining(scope.row)" />
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Documents" name="documents">
            <el-upload v-if="!isViewOnly" :auto-upload="false" :show-file-list="false" :on-change="onFilePicked" accept=".doc,.docx,.pdf,.txt,.png,.jpg,.jpeg,.gif,.webp">
              <el-button type="primary" icon="Upload">Upload</el-button>
            </el-upload>
            <p class="hint">Word, image, PDF, or text. Maximum 5 MB.</p>
            <el-table :data="files" size="small" border empty-text="No documents">
              <el-table-column prop="filename" label="File" min-width="260" />
              <el-table-column width="160" align="right">
                <template #default="scope">
                  <el-button size="small" icon="View" circle @click="viewFile(scope.row.filename)" />
                  <el-button size="small" icon="Download" circle @click="downloadFile(scope.row.filename)" />
                  <el-button v-if="!isViewOnly" size="small" type="danger" icon="Delete" circle @click="deleteFile(scope.row.filename)" />
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Rota" name="rota">
            <div class="section-head">
              <h4>Recent attended visits</h4>
              <el-button size="small" icon="Download" @click="exportRota">Export rota</el-button>
            </div>
            <el-table :data="rota" size="small" border>
              <el-table-column label="Carer" min-width="140"><template #default="scope">{{ scope.row.first_name }} {{ scope.row.surname }}</template></el-table-column>
              <el-table-column label="Service User" min-width="150"><template #default="scope">{{ scope.row.service_user?.su_full_name }}</template></el-table-column>
              <el-table-column prop="rate" label="Rate" width="90" />
              <el-table-column label="Date" min-width="160"><template #default="scope">{{ formatDateTime(scope.row.start) }}</template></el-table-column>
              <el-table-column label="Service" min-width="120"><template #default="scope">{{ scope.row.shift?.shift }}</template></el-table-column>
              <el-table-column label="Time in" width="100"><template #default="scope">{{ formatTime(scope.row.attendance?.time_in) }}</template></el-table-column>
              <el-table-column label="Time out" width="100"><template #default="scope">{{ formatTime(scope.row.attendance?.time_out) }}</template></el-table-column>
              <el-table-column label="Payroll" width="120"><template #default="scope">{{ scope.row.attendance?.paid || '' }}</template></el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane v-if="isEdit" label="Notes" name="notes">
            <fieldset :disabled="isViewOnly" class="plain-fieldset">
              <el-form-item label="Notes"><el-input v-model="form.carer_notes" type="textarea" :rows="6" /></el-form-item>
            </fieldset>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ isViewOnly ? 'Close' : 'Cancel' }}</el-button>
        <el-button v-if="!isViewOnly" type="primary" :loading="saving" @click="saveCarer">{{ isEdit ? 'Update' : 'Create' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="trainingDialog" :title="trainingForm.editing ? 'Edit training' : 'Add training'" width="520px">
      <el-form label-width="150px">
        <el-form-item label="Course" required>
          <el-select v-model="trainingForm.training_course_id" filterable style="width: 100%;">
            <el-option v-for="item in courses" :key="item.training_course_id" :label="item.name" :value="item.training_course_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Date Completed" required>
          <el-date-picker v-model="trainingForm.completion_date" type="date" value-format="YYYY-MM-DD" format="DD/MM/YYYY" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="Status" required>
          <el-select v-model="trainingForm.status" style="width: 100%;">
            <el-option label="Completed" value="completed" />
            <el-option label="Pending" value="pending" />
            <el-option label="Failed" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="trainingDialog = false">Cancel</el-button>
        <el-button type="primary" @click="saveTraining">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="previewVisible" :title="previewName" width="80%" top="4vh" @closed="closePreview">
      <iframe v-if="previewUrl" :src="previewUrl" class="preview-frame" />
      <template #footer><el-button @click="previewVisible = false">Close</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import { saveAs } from 'file-saver'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const historyEditorToolbar = [
  ['bold', 'italic'],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['link', 'clean']
]
let historyQuill = null
let historyFromEditor = false

function loadQuillHtml(quill, html) {
  if (!quill) return
  const delta = quill.clipboard.convert({ html: html || '' })
  quill.setContents(delta, 'silent')
}
function onHistoryReady(quill) {
  historyQuill = quill
  loadQuillHtml(quill, form.value.employment_history)
  quill.enable(!isViewOnly.value)
}
function markHistoryEdit() {
  historyFromEditor = true
}

const authStore = useAuthStore()
const carers = ref([])
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
const maritalStatuses = ref([])
const nationalities = ref([])
const residentStatuses = ref([])
const carerStatuses = ref([])
const employmentTypes = ref([])
const contractTypes = ref([])
const pensionSchemes = ref([])
const relations = ref([])
const courses = ref([])
const requirements = ref([])
const trainings = ref([])
const files = ref([])
const rota = ref([])
const copyAddress = ref(false)
const suppressCopy = ref(false)
const trainingDialog = ref(false)
const trainingForm = ref({ training_course_id: null, completion_date: '', status: 'completed', editing: false })
const previewVisible = ref(false)
const previewUrl = ref('')
const previewName = ref('')

const FILE_EXTENSIONS = ['doc', 'docx', 'pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp']
const PREVIEW_EXTENSIONS = ['pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp']

function emptyForm() {
  return {
    user_id: '', first_name: '', surname: '', username: '', password: '', password2: '',
    branch_id: null, carer_status_id: null, address: '', date_of_birth: '', gender_id: null,
    marital_status_id: null, nationality_id: null, resident_status_id: null, mobile: '',
    email: '', ni_num: '', emergency_contact_name: '', emergency_contact_number: '',
    relation_id: null, emergency_address: '', employment_start_date: '',
    employment_type_id: null, contract_type_id: null, pension_scheme_id: null,
    employment_history: '', carer_notes: ''
  }
}
const form = ref(emptyForm())
watch(() => form.value.employment_history, (html) => {
  if (historyFromEditor) {
    historyFromEditor = false
    return
  }
  loadQuillHtml(historyQuill, html)
}, { flush: 'post' })
watch(dialogVisible, (open) => {
  if (!open) historyQuill = null
})

const requiredEmail = (rule, value, callback) => {
  if (!value) callback(new Error('Email is required'))
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) callback(new Error('Enter a valid email'))
  else callback()
}
const rules = computed(() => ({
  branch_id: [{ required: true, message: 'Branch is required', trigger: 'change' }],
  first_name: [{ required: true, message: 'First name is required', trigger: 'blur' }],
  surname: [{ required: true, message: 'Surname is required', trigger: 'blur' }],
  username: [{ required: true, message: 'Username is required', trigger: 'blur' }],
  address: [{ required: true, message: 'Current address is required', trigger: 'blur' }],
  date_of_birth: [{ required: true, message: 'Date of birth is required', trigger: 'change' }],
  gender_id: [{ required: true, message: 'Gender is required', trigger: 'change' }],
  email: [{ validator: requiredEmail, trigger: 'blur' }],
  ...(isEdit.value ? { user_id: [{ required: true, message: 'Employee number is required', trigger: 'blur' }] } : {}),
  ...(!isEdit.value ? {
    password: [{ required: true, message: 'Password is required', trigger: 'blur' }],
    password2: [{
      validator: (rule, value, callback) => {
        if (!value) callback(new Error('Confirm the password'))
        else if (value !== form.value.password) callback(new Error('Passwords do not match'))
        else callback()
      },
      trigger: 'blur'
    }]
  } : {})
}))

const dialogTitle = computed(() => {
  const name = `${form.value.first_name || ''} ${form.value.surname || ''}`.trim()
  if (isViewOnly.value) return name || 'Carer record'
  return isEdit.value ? `Edit ${name}` : 'New carer'
})

function lookupName(list, idKey, id, labelKey) {
  const found = list.find(item => item[idKey] === id)
  return found ? (found[labelKey] || found.name || '') : ''
}
function statusLabel(row) {
  return row?.carer_status?.status_name || row?.carer_status?.name || lookupName(carerStatuses.value, 'carer_status_id', row?.carer_status_id, 'carer_status')
}
function genderLabel(row) {
  return row?.gender?.gender_name || row?.gender?.name || lookupName(genders.value, 'gender_id', row?.gender_id, 'gender')
}
function branchLabel(row) {
  return row?.branch?.branch_name || row?.branch?.name || lookupName(branches.value, 'branch_id', row?.branch_id, 'branch')
}
function statusTag(status) {
  if (status === 'Resigned') return 'danger'
  if (status === 'Not Active') return 'warning'
  return 'success'
}
function sortBy(getter) {
  return (a, b) => String(getter(a) ?? '').localeCompare(String(getter(b) ?? ''), undefined, { numeric: true })
}
function asDateInput(value) {
  return value ? String(value).slice(0, 10) : ''
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
function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString('en-GB')
}
function errorText(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map(item => item.msg || item).join('\n')
  if (typeof detail === 'string') return detail
  return error.response?.data?.message || error.message || 'Request failed'
}
function fileExtension(filename) {
  return String(filename).split('.').pop().toLowerCase()
}
function filePrefix() {
  return `id_${form.value.user_id || String(editingId.value).padStart(5, '0')}`
}

const filteredCarers = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return carers.value.filter(row => {
    if (branchFilter.value && row.branch_id !== branchFilter.value) return false
    if (!query) return true
    const haystack = [row.user_id, row.first_name, row.surname, statusLabel(row), branchLabel(row)].join(' ').toLowerCase()
    return haystack.includes(query)
  })
})
const paginatedCarers = computed(() => filteredCarers.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))
watch([searchQuery, branchFilter, pageSize], () => { currentPage.value = 1 })
watch(copyAddress, value => { if (!suppressCopy.value) form.value.emergency_address = value ? form.value.address : '' })

async function loadLookups() {
  const requests = [
    ['/getbranches', branches], ['/getgenders', genders], ['/getmaritalstatuses', maritalStatuses],
    ['/getnationalities', nationalities], ['/getresidentstatuses', residentStatuses],
    ['/getcarerstatuses', carerStatuses], ['/getemploymenttypes', employmentTypes],
    ['/getcontracttypes', contractTypes], ['/getpensionscheme', pensionSchemes],
    ['/getrelations', relations], ['/trainings', courses]
  ]
  await Promise.all(requests.map(async ([url, target]) => {
    try {
      const response = await api.get(url)
      const data = response.data
      target.value = Array.isArray(data) ? data : (data?.data || [])
    } catch (error) {
      target.value = []
    }
  }))
}

async function loadCarers() {
  loading.value = true
  try {
    const response = await api.get('/getcarers')
    carers.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    carers.value = []
    ElMessage.error(errorText(error))
  } finally {
    loading.value = false
  }
}

function exportOperationalCsv() {
  const header = ['Status', 'Emp No.', 'First Name', 'Surname', 'Gender', 'Branch', 'Date Started']
  const lines = filteredCarers.value.map(row => [
    statusLabel(row), row.user_id, row.first_name, row.surname, genderLabel(row), branchLabel(row), formatDate(row.employment_start_date)
  ].map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(','))
  saveAs(new Blob([[header.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' }), 'carers.csv')
}

function fillForm(row) {
  const next = emptyForm()
  Object.keys(next).forEach(key => {
    if (key === 'password' || key === 'password2') return
    if (row[key] !== undefined && row[key] !== null) next[key] = row[key]
  })
  next.date_of_birth = asDateInput(row.date_of_birth)
  next.employment_start_date = asDateInput(row.employment_start_date)
  return next
}

async function openRecord(row, viewOnly) {
  suppressCopy.value = true
  copyAddress.value = false
  suppressCopy.value = false
  isEdit.value = true
  isViewOnly.value = viewOnly
  editingId.value = row.id
  form.value = fillForm(row)
  activeTab.value = 'personal'
  dialogVisible.value = true
  try {
    await Promise.all([loadRequirements(), loadTrainings(), loadFiles(), loadRota()])
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}

function openCreateModal() {
  suppressCopy.value = true
  copyAddress.value = false
  suppressCopy.value = false
  isEdit.value = false
  isViewOnly.value = false
  editingId.value = null
  form.value = emptyForm()
  requirements.value = []
  trainings.value = []
  files.value = []
  rota.value = []
  activeTab.value = 'personal'
  dialogVisible.value = true
}

async function saveCarer() {
  const valid = await formRef.value.validate().then(() => true).catch(() => false)
  if (!valid) {
    ElMessage.warning('Complete the required fields before saving')
    activeTab.value = 'personal'
    return
  }
  saving.value = true
  const body = { ...form.value }
  delete body.password2
  if (!body.date_of_birth) body.date_of_birth = null
  if (!body.employment_start_date) body.employment_start_date = null
  try {
    if (isEdit.value) {
      delete body.password
      await api.put(`/carers/${editingId.value}`, body)
      ElMessage.success('Carer updated')
    } else {
      body.carer_status_id = 1
      await api.post('/carers', body)
      ElMessage.success('Carer created')
    }
    dialogVisible.value = false
    await loadCarers()
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    saving.value = false
  }
}

async function deleteCarer(row) {
  try {
    await ElMessageBox.confirm(`Delete the record for ${row.first_name} ${row.surname}?`, 'Confirm delete', { type: 'warning' })
    await api.delete(`/carers/${row.id}`)
    ElMessage.success('Carer deleted')
    await loadCarers()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}

async function loadRequirements() {
  const response = await api.get(`/getuserrequirements/${editingId.value}`)
  requirements.value = Array.isArray(response.data) ? response.data : []
}
async function updateRequirement(row, checked) {
  const body = { user_id: editingId.value, requirement_id: row.requirement_id, status: checked ? 1 : 0 }
  try {
    if (row.id) await api.post(`/updaterequirementsstatus/${row.id}`, body)
    else await api.post('/saverequirementsstatus', body)
    await loadRequirements()
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function loadTrainings() {
  const response = await api.get(`/users/${editingId.value}/training-courses`)
  trainings.value = response.data?.data || []
}
function openTraining(row) {
  trainingForm.value = row ? {
    training_course_id: row.training_course_id,
    completion_date: asDateInput(row.pivot?.completion_date),
    status: (row.pivot?.status || 'completed').toLowerCase(),
    editing: true
  } : { training_course_id: null, completion_date: '', status: 'completed', editing: false }
  trainingDialog.value = true
}
async function saveTraining() {
  if (!trainingForm.value.training_course_id || !trainingForm.value.completion_date || !trainingForm.value.status) {
    ElMessage.warning('Course, completion date, and status are required')
    return
  }
  const body = {
    user_id: editingId.value,
    training_course_id: trainingForm.value.training_course_id,
    completion_date: `${trainingForm.value.completion_date} 00:00:00`,
    status: trainingForm.value.status
  }
  try {
    if (trainingForm.value.editing) await api.put(`/users/${editingId.value}/training-courses/${trainingForm.value.training_course_id}`, body)
    else await api.post(`/users/${editingId.value}/training-courses`, body)
    trainingDialog.value = false
    await loadTrainings()
    ElMessage.success('Training saved')
  } catch (error) {
    ElMessage.error(errorText(error))
  }
}
async function deleteTraining(row) {
  try {
    await ElMessageBox.confirm('Remove this training course?', 'Confirm delete', { type: 'warning' })
    await api.delete(`/users/${editingId.value}/training-courses/${row.training_course_id}`)
    await loadTrainings()
    ElMessage.success('Training removed')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}
async function loadFiles() {
  const response = await api.get(`/carerfiles/${encodeURIComponent(filePrefix())}`)
  const names = Array.isArray(response.data) ? response.data : []
  files.value = names.filter(Boolean).map(filename => ({ filename }))
}
async function onFilePicked(uploadFile) {
  const file = uploadFile.raw
  if (!file) return
  const extension = fileExtension(file.name)
  if (!FILE_EXTENSIONS.includes(extension) || file.size > 5000000) {
    ElMessage.error('Use a Word, image, PDF, or text file smaller than 5 MB')
    return
  }
  const reader = new FileReader()
  reader.onload = async () => {
    const filename = `${filePrefix()}_${file.name.replace(/[^a-zA-Z0-9._-]/g, '')}`
    try {
      await api.post('/carerupload', { base64data: reader.result, filename })
      ElMessage.success('Document uploaded')
      await loadFiles()
    } catch (error) {
      ElMessage.error(errorText(error))
    }
  }
  reader.readAsDataURL(file)
}
async function fetchFileBlob(filename) {
  const response = await api.get(`/carerdownload/${encodeURIComponent(filename)}`, { responseType: 'blob' })
  return new Blob([response.data], { type: response.headers['content-type'] || 'application/octet-stream' })
}
async function downloadFile(filename) {
  try { saveAs(await fetchFileBlob(filename), filename) } catch (error) { ElMessage.error(errorText(error)) }
}
async function viewFile(filename) {
  try {
    const blob = await fetchFileBlob(filename)
    if (!PREVIEW_EXTENSIONS.includes(fileExtension(filename))) {
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
}
async function deleteFile(filename) {
  try {
    await ElMessageBox.confirm(`Delete ${filename}?`, 'Confirm delete', { type: 'warning' })
    await api.delete(`/carerDeleteFile/${encodeURIComponent(filename)}`)
    await loadFiles()
    ElMessage.success('Document deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  }
}
async function loadRota() {
  const response = await api.get('/getdtr', { params: { user_id: editingId.value } })
  rota.value = Array.isArray(response.data) ? response.data : []
}
function exportRota() {
  const header = ['Carer', 'Service User', 'Rate', 'Date', 'Service', 'Time in', 'Time out', 'Payroll']
  const lines = rota.value.map(row => [
    `${row.first_name || ''} ${row.surname || ''}`.trim(),
    row.service_user?.su_full_name, row.rate, formatDateTime(row.start), row.shift?.shift,
    formatTime(row.attendance?.time_in), formatTime(row.attendance?.time_out), row.attendance?.paid
  ].map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(','))
  saveAs(new Blob([[header.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' }), 'carer-rota.csv')
}

onMounted(async () => {
  await loadLookups()
  await loadCarers()
})
</script>

<style scoped>
.card-header, .section-head, .filter-bar { display: flex; gap: 12px; align-items: center; }
.card-header, .section-head { justify-content: space-between; }
.title-box { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 16px; }
.filter-bar { margin-bottom: 16px; flex-wrap: wrap; }
.pagination-container { display: flex; justify-content: flex-end; }
.mt-15 { margin-top: 15px; }
.plain-fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
.required-note, .hint { color: #64748b; font-size: 12px; }
.preview-frame { width: 100%; height: 70vh; border: 0; }
.history-field :deep(.el-form-item__content) { display: block; }
.history-editor { width: 100%; }
.history-editor :deep(.ql-toolbar) { width: 100%; box-sizing: border-box; }
.history-editor :deep(.ql-container) { width: 100%; height: 320px; font-size: 14px; }
.history-editor :deep(.ql-editor) { min-height: 100%; }
h4 { margin: 8px 0; }
</style>
