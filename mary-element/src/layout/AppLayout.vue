<template>
  <el-container class="layout-container">
    <!-- Collapsible Vertical Sidebar Menu -->
    <el-aside :width="isCollapsed ? '64px' : '250px'" class="aside-menu">
      <div class="logo-container">
        <el-icon class="logo-icon"><Calendar /></el-icon>
        <span v-if="!isCollapsed" class="logo-text">St. Mary's Team Care Ltd.</span>
      </div>

      <el-scrollbar>
        <el-menu
          :default-active="activeRoute"
          :collapse="isCollapsed"
          router
          class="el-menu-vertical"
        >
          <el-menu-item index="/" v-if="authStore.isAdmin">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>Dashboard</template>
          </el-menu-item>

          <el-menu-item index="/attendance">
            <el-icon><Clock /></el-icon>
            <template #title>Carer Portal</template>
          </el-menu-item>

          <el-menu-item index="/planner" v-if="authStore.hasStaffAccess">
            <el-icon><Calendar /></el-icon>
            <template #title>Care Rota Planner</template>
          </el-menu-item>

          <el-menu-item index="/dtr" v-if="authStore.hasStaffAccess">
            <el-icon><Timer /></el-icon>
            <template #title>Daily Time Record (DTR)</template>
          </el-menu-item>

          <el-sub-menu index="finance" v-if="authStore.hasFinanceAccess">
            <template #title>
              <el-icon><Money /></el-icon>
              <span>Finance & Payroll</span>
            </template>
            <el-menu-item index="/payments">Generate Payments</el-menu-item>
            <el-menu-item index="/payroll">Payroll Management</el-menu-item>
            <el-menu-item index="/invoice">Invoice Management</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="management" v-if="authStore.hasStaffAccess">
            <template #title>
              <el-icon><User /></el-icon>
              <span>Management</span>
            </template>
            <el-menu-item index="/management/service-users">Service Users</el-menu-item>
            <el-menu-item index="/management/carers">Carers</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="settings" v-if="authStore.hasStaffAccess">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>Settings</span>
            </template>
            <el-menu-item index="/settings/shifts">Shifts Code</el-menu-item>
            <el-menu-item index="/settings/care-types">Care Types</el-menu-item>
            <el-menu-item index="/settings/medical-conditions">Medical Conditions</el-menu-item>
            <el-menu-item index="/settings/condition-categories">Condition Categories</el-menu-item>
            <el-menu-item index="/settings/branches">Branches</el-menu-item>
            <el-menu-item index="/settings/relations">Kinship Relations</el-menu-item>
            <el-menu-item index="/settings/genders">Genders</el-menu-item>
            <el-menu-item index="/settings/religions">Religions</el-menu-item>
            <el-menu-item index="/settings/trainings">Training Courses</el-menu-item>

            <el-menu-item index="/settings/gp">General Practitioners</el-menu-item>
            <el-menu-item index="/settings/nhs">NHS Commissioners</el-menu-item>
            <el-menu-item index="/settings/service-statuses">Service Statuses</el-menu-item>
            <el-menu-item index="/settings/rates">Pay Rates</el-menu-item>

            <el-menu-item index="/settings/employment-types">Employment Types</el-menu-item>
            <el-menu-item index="/settings/carer-statuses">Carer Statuses</el-menu-item>
            <el-menu-item index="/settings/resident-statuses">Resident Statuses</el-menu-item>
            <el-menu-item index="/settings/pension-schemes">Pension Schemes</el-menu-item>
            <el-menu-item index="/settings/nationalities">Nationalities</el-menu-item>
            <el-menu-item index="/settings/contract-types">Contract Types</el-menu-item>
            <el-menu-item index="/settings/requirements">Employment Requirements</el-menu-item>

            <el-menu-item index="/settings/dtr-shifts">DTR Shifts</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container>
      <!-- Navigation Header with Collapse Toggle & Dark/Light Switch -->
      <el-header class="layout-header">
        <div class="header-left">
          <el-button
            type="text"
            :icon="isCollapsed ? 'Expand' : 'Fold'"
            @click="isCollapsed = !isCollapsed"
            class="collapse-btn"
          />
          <span class="page-title">{{ currentPageTitle }}</span>
        </div>

        <div class="header-right">
          <!-- Dark / Light Mode Switch using @vueuse/core useDark -->
          <el-switch
            v-model="isDark"
            inline-prompt
            active-icon="Moon"
            inactive-icon="Sunny"
            class="theme-switch"
          />

          <!-- User Account Dropdown -->
          <el-dropdown trigger="click">
            <span class="user-profile">
              <el-avatar :size="32" icon="UserFilled" class="user-avatar" />
              <span class="user-name">{{ authStore.user?.full_name || authStore.user?.username || 'Admin User' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/account')">
                  <el-icon class="mr-1"><UserFilled /></el-icon> My Account
                </el-dropdown-item>
                <el-dropdown-item v-if="authStore.isAdmin" @click="$router.push('/audit-logs')">
                  <el-icon class="mr-1"><DocumentChecked /></el-icon> Audit Trail
                </el-dropdown-item>
                <el-dropdown-item @click="$router.push('/privacy-policy')">
                  <el-icon class="mr-1"><Document /></el-icon> Privacy Notice
                </el-dropdown-item>
                <el-dropdown-item v-if="authStore.hasStaffAccess" @click="$router.push('/user-manual')">
                  <el-icon class="mr-1"><Reading /></el-icon> User Manual
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon class="mr-1"><SwitchButton /></el-icon> Logout
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Main Content Area -->
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDark } from '@vueuse/core'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/auth'

const isCollapsed = ref(false)
const isDark = useDark()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeRoute = computed(() => route.path)
const currentPageTitle = computed(() => {
  if (route.meta && route.meta.title) {
    return route.meta.title
  }
  return route.name || 'Mary Care System'
})

function handleLogout() {
  authStore.logout()
  ElMessage.info('Logged out successfully')
  router.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.aside-menu {
  background-color: var(--el-bg-color-overlay, #ffffff);
  border-right: 1px solid var(--el-border-color-light, #e6e6e6);
  transition: width 0.3s ease;
  display: flex;
  flex-direction: column;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, #f0f0f0);
}

.logo-icon {
  font-size: 24px;
  color: var(--el-color-primary, #409eff);
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary, #303133);
  white-space: nowrap;
}

.el-menu-vertical {
  border-right: none;
}

.layout-header {
  height: 60px;
  background-color: var(--el-bg-color-overlay, #ffffff);
  border-bottom: 1px solid var(--el-border-color-light, #e6e6e6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  color: var(--el-text-color-primary);
  cursor: pointer;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.theme-switch {
  --el-switch-on-color: #2c2c2c;
  --el-switch-off-color: #f2f2f2;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.layout-main {
  background-color: var(--el-bg-color-page, #f5f7fa);
  padding: 20px;
  overflow-y: auto;
}
</style>
