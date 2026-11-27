<template>
  <div class="settings-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-box">
            <el-icon><User /></el-icon>
            <span>Service Users (Clients) Management</span>
          </div>
          <div class="actions">
            <el-button type="success" icon="MagicStick" @click="generateAICarePlan">
              AI Care Plan Generator
            </el-button>
            <el-button type="primary" icon="Plus" @click="openDialog">Add Service User</el-button>
          </div>
        </div>
      </template>

      <el-table :data="serviceUsers" style="width: 100%" stripe border>
        <el-table-column prop="name" label="Client Name" width="180" />
        <el-table-column prop="nhs_number" label="NHS Number" width="140" />
        <el-table-column prop="address" label="Address" min-width="200" />
        <el-table-column prop="care_type" label="Care Type" width="140" />
        <el-table-column prop="status" label="Status" width="120">
          <template #default="scope">
            <el-tag type="success">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="viewCarePlan(scope.row)">Care Plan</el-button>
            <el-button size="small" type="danger" icon="Delete" @click="deleteSU(scope.row)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- AI Care Plan Generator Dialog -->
    <el-dialog v-model="aiDialogVisible" title="AI Care Plan Generator (FastAPI / Claude / Gemini)" width="600px">
      <el-form label-position="top">
        <el-form-item label="Service User Clinical Assessment Notes">
          <el-input v-model="aiPrompt" type="textarea" :rows="4" placeholder="Enter clinical assessment, mobility status, dietary requirements, and medical history..." />
        </el-form-item>
      </el-form>
      <div v-if="aiGeneratedResult" class="ai-result mt-20">
        <h4>Generated AI Person-Centred Care Plan:</h4>
        <el-input v-model="aiGeneratedResult" type="textarea" :rows="6" readonly />
      </div>
      <template #footer>
        <el-button @click="aiDialogVisible = false">Close</el-button>
        <el-button type="success" :loading="generating" icon="MagicStick" @click="runAIGenerator">
          Generate Care Plan
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const aiDialogVisible = ref(false)
const aiPrompt = ref('')
const aiGeneratedResult = ref('')
const generating = ref(false)

const serviceUsers = ref([
  { su_id: 1, name: 'Arthur Pendelton', nhs_number: '943 821 0041', address: '42 Maple Street, London NW1 4EP', care_type: 'Personal Care', status: 'Active' },
  { su_id: 2, name: 'Eleanor Vance', nhs_number: '812 554 9912', address: '18 Victoria Road, London SE10 8AB', care_type: 'Complex Care', status: 'Active' }
])

function generateAICarePlan() {
  aiPrompt.value = ''
  aiGeneratedResult.value = ''
  aiDialogVisible.value = true
}

function runAIGenerator() {
  if (!aiPrompt.value) {
    ElMessage.warning('Please enter clinical notes for AI Care Plan generation')
    return
  }
  generating.value = true
  setTimeout(() => {
    generating.value = false
    aiGeneratedResult.value = `### PERSON-CENTRED CARE PLAN
1. Morning Rota: Assistance with personal hygiene and mobility transfer using hoist.
2. Nutrition & Hydration: Soft diet, encourage 1.5L daily fluids.
3. Medication: Administer morning blister pack.
4. Risk Assessment: High fall risk in bathroom area.`
    ElMessage.success('AI Care Plan generated successfully!')
  }, 1200)
}

function openDialog() {
  ElMessage.info('Opening new Service User registration form')
}

function viewCarePlan(row) {
  ElMessage.info(`Opening Care Plan for ${row.name}`)
}

function deleteSU(row) {
  ElMessageBox.confirm(`Delete Service User record for ${row.name}?`, 'Warning', { type: 'warning' })
    .then(() => {
      serviceUsers.value = serviceUsers.value.filter(s => s.su_id !== row.su_id)
      ElMessage.success('Service User removed')
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
.actions {
  display: flex;
  gap: 10px;
}
.mt-20 {
  margin-top: 20px;
}
</style>
