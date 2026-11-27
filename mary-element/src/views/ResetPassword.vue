<template>
  <div class="reset-wrapper">
    <div class="reset-card-container">
      <el-card class="reset-card" shadow="always">
        <!-- Header -->
        <div class="branding-header">
          <div class="logo-circle">
            <el-icon class="brand-icon"><Key /></el-icon>
          </div>
          <h1 class="brand-title">Create New Password</h1>
          <p class="brand-subtitle">Choose a secure password with at least 8 characters</p>
        </div>

        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          :closable="true"
          style="margin-bottom: 16px;"
          @close="errorMessage = ''"
        />

        <el-alert
          v-if="successMessage"
          :title="successMessage"
          type="success"
          show-icon
          :closable="false"
          style="margin-bottom: 16px;"
        />

        <el-form
          ref="resetFormRef"
          :model="resetData"
          :rules="resetRules"
          label-position="top"
          @keyup.enter="handleReset"
        >
          <el-form-item label="Account Email Address" prop="email">
            <el-input
              v-model="resetData.email"
              :disabled="Boolean(route.query.email)"
              placeholder="Enter your registered email address"
              prefix-icon="Message"
              size="large"
            />
          </el-form-item>

          <el-form-item label="New Password" prop="password">
            <el-input
              v-model="resetData.password"
              type="password"
              placeholder="Minimum 8 characters"
              prefix-icon="Lock"
              show-password
              size="large"
            />
          </el-form-item>

          <el-form-item label="Confirm New Password" prop="password_confirmation">
            <el-input
              v-model="resetData.password_confirmation"
              type="password"
              placeholder="Re-enter your new password"
              prefix-icon="Lock"
              show-password
              size="large"
            />
          </el-form-item>

          <el-button
            type="primary"
            size="large"
            class="submit-button"
            :loading="loading"
            @click="handleReset"
          >
            Update Password & Return to Login
          </el-button>

          <div class="back-link-box">
            <router-link to="/login" class="back-link">
              <el-icon><ArrowLeft /></el-icon> Back to Sign In
            </router-link>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AuthService from '@/service/AuthService'

const route = useRoute()
const router = useRouter()
const resetFormRef = ref(null)

const resetData = ref({
  email: '',
  token: '',
  password: '',
  password_confirmation: ''
})

const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const validatePassConfirm = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please confirm your password'))
  } else if (value !== resetData.value.password) {
    callback(new Error('Passwords do not match'))
  } else {
    callback()
  }
}

const resetRules = {
  password: [
    { required: true, message: 'Please enter a new password', trigger: 'blur' },
    { min: 8, message: 'Password must be at least 8 characters', trigger: 'blur' }
  ],
  password_confirmation: [
    { required: true, message: 'Please confirm your new password', trigger: 'blur' },
    { validator: validatePassConfirm, trigger: 'blur' }
  ]
}

async function handleReset() {
  if (!resetFormRef.value) return
  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await ElMessageBox.confirm(
        'Are you sure you want to proceed with resetting your password?',
        'Confirm Password Reset',
        {
          type: 'warning',
          confirmButtonText: 'Reset Password',
          cancelButtonText: 'Cancel'
        }
      )
    } catch {
      return
    }

    loading.value = true
    errorMessage.value = ''
    try {
      const res = await AuthService.reset({
        email: resetData.value.email,
        token: resetData.value.token,
        password: resetData.value.password,
        password_confirmation: resetData.value.password_confirmation
      })

      successMessage.value = res.message || 'Password updated successfully! Redirecting to login...'
      ElMessage.success('Password updated successfully!')
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    } catch (err) {
      errorMessage.value = err.response?.data?.detail || err.response?.data?.message || err.message
      ElMessage.error(errorMessage.value)
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  resetData.value.email = route.query.email || ''
  resetData.value.token = route.query.token || ''
  if (!resetData.value.token) {
    errorMessage.value = 'Please request a password reset link from the login page, or paste your reset link token below.'
  }
})
</script>

<style scoped>
.reset-wrapper {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  padding: 16px;
  box-sizing: border-box;
}

.reset-card-container {
  width: 100%;
  max-width: 440px;
}

.reset-card {
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.2) !important;
  border: none;
  padding: 8px 12px;
}

.branding-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #ecf5ff;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 12px;
}

.brand-icon {
  font-size: 32px;
  color: #409eff;
}

.brand-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #2c3e50;
}

.brand-subtitle {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #909399;
}

.submit-button {
  width: 100%;
  margin-top: 12px;
  font-size: 15px;
  font-weight: 600;
  height: 44px;
}

.back-link-box {
  text-align: center;
  margin-top: 18px;
}

.back-link {
  color: #909399;
  text-decoration: none;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.back-link:hover {
  color: #409eff;
}
</style>
