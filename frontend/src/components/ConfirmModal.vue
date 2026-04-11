<template>
  <div class="modal-overlay" v-if="store.confirmDialog.isOpen" @click.self="cancel">
    <div class="modal-content glass-effect">
      <div class="modal-header">
        <svg v-if="store.confirmDialog.intent === 'danger'" class="icon danger" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <svg v-else class="icon info" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
        <h3>{{ store.confirmDialog.title }}</h3>
      </div>
      <div class="modal-body">
        <p>{{ store.confirmDialog.message }}</p>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" @click="cancel">{{ store.confirmDialog.cancelText }}</button>
        <button class="btn" :class="buttonClass" @click="confirm">{{ store.confirmDialog.confirmText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()

const buttonClass = computed(() => {
  return store.confirmDialog.intent === 'danger' ? 'btn-danger' : 'btn-primary'
})

function confirm() {
  store.resolveConfirm(true)
}

function cancel() {
  store.resolveConfirm(false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.15s ease-out;
}

.modal-content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.glass-effect {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

.dark .glass-effect {
  background: rgba(22, 33, 62, 0.95);
}

.modal-header {
  padding: 20px 24px 10px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.icon.danger {
  color: var(--danger);
}

.icon.info {
  color: var(--primary);
}

.modal-body {
  padding: 0 24px 20px;
}

.modal-body p {
  color: var(--text-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  background: rgba(0, 0, 0, 0.02);
  border-top: 1px solid var(--border);
}

.dark .modal-actions {
  background: rgba(255, 255, 255, 0.02);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes scaleIn {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
</style>
