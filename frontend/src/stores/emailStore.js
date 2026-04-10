import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api.js'

export const useEmailStore = defineStore('email', () => {
  // ── State ──────────────────────────────────────────────
  const authenticated = ref(false)
  const profile = ref(null)
  const emails = ref([])
  const senders = ref([])
  const summary = ref({ total: 0, read: 0, unread: 0, unique_senders: 0 })

  // Progress (polled from backend)
  const progress = ref({ total: 0, processed: 0, percent: 0, status: 'idle', action: 'fetch', error: null })
  const isBusy = computed(() => ['discovering', 'fetching', 'deleting'].includes(progress.value.status))
  const hasData = computed(() => emails.value.length > 0)

  // Selection (uses uid)
  const selectedUids = ref(new Set())
  const allSelected = computed(() => {
    if (emails.value.length === 0) return false
    return emails.value.every(e => selectedUids.value.has(e.uid))
  })
  const someSelected = computed(() => selectedUids.value.size > 0 && !allSelected.value)
  const selectionCount = computed(() => selectedUids.value.size)

  // Auto-pull
  const autoPullEnabled = ref(false)
  const autoPullInterval = ref(0)

  // View state
  const viewMode = ref('emails')
  const searchQuery = ref('')
  const sortBy = ref('date')
  const sortOrder = ref('desc')
  const currentPage = ref(1)
  const pageSize = ref(50)
  const totalEmails = ref(0)
  const totalPages = ref(0)
  const senderSortBy = ref('total')
  const senderSortOrder = ref('desc')

  // Polling timer
  let _pollTimer = null

  // ── Polling engine ─────────────────────────────────────
  // Polls backend for progress + data while an operation is running.
  // Also does a single poll on page load to show current state.

  function _startPolling() {
    _stopPolling()
    _pollTimer = setInterval(_pollTick, 1000)
  }

  function _stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  async function _pollTick() {
    try {
      const { data } = await api.getProgress()
      progress.value = data

      // Refresh data while operations run
      if (['fetching', 'deleting'].includes(data.status)) {
        loadEmails()
        loadSenders()
        loadSummary()
      }

      // Operation finished — do a final data refresh and stop fast-polling
      if (data.status === 'done' || data.status === 'error') {
        loadEmails()
        loadSenders()
        loadSummary()
        _stopPolling()
      }
    } catch {
      // Backend might be restarting, keep trying
    }
  }

  // ── Auth ───────────────────────────────────────────────

  async function checkAuth() {
    try {
      const { data } = await api.getAuthStatus()
      authenticated.value = data.authenticated
      if (data.authenticated) {
        profile.value = data.profile
        // Load whatever data the backend already has
        await Promise.all([loadEmails(), loadSenders(), loadSummary()])
        // Check current progress (maybe a fetch is still running)
        const prog = await api.getProgress()
        progress.value = prog.data
        if (['fetching', 'deleting', 'discovering'].includes(prog.data.status)) {
          _startPolling()
        }
        // Load auto-pull config
        const ap = await api.getAutoPull()
        autoPullEnabled.value = ap.data.enabled
        autoPullInterval.value = ap.data.interval
      }
    } catch {
      authenticated.value = false
    }
  }

  async function login(emailAddr, appPassword) {
    try {
      const { data } = await api.login(emailAddr, appPassword)
      if (data.success) {
        authenticated.value = true
        profile.value = data.profile
      }
      return data
    } catch (err) {
      throw err.response?.data?.detail || err.message
    }
  }

  async function logout() {
    _stopPolling()
    await api.logout()
    authenticated.value = false
    profile.value = null
    emails.value = []
    senders.value = []
    summary.value = { total: 0, read: 0, unread: 0, unique_senders: 0 }
    progress.value = { total: 0, processed: 0, percent: 0, status: 'idle', action: 'fetch', error: null }
    selectedUids.value = new Set()
    autoPullEnabled.value = false
    autoPullInterval.value = 0
  }

  // ── Selection ──────────────────────────────────────────

  function toggleSelect(uid) {
    const s = new Set(selectedUids.value)
    s.has(uid) ? s.delete(uid) : s.add(uid)
    selectedUids.value = s
  }

  function toggleSelectAll() {
    if (allSelected.value) {
      selectedUids.value = new Set()
    } else {
      selectedUids.value = new Set(emails.value.map(e => e.uid))
    }
  }

  function clearSelection() {
    selectedUids.value = new Set()
  }

  // ── Trigger background operations ──────────────────────

  async function startFetch() {
    await api.startFetch()
    _startPolling()
  }

  async function refreshEmails() {
    if (isBusy.value) return
    await api.startRefresh()
    _startPolling()
  }

  async function deleteSelected() {
    const uids = Array.from(selectedUids.value)
    if (uids.length === 0) return
    clearSelection()
    await api.startDelete(uids)
    _startPolling()
  }

  async function deleteBySender(senderEmail) {
    clearSelection()
    await api.startDeleteBySender(senderEmail)
    _startPolling()
  }

  // ── Auto-pull ──────────────────────────────────────────

  async function setAutoPull(intervalSeconds) {
    try {
      const { data } = await api.setAutoPull(intervalSeconds)
      autoPullEnabled.value = data.enabled
      autoPullInterval.value = data.interval
    } catch (err) {
      console.error('Failed to set auto-pull:', err)
    }
  }

  // ── Data loading ───────────────────────────────────────

  async function loadEmails() {
    try {
      const { data } = await api.getEmails({
        search: searchQuery.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        page: currentPage.value,
        page_size: pageSize.value,
      })
      emails.value = data.emails
      totalEmails.value = data.total
      totalPages.value = data.total_pages
    } catch {}
  }

  async function loadSenders() {
    try {
      const { data } = await api.getSenders({
        sort_by: senderSortBy.value,
        sort_order: senderSortOrder.value,
      })
      senders.value = data.senders
    } catch {}
  }

  async function loadSummary() {
    try {
      const { data } = await api.getSummary()
      summary.value = data
    } catch {}
  }

  // ── Search / filter ────────────────────────────────────

  function search(query) {
    searchQuery.value = query
    currentPage.value = 1
    loadEmails()
  }

  function setSort(field, order) {
    sortBy.value = field
    sortOrder.value = order
    currentPage.value = 1
    loadEmails()
  }

  function setPage(page) {
    currentPage.value = page
    loadEmails()
  }

  function setSenderSort(field, order) {
    senderSortBy.value = field
    senderSortOrder.value = order
    loadSenders()
  }

  function filterBySender(senderEmail) {
    viewMode.value = 'emails'
    searchQuery.value = senderEmail
    currentPage.value = 1
    loadEmails()
  }

  return {
    authenticated, profile, emails, senders, summary,
    progress, isBusy, hasData,
    selectedUids, allSelected, someSelected, selectionCount,
    autoPullEnabled, autoPullInterval,
    viewMode, searchQuery, sortBy, sortOrder,
    currentPage, pageSize, totalEmails, totalPages,
    senderSortBy, senderSortOrder,
    checkAuth, login, logout,
    toggleSelect, toggleSelectAll, clearSelection,
    startFetch, refreshEmails, setAutoPull,
    deleteSelected, deleteBySender,
    loadEmails, loadSenders, loadSummary,
    search, setSort, setPage, setSenderSort, filterBySender,
  }
})
