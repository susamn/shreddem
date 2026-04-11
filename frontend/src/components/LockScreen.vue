<template>
  <div class="lock-screen">
    <div class="lock-card">
      <svg class="lock-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
      </svg>
      <h2>Session Locked</h2>
      <p class="lock-desc">
        Please enter your lock code to unlock your mailbox.
      </p>

      <form @submit.prevent="handleUnlock" class="lock-form">
        <div class="form-group">
          <input
            type="password"
            v-model="code"
            placeholder="Enter lock code"
            required
            autofocus
          />
        </div>
        <button class="btn btn-primary btn-lg" type="submit" :disabled="loading">
          <template v-if="loading">
            <span class="spinner"></span> Unlocking...
          </template>
          <template v-else>
            Unlock
          </template>
        </button>
      </form>
      <p v-if="error" class="lock-error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()
const code = ref('')
const loading = ref(false)
const error = ref('')

async function handleUnlock() {
  loading.value = true
  error.value = ''
  try {
    await store.verifyLockCode(code.value)
  } catch (err) {
    error.value = typeof err === 'string' ? err : 'Invalid lock code.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.lock-screen {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--bg);
  z-index: 9999;
}
.lock-card {
  text-align: center;
  background: var(--surface);
  padding: 40px 36px;
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  max-width: 400px;
  width: 100%;
}
.lock-icon {
  margin-bottom: 12px;
  color: var(--primary);
}
.lock-card h2 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}
.lock-desc {
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin-bottom: 24px;
}
.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.95rem;
  background: var(--bg);
  color: var(--text);
  outline: none;
  text-align: center;
}
.form-group input:focus { border-color: var(--primary); }
.btn-lg {
  padding: 12px 32px;
  font-size: 1rem;
  width: 100%;
  margin-top: 16px;
}
.lock-error {
  color: var(--danger);
  margin-top: 12px;
  font-size: 0.85rem;
}
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin-right: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
