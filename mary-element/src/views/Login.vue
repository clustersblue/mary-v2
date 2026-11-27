<template>
  <div class="login-wrapper">
    <div class="login-card-container">
      <el-card class="login-card" shadow="always">
        <!-- Logo / Branding Header -->
        <div class="branding-header">
          <div class="logo-circle">
            <el-icon class="brand-icon"><Calendar /></el-icon>
          </div>
          <h1 class="brand-title">Mary Care</h1>
          <p class="brand-subtitle">Domiciliary Care Management System</p>
        </div>

        <!-- Session Expired / Info Alert -->
        <el-alert
          v-if="sessionNotice"
          :title="sessionNotice"
          type="warning"
          show-icon
          :closable="true"
          class="auth-alert"
          @close="sessionNotice = ''"
        />

        <!-- Error Alert -->
        <el-alert
          v-if="errorMessage"
          :title="errorMessage"
          type="error"
          show-icon
          :closable="true"
          class="auth-alert"
          @close="errorMessage = ''"
        />

        <!-- Success Alert -->
        <el-alert
          v-if="successMessage"
          :title="successMessage"
          type="success"
          show-icon
          :closable="true"
          class="auth-alert"
          @close="successMessage = ''"
        />

        <!-- Login Form -->
        <el-form
          ref="loginFormRef"
          :model="loginData"
          :rules="loginRules"
          label-position="top"
          class="login-form"
          @keyup.enter="handleLogin"
        >
          <el-form-item label="Username" prop="username">
            <el-input
              v-model="loginData.username"
              placeholder="e.g. username"
              prefix-icon="User"
              size="large"
              clearable
            />
          </el-form-item>

          <el-form-item label="Password" prop="password">
            <el-input
              v-model="loginData.password"
              type="password"
              placeholder="Enter your account password"
              prefix-icon="Lock"
              show-password
              size="large"
              autocomplete="current-password"
            />
          </el-form-item>

          <div class="form-options">
            <el-checkbox v-model="loginData.rememberme">Remember me</el-checkbox>
            <el-button link type="primary" class="forgot-link" @click="openForgotDialog">
              Forgot Password?
            </el-button>
          </div>

          <el-button
            type="primary"
            size="large"
            class="submit-button"
            :loading="loading"
            @click="handleLogin"
          >
            Sign In
          </el-button>
        </el-form>

        <div class="footer-note flex flex-col items-center gap-1">
          <span>Protected by Health & Social Care UK GDPR Compliance</span>
          <router-link to="/privacy-policy" class="text-xs text-blue-600 hover:underline">
            Read our UK GDPR Privacy Notice & Data Protection Policy
          </router-link>
        </div>
      </el-card>
    </div>

    <!-- Forgot Password Modal Dialog -->
    <el-dialog
      v-model="forgotDialogVisible"
      title="Reset Your Password"
      width="440px"
      destroy-on-close
    >
      <p class="dialog-instruction">
        Enter your registered email address. If the account exists, a reset link will be emailed to it.
      </p>

      <el-alert
        v-if="forgotSuccess"
        :title="forgotSuccess"
        type="success"
        show-icon
        :closable="false"
        style="margin-bottom: 16px;"
      />

      <el-form
        ref="forgotFormRef"
        :model="forgotData"
        :rules="forgotRules"
        label-position="top"
        @keyup.enter="handleForgotPassword"
      >
        <el-form-item label="Registered Email Address" prop="email">
          <el-input
            v-model="forgotData.email"
            placeholder="e.g. yourname@marycare.co.uk"
            prefix-icon="Message"
            size="large"
            clearable
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="forgotDialogVisible = false">Cancel</el-button>
        <el-button
          type="primary"
          :loading="forgotLoading"
          @click="handleForgotPassword"
        >
          Send Reset Link
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AuthService from '@/service/AuthService'
import { useAuthStore } from '@/store/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const forgotFormRef = ref(null)

const loginData = ref({
  username: '',
  password: '',
  rememberme: false
})

const loginRules = {
  username: [{ required: true, message: 'Please enter your username or email', trigger: 'blur' }],
  password: [{ required: true, message: 'Please enter your password', trigger: 'blur' }]
}

const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const sessionNotice = ref('')

// Forgot Password Dialog
const forgotDialogVisible = ref(false)
const forgotLoading = ref(false)
const forgotSuccess = ref('')
const forgotData = ref({
  email: ''
})

const forgotRules = {
  email: [
    { required: true, message: 'Please enter your email address', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: ['blur', 'change'] }
  ]
}

async function handleLogin() {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    errorMessage.value = ''
    try {
      const res = await AuthService.login({
        username: loginData.value.username,
        password: loginData.value.password,
        rememberme: loginData.value.rememberme
      })

      if (res.token) {
        authStore.setAuthenticationToken(res.token, loginData.value.rememberme)
        if (res.user) {
          authStore.setUser(res.user, loginData.value.rememberme)
        }
        ElMessage.success(`Welcome back, ${res.user?.full_name || res.user?.username || 'User'}!`)
        router.push(safeInternalPath(route.query.redirect))
      } else {
        errorMessage.value = res.detail || res.message || 'Login failed. Please check your credentials.'
      }
    } catch (err) {
      const errDetail = err.response?.data?.detail || err.response?.data?.message || err.message
      errorMessage.value = errDetail || 'Incorrect username or password. Please try again.'
    } finally {
      loading.value = false
    }
  })
}

function safeInternalPath(value) {
  const path = Array.isArray(value) ? value[0] : value
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('://')) {
    return '/'
  }
  return path
}

function openForgotDialog() {
  forgotData.value.email = loginData.value.username.includes('@') ? loginData.value.username : ''
  forgotSuccess.value = ''
  forgotDialogVisible.value = true
}

async function handleForgotPassword() {
  if (!forgotFormRef.value) return
  await forgotFormRef.value.validate(async (valid) => {
    if (!valid) return
    forgotLoading.value = true
    forgotSuccess.value = ''
    try {
      const res = await AuthService.forgot({ email: forgotData.value.email })
      forgotSuccess.value = res.message || 'If the email is registered, a reset link has been sent.'
      ElMessage.success('If the email is registered, a reset link has been sent.')
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || 'Failed to dispatch reset link.')
    } finally {
      forgotLoading.value = false
    }
  })
}

onMounted(() => {
  if (route.query.reason === 'expired') {
    sessionNotice.value = 'For your security, your session has expired. Please sign in again.'
  }
})
</script>

<style scoped>
.login-wrapper {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  padding: 16px;
  box-sizing: border-box;
}

.login-card-container {
  width: 100%;
  max-width: 440px;
}

.login-card {
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
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  letter-spacing: -0.5px;
}

.brand-subtitle {
  margin: 6px 0 0 0;
  font-size: 13px;
  color: #909399;
}

.auth-alert {
  margin-bottom: 16px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.forgot-link {
  font-size: 13px;
  padding: 0;
}

.submit-button {
  width: 100%;
  font-size: 15px;
  font-weight: 600;
  height: 44px;
}

.footer-note {
  text-align: center;
  margin-top: 24px;
  font-size: 11px;
  color: #a8abb2;
}

.dialog-instruction {
  font-size: 13px;
  color: #606266;
  margin-top: 0;
  margin-bottom: 16px;
  line-height: 1.5;
}
</style>
