<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <div class="search-box">
        <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        <input
          type="text"
          placeholder="Search by subject, sender name, or email..."
          :value="store.searchQuery"
          @input="onSearch($event.target.value)"
        />
        <button v-if="store.searchQuery" class="clear-btn" @click="onSearch('')">&times;</button>
      </div>
    </div>

    <div class="toolbar-right">
      <div class="view-toggle">
        <button
          class="btn btn-ghost"
          :class="{ active: store.viewMode === 'emails' }"
          @click="store.viewMode = 'emails'"
        >
          Emails
        </button>
        <button
          class="btn btn-ghost"
          :class="{ active: store.viewMode === 'senders' }"
          @click="store.viewMode = 'senders'"
        >
          By Sender
        </button>
      </div>

      <select class="sort-select" @change="onSortChange" :value="currentSort">
        <option value="date-desc">Newest first</option>
        <option value="date-asc">Oldest first</option>
        <option value="sender-asc">Sender A-Z</option>
        <option value="sender-desc">Sender Z-A</option>
        <option value="subject-asc">Subject A-Z</option>
      </select>

      <button
        class="btn btn-ghost"
        @click="store.refreshEmails()"
        :disabled="store.isBusy"
        title="Pull new emails (incremental)"
      >
        ↻ Refresh
      </button>

      <!-- Auto-pull dropdown -->
      <div class="auto-pull">
        <select
          class="sort-select"
          :value="store.autoPullInterval"
          @change="onAutoPullChange"
          title="Auto-pull interval"
        >
          <option :value="0">Auto-pull: Off</option>
          <option :value="30">Every 30s</option>
          <option :value="60">Every 1 min</option>
          <option :value="120">Every 2 min</option>
          <option :value="300">Every 5 min</option>
          <option :value="600">Every 10 min</option>
        </select>
        <span v-if="store.autoPullEnabled" class="auto-pull-dot" title="Auto-pull active"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()

let debounceTimer = null
function onSearch(val) {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    store.search(val)
  }, 300)
}

const currentSort = computed(() => `${store.sortBy}-${store.sortOrder}`)

function onSortChange(e) {
  const [field, order] = e.target.value.split('-')
  store.setSort(field, order)
}

function onAutoPullChange(e) {
  const interval = parseInt(e.target.value, 10)
  store.setAutoPull(interval)
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-left { flex: 1; min-width: 250px; }
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  width: 100%;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary);
}

.search-box input {
  width: 100%;
  padding: 10px 36px 10px 38px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.9rem;
  background: var(--surface);
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.search-box input:focus { border-color: var(--primary); }

.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px 8px;
}

.view-toggle { display: flex; gap: 4px; }

.sort-select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 0.85rem;
  cursor: pointer;
}

.auto-pull {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.auto-pull-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 7px;
  height: 7px;
  background: var(--success);
  border-radius: 50%;
  pointer-events: none;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
