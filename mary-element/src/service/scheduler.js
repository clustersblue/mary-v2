import api from './api'

export default {
  async getCarers() {
    const res = await api.get('/getcarers?lightweight=true')
    return res.data
  },
  async getServiceUsers() {
    const res = await api.get('/getsu')
    return res.data
  },
  // Shift catalog from mary_api_db_new.m_shifts for Care Planner & Rota
  async getMShifts() {
    const res = await api.get('/m-shifts')
    return res.data
  },
  // Work Shift definitions from mary_api_db_new.dtr_shifts (Authoritative Shift Source)
  async getShiftTemplates() {
    const res = await api.get('/shifts')
    return (res.data && res.data.data) ? res.data.data : res.data
  },
  async getDtrShifts() {
    const res = await api.get('/shifts')
    return (res.data && res.data.data) ? res.data.data : res.data
  },
  async getBranches() {
    const res = await api.get('/getbranches')
    return res.data
  },
  async getUserShifts() {
    const res = await api.get('/usershifts')
    return res.data
  },
  async getEvents(startDate, endDate, carerId, search = null) {
    let params = []
    if (startDate) params.push(`start_date=${startDate}`)
    if (endDate) params.push(`end_date=${endDate}`)
    if (carerId) params.push(`carer_id=${carerId}`)
    if (search && search.trim()) params.push(`search=${encodeURIComponent(search.trim())}`)
    
    let url = '/get-events'
    if (params.length) {
      url += '?' + params.join('&')
    }
    const res = await api.get(url)
    return res.data
  },
  async saveUserShift(shiftData) {
    const res = await api.post('/users/shifts', shiftData)
    return res.data
  },
  async updateUserShift(id, shiftData, paramsObj = {}) {
    let url = `/users/shifts/${id}`
    const query = []
    if (paramsObj.mode) query.push(`mode=${paramsObj.mode}`)
    if (paramsObj.occurrence_date) query.push(`occurrence_date=${paramsObj.occurrence_date}`)
    if (query.length) url += '?' + query.join('&')
    const res = await api.put(url, shiftData)
    return res.data
  },
  async deleteUserShift(id, paramsObj = {}) {
    let url = `/users/shifts/${id}`
    const query = []
    if (paramsObj.mode) query.push(`mode=${paramsObj.mode}`)
    if (paramsObj.occurrence_date) query.push(`occurrence_date=${paramsObj.occurrence_date}`)
    if (query.length) url += '?' + query.join('&')
    const res = await api.delete(url)
    return res.data
  },
  async bulkDeleteShifts(payload) {
    const res = await api.post('/users/shifts/bulk-delete', payload)
    return res.data
  }
}
