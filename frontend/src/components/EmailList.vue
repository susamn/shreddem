<template>
  <div class="email-list">
    <!-- Bulk action bar -->
    <div class="bulk-bar" v-if="store.selectionCount > 0">
      <span class="bulk-count">{{ store.selectionCount }} selected</span>
      <button class="btn btn-danger" @click="handleDelete" :disabled="store.isBusy">
        Delete Selected
      </button>
      <button class="btn btn-ghost" @click="store.clearSelection()">Cancel</button>
    </div>

    <div class="list-header" v-else>
      <span class="count">{{ store.totalEmails.toLocaleString() }} emails</span>
    </div>

    <div v-if="store.emails.length === 0" class="empty-state">
      <p v-if="store.searchQuery">No emails match "{{ store.searchQuery }}"</p>
      <p v-else>No emails loaded yet.</p>
    </div>

    <div class="email-table-wrap" v-else>
      <table class="email-table">
        <thead>
          <tr>
            <th class="col-check">
              <input
                type="checkbox"
                :checked="store.allSelected"
                :indeterminate="store.someSelected"
                @change="store.toggleSelectAll()"
                title="Select all on this page"
              />
            </th>
            <th class="col-status"></th>
            <th class="col-sender">Sender</th>
            <th class="col-subject">Subject</th>
            <th class="col-date">Date</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="email in store.emails"
            :key="email.uid"
            :class="{ unread: !email.is_read, selected: store.selectedUids.has(email.uid) }"
          >
            <td class="col-check">
              <input
                type="checkbox"
                :checked="store.selectedUids.has(email.uid)"
                @change="store.toggleSelect(email.uid)"
              />
            </td>
            <td class="col-status">
              <span class="dot" :class="email.is_read ? 'read' : 'unread'" :title="email.is_read ? 'Read' : 'Unread'"></span>
            </td>
            <td class="col-sender">
              <span class="sender-name">{{ email.sender_name }}</span>
              <span class="sender-email">{{ email.sender_email }}</span>
            </td>
            <td class="col-subject">
              <span class="subject-text">{{ email.subject }}</span>
              <span class="snippet">{{ email.snippet }}</span>
            </td>
            <td class="col-date">{{ formatDate(email.date) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="store.totalPages > 1">
      <button
        class="btn btn-ghost"
        :disabled="store.currentPage <= 1"
        @click="store.setPage(store.currentPage - 1)"
      >
        ← Prev
      </button>
      <span class="page-info">
        Page {{ store.currentPage }} of {{ store.totalPages }}
      </span>
      <button
        class="btn btn-ghost"
        :disabled="store.currentPage >= store.totalPages"
        @click="store.setPage(store.currentPage + 1)"
      >
        Next →
      </button>
    </div>
  </div>
</template>

<script setup>
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()

function handleDelete() {
  if (confirm(`Delete ${store.selectionCount} email(s)? This will move them to Trash.`)) {
    store.deleteSelected()
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now - d) / 86400000)

  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays < 7) {
    return d.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })
  } else {
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
  }
}
</script>

<style scoped>
.email-list {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

/* Bulk action bar */
.bulk-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #e8f0fe;
  border-bottom: 1px solid var(--primary);
}

.dark .bulk-bar {
  background: rgba(66, 133, 244, 0.15);
}

.bulk-count {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary);
  margin-right: auto;
}

.btn-danger {
  background: var(--danger);
  color: white;
  padding: 6px 14px;
  border: none;
  border-radius: var(--radius);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
}

.btn-danger:hover { background: #c82333; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }

.list-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.count {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.email-table-wrap { overflow-x: auto; }

.email-table {
  width: 100%;
  border-collapse: collapse;
}

.email-table th {
  text-align: left;
  padding: 10px 12px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.email-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}

.email-table tr:hover { background: rgba(66, 133, 244, 0.04); }
.email-table tr.unread { font-weight: 600; }
.email-table tr.selected { background: rgba(66, 133, 244, 0.08); }

.col-check {
  width: 36px;
  text-align: center;
}

.col-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--primary);
}

.col-status { width: 32px; text-align: center; }

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.read { background: var(--border); }
.dot.unread { background: var(--primary); }

.col-sender { width: 220px; }

.sender-name {
  display: block;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.sender-email {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.col-subject { min-width: 200px; }

.subject-text {
  display: block;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.snippet {
  display: block;
  font-size: 0.78rem;
  color: var(--text-secondary);
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.col-date {
  width: 140px;
  font-size: 0.83rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px;
  border-top: 1px solid var(--border);
}

.page-info {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
