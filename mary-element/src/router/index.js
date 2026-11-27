import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/layout/AppLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: 'Login - Mary Care Management System', public: true }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/ResetPassword.vue'),
    meta: { title: 'Reset Password - Mary Care', public: true }
  },
  {
    path: '/privacy-policy',
    name: 'PrivacyPolicy',
    component: () => import('@/views/PrivacyPolicy.vue'),
    meta: { title: 'Privacy notice - Mary Care', public: true }
  },
  {
    path: '/access-denied',
    name: 'AccessDenied',
    component: () => import('@/views/AccessDenied.vue'),
    meta: { title: 'Access Denied - Mary Care', public: true }
  },
  {
    path: '/auth/access',
    name: 'AccessDeniedLegacy',
    component: () => import('@/views/AccessDenied.vue'),
    meta: { title: 'Access Denied - Mary Care', public: true }
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/MaryDashboard.vue'),
        meta: { title: 'Executive Dashboard', role: [1] }
      },
      {
        path: 'account',
        name: 'Account',
        component: () => import('@/views/Account.vue'),
        meta: { title: 'My Account - User Profile', role: [1, 2, 3] }
      },
      {
        path: 'audit-logs',
        name: 'AuditLogs',
        component: () => import('@/views/AuditLogsView.vue'),
        meta: { title: 'Audit Trail', role: [1] }
      },
      {
        path: 'planner',
        name: 'CarePlanner',
        component: () => import('@/views/CarePlannerView.vue'),
        meta: { title: 'Care Rota Planner', role: [1, 2] }
      },
      {
        path: 'attendance',
        name: 'Attendance',
        component: () => import('@/views/MaryAttendance.vue'),
        meta: { title: 'Carer Portal & Attendance', role: [1, 2, 3] }
      },
      {
        path: 'dtr',
        name: 'DailyTimeRecord',
        component: () => import('@/views/DailyTimeRecord.vue'),
        meta: { title: 'Daily Time Record (DTR)', role: [1, 2] }
      },
      {
        path: 'payments',
        name: 'Payments',
        component: () => import('@/views/MaryPayments.vue'),
        meta: { title: 'Generate Payments', role: [1, 2], permission: [1] }
      },
      {
        path: 'payroll',
        name: 'Payroll',
        component: () => import('@/views/MaryPayroll.vue'),
        meta: { title: 'Payroll Management', role: [1, 2], permission: [1] }
      },
      {
        path: 'invoice',
        name: 'Invoice',
        component: () => import('@/views/MaryInvoice.vue'),
        meta: { title: 'Invoice Management', role: [1, 2], permission: [1] }
      },
      {
        path: 'user-manual',
        name: 'UserManual',
        component: () => import('@/views/UserManual.vue'),
        meta: { title: 'User Manual & Documentation', role: [1, 2] }
      },
      // Management Routes
      {
        path: 'management/service-users',
        name: 'ManagementServiceUsers',
        component: () => import('@/views/management/ServiceUsersView.vue'),
        meta: { title: 'Management - Service Users', role: [1, 2] }
      },
      {
        path: 'management/carers',
        name: 'ManagementCarers',
        component: () => import('@/views/management/CarersView.vue'),
        meta: { title: 'Management - Carers Staff', role: [1, 2] }
      },
      // 28 Master Settings Screens
      {
        path: 'settings/service-users',
        name: 'SettingsServiceUsers',
        component: () => import('@/views/management/ServiceUsersView.vue'),
        meta: { title: 'Management - Service Users', role: [1, 2] }
      },
      {
        path: 'settings/carers',
        name: 'SettingsCarers',
        component: () => import('@/views/management/CarersView.vue'),
        meta: { title: 'Management - Carer Staff', role: [1, 2] }
      },
      {
        path: 'settings/branches',
        name: 'SettingsBranches',
        component: () => import('@/views/settings/SettingsBranches.vue'),
        meta: { title: 'Settings - Agency Branches', role: [1, 2] }
      },
      {
        path: 'settings/shifts',
        name: 'SettingsShifts',
        component: () => import('@/views/settings/SettingsShifts.vue'),
        meta: { title: 'Settings - Shifts Catalog', role: [1, 2] }
      },
      {
        path: 'settings/dtr-shifts',
        name: 'SettingsDTRShifts',
        component: () => import('@/views/settings/SettingsDTRShifts.vue'),
        meta: { title: 'Settings - DTR Work Shifts', role: [1, 2] }
      },
      {
        path: 'settings/rates',
        name: 'SettingsRates',
        component: () => import('@/views/settings/SettingsRates.vue'),
        meta: { title: 'Settings - Carer Pay Rates', role: [1, 2] }
      },
      {
        path: 'settings/carer-rates',
        name: 'SettingsCarerRates',
        component: () => import('@/views/settings/SettingsCarerRates.vue'),
        meta: { title: 'Settings - Client Billable Rates', role: [1, 2] }
      },
      {
        path: 'settings/gp',
        name: 'SettingsGP',
        component: () => import('@/views/settings/SettingsGP.vue'),
        meta: { title: 'Settings - GP Practices', role: [1, 2] }
      },
      {
        path: 'settings/nhs',
        name: 'SettingsNhs',
        component: () => import('@/views/settings/SettingsNhs.vue'),
        meta: { title: 'Settings - NHS Commissioners', role: [1, 2] }
      },
      {
        path: 'settings/pension-schemes',
        name: 'SettingsPensionSchemes',
        component: () => import('@/views/settings/SettingsPensionSchemes.vue'),
        meta: { title: 'Settings - Pension Schemes', role: [1, 2] }
      },
      {
        path: 'settings/care-types',
        name: 'SettingsCareTypes',
        component: () => import('@/views/settings/SettingsCareTypes.vue'),
        meta: { title: 'Settings - Care Types', role: [1, 2] }
      },
      {
        path: 'settings/medical-conditions',
        name: 'SettingsMedicalConditions',
        component: () => import('@/views/settings/SettingsMedicalConditions.vue'),
        meta: { title: 'Settings - Medical Conditions', role: [1, 2] }
      },
      {
        path: 'settings/condition-categories',
        name: 'SettingsConditionCategories',
        component: () => import('@/views/settings/SettingsConditionCategories.vue'),
        meta: { title: 'Settings - Condition Categories', role: [1, 2] }
      },
      {
        path: 'settings/services',
        name: 'SettingsServices',
        component: () => import('@/views/settings/SettingsServices.vue'),
        meta: { title: 'Settings - Care Services', role: [1, 2] }
      },
      {
        path: 'settings/service-statuses',
        name: 'SettingsServiceStatuses',
        component: () => import('@/views/settings/SettingsServiceStatuses.vue'),
        meta: { title: 'Settings - Service Statuses', role: [1, 2] }
      },
      {
        path: 'settings/carer-statuses',
        name: 'SettingsCarerStatuses',
        component: () => import('@/views/settings/SettingsCarerStatuses.vue'),
        meta: { title: 'Settings - Carer Statuses', role: [1, 2] }
      },
      {
        path: 'settings/employment-types',
        name: 'SettingsEmploymentType',
        component: () => import('@/views/settings/SettingsEmploymentType.vue'),
        meta: { title: 'Settings - Employment Types', role: [1, 2] }
      },
      {
        path: 'settings/contract-types',
        name: 'SettingsContractType',
        component: () => import('@/views/settings/SettingsContractType.vue'),
        meta: { title: 'Settings - Contract Types', role: [1, 2] }
      },
      {
        path: 'settings/resident-statuses',
        name: 'SettingsResidentStatuses',
        component: () => import('@/views/settings/SettingsResidentStatuses.vue'),
        meta: { title: 'Settings - Resident Statuses', role: [1, 2] }
      },
      {
        path: 'settings/nationalities',
        name: 'SettingsNationalities',
        component: () => import('@/views/settings/SettingsNationalities.vue'),
        meta: { title: 'Settings - Nationalities', role: [1, 2] }
      },
      {
        path: 'settings/marital-statuses',
        name: 'SettingsMaritalStatuses',
        component: () => import('@/views/settings/SettingsMaritalStatuses.vue'),
        meta: { title: 'Settings - Marital Statuses', role: [1, 2] }
      },
      {
        path: 'settings/relations',
        name: 'SettingsRelations',
        component: () => import('@/views/settings/SettingsRelations.vue'),
        meta: { title: 'Settings - Kinship Relations', role: [1, 2] }
      },
      {
        path: 'settings/religions',
        name: 'SettingsReligions',
        component: () => import('@/views/settings/SettingsReligions.vue'),
        meta: { title: 'Settings - Religions', role: [1, 2] }
      },
      {
        path: 'settings/genders',
        name: 'SettingsGenders',
        component: () => import('@/views/settings/SettingsGenders.vue'),
        meta: { title: 'Settings - Genders', role: [1, 2] }
      },
      {
        path: 'settings/requirements',
        name: 'SettingsRequirements',
        component: () => import('@/views/settings/SettingsRequirements.vue'),
        meta: { title: 'Settings - Mandatory Requirements', role: [1, 2] }
      },
      {
        path: 'settings/requirement-statuses',
        name: 'SettingsRequirementStatuses',
        component: () => import('@/views/settings/SettingsRequirementStatuses.vue'),
        meta: { title: 'Settings - Requirement Statuses', role: [1, 2] }
      },
      {
        path: 'settings/trainings',
        name: 'SettingsTrainings',
        component: () => import('@/views/settings/SettingsTrainings.vue'),
        meta: { title: 'Settings - Training Courses', role: [1, 2] }
      },
      {
        path: 'settings/references',
        name: 'SettingsReferences',
        component: () => import('@/views/settings/SettingsReferences.vue'),
        meta: { title: 'Settings - References', role: [1, 2] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

import { useAuthStore } from '@/store/auth'
import { beginSessionValidation, setGuardOwnsRedirect } from '@/service/authGate'

router.beforeEach(async (to, from, next) => {
  if (to.meta && to.meta.title) {
    document.title = to.meta.title
  }

  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  const isPublic = to.meta.public || to.path === '/login' || to.path === '/reset-password' || to.path === '/privacy-policy' || to.path === '/access-denied' || to.path === '/auth/access'

  if (!isPublic && !token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  const authStore = useAuthStore()

  // Preflight / session validation. Data requests wait on this attempt.
  if (token && !authStore.sessionValidated) {
    let releaseGate = () => {}
    const gate = new Promise((resolve) => { releaseGate = resolve })
    beginSessionValidation(gate)
    setGuardOwnsRedirect(true)
    let status = 'unavailable'
    try {
      status = await authStore.validateSession()
    } catch (e) {
      status = authStore.token ? 'unavailable' : 'unauthorized'
    } finally {
      releaseGate()
      setGuardOwnsRedirect(false)
    }
    if (status === 'unauthorized' && !isPublic) {
      return next({ path: '/login', query: { reason: 'expired', redirect: to.fullPath } })
    }
  }

  const sessionToken = localStorage.getItem('token') || sessionStorage.getItem('token')

  // If visiting login while authenticated, route to appropriate landing page
  if (to.path === '/login' && sessionToken) {
    if (authStore.isAdmin) return next('/')
    if (authStore.hasStaffAccess) return next('/planner')
    return next('/attendance')
  }

  // Handle root '/' path redirection for non-admins
  if (to.path === '/' && sessionToken) {
    if (authStore.isAdmin) {
      return next()
    } else if (authStore.hasStaffAccess) {
      return next('/planner')
    } else {
      return next('/attendance')
    }
  }

  // RBAC Access Control Guard
  if (sessionToken && !isPublic) {
    // Administrators retain unrestricted access to all modules, pages, and menus
    if (authStore.isAdmin) {
      return next()
    }

    const requiredRoles = to.meta?.role
    const requiredPermissions = to.meta?.permission

    if (requiredRoles || requiredPermissions) {
      const hasAccess = authStore.checkAccess(requiredRoles, requiredPermissions)
      if (!hasAccess) {
        return next('/access-denied')
      }
    }
  }

  next()
})

export default router
