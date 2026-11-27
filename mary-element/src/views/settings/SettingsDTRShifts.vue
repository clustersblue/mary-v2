<template>
  <div class="dtr-shifts-settings-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><Clock /></el-icon>
            <span>DTR Work Shifts</span>
          </div>
          <div class="actions">
            <el-input
              v-model="searchQuery"
              placeholder="Search shift code..."
              prefix-icon="Search"
              clearable
              style="width: 220px; margin-right: 12px;"
            />
            <el-button type="primary" icon="Plus" @click="openCreateDialog">
              Add DTR Shift
            </el-button>
          </div>
        </div>
      </template>

      <!-- Full CRUD Table View (Internal Database ID Removed) -->
      <el-table :data="filteredShifts" style="width: 100%" stripe border v-loading="loading">
        <el-table-column prop="shift_code" label="Shift Code" min-width="140" sortable>
          <template #default="scope">
            <div class="shift-code-cell">
              <span
                class="color-indicator"
                :style="{ backgroundColor: scope.row.shift_color || '#3b82f6' }"
              ></span>
              <span class="code-text">{{ scope.row.shift_code }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="shift_color" label="Color" width="110" align="center">
          <template #default="scope">
            <div class="color-badge" :style="{ backgroundColor: scope.row.shift_color || '#3b82f6' }">
              {{ scope.row.shift_color || '#3b82f6' }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Working Hours" width="160" align="center">
          <template #default="scope">
            <span class="time-range">{{ scope.row.start_time }} - {{ scope.row.end_time }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="crosses_midnight" label="Crosses Midnight" width="150" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.crosses_midnight ? 'warning' : 'info'" size="small">
              {{ scope.row.crosses_midnight ? 'Yes (Overnight)' : 'No' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Break Window" width="150" align="center">
          <template #default="scope">
            <span v-if="scope.row.break_start && scope.row.break_end">
              {{ scope.row.break_start }} - {{ scope.row.break_end }}
            </span>
            <span v-else class="text-muted">None</span>
          </template>
        </el-table-column>

        <el-table-column prop="grace_period" label="Grace Period" width="130" align="center">
          <template #default="scope">
            <span>{{ scope.row.grace_period || 0 }} mins</span>
          </template>
        </el-table-column>

        <el-table-column label="Night Differential" width="160" align="center">
          <template #default="scope">
            <span v-if="scope.row.night_diff_from && scope.row.night_diff_to">
              {{ scope.row.night_diff_from }} - {{ scope.row.night_diff_to }}
            </span>
            <span v-else class="text-muted">None</span>
          </template>
        </el-table-column>

        <el-table-column label="Attributes" width="170" align="center">
          <template #default="scope">
            <div class="attributes-tags">
              <el-tag v-if="scope.row.is_flexible" size="small" type="success" effect="plain">Flexible</el-tag>
              <el-tag v-if="scope.row.is_rotating" size="small" type="primary" effect="plain">Rotating</el-tag>
              <span v-if="!scope.row.is_flexible && !scope.row.is_rotating" class="text-muted">Standard</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" icon="Edit" plain @click="openEditDialog(scope.row)">
              Edit
            </el-button>
            <el-button size="small" type="danger" icon="Delete" plain @click="deleteShift(scope.row)">
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create / Edit Dialog for DTR Shifts -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? `Edit DTR Shift: ${editingShiftCode}` : 'Create New DTR Shift'"
      width="600px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="160px"
        class="dtr-shift-form"
      >
        <el-form-item label="Shift Code" prop="shift_code">
          <el-input v-model="formData.shift_code" placeholder="e.g. MORNING, NIGHT, D12" />
        </el-form-item>

        <el-form-item label="Shift Color" prop="shift_color">
          <div class="color-picker-row">
            <el-color-picker v-model="formData.shift_color" show-alpha />
            <el-input v-model="formData.shift_color" placeholder="#3b82f6" style="width: 140px; margin-left: 10px;" />
          </div>
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Start Time" prop="start_time">
              <el-time-picker
                v-model="formData.start_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="Start time"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="End Time" prop="end_time">
              <el-time-picker
                v-model="formData.end_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="End time"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Crosses Midnight">
          <el-switch v-model="formData.crosses_midnight" active-text="Overnight Shift" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Break Start">
              <el-time-picker
                v-model="formData.break_start"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="Break start"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Break End">
              <el-time-picker
                v-model="formData.break_end"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="Break end"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Grace Period (mins)">
          <el-input-number v-model="formData.grace_period" :min="0" :max="120" :step="5" />
        </el-form-item>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Night Diff From">
              <el-time-picker
                v-model="formData.night_diff_from"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="22:00"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Night Diff To">
              <el-time-picker
                v-model="formData.night_diff_to"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="06:00"
                style="width: 100%;"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="Flexible Schedule">
              <el-switch v-model="formData.is_flexible" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Rotating Shift">
              <el-switch v-model="formData.is_rotating" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="saveShift">
          {{ isEdit ? 'Save Changes' : 'Create DTR Shift' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Clock, Plus, Search, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/service/api'

const shifts = ref([])
const searchQuery = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const editingShiftCode = ref('')
const formRef = ref(null)

const formData = ref({
  shift_code: '',
  shift_color: '#3b82f6',
  start_time: '08:00',
  end_time: '17:00',
  crosses_midnight: false,
  break_start: null,
  break_end: null,
  grace_period: 0,
  night_diff_from: null,
  night_diff_to: null,
  is_flexible: false,
  is_rotating: false
})

const formRules = {
  shift_code: [{ required: true, message: 'Shift code is required', trigger: 'blur' }],
  start_time: [{ required: true, message: 'Start time is required', trigger: 'change' }],
  end_time: [{ required: true, message: 'End time is required', trigger: 'change' }]
}

const filteredShifts = computed(() => {
  if (!searchQuery.value) return shifts.value
  const q = searchQuery.value.toLowerCase()
  return shifts.value.filter(s =>
    s.shift_code && s.shift_code.toLowerCase().includes(q)
  )
})

async function fetchShifts() {
  loading.value = true
  try {
    const res = await api.get('/dtr-shifts')
    const rawData = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.data) ? res.data.data : [])
    shifts.value = rawData
  } catch (err) {
    ElMessage.error('Failed to load DTR shifts from mary_api_db_new.dtr_shifts: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  editingShiftCode.value = ''
  formData.value = {
    shift_code: '',
    shift_color: '#3b82f6',
    start_time: '08:00',
    end_time: '17:00',
    crosses_midnight: false,
    break_start: null,
    break_end: null,
    grace_period: 0,
    night_diff_from: null,
    night_diff_to: null,
    is_flexible: false,
    is_rotating: false
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  editingShiftCode.value = row.shift_code
  formData.value = {
    shift_code: row.shift_code,
    shift_color: row.shift_color || '#3b82f6',
    start_time: row.start_time,
    end_time: row.end_time,
    crosses_midnight: Boolean(row.crosses_midnight),
    break_start: row.break_start || null,
    break_end: row.break_end || null,
    grace_period: row.grace_period || 0,
    night_diff_from: row.night_diff_from || null,
    night_diff_to: row.night_diff_to || null,
    is_flexible: Boolean(row.is_flexible),
    is_rotating: Boolean(row.is_rotating)
  }
  dialogVisible.value = true
}

async function saveShift() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const payload = {
      shift_code: formData.value.shift_code,
      shift_color: formData.value.shift_color,
      start_time: formData.value.start_time,
      end_time: formData.value.end_time,
      crosses_midnight: formData.value.crosses_midnight,
      break_start: formData.value.break_start || null,
      break_end: formData.value.break_end || null,
      grace_period: formData.value.grace_period || 0,
      night_diff_from: formData.value.night_diff_from || null,
      night_diff_to: formData.value.night_diff_to || null,
      is_flexible: formData.value.is_flexible,
      is_rotating: formData.value.is_rotating
    }

    if (isEdit.value && editingId.value) {
      await api.put(`/dtr-shifts/${editingId.value}`, payload)
      ElMessage.success('DTR shift updated successfully in mary_api_db_new.dtr_shifts')
    } else {
      await api.post('/dtr-shifts', payload)
      ElMessage.success('New DTR shift created successfully in mary_api_db_new.dtr_shifts')
    }
    dialogVisible.value = false
    await fetchShifts()
  } catch (err) {
    ElMessage.error('Failed to save DTR shift: ' + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}

function deleteShift(row) {
  ElMessageBox.confirm(
    `Are you sure you want to delete DTR Shift "${row.shift_code}"?`,
    'Confirm Deletion',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await api.delete(`/dtr-shifts/${row.id}`)
      ElMessage.success(`DTR Shift "${row.shift_code}" deleted successfully`)
      await fetchShifts()
    } catch (err) {
      ElMessage.error('Failed to delete shift: ' + (err.response?.data?.detail || err.message))
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchShifts()
})
</script>

<style scoped>
.dtr-shifts-settings-container {
  padding: 16px;
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
  font-weight: 600;
  font-size: 16px;
}
.actions {
  display: flex;
  align-items: center;
}
.shift-code-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.color-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}
.code-text {
  font-weight: 600;
}
.color-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  color: #ffffff;
  font-size: 11px;
  font-family: monospace;
}
.time-range {
  font-weight: 500;
}
.text-muted {
  color: #94a3b8;
  font-size: 12px;
}
.attributes-tags {
  display: flex;
  gap: 4px;
  justify-content: center;
}
.color-picker-row {
  display: flex;
  align-items: center;
}
</style>
