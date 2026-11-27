<template>
  <div class="settings-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><UserFilled /></el-icon>
            <span>Carers (Staff) Master Registry</span>
          </div>
          <el-button type="primary" icon="Plus" @click="openDialog">Add Carer Staff</el-button>
        </div>
      </template>

      <el-table :data="carers" style="width: 100%" stripe border>
        <el-table-column prop="name" label="Carer Full Name" width="200" />
        <el-table-column prop="email" label="Email Address" width="220" />
        <el-table-column prop="phone" label="Phone Number" width="160" />
        <el-table-column prop="employmentType" label="Employment Type" width="160" />
        <el-table-column prop="dbsStatus" label="DBS Clearance" width="140">
          <template #default="scope">
            <el-tag :type="scope.row.dbsStatus === 'Valid' ? 'success' : 'danger'">
              {{ scope.row.dbsStatus }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="Status" width="120">
          <template #default="scope">
            <el-tag type="success">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" icon="Edit" @click="editCarer(scope.row)" />
            <el-button size="small" type="danger" icon="Delete" @click="deleteCarer(scope.row)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const carers = ref([
  { id: 1, name: 'Sarah Jenkins', email: 'sarah.jenkins@marycare.co.uk', phone: '07700 900123', employmentType: 'Full-Time', dbsStatus: 'Valid', status: 'Active' },
  { id: 2, name: 'David Smith', email: 'david.smith@marycare.co.uk', phone: '07700 900456', employmentType: 'Part-Time', dbsStatus: 'Valid', status: 'Active' },
  { id: 3, name: 'Maria Garcia', email: 'maria.garcia@marycare.co.uk', phone: '07700 900789', employmentType: 'Zero-Hours', dbsStatus: 'Valid', status: 'Active' }
])

function openDialog() {
  ElMessage.info('Opening Carer Registration form')
}

function editCarer(row) {
  ElMessage.info(`Editing record for ${row.name}`)
}

function deleteCarer(row) {
  ElMessageBox.confirm(`Delete Carer profile for ${row.name}?`, 'Warning', { type: 'warning' })
    .then(() => {
      carers.value = carers.value.filter(c => c.id !== row.id)
      ElMessage.success('Carer profile removed')
    }).catch(() => {})
}
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
</style>
