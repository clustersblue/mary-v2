<template>
  <div class="care-planner-container">
    <!-- Element Plus Header Bar (Top Actions, Search, & Filters) -->
    <div class="el-header-bar">
      <div class="header-left">
        <h2 class="header-title">Care Rota Planner</h2>
      </div>

      <div class="header-right-actions">
        <!-- Element Plus Action Buttons -->
        <el-button icon="Plus" type="primary" size="default" @click="() => openNewShiftDialog()">
          New Shift Assignment
        </el-button>
        <el-tooltip
          class="box-item"
          content="Refresh Schedule"
          placement="bottom"
        >
          <el-button icon="Refresh" circle size="default" @click="loadPlannerData" />
        </el-tooltip>
        <el-tooltip
          class="box-item"
          content="Print Rota (Clean Calendar Layout)"
          placement="bottom"
        >
          <el-button icon="Printer" circle size="default" @click="printRota" />
        </el-tooltip>
        <el-tooltip
          class="box-item"
          content="Export CSV (Current View Range)"
          placement="bottom"
        >
          <el-button icon="Download" circle size="default" @click="exportCSV" />
        </el-tooltip>
        <el-tooltip
          class="box-item"
          content="Bulk Delete Recurrences for Client"
          placement="bottom"
        >
          <el-button icon="Delete" circle type="danger" plain size="default" @click="openDeleteRecurrenceDrawer" />
        </el-tooltip>

        <!-- Search Input by Staff or Client Name matching Legacy -->
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="Search client or carer..."
            prefix-icon="Search"
            clearable
            class="header-search-input"
            @input="onSearchInput"
            @clear="loadPlannerData"
          />
        </div>
      </div>
    </div>

    <!-- Syncfusion Component Container with Complete Legacy Parity -->
    <div
      id="printable-rota"
      class="syncfusion-scheduler-container"
      v-loading="loading"
      element-loading-text="Loading care rota planner..."
      element-loading-background="rgba(15, 23, 42, 0.45)"
    >
      <ejs-schedule
        ref="scheduleObj"
        id="schedule"
        width="100%"
        height="750px"
        dateFormat="dd-MMM-yyyy"
        :selectedDate="initialSelectedDate"
        currentView="Month"
        :eventSettings="eventSettings"
        startHour="06:00"
        endHour="24:00"
        :timeScale="{ enable: true, interval: 60, slotCount: 2 }"
        :showQuickInfo="false"
        :allowDragAndDrop="true"
        :allowResizing="true"
        :allowOverlap="false"
        :firstDayOfWeek="0"
        :workDays="[0, 1, 2, 3, 4, 5, 6]"
        :workHours="{ highlight: true, start: '08:00', end: '16:00' }"
        :renderCell="onRenderCell"
        @cellDoubleClick="onCellDoubleClick"
        @eventRendered="onEventRendered"
        @eventClick="onSyncfusionEventClick"
        @actionBegin="onSyncfusionActionBegin"
        @actionComplete="onSyncfusionActionComplete"
      >
        <e-views>
          <e-view option="Day" />
          <e-view option="Week" />
          <e-view option="Month" />
          <e-view option="TimelineDay" />
          <e-view option="TimelineWeek" />
          <e-view option="TimelineMonth" />
          <e-view option="Agenda" />
        </e-views>

        <e-resources>
          <e-resource
            field="shift_id"
            title="Shifts"
            name="Shift"
            :dataSource="resourceDataSource"
            textField="shift"
            idField="shift_id"
            colorField="shift_color"
          />
        </e-resources>

        <!-- Tooltip Template matching Legacy MaryDtrPlanner and Screenshot 1 -->
        <template v-slot:tooltipTemplate="{ data }">
          <div class="syncfusion-event-tooltip" style="padding: 10px; font-size: 13px; line-height: 1.6; color: #ffffff; min-width: 240px; max-width: 280px;">
            <div style="font-weight: 700; font-size: 14px; border-bottom: 1px solid #475569; padding-bottom: 6px; margin-bottom: 6px; color: #ffffff;">
              <div style="color: #67e8f9; margin-bottom: 2px;">
                <span style="font-size: 11px; text-transform: uppercase; color: #94a3b8; display: block;">Service User (Client):</span>
                {{ data.service_user_name || 'Client Not Assigned' }}
              </div>
              <div style="color: #f8fafc; margin-top: 4px;">
                <span style="font-size: 11px; text-transform: uppercase; color: #94a3b8; display: block;">Carer / Staff:</span>
                {{ data.carer_full_name || data.Subject }}
              </div>
            </div>
            <div><span style="font-weight: 600; color: #94a3b8;">Shift:</span> {{ data.shift_code || 'Shift' }}</div>
            <div><span style="font-weight: 600; color: #94a3b8;">Location:</span> {{ getBranchName(data.branch_id || data.BranchId) }}</div>
            <div style="margin-top: 4px; border-top: 1px dashed #475569; padding-top: 4px; font-size: 12px; color: #cbd5e1;">
              <div><strong>Start:</strong> {{ formatTooltipDateTime(data.StartTime, data.shift_start) }}</div>
              <div><strong>End:</strong> {{ formatTooltipDateTime(data.EndTime, data.shift_end) }}</div>
            </div>
            <div style="margin-top: 6px;" v-if="data.IsRecurring || data.rrule_str || data.RecurrenceRule">
              <el-tag size="small" type="primary" effect="dark">
                🔄 Recurring Series (until {{ (data.series_end_date || data.SeriesEndDate || 'end').substring(0, 10) }})
              </el-tag>
            </div>
          </div>
        </template>
      </ejs-schedule>
    </div>

    <!-- Element Plus Dialog for Shift Create / Edit / Delete -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditMode ? 'Edit Shift Assignment' : 'Create New Shift Assignment'"
      width="640px"
      destroy-on-close
      class="shift-form-dialog"
    >
      <!-- Recurring Series Informational Banner in Edit Mode -->
      <el-alert
        v-if="isEditMode && (currentEvent?.IsRecurring || currentEvent?.rrule_str || recurrenceMode !== 'none')"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 16px;"
        :title="`Recurring Shift Series (active until ${form.end_date || 'end date'})`"
        description="This occurrence is part of a series. When saving or deleting, choose whether to apply changes to this occurrence only, future occurrences, or all occurrences."
      />

      <el-form :model="form" label-width="25%" class="shift-form">
        <!-- Searchable Service User Dropdown (Client) First matching Care Planner -->
        <el-form-item label="Service User (Client)" required>
          <el-select v-model="form.su_id" placeholder="Select Service User" filterable style="width: 100%;">
            <el-option
              v-for="su in serviceUsers"
              :key="su.su_id"
              :label="su.su_full_name || `${su.first_name} ${su.surname}`"
              :value="su.su_id"
            />
          </el-select>
        </el-form-item>

        <!-- Searchable Carer Dropdown -->
        <el-form-item label="Carer / Staff" required>
          <el-select v-model="form.user_id" placeholder="Select Carer Staff" filterable style="width: 100%;">
            <el-option
              v-for="c in carers"
              :key="c.id"
              :label="c.carer_full_name || `${c.first_name} ${c.surname}`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>

        <!-- Shift Code tied directly to mary_api_db_new.m_shifts catalog -->
        <el-form-item label="Shift Code" required>
          <el-select
            v-model="form.shift_id"
            placeholder="Select Shift from catalog"
            filterable
            clearable
            style="width: 100%;"
            @change="onShiftTemplateChange"
          >
            <el-option
              v-for="s in shiftTemplates"
              :key="s.shift_id || s.id"
              :label="`${s.shift || s.shift_name || s.shift_code} (${s.start_time || '08:00'} - ${s.end_time || '17:00'})`"
              :value="s.shift_id || s.id"
            />
          </el-select>
        </el-form-item>

        <!-- Branch / Location Dropdown with User-Friendly Names -->
        <el-form-item label="Location / Branch">
          <el-select v-model="form.branch_id" placeholder="Select Location Branch" filterable clearable style="width: 100%;">
            <el-option
              v-for="b in branches"
              :key="b.branch_id || b.id"
              :label="b.branch || b.branch_name || ('Branch #' + (b.branch_id || b.id))"
              :value="b.branch_id || b.id"
            />
          </el-select>
        </el-form-item>

        <!-- Start & End Time Pickers -->
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Start Time" label-width="100px">
              <el-time-picker
                v-model="form.start_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="Start Time"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="End Time" label-width="100px">
              <el-time-picker
                v-model="form.end_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="End Time"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Start Date">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            placeholder="Select Start Date"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>

        <!-- Recurrence Selection -->
        <el-form-item label="Recurrence">
          <el-radio-group v-model="recurrenceMode" @change="onRecurrenceModeChange">
            <el-radio-button label="none">One-Time</el-radio-button>
            <el-radio-button label="daily">Daily</el-radio-button>
            <el-radio-button label="custom">Custom Days</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- Custom Days Checkboxes -->
        <el-form-item label="Active Days" v-if="recurrenceMode === 'custom'">
          <el-checkbox-group v-model="selectedWeekdays" @change="updateRruleString">
            <el-checkbox label="MO">Mon</el-checkbox>
            <el-checkbox label="TU">Tue</el-checkbox>
            <el-checkbox label="WE">Wed</el-checkbox>
            <el-checkbox label="TH">Thu</el-checkbox>
            <el-checkbox label="FR">Fri</el-checkbox>
            <el-checkbox label="SA">Sat</el-checkbox>
            <el-checkbox label="SU">Sun</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="Recurrence End Date" v-if="recurrenceMode !== 'none'">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            placeholder="Recurrence End Date"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="Double-Up Shift">
          <el-switch v-model="form.doubleup" active-text="2 Carers Required" />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">Cancel</el-button>
          <el-button v-if="isEditMode" type="danger" @click="promptDeleteShift">
            Delete Shift
          </el-button>
          <el-button type="primary" :loading="saving" @click="promptSaveShift">
            {{ isEditMode ? 'Update Shift' : 'Create Shift' }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Recurrence Update/Delete Action Prompt Dialog -->
    <el-dialog
      v-model="recurrencePromptVisible"
      title="Recurring Shift Assignment"
      width="460px"
      destroy-on-close
    >
      <div style="font-size: 14px; color: #1e293b; margin-bottom: 15px; line-height: 1.5;">
        This shift on <strong>{{ currentEvent?.OccurrenceDate || form.start_date }}</strong> is part of a recurring series active until <strong>{{ form.end_date }}</strong>. Which occurrences would you like to {{ recurrencePromptAction }}?
      </div>
      <el-radio-group v-model="recurrenceModeChoice" direction="vertical" style="width: 100%;">
        <el-radio label="single" border style="width: 100%; margin-bottom: 10px;">
          <div style="font-weight: 700;">This occurrence only</div>
          <div style="font-size: 12px; color: #64748b;">Modify or remove only this single shift date</div>
        </el-radio>
        <el-radio label="future" border style="width: 100%; margin-bottom: 10px;">
          <div style="font-weight: 700;">This and future occurrences</div>
          <div style="font-size: 12px; color: #64748b;">Apply changes starting from this date onward</div>
        </el-radio>
        <el-radio label="all" border style="width: 100%;">
          <div style="font-weight: 700;">Entire series</div>
          <div style="font-size: 12px; color: #64748b;">Apply changes to all past and future shifts in series</div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="recurrencePromptVisible = false">Cancel</el-button>
          <el-button type="primary" :loading="saving" @click="confirmRecurrenceExecution">
            Confirm Action
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Element Plus Drawer for Bulk Deleting Recurrences for Service User matching Legacy -->
    <el-drawer
      v-model="deleteRecurrenceDrawerVisible"
      title="Delete Recurrences for Service User"
      size="420px"
      destroy-on-close
    >
      <div style="font-size: 13px; color: #64748b; margin-bottom: 18px;">
        Select a client and date range to remove recurring rota assignments.
      </div>
      <el-form label-position="top">
        <el-form-item label="Service User (Client)" required>
          <el-select v-model="deleteRecurrenceSuId" placeholder="Select Service User" filterable style="width: 100%;">
            <el-option
              v-for="su in serviceUsers"
              :key="su.su_id"
              :label="su.su_full_name || `${su.first_name} ${su.surname}`"
              :value="su.su_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Date Range" required>
          <el-date-picker
            v-model="deleteRecurrenceRange"
            type="daterange"
            range-separator="To"
            start-placeholder="Start Date"
            end-placeholder="End Date"
            value-format="YYYY-MM-DD"
            style="width: 100%;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <el-button @click="deleteRecurrenceDrawerVisible = false">Cancel</el-button>
          <el-button type="danger" :loading="deletingRecurrence" @click="confirmDeleteRecurrence">
            Delete Recurrences
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, provide, nextTick } from 'vue'
import {
  ScheduleComponent as EjsSchedule,
  ViewsDirective as EViews,
  ViewDirective as EView,
  ResourcesDirective as EResources,
  ResourceDirective as EResource,
  Day,
  Week,
  Month,
  Year,
  TimelineViews,
  TimelineMonth,
  Agenda,
  Resize,
  DragAndDrop,
  Print,
  ExcelExport
} from '@syncfusion/ej2-vue-schedule'
import '@syncfusion/ej2-base/styles/material.css'
import '@syncfusion/ej2-buttons/styles/material.css'
import '@syncfusion/ej2-calendars/styles/material.css'
import '@syncfusion/ej2-dropdowns/styles/material.css'
import '@syncfusion/ej2-inputs/styles/material.css'
import '@syncfusion/ej2-navigations/styles/material.css'
import '@syncfusion/ej2-popups/styles/material.css'
import '@syncfusion/ej2-vue-schedule/styles/material.css'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Printer,
  Download,
  Search,
  Delete
} from '@element-plus/icons-vue'
import schedulerService from '@/service/scheduler'

provide('schedule', [Day, Week, Month, Year, TimelineViews, TimelineMonth, Agenda, Resize, DragAndDrop, Print, ExcelExport])

const scheduleObj = ref(null)
const initialSelectedDate = ref(new Date())

// Filters
const selectedCarer = ref(null)
const selectedServiceUser = ref(null)
const searchQuery = ref('')
let searchDebounceTimer = null

// Bulk Recurrence Deletion Drawer State
const deleteRecurrenceDrawerVisible = ref(false)
const deleteRecurrenceSuId = ref(null)
const deleteRecurrenceRange = ref([])
const deletingRecurrence = ref(false)

// Raw Data loaded directly from DB
const carers = ref([])
const serviceUsers = ref([])
const shiftTemplates = ref([])
const branches = ref([])
const events = ref([])

// Form & Dialog State
const loading = ref(false)
const dialogVisible = ref(false)
const isEditMode = ref(false)
const saving = ref(false)

// Active selected event metadata for CRUD & Recurrence
const currentEvent = ref(null)
const currentShiftId = ref(null)

// Recurrence Choice Modal State
const recurrencePromptVisible = ref(false)
const recurrencePromptAction = ref('update')
const recurrenceModeChoice = ref('all')

const recurrenceMode = ref('none')
const selectedWeekdays = ref(['MO', 'TU', 'WE', 'TH', 'FR'])

const form = ref({
  user_id: null,
  su_id: null,
  shift_id: null,
  branch_id: null,
  start_date: new Date().toISOString().substring(0, 10),
  end_date: '',
  start_time: '08:00',
  end_time: '17:00',
  rrule_str: '',
  doubleup: false,
  status: 'confirmed'
})

// Database-driven Shift Resource Data Source from mary_api_db_new.m_shifts
const resourceDataSource = computed(() => {
  return shiftTemplates.value.map(s => ({
    shift_id: s.shift_id || s.id,
    shift: s.shift || s.shift_name || s.shift_code,
    shift_color: s.shift_color
  }))
})

// Convert Backend Events to Syncfusion Scheduler Event Schema with Complete Parity
const syncfusionEvents = computed(() => {
  const seenMap = new Set()
  return events.value
    .filter(e => {
      const uId = e.user_id || e.CarerId
      const sId = e.su_id || e.ServiceUserId
      if (selectedCarer.value && uId !== selectedCarer.value) return false
      if (selectedServiceUser.value && sId !== selectedServiceUser.value) return false

      // Defense-in-depth: Deduplicate events with identical Carer, Client, Date, and Time
      const sDateStr = (e.start || e.start_date || e.StartTime || '').toString().substring(0, 16)
      const eDateStr = (e.end || e.end_date || e.EndTime || '').toString().substring(0, 16)
      const dedupKey = `${uId}_${sId}_${sDateStr}_${eDateStr}`
      if (seenMap.has(dedupKey)) return false
      seenMap.add(dedupKey)

      return true
    })
    .map(e => {
      const carerObj = e.carer || carers.value.find(c => c.id === (e.user_id || e.CarerId))
      const carerName = e.carer_full_name || e.carer_name || (carerObj ? (carerObj.carer_full_name || `${carerObj.first_name} ${carerObj.surname}`) : '')

      const suObj = e.service_user || serviceUsers.value.find(su => su.su_id === (e.su_id || e.ServiceUserId))
      const suName = e.service_user_name || (suObj ? (suObj.su_full_name || `${suObj.first_name} ${suObj.surname}`) : '')

      const shiftId = e.shift_id || e.ShiftId
      const shiftObj = e.shift_template || e.shift || shiftTemplates.value.find(s => (s.shift_id || s.id) === shiftId)
      const shiftCode = e.shift_code || (shiftObj ? (shiftObj.shift_name || shiftObj.shift || shiftObj.shift_code) : '')
      const shiftColor = e.shift_color || shiftObj?.shift_color || null

      const sDateRaw = e.start || e.start_date || e.StartTime
      const eDateRaw = e.end || e.end_date || e.EndTime
      const sTimeStr = e.shift_start || e.start_time || (shiftObj ? shiftObj.start_time : '08:00')
      const eTimeStr = e.shift_end || e.end_time || (shiftObj ? shiftObj.end_time : '20:00')

      let sDate = toValidDate(sDateRaw)
      let eDate = toValidDate(eDateRaw)

      if (typeof sDateRaw === 'string' && sDateRaw.length === 10) {
        sDate = toValidDate(`${sDateRaw} ${sTimeStr}`)
      }
      if (typeof eDateRaw === 'string' && eDateRaw.length === 10) {
        if (eTimeStr < sTimeStr) {
          const rawD = toValidDate(eDateRaw)
          const nextDay = new Date(rawD.getTime() + 86400000)
          const nextDayStr = nextDay.toISOString().substring(0, 10)
          eDate = toValidDate(`${nextDayStr} ${eTimeStr}`)
        } else {
          eDate = toValidDate(`${eDateRaw} ${eTimeStr}`)
        }
      }

      const rRule = e.RecurrenceRule || e.recurrence_rule || e.rrule_str || null
      const rException = e.RecurrenceException || e.recurrence_exception || null
      const rId = e.RecurrenceID || e.recurrence_id || null
      const isRec = Boolean(rRule || e.is_recurring)
      const seriesStartDate = e.series_start_date || e.SeriesStartDate || e.start_date || null
      const seriesEndDate = e.series_end_date || e.SeriesEndDate || e.end_date || null

      // Carer name and shift code displayed as Subject on card matching Legacy DailyTimeRecord/MaryDtrPlanner Screenshot 1
      const baseSubject = carerName
        ? (shiftCode ? `${carerName}; ${shiftCode}` : carerName)
        : (suName ? `${suName} (${shiftCode})` : (shiftCode || 'Shift'))
      const subject = baseSubject

      return {
        Id: e.id || e.Id,
        id: e.id || e.Id,
        user_shift_id: e.user_shift_id || e.id || e.Id,
        Subject: subject,
        carer_full_name: carerName,
        service_user_name: suName,
        shift_id: shiftId,
        shift_code: shiftCode,
        shift_color: shiftColor,
        shift_start: sTimeStr,
        shift_end: eTimeStr,
        StartTime: sDate || new Date(),
        EndTime: eDate || new Date(),
        IsAllDay: Boolean(e.AllDay || e.isAllDay || e.IsAllDay),
        user_id: e.user_id || e.CarerId,
        CarerId: e.user_id || e.CarerId,
        su_id: e.su_id || e.ServiceUserId,
        ServiceUserId: e.su_id || e.ServiceUserId,
        branch_id: e.branch_id || e.BranchId,
        BranchId: e.branch_id || e.BranchId,
        Status: getNormalizedStatus(e.status || e.Status),
        DoubleUp: Boolean(e.doubleup || e.DoubleUp),
        IsRecurring: isRec,
        // Set RecurrenceRule to null so Syncfusion Scheduler EJ2's internal recurrence engine
        // does not re-expand already-expanded server occurrences into N x N duplicates.
        // Recurrence metadata is preserved via rrule_str, recurrence_rule, and series_end_date for the Edit dialog.
        RecurrenceRule: null,
        RecurrenceException: rException,
        RecurrenceID: rId,
        OccurrenceDate: e.occurrence_date || null,
        rrule_str: rRule,
        recurrence_rule: rRule,
        series_start_date: seriesStartDate,
        SeriesStartDate: seriesStartDate,
        series_end_date: seriesEndDate,
        SeriesEndDate: seriesEndDate
      }
    })
})

const eventSettings = computed(() => ({
  dataSource: syncfusionEvents.value,
  enableTooltip: true,
  tooltipTemplate: 'tooltipTemplate',
  fields: {
    id: 'Id',
    subject: { name: 'Subject', title: 'Carer' },
    location: { name: 'shift_code', title: 'Shift' },
    isAllDay: { name: 'IsAllDay' },
    startTime: { name: 'StartTime' },
    endTime: { name: 'EndTime' },
    recurrenceRule: { name: 'RecurrenceRule' },
    recurrenceException: { name: 'RecurrenceException' },
    recurrenceID: { name: 'RecurrenceID' }
  }
}))

// Get Branch Name for Tooltip & Dropdown Parity (Fallback to 'Location Missing' matching Screenshot 1)
function getBranchName(branchId) {
  if (!branchId || branchId === 0) return 'Location Missing'
  const b = branches.value.find(item => item.branch_id === branchId || item.id === branchId)
  return b ? (b.branch || b.branch_name) : 'Location Missing'
}

// Tooltip DateTime Formatter matching Legacy
function formatTooltipDateTime(dateVal, timeStr) {
  if (!dateVal) return ''
  const d = toValidDate(dateVal)
  if (!d) return ''

  const pad = n => String(n).padStart(2, '0')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const day = pad(d.getDate())
  const month = months[d.getMonth()]
  const year = d.getFullYear()

  let timeFormatted = ''
  if (timeStr && typeof timeStr === 'string' && timeStr.includes(':')) {
    const parts = timeStr.split(':')
    let hours = parseInt(parts[0], 10)
    const minutes = parts[1] || '00'
    const ampm = hours >= 12 ? 'PM' : 'AM'
    hours = hours % 12
    hours = hours ? hours : 12
    timeFormatted = `${pad(hours)}:${minutes} ${ampm}`
  } else {
    let hours = d.getHours()
    const minutes = pad(d.getMinutes())
    const ampm = hours >= 12 ? 'PM' : 'AM'
    hours = hours % 12
    hours = hours ? hours : 12
    timeFormatted = `${pad(hours)}:${minutes} ${ampm}`
  }

  return `${day}-${month}-${year} ${timeFormatted}`
}

// Weekend work cell rendering matching Legacy MaryCarePlanner (#EBFFCD highlight)
function onRenderCell(args) {
  if (args.elementType === 'workCells' && args.date) {
    const day = args.date.getDay()
    if (day === 0 || day === 6) {
      args.element.style.backgroundColor = '#EBFFCD'
    }
  }
}

// Event Rendered Handler for Shift Color Customization matching Legacy Scheduler
function onEventRendered(args) {
  const shiftId = args?.data?.shift_id
  const shiftObj = shiftTemplates.value.find(s => (s.shift_id || s.id) === shiftId)
  const shiftColor = args?.data?.shift_color || shiftObj?.shift_color

  if (shiftColor && args.element) {
    if (args.element.classList.contains('e-agenda-item')) {
      if (args.element.firstChild) {
        args.element.firstChild.style.borderLeftColor = shiftColor
      }
    } else {
      args.element.style.backgroundColor = shiftColor
      args.element.style.borderColor = shiftColor
    }
  }

  // Restore Recurrence Indicator icon for recurring events
  if (args?.data?.IsRecurring || args?.data?.rrule_str) {
    const details = args.element.querySelector('.e-appointment-details') || args.element
    if (details && !details.querySelector('.e-recurrence-icon')) {
      const recIcon = document.createElement('div')
      recIcon.className = 'e-recurrence-icon e-icons'
      recIcon.setAttribute('title', 'Recurring Shift')
      details.insertBefore(recIcon, details.firstChild)
    }
  }

  if (args.data?.EndTime && new Date(args.data.EndTime) < new Date()) {
    args.element.classList.add('e-past-app')
  }
}

// Calculate Visible Date Bounds directly from Syncfusion Scheduler Instance
function getScheduleDateBounds() {
  const schedule = scheduleObj.value?.ej2Instances || scheduleObj.value
  if (schedule && typeof schedule.getCurrentViewDates === 'function') {
    const dates = schedule.getCurrentViewDates()
    if (dates && dates.length > 0) {
      const pad = n => String(n).padStart(2, '0')
      const format = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
      return {
        start: `${format(dates[0])} 00:00:00`,
        end: `${format(dates[dates.length - 1])} 23:59:59`
      }
    }
  }

  // Fallback to month window around current date
  const d = new Date()
  const pad = n => String(n).padStart(2, '0')
  const startOfMonth = new Date(d.getFullYear(), d.getMonth() - 1, 1)
  const endOfMonth = new Date(d.getFullYear(), d.getMonth() + 2, 0)
  return {
    start: `${startOfMonth.getFullYear()}-${pad(startOfMonth.getMonth() + 1)}-${pad(startOfMonth.getDate())} 00:00:00`,
    end: `${endOfMonth.getFullYear()}-${pad(endOfMonth.getMonth() + 1)}-${pad(endOfMonth.getDate())} 23:59:59`
  }
}

// Status Normalization Helpers
function getNormalizedStatus(rawStatus) {
  if (!rawStatus) return 'confirmed'
  const s = String(rawStatus).toLowerCase().replace(/_/g, '-').replace(/\s+/g, '-')
  if (s.includes('confirm')) return 'confirmed'
  if (s.includes('present') || s.includes('in-progress') || s.includes('in_progress')) return 'in-progress'
  if (s.includes('complete') || s.includes('done')) return 'completed'
  if (s.includes('cancel')) return 'cancelled'
  if (s.includes('miss') || s.includes('absence') || s.includes('unresolved')) return 'missed'
  if (s.includes('urgent') || s.includes('priority')) return 'urgent'
  return 'confirmed'
}

function getStatusLabel(rawStatus) {
  const norm = getNormalizedStatus(rawStatus)
  switch (norm) {
    case 'confirmed': return 'Confirmed'
    case 'in-progress': return 'In Progress'
    case 'completed': return 'Completed'
    case 'cancelled': return 'Cancelled'
    case 'missed': return 'Missed Visit'
    case 'urgent': return 'Urgent Visit'
    default: return 'Confirmed'
  }
}

// Load data from backend API with database-driven shifts from mary_api_db_new.m_shifts
async function loadPlannerData() {
  loading.value = true
  try {
    const { start, end } = getScheduleDateBounds()

    const [cData, suData, sData, bData, eData] = await Promise.all([
      carers.value.length ? Promise.resolve(carers.value) : schedulerService.getCarers().catch(() => []),
      serviceUsers.value.length ? Promise.resolve(serviceUsers.value) : schedulerService.getServiceUsers().catch(() => []),
      shiftTemplates.value.length ? Promise.resolve(shiftTemplates.value) : schedulerService.getShiftTemplates().catch(() => []),
      branches.value.length ? Promise.resolve(branches.value) : schedulerService.getBranches().catch(() => []),
      schedulerService.getEvents(start, end, selectedCarer.value, searchQuery.value).catch(() => [])
    ])

    carers.value = cData || []
    serviceUsers.value = suData || []
    shiftTemplates.value = sData || []
    branches.value = bData || []
    events.value = Array.isArray(eData) ? eData : []
  } catch (err) {
    console.error('Failed to load planner data:', err)
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    loadPlannerData()
  }, 350)
}

function toValidDate(val) {
  if (!val) return null
  if (val instanceof Date) return isNaN(val.getTime()) ? null : val
  if (typeof val === 'string') {
    const d = new Date(val.replace(' ', 'T'))
    if (!isNaN(d.getTime())) return d
  }
  return null
}

function toDateString(d) {
  if (!d) return ''
  const dt = toValidDate(d)
  if (!dt) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`
}

function toNaiveDateTimeString(d) {
  if (!d) return ''
  const dt = toValidDate(d)
  if (!dt) return ''
  const pad = n => String(n).padStart(2, '0')
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}

// Cell Double-Click Event Handler matching Legacy MaryCarePlanner
function onCellDoubleClick(args) {
  args.cancel = true
  const date = args.startTime || new Date()
  openNewShiftDialog(date)
}

// Syncfusion Event Handlers
function onSyncfusionEventClick(args) {
  if (args && args.event) {
    const data = args.event
    isEditMode.value = true
    currentEvent.value = data
    currentShiftId.value = data.user_shift_id || data.Id || data.id

    const sDt = toValidDate(data.StartTime)
    const eDt = toValidDate(data.EndTime)
    const pad = n => String(n).padStart(2, '0')

    const sDateStr = sDt ? `${sDt.getFullYear()}-${pad(sDt.getMonth() + 1)}-${pad(sDt.getDate())}` : new Date().toISOString().substring(0, 10)
    const sTimeStr = sDt ? `${pad(sDt.getHours())}:${pad(sDt.getMinutes())}` : '08:00'
    const eTimeStr = eDt ? `${pad(eDt.getHours())}:${pad(eDt.getMinutes())}` : '20:00'

    const rRule = data.rrule_str || data.RecurrenceRule || ''
    const isRecurring = Boolean(data.IsRecurring || rRule)
    const seriesEndDate = data.series_end_date || data.SeriesEndDate || data.end_date

    if (isRecurring && rRule) {
      if (rRule.includes('BYDAY=')) {
        recurrenceMode.value = 'custom'
        const match = rRule.match(/BYDAY=([A-Z,]+)/)
        if (match && match[1]) {
          selectedWeekdays.value = match[1].split(',')
        }
      } else if (rRule.includes('FREQ=DAILY')) {
        recurrenceMode.value = 'daily'
      } else {
        recurrenceMode.value = 'custom'
      }
    } else {
      recurrenceMode.value = 'none'
    }

    const seriesStartDate = data.series_start_date || data.SeriesStartDate || data.start_date
    const calculatedStartDate = isRecurring
      ? (seriesStartDate ? (typeof seriesStartDate === 'string' ? seriesStartDate.substring(0, 10) : toDateString(seriesStartDate)) : sDateStr)
      : sDateStr

    const calculatedEndDate = isRecurring
      ? (seriesEndDate ? (typeof seriesEndDate === 'string' ? seriesEndDate.substring(0, 10) : toDateString(seriesEndDate)) : sDateStr)
      : sDateStr

    form.value = {
      user_id: data.user_id || data.CarerId,
      su_id: data.su_id || data.ServiceUserId,
      shift_id: data.shift_id || (shiftTemplates.value[0] ? (shiftTemplates.value[0].shift_id || shiftTemplates.value[0].id) : null),
      branch_id: data.branch_id || data.BranchId || null,
      start_date: calculatedStartDate,
      end_date: calculatedEndDate,
      start_time: sTimeStr,
      end_time: eTimeStr,
      rrule_str: rRule,
      recurrence_rule: rRule,
      doubleup: data.DoubleUp || false,
      status: data.Status || 'confirmed'
    }
    dialogVisible.value = true
  }
}

// Interactive Drag & Drop / Resize handler
async function onSyncfusionActionBegin(args) {
  if (args.requestType === 'eventChange') {
    const data = args.data
    const realId = data.user_shift_id || data.Id || data.id
    const sDt = toValidDate(data.StartTime)
    const eDt = toValidDate(data.EndTime)
    const pad = n => String(n).padStart(2, '0')

    const updatedPayload = {
      user_id: data.user_id || data.CarerId,
      su_id: data.su_id || data.ServiceUserId,
      shift_id: data.shift_id || null,
      branch_id: data.branch_id || data.BranchId || null,
      start_date: sDt ? `${sDt.getFullYear()}-${pad(sDt.getMonth() + 1)}-${pad(sDt.getDate())}` : new Date().toISOString().substring(0, 10),
      start_time: sDt ? `${pad(sDt.getHours())}:${pad(sDt.getMinutes())}` : '08:00',
      end_time: eDt ? `${pad(eDt.getHours())}:${pad(eDt.getMinutes())}` : '17:00',
      status: data.Status || 'confirmed',
      recurrence_rule: data.RecurrenceRule || null,
      rrule_str: data.RecurrenceRule || null,
      recurrence_exception: data.RecurrenceException || null
    }
    try {
      await schedulerService.updateUserShift(realId, updatedPayload)
      ElMessage.success('Shift reallocated successfully!')
    } catch (err) {
      ElMessage.error('Failed to update shift: ' + (err.response?.data?.detail || err.message))
      await loadPlannerData()
    }
  }
}

async function onSyncfusionActionComplete(args) {
  if (['viewNavigate', 'dateNavigate'].includes(args.requestType)) {
    await nextTick()
    await loadPlannerData()
  }
}

// Recurrence Handlers
function onRecurrenceModeChange(val) {
  if (val === 'none') {
    form.value.rrule_str = ''
    form.value.recurrence_rule = ''
    form.value.end_date = form.value.start_date
  } else {
    // When switching to recurring mode, default end date to +30 days if not set or equal to start date
    if (!form.value.end_date || form.value.end_date === form.value.start_date) {
      const d = toValidDate(form.value.start_date) || new Date()
      d.setDate(d.getDate() + 30)
      const pad = n => String(n).padStart(2, '0')
      form.value.end_date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
    }
    if (val === 'daily') {
      form.value.rrule_str = 'FREQ=DAILY'
      form.value.recurrence_rule = 'FREQ=DAILY'
    } else if (val === 'custom') {
      updateRruleString()
    }
  }
}

function updateRruleString() {
  if (!selectedWeekdays.value.length) {
    form.value.rrule_str = ''
    form.value.recurrence_rule = ''
  } else {
    const rule = `FREQ=WEEKLY;BYDAY=${selectedWeekdays.value.join(',')}`
    form.value.rrule_str = rule
    form.value.recurrence_rule = rule
  }
}

function onShiftTemplateChange(shiftId) {
  if (!shiftId) return
  const tmpl = shiftTemplates.value.find(s => (s.shift_id || s.id) === shiftId)
  if (tmpl) {
    form.value.start_time = tmpl.start_time ? tmpl.start_time.substring(0, 5) : '08:00'
    form.value.end_time = tmpl.end_time ? tmpl.end_time.substring(0, 5) : '20:00'
  }
}

function openNewShiftDialog(targetDate = null) {
  isEditMode.value = false
  currentEvent.value = null
  currentShiftId.value = null
  recurrenceMode.value = 'none'
  selectedWeekdays.value = ['MO', 'TU', 'WE', 'TH', 'FR']

  const activeDate = targetDate ? toDateString(targetDate) : toDateString(new Date())

  form.value = {
    user_id: null,
    su_id: null,
    shift_id: null,
    branch_id: null,
    start_date: activeDate,
    end_date: activeDate,
    start_time: '08:00',
    end_time: '17:00',
    rrule_str: '',
    recurrence_rule: '',
    doubleup: false,
    status: 'confirmed'
  }
  dialogVisible.value = true
}

function promptSaveShift() {
  if (!form.value.user_id || !form.value.start_date || !form.value.su_id) {
    ElMessage.warning('Please select a Service User, Carer Staff, and Start Date')
    return
  }

  if (isEditMode.value && currentEvent.value && (currentEvent.value.IsRecurring || currentEvent.value.RecurrenceRule || currentEvent.value.rrule_str)) {
    recurrencePromptAction.value = 'update'
    recurrenceModeChoice.value = 'all'
    recurrencePromptVisible.value = true
    return
  }
  executeSaveShift('all')
}

function promptDeleteShift() {
  if (!currentShiftId.value) return

  if (currentEvent.value && (currentEvent.value.IsRecurring || currentEvent.value.RecurrenceRule || currentEvent.value.rrule_str)) {
    recurrencePromptAction.value = 'delete'
    recurrenceModeChoice.value = 'all'
    recurrencePromptVisible.value = true
    return
  }

  ElMessageBox.confirm('Are you sure you want to delete this shift assignment?', 'Confirm Deletion', {
    type: 'warning',
    confirmButtonText: 'Delete',
    cancelButtonText: 'Cancel'
  }).then(() => {
    executeDeleteShift('all')
  }).catch(() => {})
}

async function confirmRecurrenceExecution() {
  recurrencePromptVisible.value = false
  if (recurrencePromptAction.value === 'update') {
    await executeSaveShift(recurrenceModeChoice.value)
  } else {
    await executeDeleteShift(recurrenceModeChoice.value)
  }
}

async function executeSaveShift(modeChoice) {
  saving.value = true
  try {
    const realId = currentShiftId.value
    const occurrenceDate = currentEvent.value?.OccurrenceDate || form.value.start_date

    if (isEditMode.value && realId) {
      await schedulerService.updateUserShift(realId, form.value, {
        mode: modeChoice,
        occurrence_date: occurrenceDate
      })
      ElMessage.success('Shift assignment updated successfully')
    } else {
      await schedulerService.saveUserShift(form.value)
      ElMessage.success('New shift assignment created successfully')
    }
    dialogVisible.value = false
    await loadPlannerData()
  } catch (err) {
    ElMessage.error('Error saving shift: ' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}

async function executeDeleteShift(modeChoice) {
  saving.value = true
  try {
    const realId = currentShiftId.value
    const occurrenceDate = currentEvent.value?.OccurrenceDate || form.value.start_date

    await schedulerService.deleteUserShift(realId, {
      mode: modeChoice,
      occurrence_date: occurrenceDate
    })
    ElMessage.success('Shift deleted successfully')
    dialogVisible.value = false
    await loadPlannerData()
  } catch (err) {
    ElMessage.error('Error deleting shift: ' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}

// Bulk Recurrence Deletion Drawer Actions matching Legacy
function openDeleteRecurrenceDrawer() {
  deleteRecurrenceSuId.value = selectedServiceUser.value || null
  deleteRecurrenceRange.value = []
  deleteRecurrenceDrawerVisible.value = true
}

async function confirmDeleteRecurrence() {
  if (!deleteRecurrenceSuId.value) {
    ElMessage.warning('Please select a Service User')
    return
  }
  if (!deleteRecurrenceRange.value || deleteRecurrenceRange.value.length !== 2) {
    ElMessage.warning('Please select a valid date range')
    return
  }

  ElMessageBox.confirm(
    'You are about to delete recurring rota schedules for this client in the selected date range. Proceed?',
    'Confirm Bulk Recurrence Deletion',
    {
      type: 'warning',
      confirmButtonText: 'Yes, Delete',
      cancelButtonText: 'Cancel'
    }
  ).then(async () => {
    deletingRecurrence.value = true
    try {
      const payload = {
        su_id: deleteRecurrenceSuId.value,
        start_date: deleteRecurrenceRange.value[0],
        end_date: deleteRecurrenceRange.value[1]
      }
      const res = await schedulerService.bulkDeleteShifts(payload)
      ElMessage.success(res.message || 'Recurrences successfully deleted')
      deleteRecurrenceDrawerVisible.value = false
      await loadPlannerData()
    } catch (err) {
      ElMessage.error('Failed to delete recurrences: ' + (err.response?.data?.detail || err.message))
    } finally {
      deletingRecurrence.value = false
    }
  }).catch(() => {})
}

// View-Scoped CSV Export with dynamic filename matching Legacy Care Planner
function exportCSV() {
  const scheduleInstance = scheduleObj.value?.ej2Instances || scheduleObj.value
  let visibleEvents = []
  if (scheduleInstance && typeof scheduleInstance.getCurrentViewEvents === 'function') {
    visibleEvents = scheduleInstance.getCurrentViewEvents()
  } else {
    visibleEvents = syncfusionEvents.value
  }

  if (!visibleEvents.length) {
    ElMessage.warning('No shift records visible in current view to export')
    return
  }

  const { start, end } = getScheduleDateBounds()
  const cleanStart = start.split(' ')[0]
  const cleanEnd = end.split(' ')[0]
  let fileName = `CarePlanner_${cleanStart}_to_${cleanEnd}`
  if (searchQuery.value && searchQuery.value.trim()) {
    fileName += `_${searchQuery.value.trim().replace(/[^a-zA-Z0-9]/g, '_')}`
  }

  const headers = ['Service User ID', 'Service User', 'Carer', 'Shift Code', 'Location', 'Start Date & Time', 'End Date & Time', 'Status', 'Double-Up']
  const rows = visibleEvents.map(e => [
    e.su_id || '',
    `"${e.service_user_name || ''}"`,
    `"${e.carer_full_name || ''}"`,
    `"${e.shift_code || ''}"`,
    `"${getBranchName(e.branch_id)}"`,
    `"${e.StartTime instanceof Date ? toNaiveDateTimeString(e.StartTime) : e.StartTime || ''}"`,
    `"${e.EndTime instanceof Date ? toNaiveDateTimeString(e.EndTime) : e.EndTime || ''}"`,
    `"${getStatusLabel(e.Status)}"`,
    `"${e.DoubleUp ? 'Yes' : 'No'}"`
  ])

  const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `${fileName}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('Care Planner CSV exported successfully!')
}

// Native Syncfusion Schedule Printing matching Legacy
function printRota() {
  const scheduleInstance = scheduleObj.value?.ej2Instances || scheduleObj.value
  if (scheduleInstance && typeof scheduleInstance.print === 'function') {
    scheduleInstance.print()
  } else {
    window.print()
  }
}

onMounted(async () => {
  await nextTick()
  await loadPlannerData()
})
</script>

<style scoped>
.care-planner-container {
  padding: 0;
  font-family: var(--el-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
  background-color: var(--el-bg-color-page, #0f172a);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Element Plus Navigation Header Bar */
.el-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background-color: #0f172a;
  border-bottom: 1px solid #1e293b;
  color: #ffffff;
  flex-wrap: wrap;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.search-box {
  margin-left: 6px;
}

.header-search-input {
  width: 240px;
}

/* Syncfusion Recurrence Indicator Icon Parity */
:deep(.e-schedule .e-appointment .e-recurrence-icon) {
  display: inline-block;
  font-size: 13px;
  line-height: inherit;
  margin-right: 4px;
  vertical-align: middle;
}

:deep(.e-schedule .e-appointment .e-recurrence-icon::before) {
  content: '\e308';
  font-family: 'e-icons';
}

/* Isolated Syncfusion Scheduler Container */
.syncfusion-scheduler-container {
  background-color: #ffffff;
  padding: 0;
  margin: 0;
  border-top: 1px solid #e2e8f0;
}

/* Syncfusion Event Tooltip Styling matching Legacy */
.syncfusion-event-tooltip {
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #ffffff;
  max-width: 260px;
  background-color: #1e293b;
  border-radius: 6px;
}

.tooltip-header-title {
  font-weight: 700;
  font-size: 14px;
  border-bottom: 1px solid #334155;
  padding-bottom: 6px;
  margin-bottom: 8px;
  color: #ffffff;
}

.tooltip-detail-row {
  display: flex;
  gap: 6px;
  margin-bottom: 3px;
}

.tooltip-lbl {
  font-weight: 600;
  color: #94a3b8;
  width: 65px;
}

.tooltip-val {
  color: #f8fafc;
  font-weight: 600;
}

.tooltip-date-section {
  margin-top: 6px;
  border-top: 1px dashed #475569;
  padding-top: 6px;
  font-size: 12px;
  color: #cbd5e1;
}

.tooltip-tag-row {
  margin-top: 6px;
}

/* Visual styling for past appointments matching legacy .e-past-app */
:deep(.e-schedule .e-past-app) {
  opacity: 0.72;
  filter: saturate(65%);
  border-left: 4px solid #64748b !important;
}

/* Print Styles */
@media print {
  body * {
    visibility: hidden;
  }
  #printable-rota, #printable-rota * {
    visibility: visible;
  }
  #printable-rota {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
  }
}
</style>
