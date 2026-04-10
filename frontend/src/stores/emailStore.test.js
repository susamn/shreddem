import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEmailStore } from './emailStore'
import api from '../services/api'

vi.mock('../services/api', () => ({
  default: {
    getAuthStatus: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getProgress: vi.fn(),
    getEmails: vi.fn(),
    getSenders: vi.fn(),
    getSummary: vi.fn(),
    getAutoPull: vi.fn(),
    startFetch: vi.fn(),
    startRefresh: vi.fn(),
    startDelete: vi.fn(),
    startDeleteBySender: vi.fn(),
    startDeleteBulkSenders: vi.fn(),
    setAutoPull: vi.fn(),
  }
}))

describe('Email Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('initial state is correct', () => {
    const store = useEmailStore()
    expect(store.authenticated).toBe(false)
    expect(store.emails).toEqual([])
    expect(store.selectedUids.size).toBe(0)
  })

  it('checkAuth sets authenticated status', async () => {
    const store = useEmailStore()
    api.getAuthStatus.mockResolvedValue({ data: { authenticated: true, profile: { email: 't@g.com' } } })
    api.getProgress.mockResolvedValue({ data: { status: 'idle' } })
    api.getAutoPull.mockResolvedValue({ data: { enabled: false, interval: 0 } })
    api.getEmails.mockResolvedValue({ data: { emails: [], total: 0 } })
    api.getSenders.mockResolvedValue({ data: { senders: [] } })
    api.getSummary.mockResolvedValue({ data: { total: 0 } })

    await store.checkAuth()
    expect(store.authenticated).toBe(true)
    expect(store.profile.email).toBe('t@g.com')
  })

  it('toggles selection correctly', () => {
    const store = useEmailStore()
    store.toggleSelect('1')
    expect(store.selectedUids.has('1')).toBe(true)
    store.toggleSelect('1')
    expect(store.selectedUids.has('1')).toBe(false)
  })

  it('toggles select all correctly', () => {
    const store = useEmailStore()
    store.emails = [{ uid: '1' }, { uid: '2' }]
    store.toggleSelectAll()
    expect(store.selectedUids.size).toBe(2)
    store.toggleSelectAll()
    expect(store.selectedUids.size).toBe(0)
  })

  it('bulk delete senders calls api', async () => {
    const store = useEmailStore()
    store.selectedSenderEmails = new Set(['a@b.com'])
    await store.deleteSelectedSenders()
    expect(api.startDeleteBulkSenders).toHaveBeenCalledWith(['a@b.com'])
  })

  it('sets page and loads emails', async () => {
    const store = useEmailStore()
    api.getEmails.mockResolvedValue({ data: { emails: [{ uid: '1' }], total: 1 } })
    await store.setPage(2)
    expect(store.currentPage).toBe(2)
    expect(api.getEmails).toHaveBeenCalled()
  })
})
