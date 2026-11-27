<template>
  <div class="settings-rates-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon class="header-icon"><Money /></el-icon>
            <div>
              <h2 class="page-title">Service Users Rates Master Matrix</h2>
              <span class="subtitle">Cross-reference matrix of Service Users, Shifts, Carer Pay Rates & Client Invoicing</span>
            </div>
          </div>
          <div class="header-actions">
            <el-button type="success" plain icon="Refresh" :loading="loading" @click="loadRates">
              Refresh
            </el-button>
            <el-button type="primary" plain icon="Download" @click="exportCSV">
              Export CSV
            </el-button>
          </div>
        </div>
      </template>

      <!-- Filter and Stats Bar -->
      <div class="table-toolbar">
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="Search service user, shift, or rate..."
            prefix-icon="Search"
            clearable
            style="width: 320px;"
          />
        </div>
        <div class="stats-badge">
          <el-tag type="info" size="large" effect="plain">
            Total Rate Entries: <strong>{{ filteredRates.length }}</strong>
          </el-tag>
        </div>
      </div>

      <!-- Main Rates Matrix Table -->
      <el-table
        :data="filteredRates"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        class="rates-table"
      >
        <el-table-column prop="su_full_name" label="Service User" min-width="200" sortable>
          <template #default="scope">
            <div class="user-cell">
              <el-avatar :size="28" class="user-avatar">
                {{ scope.row.su_full_name ? scope.row.su_full_name.charAt(0) : 'U' }}
              </el-avatar>
              <span class="user-name">{{ scope.row.su_full_name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="shift" label="Shift Type" min-width="180" sortable>
          <template #default="scope">
            <el-tag :type="getShiftTagType(scope.row.shift)" effect="light">
              {{ scope.row.shift }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Carer Rate (£/hr)" width="220" align="center">
          <template #default="scope">
            <div class="rate-input-cell">
              <el-input-number
                v-model="scope.row.rate"
                :min="0"
                :precision="2"
                :step="0.5"
                size="default"
                controls-position="right"
                style="width: 140px;"
                :disabled="!authStore.isAdmin"
                @change="markDirty(scope.row)"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Service User Invoice (£/hr)" width="230" align="center">
          <template #default="scope">
            <div class="rate-input-cell">
              <el-input-number
                v-model="scope.row.invoice"
                :min="0"
                :precision="2"
                :step="0.5"
                size="default"
                controls-position="right"
                style="width: 140px;"
                :disabled="!authStore.isAdmin"
                @change="markDirty(scope.row)"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column v-if="authStore.isAdmin" label="Actions" width="130" align="center" fixed="right">
          <template #default="scope">
            <el-button
              size="small"
              :type="scope.row._dirty ? 'primary' : 'default'"
              :plain="!scope.row._dirty"
              :loading="scope.row._saving"
              icon="Check"
              @click="saveRow(scope.row)"
            >
              {{ scope.row._dirty ? 'Save' : 'Saved' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()

const loading = ref(false)
const rates = ref([])
const searchQuery = ref('')

async function loadRates() {
  loading.value = true
  try {
    const res = await api.get('/getsurates')
    const rawList = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.data) ? res.data.data : [])
    rates.value = rawList.map(item => ({
      ...item,
      rate: Number(item.rate || 0),
      invoice: Number(item.invoice || 0),
      _dirty: false,
      _saving: false
    }))
    ElMessage.success('Rates matrix loaded successfully!')
  } catch (err) {
    ElMessage.error('Failed to load rates: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

const filteredRates = computed(() => {
  if (!searchQuery.value) return rates.value
  const q = searchQuery.value.toLowerCase()
  return rates.value.filter(item => {
    const suName = (item.su_full_name || '').toLowerCase()
    const shift = (item.shift || '').toLowerCase()
    const rateStr = String(item.rate || '')
    const invStr = String(item.invoice || '')
    return suName.includes(q) || shift.includes(q) || rateStr.includes(q) || invStr.includes(q)
  })
})

function markDirty(row) {
  row._dirty = true
}

async function saveRow(row) {
  row._saving = true
  try {
    if (row.id == null) {
      // Create new rate record
      const res = await api.post('/savesurate', {
        su_id: row.su_id,
        shift_id: row.shift_id,
        rate: row.rate,
        invoice: row.invoice
      })
      if (res.data?.data?.id) {
        row.id = res.data.data.id
      }
      ElMessage.success(`Rates saved for ${row.su_full_name} (${row.shift})`)
    } else {
      // Update existing rate record
      await api.post(`/updatesurate/${row.id}`, {
        id: row.id,
        su_id: row.su_id,
        shift_id: row.shift_id,
        rate: row.rate,
        invoice: row.invoice
      })
      ElMessage.success(`Rates updated for ${row.su_full_name} (${row.shift})`)
    }
    row._dirty = false
  } catch (err) {
    ElMessage.error('Failed to save rate: ' + (err.response?.data?.detail || err.message))
  } finally {
    row._saving = false
  }
}

function getShiftTagType(shift) {
  if (!shift) return 'info'
  const s = shift.toLowerCase()
  if (s.includes('morning')) return 'success'
  if (s.includes('noon') || s.includes('afternoon')) return 'warning'
  if (s.includes('night') || s.includes('sleep')) return 'danger'
  if (s.includes('live')) return ''
  return 'info'
}

function exportCSV() {
  if (!filteredRates.value.length) {
    ElMessage.warning('No rates data to export')
    return
  }
  const headers = ['Service User', 'Shift', 'Carer Rate (£)', 'Invoice (£)']
  const rows = filteredRates.value.map(r => [
    `"${r.su_full_name || ''}"`,
    `"${r.shift || ''}"`,
    Number(r.rate || 0).toFixed(2),
    Number(r.invoice || 0).toFixed(2)
  ])
  const csvContent = [headers.join(','), ...rows.map(e => e.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', `Service_Users_Rates_${new Date().toISOString().slice(0, 10)}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  ElMessage.success('Rates CSV exported')
}

onMounted(() => {
  loadRates()
})
</script>

<style scoped>
.settings-rates-container {
  padding: 8px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-icon {
  font-size: 26px;
  color: #409eff;
}
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.subtitle {
  font-size: 13px;
  color: #909399;
}
.header-actions {
  display: flex;
  gap: 10px;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-avatar {
  background-color: #409eff;
  color: #fff;
  font-weight: 600;
  font-size: 12px;
}
.user-name {
  font-weight: 500;
  color: #303133;
}
.rate-input-cell {
  display: flex;
  justify-content: center;
}
</style>
