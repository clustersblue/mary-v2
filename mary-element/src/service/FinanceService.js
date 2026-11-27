import api from './api'

export default {
  async getTransactions({ param, selectionList, dates }) {
    let url = `/getaserviceusertransactions?param=${param}`
    if (selectionList) {
      url += `&selectionList=${selectionList}`
    }
    if (dates && dates.length === 2) {
      url += `&dates=${encodeURIComponent(dates[0])}&dates=${encodeURIComponent(dates[1])}`
    } else if (dates && dates.length === 1) {
      url += `&dates=${encodeURIComponent(dates[0])}`
    }
    const response = await api.get(url)
    return response.data
  },

  async generatePayments(payload) {
    const response = await api.post('/generatepayments', payload)
    return response.data
  },

  async getPayrolls() {
    const response = await api.get('/getpayrolls')
    return response.data
  },

  async markPayrolls(payload) {
    const response = await api.post('/markpayrolls', payload)
    return response.data
  },

  async deletePayroll(payload) {
    const response = await api.post('/deletepayroll', payload)
    return response.data
  },

  async updateTransactionRate({ id, rate }) {
    const response = await api.post(`/updatetransactionrate/${id}`, { rate })
    return response.data
  },

  async getInvoices() {
    const response = await api.get('/getinvoices')
    return response.data
  },

  async markInvoices(payload) {
    const response = await api.post('/markinvoices', payload)
    return response.data
  },

  async deleteInvoice(payload) {
    const response = await api.post('/deleteinvoice', payload)
    return response.data
  },

  async getCarers() {
    const response = await api.get('/getcarers?lightweight=true')
    return response.data
  },

  async getServiceUsers() {
    const response = await api.get('/getactivesu')
    return response.data
  }
}
