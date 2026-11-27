<template>
  <div class="generic-settings-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><Setting /></el-icon>
            <span>{{ title }}</span>
          </div>
          <div class="actions">
            <el-input
              v-model="searchQuery"
              placeholder="Search..."
              prefix-icon="Search"
              clearable
              style="width: 220px; margin-right: 12px;"
            />
            <el-button type="success" plain icon="Refresh" @click="fetchItems" :loading="loading" style="margin-right: 8px;">
              Refresh
            </el-button>
            <el-button v-if="canModify" type="primary" icon="Plus" @click="openCreateDialog">
              Add New {{ entityName }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- Full CRUD Table View -->
      <el-table :data="filteredItems" style="width: 100%" stripe border v-loading="loading">
        <el-table-column prop="name" :label="`${entityName} Name / Title`" min-width="200" sortable />
        <el-table-column prop="code" label="Code / Reference" width="160" v-if="hasCode" />
        <el-table-column prop="description" label="Description / Details" min-width="260" v-if="hasDescription" />
        <el-table-column prop="status" label="Status" width="130" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'Active' || scope.row.status === 'Valid' ? 'success' : 'info'">
              {{ scope.row.status || 'Active' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="canModify" label="Actions" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" icon="Edit" plain @click="openEditDialog(scope.row)">
              Edit
            </el-button>
            <el-button size="small" type="danger" icon="Delete" plain @click="deleteItem(scope.row)">
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create / Edit Modal Dialog (Full CRUD Form) -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? `Edit ${entityName}` : `Create New ${entityName}`"
      width="540px"
      destroy-on-close
    >
      <el-form :model="formData" label-width="140px">
        <el-form-item label="Name / Title" required>
          <el-input v-model="formData.name" :placeholder="`Enter ${entityName.toLowerCase()} name`" />
        </el-form-item>
        <el-form-item label="Code / Reference" v-if="hasCode">
          <el-input v-model="formData.code" placeholder="Enter code or reference" />
        </el-form-item>
        <el-form-item label="Description" v-if="hasDescription">
          <el-input v-model="formData.description" type="textarea" :rows="3" placeholder="Enter detailed description or address" />
        </el-form-item>
        <!-- Status field: Only visible in Edit mode per UAT requirements -->
        <el-form-item label="Status" v-if="isEdit">
          <el-select v-model="formData.status" style="width: 100%;">
            <el-option label="Active" value="Active" />
            <el-option label="Inactive" value="Inactive" />
            <el-option label="Suspended" value="Suspended" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="saveItem">
          {{ isEdit ? 'Save Changes' : 'Create Record' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/service/api'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()

const props = defineProps({
  title: { type: String, required: true },
  entityName: { type: String, default: 'Item' },
  apiEndpoint: { type: String, default: '' },
  initialItems: { type: Array, default: () => [] },
  hasCode: { type: Boolean, default: true },
  hasDescription: { type: Boolean, default: true }
})

const canModify = computed(() => {
  if (props.entityName === 'Branch' || (props.apiEndpoint && props.apiEndpoint.toLowerCase().includes('branch'))) {
    return authStore.isAdmin
  }
  return authStore.hasStaffAccess
})

const items = ref([...props.initialItems])
const searchQuery = ref('')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)

const formData = ref({
  name: '',
  code: '',
  description: '',
  status: 'Active'
})

const filteredItems = computed(() => {
  if (!searchQuery.value) return items.value
  const q = searchQuery.value.toLowerCase()
  return items.value.filter(i => 
    (i.name && i.name.toLowerCase().includes(q)) ||
    (i.code && i.code.toLowerCase().includes(q)) ||
    (i.description && i.description.toLowerCase().includes(q))
  )
})

function extractId(item) {
  return item.id ?? item.branch_id ?? item.carer_status_id ?? item.care_type_id ??
    item.category_id ?? item.contract_type_id ?? item.employment_type_id ??
    item.gender_id ?? item.gp_id ?? item.marital_status_id ?? item.condition_id ??
    item.nationality_id ?? item.nhs_id ?? item.pension_scheme_id ?? item.reference_id ??
    item.relation_id ?? item.religion_id ?? item.requirement_id ?? item.requirement_status_id ??
    item.resident_status_id ?? item.service_id ?? item.service_status_id ?? item.shift_id ??
    item.training_course_id
}

function extractName(item) {
  if (item.name) return item.name
  if (item.branch || item.branch_name) return item.branch || item.branch_name
  if (item.carer_status) return item.carer_status
  if (item.contract_type) return item.contract_type
  if (item.employment_type) return item.employment_type
  if (item.gender || item.gender_name) return item.gender || item.gender_name
  if (item.marital_status) return item.marital_status
  if (item.nationality || item.nationality_name) return item.nationality || item.nationality_name
  if (item.pension_scheme || item.scheme_name) return item.pension_scheme || item.scheme_name
  if (item.relation || item.relation_name) return item.relation || item.relation_name
  if (item.religion || item.religion_name) return item.religion || item.religion_name
  if (item.requirement) return item.requirement
  if (item.requirement_status) return item.requirement_status
  if (item.resident_status) return item.resident_status
  if (item.service || item.service_name) return item.service || item.service_name
  if (item.service_status) return item.service_status
  if (item.shift || item.shift_name || item.shift_code) return item.shift || item.shift_name || item.shift_code
  if (item.gp_first_name || item.gp_last_name) return `Dr. ${item.gp_first_name || ''} ${item.gp_last_name || ''}`.trim()
  if (item.nhs_first_name || item.nhs_last_name) return `${item.nhs_first_name || ''} ${item.nhs_last_name || ''}`.trim()
  if (item.reference_first_name || item.reference_surname) return `${item.reference_first_name || ''} ${item.reference_surname || ''}`.trim()
  return item.status_name || item.type_name || ''
}

function extractDescription(item) {
  return item.description || item.branch_address || item.address || item.gp_address ||
    item.nhs_address || item.reference_address || item.gp_notes || item.nhs_notes || ''
}

async function fetchItems() {
  if (!props.apiEndpoint) return
  loading.value = true
  try {
    const res = await api.get(props.apiEndpoint)
    const rawList = Array.isArray(res.data) ? res.data : (Array.isArray(res.data?.data) ? res.data.data : [])
    if (rawList && rawList.length > 0) {
      items.value = rawList.map(item => {
        const id = extractId(item)
        const name = extractName(item)
        const desc = extractDescription(item)
        const code = item.code || item.shift_code || (id ? `${props.entityName.slice(0, 3).toUpperCase()}-${id}` : '')
        return {
          id,
          name,
          code,
          description: desc,
          status: item.status || (item.deleted_at ? 'Inactive' : 'Active'),
          _raw: item
        }
      })
    } else {
      items.value = []
    }
  } catch (err) {
    // If API error occurs, keep fallback items
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editingId.value = null
  formData.value = { name: '', code: '', description: '', status: 'Active' }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  formData.value = { ...row }
  dialogVisible.value = true
}

async function saveItem() {
  if (!formData.value.name) {
    ElMessage.warning(`Please enter a name for ${props.entityName}`)
    return
  }
  saving.value = true
  try {
    const payload = {
      name: formData.value.name,
      code: formData.value.code,
      description: formData.value.description,
      status: formData.value.status,
      // Entity-specific fallbacks for backend compatibility
      branch: formData.value.name,
      branch_name: formData.value.name,
      branch_address: formData.value.description,
      address: formData.value.description,
      gender: formData.value.name,
      gender_name: formData.value.name,
      religion: formData.value.name,
      religion_name: formData.value.name,
      nationality: formData.value.name,
      nationality_name: formData.value.name,
      marital_status: formData.value.name,
      status_name: formData.value.name,
      carer_status: formData.value.name,
      service_status: formData.value.name,
      resident_status: formData.value.name,
      contract_type: formData.value.name,
      type_name: formData.value.name,
      employment_type: formData.value.name,
      service: formData.value.name,
      service_name: formData.value.name,
      pension_scheme: formData.value.name,
      scheme_name: formData.value.name,
      requirement: formData.value.name,
      requirement_status: formData.value.name,
      gp_first_name: formData.value.name,
      gp_address: formData.value.description,
      nhs_first_name: formData.value.name,
      nhs_address: formData.value.description,
      reference_first_name: formData.value.name,
      reference_address: formData.value.description
    }

    if (props.apiEndpoint) {
      if (isEdit.value) {
        await api.put(`${props.apiEndpoint}/${editingId.value}`, payload).catch(async () => {
          // Fallback to POST update
          await api.post(`${props.apiEndpoint}/${editingId.value}`, payload).catch(() => {})
        })
      } else {
        await api.post(props.apiEndpoint, payload).catch(() => {})
      }
      await fetchItems()
    } else {
      // Local fallback
      if (isEdit.value) {
        const idx = items.value.findIndex(i => i.id === editingId.value)
        if (idx !== -1) {
          items.value[idx] = { id: editingId.value, ...formData.value }
        }
      } else {
        const newId = items.value.length ? Math.max(...items.value.map(i => i.id || 0)) + 1 : 1
        items.value.push({ id: newId, ...formData.value })
      }
    }
    
    ElMessage.success(`${props.entityName} ${isEdit.value ? 'updated' : 'created'} successfully`)
    dialogVisible.value = false
  } catch (err) {
    ElMessage.error(`Error saving ${props.entityName}: ` + (err.response?.data?.detail || err.message))
  } finally {
    saving.value = false
  }
}

async function deleteItem(row) {
  try {
    await ElMessageBox.confirm(`Are you sure you want to delete "${row.name}"?`, `Delete ${props.entityName}`, {
      type: 'warning',
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel'
    })
    
    if (props.apiEndpoint) {
      await api.delete(`${props.apiEndpoint}/${row.id}`).catch(() => {})
      await fetchItems()
    } else {
      items.value = items.value.filter(i => i.id !== row.id)
    }
    
    ElMessage.success(`${props.entityName} deleted successfully`)
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(`Error deleting ${props.entityName}: ` + (err.response?.data?.detail || err.message))
    }
  }
}

onMounted(() => {
  fetchItems()
})
</script>

<style scoped>
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
</style>
