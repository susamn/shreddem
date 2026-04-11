<template>
  <div class="sender-list">
    <!-- Bulk action bar -->
    <div class="bulk-bar" v-if="store.senderSelectionCount > 0">
      <span class="bulk-count">{{ store.senderSelectionCount }} senders selected</span>
      <button class="btn btn-danger" @click="handleDeleteSelected" :disabled="store.isBusy">
        Delete All from Selected Senders
      </button>
      <button class="btn btn-ghost" @click="store.clearSenderSelection()">Cancel</button>
    </div>

    <div class="list-header" v-else>
      <div class="header-left">
        <input
          type="checkbox"
          class="master-check"
          :checked="store.allSendersSelected"
          :indeterminate="store.someSendersSelected"
          @change="store.toggleAllSendersSelect()"
          title="Select all senders"
        />
        <span class="count">{{ store.senders.length }} unique senders</span>
      </div>
      <div class="sender-sort">
        <select @change="onSortChange" :value="currentSort">
          <option value="total-desc">Most emails</option>
          <option value="total-asc">Fewest emails</option>
          <option value="unread-desc">Most unread</option>
          <option value="name-asc">Name A-Z</option>
          <option value="name-desc">Name Z-A</option>
        </select>
      </div>
    </div>

    <div v-if="store.senders.length === 0" class="empty-state">
      <p>No sender data yet.</p>
    </div>

    <div class="sender-grid" v-else>
      <div
        class="sender-card"
        v-for="sender in store.senders"
        :key="sender.sender_email"
        :class="{ selected: store.selectedSenderEmails.has(sender.sender_email) }"
      >
        <div class="sender-check">
          <input
            type="checkbox"
            :checked="store.selectedSenderEmails.has(sender.sender_email)"
            @change="store.toggleSenderSelect(sender.sender_email)"
          />
        </div>
        <div class="sender-avatar" @click="store.filterBySender(sender.sender_email)">
          {{ getInitials(sender.sender_name) }}
        </div>
        <div class="sender-info" @click="store.filterBySender(sender.sender_email)">
          <span class="sender-name">{{ sender.sender_name }}</span>
          <span class="sender-email">{{ sender.sender_email }}</span>
          <span class="sender-date">Latest: {{ formatDate(sender.latest_date) }}</span>
        </div>
        <div class="sender-stats">
          <div class="stat">
            <span class="stat-num">{{ sender.total }}</span>
            <span class="stat-lbl">Total</span>
          </div>
          <div class="stat">
            <span class="stat-num read">{{ sender.read }}</span>
            <span class="stat-lbl">Read</span>
          </div>
          <div class="stat">
            <span class="stat-num unread">{{ sender.unread }}</span>
            <span class="stat-lbl">Unread</span>
          </div>
        </div>
        <button
          class="delete-btn"
          @click.stop="handleDeleteSender(sender)"
          :disabled="store.isBusy"
          title="Delete all emails from this sender"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- Pagination -->
    <div class="pagination" v-if="store.senderTotalPages > 1">
      <button
        class="btn btn-ghost"
        :disabled="store.senderCurrentPage <= 1"
        @click="store.setSenderPage(store.senderCurrentPage - 1)"
      >
        ← Prev
      </button>
      <span class="page-info">
        Page {{ store.senderCurrentPage }} of {{ store.senderTotalPages }}
      </span>
      <button
        class="btn btn-ghost"
        :disabled="store.senderCurrentPage >= store.senderTotalPages"
        @click="store.setSenderPage(store.senderCurrentPage + 1)"
      >
        Next →
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()

const currentSort = computed(() => `${store.senderSortBy}-${store.senderSortOrder}`)

function onSortChange(e) {
  const [field, order] = e.target.value.split('-')
  store.setSenderSort(field, order)
}

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

async function handleDeleteSender(sender) {
  const confirmed = await store.askConfirm({
    title: 'Delete Sender',
    message: `Delete all ${sender.total} email(s) from ${sender.sender_name} (${sender.sender_email})? This will move them to Trash.`,
    confirmText: 'Delete Everything',
    intent: 'danger'
  })
  if (confirmed) {
    store.deleteBySender(sender.sender_email)
  }
}

async function handleDeleteSelected() {
  const confirmed = await store.askConfirm({
    title: 'Delete Selected Senders',
    message: `Delete ALL emails from the ${store.senderSelectionCount} selected senders? This will move them to Trash.`,
    confirmText: 'Delete Bulk',
    intent: 'danger'
  })
  if (confirmed) {
    store.deleteSelectedSenders()
  }
}
</script>

<style scoped>
.sender-list {
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

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.master-check {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--primary);
}

.count {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.sender-sort select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 0.8rem;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.sender-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1px;
  background: var(--border);
}

.sender-card {
  display: grid;
  grid-template-columns: 24px 42px 1fr auto 32px;
  gap: 4px 10px;
  padding: 14px 12px;
  background: var(--surface);
  align-items: center;
  transition: background 0.1s;
}

.sender-card:hover { background: rgba(66, 133, 244, 0.04); }
.sender-card.selected { background: rgba(66, 133, 244, 0.08); }

.sender-check {
  display: flex;
  align-items: center;
  justify-content: center;
}

.sender-check input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--primary);
}

.sender-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4285f4, #34a853);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}

.sender-info {
  cursor: pointer;
  overflow: hidden;
}

.sender-name {
  display: block;
  font-weight: 600;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sender-email {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.sender-date {
  display: block;
  font-size: 0.7rem;
  color: var(--text-secondary);
  margin-top: 2px;
}

.sender-stats {
  display: flex;
  gap: 10px;
  align-items: center;
}

.stat { text-align: center; }

.stat-num {
  display: block;
  font-weight: 700;
  font-size: 0.95rem;
}

.stat-num.read { color: var(--success); }
.stat-num.unread { color: var(--danger); }

.stat-lbl {
  font-size: 0.65rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  opacity: 0;
}

.sender-card:hover .delete-btn { opacity: 1; }

.delete-btn:hover {
  background: rgba(220, 53, 69, 0.1);
  color: var(--danger);
}

.delete-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
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

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px;
  border-top: 1px solid var(--border);
  margin-top: auto;
}

.page-info {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
