import { defineStore } from 'pinia'
import AuthService from '@/service/AuthService'
import { registerSessionReset } from '@/service/authGate'

export const useAuthStore = defineStore('auth', {
  state: () => {
    const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token') || null
    let storedUser = null
    try {
      const rawUser = localStorage.getItem('user') || sessionStorage.getItem('user')
      if (rawUser) storedUser = JSON.parse(rawUser)
    } catch (e) {
      storedUser = null
    }

    return {
      token: storedToken,
      isAuthenticated: Boolean(storedToken),
      user: storedUser,
      sessionValidated: false
    }
  },

  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    currentUser: (state) => state.user,
    userRole: (state) => Number(state.user?.role || 3),
    isAdmin: (state) => Boolean(Number(state.user?.role) === 1 || Number(state.user?.is_admin) === 1),
    isStaff: (state) => Boolean(Number(state.user?.role) === 2),
    isCarer: (state) => Boolean(Number(state.user?.role) === 3 && Number(state.user?.is_admin) !== 1),
    hasStaffAccess: (state) => {
      const role = Number(state.user?.role)
      const isAdminFlag = Number(state.user?.is_admin) === 1
      return isAdminFlag || role === 1 || role === 2
    },
    hasFinanceAccess: (state) => {
      const role = Number(state.user?.role)
      const isAdminFlag = Number(state.user?.is_admin) === 1
      if (isAdminFlag || role === 1) return true
      return role === 2 && isAdminFlag
    },
    hasCarerAccess: (state) => Boolean(state.user)
  },

  actions: {
    setAuthenticationToken(token, remember = true) {
      this.token = token
      this.isAuthenticated = Boolean(token)
      if (remember) {
        localStorage.setItem('token', token)
      } else {
        sessionStorage.setItem('token', token)
      }
    },

    setUser(user, remember = true) {
      this.user = user
      this.isAuthenticated = true
      const userStr = JSON.stringify(user)
      if (remember) {
        localStorage.setItem('user', userStr)
      } else {
        sessionStorage.setItem('user', userStr)
      }
    },

    async validateSession() {
      if (!this.token) {
        this.logout()
        return 'unauthorized'
      }
      try {
        const userData = await AuthService.getCurrentUser()
        if (userData && userData.id) {
          this.user = userData
          this.isAuthenticated = true
          this.sessionValidated = true
          return 'ok'
        }
        this.logout()
        return 'unauthorized'
      } catch (err) {
        const status = err?.response?.status
        if (status === 401) {
          this.logout()
          return 'unauthorized'
        }
        return 'unavailable'
      }
    },

    getAuthenticationToken() {
      return { token: this.token }
    },

    getUser() {
      return this.user
    },

    logout() {
      this.token = null
      this.user = null
      this.isAuthenticated = false
      this.sessionValidated = false
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      sessionStorage.removeItem('token')
      sessionStorage.removeItem('user')
    },

    checkAccess(roles, permissions) {
      if (!this.user) return false
      // Administrators have unrestricted access to all modules, pages, menus, APIs, and actions
      if (this.isAdmin) return true
      if (roles && Array.isArray(roles) && roles.length > 0) {
        const userRole = Number(this.user.role)
        if (!roles.map(Number).includes(userRole)) return false
      }
      if (permissions && Array.isArray(permissions) && permissions.length > 0) {
        const userAdminFlag = Number(this.user.is_admin)
        if (!permissions.map(Number).includes(userAdminFlag)) return false
      }
      return true
    }
  }
})

registerSessionReset(() => {
  useAuthStore().logout()
})
