<template>
  <div class="attendance-container">
    <el-row :gutter="16" class="portal-row">
      <el-col :xs="24" :sm="24" :md="24" :lg="24">
        <el-card shadow="never" class="portal-card">
          <template #header>
            <div class="card-header">
              <el-icon><Clock /></el-icon>
              <span>Carer Mobile Portal - Shift Clock-In / Out</span>
            </div>
          </template>

          <div class="clockin-box" v-loading="loading">
            <el-alert
              v-if="activeShift"
              :title="activeShift"
              type="info"
              :closable="false"
              show-icon
              class="shift-alert"
            />
            <el-alert
              v-else-if="!loading"
              title="No active shift is assigned to you."
              description="Clock In and Clock Out are unavailable until a shift is assigned."
              type="warning"
              :closable="false"
              show-icon
              class="shift-alert"
            />

            <p v-if="sessionComplete" class="session-note">Today's attendance is complete.</p>

            <div v-if="showClockIn || showClockOut" class="action-buttons">
              <el-button
                v-if="showClockIn"
                type="success"
                size="large"
                icon="CircleCheck"
                :loading="saving"
                @click="handleClockIn"
              >
                Clock In
              </el-button>
              <el-button
                v-if="showClockOut"
                type="danger"
                size="large"
                icon="CircleClose"
                :loading="saving"
                @click="handleClockOut"
              >
                Clock Out
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="24" :lg="24">
        <el-card shadow="never" class="portal-card">
          <el-tabs v-model="activeTab" class="portal-tabs">
            <el-tab-pane label="Carer Visit Logs & Care Notes" name="visits">
              <div class="section-head">
                <h4>Care notes</h4>
                <el-button size="small" type="primary" icon="Plus" @click="openNote()">Add note</el-button>
              </div>
              <el-input v-model="noteSearch" clearable placeholder="Search notes, author, service user, or date" class="note-search" />
              <div class="table-scroll">
                <el-table :data="visibleNotes" size="small" border v-loading="notesLoading" :empty-text="notesEmptyText">
                  <el-table-column label="When" min-width="200"><template #default="scope">{{ formatNoteWhen(scope.row.created_at || scope.row.updated_at) }}</template></el-table-column>
                  <el-table-column label="Author" min-width="140"><template #default="scope">{{ authorName(scope.row) }}</template></el-table-column>
                  <el-table-column prop="notes" label="Note" min-width="220" />
                  <el-table-column label="" width="110" align="right">
                    <template #default="scope">
                      <template v-if="Number(scope.row.user_id) === Number(userId)">
                        <el-button size="small" icon="Edit" circle @click="openNote(scope.row)" />
                        <el-button size="small" type="danger" icon="Delete" circle @click="deleteNote(scope.row)" />
                      </template>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <el-tab-pane label="My Attendance History" name="history">
              <el-tabs v-model="historyTab" class="history-tabs" v-loading="loading">
                <el-tab-pane label="Attendance Records" name="records">
                  <p class="history-caption">Clock in and clock out records from the last three months.</p>
                  <div class="table-scroll">
                    <el-table :data="attendanceRows" size="small" stripe border empty-text="No attendance records for your account">
                      <el-table-column label="Date" min-width="130"><template #default="scope">{{ formatHistoryDate(scope.row.date) }}</template></el-table-column>
                      <el-table-column prop="clock_in" label="Clock In" min-width="100" />
                      <el-table-column prop="clock_out" label="Clock Out" min-width="100" />
                      <el-table-column label="Total Hours" min-width="120"><template #default="scope">{{ formatHours(scope.row.total_hours) }}</template></el-table-column>
                      <el-table-column label="Status" min-width="130">
                        <template #default="scope">
                          <el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                </el-tab-pane>
                <el-tab-pane label="My Scheduled Shifts" name="shifts">
                  <p class="history-caption">{{ scheduleCaption }}</p>
                  <div class="table-scroll">
                    <el-table :data="scheduleRows" size="small" stripe border empty-text="No scheduled shifts for this month">
                      <el-table-column label="Date" min-width="130"><template #default="scope">{{ formatHistoryDate(scope.row.date) }}</template></el-table-column>
                      <el-table-column prop="service_user" label="Service User" min-width="150" />
                      <el-table-column label="Scheduled Shift" min-width="150"><template #default="scope">{{ scope.row.scheduled_start }} - {{ scope.row.scheduled_end }}</template></el-table-column>
                      <el-table-column prop="clock_in" label="Clock In" min-width="100" />
                      <el-table-column prop="clock_out" label="Clock Out" min-width="100" />
                      <el-table-column label="Status" min-width="130">
                        <template #default="scope">
                          <el-tag :type="statusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="noteDialog" :title="noteForm.id ? 'Edit note' : 'Add note'" width="min(560px, 92vw)">
      <el-input v-model="noteForm.notes" type="textarea" :rows="5" placeholder="Log daily care activities, medication support, fluid intake, and observations..." />
      <template #footer>
        <el-button @click="noteDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="savingNote" @click="saveNote">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const savingNote = ref(false)
const notesLoading = ref(false)
const activeTab = ref('visits')
const historyTab = ref('records')
const noteSearch = ref('')
const notes = ref([])
const noteDialog = ref(false)
const noteForm = ref({ id: null, notes: '' })
const noteBusy = ref(false)
const historyMonth = ref('')
const attendanceRows = ref([])
const scheduleRows = ref([])
const session = ref({ attendance_id: null, clock_in: null, clock_out: null })
let notesRequest = 0

const userId = computed(() => authStore.user?.id || null)

function localISODate(value = new Date()) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
function formatHistoryDate(value) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return value ? String(value) : ''
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${Number(match[3])} ${months[Number(match[2]) - 1]} ${match[1]}`
}
function formatHours(value) {
  if (value === null || value === undefined || value === '') return ''
  const number = Number(value)
  return Number.isNaN(number) ? String(value) : number.toFixed(2)
}
function statusTag(status) {
  if (status === 'Completed') return 'success'
  if (status === 'Clocked in') return 'warning'
  if (status === 'Cancelled') return 'danger'
  return 'info'
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
function authorName(row) {
  return `${row?.user?.first_name || ''} ${row?.user?.surname || ''}`.trim()
}
function noteHaystack(row, serviceUserName = '') {
  const when = formatNoteWhen(row?.created_at || row?.updated_at)
  const serviceUser = row?.service_user?.full_name || serviceUserName
  return [when, row?.created_at, row?.updated_at, authorName(row), serviceUser, row?.notes].join(' ').toLowerCase()
}
function errorText(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item.msg || item).join(', ')
  return 'The attendance request could not be completed'
}
const today = computed(() => localISODate())
const todayShifts = computed(() => scheduleRows.value.filter(row => row.date === today.value && row.status !== 'Cancelled'))
const activeShift = computed(() => {
  if (!todayShifts.value.length) return ''
  const names = [...new Set(todayShifts.value.map(row => row.service_user).filter(Boolean))]
  const windows = [...new Set(todayShifts.value.map(row => `${row.scheduled_start} - ${row.scheduled_end}`))]
  return `Active shift: ${names.join(', ')} (${windows.join(', ')})`
})
const openSession = computed(() => (session.value.clock_in && !session.value.clock_out) ? session.value : null)
const sessionComplete = computed(() => Boolean(session.value.clock_in && session.value.clock_out))
const showClockIn = computed(() => Boolean(activeShift.value) && !openSession.value && !sessionComplete.value)
const showClockOut = computed(() => Boolean(activeShift.value) && Boolean(openSession.value))
const visibleNotes = computed(() => {
  const query = noteSearch.value.trim().toLowerCase()
  if (!query) return notes.value
  return notes.value.filter(row => noteHaystack(row).includes(query))
})
const notesEmptyText = computed(() => noteSearch.value.trim() ? 'No matching care notes' : 'No care notes for the active shift')
const scheduleCaption = computed(() => {
  const match = String(historyMonth.value || '').match(/^(\d{4})-(\d{2})$/)
  if (!match) return 'Shifts assigned to you this month.'
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  return `Shifts assigned to you in ${months[Number(match[2]) - 1]} ${match[1]}, including later dates this month.`
})

async function loadAttendance() {
  if (!userId.value) return
  loading.value = true
  const [historyResult, sessionResult] = await Promise.allSettled([
    api.get('/attendances/my-history'),
    api.get('/attendances/session')
  ])
  const problems = []
  if (historyResult.status === 'fulfilled') {
    const payload = historyResult.value.data || {}
    historyMonth.value = payload.month || ''
    attendanceRows.value = Array.isArray(payload.attendance) ? payload.attendance : []
    scheduleRows.value = Array.isArray(payload.schedules) ? payload.schedules : []
  } else {
    historyMonth.value = ''
    attendanceRows.value = []
    scheduleRows.value = []
    problems.push(errorText(historyResult.reason))
  }
  if (sessionResult.status === 'fulfilled') {
    session.value = sessionResult.value.data || { attendance_id: null, clock_in: null, clock_out: null }
  } else {
    session.value = { attendance_id: null, clock_in: null, clock_out: null }
    problems.push(errorText(sessionResult.reason))
  }
  await loadNotes()
  if (problems.length) ElMessage.error(problems[0])
  loading.value = false
}

async function handleClockIn() {
  if (!activeShift.value) {
    ElMessage.warning('No active shift is assigned to you.')
    return
  }
  saving.value = true
  try {
    await api.post('/attendances/timein', { user_id: userId.value })
    ElMessage.success('Clocked in')
    await loadAttendance()
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    saving.value = false
  }
}

async function handleClockOut() {
  if (!activeShift.value) {
    ElMessage.warning('No active shift is assigned to you.')
    return
  }
  if (!session.value.attendance_id) {
    ElMessage.warning('No open attendance session was found')
    return
  }
  saving.value = true
  try {
    await api.post('/attendances/timeout', { attendance_id: openSession.value.attendance_id })
    ElMessage.success('Clocked out')
    await loadAttendance()
  } catch (error) {
    ElMessage.error(errorText(error))
  } finally {
    saving.value = false
  }
}

async function loadNotes() {
  const requestId = ++notesRequest
  notesLoading.value = true
  try {
    const response = await api.get('/attendances/visit-notes')
    if (requestId !== notesRequest) return
    notes.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    if (requestId !== notesRequest) return
    notes.value = []
    ElMessage.error(errorText(error))
  } finally {
    if (requestId === notesRequest) notesLoading.value = false
  }
}
function showShiftNoteWarning() {
  return ElMessageBox.alert(
    'No active shift or assigned Service User was found.\nPlease Clock In before creating Care Notes.',
    'Unable to save Care Note.',
    { type: 'warning' }
  )
}
function openNote(row) {
  if (!row && !openSession.value) {
    showShiftNoteWarning()
    return
  }
  noteForm.value = row ? { id: row.id, notes: row.notes } : { id: null, notes: '' }
  noteDialog.value = true
}
async function saveNote() {
  const text = (noteForm.value.notes || '').trim()
  if (!text) {
    ElMessage.warning('Note cannot be empty')
    return
  }
  if (!noteForm.value.id && !openSession.value) {
    showShiftNoteWarning()
    return
  }
  savingNote.value = true
  try {
    if (noteForm.value.id) {
      await api.post(`/attendances/visit-notes/${noteForm.value.id}`, { notes: text })
    } else {
      await api.post('/attendances/visit-log', { notes: text })
    }
    noteDialog.value = false
    await loadNotes()
    ElMessage.success('Note saved')
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (typeof detail === 'string' && detail.startsWith('Unable to save Care Note')) showShiftNoteWarning()
    else ElMessage.error(errorText(error))
  } finally {
    savingNote.value = false
  }
}
async function deleteNote(row) {
  if (noteBusy.value) return
  noteBusy.value = true
  try {
    await ElMessageBox.confirm('Delete this note?', 'Confirm delete', { type: 'warning' })
    await api.delete(`/attendances/visit-notes/${row.id}`)
    await loadNotes()
    ElMessage.success('Note deleted')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(errorText(error))
  } finally {
    noteBusy.value = false
  }
}
watch(
  () => [authStore.sessionValidated, authStore.user?.id ?? null],
  ([validated, id], previous) => {
    if (id) {
      if (previous?.[1] !== id) loadAttendance()
      return
    }
    if (validated) {
      attendanceRows.value = []
      scheduleRows.value = []
      ElMessage.error('Sign in again to view your attendance')
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.attendance-container {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  box-sizing: border-box;
}
.portal-row {
  width: 100%;
}
.portal-card {
  width: 100%;
  height: auto;
  margin-bottom: 16px;
}
.mt-20 {
  margin-top: 4px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  min-width: 0;
}
.card-header span {
  overflow-wrap: anywhere;
}
.clockin-box {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 16px;
  padding: 8px 0 4px;
}
.shift-alert {
  width: 100%;
}
.session-note {
  margin: 0;
  color: var(--el-text-color-secondary);
}
.action-buttons {
  display: flex;
  width: 100%;
  max-width: 420px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.section-head h4 { margin: 0; }
.note-search {
  width: 100%;
  margin-bottom: 12px;
}
.portal-tabs :deep(.el-tabs__item),
.history-tabs :deep(.el-tabs__item) {
  height: auto;
  line-height: 1.3;
  white-space: normal;
  text-align: left;
}
.history-caption {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
}
.action-buttons :deep(.el-button) {
  flex: 1;
}
.submit-log {
  width: 100%;
}
.table-scroll {
  width: 100%;
  overflow-x: auto;
}
@media (max-width: 768px) {
  .action-buttons {
    flex-direction: column;
  }
  .action-buttons :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
  .action-buttons :deep(.el-button + .el-button) {
    margin-top: 12px;
    margin-left: 0;
  }
}
</style>
