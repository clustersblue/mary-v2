<template>
  <div class="payments-view">
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
          <div class="header-title">
            <h2 class="text-xl font-bold text-gray-800 m-0">Payments & Billing Management</h2>
            <p class="text-sm text-gray-500 m-0 mt-1">
              Preview unbilled shift records and generate batch Payroll for staff or Invoices for service users.
            </p>
          </div>
          <el-tag type="info" effect="plain" class="text-sm">
            UK Care Financial Processing
          </el-tag>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange" type="border-card">
        <!-- TAB 0: GENERATE PAYROLL -->
        <el-tab-pane label="Generate Payroll" name="payroll">
          <div class="tab-description p-3 bg-blue-50 text-blue-900 rounded mb-4 text-sm">
            <i class="el-icon-info mr-1"></i>
            This section enables administrators to generate payroll batches for selected Carers within a specified date range.
            Choose a Carer and the date window, search for completed shifts, verify the hours and rates, and generate the payroll batch.
          </div>

          <div class="filter-bar flex flex-wrap gap-3 items-center mb-4">
            <el-select
              v-model="selectedEntityId"
              filterable
              clearable
              placeholder="Select a Carer"
              style="width: 260px;"
            >
              <el-option
                v-for="carer in carerList"
                :key="carer.id"
                :label="getCarerLabel(carer)"
                :value="carer.id"
              />
            </el-select>

            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="to"
              start-placeholder="Start Date"
              end-placeholder="End Date"
              format="DD/MM/YYYY"
              value-format="YYYY-MM-DD"
              :unlink-panels="false"
              single-panel
              style="width: 280px;"
              class="box-item"
            />

            <el-tooltip
              class="box-item"
              effect="dark"
              content="Search Shifts"
              placement="bottom"
            >
              <el-button type="primary" :disabled="!selectedEntityId || !dateRange" @click="fetchTransactions(0)" :loading="loading">
                <el-icon class="mr-1"><Search /></el-icon>
              </el-button>
            </el-tooltip>

            <el-tooltip
              class="box-item"
              effect="dark"
              content="Refresh"
              placement="bottom"
            >
              <el-button @click="clearSearch" :disabled="loading && !transactions.length">
                <el-icon class="mr-1"><Refresh /></el-icon>
              </el-button>
            </el-tooltip>

            <el-divider direction="vertical" />

            <el-button
              type="success"
              :disabled="!transactions.length || generating"
              @click="confirmGenerate(0)"
              :loading="generating"
            >
              <el-icon class="mr-1"><Check /></el-icon> Generate Payroll Batch
            </el-button>
          </div>
        </el-tab-pane>

        <!-- TAB 1: GENERATE INVOICE -->
        <el-tab-pane label="Generate Invoice" name="invoice">
          <div class="tab-description p-3 bg-indigo-50 text-indigo-900 rounded mb-4 text-sm">
            <i class="el-icon-info mr-1"></i>
            This section enables administrators to generate invoices for selected Service Users within a specified billing range.
            Select a Service User, choose the date range, inspect billable shifts and invoice rates, and generate the batch invoice.
          </div>

          <div class="filter-bar flex flex-wrap gap-3 items-center mb-4">
            <el-select
              v-model="selectedEntityId"
              filterable
              clearable
              placeholder="Select a Service User"
              style="width: 260px;"
            >
              <el-option
                v-for="su in serviceUserList"
                :key="su.su_id"
                :label="getServiceUserLabel(su)"
                :value="su.su_id"
              />
            </el-select>

            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="to"
              start-placeholder="Start Date"
              end-placeholder="End Date"
              format="DD/MM/YYYY"
              value-format="YYYY-MM-DD"
              :unlink-panels="false"
              single-panel
              style="width: 280px;"
            />

            <el-tooltip
              class="box-item"
              effect="dark"
              content="Search Shifts"
              placement="bottom"
            >
              <el-button type="primary" :disabled="!selectedEntityId || !dateRange" @click="fetchTransactions(1)" :loading="loading">
                <el-icon class="mr-1"><Search /></el-icon>
              </el-button>
            </el-tooltip>

            <el-tooltip
              class="box-item"
              effect="dark"
              content="Refresh"
              placement="bottom"
            >
              <el-button @click="clearSearch" :disabled="loading && !transactions.length">
                <el-icon class="mr-1"><Refresh /></el-icon>
              </el-button>
            </el-tooltip>

            <el-divider direction="vertical" />

            <el-button
              type="success"
              :disabled="!transactions.length || generating"
              @click="confirmGenerate(1)"
              :loading="generating"
            >
              <el-icon class="mr-1"><Check /></el-icon> Generate Invoice Batch
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- KPI Summary Cards -->
      <div v-if="transactions.length" class="kpi-banner grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
        <el-card shadow="hover" class="stat-card">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Eligible Shifts</div>
          <div class="text-2xl font-bold text-gray-900 mt-1">{{ transactions.length }}</div>
        </el-card>

        <el-card shadow="hover" class="stat-card">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Total Billed Hours</div>
          <div class="text-2xl font-bold text-blue-600 mt-1">{{ totalHours.toFixed(2) }} hrs</div>
        </el-card>

        <el-card shadow="hover" class="stat-card">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            {{ activeTab === 'payroll' ? 'Total Payroll Cost' : 'Total Invoice Value' }}
          </div>
          <div class="text-2xl font-bold text-green-600 mt-1">£{{ totalAmount.toFixed(2) }}</div>
        </el-card>

        <el-card shadow="hover" class="stat-card">
          <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Date Range</div>
          <div class="text-sm font-semibold text-gray-700 mt-2">
            {{ dateRange ? `${dateRange[0]} to ${dateRange[1]}` : 'All Dates' }}
          </div>
        </el-card>
      </div>

      <!-- TRANSACTIONS TABLE SECTION -->
      <div class="mt-4">
        <!-- Table Toolbar: Legacy Title, Search Filter & Export -->
        <div class="flex flex-col sm:flex-row justify-between items-center mb-3 gap-3">
          <h3 class="text-base font-semibold text-gray-800 m-0">Invoice and Payroll</h3>
          <div class="flex items-center gap-3 w-full sm:w-auto justify-end">
            <el-input
              v-model="searchQuery"
              placeholder="Search..."
              prefix-icon="Search"
              clearable
              style="width: 240px;"
              @input="currentPage = 1"
            />
            <el-button
              type="warning"
              plain
              :disabled="!filteredTransactions.length"
              @click="exportCsv"
            >
              <el-icon class="mr-1"><Download /></el-icon> Export CSV
            </el-button>
          </div>
        </div>

        <el-table
          :data="paginatedTransactions"
          v-loading="loading"
          stripe
          border
          style="width: 100%"
          empty-text="No unbilled shifts found for the selected criteria."
        >
          <!-- 1. Carer (Legacy Column 1) -->
          <el-table-column
            prop="carer_full_name"
            label="Carer"
            min-width="150"
            sortable
          />

          <!-- 2. Service User (Legacy Column 2) -->
          <el-table-column
            label="Service User"
            min-width="160"
            sortable
            :sort-by="(row) => row.su_full_name || row.service_user || ''"
          >
            <template #default="{ row }">
              {{ row.su_full_name || row.service_user || '—' }}
            </template>
          </el-table-column>

          <!-- 3. Rate (Legacy Column 3) -->
          <el-table-column
            label="Rate"
            width="110"
            align="right"
            sortable
            :sort-by="(row) => activeTab === 'payroll' ? (Number(row.rate) || 0) : (Number(row.invoice) || Number(row.invoice_rate) || Number(row.rate) || 0)"
          >
            <template #default="{ row }">
              {{ formatCurrency(activeTab === 'payroll' ? row.rate : (row.invoice || row.invoice_rate || row.rate || 0)) }}
            </template>
          </el-table-column>

          <!-- 4. Date (Legacy Column 4) -->
          <el-table-column
            prop="start"
            label="Date"
            min-width="175"
            sortable
            :sort-by="(row) => new Date(row.start).getTime()"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.start) }}
            </template>
          </el-table-column>

          <!-- 5. Shift (Legacy Column 5) -->
          <el-table-column
            prop="shift"
            label="Shift"
            min-width="130"
            sortable
          />

          <!-- 6. Time IN (Legacy Column 6) -->
          <el-table-column
            prop="time_in"
            label="Time IN"
            width="110"
            sortable
          >
            <template #default="{ row }">
              {{ formatTime(row.time_in) }}
            </template>
          </el-table-column>

          <!-- 7. Time OUT (Legacy Column 7) -->
          <el-table-column
            prop="time_out"
            label="Time OUT"
            width="110"
            sortable
          >
            <template #default="{ row }">
              {{ formatTime(row.time_out) }}
            </template>
          </el-table-column>

          <!-- 8. Total Time (Legacy Column 8: Sum/Duration of Time IN & OUT) -->
          <el-table-column
            label="Total Time"
            width="120"
            sortable
            :sort-by="(row) => getTotalMinutes(row.time_in, row.time_out) || getTotalMinutes(row.start, row.end)"
          >
            <template #default="{ row }">
              {{ formatTotalTime(row) }}
            </template>
          </el-table-column>

          <!-- Supplementary Columns (Preserved from new functionality) -->
          <!-- 9. Hours -->
          <el-table-column
            label="Hours"
            width="100"
            align="right"
            sortable
            :sort-by="(row) => getRowHours(row)"
          >
            <template #default="{ row }">
              {{ getRowHours(row).toFixed(2) }}
            </template>
          </el-table-column>

          <!-- 10. Total (£) -->
          <el-table-column
            label="Total (£)"
            width="120"
            align="right"
            sortable
            :sort-by="(row) => getRowHours(row) * (activeTab === 'payroll' ? (Number(row.rate) || 0) : (Number(row.invoice) || Number(row.invoice_rate) || Number(row.rate) || 0))"
          >
            <template #default="{ row }">
              <strong class="text-green-700">
                {{ formatCurrency(getRowHours(row) * (activeTab === 'payroll' ? (Number(row.rate) || 0) : (Number(row.invoice) || Number(row.invoice_rate) || Number(row.rate) || 0))) }}
              </strong>
            </template>
          </el-table-column>

          <!-- 11. Tx ID -->
          <el-table-column
            prop="tx_id"
            label="Tx ID"
            width="85"
            sortable
          />
        </el-table>

        <!-- PAGINATION (Matching Legacy Paginator) -->
        <div class="flex flex-col sm:flex-row justify-between items-center mt-4 gap-3">
          <div class="text-sm text-gray-500">
            Showing {{ filteredTransactions.length === 0 ? 0 : (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, filteredTransactions.length) }} of {{ filteredTransactions.length }} schedules
          </div>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 25, 50, 100]"
            layout="sizes, prev, pager, next, jumper"
            :total="filteredTransactions.length"
            small
          />
        </div>
      </div>
    </el-card>

    <!-- CONFIRM GENERATION DIALOG -->
    <el-dialog
      v-model="showConfirmDialog"
      :title="activeTab === 'payroll' ? 'Confirm Payroll Generation' : 'Confirm Invoice Generation'"
      width="480px"
    >
      <div class="py-2">
        <p class="text-base text-gray-800">
          Are you sure you want to generate
          <strong>{{ activeTab === 'payroll' ? 'Payroll' : 'Client Invoices' }}</strong>
          for <strong>{{ transactions.length }}</strong> shift records?
        </p>
        <div class="bg-gray-50 p-3 rounded mt-3 text-sm space-y-1">
          <div><strong>Billing Range:</strong> {{ dateRange ? `${dateRange[0]} to ${dateRange[1]}` : 'N/A' }}</div>
          <div><strong>Total Hours:</strong> {{ totalHours.toFixed(2) }} hrs</div>
          <div><strong>Total Value:</strong> £{{ totalAmount.toFixed(2) }}</div>
        </div>
        <p class="text-xs text-amber-600 mt-3">
          * This will batch the selected transactions and make them available in the
          {{ activeTab === 'payroll' ? 'Payroll Management' : 'Invoice Management' }} view.
        </p>
      </div>
      <template #footer>
        <el-button @click="showConfirmDialog = false">Cancel</el-button>
        <el-button type="success" :loading="generating" @click="executeGenerate">
          Confirm & Generate
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Check, Download } from '@element-plus/icons-vue'
import FinanceService from '@/service/FinanceService'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()

const activeTab = ref('payroll')
const selectedEntityId = ref(null)
const dateRange = ref(['2026-10-01', '2026-10-31'])
const transactions = ref([])
const carerList = ref([])
const serviceUserList = ref([])
const loading = ref(false)
const generating = ref(false)
const showConfirmDialog = ref(false)

// Search & Pagination state (Parity with Legacy DataTable)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(50)

// Global filter matching legacy globalFilterFields: ['su_full_name', 'carer_full_name', 'rate', 'start', 'shift', 'time_in', 'time_out']
const filteredTransactions = computed(() => {
  if (!searchQuery.value) return transactions.value
  const q = searchQuery.value.toLowerCase().trim()
  return transactions.value.filter(row => {
    const carer = String(row.carer_full_name || '').toLowerCase()
    const su = String(row.su_full_name || row.service_user || '').toLowerCase()
    const rate = String(row.rate || '')
    const start = String(row.start || '').toLowerCase()
    const shift = String(row.shift || '').toLowerCase()
    const timeIn = String(row.time_in || '').toLowerCase()
    const timeOut = String(row.time_out || '').toLowerCase()
    const totalTime = String(row.total_time || '').toLowerCase()
    const txId = String(row.tx_id || '')
    return carer.includes(q) ||
      su.includes(q) ||
      rate.includes(q) ||
      start.includes(q) ||
      shift.includes(q) ||
      timeIn.includes(q) ||
      timeOut.includes(q) ||
      totalTime.includes(q) ||
      txId.includes(q)
  })
})

const paginatedTransactions = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredTransactions.value.slice(start, start + pageSize.value)
})

const totalHours = computed(() => {
  return filteredTransactions.value.reduce((acc, curr) => acc + getRowHours(curr), 0)
})

const totalAmount = computed(() => {
  return filteredTransactions.value.reduce((acc, curr) => {
    const rate = activeTab.value === 'payroll' ? (Number(curr.rate) || 0) : (Number(curr.invoice) || Number(curr.invoice_rate) || Number(curr.rate) || 0)
    return acc + (getRowHours(curr) * rate)
  }, 0)
})

function handleTabChange() {
  selectedEntityId.value = null
  transactions.value = []
  searchQuery.value = ''
  currentPage.value = 1
}

function clearSearch() {
  selectedEntityId.value = null
  transactions.value = []
  searchQuery.value = ''
  currentPage.value = 1
}

// Label helpers for dropdown selectors (safeguarding against missing/undefined properties)
function getCarerLabel(carer) {
  if (!carer) return ''
  if (carer.full_name) return carer.full_name
  if (carer.carer_full_name) return carer.carer_full_name
  const name = `${carer.first_name || ''} ${carer.surname || ''}`.trim()
  return name || `Carer #${carer.id}`
}

function getServiceUserLabel(su) {
  if (!su) return ''
  if (su.su_full_name) return su.su_full_name
  if (su.full_name) return su.full_name
  const name1 = `${su.first_name || ''} ${su.surname || ''}`.trim()
  if (name1) return name1
  const name2 = `${su.su_first_name || ''} ${su.su_last_name || ''}`.trim()
  if (name2) return name2
  return `Service User #${su.su_id}`
}

// Duration calculation helpers: Difference/Sum of worked duration between Time IN and Time OUT
function getTotalMinutes(timeIn, timeOut) {
  if (!timeIn || !timeOut) return 0

  // 1. If ISO date-time strings
  if (String(timeIn).includes('-') && String(timeOut).includes('-')) {
    const dIn = new Date(timeIn).getTime()
    const dOut = new Date(timeOut).getTime()
    if (!isNaN(dIn) && !isNaN(dOut)) {
      let diffMs = dOut - dIn
      if (diffMs < 0) {
        diffMs += 24 * 60 * 60 * 1000 // handle crossing midnight
      }
      return Math.round(diffMs / 60000)
    }
  }

  // 2. Parse time strings (e.g. "08:00", "08:00:00", "2026-07-01T08:00:00")
  const parseMins = (t) => {
    if (!t) return 0
    let str = String(t)
    if (str.includes('T')) str = str.split('T')[1]
    else if (str.includes(' ')) str = str.split(' ')[1]
    const parts = str.split(':').map(Number)
    return (parts[0] || 0) * 60 + (parts[1] || 0)
  }

  const startMins = parseMins(timeIn)
  let endMins = parseMins(timeOut)

  if (endMins < startMins) {
    endMins += 24 * 60 // overnight shift
  }

  return endMins - startMins
}

function formatTotalTime(row) {
  let totalMins = 0
  if (row.time_in && row.time_out) {
    totalMins = getTotalMinutes(row.time_in, row.time_out)
  } else if (row.start && row.end) {
    totalMins = getTotalMinutes(row.start, row.end)
  } else if (row.hours) {
    totalMins = Math.round(Number(row.hours) * 60)
  }

  if (totalMins > 0) {
    const h = String(Math.floor(totalMins / 60)).padStart(2, '0')
    const m = String(totalMins % 60).padStart(2, '0')
    return `${h}:${m}`
  }

  if (row.total_time && row.total_time !== '00:00' && row.total_time !== '—') {
    return row.total_time
  }

  return '00:00'
}

function getRowHours(row) {
  let totalMins = 0
  if (row.time_in && row.time_out) {
    totalMins = getTotalMinutes(row.time_in, row.time_out)
  } else if (row.start && row.end) {
    totalMins = getTotalMinutes(row.start, row.end)
  }
  if (totalMins > 0) {
    return totalMins / 60
  }
  const h = Number(row.hours)
  return (!isNaN(h) && h > 0) ? h : 0
}

// Formatting helpers preserving legacy rules
function formatCurrency(val) {
  const num = Number(val) || 0
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(num)
}

function formatDateTime(val) {
  if (!val) return '—'
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  const hours = String(d.getHours()).padStart(2, '0')
  const mins = String(d.getMinutes()).padStart(2, '0')
  const secs = String(d.getSeconds()).padStart(2, '0')
  return `${day}/${month}/${year} ${hours}:${mins}:${secs}`
}

function formatTime(val) {
  if (!val) return '—'
  if (typeof val === 'string') {
    if (val.includes('T')) {
      const timePart = val.split('T')[1]
      return timePart ? timePart.slice(0, 5) : val
    }
    if (val.length >= 5) {
      return val.slice(0, 5)
    }
  }
  const d = new Date(val)
  if (!isNaN(d.getTime())) {
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  }
  return String(val)
}

async function loadDropdowns() {
  try {
    const [carersRes, suRes] = await Promise.all([
      FinanceService.getCarers(),
      FinanceService.getServiceUsers()
    ])
    carerList.value = Array.isArray(carersRes) ? carersRes : (carersRes.data || [])
    serviceUserList.value = Array.isArray(suRes) ? suRes : (suRes.data || [])
  } catch (err) {
    ElMessage.error('Failed to load carer and service user directory: ' + (err.message || 'Network error'))
  }
}

async function fetchTransactions(param) {
  if (!selectedEntityId.value || !dateRange.value) {
    ElMessage.warning('Please select an entity and date range first.')
    return
  }

  loading.value = true
  try {
    const res = await FinanceService.getTransactions({
      param: param,
      selectionList: selectedEntityId.value,
      dates: dateRange.value
    })
    transactions.value = res.data || []
    currentPage.value = 1
    if (transactions.value.length === 0) {
      ElMessage.info('No unbilled transactions found for the specified period.')
    } else {
      ElMessage.success(`Found ${transactions.value.length} unbilled shift records.`)
    }
  } catch (err) {
    ElMessage.error('Error fetching transactions: ' + (err.message || 'Server error'))
  } finally {
    loading.value = false
  }
}

function confirmGenerate(param) {
  if (!transactions.value.length) {
    ElMessage.warning('No transactions available to generate.')
    return
  }
  showConfirmDialog.value = true
}

async function executeGenerate() {
  showConfirmDialog.value = false
  generating.value = true

  const currentUser = authStore.user || {}
  const param = activeTab.value === 'payroll' ? 0 : 1
  const dateRangeStr = dateRange.value ? `${dateRange.value[0]} - ${dateRange.value[1]}` : ''

  const payloadData = transactions.value.map(t => {
    const hours = getRowHours(t)
    const rateVal = activeTab.value === 'payroll' ? Number(t.rate || 0) : (Number(t.invoice) || Number(t.invoice_rate) || Number(t.rate) || 0)
    return {
      ...t,
      hours: hours.toFixed(2),
      total_time: formatTotalTime(t),
      amount: Number((hours * rateVal).toFixed(2))
    }
  })

  const payload = {
    param: param,
    user_id: currentUser.id || 1,
    date_range: dateRangeStr,
    data: payloadData
  }

  try {
    const res = await FinanceService.generatePayments(payload)
    if (res.message) {
      ElMessage.success(typeof res.data === 'string' ? res.data : 'Batch generated successfully!')
      transactions.value = []
      selectedEntityId.value = null
      searchQuery.value = ''
      currentPage.value = 1
    } else {
      ElMessage.error(res.data || 'Failed to generate batch.')
    }
  } catch (err) {
    ElMessage.error('Generation error: ' + (err.response?.data?.detail || err.message || 'Server error'))
  } finally {
    generating.value = false
  }
}

function exportCsv() {
  const dataToExport = filteredTransactions.value.length ? filteredTransactions.value : transactions.value
  if (!dataToExport.length) return

  const headers = ['Carer', 'Service User', 'Rate', 'Date', 'Shift', 'Time IN', 'Time OUT', 'Total Time', 'Hours', 'Total (£)', 'Tx ID']
  const rows = dataToExport.map(t => {
    const rateVal = activeTab.value === 'payroll' ? Number(t.rate || 0) : (Number(t.invoice) || Number(t.invoice_rate) || Number(t.rate) || 0)
    const hours = getRowHours(t)
    const total = (hours * rateVal).toFixed(2)
    return [
      `"${t.carer_full_name || ''}"`,
      `"${t.su_full_name || t.service_user || ''}"`,
      rateVal.toFixed(2),
      `"${formatDateTime(t.start)}"`,
      `"${t.shift || ''}"`,
      `"${formatTime(t.time_in)}"`,
      `"${formatTime(t.time_out)}"`,
      `"${formatTotalTime(t)}"`,
      hours.toFixed(2),
      total,
      t.tx_id
    ]
  })

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `${activeTab.value}_preview_${new Date().toISOString().slice(0, 10)}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onMounted(() => {
  loadDropdowns()
})
</script>

<style scoped>
.payments-view {
  padding: 0;
}
.stat-card {
  border-left: 4px solid #409eff;
}
.kpi-banner {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
</style>
