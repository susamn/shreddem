import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default {
  // Auth
  getAuthStatus: () => api.get('/auth/status'),
  login: (email, app_password) => api.post('/auth/login', { email, app_password }),
  logout: () => api.post('/auth/logout'),

  // Background task triggers (return immediately)
  startFetch: () => api.post('/emails/fetch'),
  startRefresh: () => api.post('/emails/refresh'),
  startDelete: (uids) => api.post('/emails/delete', { uids }),
  startDeleteBySender: (senderEmail) => api.post('/emails/delete-by-sender', { sender_email: senderEmail }),

  // State polling
  getProgress: () => api.get('/emails/progress'),
  getEmails: (params) => api.get('/emails', { params }),
  getSenders: (params) => api.get('/emails/senders', { params }),
  getSummary: () => api.get('/emails/summary'),

  // Auto-pull
  getAutoPull: () => api.get('/auto-pull'),
  setAutoPull: (interval) => api.post('/auto-pull', { interval }),
}
