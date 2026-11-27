<template>
  <div class="dtr-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon class="title-icon"><Clock /></el-icon>
            <span>Daily Time Record (DTR)</span>
          </div>
          <div class="header-actions">
            <!-- Single Panel Variant Date Range Picker (Max 1 Month) -->
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="To"
              start-placeholder="Start Date"
              end-placeholder="End Date"
              value-format="YYYY-MM-DD"
              :unlink-panels="false"
              single-panel
              style="width: 250px;"
              @change="onDateRangeChange"
            />
          </div>
        </div>
      </template>

      <!-- Optimized Table Toolbar (Compact Icon-Only Buttons with Tooltips) -->
      <div class="table-menu-bar">
        <div class="left-tools">
          <el-input
            v-model="searchQuery"
            placeholder="Search by Carer Staff or Service User..."
            prefix-icon="Search"
            clearable
            style="width: 320px;"
            @input="currentPage = 1"
          />
        </div>
        <div class="right-actions">
          <el-tooltip content="Refresh Table" placement="top">
            <el-button icon="Refresh" type="primary" circle @click="fetchDTR" />
          </el-tooltip>

          <el-tooltip content="Download CSV" placement="top">
            <el-button icon="Download" type="success" circle @click="exportCSV" />
          </el-tooltip>

          <el-tooltip content="Expand All Rows" placement="top">
            <el-button icon="FolderOpened" type="info" circle @click="expandAll" />
          </el-tooltip>

          <el-tooltip content="Collapse All Rows" placement="top">
            <el-button icon="Folder" type="info" circle @click="collapseAll" />
          </el-tooltip>

          <el-tooltip v-if="authStore.isAdmin" content="Generate Automatic Clock Times (Up to Today)" placement="top">
            <el-button
              icon="MagicStick"
              type="warning"
              circle
              :loading="generatingClocks"
              @click="generateDummyTimes"
            />
          </el-tooltip>
        </div>
      </div>

      <!-- Initial Prompt Alert if Date Range not set -->
      <el-alert
        v-if="!dateRange || !dateRange.length"
        type="info"
        title="Date Range Not Set"
        description="Please select a Date Range (maximum 1 month) or click Refresh Table to load Daily Time Records from the database."
        show-icon
        class="mt-15 mb-15"
      />

      <!-- Warning Alert if Data Fetch returned empty -->
      <el-alert
        v-else-if="!loading && !filteredDtrList.length"
        type="warning"
        title="No Daily Time Records Found"
        description="No database shift records were returned for the selected date range and filter parameters."
        show-icon
        class="mt-15 mb-15"
      />

      <!-- Main DTR Parent Table (Paginated for High Performance) -->
      <el-table
        ref="dtrTableRef"
        :data="paginatedDtrList"
        style="width: 100%"
        stripe
        border
        v-loading="loading"
        row-key="id"
        :expand-row-keys="expandedRowKeys"
        @expand-change="handleExpandChange"
        @row-dblclick="startParentEdit"
        class="mt-15"
      >
        <!-- Expanded Child Table (Assigned Client Visits) -->
        <el-table-column type="expand">
          <template #default="props">
            <div class="nested-visits-container">
              <div class="child-table-title">
                <el-icon><User /></el-icon>
                <span>Assigned Service User Visits for {{ props.row.carer_full_name }} ({{ props.row.occurrence_date }})</span>
              </div>
              <el-table :data="props.row.service_users" border size="small" stripe style="width: 60%;" @row-dblclick="(row) => startChildEdit(row, props.row)">
                <el-table-column prop="su_full_name" label="Service User" min-width="50" />
                <el-table-column prop="scheduled_visit" label="Scheduled Visit" width="130" align="center" />

                <el-table-column label="Clock In" width="140" align="center">
                  <template #default="scope">
                    <input
                      v-if="isChildEditing(scope.row, props.row)"
                      v-model="childClockDraft.clock_in"
                      type="time"
                      class="clock-input"
                    />
                    <span v-else>{{ formatTimeToHHMM(scope.row.clock_in) }}</span>
                  </template>
                </el-table-column>

                <el-table-column label="Clock Out" width="140" align="center">
                  <template #default="scope">
                    <input
                      v-if="isChildEditing(scope.row, props.row)"
                      v-model="childClockDraft.clock_out"
                      type="time"
                      class="clock-input"
                    />
                    <span v-else>{{ formatTimeToHHMM(scope.row.clock_out) }}</span>
                  </template>
                </el-table-column>

                <el-table-column label="" width="90" align="center">
                  <template #default="scope">
                    <div v-if="isChildEditing(scope.row, props.row)" class="clock-actions">
                      <el-button size="small" type="success" icon="Check" circle @click="confirmChildEdit(scope.row, props.row)" />
                      <el-button size="small" type="danger" icon="Close" circle @click="cancelChildEdit(scope.row)" />
                    </div>
                  </template>
                </el-table-column>

                <!-- Child Action: Care Notes (Generate / View / Delete) -->
                <el-table-column label="Care Notes" width="180" align="center">
                  <template #default="scope">
                    <div class="care-notes-actions">
                      <el-button
                        v-if="!scope.row.is_care_note_generated"
                        size="small"
                        type="success"
                        icon="MagicStick"
                        @click="openAICarePlanModalForVisit(scope.row, props.row)"
                      >
                        Care Notes
                      </el-button>
                      <template v-else>
                        <el-tooltip content="View Generated Care Note PDF in Browser" placement="top">
                          <el-button
                            size="small"
                            type="primary"
                            icon="View"
                            circle
                            @click="viewCareNotePdf(scope.row)"
                          />
                        </el-tooltip>
                        <el-tooltip content="Delete / Revert Care Note PDF from Server" placement="top">
                          <el-button
                            size="small"
                            type="danger"
                            icon="Delete"
                            circle
                            @click="revertAiCareNote(scope.row, props.row)"
                          />
                        </el-tooltip>
                      </template>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>

        <!-- Parent Columns in Exact Specification -->
        <el-table-column prop="carer_full_name" label="Employee Name" min-width="160" sortable />
        
        <el-table-column prop="status" label="Status" width="130" align="center">
          <template #default="scope">
            <el-tag :type="getStatusTag(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="occurrence_date" label="Date" width="110" sortable align="center" />
        <el-table-column prop="occurrence_day" label="Day" width="100" align="center" />
        <el-table-column prop="location" label="Location" width="130" align="center" />
        <el-table-column prop="shift_code" label="Scheduled Shift" width="140" align="center" sortable>
          <template #default="scope">
            <span class="shift-code" :style="shiftCodeStyle(scope.row.shift_color)">
              {{ scope.row.shift_code }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="service_user_name" label="Service User(s)" min-width="160" />

        <el-table-column label="Clock In" width="130" align="center">
          <template #default="scope">
            <input
              v-if="editingParentId === scope.row.occurrence_id"
              v-model="parentClockDraft.clock_in"
              type="time"
              class="clock-input"
            />
            <span v-else>{{ formatTimeToHHMM(scope.row.clock_in) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Clock Out" width="130" align="center">
          <template #default="scope">
            <input
              v-if="editingParentId === scope.row.occurrence_id"
              v-model="parentClockDraft.clock_out"
              type="time"
              class="clock-input"
            />
            <span v-else>{{ formatTimeToHHMM(scope.row.clock_out) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Break (Unpaid)" width="120" align="center">
          <template #default="scope">
            {{ displayedHours(scope.row).breakHrs }}
          </template>
        </el-table-column>
        <el-table-column label="Hours Worked" width="120" align="center">
          <template #default="scope">
            {{ displayedHours(scope.row).worked }}
          </template>
        </el-table-column>
        <el-table-column label="Payable Hours" width="120" align="center">
          <template #default="scope">
            <strong>{{ displayedHours(scope.row).payable }}</strong>
          </template>
        </el-table-column>

        <!-- Parent Action Buttons -->
        <el-table-column label="Actions" width="120" align="center" fixed="right">
          <template #default="scope">
            <template v-if="editingParentId === scope.row.occurrence_id">
              <el-button size="small" type="success" icon="Check" circle @click="confirmParentEdit(scope.row)" />
              <el-button size="small" type="danger" icon="Close" circle @click="cancelParentEdit(scope.row)" />
            </template>
            <el-tooltip v-else :content="`Modify DTR Details for ${scope.row.carer_full_name}`" placement="top">
              <el-button
                size="small"
                type="primary"
                icon="EditPen"
                circle
                @click="openModifyModal(scope.row)"
              />
            </el-tooltip>

            <el-tooltip v-if="authStore.isAdmin && editingParentId !== scope.row.occurrence_id" :content="`Clear / Reset Clock Times for ${scope.row.carer_full_name}`" placement="top">
              <el-button
                size="small"
                type="warning"
                icon="RefreshLeft"
                circle
                @click="openResetDialog(scope.row)"
              />
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <!-- Table Pagination (Default 50 Records per Page) -->
      <div class="pagination-container mt-15">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredDtrList.length"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- Enhanced DTR Details Dialog Form (Requirement #3 & #4: Employee Name & Occurrence Date fields removed) -->
    <el-dialog
      v-model="modifyModalVisible"
      :title="`DTR Details - ${editForm.carer_full_name || ''} (${editForm.occurrence_date || ''})`"
      width="680px"
      destroy-on-close
    >
      <el-form :model="editForm" label-width="170px">
        <el-form-item label="Clock In">
          <el-time-picker v-model="editForm.clock_in" format="HH:mm" value-format="HH:mm" placeholder="HH:mm" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="Clock Out">
          <el-time-picker v-model="editForm.clock_out" format="HH:mm" value-format="HH:mm" placeholder="HH:mm" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="Attendance / Leave Status">
          <el-select v-model="editForm.leave_type_id" placeholder="Select Leave Status (Default: Working / On Duty)" clearable style="width: 100%;" @change="onLeaveTypeChange">
            <el-option label="Working / On Duty (No Leave)" :value="null" />
            <el-option label="Annual Leave" :value="1" />
            <el-option label="Sick Leave" :value="2" />
            <el-option label="Maternity Leave" :value="3" />
            <el-option label="Compassionate Leave" :value="4" />
            <el-option label="Unpaid Leave" :value="5" />
          </el-select>
        </el-form-item>

        <el-form-item label="Full Attendance">
          <el-checkbox v-model="editForm.full_attendance" @change="onFullAttendanceChange">
            Full Attendance (Auto-fill Scheduled Times)
          </el-checkbox>
        </el-form-item>

        <el-divider>Assigned Service Users / Visits</el-divider>

        <div class="mb-15" style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600;">Visit Assignments ({{ dialogServiceUsers.length }})</span>
          <el-button type="success" size="small" icon="Plus" @click="addServiceUserVisit">
            Add Visit
          </el-button>
        </div>

        <el-table :data="dialogServiceUsers" size="small" border stripe style="width: 100%; margin-bottom: 15px;">
          <el-table-column label="Service User" min-width="150">
            <template #default="scope">
              <el-select v-model="scope.row.su_id" placeholder="Select Service User" filterable size="small" style="width: 100%;" @change="onDialogSuChange(scope.row)">
                <el-option
                  v-for="su in suList"
                  :key="su.su_id || su.id"
                  :label="su.su_full_name || (su.first_name + ' ' + su.surname)"
                  :value="su.su_id || su.id"
                />
              </el-select>
            </template>
          </el-table-column>

          <el-table-column label="Sched Start" width="110">
            <template #default="scope">
              <el-time-picker v-model="scope.row.start_time" format="HH:mm" value-format="HH:mm" size="small" style="width: 90px;" />
            </template>
          </el-table-column>

          <el-table-column label="Sched End" width="110">
            <template #default="scope">
              <el-time-picker v-model="scope.row.end_time" format="HH:mm" value-format="HH:mm" size="small" style="width: 90px;" />
            </template>
          </el-table-column>

          <el-table-column label="Clock In" width="110">
            <template #default="scope">
              <el-time-picker v-model="scope.row.clock_in" format="HH:mm" value-format="HH:mm" size="small" style="width: 90px;" />
            </template>
          </el-table-column>

          <el-table-column label="Clock Out" width="110">
            <template #default="scope">
              <el-time-picker v-model="scope.row.clock_out" format="HH:mm" value-format="HH:mm" size="small" style="width: 90px;" />
            </template>
          </el-table-column>

          <el-table-column width="50" align="center">
            <template #default="scope">
              <el-button type="danger" icon="Delete" circle size="small" @click="removeServiceUserVisit(scope.$index)" />
            </template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <el-button @click="modifyModalVisible = false">Cancel</el-button>
        <el-button type="primary" @click="saveModifyForm">Save DTR Details</el-button>
      </template>
    </el-dialog>

    <!-- Modal for AI Care Plan Generator / Care Notes -->
    <el-dialog v-model="aiModalVisible" title="Care Plan Generator (Care Notes)" width="620px">
      <el-form label-position="top">
        <el-form-item label="Service User (Client)">
          <el-input v-model="aiForm.su_full_name" readonly />
        </el-form-item>
        <el-form-item label="Assigned Carer Staff">
          <el-input v-model="aiForm.carer_full_name" readonly />
        </el-form-item>
        <el-form-item label="Additional Clinical Observations & Care Visit Notes">
          <el-input
            v-model="aiNotes"
            type="textarea"
            :rows="4"
            placeholder="Enter clinical observations, mobility assessment, medication administration, and care tasks performed..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aiModalVisible = false">Close</el-button>
        <el-button type="success" :loading="generating" icon="MagicStick" @click="runAIGenerator">
          Generate Care Plan
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="careNoteVisible"
      :title="careNoteTitle"
      width="860px"
      top="4vh"
      @closed="releaseCareNoteUrl"
    >
      <iframe v-if="careNoteUrl" class="care-note-frame" :src="careNoteUrl" title="Care Note PDF"></iframe>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="Reset Attendance Clock Times" width="520px">
      <p class="reset-note">Resetting clock times clears recorded attendance timestamps and returns the schedule to an unconsumed state.</p>
      <div class="reset-field">
        <div class="reset-label">Target scope</div>
        <el-radio-group v-model="resetTarget" class="reset-radios">
          <el-radio value="all" label="all">All (employee and every service user visit)</el-radio>
          <el-radio value="main" label="main">Employee attendance only</el-radio>
        </el-radio-group>
      </div>
      <div class="reset-field">
        <div class="reset-label">Clear action</div>
        <el-radio-group v-model="resetClearType" class="reset-radios">
          <el-radio value="both" label="both">Clear both Clock In and Clock Out</el-radio>
          <el-radio value="in" label="in">Clear Clock In only</el-radio>
          <el-radio value="out" label="out">Clear Clock Out only</el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="resetDialogVisible = false">Cancel</el-button>
        <el-button type="danger" @click="executeReset">Clear and reset times</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import schedulerService from '@/service/scheduler'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()

const dtrTableRef = ref(null)
const expandedRowKeys = ref([])
const isAllExpanded = ref(false)

const nowDt = new Date()
const pad = n => String(n).padStart(2, '0')
const defaultStartOfMonth = `${nowDt.getFullYear()}-${pad(nowDt.getMonth() + 1)}-01`
const defaultEndOfMonthObj = new Date(nowDt.getFullYear(), nowDt.getMonth() + 1, 0)
const defaultEndOfMonth = `${defaultEndOfMonthObj.getFullYear()}-${pad(defaultEndOfMonthObj.getMonth() + 1)}-${pad(defaultEndOfMonthObj.getDate())}`

const GENERATE_RELOAD_KEY = 'dtr-generate-reload'

function takeGenerateReload() {
  try {
    const raw = sessionStorage.getItem(GENERATE_RELOAD_KEY)
    sessionStorage.removeItem(GENERATE_RELOAD_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    const range = parsed.dateRange
    if (Array.isArray(range) && range.length === 2 && range[0] && range[1]) return parsed
  } catch {
    /* Ignore a stale or unreadable reload note. */
  }
  return null
}

const pendingGenerateReload = takeGenerateReload()
const dateRange = ref(pendingGenerateReload?.dateRange || [defaultStartOfMonth, defaultEndOfMonth])
const searchQuery = ref('')
const loading = ref(false)
const generatingClocks = ref(false)

const currentPage = ref(1)
const pageSize = ref(50) // Default 50 records per page

const modifyModalVisible = ref(false)
const editForm = ref({})
const dialogServiceUsers = ref([])
const suList = ref([])
const leaveTypes = ref([
  { id: 1, name: 'Annual Leave' },
  { id: 2, name: 'Sick Leave' },
  { id: 3, name: 'Maternity Leave' },
  { id: 4, name: 'Compassionate Leave' },
  { id: 5, name: 'Unpaid Leave' }
])

const aiModalVisible = ref(false)
const aiForm = ref({})
const aiNotes = ref('')
const generating = ref(false)
const activeVisitRow = ref(null)
const activeParentRow = ref(null)

const dtrList = ref([])
const editingParentId = ref(null)
const parentClockDraft = ref({ clock_in: '', clock_out: '' })
const parentClockBackup = ref(null)
const editingChildKey = ref('')
const childClockDraft = ref({ clock_in: '', clock_out: '' })
const childClockBackup = ref(null)
const resetDialogVisible = ref(false)
const careNoteVisible = ref(false)
const careNoteUrl = ref('')
const careNoteTitle = ref('Care Note')
const resetTarget = ref('all')
const resetClearType = ref('both')
const resetRowTarget = ref(null)

function shiftCodeStyle(value) {
  const color = String(value || '').trim()
  if (!color || color === 'inherit') return {}
  return { color }
}

function formatTimeToHHMM(val) {
  if (!val) return ''
  if (typeof val === 'string') {
    if (val.includes('T')) return val.split('T')[1].substring(0, 5)
    if (val.includes(' ')) {
      const time = val.split(' ')[1]
      return time ? time.substring(0, 5) : val.substring(0, 5)
    }
    if (val.length >= 5 && val.includes(':')) return val.substring(0, 5)
  }
  return ''
}

function formatScheduledVisit(start, end) {
  if (start && end) return `${start} - ${end}`
  if (end) return `- ${end}`
  if (start) return start
  return ''
}

function displayedHours(row) {
  const clockIn = editingParentId.value === row.occurrence_id
    ? parentClockDraft.value.clock_in
    : row.clock_in
  if (!clockIn) return { worked: '', breakHrs: '', payable: '' }
  return calculateHours(row.scheduled_start, row.scheduled_end)
}

function isOnLeave(row) {
  return row && row.leave_type_id !== null && row.leave_type_id !== undefined && row.leave_type_id !== ''
}

function childEditKey(child, parent) {
  return `${parent.occurrence_id}:${child.id}`
}

function isChildEditing(child, parent) {
  return editingChildKey.value === childEditKey(child, parent)
}

function startParentEdit(row, _column, event) {
  if (event?.target?.closest?.('.nested-visits-container')) return
  if (!row || editingParentId.value === row.occurrence_id) return
  editingParentId.value = row.occurrence_id
  parentClockBackup.value = { clock_in: row.clock_in || '', clock_out: row.clock_out || '' }
  parentClockDraft.value = { ...parentClockBackup.value }
}

function cancelParentEdit(row) {
  if (parentClockBackup.value) {
    row.clock_in = parentClockBackup.value.clock_in
    row.clock_out = parentClockBackup.value.clock_out
  }
  editingParentId.value = null
}

async function confirmParentEdit(row) {
  row.clock_in = parentClockDraft.value.clock_in || ''
  row.clock_out = parentClockDraft.value.clock_out || ''
  const saved = await saveInlineParentRow(row)
  if (saved) {
    editingParentId.value = null
    await fetchDTR({ quiet: true })
  }
}

function startChildEdit(row, parent) {
  const key = childEditKey(row, parent)
  if (editingChildKey.value === key) return
  editingChildKey.value = key
  childClockBackup.value = { clock_in: row.clock_in || '', clock_out: row.clock_out || '' }
  childClockDraft.value = { ...childClockBackup.value }
}

function cancelChildEdit(row) {
  if (childClockBackup.value) {
    row.clock_in = childClockBackup.value.clock_in
    row.clock_out = childClockBackup.value.clock_out
  }
  editingChildKey.value = ''
}

async function confirmChildEdit(row, parent) {
  row.clock_in = childClockDraft.value.clock_in || ''
  row.clock_out = childClockDraft.value.clock_out || ''
  const saved = await saveInlineChildRow(row, parent)
  if (saved) {
    editingChildKey.value = ''
    await fetchDTR({ quiet: true })
  }
}

const filteredDtrList = computed(() => {
  return dtrList.value.filter(item => {
    return !searchQuery.value || 
      item.carer_full_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      item.service_user_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      item.location.toLowerCase().includes(searchQuery.value.toLowerCase())
  })
})

const paginatedDtrList = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredDtrList.value.slice(start, end)
})

function handleSizeChange(val) {
  pageSize.value = val
  currentPage.value = 1
}

function handleCurrentChange(val) {
  currentPage.value = val
}

function getStatusTag(status) {
  const label = String(status || '').toLowerCase()
  if (label === 'present') return 'success'
  if (label === 'marked absent' || label === 'unresolved absence') return 'danger'
  if (label.includes('leave')) return 'warning'
  return 'info'
}

function getDayOfWeek(dateStr) {
  if (!dateStr) return ''
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const d = new Date(dateStr)
  return days[d.getDay()] || ''
}

function calculateHours(scheduledStart, scheduledEnd) {
  if (!scheduledStart || !scheduledEnd) {
    return { worked: '00:00', breakHrs: '00:00', payable: '00:00' }
  }

  function parseMins(timeStr) {
    if (!timeStr) return 0
    const parts = timeStr.split(':').map(Number)
    return (parts[0] || 0) * 60 + (parts[1] || 0)
  }

  function formatMin(mins) {
    const h = String(Math.floor(mins / 60)).padStart(2, '0')
    const m = String(mins % 60).padStart(2, '0')
    return `${h}:${m}`
  }

  let startMins = parseMins(scheduledStart)
  let endMins = parseMins(scheduledEnd)

  if (endMins <= startMins) {
    endMins += 24 * 60
  }

  const totalMins = endMins - startMins
  const totalHrs = totalMins / 60

  let breakMins = 0
  if (totalHrs >= 12) {
    breakMins = 120
  } else if (totalHrs >= 6) {
    breakMins = 30
  }

  const payableMins = Math.max(0, totalMins - breakMins)

  return {
    worked: formatMin(totalMins),
    breakHrs: formatMin(breakMins),
    payable: formatMin(payableMins)
  }
}

function recalculateRow(row) {
  const calc = displayedHours(row)
  row.hours_worked = calc.worked
  row.break_hours = calc.breakHrs
  row.payable_hours = calc.payable
  if (row.leave_type) {
    row.status = row.leave_type
  } else if (row.clock_in) {
    row.status = 'Present'
  } else if (!row.status || row.status === 'Present') {
    row.status = 'Scheduled'
  }
}

function onDateRangeChange(val) {
  if (!val || val.length !== 2) return
  const start = new Date(val[0])
  const end = new Date(val[1])
  const diffDays = (end - start) / (1000 * 60 * 60 * 24)

  if (diffDays > 31) {
    ElMessage.warning('Date range cannot exceed 1 month (31 days). Clamped to 31 days.')
    const clampedEnd = new Date(start)
    clampedEnd.setDate(clampedEnd.getDate() + 30)
    dateRange.value = [val[0], clampedEnd.toISOString().substring(0, 10)]
  }
  currentPage.value = 1
  fetchDTR()
}

async function fetchDTR(options = {}) {
  const quiet = options.quiet === true
  loading.value = true
  if (!quiet) dtrList.value = []
  
  const startDate = dateRange.value && dateRange.value[0] ? dateRange.value[0] : '2026-07-01'
  const endDate = dateRange.value && dateRange.value[1] ? dateRange.value[1] : '2026-07-31'

  try {
    const response = await api.post('/attendances/report', { start: startDate, end: endDate })
    const records = response.data || response
    if (records && Array.isArray(records) && records.length) {
      dtrList.value = records.map(occ => {
        const sTime = formatTimeToHHMM(occ.scheduled_start) || '08:00'
        const eTime = formatTimeToHHMM(occ.scheduled_end) || '17:00'
        const clockIn = formatTimeToHHMM(occ.clock_in)
        const clockOut = formatTimeToHHMM(occ.clock_out)
        const calc = clockIn ? calculateHours(sTime, eTime) : { worked: '', breakHrs: '', payable: '' }

        const serviceUsers = (occ.service_users || []).map(su => {
          const suStart = formatTimeToHHMM(su.start_date)
          const suEnd = formatTimeToHHMM(su.end_date)
          const cIn = formatTimeToHHMM(su.clock_in)
          const cOut = formatTimeToHHMM(su.clock_out)

          return {
            id: su.id,
            su_id: su.su_id,
            su_full_name: su.su_full_name,
            scheduled_visit: formatScheduledVisit(suStart, suEnd),
            start_time: suStart,
            end_time: suEnd,
            clock_in: cIn,
            clock_out: cOut,
            is_care_note_generated: su.is_care_note_generated || false,
            care_note_filename: su.care_note_filename || null
          }
        })
        const serviceUserName = serviceUsers.map(su => su.su_full_name).join(', ')

        return {
          id: occ.id,
          occurrence_id: occ.occurrence_id || occ.id,
          user_id: occ.user_id,
          carer_full_name: occ.full_name,
          status: occ.status_label || 'Scheduled',
          occurrence_date: occ.occurrence_date,
          occurrence_day: getDayOfWeek(occ.occurrence_date),
          location: occ.branch_name || 'Barnes Branch',
          shift_id: occ.shift_id || null,
          user_shift_id: occ.user_shift_id || null,
          shift_code: occ.shift_code || '',
          shift_color: occ.shift_color || '',
          leave_type_id: occ.leave_type_id ?? null,
          leave_type: occ.leave_type || null,
          scheduled_start: sTime,
          scheduled_end: eTime,
          clock_in: clockIn,
          clock_out: clockOut,
          break_hours: calc.breakHrs,
          hours_worked: calc.worked,
          payable_hours: calc.payable,
          hourly_rate: 15.50,
          notes: '',
          service_users: serviceUsers,
          service_user_name: serviceUserName
        }
      })
      if (!quiet) ElMessage.success(`Loaded ${dtrList.value.length} Daily Time Records from database`)
      if (isAllExpanded.value) {
        expandedRowKeys.value = filteredDtrList.value.map(row => row.id)
        nextTick(() => {
          if (dtrTableRef.value) {
            paginatedDtrList.value.forEach(row => {
              dtrTableRef.value.toggleRowExpansion(row, true)
            })
          }
        })
      }
    } else if (!quiet) {
      dtrList.value = []
      ElMessage.warning('No DTR database records returned for the selected parameters.')
    }
  } catch (err) {
    console.error(err)
    if (!quiet) dtrList.value = []
    ElMessage.error('Failed to load database DTR records: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

function handleExpandChange(row, expandedRows) {
  expandedRowKeys.value = expandedRows.map(r => r.id)
  if (paginatedDtrList.value.length > 0 && expandedRows.length === paginatedDtrList.value.length) {
    isAllExpanded.value = true
  } else if (expandedRows.length === 0) {
    isAllExpanded.value = false
  }
}

function expandAll() {
  isAllExpanded.value = true
  expandedRowKeys.value = filteredDtrList.value.map(row => row.id)
  nextTick(() => {
    if (dtrTableRef.value) {
      paginatedDtrList.value.forEach(row => {
        dtrTableRef.value.toggleRowExpansion(row, true)
      })
    }
  })
  ElMessage.info('Expanded all DTR rows')
}

function collapseAll() {
  isAllExpanded.value = false
  expandedRowKeys.value = []
  nextTick(() => {
    if (dtrTableRef.value) {
      paginatedDtrList.value.forEach(row => {
        dtrTableRef.value.toggleRowExpansion(row, false)
      })
    }
  })
  ElMessage.info('Collapsed all DTR rows')
}

// Ensure expand/collapse state persists across pagination, search, and filtering
watch(paginatedDtrList, () => {
  if (isAllExpanded.value) {
    expandedRowKeys.value = filteredDtrList.value.map(row => row.id)
    nextTick(() => {
      if (dtrTableRef.value) {
        paginatedDtrList.value.forEach(row => {
          dtrTableRef.value.toggleRowExpansion(row, true)
        })
      }
    })
  }
})

// 1. Save Inline Parent Main Clock In/Out immediately to Database
function manualClock(value, onLeave) {
  if (onLeave || !value) return null
  return value
}

async function saveInlineParentRow(row) {
  const onLeave = isOnLeave(row)
  try {
    await api.post('/attendances/inputManualDTR', {
      user_id: row.user_id,
      shift_id: row.shift_id || null,
      user_shift_id: row.user_shift_id || null,
      occurrence_date: row.occurrence_date,
      clock_in: manualClock(row.clock_in, onLeave),
      clock_out: manualClock(row.clock_out, onLeave),
      full_attendance: false,
      leave_type_id: onLeave ? row.leave_type_id : null,
      leave_type: onLeave ? (row.leave_type || null) : null,
      service_users: (row.service_users || []).map(su => ({
        id: su.id,
        su_id: su.su_id,
        start_time: su.start_time,
        end_time: su.end_time,
        clock_in: manualClock(su.clock_in, onLeave),
        clock_out: manualClock(su.clock_out, onLeave)
      }))
    })
    ElMessage.success(`Clock times persisted to database for ${row.carer_full_name}`)
    return true
  } catch (err) {
    ElMessage.error('Failed to save inline clock times to database')
    return false
  }
}

// 2. Save Inline Child Visit Clock In/Out immediately to Database
async function saveInlineChildRow(childRow, parentRow) {
  const onLeave = isOnLeave(parentRow)
  try {
    await api.post('/attendances/inputManualDTR', {
      user_id: parentRow.user_id,
      shift_id: parentRow.shift_id || null,
      user_shift_id: parentRow.user_shift_id || null,
      occurrence_date: parentRow.occurrence_date,
      clock_in: manualClock(parentRow.clock_in, onLeave),
      clock_out: manualClock(parentRow.clock_out, onLeave),
      full_attendance: false,
      leave_type_id: onLeave ? parentRow.leave_type_id : null,
      leave_type: onLeave ? (parentRow.leave_type || null) : null,
      service_users: (parentRow.service_users || []).map(su => ({
        id: su.id,
        su_id: su.su_id,
        start_time: su.start_time,
        end_time: su.end_time,
        clock_in: manualClock(su.clock_in, onLeave),
        clock_out: manualClock(su.clock_out, onLeave)
      }))
    })
    ElMessage.success(`Visit clock times persisted to database for ${childRow.su_full_name}`)
    return true
  } catch (err) {
    ElMessage.error('Failed to save visit clock times to database')
    return false
  }
}

// 8. Automatic Clock Time Generation (Enforces Business Rules)
async function generateDummyTimes() {
  try {
    await ElMessageBox.confirm(
      'Generate automatic clock-in and clock-out times for shifts and assigned Service User visits in this date range, up to today?',
      'Generate Automatic Clock Times',
      { type: 'warning', confirmButtonText: 'Generate', cancelButtonText: 'Cancel' }
    )
  } catch {
    return
  }

  generatingClocks.value = true
  try {
    const startDate = dateRange.value && dateRange.value[0] ? dateRange.value[0] : '2026-07-01'
    const endDate = dateRange.value && dateRange.value[1] ? dateRange.value[1] : '2026-07-31'
    const res = await api.post('/attendances/generate-dummy-times', { start: startDate, end: endDate })
    sessionStorage.setItem(GENERATE_RELOAD_KEY, JSON.stringify({
      dateRange: [startDate, endDate],
      message: res.data?.message || 'Generated clock times successfully.'
    }))
    window.location.reload()
  } catch (err) {
    generatingClocks.value = false
    ElMessage.error('Error generating clock times')
  }
}

function openModifyModal(row) {
  const onLeave = row.leave_type_id !== null && row.leave_type_id !== undefined && row.leave_type_id !== ''
  editForm.value = {
    ...row,
    full_attendance: false,
    leave_type_id: onLeave ? row.leave_type_id : null,
    _previousLeaveTypeId: onLeave ? row.leave_type_id : null,
    clock_in: onLeave ? '' : (row.clock_in || ''),
    clock_out: onLeave ? '' : (row.clock_out || '')
  }
  dialogServiceUsers.value = (row.service_users || []).map(su => ({
    ...su,
    clock_in: onLeave ? '' : (su.clock_in || ''),
    clock_out: onLeave ? '' : (su.clock_out || '')
  }))
  modifyModalVisible.value = true
}

async function onLeaveTypeChange(val) {
  const previous = editForm.value._previousLeaveTypeId ?? null
  if (val !== null && val !== undefined) {
    const leaveName = leaveTypes.value.find(item => Number(item.id) === Number(val))?.name || 'a leave status'
    try {
      await ElMessageBox.confirm(
        `Changing the status to "${leaveName}" will clear all Clock In and Clock Out times for this carer and all assigned visits. Once saved, previous clock times cannot be restored.`,
        'Warning: Clear Clock In and Clock Out',
        { type: 'warning', confirmButtonText: 'Proceed and clear times', cancelButtonText: 'Cancel' }
      )
      editForm.value._previousLeaveTypeId = val
      editForm.value.full_attendance = false
      editForm.value.clock_in = ''
      editForm.value.clock_out = ''
      dialogServiceUsers.value.forEach(su => {
        su.clock_in = ''
        su.clock_out = ''
      })
    } catch {
      editForm.value.leave_type_id = previous
    }
    return
  }
  editForm.value._previousLeaveTypeId = null
  if (!editForm.value.clock_in && editForm.value.scheduled_start) editForm.value.clock_in = editForm.value.scheduled_start
  if (!editForm.value.clock_out && editForm.value.scheduled_end) editForm.value.clock_out = editForm.value.scheduled_end
  dialogServiceUsers.value.forEach(su => {
    if (!su.clock_in) su.clock_in = su.start_time || editForm.value.scheduled_start || '08:00'
    if (!su.clock_out) su.clock_out = su.end_time || editForm.value.scheduled_end || '17:00'
  })
}

function onFullAttendanceChange(val) {
  if (!val || isOnLeave(editForm.value)) return
  if (val) {
    editForm.value.clock_in = editForm.value.scheduled_start
    editForm.value.clock_out = editForm.value.scheduled_end
    dialogServiceUsers.value.forEach(su => {
      su.clock_in = su.start_time || editForm.value.scheduled_start
      su.clock_out = su.end_time || editForm.value.scheduled_end
    })
  }
}

function onDialogSuChange(row) {
  const suObj = suList.value.find(s => Number(s.su_id || s.id) === Number(row.su_id))
  if (suObj) {
    row.su_full_name = suObj.su_full_name || `${suObj.first_name || ''} ${suObj.surname || ''}`.trim()
  }
}

function addServiceUserVisit() {
  dialogServiceUsers.value.push({
    id: null,
    su_id: null,
    su_full_name: '',
    scheduled_visit: `${editForm.value.scheduled_start || '08:00'} - ${editForm.value.scheduled_end || '17:00'}`,
    start_time: editForm.value.scheduled_start || '08:00',
    end_time: editForm.value.scheduled_end || '17:00',
    clock_in: '',
    clock_out: ''
  })
}

function removeServiceUserVisit(index) {
  dialogServiceUsers.value.splice(index, 1)
}

// 3. Save DTR Details Form
async function saveModifyForm() {
  try {
    const onLeave = isOnLeave(editForm.value)
    const selectedLeave = (leaveTypes.value || []).find(l => Number(l.id) === Number(editForm.value.leave_type_id))
    const leaveName = onLeave
      ? (selectedLeave ? selectedLeave.name : (editForm.value.leave_type || null))
      : null
    const useSchedule = !onLeave && editForm.value.full_attendance
    const clockIn = onLeave ? null : (useSchedule ? (editForm.value.scheduled_start || null) : (editForm.value.clock_in || null))
    const clockOut = onLeave ? null : (useSchedule ? (editForm.value.scheduled_end || null) : (editForm.value.clock_out || null))

    const payload = {
      user_id: editForm.value.user_id,
      shift_id: editForm.value.shift_id || null,
      user_shift_id: editForm.value.user_shift_id || null,
      occurrence_date: editForm.value.occurrence_date,
      clock_in: clockIn,
      clock_out: clockOut,
      full_attendance: useSchedule,
      leave_type_id: onLeave ? editForm.value.leave_type_id : null,
      leave_type: leaveName,
      service_users: (dialogServiceUsers.value || []).map(su => ({
        id: su.id,
        su_id: su.su_id,
        start_time: su.start_time,
        end_time: su.end_time,
        clock_in: onLeave ? null : (useSchedule ? (su.start_time || editForm.value.scheduled_start || null) : (su.clock_in || null)),
        clock_out: onLeave ? null : (useSchedule ? (su.end_time || editForm.value.scheduled_end || null) : (su.clock_out || null))
      }))
    }

    await api.post('/attendances/inputManualDTR', payload)
    modifyModalVisible.value = false
    ElMessage.success('Saved DTR Details to database')
    await fetchDTR({ quiet: true })
  } catch (err) {
    console.error('Error saving DTR details:', err)
    ElMessage.error('Failed to save DTR details: ' + (err.response?.data?.detail || err.message))
  }
}

function openResetDialog(row) {
  resetRowTarget.value = row
  resetTarget.value = 'all'
  resetClearType.value = 'both'
  resetDialogVisible.value = true
}

function clearClockField(target, clearType) {
  if (clearType === 'in' || clearType === 'both') target.clock_in = ''
  if (clearType === 'out' || clearType === 'both') target.clock_out = ''
}

async function executeReset() {
  const row = resetRowTarget.value
  if (!row) return
  if (!row.user_id || !row.shift_id) {
    ElMessage.error('This schedule has no shift to reset')
    return
  }
  try {
    await api.post('/attendances/reset', {
      user_id: row.user_id,
      shift_id: row.shift_id,
      attendance_date: row.occurrence_date,
      target_type: resetTarget.value,
      target_id: null,
      clear_type: resetClearType.value
    })
    if (resetTarget.value === 'all' || resetTarget.value === 'main') clearClockField(row, resetClearType.value)
    if (resetTarget.value === 'all' && row.service_users) {
      row.service_users.forEach(su => clearClockField(su, resetClearType.value))
    }
    recalculateRow(row)
    resetDialogVisible.value = false
    ElMessage.success(`Clock times reset for ${row.carer_full_name}`)
    await fetchDTR({ quiet: true })
  } catch (err) {
    ElMessage.error('Error resetting clock times')
  }
}

// 5 & 6. Open AI Care Notes Modal
function openAICarePlanModalForVisit(visitRow, parentRow) {
  activeVisitRow.value = visitRow
  activeParentRow.value = parentRow
  aiForm.value = {
    su_full_name: visitRow.su_full_name,
    carer_full_name: parentRow.carer_full_name,
    scheduled_visit: visitRow.scheduled_visit,
    occurrence_date: parentRow.occurrence_date
  }
  aiNotes.value = '' // Empty by default; optional additional carer observations
  aiModalVisible.value = true
}

// 5 & 6. Run AI Care Note Generator and Store PDF on Server
async function runAIGenerator() {
  generating.value = true
  try {
    const visit = activeVisitRow.value
    const payload = {
      su_id: visit ? visit.su_id : null,
      user_id: activeParentRow.value ? activeParentRow.value.user_id : null,
      date: aiForm.value.occurrence_date,
      shift: activeParentRow.value ? (activeParentRow.value.shift_code || 'LD') : 'LD',
      visit_id: visit ? visit.id : null,
      visit_clock_in: visit ? (visit.clock_in || '') : '',
      visit_clock_out: visit ? (visit.clock_out || '') : '',
      scheduled_visit_start: visit ? (visit.start_time || '') : '',
      scheduled_visit_end: visit ? (visit.end_time || '') : '',
      time_in: visit ? (visit.clock_in || visit.start_time || '08:00') : '08:00',
      time_out: visit ? (visit.clock_out || visit.end_time || '17:00') : '17:00',
      patient_name: aiForm.value.su_full_name,
      carer_name: aiForm.value.carer_full_name,
      clinical_notes: aiNotes.value
    }
    const res = await api.post('/care-notes/generate', payload)
    if (res.data && res.data.success) {
      ElMessage.success('AI Person-Centred Care Note PDF generated & saved to server!')
      if (activeVisitRow.value) {
        activeVisitRow.value.is_care_note_generated = true
        activeVisitRow.value.care_note_filename = res.data.filename
      }
      aiModalVisible.value = false
    } else {
      ElMessage.error(res.data?.message || 'Failed to generate Care Note')
    }
  } catch (err) {
    ElMessage.error('Error generating AI Care Note')
  } finally {
    generating.value = false
  }
}

function releaseCareNoteUrl() {
  if (careNoteUrl.value) {
    URL.revokeObjectURL(careNoteUrl.value)
    careNoteUrl.value = ''
  }
}

// View the care note inside the page. The request carries the login token.
async function viewCareNotePdf(visitRow) {
  const filename = visitRow?.care_note_filename
  if (!filename) {
    ElMessage.warning('No care note PDF file found for this visit.')
    return
  }
  try {
    const response = await api.get(`/care-notes/view/${encodeURIComponent(filename)}`, {
      responseType: 'blob'
    })
    releaseCareNoteUrl()
    const pdf = new Blob([response.data], { type: 'application/pdf' })
    careNoteUrl.value = URL.createObjectURL(pdf)
    careNoteTitle.value = visitRow.su_full_name ? `Care Note - ${visitRow.su_full_name}` : 'Care Note'
    careNoteVisible.value = true
  } catch (err) {
    if (err.response?.status === 404) {
      ElMessage.error('Care Note file was not found on the server.')
    } else if (err.response?.status !== 401) {
      ElMessage.error('Could not open the Care Note PDF.')
    }
  }
}

// 6 & 7. Revert / Delete Care Note PDF from Server
async function revertAiCareNote(visitRow, parentRow) {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to revert/delete the AI Care Note PDF for ${visitRow.su_full_name}?`,
      'Revert Care Note',
      { type: 'warning', confirmButtonText: 'Revert & Delete', cancelButtonText: 'Cancel' }
    )
    if (visitRow.care_note_filename) {
      await api.delete(`/care-notes/revert/${visitRow.care_note_filename}`)
    }
    visitRow.is_care_note_generated = false
    visitRow.care_note_filename = null
    ElMessage.success(`Care Note deleted from server for ${visitRow.su_full_name}`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Error reverting Care Note')
    }
  }
}

function exportCSV() {
  if (!filteredDtrList.value.length) {
    ElMessage.warning('No DTR records available to download')
    return
  }
  const headers = ['Employee Name', 'Status', 'Date', 'Day', 'Location', 'Scheduled Shift', 'Service User(s)', 'Clock In', 'Clock Out', 'Break (Unpaid)', 'Hours Worked', 'Payable Hours']
  const rows = filteredDtrList.value.map(r => [
    `"${r.carer_full_name}"`,
    `"${r.status}"`,
    `"${r.occurrence_date}"`,
    `"${r.occurrence_day}"`,
    `"${r.location}"`,
    `"${r.shift_code || ''}"`,
    `"${r.service_user_name}"`,
    `"${r.clock_in || ''}"`,
    `"${r.clock_out || ''}"`,
    `"${r.break_hours}"`,
    `"${r.hours_worked}"`,
    `"${r.payable_hours}"`
  ])
  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `Daily_Time_Records_${new Date().toISOString().substring(0, 10)}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('Downloaded Daily Time Records CSV successfully!')
}

onMounted(async () => {
  try {
    const res = await schedulerService.getServiceUsers()
    if (res) {
      suList.value = Array.isArray(res) ? res : (res.data || [])
    }
    await fetchDTR()
    if (pendingGenerateReload?.message) {
      ElMessage.success(pendingGenerateReload.message)
    }
  } catch (err) {
    console.error('Failed to load Service Users list or DTR records', err)
  }
})
</script>

<style scoped>
.dtr-container {
  padding: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title-box {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
  font-weight: 600;
}
.title-icon {
  font-size: 20px;
  color: var(--el-color-primary);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.table-menu-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 12px;
}
.right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nested-visits-container {
  padding: 10px 15px;
  background-color: var(--el-fill-color-blank);
  border-radius: 4px;
}
.child-table-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 8px;
  font-size: 0.9rem;
}
.care-notes-actions,
.clock-actions {
  display: flex;
  gap: 4px;
  justify-content: center;
  align-items: center;
}
.shift-code {
  font-weight: 600;
  color: inherit;
}
.clock-input {
  width: 108px;
  padding: 4px 6px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-primary);
}
.reset-note {
  margin-top: 0;
  color: var(--el-text-color-secondary);
}
.reset-field {
  margin-top: 16px;
}
.reset-label {
  margin-bottom: 8px;
  font-weight: 600;
}
.reset-radios {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.reset-radios :deep(.el-radio) {
  display: flex;
  height: auto;
  margin-right: 0;
  white-space: normal;
}
.care-note-frame {
  width: 100%;
  height: 72vh;
  border: 0;
  background: #fff;
}
.mt-15 {
  margin-top: 15px;
}
.mb-15 {
  margin-bottom: 15px;
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
}
</style>
