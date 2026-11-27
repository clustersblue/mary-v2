<template>
  <div class="access-denied-wrapper">
    <div class="access-denied-container">
      <el-card class="access-denied-card" shadow="always">
        <div class="branding-header">
          <div class="lock-circle">
            <el-icon class="lock-icon"><Lock /></el-icon>
          </div>
          <h1 class="denied-title">Access Denied</h1>
          <p class="denied-code">HTTP 403 Forbidden</p>
          <p class="denied-subtitle">
            You do not have the required permissions to access this page or resource.
          </p>
        </div>

        <el-alert
          type="warning"
          :closable="false"
          show-icon
          class="denied-alert"
        >
          <template #title>
            <strong>Role Authorization Notice</strong>
          </template>
          If you believe this is an error or require access to this administrative feature, please contact your System Administrator.
        </el-alert>

        <div class="action-buttons">
          <el-button
            type="primary"
            size="large"
            icon="Back"
            @click="goToPortal"
          >
            {{ portalButtonLabel }}
          </el-button>
          <el-button
            size="large"
            icon="SwitchButton"
            @click="handleLogout"
          >
            Switch Account
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import { Lock, Back, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const portalButtonLabel = computed(() => {
  if (authStore.isAdmin) return 'Go to Admin Dashboard'
  if (authStore.hasStaffAccess) return 'Go to Staff Planner'
  if (authStore.isCarer) return 'Go to Carer Portal'
  return 'Go to Login'
})

const goToPortal = () => {
  if (authStore.isAdmin) {
    router.push('/')
  } else if (authStore.hasStaffAccess) {
    router.push('/planner')
  } else if (authStore.isCarer) {
    router.push('/attendance')
  } else {
    router.push('/login')
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.access-denied-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
  padding: 24px;
}

.access-denied-container {
  width: 100%;
  max-width: 520px;
}

.access-denied-card {
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.02);
  padding: 24px 16px;
  text-align: center;
}

.branding-header {
  margin-bottom: 24px;
}

.lock-circle {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  background: rgba(245, 108, 108, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.lock-icon {
  font-size: 38px;
  color: #f56c6c;
}

.denied-title {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 6px 0;
}

.denied-code {
  font-size: 14px;
  font-weight: 600;
  color: #e6a23c;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0 0 12px 0;
}

.denied-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.denied-alert {
  margin-bottom: 28px;
  text-align: left;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}

@media (max-width: 480px) {
  .action-buttons {
    flex-direction: column;
  }
}
</style>
