<template>
  <div class="app" :class="{ 'dark': isDark }">
    <header class="header">
      <div class="header-left">
        <svg class="logo" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M22 4L12 13L2 4" />
        </svg>
        <h1>Gmail Client</h1>
      </div>
      <div class="header-right" v-if="store.authenticated">
        <button
          class="btn btn-ghost"
          @click="store.startFetch()"
          :disabled="store.isBusy"
          title="Full Refetch (clear local and redownload all headers)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          Full Refetch
        </button>
        <span class="user-email">{{ store.profile?.email }}</span>
        <button class="btn btn-ghost" @click="toggleDark">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
        <button class="btn btn-ghost" @click="store.logout()">Logout</button>
      </div>
    </header>

    <main class="main">
      <!-- Login screen -->
      <LoginScreen v-if="!store.authenticated" />

      <!-- Dashboard -->
      <template v-else>
        <!-- Show start button only if idle and no data -->
        <div v-if="store.progress.status === 'idle' && !store.hasData" class="start-section">
          <button class="btn btn-primary btn-lg" @click="store.startFetch()">
            Start Fetching Emails
          </button>
        </div>

        <!-- Show data as soon as we have any -->
        <template v-if="store.hasData || store.progress.status === 'done'">
          <SummaryBar />
          <Toolbar />
          <EmailList v-if="store.viewMode === 'emails'" />
          <SenderList v-if="store.viewMode === 'senders'" />
        </template>

        <!-- Error state -->
        <div v-if="store.progress.status === 'error'" class="error-box">
          <p>Error: {{ store.progress.error }}</p>
          <button class="btn btn-primary" @click="store.startFetch()">Retry</button>
        </div>

        <!-- Floating progress bar (bottom-right) — shows for fetch, delete, etc. -->
        <ProgressBar v-if="store.isBusy" />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useEmailStore } from './stores/emailStore.js'
import LoginScreen from './components/LoginScreen.vue'
import ProgressBar from './components/ProgressBar.vue'
import SummaryBar from './components/SummaryBar.vue'
import Toolbar from './components/Toolbar.vue'
import EmailList from './components/EmailList.vue'
import SenderList from './components/SenderList.vue'

const store = useEmailStore()
const isDark = ref(false)

function toggleDark() {
  isDark.value = !isDark.value
}

onMounted(async () => {
  await store.checkAuth()
})
</script>

<style>
/* ── Reset & Base ──────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f8f9fa;
  --surface: #ffffff;
  --text: #1a1a2e;
  --text-secondary: #6c757d;
  --border: #dee2e6;
  --primary: #4285f4;
  --primary-hover: #3367d6;
  --danger: #dc3545;
  --success: #28a745;
  --warning: #ffc107;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.1);
}

.dark {
  --bg: #1a1a2e;
  --surface: #16213e;
  --text: #e8e8e8;
  --text-secondary: #a0a0b0;
  --border: #2a2a4a;
  --shadow: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.4);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}

.app { min-height: 100vh; }

/* ── Header ────────────────────────────────────────────── */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h1 {
  font-size: 1.2rem;
  font-weight: 600;
}

.logo { color: var(--primary); }

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-email {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

/* ── Main ──────────────────────────────────────────────── */
.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

/* ── Start section ─────────────────────────────────────── */
.start-section {
  display: flex;
  justify-content: center;
  padding: 80px 20px;
}

/* ── Buttons ───────────────────────────────────────────── */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover { background: var(--primary-hover); }

.btn-lg {
  padding: 14px 36px;
  font-size: 1rem;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-ghost:hover {
  background: var(--border);
  color: var(--text);
}

.btn-ghost.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

/* ── Utilities ─────────────────────────────────────────── */
.error-box {
  text-align: center;
  padding: 40px;
  color: var(--danger);
}

.error-box p { margin-bottom: 16px; }
</style>
