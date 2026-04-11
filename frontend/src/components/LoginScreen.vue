<template>
  <div class="login-screen">
    <div class="login-card">
      <svg class="login-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#4285f4" stroke-width="1.5">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M22 4L12 13L2 4" />
      </svg>
      <h2>Gmail Client</h2>
      <p class="login-desc">
        Sign in with your Gmail address and an App Password
        to scan and analyze your inbox.
      </p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="email">Gmail Address</label>
          <input
            id="email"
            type="email"
            v-model="emailAddr"
            placeholder="you@gmail.com"
            required
            autocomplete="email"
          />
        </div>
        <div class="form-group">
          <label for="password">App Password</label>
          <input
            id="password"
            type="password"
            v-model="appPassword"
            placeholder="xxxx xxxx xxxx xxxx"
            required
            autocomplete="current-password"
          />
        </div>
        <div class="form-group">
          <label for="lockCode">Lock Code (Required)</label>
          <input
            id="lockCode"
            type="password"
            v-model="lockCode"
            placeholder="Set a quick unlock code"
            required
          />
        </div>

        <button class="btn btn-primary btn-lg" type="submit" :disabled="loading">
          <template v-if="loading">
            <span class="spinner"></span> Connecting...
          </template>
          <template v-else>
            Sign In
          </template>
        </button>
      </form>

      <p v-if="error" class="login-error">{{ error }}</p>

      <details class="help-section">
        <summary>How to get an App Password</summary>
        <ol>
          <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank">Google App Passwords</a></li>
          <li>You may need to enable 2-Step Verification first</li>
          <li>Select app: "Mail", device: "Other" (enter "Gmail Client")</li>
          <li>Click Generate — copy the 16-character password</li>
          <li>Paste it above (spaces are fine)</li>
        </ol>
      </details>

      <p class="login-note">
        Your credentials are only used to connect via IMAP and are never stored on disk.
        Only email headers are read — no message bodies.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useEmailStore } from '../stores/emailStore.js'

const store = useEmailStore()
const emailAddr = ref('')
const appPassword = ref('')
const lockCode = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await store.login(emailAddr.value, appPassword.value, lockCode.value)
    store.startFetch()
  } catch (err) {
    error.value = typeof err === 'string' ? err : 'Login failed. Check your email and app password.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-screen {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 70vh;
}

.login-card {
  text-align: center;
  background: var(--surface);
  padding: 40px 36px;
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  max-width: 440px;
  width: 100%;
}

.login-icon { margin-bottom: 12px; }

.login-card h2 {
  font-size: 1.5rem;
  margin-bottom: 6px;
}

.login-desc {
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin-bottom: 24px;
  line-height: 1.5;
}

.login-form { text-align: left; }

.form-group {
  margin-bottom: 14px;
}

.form-group label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--text-secondary);
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
  transition: border-color 0.15s;
}

.form-group input:focus { border-color: var(--primary); }

.btn-lg {
  padding: 12px 32px;
  font-size: 1rem;
  width: 100%;
  margin-top: 8px;
}

.login-error {
  color: var(--danger);
  margin-top: 12px;
  font-size: 0.85rem;
}

.help-section {
  text-align: left;
  margin-top: 20px;
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.help-section summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--primary);
}

.help-section ol {
  margin-top: 8px;
  padding-left: 20px;
  line-height: 1.8;
}

.help-section a {
  color: var(--primary);
  text-decoration: none;
}

.help-section a:hover { text-decoration: underline; }

.login-note {
  margin-top: 16px;
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
