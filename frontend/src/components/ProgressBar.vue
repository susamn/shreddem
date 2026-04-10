<template>
  <div class="progress-float">
    <div class="progress-pill" :class="actionClass">
      <div class="progress-info">
        <!-- Discovering -->
        <template v-if="store.progress.status === 'discovering'">
          <span class="spinner"></span>
          <span>Discovering emails...</span>
        </template>

        <!-- Fetching -->
        <template v-else-if="store.progress.status === 'fetching'">
          <span class="progress-text">
            Fetching: <strong>{{ store.progress.processed.toLocaleString() }}</strong>
            / {{ store.progress.total.toLocaleString() }}
          </span>
          <span class="progress-pct">{{ store.progress.percent }}%</span>
        </template>

        <!-- Deleting -->
        <template v-else-if="store.progress.status === 'deleting'">
          <span class="progress-text">
            Deleting: <strong>{{ store.progress.processed.toLocaleString() }}</strong>
            / {{ store.progress.total.toLocaleString() }}
          </span>
          <span class="progress-pct">{{ store.progress.percent }}%</span>
        </template>
      </div>
      <div class="bar-wrap">
        <div
          class="bar"
          :class="{
            indeterminate: store.progress.status === 'discovering',
            'bar-delete': store.progress.action === 'delete',
          }"
          :style="['fetching', 'deleting'].includes(store.progress.status) ? { width: store.progress.percent + '%' } : {}"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()

const actionClass = computed(() => {
  return store.progress.action === 'delete' ? 'action-delete' : 'action-fetch'
})
</script>

<style scoped>
.progress-float {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.progress-pill {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  min-width: 280px;
}

.progress-pill.action-delete {
  border-color: var(--danger);
}

.progress-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 0.82rem;
  color: var(--text);
}

.progress-text { font-size: 0.82rem; }

.progress-pct {
  font-weight: 700;
  color: var(--primary);
  font-size: 0.82rem;
}

.action-delete .progress-pct { color: var(--danger); }

.bar-wrap {
  width: 100%;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.bar {
  height: 100%;
  background: linear-gradient(90deg, #4285f4, #34a853);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.bar.bar-delete {
  background: linear-gradient(90deg, #dc3545, #e85d04);
}

.bar.indeterminate {
  width: 40%;
  animation: slide 1.2s ease-in-out infinite;
}

@keyframes slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
