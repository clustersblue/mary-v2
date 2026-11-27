<template>
  <div class="account-view-container">
    <el-card shadow="never" class="account-card">
      <template #header>
        <div class="flex items-center gap-3">
          <el-avatar :size="48" icon="UserFilled" class="bg-blue-600 text-white" />
          <div>
            <h2 class="text-xl font-bold text-gray-800 m-0">My Account Profile</h2>
            <p class="text-sm text-gray-500 m-0 mt-1">
              Manage your personal information, emergency contacts, and account security credentials.
            </p>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        v-loading="loading"
        @submit.prevent="handleSubmit"
      >
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <el-form-item label="First Name" prop="first_name">
            <el-input v-model="form.first_name" placeholder="Your First Name" clearable />
          </el-form-item>

          <el-form-item label="Surname" prop="surname">
            <el-input v-model="form.surname" placeholder="Your Surname" clearable />
          </el-form-item>

          <el-form-item label="Username" prop="username">
            <el-input v-model="form.username" placeholder="Username for system login" clearable />
          </el-form-item>

          <el-form-item label="Mobile Number" prop="mobile_number">
            <el-input v-model="form.mobile_number" placeholder="Mobile phone number" clearable />
          </el-form-item>

          <el-form-item label="Email Address" prop="email" class="md:col-span-2">
            <el-input v-model="form.email" placeholder="Official contact email" clearable />
          </el-form-item>
        </div>

        <el-divider content-position="left">
          <span class="text-sm font-semibold text-gray-600">In Case of Emergency</span>
        </el-divider>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <el-form-item label="Emergency Contact Name">
            <el-input v-model="form.emergency_contact_name" placeholder="Name of primary emergency contact" clearable />
          </el-form-item>

          <el-form-item label="Emergency Contact Number">
            <el-input v-model="form.emergency_contact_number" placeholder="Phone number for emergencies" clearable />
          </el-form-item>
        </div>

        <el-divider content-position="left">
          <span class="text-sm font-semibold text-gray-600">Change Password (Optional)</span>
        </el-divider>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <el-form-item label="New Password" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="Leave blank to keep current password"
            />
          </el-form-item>

          <el-form-item label="Confirm New Password" prop="password_confirmation">
            <el-input
              v-model="form.password_confirmation"
              type="password"
              show-password
              placeholder="Confirm new password"
            />
          </el-form-item>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <el-button @click="resetForm">Reset Changes</el-button>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            Update Account
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AuthService from '@/service/AuthService'
import { useAuthStore } from '@/store/auth'

const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)
const saving = ref(false)

const form = ref({
  id: null,
  first_name: '',
  surname: '',
  username: '',
  email: '',
  mobile_number: '',
  emergency_contact_name: '',
  emergency_contact_number: '',
  password: '',
  password_confirmation: ''
})

const validatePassConfirm = (rule, value, callback) => {
  if (form.value.password && value !== form.value.password) {
    callback(new Error('Passwords do not match'))
  } else {
    callback()
  }
}

const rules = {
  first_name: [{ required: true, message: 'Please enter your first name', trigger: 'blur' }],
  surname: [{ required: true, message: 'Please enter your surname', trigger: 'blur' }],
  username: [{ required: true, message: 'Please enter your username', trigger: 'blur' }],
  email: [
    { required: true, message: 'Please enter your email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: ['blur', 'change'] }
  ],
  password: [
    { min: 8, message: 'Password must be at least 8 characters if provided', trigger: 'blur' }
  ],
  password_confirmation: [
    { validator: validatePassConfirm, trigger: 'blur' }
  ]
}

function populateForm(user) {
  if (!user) return
  form.value.id = user.id
  form.value.first_name = user.first_name || ''
  form.value.surname = user.surname || ''
  form.value.username = user.username || ''
  form.value.email = user.email || ''
  form.value.mobile_number = user.mobile_number || ''
  form.value.emergency_contact_name = user.emergency_contact_name || ''
  form.value.emergency_contact_number = user.emergency_contact_number || ''
  form.value.password = ''
  form.value.password_confirmation = ''
}

async function loadProfile() {
  loading.value = true
  try {
    const user = await AuthService.getCurrentUser()
    if (user) {
      authStore.setUser(user)
      populateForm(user)
    }
  } catch (err) {
    if (authStore.user) {
      populateForm(authStore.user)
    }
  } finally {
    loading.value = false
  }
}

function resetForm() {
  if (authStore.user) {
    populateForm(authStore.user)
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      await ElMessageBox.confirm(
        'Do you want to proceed with updating your account profile?',
        'Confirm Account Changes',
        {
          type: 'info',
          confirmButtonText: 'Proceed',
          cancelButtonText: 'Cancel'
        }
      )
    } catch {
      return
    }

    saving.value = true
    try {
      const payload = {
        first_name: form.value.first_name,
        surname: form.value.surname,
        username: form.value.username,
        email: form.value.email,
        mobile_number: form.value.mobile_number,
        emergency_contact_name: form.value.emergency_contact_name,
        emergency_contact_number: form.value.emergency_contact_number
      }

      if (form.value.password && form.value.password.trim() !== '') {
        payload.password = form.value.password.trim()
      }

      const res = await AuthService.updateAccount(form.value.id || authStore.user?.id || 1, payload)
      if (res.success || res.data) {
        ElMessage.success('Account profile updated successfully!')
        if (res.data) {
          authStore.setUser(res.data)
          populateForm(res.data)
        }
      } else {
        ElMessage.error(res.message || 'Failed to update account.')
      }
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || err.message || 'Error updating account')
    } finally {
      saving.value = false
    }
  })
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.account-view-container {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}
.account-card {
  border-radius: 8px;
}
</style>
