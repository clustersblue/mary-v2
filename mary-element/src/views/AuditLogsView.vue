<template>
  <div class="audit-logs-view">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <div>
            <h2 class="text-xl font-bold text-gray-800 m-0">Audit Trail</h2>
            <p class="text-sm text-gray-500 m-0 mt-1">
              Shows dossier reads, document views, care-note views, note and medication changes, and access-request exports recorded by this version. Each new event stores the signed-in person. Older rows may have no staff identity. This log is not immutable and does not store clinical text.
            </p>
          </div>
          <div class="actions flex gap-2">
            <el-button type="primary" plain @click="scheduleFetch(true)" :loading="loading">
              <el-icon class="mr-1"><Refresh /></el-icon> Refresh Logs
            </el-button>
            <el-button type="warning" plain @click="exportCsv" :disabled="!total" :loading="exporting">
              <el-icon class="mr-1"><Download /></el-icon> Export CSV
            </el-button>
          </div>
        </div>
      </template>

      <div class="audit-summary">
        <span class="audit-stat">Total audited events <strong>{{ summary.total }}</strong></span>
        <span class="audit-stat">Events with a staff identity <strong>{{ summary.identified }}</strong></span>
        <span class="audit-stat">Medical dossier access <strong>{{ summary.dossier }}</strong></span>
        <span class="audit-stat">Other recorded events <strong>{{ summary.other }}</strong></span>
      </div>

      <!-- FILTER BAR -->
      <div class="flex flex-wrap gap-3 items-center mb-4">
        <el-input
          v-model="searchQuery"
          placeholder="Filter by Patient, Staff or Action..."
          clearable
          style="width: 320px;"
          prefix-icon="Search"
        />

        <el-select v-model="filterRecordType" placeholder="Record Category" clearable style="width: 200px;">
          <el-option label="All Categories" value="" />
          <el-option label="Medical dossier" value="medical_dossier" />
          <el-option label="Medication record" value="mar_chart" />
          <el-option label="Care notes" value="care_notes" />
          <el-option label="Documents" value="documents" />
          <el-option label="Access-request preview" value="sar_preview" />
          <el-option label="Access-request export" value="sar_export" />
        </el-select>
      </div>

      <!-- AUDIT TABLE -->
      <el-table
        :data="filteredLogs"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        empty-text="No audit events recorded."
      >
        <el-table-column prop="id" label="Audit ID" width="90" />
        <el-table-column prop="created_at" label="Timestamp" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="Staff / User" width="160" />
        <el-table-column prop="patient_name" label="Service User (Patient)" width="180">
          <template #default="{ row }">
            <strong>{{ subjectLabel(row) }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="record_type" label="Data Classification" width="160">
          <template #default="{ row }">
            <el-tag :type="getRecordTypeTag(row.record_type)" effect="light">
              {{ row.record_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="Action" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="details" label="Audit Event Details" min-width="220" />
        <el-table-column prop="ip_address" label="Client IP" width="130" />
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[25, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="scheduleFetch"
          @size-change="scheduleFetch"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Search } from '@element-plus/icons-vue'
import api from '@/service/api'

const logs = ref([])
const loading = ref(false)
const exporting = ref(false)
const searchQuery = ref('')
const filterRecordType = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)
const summary = ref({ total: 0, identified: 0, dossier: 0, other: 0 })
let searchTimer = null
let fetchQueued = false
let fetchNotify = false

function scheduleFetch(notify = false) {
  if (notify === true) fetchNotify = true
  if (fetchQueued) return
  fetchQueued = true
  Promise.resolve().then(() => {
    const notifyNow = fetchNotify
    fetchQueued = false
    fetchNotify = false
    fetchLogs(notifyNow)
  })
}

const filteredLogs = logs

function getRecordTypeTag(type) {
  if (type === 'medical_dossier') return 'danger'
  if (type === 'mar_chart') return 'warning'
  return 'primary'
}

function subjectLabel(row) {
  const name = (row.patient_name || '').trim()
  if (name && name !== 'Unknown Patient') return name
  if (row.su_id) return `Service user #${row.su_id}`
  return '—'
}

function formatDateTime(val) {
  if (!val) return '—'
  const d = new Date(val)
  return isNaN(d) ? val : d.toLocaleString('en-GB', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

function listParams(page, size) {
  return {
    page,
    page_size: size,
    record_type: filterRecordType.value || undefined,
    q: searchQuery.value.trim() || undefined,
  }
}

async function fetchLogs(notify = false) {
  loading.value = true
  try {
    const res = await api.get('/audit/logs', { params: listParams(currentPage.value, pageSize.value) })
    const body = res.data || {}
    logs.value = body.data || []
    total.value = body.total || 0
    if (body.summary) summary.value = body.summary
    if (body.page && body.page !== currentPage.value) currentPage.value = body.page
    if (notify === true) ElMessage.success(`Audit trail refreshed. ${total.value} matching events.`)
  } catch (err) {
    ElMessage.error('Failed to load audit logs: ' + (err.message || 'Server error'))
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  if (!total.value || exporting.value) return
  exporting.value = true
  try {
    const collected = []
    let page = 1
    let matching = 0
    do {
      const res = await api.get('/audit/logs', { params: listParams(page, 100) })
      const batch = res.data?.data || []
      matching = res.data?.total || 0
      collected.push(...batch)
      page += 1
      if (!batch.length) break
    } while (collected.length < matching && collected.length < 5000)
    const headers = ['Audit ID', 'Timestamp', 'Staff', 'Patient', 'Classification', 'Action', 'Details', 'IP Address']
    const rows = collected.map(l => [
      l.id,
      `"${l.created_at || ''}"`,
      `"${(l.username || '').replace(/"/g, '""')}"`,
      `"${subjectLabel(l).replace(/"/g, '""')}"`,
      `"${l.record_type || ''}"`,
      `"${l.action || ''}"`,
      `"${(l.details || '').replace(/"/g, '""')}"`,
      `"${l.ip_address || ''}"`
    ])
    const csv = [headers.join(','), ...rows.map(cells => cells.join(','))].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_trail_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    if (matching > collected.length) {
      ElMessage.warning(`Exported the first ${collected.length} of ${matching} matching events.`)
    }
  } catch (err) {
    ElMessage.error('Failed to export the audit trail: ' + (err.message || 'Server error'))
  } finally {
    exporting.value = false
  }
}

watch(filterRecordType, () => {
  currentPage.value = 1
  scheduleFetch()
})

watch(searchQuery, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    scheduleFetch()
  }, 300)
})

onMounted(() => {
  scheduleFetch()
})
</script>

<style scoped>
.audit-logs-view {
  padding: 16px;
}
.audit-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px 18px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}
.audit-stat {
  font-size: 13px;
  line-height: 1.4;
  color: #4b5563;
  white-space: nowrap;
}
.audit-stat strong {
  margin-left: 6px;
  font-size: 15px;
  color: #111827;
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
