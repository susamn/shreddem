<template>
  <div class="summary-bar">
    <div class="stat-card">
      <span class="stat-value">{{ store.summary.total.toLocaleString() }}</span>
      <span class="stat-label">Total Emails</span>
    </div>
    <div class="stat-card">
      <span class="stat-value read">{{ store.summary.read.toLocaleString() }}</span>
      <span class="stat-label">Read</span>
    </div>
    <div class="stat-card">
      <span class="stat-value unread">{{ store.summary.unread.toLocaleString() }}</span>
      <span class="stat-label">Unread</span>
    </div>
    <div class="stat-card">
      <span class="stat-value senders">{{ store.summary.unique_senders.toLocaleString() }}</span>
      <span class="stat-label">Unique Senders</span>
    </div>
  </div>
</template>

<script setup>
import { useEmailStore } from '../stores/emailStore.js'
const store = useEmailStore()
</script>

<style scoped>
.summary-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--surface);
  padding: 16px 20px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--primary);
}

.stat-value.read { color: var(--success); }
.stat-value.unread { color: var(--danger); }
.stat-value.senders { color: #8e44ad; }

.stat-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 2px;
}
</style>
