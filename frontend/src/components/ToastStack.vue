<script setup lang="ts">
import { lab } from '../state/useLabStore'
</script>

<template>
  <div class="toasts" aria-live="polite" aria-atomic="false">
    <transition-group name="toast">
      <div v-for="toast in lab.state.toasts" :key="toast.id" class="toast" :class="`toast-${toast.kind}`">
        <span class="toast-dot" aria-hidden="true"></span>
        <span>{{ toast.text }}</span>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 80;
  display: grid;
  gap: 8px;
  width: min(340px, calc(100vw - 36px));
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 13px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line-strong);
  background: var(--ink-800);
  box-shadow: var(--shadow);
  font-size: 13px;
}

.toast-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
  background: var(--muted);
}

.toast-ok {
  border-color: rgba(79, 185, 138, 0.4);
}
.toast-ok .toast-dot {
  background: var(--ok);
}

.toast-error {
  border-color: rgba(224, 96, 79, 0.45);
}
.toast-error .toast-dot {
  background: var(--bad);
}

.toast-info {
  border-color: rgba(72, 198, 212, 0.4);
}
.toast-info .toast-dot {
  background: var(--signal);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(12px);
}
</style>
