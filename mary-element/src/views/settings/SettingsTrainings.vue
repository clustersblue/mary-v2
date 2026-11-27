<template>
  <div class="settings-trainings-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon class="header-icon"><Reading /></el-icon>
            <div>
              <h2 class="page-title">Mandatory Care Training Courses</h2>
              <span class="subtitle">Compliance training modules, duration, and certificate validity requirements</span>
            </div>
          </div>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="Search training courses..."
              prefix-icon="Search"
              clearable
              style="width: 240px; margin-right: 12px;"
            />
            <el-button type="success" plain icon="Refresh" :loading="loading" @click="fetchCourses">
              Refresh
            </el-button>
            <el-button type="primary" icon="Plus" @click="openCreateDialog">
              Add Training Course
            </el-button>
          </div>
        </div>
      </template>

      <!-- Training Courses Data Grid -->
      <el-table
        :data="filteredCourses"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        class="trainings-table"
      >
        <el-table-column prop="name" label="Training Course" min-width="220" sortable>
          <template #default="scope">
            <div class="course-name-cell">
              <el-icon class="course-icon"><DocumentChecked /></el-icon>
              <strong>{{ scope.row.name }}</strong>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="Description" min-width="260" show-overflow-tooltip />

        <el-table-column prop="duration_hours" label="Duration (Hours)" width="160" align="center" sortable>
          <template #default="scope">
            <el-tag type="info" effect="plain" class="duration-tag">
              <el-icon style="margin-right: 4px;"><Timer /></el-icon>
              {{ scope.row.duration_hours ? `${scope.row.duration_hours} hrs` : 'N/A' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="validity_months" label="Validity (Months)" width="170" align="center" sortable>
          <template #default="scope">
            <el-tag :type="getValidityTagType(scope.row.validity_months)" effect="light">
              <el-icon style="margin-right: 4px;"><Calendar /></el-icon>
              {{ scope.row.validity_months ? `${scope.row.validity_months} months` : 'No Expiry' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="Status" width="120" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'Active' ? 'success' : 'info'">
              {{ scope.row.status || 'Active' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Actions" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" icon="Edit" plain @click="openEditDialog(scope.row)">
              Edit
            </el-button>
            <el-button size="small" type="danger" icon="Delete" plain @click="deleteCourse(scope.row)">
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? 'Edit Training Course' : 'Create New Training Course'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="150px">
        <el-form-item label="Course Name" prop="name" required>
          <el-input v-model="formData.name" placeholder="e.g. Safeguarding Vulnerable Adults" />
        </el-form-item>

        <el-form-item label="Description" prop="description" required>
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="Detailed overview of syllabus and certification requirements"
          />
        </el-form-item>

        <el-form-item label="Duration (Hours)" prop="duration_hours" required>
          <el-input-number
            v-model="formData.duration_hours"
            :min="0.5"
            :max="100"
            :step="0.5"
            controls-position="right"
            style="width: 180px;"
          />
          <span style="margin-left: 8px; color: #909399;">hours</span>
        </el-form-item>

        <el-form-item label="Validity (Months)" prop="validity_months" required>
          <el-input-number
            v-model="formData.validity_months"
            :min="1"
            :max="120"
            :step="1"
            controls-position="right"
            style="width: 180px;"
          />
          <span style="margin-left: 8px; color: #909399;">months (12 = Annual, 36 = 3 Years)</span>
        </el-form-item>

        <!-- Status field: Only visible in Edit mode per UAT requirements -->
        <el-form-item label="Status" v-if="isEdit">
          <el-select v-model="formData.status" style="width: 100%;">
            <el-option label="Active" value="Active" />
            <el-option label="Inactive" value="Inactive" />
            <el-option label="Archived" value="Archived" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="saveCourse">
          {{ isEdit ? 'Save Changes' : 'Create Course' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/service/api'

const loading = ref(false)
const saving = ref(false)
const courses = ref([])
const searchQuery = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const formData = ref({
  name: '',
  description: '',
  duration_hours: 4,
  validity_months: 12,
  status: 'Active'
})

const formRules = {
  name: [{ required: true, message: 'Please enter training course name', trigger: 'blur' }],
  description: [{ required: true, message: 'Please enter course description', trigger: 'blur' }],
  duration_hours: [{ required: true, message: 'Please specify course duration in hours', trigger: 'change' }],
  validity_months: [{ required: true, message: 'Please specify certificate validity in months', trigger: 'change' }]
}

async function fetchCourses() {
  loading.value = true
  try {
    const res = await api.get('/trainings')
    const rawList = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.data) ? res.data.data : [])
    courses.value = rawList.map(item => ({
      id: item.training_course_id || item.id,
      training_course_id: item.training_course_id || item.id,
      name: item.name || '',
      description: item.description || '',
      duration_hours: item.duration_hours || '4',
      validity_months: Number(item.validity_months || 12),
      status: item.status || 'Active'
    }))
  } catch (err) {
    ElMessage.error('Failed to load training courses: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

const filteredCourses = computed(() => {
  if (!searchQuery.value) return courses.value
  const q = searchQuery.value.toLowerCase()
  return courses.value.filter(c =>
    (c.name && c.name.toLowerCase().includes(q)) ||
    (c.description && c.description.toLowerCase().includes(q)) ||
    String(c.duration_hours).includes(q) ||
    String(c.validity_months).includes(q)
  )
})

function getValidityTagType(months) {
  if (!months) return 'info'
  if (months <= 12) return 'warning'
  if (months <= 24) return 'primary'
  return 'success'
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  formData.value = {
    name: '',
    description: '',
    duration_hours: 4,
    validity_months: 12,
    status: 'Active'
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = {
    name: row.name,
    description: row.description,
    duration_hours: parseFloat(row.duration_hours) || 4,
    validity_months: parseInt(row.validity_months) || 12,
    status: row.status || 'Active'
  }
  dialogVisible.value = true
}

async function saveCourse() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = {
        name: formData.value.name,
        description: formData.value.description,
        duration_hours: String(formData.value.duration_hours),
        validity_months: parseInt(formData.value.validity_months)
      }

      if (isEdit.value) {
        await api.put(`/trainings/${editingId.value}`, payload)
        ElMessage.success('Training course updated successfully')
      } else {
        await api.post('/trainings', payload)
        ElMessage.success('Training course created successfully')
      }
      dialogVisible.value = false
      await fetchCourses()
    } catch (err) {
      ElMessage.error('Failed to save training course: ' + (err.response?.data?.detail || err.message))
    } finally {
      saving.value = false
    }
  })
}

async function deleteCourse(row) {
  try {
    await ElMessageBox.confirm(`Are you sure you want to delete "${row.name}"?`, 'Confirm Delete', {
      type: 'warning',
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel'
    })
    await api.delete(`/trainings/${row.id}`)
    ElMessage.success(`Training course "${row.name}" deleted`)
    await fetchCourses()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('Failed to delete course: ' + (err.response?.data?.detail || err.message))
    }
  }
}

onMounted(() => {
  fetchCourses()
})
</script>

<style scoped>
.settings-trainings-container {
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
  align-items: center;
}
.course-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.course-icon {
  color: #409eff;
  font-size: 16px;
}
.duration-tag {
  font-weight: 500;
}
</style>
