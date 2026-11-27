import api from './api'

export default {
  async login(credentials) {
    const res = await api.post('/login', credentials)
    return res.data
  },

  async logout() {
    try {
      const res = await api.post('/logout')
      return res.data
    } catch (e) {
      return { success: true }
    }
  },

  async forgot(payload) {
    const res = await api.post('/forgot-password', payload)
    return res.data
  },

  async reset(payload) {
    const res = await api.post('/reset-password', payload)
    return res.data
  },

  async getCurrentUser() {
    const res = await api.get('/me')
    return res.data
  },

  async updateAccount(id, data) {
    const res = await api.post(`/updateaccount/${id}`, data)
    return res.data
  }
}
